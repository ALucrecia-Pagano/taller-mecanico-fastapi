"""Recursos creados y liberados en el ciclo de vida (spec ciclo-de-vida, L1-L4, G1-G2, F1-F5)."""

import asyncio

import pytest
from asgi_lifespan import LifespanManager
from fastapi import Request
from pydantic import ValidationError
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.core.security import hashear_password, verificar_password
from espia_bcrypt import espiar_bcrypt
from seed import CONTRASENA_DEL_SEED
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


async def test_f1_hash_ficticio_con_el_costo_configurado(arrancar_app):
    async with arrancar_app() as app_arrancada:
        assert app_arrancada.state.hash_ficticio.startswith("$2b$04$")  # BCRYPT_COST=4 del arnés


async def test_f2_el_hash_ficticio_se_calcula_una_sola_vez(crear_cliente, entorno_de_prueba):
    llamadas = []

    async def contar(*args, **kwargs):
        llamadas.append(args)
        return await hashear_password(*args, **kwargs)

    entorno_de_prueba.setattr("main.hashear_password", contar)

    async with crear_cliente() as cliente:
        for _ in range(3):
            assert (await cliente.get("/health/live")).status_code == 200

    assert len(llamadas) == 1


async def test_f3_ninguna_contrasena_conocida_verifica(arrancar_app):
    async with arrancar_app() as app_arrancada:
        estado = app_arrancada.state
        assert await verificar_password(CONTRASENA_DEL_SEED, estado.hash_ficticio, semaforo=estado.semaforo_bcrypt) is False


async def test_f4_el_costo_no_esta_fijo(arrancar_app, entorno_de_prueba):
    entorno_de_prueba.setenv("BCRYPT_COST", "5")

    async with arrancar_app() as app_arrancada:
        assert app_arrancada.state.hash_ficticio.startswith("$2b$05$")


async def test_f5_el_semaforo_sale_de_la_configuracion(arrancar_app, entorno_de_prueba):
    entorno_de_prueba.setenv("BCRYPT_MAX_CONCURRENCY", "1")

    async with arrancar_app() as app_arrancada:
        estado = app_arrancada.state
        espia = espiar_bcrypt(entorno_de_prueba, pausa=0.05)  # después del arranque: sólo cuenta lo de abajo

        await asyncio.gather(
            *(verificar_password("x", estado.hash_ficticio, semaforo=estado.semaforo_bcrypt) for _ in range(2))
        )

    assert len(espia.hilos) == 2
    assert espia.pico == 1
