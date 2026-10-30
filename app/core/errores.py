"""Errores de dominio: los lanzan servicios, UoW y paginación; el router los traduce a HTTP.

No especificado en la consigna (archivo propio del core, decisión de la alumna). No importa nada de HTTP.
"""

import logging
from collections.abc import Mapping

from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

# Para restricciones sin mensaje en el UoW del módulo (No especificado en la consigna).
MENSAJE_GENERICO = "La operación choca con datos existentes"
SQLSTATE_NOT_NULL = "23502"


class ErrorDeDominio(Exception):
    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


class NoEncontrado(ErrorDeDominio):
    """El recurso de la ruta no existe."""


class PaginaInexistente(ErrorDeDominio):
    """Se pidió una página más allá de la última."""


class EntradaInvalida(ErrorDeDominio):
    """La operación no cumple una regla de validación del dominio."""


class Conflicto(ErrorDeDominio):
    """La operación choca con lo guardado (RN-01, DD-04)."""


class PermisoDenegado(ErrorDeDominio):
    """La sesión es válida pero la operación no está autorizada."""


class TokenInvalido(ErrorDeDominio):
    """El token no sirve: mal formado, con otra firma u otro algoritmo, vencido o sin sus claims."""


class LimiteDeIntentos(ErrorDeDominio):
    def __init__(self, mensaje: str = "Demasiados intentos", segundos: int = 1) -> None:
        super().__init__(mensaje)
        self.segundos = segundos


def _datos_de_la_restriccion(error: IntegrityError) -> tuple[str | None, str | None]:
    # Con asyncpg: error.orig es el adaptador de SQLAlchemy (lleva sqlstate) y su __cause__
    # es la excepción de asyncpg, que lleva el nombre de la restricción (V1, design).
    original = error.orig
    nombre = getattr(original.__cause__, "constraint_name", None)
    return nombre, getattr(original, "sqlstate", None)


def traducir_integrity_error(error: IntegrityError, mensajes: Mapping[str, str]) -> Conflicto:
    """Mensaje propio del módulo para la restricción violada; nunca el texto de la base (RN-18)."""
    nombre, sqlstate = _datos_de_la_restriccion(error)
    # El detalle queda en el log del servidor; al cliente sólo le llega el mensaje propio.
    # Un NOT NULL es un bug que el contrato debía impedir: se registra como error.
    nivel = logging.ERROR if sqlstate == SQLSTATE_NOT_NULL else logging.WARNING
    logger.log(nivel, "Restricción violada: %s (SQLSTATE %s)", nombre, sqlstate)
    return Conflicto(mensajes.get(nombre, MENSAJE_GENERICO))
