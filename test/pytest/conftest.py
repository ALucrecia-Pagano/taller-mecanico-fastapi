"""Arnés de pruebas: base <POSTGRES_DB>_test, lifespan real y un cliente por test (DA-29, OB-06)."""

import asyncio
import os
import socket
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import crear_fabrica_de_sesiones, crear_motor
from guarda import derivar_base_de_prueba, verificar_base_de_prueba
from tablas_de_prueba import borrar_tablas_de_prueba, crear_tablas_de_prueba


def pytest_sessionstart(session):
    try:
        derivar_base_de_prueba(Settings().postgres_db)
    except ValueError as error:
        pytest.exit(str(error), returncode=1)


@pytest.fixture(scope="session")
def base_de_prueba() -> str:
    return derivar_base_de_prueba(Settings().postgres_db)


@pytest.fixture
def entorno_de_prueba(monkeypatch, base_de_prueba):
    """Entorno apuntado a la base de prueba; el test puede ajustarlo antes de arrancar la app."""
    monkeypatch.setenv("POSTGRES_DB", base_de_prueba)
    # Costo mínimo: cada arranque calcula el hash ficticio, y con 12 sumaría ~250 ms por test.
    monkeypatch.setenv("BCRYPT_COST", "4")
    get_settings.cache_clear()
    yield monkeypatch
    get_settings.cache_clear()


