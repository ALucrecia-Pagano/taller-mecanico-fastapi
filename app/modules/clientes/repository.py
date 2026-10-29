"""Alta mínima requerida por el auto-registro; CH-07 amplía este repositorio."""

from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.clientes.models import Cliente


class ClienteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, cliente: Cliente) -> Cliente:
        self.session.add(cliente)
        await self.session.flush()
        return cliente
