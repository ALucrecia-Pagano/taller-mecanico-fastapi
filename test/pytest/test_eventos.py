"""EV1-9: auditoría atómica integrada y paginación estable del historial."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from auth_helpers import REGISTRO, foto_auth
from seed import CONTRASENA_DEL_SEED
from test_autorizacion import cookie


async def test_ev6_paginas_orden_estable_y_formato(cliente, base_sembrada):
    async with base_sembrada() as s:
        await s.exec(text("TRUNCATE evento_seguridad RESTART IDENTITY"))
        await s.exec(text("""INSERT INTO evento_seguridad(cuando,actor,accion)
            SELECT :ahora,'admin@example.com','Evento '||n FROM generate_series(1,23) AS n""").bindparams(ahora=datetime.now(UTC)))
        await s.commit()
    cookie(cliente)
    primera = await cliente.get("/eventos")
    segunda = await cliente.get("/eventos?page=2")
    assert primera.status_code == segunda.status_code == 200
    a, b = primera.json(), segunda.json()
    assert {k:a[k] for k in ("total","page","size","pages")} == {"total":23,"page":1,"size":20,"pages":2}
    assert [e["id"] for e in a["items"]+b["items"]] == list(range(23,0,-1))
    assert all(set(e) == {"id","cuando","actor","accion"} for e in a["items"])
    assert all(datetime.fromisoformat(e["cuando"]).tzinfo is not None for e in a["items"])
    assert (await cliente.get("/eventos")).json() == a


async def test_ev7_eventos_vacios(cliente, base_sembrada):
    async with base_sembrada() as s:
        await s.exec(text("TRUNCATE evento_seguridad RESTART IDENTITY"))
        await s.commit()
    cookie(cliente)
    r = await cliente.get("/eventos")
    assert r.status_code == 200 and r.json() == {"items":[],"total":0,"page":1,"size":20,"pages":1}


@pytest.mark.parametrize("query", ["page=0", "size=0", "size=101", "page=2"])
async def test_ev8_parametros_invalidos(cliente, base_sembrada, query):
    cookie(cliente)
    r = await cliente.get("/eventos?"+query)
    assert r.status_code == 422
    if query == "page=2":
        assert r.json() == {"detail": "La página 2 no existe: hay 1"}


@pytest.mark.parametrize("size", [1,100])
async def test_ev9_tamanos_limite(cliente, base_sembrada, size):
    cookie(cliente)
    r = await cliente.get(f"/eventos?size={size}")
    assert r.status_code == 200
    assert r.json()["size"] == size and r.json()["total"] == 1 and r.json()["pages"] == 1


async def test_ev4_preserva_eventos_ch05(cliente, base_sembrada):
    assert (await cliente.post("/auth/registro", json=REGISTRO)).status_code == 201
    cookie(cliente,7,("MECANICO",))
    r = await cliente.post("/auth/cambiar-password", json={"password_actual": CONTRASENA_DEL_SEED,"password_nueva":"DistintaNueva99!"})
    assert r.status_code == 200
    cookie(cliente)
    r = await cliente.get("/eventos")
    assert r.status_code == 200
    assert [(e["actor"],e["accion"]) for e in r.json()["items"]] == [
        ("nuevo@example.com","Cambio de contraseña"),("alta@example.com","Registro de cliente alta@example.com"),
        ("SISTEMA","Carga de los datos iniciales")]


async def test_ev5_lecturas_login_logout_no_agregan_eventos(cliente, base_sembrada):
    cookie(cliente)
    antes = (await foto_auth(base_sembrada))["evento_seguridad"]
    assert (await cliente.get("/usuarios/1/roles")).status_code == 200
    assert (await cliente.get("/eventos")).status_code == 200
    assert (await cliente.get("/auth/yo")).status_code == 200
    assert (await cliente.post("/auth/login", json={"email":"admin@example.com","password":CONTRASENA_DEL_SEED})).status_code == 200
    assert (await cliente.post("/auth/logout")).status_code == 200
    assert (await foto_auth(base_sembrada))["evento_seguridad"] == antes
    async with base_sembrada() as s:
        assert (await s.exec(text("SELECT count(*) FROM intento_acceso WHERE exito"))).one().count == 1
