"""Catálogo CH-09 E18/E22 con base real."""

import pytest
from sqlalchemy import text

from app.core.config import get_settings
from app.core.security import emitir_token


def autenticar(cliente, usuario_id=1, roles=None):
    cliente.cookies.set("access_token", emitir_token(usuario_id, roles or [], settings=get_settings()))


async def test_catalogo_estados_sembrado_orden_y_finales(cliente, base_sembrada):
    autenticar(cliente, 6)
    respuesta = await cliente.get("/estados-orden")
    assert respuesta.status_code == 200
    assert [(e["codigo"], e["posicion"], e["es_final"]) for e in respuesta.json()] == [
        ("PENDIENTE", 1, False), ("EN_REPARACION", 2, False), ("TERMINADA", 3, True), ("CANCELADA", 4, True)]
    assert all(set(e) == {"codigo", "descripcion", "posicion", "es_final"} for e in respuesta.json())


@pytest.mark.parametrize("usuario,esperado", [(None, 401), (7, 403), (3, 200)])
async def test_catalogo_autenticacion_y_cambio(cliente, base_sembrada, usuario, esperado):
    if usuario:
        autenticar(cliente, usuario)
    assert (await cliente.get("/estados-orden")).status_code == esperado


async def test_catalogo_vacio_no_se_repara(cliente, base_sembrada):
    async with base_sembrada() as sesion:
        await sesion.exec(text("TRUNCATE estado_orden CASCADE"))
        await sesion.commit()
    autenticar(cliente)
    assert (await cliente.get("/estados-orden")).json() == []


async def test_catalogo_solo_lectura_y_router_traductor(cliente, base_sembrada):
    from main import app
    from app.core.rutas import RutaQueTraduceErrores
    from app.modules.ordenes.repository import EstadoOrdenRepository

    autenticar(cliente)
    for metodo in ("POST", "PATCH", "DELETE"):
        assert (await cliente.request(metodo, "/estados-orden", json={})).status_code == 405
    from test_rutas import rutas_de
    rutas = [r for r in rutas_de(app.routes) if r.path == "/estados-orden"]
    assert len(rutas) == 1 and isinstance(rutas[0], RutaQueTraduceErrores)
    assert not any(hasattr(EstadoOrdenRepository, nombre) for nombre in ("add", "update", "delete"))
