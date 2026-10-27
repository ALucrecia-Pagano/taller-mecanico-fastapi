"""Unit of Work (spec unidad-de-trabajo, U1-U10), sobre las tablas prueba_*."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlmodel import func, select

from app.core.errores import Conflicto, ErrorDeDominio
from app.core.repository import BaseRepository
from app.core.unit_of_work import UnitOfWork
from tablas_de_prueba import MENSAJE_NOMBRE_REPETIDO, ArticuloDePrueba, BajaDePrueba, UoWDePrueba


async def articulos_en_la_base(fabrica) -> int:
    async with fabrica() as otra:
        return (await otra.exec(select(func.count()).select_from(ArticuloDePrueba))).one()


async def test_u1_bloque_exitoso(tablas_limpias):
    async with tablas_limpias() as sesion:
        uow = UnitOfWork(sesion)
        async with uow:
            await BaseRepository(sesion, ArticuloDePrueba).add(ArticuloDePrueba(nombre="Filtro"))

    assert await articulos_en_la_base(tablas_limpias) == 1


async def test_u3_excepcion_de_dominio_despues_de_escribir(tablas_limpias):
    async with tablas_limpias() as sesion:
        uow = UnitOfWork(sesion)
        with pytest.raises(ErrorDeDominio, match="regla de negocio"):
            async with uow:
                await BaseRepository(sesion, ArticuloDePrueba).add(ArticuloDePrueba(nombre="Filtro"))
                raise ErrorDeDominio("La regla de negocio no se cumple")  # como haría un servicio

    assert await articulos_en_la_base(tablas_limpias) == 0


async def test_u2_error_de_la_base(tablas_limpias):
    async with tablas_limpias() as sesion:
        with pytest.raises(ProgrammingError):
            async with UnitOfWork(sesion):
                await BaseRepository(sesion, ArticuloDePrueba).add(ArticuloDePrueba(nombre="Filtro"))
                await sesion.exec(text("SELECT * FROM tabla_que_no_existe"))

    assert await articulos_en_la_base(tablas_limpias) == 0


async def test_u4_excepcion_cualquiera_sale_sin_cambios(tablas_limpias):
    original = ValueError("un bug cualquiera")
    async with tablas_limpias() as sesion:
        with pytest.raises(ValueError) as capturada:
            async with UnitOfWork(sesion):
                await BaseRepository(sesion, ArticuloDePrueba).add(ArticuloDePrueba(nombre="Filtro"))
                raise original

    assert capturada.value is original
    assert await articulos_en_la_base(tablas_limpias) == 0


async def test_u5_la_sesion_sigue_usable_despues_del_bloque(tablas_limpias):
    async with tablas_limpias() as sesion:
        async with UnitOfWork(sesion):
            await BaseRepository(sesion, ArticuloDePrueba).add(ArticuloDePrueba(nombre="Filtro"))
        assert (await sesion.exec(text("SELECT 1"))).one() == (1,)  # después de confirmar

        with pytest.raises(ValueError):
            async with UnitOfWork(sesion):
                raise ValueError("revierte")
        assert (await sesion.exec(text("SELECT 1"))).one() == (1,)  # después de revertir


async def test_u6_bloque_dentro_de_otro(tablas_limpias):
    async with tablas_limpias() as sesion:
        uow = UnitOfWork(sesion)
        with pytest.raises(RuntimeError, match="anidado"):
            async with uow:
                await BaseRepository(sesion, ArticuloDePrueba).add(ArticuloDePrueba(nombre="Filtro"))
                async with uow:
                    pass

    assert await articulos_en_la_base(tablas_limpias) == 0


async def test_u7_bloques_consecutivos(tablas_limpias):
    async with tablas_limpias() as sesion:
        uow = UnitOfWork(sesion)
        repo = BaseRepository(sesion, ArticuloDePrueba)
        async with uow:
            await repo.add(ArticuloDePrueba(nombre="Filtro"))
        async with uow:
            await repo.add(ArticuloDePrueba(nombre="Aceite"))

    assert await articulos_en_la_base(tablas_limpias) == 2


async def test_u8_la_restriccion_salta_en_la_confirmacion(tablas_limpias):
    async with tablas_limpias() as sesion:
        async with UoWDePrueba(sesion) as uow:
            await uow.articulos.add(ArticuloDePrueba(nombre="Filtro"))

        with pytest.raises(Conflicto) as error:
            async with UoWDePrueba(sesion):
                sesion.add(ArticuloDePrueba(nombre="Filtro"))  # sin flush: choca recién al confirmar

        assert error.value.mensaje == MENSAJE_NOMBRE_REPETIDO
        assert (await sesion.exec(text("SELECT 1"))).one() == (1,)

    assert await articulos_en_la_base(tablas_limpias) == 1


async def bajas_en_la_base(fabrica) -> int:
    async with fabrica() as otra:
        return (await otra.exec(select(func.count()).select_from(BajaDePrueba))).one()


async def test_u9_escrituras_en_dos_tablas(tablas_limpias):
    async with tablas_limpias() as sesion:
        uow = UoWDePrueba(sesion)
        async with uow:
            await uow.articulos.add(ArticuloDePrueba(nombre="Filtro"))
            await uow.bajas.add(BajaDePrueba(nombre="AB123CD"))

        with pytest.raises(ValueError):
            async with uow:
                await uow.articulos.add(ArticuloDePrueba(nombre="Aceite"))
                await uow.bajas.add(BajaDePrueba(nombre="AC456EF"))
                raise ValueError("falla a mitad de la operación")

    assert await articulos_en_la_base(tablas_limpias) == 1
    assert await bajas_en_la_base(tablas_limpias) == 1


async def test_u10_la_sesion_propia_sobrevive_al_rollback_de_la_peticion(tablas_limpias):
    # Patrón de DD-05 (intento de acceso): la sesión propia confirma aunque la petición revierta.
    async with tablas_limpias() as sesion_de_la_peticion:
        with pytest.raises(ErrorDeDominio):
            async with UoWDePrueba(sesion_de_la_peticion) as uow:
                await uow.articulos.add(ArticuloDePrueba(nombre="De la petición"))
                async with tablas_limpias() as sesion_propia:
                    async with UoWDePrueba(sesion_propia) as propio:
                        await propio.articulos.add(ArticuloDePrueba(nombre="Intento anotado"))
                raise ErrorDeDominio("Credenciales inválidas")

    async with tablas_limpias() as otra:
        nombres = (await otra.exec(select(ArticuloDePrueba.nombre))).all()
    assert nombres == ["Intento anotado"]
