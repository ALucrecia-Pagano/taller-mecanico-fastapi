"""Tablas de órdenes: estado_orden (catálogo), orden_trabajo, item_orden e historial_estado_orden.

historial_estado_orden es de sólo agregado: el disparador de la migración 0002 rechaza todo
UPDATE y DELETE sobre ella (RN-15).
"""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, DateTime, text
from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

import app.core.database  # noqa: F401  (pone la convención de nombres antes de declarar las tablas)

if TYPE_CHECKING:
    from app.modules.clientes.models import Vehiculo
    from app.modules.repuestos.models import Repuesto
    from app.modules.usuarios.models import Usuario


class CodigoEstado(StrEnum):
    """Espejo del catálogo estado_orden: el contrato de la API y el vocabulario del servicio.

    Tiene que coincidir con las filas que carga seed.py; agregar un estado obliga a tocar los dos.
    """

    PENDIENTE = "PENDIENTE"
    EN_REPARACION = "EN_REPARACION"
    TERMINADA = "TERMINADA"
    CANCELADA = "CANCELADA"


class EstadoOrden(SQLModel, table=True):
    """Catálogo de sólo lectura: la migración lo crea vacío y lo carga seed.py."""

    __tablename__ = "estado_orden"

    # El código es la PK para que orden_trabajo.estado se lea igual en psql que en la API.
    codigo: str = Field(primary_key=True)
    descripcion: str
    posicion: int = Field(unique=True)
    es_final: bool

    ordenes: list["OrdenTrabajo"] = Relationship(
        back_populates="estado_orden", sa_relationship_kwargs={"lazy": "raise"}
    )


class OrdenTrabajo(SQLModel, table=True):
    __tablename__ = "orden_trabajo"
    __table_args__ = (CheckConstraint("total >= 0", name="total_no_negativo"),)

    id: int | None = Field(default=None, primary_key=True)
    vehiculo_id: int = Field(foreign_key="vehiculo.id", index=True)
    mecanico_id: int | None = Field(default=None, foreign_key="usuario.id", index=True)
    # Clave foránea al catálogo, no un CHECK con la lista (RN-19).
    estado: str = Field(foreign_key="estado_orden.codigo", index=True)
    falla: str
    creada_en: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        nullable=False,
        sa_column_kwargs={"server_default": text("now()")},
    )
    total: Decimal = Field(max_digits=12, decimal_places=2)

    vehiculo: "Vehiculo" = Relationship(back_populates="ordenes", sa_relationship_kwargs={"lazy": "raise"})
    mecanico: Optional["Usuario"] = Relationship(
        back_populates="ordenes_asignadas",
        sa_relationship_kwargs={"lazy": "raise", "foreign_keys": "[OrdenTrabajo.mecanico_id]"},
    )
    # `estado` ya es la columna.
    estado_orden: EstadoOrden = Relationship(back_populates="ordenes", sa_relationship_kwargs={"lazy": "raise"})
    items: list["ItemOrden"] = Relationship(back_populates="orden", sa_relationship_kwargs={"lazy": "raise"})
    historial: list["HistorialEstadoOrden"] = Relationship(
        back_populates="orden", sa_relationship_kwargs={"lazy": "raise"}
    )


class ItemOrden(SQLModel, table=True):
    __tablename__ = "item_orden"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="cantidad_positiva"),
        CheckConstraint("precio_unitario > 0", name="precio_unitario_positivo"),
        # También es el índice de la FK orden_id (D4).
        UniqueConstraint("orden_id", "repuesto_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    orden_id: int = Field(foreign_key="orden_trabajo.id")
    repuesto_id: int = Field(foreign_key="repuesto.id", index=True)
    cantidad: int
    precio_unitario: Decimal = Field(max_digits=10, decimal_places=2)

    orden: OrdenTrabajo = Relationship(back_populates="items", sa_relationship_kwargs={"lazy": "raise"})
    repuesto: "Repuesto" = Relationship(back_populates="items", sa_relationship_kwargs={"lazy": "raise"})


class HistorialEstadoOrden(SQLModel, table=True):
    __tablename__ = "historial_estado_orden"

    id: int | None = Field(default=None, primary_key=True)
    orden_id: int = Field(foreign_key="orden_trabajo.id", index=True)
    desde_estado: str | None = Field(default=None, foreign_key="estado_orden.codigo", index=True)
    hasta_estado: str = Field(foreign_key="estado_orden.codigo", index=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    cuando: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        nullable=False,
        sa_column_kwargs={"server_default": text("now()")},
    )

    orden: OrdenTrabajo = Relationship(back_populates="historial", sa_relationship_kwargs={"lazy": "raise"})
