"""Lecturas explícitas y escrituras sin commit del módulo de órdenes."""

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.repository import BaseRepository
from app.modules.clientes.models import Cliente, Vehiculo
from app.modules.repuestos.models import Repuesto
from app.modules.ordenes.models import EstadoOrden, HistorialEstadoOrden, ItemOrden, OrdenTrabajo


class EstadoOrdenRepository:
    """Catálogo sólo lectura, sin heredar operaciones de escritura."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def listar(self) -> list[EstadoOrden]:
        return list((await self.session.exec(select(EstadoOrden).order_by(EstadoOrden.posicion))).all())


class OrdenTrabajoRepository(BaseRepository[OrdenTrabajo]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, OrdenTrabajo)

    async def detalle(self, orden_id: int) -> OrdenTrabajo | None:
        consulta = select(OrdenTrabajo).where(OrdenTrabajo.id == orden_id).options(
            joinedload(OrdenTrabajo.vehiculo).joinedload(Vehiculo.cliente),
            selectinload(OrdenTrabajo.items).joinedload(ItemOrden.repuesto),
            selectinload(OrdenTrabajo.historial),
        )
        return (await self.session.exec(consulta)).first()

    async def repuestos_vigentes(self, ids: list[int]) -> list[Repuesto]:
        consulta = select(Repuesto).where(Repuesto.id.in_(ids), Repuesto.borrado_en.is_(None))
        return list((await self.session.exec(consulta)).all())

    def _filtrada(self, estado: str | None, usuario_id: int | None):
        consulta = select(OrdenTrabajo)
        if estado is not None:
            consulta = consulta.where(OrdenTrabajo.estado == estado)
        if usuario_id is not None:
            consulta = consulta.join(Vehiculo, Vehiculo.id == OrdenTrabajo.vehiculo_id).join(
                Cliente, Cliente.id == Vehiculo.cliente_id).where(Cliente.usuario_id == usuario_id)
        return consulta

    async def contar_filtradas(self, estado: str | None, usuario_id: int | None) -> int:
        return await self._contar(self._filtrada(estado, usuario_id))

    async def listar(self, estado: str | None, usuario_id: int | None, offset: int, limit: int) -> list[OrdenTrabajo]:
        consulta = self._filtrada(estado, usuario_id).options(joinedload(OrdenTrabajo.vehiculo).joinedload(Vehiculo.cliente))
        return await self._listar(consulta, offset, limit)


class ItemOrdenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, item: ItemOrden) -> None:
        self.session.add(item)
        await self.session.flush()


class HistorialEstadoRepository:
    """Únicamente agregado dentro de la operación de negocio, nunca CRUD."""
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, historial: HistorialEstadoOrden) -> None:
        self.session.add(historial)
        await self.session.flush()
