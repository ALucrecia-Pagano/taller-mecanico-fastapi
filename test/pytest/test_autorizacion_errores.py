"""E403a-c: traducción de autorización y regresiones del core."""

import pytest
from fastapi import APIRouter, Depends

from app.core.errores import PermisoDenegado
from app.core.rutas import RutaQueTraduceErrores
from test_rutas import app_de_prueba, llamar


@pytest.mark.parametrize("mensaje", [
    "No tiene permisos para realizar esta operación",
    "Debe cambiar la contraseña para continuar",
])
async def test_e403a_e403b_dependencia_traduce_permiso(mensaje):
    async def rechazar():
        raise PermisoDenegado(mensaje)
    router = APIRouter(route_class=RutaQueTraduceErrores)
    @router.get("/protegida", dependencies=[Depends(rechazar)])
    async def protegida():
        return {"acceso": True}
    r = await llamar(app_de_prueba(router), "/protegida")
    assert r.status_code == 403
    assert r.json() == {"detail": mensaje}
