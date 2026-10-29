"""Login por API, credenciales uniformes y roles informativos (L1-L6)."""

from seed import CONTRASENA_DEL_SEED
import pytest
from datetime import UTC, datetime, timedelta
from sqlalchemy import text
from sqlmodel import select
from main import app
from app.modules.usuarios import service as modulo
from app.modules.usuarios.models import AsignacionRol, Rol, Usuario
from app.core.security import decodificar_token
from app.core.config import get_settings


async def test_l1_login_activo(cliente, base_sembrada):
    r = await cliente.post("/auth/login", json={"email": "admin@example.com", "password": CONTRASENA_DEL_SEED})
    assert r.status_code == 200
    assert r.json() == {"mensaje": "Sesión iniciada", "debe_cambiar_password": False, "expira_en_segundos": 1800}
    assert "access_token=" in r.headers["set-cookie"]
    assert "token" not in r.json() and "password" not in r.json()
    async with base_sembrada() as s:
        intento = (await s.exec(text("SELECT email,exito FROM intento_acceso"))).one()
        assert intento.email == "admin@example.com" and intento.exito is True


async def test_l2_l3_inexistente_verifica_ficticio_una_vez(cliente, base_sembrada, monkeypatch):
    original = modulo.verificar_password
    llamadas = []
    async def espiar(password, hash_, **kwargs):
        llamadas.append(hash_)
        return await original(password, hash_, **kwargs)
    monkeypatch.setattr(modulo, "verificar_password", espiar)
    malo = await cliente.post("/auth/login", json={"email": "admin@example.com", "password": "Mala99!"})
    llamadas.clear()
    inexistente = await cliente.post("/auth/login", json={"email": "nadie@example.com", "password": "Mala99!"})
    assert inexistente.status_code == malo.status_code == 401
    assert inexistente.json() == malo.json() == {"detail": "Correo o contraseña incorrectos"}
    assert llamadas == [app.state.hash_ficticio]
    assert "set-cookie" not in inexistente.headers
    async with base_sembrada() as s:
        assert (await s.exec(text("SELECT count(*) FROM intento_acceso WHERE NOT exito"))).one().count == 2


@pytest.mark.parametrize("password", [CONTRASENA_DEL_SEED, "Incorrecta99!"])
async def test_l4_l5_inactivo_registra_fallo(cliente, base_sembrada, password):
    async with base_sembrada() as s:
        await s.exec(text("UPDATE usuario SET activo=false WHERE id=1"))
        await s.commit()
    r = await cliente.post("/auth/login", json={"email": "admin@example.com", "password": password})
    assert r.status_code == 401
    assert r.json() == {"detail": "Correo o contraseña incorrectos"}
    assert "set-cookie" not in r.headers
    async with base_sembrada() as s:
        assert (await s.exec(text("SELECT exito FROM intento_acceso"))).one().exito is False


async def test_l6_token_solo_roles_vigentes(cliente, base_sembrada):
    async with base_sembrada() as s:
        s.add_all([
            AsignacionRol(usuario_id=1, rol=Rol.CLIENTE),
            AsignacionRol(usuario_id=1, rol=Rol.MECANICO, vence_en=datetime.now(UTC)-timedelta(seconds=1)),
            AsignacionRol(usuario_id=1, rol=Rol.RECEPCION, revocada_en=datetime.now(UTC)),
        ])
        await s.commit()
    r = await cliente.post("/auth/login", json={"email": "admin@example.com", "password": CONTRASENA_DEL_SEED})
    assert r.status_code == 200
    datos = decodificar_token(cliente.cookies["access_token"], settings=get_settings())
    assert datos.usuario_id == 1
    assert datos.roles == ["ADMIN", "CLIENTE"]


async def test_i1_i6_429_no_bcrypt_no_fila_ni_ip_falsa(cliente, base_sembrada, monkeypatch):
    for _ in range(5):
        r = await cliente.post("/auth/login", json={"email": "admin@example.com", "password": "Mala99!"})
        assert r.status_code == 401
    llamadas = []
    original = modulo.verificar_password
    async def espiar(*args, **kwargs):
        llamadas.append(True)
        return await original(*args, **kwargs)
    monkeypatch.setattr(modulo, "verificar_password", espiar)
    sexto = await cliente.post("/auth/login", json={"email": "admin@example.com", "password": CONTRASENA_DEL_SEED},
                               headers={"X-Forwarded-For": "8.8.8.8"})
    assert sexto.status_code == 429 and int(sexto.headers["retry-after"]) > 0
    assert llamadas == []
    async with base_sembrada() as s:
        filas = (await s.exec(text("SELECT ip,exito FROM intento_acceso"))).all()
        assert len(filas) == 5 and all(not f.exito and f.ip == "127.0.0.1" for f in filas)
