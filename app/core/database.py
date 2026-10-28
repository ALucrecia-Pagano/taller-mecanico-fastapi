"""Motor y fábrica de sesiones (los crea el lifespan) y la sesión por petición."""

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import Settings

# Nombres de restricción fijos: los mapas restricción -> mensaje de cada UoW dependen de ellos.
# SQLAlchemy la aplica al declarar cada tabla, así que todo models.py importa este módulo primero.
CONVENCION_DE_NOMBRES = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
}
SQLModel.metadata.naming_convention = CONVENCION_DE_NOMBRES


def crear_motor(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        echo=settings.sql_echo,
    )


def crear_fabrica_de_sesiones(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Una sesión por petición, tomada de la fábrica de app.state; se cierra al terminar. No confirma."""
    async with request.app.state.session_factory() as session:
        yield session
