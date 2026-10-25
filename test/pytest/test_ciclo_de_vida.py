"""Recursos de base de datos en el ciclo de vida (spec ciclo-de-vida, L1-L4, G1-G2)."""

import pytest
from asgi_lifespan import LifespanManager
from fastapi import Request
from pydantic import ValidationError
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from main import app


async def test_l1_el_arranque_puebla_el_estado(arrancar_app):
    async with arrancar_app() as app_arrancada:
        assert app_arrancada.state.engine.pool.size() == get_settings().db_pool_size
        assert app_arrancada.state.session_factory.kw["expire_on_commit"] is False


async def test_l1_el_pool_sale_de_la_configuracion(arrancar_app, entorno_de_prueba):
    entorno_de_prueba.setenv("DB_POOL_SIZE", "3")

    async with arrancar_app() as app_arrancada:
        assert app_arrancada.state.engine.pool.size() == 3


async def test_l4_sin_clave_de_firma_el_arranque_falla(entorno_de_prueba, tmp_path):
    entorno_de_prueba.chdir(tmp_path)  # sin .env: sólo cuenta el entorno
    entorno_de_prueba.setenv("POSTGRES_PASSWORD", "secreta")
    entorno_de_prueba.delenv("JWT_SECRET_KEY", raising=False)

    with pytest.raises(ValidationError, match="jwt_secret_key"):
        async with LifespanManager(app):
            pass


async def test_l2_el_apagado_libera_el_pool(arrancar_app):
    async with arrancar_app() as app_arrancada:
        engine = app_arrancada.state.engine
        async with engine.connect() as conexion:
            assert (await conexion.execute(text("SELECT 1"))).scalar_one() == 1
        pool_en_uso = engine.pool

    assert engine.pool is not pool_en_uso
    assert engine.pool.checkedin() == 0


async def test_l3_arranca_con_la_base_caida(arrancar_app, entorno_de_prueba, puerto_cerrado):
    entorno_de_prueba.setenv("POSTGRES_HOST", "127.0.0.1")
    entorno_de_prueba.setenv("POSTGRES_PORT", str(puerto_cerrado))

    async with arrancar_app() as app_arrancada:
        assert app_arrancada.state.engine.url.port == puerto_cerrado


def peticion(app_arrancada) -> Request:
    return Request({"type": "http", "app": app_arrancada})


async def test_g1_cada_peticion_recibe_su_propia_sesion(arrancar_app):
    async with arrancar_app() as app_arrancada:
        primera = get_session(peticion(app_arrancada))
        segunda = get_session(peticion(app_arrancada))
        sesion_1 = await anext(primera)
        sesion_2 = await anext(segunda)
        try:
            assert sesion_1 is not sesion_2
            assert isinstance(sesion_1, AsyncSession)
            assert sesion_1.bind is app_arrancada.state.engine
            assert (await sesion_1.exec(text("SELECT 1"))).scalar_one() == 1
            assert (await sesion_2.exec(text("SELECT 1"))).scalar_one() == 1
        finally:
            await primera.aclose()
            await segunda.aclose()


async def test_g2_la_sesion_se_cierra_y_devuelve_la_conexion(arrancar_app):
    async with arrancar_app() as app_arrancada:
        pool = app_arrancada.state.engine.pool
        dependencia = get_session(peticion(app_arrancada))
        sesion = await anext(dependencia)
        await sesion.exec(text("SELECT 1"))
        assert pool.checkedout() == 1

        await dependencia.aclose()

        assert pool.checkedout() == 0
