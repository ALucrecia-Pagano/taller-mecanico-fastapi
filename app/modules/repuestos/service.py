from app.core.errores import EntradaInvalida, NoEncontrado
from app.core.paginacion import armar_pagina, calcular_ventana
from app.modules.repuestos.models import HistorialPrecio, Repuesto
from app.modules.repuestos.schemas import (
    EntradaReponer,
    EntradaRepuesto,
    EntradaRepuestoPatch,
    MovimientoRespuesta,
    PrecioRespuesta,
    RepuestoRespuesta,
)


class RepuestosService:
    def __init__(self, uow) -> None:
        self.uow = uow

    async def listar(self, q: str | None, page: int, size: int):
        async with self.uow:
            filas, total = await self.uow.repuestos.buscar(q, (page - 1) * size, size)
            ventana = calcular_ventana(total, page, size)
            return armar_pagina([RepuestoRespuesta.model_validate(fila) for fila in filas], total, page, size, ventana)

    async def obtener(self, repuesto_id: int) -> RepuestoRespuesta:
        async with self.uow:
            repuesto = await self.uow.repuestos.get_by_id(repuesto_id)
            if repuesto is None:
                raise NoEncontrado("Repuesto no encontrado")
            return RepuestoRespuesta.model_validate(repuesto)

    async def crear(self, datos: EntradaRepuesto, usuario_id: int) -> RepuestoRespuesta:
        async with self.uow:
            repuesto = await self.uow.repuestos.add(
                Repuesto(codigo=datos.codigo, descripcion=datos.descripcion, precio=datos.precio, stock=0)
            )
            if datos.stock_inicial:
                await self.uow.repuestos.ajustar_stock(
                    repuesto.id, datos.stock_inicial, usuario_id, "Stock inicial"
                )
            return RepuestoRespuesta.model_validate(repuesto)

    async def reponer(self, repuesto_id: int, datos: EntradaReponer, usuario_id: int) -> RepuestoRespuesta:
        async with self.uow:
            try:
                repuesto = await self.uow.repuestos.ajustar_stock(
                    repuesto_id, datos.cantidad, usuario_id, "Reposición"
                )
            except LookupError:
                raise NoEncontrado("Repuesto no encontrado") from None
            return RepuestoRespuesta.model_validate(repuesto)

    async def actualizar(self, repuesto_id: int, datos: EntradaRepuestoPatch, usuario_id: int) -> RepuestoRespuesta:
        async with self.uow:
            repuesto = await self.uow.repuestos.get_by_id(repuesto_id)
            if repuesto is None:
                raise NoEncontrado("Repuesto no encontrado")
            cambios = datos.model_dump(exclude_unset=True)
            if "precio" in cambios:
                if cambios["precio"] == repuesto.precio:
                    raise EntradaInvalida("El precio nuevo debe ser distinto del actual")
                anterior = repuesto.precio
                repuesto.precio = cambios["precio"]
                await self.uow.precios.add(
                    HistorialPrecio(
                        repuesto_id=repuesto.id,
                        usuario_id=usuario_id,
                        precio_anterior=anterior,
                        precio_nuevo=repuesto.precio,
                    )
                )
            if "descripcion" in cambios:
                repuesto.descripcion = cambios["descripcion"]
            await self.uow.session.flush()
            return RepuestoRespuesta.model_validate(repuesto)

    async def borrar(self, repuesto_id: int) -> None:
        async with self.uow:
            repuesto = await self.uow.repuestos.get_by_id(repuesto_id)
            if repuesto is None:
                raise NoEncontrado("Repuesto no encontrado")
            await self.uow.repuestos.soft_delete(repuesto)

    async def movimientos(self, repuesto_id: int) -> list[MovimientoRespuesta]:
        async with self.uow:
            if await self.uow.repuestos.get_by_id(repuesto_id) is None:
                raise NoEncontrado("Repuesto no encontrado")
            filas = await self.uow.movimientos.por_repuesto(repuesto_id)
            return [MovimientoRespuesta.model_validate(fila) for fila in filas]

    async def precios(self, repuesto_id: int) -> list[PrecioRespuesta]:
        async with self.uow:
            if await self.uow.repuestos.get_by_id(repuesto_id) is None:
                raise NoEncontrado("Repuesto no encontrado")
            filas = await self.uow.precios.por_repuesto(repuesto_id)
            return [PrecioRespuesta.model_validate(fila) for fila in filas]
