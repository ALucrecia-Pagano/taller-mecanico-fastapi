"""AU8-12: composición transversal y C-09, sin privilegios inventados."""

import pytest
from asgi_lifespan import LifespanManager
from fastapi import APIRouter, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.dependencies import UsuarioActualDep, controlar_cambio_obligatorio
from app.core.rutas import RutaQueTraduceErrores
from seed import CONTRASENA_DEL_SEED
from test_autorizacion import cookie
import main


@pytest.fixture
async def cliente_grupo(entorno_de_prueba):
    grupo = main.rutas_protegidas
    originales = list(grupo.routes)
    prueba = APIRouter(route_class=RutaQueTraduceErrores)
    @prueba.get("/solo-identidad")
    async def identidad(actual: UsuarioActualDep):
        return {"email": actual.usuario.email}
    grupo.include_router(prueba)
    app = FastAPI(lifespan=main.lifespan)
    app.include_router(grupo)
    try:
        async with LifespanManager(app), AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
    finally:
        grupo.routes[:] = originales


@pytest.mark.parametrize("usuario_id,esperado", [(7, 403), (6, 200)])
async def test_au8_grupo_solo_identidad(cliente_grupo, base_sembrada, usuario_id, esperado):
    cookie(cliente_grupo, usuario_id, ())
    r = await cliente_grupo.get("/solo-identidad")
    assert r.status_code == esperado
    if esperado == 403:
        assert r.json() == {"detail": "Debe cambiar la contraseña para continuar"}


def test_au8_control_declarado_una_vez():
    assert [d.dependency for d in main.rutas_protegidas.dependencies] == [controlar_cambio_obligatorio]
    assert main.rutas_abiertas.dependencies == []


async def test_au9_au10_auth_y_salud_no_bloqueadas(cliente, cliente_grupo, base_sembrada):
    cookie(cliente, 7, ("MECANICO",))
    cookie(cliente_grupo, 7, ())
    assert (await cliente.get("/health/live")).status_code == 200
    assert (await cliente.get("/health/ready")).status_code == 200
    assert (await cliente.get("/auth/yo")).status_code == 200
    r = await cliente.post("/auth/cambiar-password", json={"password_actual": CONTRASENA_DEL_SEED,
                                                          "password_nueva": CONTRASENA_DEL_SEED})
    assert r.status_code == 422
    assert (await cliente_grupo.get("/solo-identidad")).status_code == 403


async def test_au11_cookie_nueva_desbloquea_identidad(cliente, cliente_grupo, base_sembrada):
    cookie(cliente, 7, ("MECANICO",))
    anterior = cliente.cookies["access_token"]
    r = await cliente.post("/auth/cambiar-password", json={"password_actual": CONTRASENA_DEL_SEED,
                                                          "password_nueva": "DistintaNueva99!"})
    assert r.status_code == 200
    cliente_grupo.cookies.set("access_token", r.cookies["access_token"])
    assert (await cliente_grupo.get("/solo-identidad")).status_code == 200
    cliente_grupo.cookies.set("access_token", anterior)
    assert (await cliente_grupo.get("/solo-identidad")).status_code == 401
