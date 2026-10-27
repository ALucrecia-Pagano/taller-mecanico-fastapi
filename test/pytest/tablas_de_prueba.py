"""Tablas de prueba de la suite: DDL escrito a mano, nunca create_all (OB-05, design D7)."""

from datetime import datetime

from sqlalchemy import DateTime, text
from sqlalchemy.orm import registry
from sqlmodel import Field, SQLModel

from app.core.database import crear_motor
from app.core.repository import BaseRepository, SoftDeleteRepository
from app.core.unit_of_work import UnitOfWork
from guarda import verificar_base_de_prueba

# Nombres de restricción fijos: los usa el mapa restricción -> mensaje de los tests de errores.
UQ_NOMBRE = "uq_prueba_articulo_nombre"
CK_CANTIDAD = "ck_prueba_articulo_cantidad"
FK_ARTICULO = "fk_prueba_baja_articulo_id"

BORRAR = "DROP TABLE IF EXISTS prueba_baja, prueba_articulo"
CREAR = (
    f"""
    CREATE TABLE prueba_articulo (
        id serial PRIMARY KEY,
        nombre text NOT NULL CONSTRAINT {UQ_NOMBRE} UNIQUE,
        cantidad integer NOT NULL DEFAULT 0 CONSTRAINT {CK_CANTIDAD} CHECK (cantidad >= 0),
        creado_en timestamptz NOT NULL DEFAULT now()
    )
    """,
    f"""
    CREATE TABLE prueba_baja (
        id serial PRIMARY KEY,
        nombre text NOT NULL,
        articulo_id integer NULL CONSTRAINT {FK_ARTICULO} REFERENCES prueba_articulo (id),
        borrado_en timestamptz NULL
    )
    """,
)


class BaseDePrueba(SQLModel, registry=registry()):
    """Registry propio: los modelos de prueba nunca entran en SQLModel.metadata (la que ve Alembic)."""


class ArticuloDePrueba(BaseDePrueba, table=True):
    __tablename__ = "prueba_articulo"

    id: int | None = Field(default=None, primary_key=True)
    # Opcional en el modelo para poder provocar el NOT NULL de la base (E4).
    nombre: str | None = None
    cantidad: int = 0
    creado_en: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": text("now()")},
    )


class BajaDePrueba(BaseDePrueba, table=True):
    __tablename__ = "prueba_baja"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str
    articulo_id: int | None = None
    borrado_en: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))


class RepositorioDeArticulos(BaseRepository[ArticuloDePrueba]):
    """Repositorio de entidad de prueba: métodos con nombre sobre el mismo stmt filtrado (2a)."""

    def __init__(self, session) -> None:
        super().__init__(session, ArticuloDePrueba)

    def _con_cantidad_mayor_a(self, minimo: int):
        return self._consulta().where(ArticuloDePrueba.cantidad > minimo)

    async def listar_con_cantidad_mayor_a(self, minimo: int, offset: int, limit: int) -> list[ArticuloDePrueba]:
        return await self._listar(self._con_cantidad_mayor_a(minimo), offset, limit)

    async def contar_con_cantidad_mayor_a(self, minimo: int) -> int:
        return await self._contar(self._con_cantidad_mayor_a(minimo))


MENSAJE_NOMBRE_REPETIDO = "Ese artículo ya está cargado"
MENSAJE_CANTIDAD_NEGATIVA = "La cantidad no puede ser negativa"
MENSAJE_ARTICULO_REFERENCIADO = "El artículo tiene registros que lo usan"


class UoWDePrueba(UnitOfWork):
    """UoW de módulo de prueba: sus repositorios comparten la sesión (4a)."""

    mensajes_de_restriccion = {
        UQ_NOMBRE: MENSAJE_NOMBRE_REPETIDO,
        CK_CANTIDAD: MENSAJE_CANTIDAD_NEGATIVA,
        FK_ARTICULO: MENSAJE_ARTICULO_REFERENCIADO,
    }

    def __init__(self, session) -> None:
        super().__init__(session)
        self.articulos = RepositorioDeArticulos(session)
        self.bajas = SoftDeleteRepository(session, BajaDePrueba)


async def _ejecutar(settings, sentencias) -> None:
    verificar_base_de_prueba(settings)  # antes de crear el motor: nunca se conecta a otra base
    engine = crear_motor(settings)
    try:
        async with engine.begin() as conexion:
            for sentencia in sentencias:
                await conexion.execute(text(sentencia))
    finally:
        await engine.dispose()


async def crear_tablas_de_prueba(settings) -> None:
    """Las crea desde cero; el DROP previo cubre una corrida interrumpida."""
    await _ejecutar(settings, (BORRAR, *CREAR))


async def borrar_tablas_de_prueba(settings) -> None:
    await _ejecutar(settings, (BORRAR,))
