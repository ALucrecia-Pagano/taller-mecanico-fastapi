"""Contratos de órdenes, separados de los modelos de tabla."""

from decimal import Decimal
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, model_validator

Dinero = Annotated[Decimal, PlainSerializer(lambda valor: format(valor, ".2f"), return_type=str, when_used="json")]


class ItemRespuesta(BaseModel):
    repuesto_id: int
    codigo: str
    descripcion: str
    cantidad: int
    precio_unitario: Dinero
    subtotal: Dinero


class EstadoRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    codigo: str
    descripcion: str
    posicion: int
    es_final: bool


class HistorialRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    desde_estado: str | None
    hasta_estado: str
    usuario_id: int
    cuando: datetime


class OrdenResumen(BaseModel):
    id: int
    estado: str
    patente: str
    total: Dinero
    creada_en: datetime
    mecanico_id: int | None
    falla: str
    cliente: str


class OrdenDetalle(OrdenResumen):
    items: list[ItemRespuesta]
    historial: list[HistorialRespuesta]


class EntradaItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    repuesto_id: int
    # Límite físico INTEGER, no un máximo de negocio [Agente, No especificado en la consigna].
    cantidad: int = Field(gt=0, le=2147483647)


class EntradaOrden(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vehiculo_id: int
    falla: str
    items: list[EntradaItem] = Field(min_length=1)

    @model_validator(mode="after")
    def repuestos_distintos(self):
        ids = [item.repuesto_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("No se permiten repuestos repetidos")
        return self
