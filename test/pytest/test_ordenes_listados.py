"""Paginación, estado y propiedad de órdenes E15–E17/E21."""

import pytest
from sqlalchemy import text

from test_ordenes_alta import cuerpo_orden
from test_ordenes_catalogo import autenticar


@pytest.mark.parametrize("usuario", [1, 3, 4, 5])
async def test_listado_personal_todas_sin_filtrar_mecanico(cliente, base_sembrada, usuario):
    autenticar(cliente, usuario)
    respuesta = await cliente.get("/ordenes")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert {k: datos[k] for k in ("total", "page", "size", "pages")} == {"total": 2, "page": 1, "size": 20, "pages": 1}
    assert [i["id"] for i in datos["items"]] == [1, 2]
    assert all(set(i) == {"id", "estado", "patente", "total", "creada_en", "mecanico_id", "falla", "cliente"} for i in datos["items"])


@pytest.mark.parametrize("estado,ids", [("PENDIENTE", [1]), ("EN_REPARACION", [2]), ("CANCELADA", []), ("TERMINADA", [])])
async def test_filtro_estado_y_count_identicos(cliente, base_sembrada, estado, ids):
    autenticar(cliente, 5)
    respuesta = await cliente.get("/ordenes", params={"estado": estado, "size": 1})
    assert respuesta.status_code == 200
    assert [i["id"] for i in respuesta.json()["items"]] == ids
    assert respuesta.json()["total"] == len(ids)
    assert respuesta.json()["pages"] == 1


@pytest.mark.parametrize("estado", ["XYZ", "", "pendiente", "' OR '1'='1"])
async def test_filtro_estado_desconocido_422(cliente, base_sembrada, estado):
    autenticar(cliente, 4)
    assert (await cliente.get("/ordenes", params={"estado": estado})).status_code == 422


@pytest.mark.parametrize("ruta", ["/ordenes", "/mis-ordenes"])
@pytest.mark.parametrize("params", [{"page": 0}, {"page": "abc"}, {"size": 0}, {"size": 500}, {"size": "abc"}, {"page": 999}])
async def test_paginacion_invalida_422(cliente, base_sembrada, ruta, params):
    autenticar(cliente, 1)
    assert (await cliente.get(ruta, params=params)).status_code == 422


async def test_paginas_primera_ultima_y_size100(cliente, base_sembrada):
    autenticar(cliente, 1)
    primera = await cliente.get("/ordenes", params={"size": 1})
    ultima = await cliente.get("/ordenes", params={"size": 1, "page": 2})
    assert primera.status_code == ultima.status_code == 200
    assert [i["id"] for i in primera.json()["items"]] == [1]
    assert [i["id"] for i in ultima.json()["items"]] == [2]
    assert primera.json()["total"] == ultima.json()["total"] == 2
    assert primera.json()["pages"] == ultima.json()["pages"] == 2
    assert (await cliente.get("/ordenes", params={"size": 100})).status_code == 200


@pytest.mark.parametrize("usuario,ids", [(6, [1]), (1, []), (3, []), (4, [])])
async def test_mis_ordenes_solo_dueno_y_sin_ficha_vacio(cliente, base_sembrada, usuario, ids):
    autenticar(cliente, usuario)
    respuesta = await cliente.get("/mis-ordenes", params={"size": 2})
    assert respuesta.status_code == 200
    assert respuesta.json() == {"items": respuesta.json()["items"], "total": len(ids), "page": 1, "size": 2, "pages": 1}
    assert [i["id"] for i in respuesta.json()["items"]] == ids
    if not ids:
        assert (await cliente.get("/mis-ordenes", params={"page": 2})).json() == {"detail": "La página 2 no existe: hay 1"}


async def test_mis_ordenes_no_exige_cliente_y_personal_no_amplia(cliente, base_sembrada):
    async with base_sembrada() as s:
        await s.exec(text("UPDATE asignacion_rol SET revocada_en=now() WHERE usuario_id=6"))
        await s.exec(text("INSERT INTO asignacion_rol(usuario_id,rol) VALUES (6,'MECANICO')"))
        await s.commit()
    autenticar(cliente, 6, [])
    assert [i["id"] for i in (await cliente.get("/mis-ordenes")).json()["items"]] == [1]
    assert [i["id"] for i in (await cliente.get("/ordenes")).json()["items"]] == [1, 2]


async def test_listados_vacios_y_bajas_historicas(cliente, base_sembrada):
    autenticar(cliente, 1)
    vacio = await cliente.get("/ordenes", params={"estado": "CANCELADA"})
    assert vacio.status_code == 200
    assert vacio.json() == {"items": [], "total": 0, "page": 1, "size": 20, "pages": 1}
    assert (await cliente.get("/ordenes", params={"estado": "CANCELADA", "page": 2})).status_code == 422
    async with base_sembrada() as s:
        await s.exec(text("UPDATE orden_trabajo SET estado='TERMINADA' WHERE id=1"))
        await s.commit()
    assert (await cliente.delete("/vehiculos/1")).status_code == 204
    assert (await cliente.delete("/repuestos/1")).status_code == 204
    assert [i["id"] for i in (await cliente.get("/ordenes")).json()["items"]] == [1, 2]
    autenticar(cliente, 6)
    propia = await cliente.get("/mis-ordenes")
    assert propia.status_code == 200
    assert propia.json()["items"][0]["patente"] == "AB123CD"
    assert propia.json()["items"][0]["total"] == "56500.00"
