"""Contratos de /auth separados de los modelos de tabla (DA-16)."""

from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

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
