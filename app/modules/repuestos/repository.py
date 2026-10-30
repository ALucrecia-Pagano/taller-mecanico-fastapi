from datetime import datetime

from sqlalchemy import false, text
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.repository import SoftDeleteRepository
from app.core.errores import Conflicto
from app.modules.repuestos.models import HistorialPrecio, MovimientoStock, Repuesto


class RepuestoRepository(SoftDeleteRepository[Repuesto]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Repuesto)

    async def buscar(self, q: str | None, offset: int, limit: int) -> tuple[list[Repuesto], int]:
        consulta = self._consulta()
        if q is not None:
            consulta = consulta.where(false() if q == "" else Repuesto.descripcion.ilike(f"%{q}%"))
        total = await self._contar(consulta)
        filas = await self._listar(consulta, offset, limit)
        return filas, total

    async def ajustar_stock(
        self,
        repuesto_id: int,
        cantidad: int,
        usuario_id: int,
        motivo: str,
        orden_id: int | None = None,
        incluir_baja: bool = False,
    ) -> Repuesto:
        filtro_baja = "" if incluir_baja else " AND borrado_en IS NULL"
        disponibilidad = " AND stock + :cantidad >= 0" if cantidad < 0 else ""
        sentencia = text(
            f"UPDATE repuesto SET stock = stock + :cantidad "
            f"WHERE id = :id{filtro_baja}{disponibilidad} RETURNING id"
        ).bindparams(cantidad=cantidad, id=repuesto_id)
        fila = (await self.session.exec(sentencia)).first()
        if fila is None:
            if cantidad < 0:
                raise Conflicto("Stock insuficiente")
            raise LookupError("repuesto_no_encontrado")
        movimiento = MovimientoStock(
            repuesto_id=repuesto_id,
            orden_id=orden_id,
            usuario_id=usuario_id,
            cantidad=cantidad,
            motivo=motivo,
        )
        self.session.add(movimiento)
        await self.session.flush()
        repuesto = await self.get_by_id_including_deleted(repuesto_id)
        assert repuesto is not None
        await self.session.refresh(repuesto)
        return repuesto


class MovimientoStockRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def por_repuesto(self, repuesto_id: int) -> list[MovimientoStock]:
        consulta = (
            select(MovimientoStock)
            .where(MovimientoStock.repuesto_id == repuesto_id)
            .order_by(MovimientoStock.cuando, MovimientoStock.id)
        )
        return list((await self.session.exec(consulta)).all())


class HistorialPrecioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def por_repuesto(self, repuesto_id: int) -> list[HistorialPrecio]:
        consulta = (
            select(HistorialPrecio)
            .where(HistorialPrecio.repuesto_id == repuesto_id)
            .order_by(HistorialPrecio.cuando, HistorialPrecio.id)
        )
        return list((await self.session.exec(consulta)).all())

    async def add(self, historial: HistorialPrecio) -> HistorialPrecio:
        self.session.add(historial)
        await self.session.flush()
        return historial
