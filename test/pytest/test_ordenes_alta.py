"""Altas CH-09: API real y verificaciones transaccionales en PostgreSQL _test."""

from datetime import datetime

import pytest
from sqlalchemy import text

from test_ordenes_catalogo import autenticar


def cuerpo_orden(vehiculo_id=2, items=None):
    return {"vehiculo_id": vehiculo_id, "falla": "Ruido al frenar", "items": items or [
        {"repuesto_id": 2, "cantidad": 1}, {"repuesto_id": 4, "cantidad": 3}]}


async def test_alta_c10_ejemplo_atomico_y_dinero(cliente, base_sembrada, foto_de_la_base):
    autenticar(cliente, 3)
    async with base_sembrada() as sesion:
        antes = await foto_de_la_base(sesion)
    respuesta = await cliente.post("/ordenes", json=cuerpo_orden())
    assert respuesta.status_code == 201
    orden = respuesta.json()
    assert {k: orden[k] for k in ("id", "estado", "patente", "total", "mecanico_id", "falla", "cliente")} == {
        "id": 3, "estado": "PENDIENTE", "patente": "AC456EF", "total": "68000.00", "mecanico_id": None,
        "falla": "Ruido al frenar", "cliente": "Laura Cliente"}
    assert orden["items"] == [
        {"repuesto_id": 2, "codigo": "FRE-010", "descripcion": "Pastillas de freno delanteras", "cantidad": 1, "precio_unitario": "32000.00", "subtotal": "32000.00"},
        {"repuesto_id": 4, "codigo": "ACE-530", "descripcion": "Aceite 5W30 por litro", "cantidad": 3, "precio_unitario": "12000.00", "subtotal": "36000.00"}]
    assert len(orden["historial"]) == 1
    assert {k: orden["historial"][0][k] for k in ("desde_estado", "hasta_estado", "usuario_id")} == {
        "desde_estado": None, "hasta_estado": "PENDIENTE", "usuario_id": 3}
    assert datetime.fromisoformat(orden["creada_en"]).tzinfo is not None
    assert datetime.fromisoformat(orden["historial"][0]["cuando"]).tzinfo is not None
    async with base_sembrada() as sesion:
        despues = await foto_de_la_base(sesion)
    for tabla, incremento in (("orden_trabajo", 1), ("item_orden", 2), ("historial_estado_orden", 1)):
        assert len(despues[tabla]) == len(antes[tabla]) + incremento
    assert despues["repuesto"] == antes["repuesto"]
    assert despues["movimiento_stock"] == antes["movimiento_stock"]


@pytest.mark.parametrize("items,total", [([{"repuesto_id": 1, "cantidad": 1}], "8500.00"),
    ([{"repuesto_id": i, "cantidad": 1} for i in (1, 2, 3, 4)], "58500.00")])
async def test_alta_admin_uno_y_cuatro_items_ajenos(cliente, base_sembrada, items, total):
    autenticar(cliente, 1)
    respuesta = await cliente.post("/ordenes", json=cuerpo_orden(vehiculo_id=3, items=items))
    assert respuesta.status_code == 201
    assert respuesta.json()["total"] == total
    assert len(respuesta.json()["items"]) == len(items)


@pytest.mark.parametrize("cantidad", [3, 999])
async def test_alta_no_exige_stock_ni_lo_mueve(cliente, base_sembrada, cantidad):
    autenticar(cliente, 1)
    # Un repuesto con stock cero se crea por la operación válida CH-08.
    alta = await cliente.post("/repuestos", json={"codigo": "CERO-CH09", "descripcion": "Sin stock", "precio": "1.00", "stock_inicial": 0})
    assert alta.status_code == 201
    id_repuesto = alta.json()["id"]
    respuesta = await cliente.post("/ordenes", json=cuerpo_orden(items=[{"repuesto_id": id_repuesto, "cantidad": cantidad}]))
    assert respuesta.status_code == 201
    assert (await cliente.get(f"/repuestos/{id_repuesto}")).json()["stock"] == 0
    assert (await cliente.get(f"/repuestos/{id_repuesto}/movimientos")).json() == []
