"""Traducción de IntegrityError a errores de dominio (spec errores-de-dominio, E1-E6)."""

import logging

import pytest

from app.core import errores
from app.core.errores import ErrorDeDominio
from tablas_de_prueba import (
    MENSAJE_ARTICULO_REFERENCIADO,
    MENSAJE_CANTIDAD_NEGATIVA,
    MENSAJE_NOMBRE_REPETIDO,
    UQ_NOMBRE,
    ArticuloDePrueba,
    BajaDePrueba,
    UoWDePrueba,
)

# Nada de esto puede llegar al cliente: entregaría el mapa del esquema (RN-18).
TEXTO_INTERNO = (UQ_NOMBRE, "prueba_articulo", "nombre", "duplicate", "violates", "unique")


async def guardar(fabrica, *articulos: ArticuloDePrueba, uow_clase=UoWDePrueba) -> None:
    async with fabrica() as sesion:
        uow = uow_clase(sesion)
        async with uow:
            for articulo in articulos:
                await uow.articulos.add(articulo)


def sin_texto_interno(mensaje: str) -> bool:
    return not any(fragmento in mensaje.lower() for fragmento in TEXTO_INTERNO)


async def test_e1_unique_mapeado(tablas_limpias):
    await guardar(tablas_limpias, ArticuloDePrueba(nombre="Filtro"))

    with pytest.raises(ErrorDeDominio) as error:
        await guardar(tablas_limpias, ArticuloDePrueba(nombre="Filtro"))

    assert isinstance(error.value, errores.Conflicto)
    assert error.value.mensaje == MENSAJE_NOMBRE_REPETIDO
    assert sin_texto_interno(error.value.mensaje)


async def test_e2_check_mapeado(tablas_limpias):
    with pytest.raises(errores.Conflicto) as error:
        await guardar(tablas_limpias, ArticuloDePrueba(nombre="Filtro", cantidad=-1))

    assert error.value.mensaje == MENSAJE_CANTIDAD_NEGATIVA
    assert error.value.mensaje != MENSAJE_NOMBRE_REPETIDO


class UoWSinMapa(UoWDePrueba):
    mensajes_de_restriccion = {}


async def test_e3_restriccion_sin_mapear(tablas_limpias):
    await guardar(tablas_limpias, ArticuloDePrueba(nombre="Filtro"))

    with pytest.raises(errores.Conflicto) as error:
        await guardar(tablas_limpias, ArticuloDePrueba(nombre="Filtro"), uow_clase=UoWSinMapa)

    assert error.value.mensaje == errores.MENSAJE_GENERICO
    assert sin_texto_interno(error.value.mensaje)


LOGGER = "app.core.errores"


async def test_e4_not_null(tablas_limpias, caplog):
    caplog.set_level(logging.WARNING, logger=LOGGER)

    with pytest.raises(errores.Conflicto) as error:
        await guardar(tablas_limpias, ArticuloDePrueba(nombre=None))

    assert error.value.mensaje == errores.MENSAJE_GENERICO
    assert [r.levelno for r in caplog.records if r.name == LOGGER] == [logging.ERROR]


async def test_e5_log_con_el_detalle_mensaje_sin_el_detalle(tablas_limpias, caplog):
    caplog.set_level(logging.WARNING, logger=LOGGER)
    await guardar(tablas_limpias, ArticuloDePrueba(nombre="Filtro"))

    with pytest.raises(errores.Conflicto) as error:
        await guardar(tablas_limpias, ArticuloDePrueba(nombre="Filtro"))

    registro = next(r for r in caplog.records if r.name == LOGGER)
    assert registro.levelno == logging.WARNING
    assert UQ_NOMBRE in registro.getMessage()
    assert "23505" in registro.getMessage()
    assert UQ_NOMBRE not in error.value.mensaje
    assert "23505" not in error.value.mensaje


async def test_e6_fk_mapeada_al_borrar_un_referenciado(tablas_limpias):
    async with tablas_limpias() as sesion:
        async with UoWDePrueba(sesion) as uow:
            articulo = await uow.articulos.add(ArticuloDePrueba(nombre="Filtro"))
            await uow.bajas.add(BajaDePrueba(nombre="AB123CD", articulo_id=articulo.id))

    async with tablas_limpias() as sesion:
        with pytest.raises(errores.Conflicto) as error:
            async with UoWDePrueba(sesion) as uow:
                await uow.articulos.delete(await uow.articulos.get_by_id(1))

    assert error.value.mensaje == MENSAJE_ARTICULO_REFERENCIADO
    async with tablas_limpias() as sesion:
        assert await UoWDePrueba(sesion).articulos.get_by_id(1) is not None
