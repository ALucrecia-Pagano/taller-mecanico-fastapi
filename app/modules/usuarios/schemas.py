"""Contratos de /auth separados de los modelos de tabla (DA-16)."""

from datetime import UTC, datetime
from typing import Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, field_validator, model_validator

from app.core.security import Contrasena


class EntradaAuth(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Mensaje(BaseModel):
    mensaje: str


class SesionIniciada(Mensaje):
    debe_cambiar_password: bool
    expira_en_segundos: int


class Perfil(BaseModel):
    id: int
    email: str
    nombre: str
    debe_cambiar_password: bool
    roles_vigentes: list[str]
    roles_token: list[str]


class Registro(EntradaAuth):
    email: str
    nombre: str
    password: Contrasena
    documento: str
    telefono: str


class Login(EntradaAuth):
    email: str
    password: Contrasena


class CambioPassword(EntradaAuth):
    password_actual: Contrasena
    password_nueva: Contrasena

    @model_validator(mode="after")
    def nueva_distinta(self) -> Self:
        # [Alumna] D7 — No especificado en la consigna. No usar bcrypt para comparar el contrato.
        if self.password_nueva == self.password_actual:
            raise ValueError("La contraseña nueva debe ser distinta de la actual")
        return self


# [Alumna] D1=B: CLIENTE sólo por auto-registro, también se excluye en asignación.
RolPersonal = Literal["ADMIN", "RECEPCION", "MECANICO"]


class AltaPersonal(EntradaAuth):
    email: str
    nombre: str
    password_provisoria: Contrasena
    rol: RolPersonal


class PersonalRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    nombre: str
    activo: bool
    debe_cambiar_password: bool


class AsignarRol(EntradaAuth):
    rol: RolPersonal
    vence_en: AwareDatetime | None = None

    @field_validator("vence_en")
    @classmethod
    def vencimiento_futuro(cls, valor: datetime | None) -> datetime | None:
        if valor is not None and valor <= datetime.now(UTC):
            raise ValueError("vence_en debe estar en el futuro")
        return valor


class AsignacionRespuesta(BaseModel):
    id: int
    usuario_id: int
    rol: str
    desde: datetime
    vence_en: datetime | None
    revocada_en: datetime | None
    otorgada_por: int | None
    vigente: bool

    @classmethod
    def de_asignacion(cls, asignacion, ahora: datetime):
        # Proyección explícita: AutoString devuelve str al leer; no serializar el modelo de tabla.
        return cls(id=asignacion.id, usuario_id=asignacion.usuario_id, rol=asignacion.rol,
                   desde=asignacion.desde, vence_en=asignacion.vence_en,
                   revocada_en=asignacion.revocada_en, otorgada_por=asignacion.otorgada_por,
                   vigente=asignacion.revocada_en is None and
                   (asignacion.vence_en is None or asignacion.vence_en > ahora))


class EventoRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    cuando: datetime
    actor: str
    accion: str
