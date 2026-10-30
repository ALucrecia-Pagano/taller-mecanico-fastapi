"""AU1-7: autorización real de peticiones, roles de base y transporte cookie."""

from datetime import UTC, datetime, timedelta

import pytest
from asgi_lifespan import LifespanManager
from fastapi import APIRouter, Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.config import get_settings
from app.core.dependencies import requiere_rol
from app.core.rutas import RutaQueTraduceErrores
from app.core.security import emitir_token
from main import lifespan


def cookie(cliente, usuario_id=1, roles=("ADMIN",)):
    cliente.cookies.clear()
    cliente.cookies.set("access_token", emitir_token(usuario_id, list(roles), settings=get_settings()))


@pytest.fixture
async def cliente_roles(entorno_de_prueba):
    app = FastAPI(lifespan=lifespan)
    router = APIRouter(route_class=RutaQueTraduceErrores)
    @router.get("/admin", dependencies=[Depends(requiere_rol("ADMIN"))])
    async def admin():
        return {"permiso": "ADMIN"}
    @router.get("/alternativos", dependencies=[Depends(requiere_rol("RECEPCION", "MECANICO"))])
    async def alternativos():
        return {"permiso": "personal"}
    app.include_router(router)
    async with LifespanManager(app), AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_au1_admin_desde_base(cliente_roles, base_sembrada):
    cookie(cliente_roles)
    r = await cliente_roles.get("/admin")
    assert r.status_code == 200 and r.json() == {"permiso": "ADMIN"}


@pytest.mark.parametrize("bearer", [False, True])
async def test_au6_401_antes_rol(cliente_roles, base_sembrada, bearer):
    headers = {"Authorization": "Bearer " + emitir_token(1, ["ADMIN"], settings=get_settings())} if bearer else {}
    r = await cliente_roles.get("/admin", headers=headers)
    assert r.status_code == 401
    assert r.json() == {"detail": "Sesión no válida o vencida"}


@pytest.mark.parametrize("usuario_id,esperado", [(3, 200), (4, 200), (1, 403)])
async def test_au5_roles_alternativos_sin_bypass(cliente_roles, base_sembrada, usuario_id, esperado):
    cookie(cliente_roles, usuario_id, ())
    r = await cliente_roles.get("/alternativos")
    assert r.status_code == esperado


async def test_au2_revocado_mismo_token(cliente_roles, cliente, base_sembrada):
    cookie(cliente_roles)
    token = cliente_roles.cookies["access_token"]
    assert (await cliente_roles.get("/admin")).status_code == 200
    async with base_sembrada() as s:
        await s.exec(text("UPDATE asignacion_rol SET revocada_en=:ahora WHERE usuario_id=1").bindparams(ahora=datetime.now(UTC)))
        await s.commit()
    assert cliente_roles.cookies["access_token"] == token
    r = await cliente_roles.get("/admin")
    assert r.status_code == 403 and r.json() == {"detail": "No tiene permisos para realizar esta operación"}
    cliente.cookies.set("access_token", token)
    yo = await cliente.get("/auth/yo")
    assert yo.status_code == 200
    assert yo.json()["roles_token"] == ["ADMIN"] and yo.json()["roles_vigentes"] == []


async def test_au3_asignacion_tras_login(cliente_roles, base_sembrada):
    cookie(cliente_roles, 3, ())
    assert (await cliente_roles.get("/admin")).status_code == 403
    async with base_sembrada() as s:
        await s.exec(text("INSERT INTO asignacion_rol(usuario_id,rol,otorgada_por) VALUES(3,'ADMIN',1)"))
        await s.commit()
    assert (await cliente_roles.get("/admin")).status_code == 200


@pytest.mark.parametrize("delta", [-1, 0])
async def test_au4_vencimiento_y_igualdad(cliente_roles, base_sembrada, monkeypatch, delta):
    import app.core.dependencies as dependencias
    ahora = datetime.now(UTC)
    class Reloj(datetime):
        @classmethod
        def now(cls, tz=None):
            return ahora
    monkeypatch.setattr(dependencias, "datetime", Reloj)
    async with base_sembrada() as s:
        await s.exec(text("UPDATE asignacion_rol SET vence_en=:fecha WHERE usuario_id=1").bindparams(fecha=ahora+timedelta(seconds=delta)))
        await s.commit()
    cookie(cliente_roles)
    assert (await cliente_roles.get("/admin")).status_code == 403
