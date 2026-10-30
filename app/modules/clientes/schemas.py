"""Contratos HTTP del módulo de clientes."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EntradaCliente(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str
    documento: str
    telefono: str

    @field_validator("documento")
    @classmethod
    def recortar_documento(cls, valor: str) -> str:
        return valor.strip()


class EntradaVehiculo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patente: str
    marca: str
    modelo: str
    anio: int = Field(ge=1950, le=2100)

    @field_validator("patente")
    @classmethod
    def normalizar_patente(cls, valor: str) -> str:
        return "".join(valor.split()).upper()


class VehiculoRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int
    patente: str
    marca: str
    modelo: str
    anio: int


class ClienteRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int | None
    nombre: str
    documento: str
    telefono: str
    vehiculos: list[VehiculoRespuesta] = Field(default_factory=list)
