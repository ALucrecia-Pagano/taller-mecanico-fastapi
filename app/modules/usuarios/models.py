"""Tablas de usuarios: usuario, asignacion_rol, intento_acceso y evento_seguridad."""

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, DateTime, Index, text
from sqlmodel import AutoString, Field, Relationship, SQLModel

import app.core.database  # noqa: F401  (pone la convención de nombres antes de declarar las tablas)

if TYPE_CHECKING:
    from app.modules.clientes.models import Cliente
    from app.modules.ordenes.models import OrdenTrabajo


class Rol(StrEnum):
    ADMIN = "ADMIN"
    RECEPCION = "RECEPCION"
    MECANICO = "MECANICO"
    CLIENTE = "CLIENTE"


class Usuario(SQLModel, table=True):
    __tablename__ = "usuario"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True)
    nombre: str
    password_hash: str
    activo: bool = True
    debe_cambiar_password: bool = False
    password_cambiada_en: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))

    roles: list["AsignacionRol"] = Relationship(
        back_populates="usuario",
        sa_relationship_kwargs={"lazy": "raise", "foreign_keys": "[AsignacionRol.usuario_id]"},
    )
    cliente: Optional["Cliente"] = Relationship(
        back_populates="usuario", sa_relationship_kwargs={"lazy": "raise", "uselist": False}
    )
    ordenes_asignadas: list["OrdenTrabajo"] = Relationship(
        back_populates="mecanico",
        sa_relationship_kwargs={"lazy": "raise", "foreign_keys": "[OrdenTrabajo.mecanico_id]"},
    )


class AsignacionRol(SQLModel, table=True):
    __tablename__ = "asignacion_rol"
    __table_args__ = (
        # La lista sale del enum: el CHECK y el contrato de la API no pueden separarse.
        CheckConstraint(f"rol IN ({', '.join(repr(r.value) for r in Rol)})", name="rol"),
        # Una sola asignación abierta por rol (RN-03); las revocadas no cuentan.
        Index(
            "uq_asignacion_rol_abierta",
            "usuario_id",
            "rol",
            unique=True,
            postgresql_where=text("revocada_en IS NULL"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    # Texto con CHECK, no un ENUM nativo: el PDF pide un CHECK, y el tipo nativo rompe el downgrade.
    rol: Rol = Field(sa_type=AutoString)
    desde: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        nullable=False,
        sa_column_kwargs={"server_default": text("now()")},
    )
    vence_en: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    revocada_en: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    # El ADMIN que la otorgó; NULL si la asignó el auto-registro o el seed (DA-08).
    otorgada_por: int | None = Field(default=None, foreign_key="usuario.id", index=True)

    usuario: Usuario = Relationship(
        back_populates="roles",
        sa_relationship_kwargs={"lazy": "raise", "foreign_keys": "[AsignacionRol.usuario_id]"},
    )


class IntentoAcceso(SQLModel, table=True):
    __tablename__ = "intento_acceso"
    __table_args__ = (Index(None, "email", "ip", "cuando"),)

    id: int | None = Field(default=None, primary_key=True)
    cuando: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        nullable=False,
        sa_column_kwargs={"server_default": text("now()")},
    )
    email: str
    ip: str
    exito: bool


class EventoSeguridad(SQLModel, table=True):
    __tablename__ = "evento_seguridad"

    id: int | None = Field(default=None, primary_key=True)
    cuando: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        nullable=False,
        sa_column_kwargs={"server_default": text("now()")},
    )
    # Texto, no FK: los datos iniciales usan «SISTEMA».
    actor: str
    accion: str
