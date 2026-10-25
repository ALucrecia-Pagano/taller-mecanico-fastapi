"""Arnés de pruebas: base <POSTGRES_DB>_test, lifespan real y un cliente por test (DA-29, OB-06)."""

import asyncio
import socket
from contextlib import asynccontextmanager

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings, get_settings
from guarda import derivar_base_de_prueba, verificar_base_de_prueba


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
