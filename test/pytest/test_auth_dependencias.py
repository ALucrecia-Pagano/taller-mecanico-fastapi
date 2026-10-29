"""Autenticación sólo por cookie y precisión RN-07 (A1-A8, K3/K5)."""

import pytest
from datetime import UTC, datetime, timedelta
from sqlalchemy import text
import jwt
from app.core.config import get_settings
from app.core.security import emitir_token


@pytest.mark.parametrize("bearer", [False, True])
async def test_a1_k3_sin_cookie_no_autentica(cliente, base_sembrada, bearer):
    headers = {"Authorization": "Bearer " + emitir_token(1, ["ADMIN"], settings=get_settings())} if bearer else {}
    r = await cliente.get("/auth/yo", headers=headers)
    assert r.status_code == 401
    assert r.json() == {"detail": "Sesión no válida o vencida"}


@pytest.mark.parametrize("tipo", ["texto", "firma", "vencido", "claims", "algoritmo"])
async def test_a2_token_invalido_mensaje_neutro(cliente, base_sembrada, tipo):
    s = get_settings()
    if tipo == "texto":
        token = "no-es-token"
    elif tipo == "vencido":
        token = emitir_token(1, ["ADMIN"], settings=s, ahora=datetime.now(UTC)-timedelta(hours=2))
    elif tipo == "claims":
        token = jwt.encode({"sub": "abc", "exp": datetime.now(UTC)+timedelta(hours=1)}, s.jwt_secret_key.get_secret_value(), algorithm=s.jwt_algorithm)
    elif tipo == "algoritmo":
        token = jwt.encode({"sub": "1"}, s.jwt_secret_key.get_secret_value(), algorithm="HS512")
    else:
        token = jwt.encode({"sub": "1"}, "otra-clave-ficticia-para-test-de-firma"*2, algorithm=s.jwt_algorithm)
    cliente.cookies.set("access_token", token)
    r = await cliente.get("/auth/yo")
    assert r.status_code == 401 and r.json() == {"detail": "Sesión no válida o vencida"}


@pytest.mark.parametrize("inactivo", [False, True])
async def test_a3_a4_usuario_no_valido(cliente, base_sembrada, inactivo):
    if inactivo:
        async with base_sembrada() as s:
            await s.exec(text("UPDATE usuario SET activo=false WHERE id=1"))
            await s.commit()
    cliente.cookies.set("access_token", emitir_token(1 if inactivo else 99999, [], settings=get_settings()))
    r = await cliente.get("/auth/yo")
    assert r.status_code == 401 and r.json() == {"detail": "Sesión no válida o vencida"}


async def test_k5_cookie_valida_ignora_header(cliente, base_sembrada):
    cliente.cookies.set("access_token", emitir_token(1, ["ADMIN"], settings=get_settings()))
    r = await cliente.get("/auth/yo", headers={"Authorization": "Bearer no-es-valido"})
    assert r.status_code == 200
    assert "password_hash" not in r.text


@pytest.mark.parametrize("delta,esperado", [(-1, 401), (0, 200), (1, 200)])
async def test_a5_a6_a7_iat_microsegundos(cliente, base_sembrada, delta, esperado):
    cambio = (datetime.now(UTC)-timedelta(seconds=10)).replace(microsecond=200000)
    async with base_sembrada() as s:
        await s.exec(text("UPDATE usuario SET password_cambiada_en=:cambio WHERE id=1").bindparams(cambio=cambio))
        await s.commit()
    token = emitir_token(1, ["ADMIN"], settings=get_settings(), ahora=cambio+timedelta(microseconds=delta))
    cliente.cookies.set("access_token", token)
    r = await cliente.get("/auth/yo")
    assert r.status_code == esperado
    if esperado == 401:
        assert r.json() == {"detail": "Sesión no válida o vencida"}


async def test_a8_anterior_y_nuevo_en_mismo_segundo(cliente, base_sembrada):
    cambio = (datetime.now(UTC)-timedelta(seconds=10)).replace(microsecond=200000)
    async with base_sembrada() as s:
        await s.exec(text("UPDATE usuario SET password_cambiada_en=:cambio WHERE id=1").bindparams(cambio=cambio))
        await s.commit()
    for instante, esperado in [(cambio.replace(microsecond=100000), 401), (cambio.replace(microsecond=300000), 200)]:
        cliente.cookies.set("access_token", emitir_token(1, ["ADMIN"], settings=get_settings(), ahora=instante))
        assert (await cliente.get("/auth/yo")).status_code == esperado
