"""Operaciones de órdenes: la transacción pertenece al UoW recibido."""

import asyncio
import logging
from decimal import Decimal
from datetime import UTC, datetime

from app.core.errores import Conflicto, NoEncontrado, PermisoDenegado
from app.core.paginacion import Pagina, armar_pagina, calcular_ventana

from app.modules.ordenes.models import CodigoEstado, HistorialEstadoOrden, ItemOrden, OrdenTrabajo
from app.modules.ordenes.schemas import EntradaOrden, EstadoRespuesta, HistorialRespuesta, ItemRespuesta, OrdenDetalle, OrdenResumen

logger = logging.getLogger(__name__)


def resumen_respuesta(orden: OrdenTrabajo) -> OrdenResumen:
    return OrdenResumen(id=orden.id, estado=orden.estado, patente=orden.vehiculo.patente,
                        total=orden.total, creada_en=orden.creada_en, mecanico_id=orden.mecanico_id,
                        falla=orden.falla, cliente=orden.vehiculo.cliente.nombre)


def detalle_respuesta(orden: OrdenTrabajo) -> OrdenDetalle:
    return OrdenDetalle(
        id=orden.id, estado=orden.estado, patente=orden.vehiculo.patente,
        total=orden.total, creada_en=orden.creada_en, mecanico_id=orden.mecanico_id,
        falla=orden.falla, cliente=orden.vehiculo.cliente.nombre,
        items=[ItemRespuesta(repuesto_id=i.repuesto_id, codigo=i.repuesto.codigo,
                             descripcion=i.repuesto.descripcion, cantidad=i.cantidad,
                             precio_unitario=i.precio_unitario, subtotal=i.precio_unitario * i.cantidad)
               for i in sorted(orden.items, key=lambda item: item.id)],
        historial=[HistorialRespuesta.model_validate(h) for h in sorted(orden.historial, key=lambda h: (h.cuando, h.id))],
    )


