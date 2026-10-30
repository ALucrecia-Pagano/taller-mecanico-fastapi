from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EntradaRepuesto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: str
    descripcion: str
    precio: Decimal = Field(gt=0)
    stock_inicial: int = Field(ge=0)


class EntradaRepuestoPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    descripcion: str | None = None
    precio: Decimal | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def no_vacio(self):
        if self.descripcion is None and self.precio is None:
            raise ValueError("Debe enviar al menos un campo modificable")
        return self


class EntradaReponer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cantidad: int = Field(gt=0)


class RepuestoRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    descripcion: str
    precio: Decimal
    stock: int


class MovimientoRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repuesto_id: int
    orden_id: int | None
    usuario_id: int
    cantidad: int
    motivo: str
    cuando: datetime


class PrecioRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repuesto_id: int
    usuario_id: int
    precio_anterior: Decimal
    precio_nuevo: Decimal
    cuando: datetime
