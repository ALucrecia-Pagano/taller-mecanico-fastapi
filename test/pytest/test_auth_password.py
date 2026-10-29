"""Cambio atómico, rechazo contractual y renovación inmediata (P1-P5)."""

import asyncio
from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy import event, text
from seed import CONTRASENA_DEL_SEED
from app.core.security import emitir_token, verificar_password
from app.core.config import get_settings
from auth_helpers import foto_auth
from app.modules.usuarios.models import EventoSeguridad
from app.modules.usuarios import service as modulo
from app.core.errores import Conflicto

NUEVA = "DistintaNueva99!"


async def test_p1_cambio_actualiza_hash_fecha_bandera_y_evento(cliente, base_sembrada):
    cliente.cookies.set("access_token", emitir_token(7, ["MECANICO"], settings=get_settings()))
    antes = await foto_auth(base_sembrada)
    r = await cliente.post("/auth/cambiar-password", json={"password_actual": CONTRASENA_DEL_SEED, "password_nueva": NUEVA})
    assert r.status_code == 200 and "set-cookie" in r.headers
    despues = await foto_auth(base_sembrada)
    usuario = despues["usuario"][-1]
    assert not usuario.debe_cambiar_password
    assert usuario.password_cambiada_en is not None and usuario.password_cambiada_en.tzinfo is not None
    assert usuario.password_hash != antes["usuario"][-1].password_hash
    assert await verificar_password(NUEVA, usuario.password_hash, semaforo=asyncio.Semaphore(1))
    assert not await verificar_password(CONTRASENA_DEL_SEED, usuario.password_hash, semaforo=asyncio.Semaphore(1))
    assert len(despues["evento_seguridad"]) == len(antes["evento_seguridad"]) + 1
    assert despues["evento_seguridad"][-1].actor == "nuevo@example.com"
    assert despues["evento_seguridad"][-1].accion == "Cambio de contraseña"


async def test_p2_actual_incorrecta_no_cambia_nada(cliente, base_sembrada, monkeypatch):
    cliente.cookies.set("access_token", emitir_token(7, ["MECANICO"], settings=get_settings()))
    antes = await foto_auth(base_sembrada)
    llamadas_hash = []
    original = modulo.hashear_password
    async def espiar(*args, **kwargs):
        llamadas_hash.append(True)
        return await original(*args, **kwargs)
    monkeypatch.setattr(modulo, "hashear_password", espiar)
    r = await cliente.post("/auth/cambiar-password", json={"password_actual": "Incorrecta99!", "password_nueva": NUEVA})
    assert r.status_code == 401 and "set-cookie" not in r.headers
    assert llamadas_hash == []
    assert await foto_auth(base_sembrada) == antes


async def test_p4_fallo_del_evento_revierte_y_no_emite_cookie(cliente, base_sembrada):
    cliente.cookies.set("access_token", emitir_token(7, ["MECANICO"], settings=get_settings()))
    antes = await foto_auth(base_sembrada)
    def fallar(mapper, connection, target):
        raise Conflicto("Fallo controlado del evento")
    event.listen(EventoSeguridad, "before_insert", fallar)
    try:
        r = await cliente.post("/auth/cambiar-password", json={"password_actual": CONTRASENA_DEL_SEED, "password_nueva": NUEVA})
    finally:
        event.remove(EventoSeguridad, "before_insert", fallar)
    assert r.status_code == 409 and "set-cookie" not in r.headers
    assert await foto_auth(base_sembrada) == antes


@pytest.mark.parametrize("usuario_id", [1, 7])
async def test_p3_p3b_igualdad_422_cero_bcrypt_sin_escrituras(cliente, base_sembrada, monkeypatch, usuario_id):
    cliente.cookies.set("access_token", emitir_token(usuario_id, [], settings=get_settings()))
    antes = await foto_auth(base_sembrada)
    llamadas = []
    original_verificar = modulo.verificar_password
    original_hashear = modulo.hashear_password
    async def verificar(*args, **kwargs):
        llamadas.append("verificar")
        return await original_verificar(*args, **kwargs)
    async def hashear(*args, **kwargs):
        llamadas.append("hashear")
        return await original_hashear(*args, **kwargs)
    monkeypatch.setattr(modulo, "verificar_password", verificar)
    monkeypatch.setattr(modulo, "hashear_password", hashear)
    r = await cliente.post("/auth/cambiar-password", json={"password_actual": CONTRASENA_DEL_SEED, "password_nueva": CONTRASENA_DEL_SEED})
    assert r.status_code == 422 and "set-cookie" not in r.headers
    assert llamadas == []
    assert await foto_auth(base_sembrada) == antes


async def test_p5_y3_cookie_nueva_vale_y_anterior_no_mismo_segundo(cliente, base_sembrada, monkeypatch):
    import app.core.security as seguridad
    reloj = [(datetime.now(UTC)-timedelta(seconds=3)).replace(microsecond=100000)]
    class Reloj(datetime):
        @classmethod
        def now(cls, tz=None):
            return reloj[0]
    monkeypatch.setattr(seguridad, "datetime", Reloj)
    monkeypatch.setattr(modulo, "datetime", Reloj)
    login = await cliente.post("/auth/login", json={"email": "nuevo@example.com", "password": CONTRASENA_DEL_SEED})
    assert login.status_code == 200 and login.json()["debe_cambiar_password"] is True
    anterior = cliente.cookies["access_token"]
    assert (await cliente.get("/auth/yo")).json()["debe_cambiar_password"] is True
    reloj[0] = reloj[0].replace(microsecond=200000)
    cambio = await cliente.post("/auth/cambiar-password", json={"password_actual": CONTRASENA_DEL_SEED, "password_nueva": NUEVA})
    assert cambio.status_code == 200
    nuevo = cliente.cookies["access_token"]
    perfil = await cliente.get("/auth/yo")
    assert perfil.status_code == 200 and perfil.json()["debe_cambiar_password"] is False
    cliente.cookies.clear()
    cliente.cookies.set("access_token", anterior)
    assert (await cliente.get("/auth/yo")).status_code == 401
    cliente.cookies.set("access_token", nuevo)
    assert (await cliente.get("/auth/yo")).status_code == 200
