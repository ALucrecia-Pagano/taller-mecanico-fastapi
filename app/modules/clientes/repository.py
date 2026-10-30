"""Repositorios de clientes y vehículos con precarga declarada."""

from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.repository import BaseRepository, SoftDeleteRepository
from app.modules.clientes.models import Cliente, Vehiculo
from app.modules.ordenes.models import EstadoOrden, OrdenTrabajo


class ClienteRepository(BaseRepository[Cliente]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Cliente)

    async def add(self, cliente: Cliente) -> Cliente:
        return await super().add(cliente)

    async def get_by_id_with_vehiculos(self, cliente_id: int) -> Cliente | None:
        consulta = (
            select(Cliente)
            .options(selectinload(Cliente.vehiculos.and_(Vehiculo.borrado_en.is_(None))))
            .where(Cliente.id == cliente_id)
        )
        return (await self.session.exec(consulta)).first()

    async def get_by_usuario_id(self, usuario_id: int) -> Cliente | None:
        return (await self.session.exec(select(Cliente).where(Cliente.usuario_id == usuario_id))).first()


class VehiculoRepository(SoftDeleteRepository[Vehiculo]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Vehiculo)

    async def propios_vigentes(self, usuario_id: int) -> list[Vehiculo]:
        consulta = (
            select(Vehiculo)
            .join(Cliente, Cliente.id == Vehiculo.cliente_id)
            .where(Cliente.usuario_id == usuario_id, Vehiculo.borrado_en.is_(None))
            .order_by(Vehiculo.id)
        )
        return list((await self.session.exec(consulta)).all())

    async def tiene_orden_abierta(self, vehiculo_id: int) -> bool:
        consulta = (
            select(func.count())
            .select_from(OrdenTrabajo)
            .join(EstadoOrden, EstadoOrden.codigo == OrdenTrabajo.estado)
            .where(OrdenTrabajo.vehiculo_id == vehiculo_id, EstadoOrden.es_final.is_(False))
        )
        return (await self.session.exec(consulta)).one() > 0
