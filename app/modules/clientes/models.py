"""Tablas de clientes: cliente y vehiculo."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, DateTime, Index, text
from sqlmodel import Field, Relationship, SQLModel

import app.core.database  # noqa: F401  (pone la convención de nombres antes de declarar las tablas)

if TYPE_CHECKING:
    from app.modules.ordenes.models import OrdenTrabajo
    from app.modules.usuarios.models import Usuario


class Cliente(SQLModel, table=True):
    __tablename__ = "cliente"

    id: int | None = Field(default=None, primary_key=True)
    # El UNIQUE también es el índice de la FK (D4).
    usuario_id: int | None = Field(default=None, foreign_key="usuario.id", unique=True)
    nombre: str
    documento: str = Field(unique=True)
    telefono: str

    usuario: Optional["Usuario"] = Relationship(back_populates="cliente", sa_relationship_kwargs={"lazy": "raise"})
    vehiculos: list["Vehiculo"] = Relationship(back_populates="cliente", sa_relationship_kwargs={"lazy": "raise"})


class Vehiculo(SQLModel, table=True):
    __tablename__ = "vehiculo"
    __table_args__ = (
        CheckConstraint("anio BETWEEN 1950 AND 2100", name="anio"),
        # Única sólo entre los vigentes: el comprador de un auto dado de baja puede registrarlo (DD-03).
        Index("uq_vehiculo_patente_vigente", "patente", unique=True, postgresql_where=text("borrado_en IS NULL")),
    )

    id: int | None = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="cliente.id", index=True)
    patente: str
    marca: str
    modelo: str
    anio: int
    borrado_en: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))

    cliente: Cliente = Relationship(back_populates="vehiculos", sa_relationship_kwargs={"lazy": "raise"})
    ordenes: list["OrdenTrabajo"] = Relationship(back_populates="vehiculo", sa_relationship_kwargs={"lazy": "raise"})
