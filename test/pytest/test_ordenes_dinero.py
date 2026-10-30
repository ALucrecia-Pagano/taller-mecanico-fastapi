"""Dinero Decimal y límites físicos E08/RN-18."""

import pytest

from test_ordenes_alta import cuerpo_orden
from test_ordenes_catalogo import autenticar


@pytest.mark.parametrize("excede", [False, True])
async def test_total_maximo_numeric_y_exceso_409(cliente, base_sembrada, foto_de_la_base, excede):
    autenticar(cliente, 1)
    assert (await cliente.patch("/repuestos/1", json={"precio": "99999999.99"})).status_code == 200
    assert (await cliente.patch("/repuestos/2", json={"precio": "0.99" if not excede else "1.00"})).status_code == 200
    async with base_sembrada() as s:
        antes = await foto_de_la_base(s)
    respuesta = await cliente.post("/ordenes", json=cuerpo_orden(items=[{"repuesto_id": 1, "cantidad": 100}, {"repuesto_id": 2, "cantidad": 1}]))
    assert respuesta.status_code == (409 if excede else 201)
    if excede:
        assert respuesta.json() == {"detail": "El total de la orden excede el importe permitido"}
        async with base_sembrada() as s:
            assert await foto_de_la_base(s) == antes
    else:
        assert respuesta.json()["total"] == "9999999999.99"


@pytest.mark.parametrize("cantidad,total", [(3, "0.30"), (7, "0.70")])
async def test_total_centavos_exacto(cliente, base_sembrada, cantidad, total):
    autenticar(cliente, 1)
    assert (await cliente.patch("/repuestos/1", json={"precio": "0.10"})).status_code == 200
    respuesta = await cliente.post("/ordenes", json=cuerpo_orden(items=[{"repuesto_id": 1, "cantidad": cantidad}]))
    assert respuesta.status_code == 201
    assert respuesta.json()["total"] == total
    assert respuesta.json()["items"][0]["subtotal"] == total


@pytest.mark.parametrize("cantidad", [2147483648, 10**30])
async def test_cantidad_fuera_integer_422_sin_driver_error(cliente, base_sembrada, foto_de_la_base, cantidad):
    autenticar(cliente, 1)
    assert (await cliente.patch("/repuestos/1", json={"precio": "0.01"})).status_code == 200
    async with base_sembrada() as s:
        antes = await foto_de_la_base(s)
    respuesta = await cliente.post("/ordenes", json=cuerpo_orden(items=[{"repuesto_id": 1, "cantidad": cantidad}]))
    assert respuesta.status_code == 422
    async with base_sembrada() as s:
        assert await foto_de_la_base(s) == antes
