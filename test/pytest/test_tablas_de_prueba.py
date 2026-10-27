"""Tablas de prueba de la suite (spec suite-de-pruebas, F1-F2)."""

import pytest
from sqlalchemy import text

from app.core.config import Settings
from app.core.database import crear_motor
from tablas_de_prueba import crear_tablas_de_prueba


def settings_de(postgres_db: str, puerto: int) -> Settings:
    return Settings(
        _env_file=None,
        postgres_password="secreta",
        jwt_secret_key="k" * 64,
        postgres_db=postgres_db,
        postgres_host="127.0.0.1",
        postgres_port=puerto,
    )


async def test_f1_la_guarda_va_antes_que_el_ddl(puerto_cerrado):
    # Con el puerto cerrado, conectarse daría OSError: si sale el error de la guarda, no se conectó.
    with pytest.raises(pytest.fail.Exception, match="_test"):
        await crear_tablas_de_prueba(settings_de("taller_mecanico", puerto_cerrado))


async def contar_filas(settings) -> int:
    engine = crear_motor(settings)
    try:
        async with engine.connect() as conexion:
            articulos = (await conexion.execute(text("SELECT count(*) FROM prueba_articulo"))).scalar_one()
            bajas = (await conexion.execute(text("SELECT count(*) FROM prueba_baja"))).scalar_one()
            return articulos + bajas
    finally:
        await engine.dispose()


async def test_f2_tablas_que_quedaron_de_una_corrida_interrumpida(settings_de_prueba, tablas_de_prueba):
    settings = settings_de_prueba  # las tablas ya existen: las creó la fixture de sesión
    engine = crear_motor(settings)
    try:
        async with engine.begin() as conexion:  # una fila que una corrida cortada dejó atrás
            await conexion.execute(text("INSERT INTO prueba_articulo (nombre) VALUES ('resto')"))
    finally:
        await engine.dispose()

    await crear_tablas_de_prueba(settings)

    assert await contar_filas(settings) == 0


def test_los_modelos_de_prueba_no_tocan_la_metadata_de_alembic():
    from sqlmodel import SQLModel

    from tablas_de_prueba import ArticuloDePrueba, BajaDePrueba

    assert ArticuloDePrueba.__tablename__ == "prueba_articulo"
    assert BajaDePrueba.__tablename__ == "prueba_baja"
    assert "prueba_articulo" not in SQLModel.metadata.tables
    assert "prueba_baja" not in SQLModel.metadata.tables
