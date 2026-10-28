"""Tablas de repuestos: repuesto, movimiento_stock e historial_precio_repuesto.

movimiento_stock e historial_precio_repuesto son de sólo agregado: el disparador de la
migración 0002 rechaza todo UPDATE y DELETE sobre ellas (RN-15).
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Index, text
from sqlmodel import Field, Relationship, SQLModel

import app.core.database  # noqa: F401  (pone la convención de nombres antes de declarar las tablas)

if TYPE_CHECKING:
    from app.modules.ordenes.models import ItemOrden


class Repuesto(SQLModel, table=True):
    __tablename__ = "repuesto"
    __table_args__ = (
        CheckConstraint("precio > 0", name="precio_positivo"),
        CheckConstraint("stock >= 0", name="stock_no_negativo"),
        # Único sólo entre los vigentes (DD-03).
        Index("uq_repuesto_codigo_vigente", "codigo", unique=True, postgresql_where=text("borrado_en IS NULL")),
    )

    id: int | None = Field(default=None, primary_key=True)
    codigo: str
    descripcion: str
    precio: Decimal = Field(max_digits=10, decimal_places=2)
    # Sólo cambia a través de movimientos (RN-14).
    stock: int
    borrado_en: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))

    items: list["ItemOrden"] = Relationship(back_populates="repuesto", sa_relationship_kwargs={"lazy": "raise"})
    movimientos: list["MovimientoStock"] = Relationship(
        back_populates="repuesto", sa_relationship_kwargs={"lazy": "raise"}
    )
    historial_precios: list["HistorialPrecio"] = Relationship(
        back_populates="repuesto", sa_relationship_kwargs={"lazy": "raise"}
    )


class MovimientoStock(SQLModel, table=True):
    __tablename__ = "movimiento_stock"
    # Entradas positivas, salidas por terminar una orden negativas (DD-13).
    __table_args__ = (CheckConstraint("cantidad <> 0", name="cantidad_distinta_de_cero"),)

    id: int | None = Field(default=None, primary_key=True)
    repuesto_id: int = Field(foreign_key="repuesto.id", index=True)
    orden_id: int | None = Field(default=None, foreign_key="orden_trabajo.id", index=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    cantidad: int
    motivo: str
    cuando: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        nullable=False,
        sa_column_kwargs={"server_default": text("now()")},
    )

    repuesto: Repuesto = Relationship(back_populates="movimientos", sa_relationship_kwargs={"lazy": "raise"})


class HistorialPrecio(SQLModel, table=True):
    __tablename__ = "historial_precio_repuesto"
    __table_args__ = (
        CheckConstraint("precio_nuevo > 0", name="precio_nuevo_positivo"),
        # El precio puede bajar; sólo tiene que cambiar (RN-20).
        CheckConstraint("precio_nuevo <> precio_anterior", name="precio_cambia"),
    )

    id: int | None = Field(default=None, primary_key=True)
    repuesto_id: int = Field(foreign_key="repuesto.id", index=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    precio_anterior: Decimal = Field(max_digits=10, decimal_places=2)
    precio_nuevo: Decimal = Field(max_digits=10, decimal_places=2)
    cuando: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        nullable=False,
        sa_column_kwargs={"server_default": text("now()")},
    )

    repuesto: Repuesto = Relationship(back_populates="historial_precios", sa_relationship_kwargs={"lazy": "raise"})
