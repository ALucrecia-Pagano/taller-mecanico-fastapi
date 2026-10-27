"""El envoltorio de los listados y el cálculo de las páginas (sección 2.9 de la consigna)."""

from collections.abc import Sequence
from math import ceil
from typing import Annotated, NamedTuple

from fastapi import Query
from pydantic import BaseModel

from app.core.errores import PaginaInexistente


class ParametrosDePagina(NamedTuple):
    page: int
    size: int


async def parametros_de_pagina(
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ParametrosDePagina:
    """page desde 1; size de 1 a 100, por defecto 20. Fuera de rango: 422 por contrato."""
    return ParametrosDePagina(page, size)


class Ventana(NamedTuple):
    """Qué filas abarca una página; valor interno, no es un contrato de la API."""

    offset: int
    limit: int
    pages: int


def calcular_ventana(total: int, page: int, size: int) -> Ventana:
    pages = max(1, ceil(total / size))  # con cero resultados hay una página, vacía
    if page > pages:
        raise PaginaInexistente(f"La página {page} no existe: hay {pages}")
    return Ventana(offset=(page - 1) * size, limit=size, pages=pages)


class Pagina[T](BaseModel):
    """Envoltorio de todo listado: se usa como response_model=Pagina[XRespuesta]."""

    items: list[T]
    total: int
    page: int
    size: int
    pages: int


def armar_pagina[T](items: Sequence[T], total: int, page: int, size: int, ventana: Ventana) -> Pagina[T]:
    return Pagina[T](items=list(items), total=total, page=page, size=size, pages=ventana.pages)