@pytest.fixture
def puerto_cerrado() -> int:
    """Un puerto local en el que no escucha nadie: la conexión se rechaza al instante."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def arrancar_app(entorno_de_prueba):
    """Arranca la app con la configuración que efectivamente resuelve get_settings()."""
    from main import app

    @asynccontextmanager
    async def arrancar():
        get_settings.cache_clear()
        verificar_base_de_prueba(get_settings())  # la misma instancia que usará el lifespan
        async with LifespanManager(app):
            yield app

    return arrancar


@pytest.fixture
def crear_cliente(arrancar_app):
    """Cliente HTTP sobre la app arrancada, para tests que ajustan el entorno antes de crearlo."""

    @asynccontextmanager
    async def crear():
        async with arrancar_app() as app:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                yield c

    return crear


@pytest.fixture
async def cliente(crear_cliente):
    async with crear_cliente() as c:
        yield c


@pytest.fixture(scope="session")
def settings_de_prueba(base_de_prueba) -> Settings:
    """La Settings que resuelve get_settings() con la base de prueba, igual que en el lifespan."""
    with pytest.MonkeyPatch.context() as entorno:
        entorno.setenv("POSTGRES_DB", base_de_prueba)
        get_settings.cache_clear()
        settings = get_settings()
    get_settings.cache_clear()
    verificar_base_de_prueba(settings)
    return settings


@pytest.fixture(scope="session")
async def tablas_de_prueba(settings_de_prueba):
    """Tablas prueba_* por DDL a mano (nunca create_all), creadas detrás de la guarda (design D7)."""
    await crear_tablas_de_prueba(settings_de_prueba)
    yield
    await borrar_tablas_de_prueba(settings_de_prueba)


@pytest.fixture(scope="session")
async def fabrica_de_prueba(settings_de_prueba, tablas_de_prueba):
    """Fábrica de sesiones de CH-01 sobre la base de prueba, sin levantar la app."""
    engine = crear_motor(settings_de_prueba)
    yield crear_fabrica_de_sesiones(engine)
    await engine.dispose()


@pytest.fixture
async def tablas_limpias(fabrica_de_prueba):
    """Tablas vacías y secuencias reiniciadas: cada test arranca con ids desde 1."""
    async with fabrica_de_prueba() as sesion:
        await sesion.exec(text("TRUNCATE prueba_baja, prueba_articulo RESTART IDENTITY"))
        await sesion.commit()
    return fabrica_de_prueba


@pytest.fixture
async def servidor_mudo():
    """Servidor TCP que acepta la conexión y nunca responde: simula una base que no contesta."""
    conexiones = []

    async def aceptar(reader, writer):
        conexiones.append(writer)
        await reader.read()  # espera sin responder hasta que el cliente cierre

    servidor = await asyncio.start_server(aceptar, "127.0.0.1", 0)
    yield servidor.sockets[0].getsockname()[1]
    for writer in conexiones:
        writer.close()
    servidor.close()
    await servidor.wait_closed()


@pytest.fixture(scope="session")
def alembic_de_prueba(settings_de_prueba, base_de_prueba):
    """Corre Alembic por subproceso contra la base de prueba, como lo haría una persona (nota 6d de CH-01)."""
    raiz = Path(__file__).resolve().parents[2]

    def correr(*argumentos: str) -> subprocess.CompletedProcess:
        verificar_base_de_prueba(settings_de_prueba)
        resultado = subprocess.run(
            [sys.executable, "-m", "alembic", *argumentos],
            cwd=raiz,
            env={**os.environ, "POSTGRES_DB": base_de_prueba},
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert resultado.returncode == 0, resultado.stdout + resultado.stderr
        return resultado

    return correr


@pytest.fixture(scope="session")
def esquema_al_dia(alembic_de_prueba):
    """La base de prueba migrada a la última versión, una vez por sesión."""
    alembic_de_prueba("upgrade", "head")


@pytest.fixture(scope="session")
async def motor_del_esquema(settings_de_prueba, esquema_al_dia):
    engine = crear_motor(settings_de_prueba)
    yield engine
    await engine.dispose()


@pytest.fixture
async def base_sembrada(settings_de_prueba, esquema_al_dia):
    """Base de prueba cargada por el seed; al terminar la deja vacía (design D7).

    Vaciarla importa: M3 y X2 esperan las tablas del dominio vacías, y _una_fila_por_tabla
    (D5, X1) carga su propio catálogo, que chocaría con el del seed.
    Devuelve una fábrica de sesiones sobre esa base para leer lo cargado.
    """
    import seed

    # settings_de_prueba es de sesión y no ve el BCRYPT_COST=4 de entorno_de_prueba.
    settings = settings_de_prueba.model_copy(update={"bcrypt_cost": 4})
    verificar_base_de_prueba(settings)
    await seed.sembrar(settings)
    engine = crear_motor(settings)
    try:
        yield crear_fabrica_de_sesiones(engine)
    finally:
        async with engine.begin() as conexion:
            await conexion.execute(seed.sentencia_de_vaciado())
        await engine.dispose()


@pytest.fixture
def foto_de_la_base():
    """Las filas de las 13 tablas del dominio, sin las columnas de hora, ordenadas por clave (S9, S12)."""
    from sqlmodel import SQLModel

    import seed  # noqa: F401  (importa los cuatro modelos: las 13 tablas quedan en la metadata)

    # Los nombres de tablas y columnas salen de la metadata y del catálogo de la base, nunca de una entrada.
    async def foto(sesion) -> dict[str, list[tuple]]:
        resultado = {}
        for tabla in SQLModel.metadata.sorted_tables:
            columnas = (
                await sesion.exec(
                    text(
                        "SELECT column_name FROM information_schema.columns"
                        " WHERE table_schema = 'public' AND table_name = :tabla"
                        " AND data_type <> 'timestamp with time zone' ORDER BY ordinal_position"
                    ).bindparams(tabla=tabla.name)
                )
            ).scalars().all()
            clave = ", ".join(c.name for c in tabla.primary_key.columns)
            filas = await sesion.exec(text(f"SELECT {', '.join(columnas)} FROM {tabla.name} ORDER BY {clave}"))
            resultado[tabla.name] = [tuple(fila) for fila in filas.all()]
        return resultado

    return foto


@pytest.fixture
async def conexion_revertida(motor_del_esquema):
    """Sesión sobre una transacción externa que se revierte al final: el test no deja filas.

    Cada flush o rechazo esperado va en un SAVEPOINT; las secuencias no se revierten,
    así que ningún test asume ids fijos.
    """
    async with motor_del_esquema.connect() as conexion:
        transaccion = await conexion.begin()
        sesion = AsyncSession(bind=conexion, join_transaction_mode="create_savepoint", expire_on_commit=False)
        try:
            yield sesion
        finally:
            await sesion.close()
            await transaccion.rollback()
