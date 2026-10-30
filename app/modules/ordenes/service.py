"""Operaciones de órdenes: la transacción pertenece al UoW recibido."""

from decimal import Decimal
from datetime import UTC, datetime

from app.core.errores import Conflicto, NoEncontrado, PermisoDenegado
from app.core.paginacion import Pagina, armar_pagina, calcular_ventana

from app.modules.ordenes.models import CodigoEstado, HistorialEstadoOrden, ItemOrden, OrdenTrabajo
from app.modules.ordenes.schemas import EntradaOrden, EstadoRespuesta, HistorialRespuesta, ItemRespuesta, OrdenDetalle, OrdenResumen


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