class OrdenesService:
    def __init__(self, uow) -> None:
        self.uow = uow

    async def estados(self) -> list[EstadoRespuesta]:
        async with self.uow:
            return [EstadoRespuesta.model_validate(e) for e in await self.uow.estados.listar()]

    async def obtener(self, orden_id: int, usuario_id: int) -> OrdenDetalle:
        async with self.uow:
            # Un id fuera del tipo INTEGER no puede existir; evitar desbordar el bind.
            if not -2147483648 <= orden_id <= 2147483647:
                raise NoEncontrado("Orden no encontrada")
            orden = await self.uow.ordenes.detalle(orden_id)
            if orden is None:
                raise NoEncontrado("Orden no encontrada")
            roles = await self.uow.usuarios.roles_vigentes(usuario_id, datetime.now(UTC))
            if not {"ADMIN", "RECEPCION", "MECANICO"}.intersection(roles) and orden.vehiculo.cliente.usuario_id != usuario_id:
                raise PermisoDenegado("No tiene permisos para realizar esta operación")
            return detalle_respuesta(orden)

    async def listar(self, page: int, size: int, estado: str | None = None,
                     usuario_id: int | None = None) -> Pagina[OrdenResumen]:
        async with self.uow:
            total = await self.uow.ordenes.contar_filtradas(estado, usuario_id)
            ventana = calcular_ventana(total, page, size)
            ordenes = await self.uow.ordenes.listar(estado, usuario_id, ventana.offset, ventana.limit)
            return armar_pagina([resumen_respuesta(o) for o in ordenes], total, page, size, ventana)

    async def crear(self, datos: EntradaOrden, usuario_id: int) -> OrdenDetalle:
        async with self.uow:
            if not any(e.codigo == CodigoEstado.PENDIENTE for e in await self.uow.estados.listar()):
                raise Conflicto("El catálogo de estados no está disponible")
            if not -2147483648 <= datos.vehiculo_id <= 2147483647 or await self.uow.vehiculos.get_by_id(datos.vehiculo_id) is None:
                raise Conflicto("Vehículo inexistente o dado de baja")
            if any(not -2147483648 <= i.repuesto_id <= 2147483647 for i in datos.items):
                raise Conflicto("Repuesto inexistente o dado de baja")
            repuestos = {r.id: r for r in await self.uow.ordenes.repuestos_vigentes([i.repuesto_id for i in datos.items])}
            if len(repuestos) != len(datos.items):
                raise Conflicto("Repuesto inexistente o dado de baja")
            total = sum((repuestos[i.repuesto_id].precio * i.cantidad for i in datos.items), Decimal("0.00"))
            if total > Decimal("9999999999.99"):
                raise Conflicto("El total de la orden excede el importe permitido")
            orden = await self.uow.ordenes.add(OrdenTrabajo(
                vehiculo_id=datos.vehiculo_id, falla=datos.falla, estado=CodigoEstado.PENDIENTE,
                mecanico_id=None, total=total))
            for item in datos.items:
                await self.uow.items.add(ItemOrden(orden_id=orden.id, repuesto_id=item.repuesto_id,
                    cantidad=item.cantidad, precio_unitario=repuestos[item.repuesto_id].precio))
            await self.uow.historial.add(HistorialEstadoOrden(orden_id=orden.id,
                desde_estado=None, hasta_estado=CodigoEstado.PENDIENTE, usuario_id=usuario_id))
            cargada = await self.uow.ordenes.detalle(orden.id)
            respuesta = detalle_respuesta(cargada)
        return respuesta

    async def iniciar(self, orden_id: int, usuario_id: int) -> OrdenDetalle:
        async with self.uow:
            orden = await self._obtener_para_transicion(orden_id)
            await self._exigir_rol(usuario_id, "MECANICO")
            if orden.estado != CodigoEstado.PENDIENTE:
                raise Conflicto("La orden no está en un estado que permita esta operación")
            if not await self.uow.ordenes.actualizar_estado_condicional(
                orden_id, CodigoEstado.PENDIENTE, CodigoEstado.EN_REPARACION, usuario_id
            ):
                raise Conflicto("La orden no está en un estado que permita esta operación")
            orden.estado = CodigoEstado.EN_REPARACION
            orden.mecanico_id = usuario_id
            await self.uow.historial.add(
                HistorialEstadoOrden(
                    orden_id=orden_id,
                    desde_estado=CodigoEstado.PENDIENTE,
                    hasta_estado=CodigoEstado.EN_REPARACION,
                    usuario_id=usuario_id,
                )
            )
            cargada = await self.uow.ordenes.detalle(orden_id)
            return detalle_respuesta(cargada)

    async def cancelar(self, orden_id: int, usuario_id: int) -> OrdenDetalle:
        async with self.uow:
            orden = await self._obtener_para_transicion(orden_id)
            if not await self._puede_cancelar(orden, usuario_id):
                raise PermisoDenegado("No tiene permisos para realizar esta operación")
            if orden.estado != CodigoEstado.PENDIENTE:
                raise Conflicto("La orden no está en un estado que permita esta operación")
            if not await self.uow.ordenes.actualizar_estado_condicional(
                orden_id, CodigoEstado.PENDIENTE, CodigoEstado.CANCELADA
            ):
                raise Conflicto("La orden no está en un estado que permita esta operación")
            orden.estado = CodigoEstado.CANCELADA
            await self.uow.historial.add(
                HistorialEstadoOrden(
                    orden_id=orden_id,
                    desde_estado=CodigoEstado.PENDIENTE,
                    hasta_estado=CodigoEstado.CANCELADA,
                    usuario_id=usuario_id,
                )
            )
            cargada = await self.uow.ordenes.detalle(orden_id)
            return detalle_respuesta(cargada)

    async def terminar(self, orden_id: int, usuario_id: int) -> tuple[OrdenDetalle, int]:
        async with self.uow:
            orden = await self._obtener_para_transicion(orden_id)
            if not await self._puede_terminar(orden, usuario_id):
                raise PermisoDenegado(
                    "Solo el mecánico asignado o un administrador pueden terminar la orden"
                )
            if orden.estado != CodigoEstado.EN_REPARACION:
                raise Conflicto("La orden no está en un estado que permita esta operación")
            if not await self.uow.ordenes.actualizar_estado_condicional(
                orden_id, CodigoEstado.EN_REPARACION, CodigoEstado.TERMINADA
            ):
                raise Conflicto("La orden no está en un estado que permita esta operación")
            orden.estado = CodigoEstado.TERMINADA
            for item in orden.items:
                try:
                    await self.uow.repuestos.ajustar_stock(
                        item.repuesto_id,
                        -item.cantidad,
                        usuario_id,
                        "Orden terminada",
                        orden_id=orden_id,
                        incluir_baja=True,
                    )
                except Conflicto:
                    raise Conflicto(
                        f"Stock insuficiente para el repuesto {item.repuesto.codigo}"
                    ) from None
            await self.uow.historial.add(
                HistorialEstadoOrden(
                    orden_id=orden_id,
                    desde_estado=CodigoEstado.EN_REPARACION,
                    hasta_estado=CodigoEstado.TERMINADA,
                    usuario_id=usuario_id,
                )
            )
            cliente_id = orden.vehiculo.cliente.id
            cargada = await self.uow.ordenes.detalle(orden_id)
            return detalle_respuesta(cargada), cliente_id

    async def _obtener_para_transicion(self, orden_id: int) -> OrdenTrabajo:
        if not -2147483648 <= orden_id <= 2147483647:
            raise NoEncontrado("Orden no encontrada")
        orden = await self.uow.ordenes.detalle(orden_id)
        if orden is None:
            raise NoEncontrado("Orden no encontrada")
        return orden

    async def _exigir_rol(self, usuario_id: int, rol: str) -> None:
        roles = await self.uow.usuarios.roles_vigentes(usuario_id, datetime.now(UTC))
        if rol not in roles:
            raise PermisoDenegado("No tiene permisos para realizar esta operación")

    async def _puede_terminar(self, orden: OrdenTrabajo, usuario_id: int) -> bool:
        roles = await self.uow.usuarios.roles_vigentes(usuario_id, datetime.now(UTC))
        return "ADMIN" in roles or (
            orden.mecanico_id == usuario_id and "MECANICO" in roles
        )

    async def _puede_cancelar(self, orden: OrdenTrabajo, usuario_id: int) -> bool:
        roles = await self.uow.usuarios.roles_vigentes(usuario_id, datetime.now(UTC))
        return bool({"ADMIN", "RECEPCION"}.intersection(roles)) or (
            orden.vehiculo.cliente.usuario_id == usuario_id
        )


async def enviar_aviso(orden_id: int, cliente_id: int) -> None:
    await asyncio.sleep(0.5)
    logger.info("Aviso de orden terminada: orden_id=%s cliente_id=%s", orden_id, cliente_id)


async def avisar_cliente(orden_id: int, cliente_id: int) -> None:
    try:
        await enviar_aviso(orden_id, cliente_id)
    except Exception:
        logger.exception("Falló el aviso de orden terminada: orden_id=%s cliente_id=%s", orden_id, cliente_id)
