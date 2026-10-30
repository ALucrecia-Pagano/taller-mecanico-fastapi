"""Contratos públicos CH-09, E03/E04 y dinero del ejemplo (sin base mockeada)."""

import pytest
from pydantic import ValidationError

from app.modules.ordenes.schemas import EntradaOrden


def test_entrada_orden_acepta_datos_del_ejemplo():
    datos = EntradaOrden(vehiculo_id=2, falla="Ruido al frenar", items=[{"repuesto_id": 2, "cantidad": 1}])
    assert datos.model_dump() == {"vehiculo_id": 2, "falla": "Ruido al frenar", "items": [{"repuesto_id": 2, "cantidad": 1}]}


@pytest.mark.parametrize("items", [[], [{"repuesto_id": 1, "cantidad": 0}], [{"repuesto_id": 1, "cantidad": -1}], [{"repuesto_id": 1, "cantidad": 1.5}], [{"repuesto_id": 1, "cantidad": 1}, {"repuesto_id": 1, "cantidad": 2}]])
def test_entrada_orden_rechaza_items_invalidos(items):
    with pytest.raises(ValidationError):
        EntradaOrden(vehiculo_id=2, falla="x", items=items)


@pytest.mark.parametrize("campo", ["precio", "total", "estado", "creada_en", "mecanico_id", "extra"])
def test_entrada_orden_rechaza_campos_controlados(campo):
    with pytest.raises(ValidationError):
        EntradaOrden.model_validate({"vehiculo_id": 2, "falla": "x", "items": [{"repuesto_id": 1, "cantidad": 1}], campo: "x"})


@pytest.mark.parametrize("campo", ["precio_unitario", "subtotal", "total", "extra"])
def test_entrada_item_rechaza_extras(campo):
    with pytest.raises(ValidationError):
        EntradaOrden(vehiculo_id=2, falla="x", items=[{"repuesto_id": 1, "cantidad": 1, campo: "x"}])


@pytest.mark.parametrize("campo", ["vehiculo_id", "falla", "items"])
def test_entrada_orden_exige_campos(campo):
    cuerpo = {"vehiculo_id": 2, "falla": "x", "items": [{"repuesto_id": 1, "cantidad": 1}]}
    del cuerpo[campo]
    with pytest.raises(ValidationError):
        EntradaOrden.model_validate(cuerpo)


@pytest.mark.parametrize("precio,subtotal,esperado", [("0.10", "0.30", ("0.10", "0.30")), ("32000", "32000", ("32000.00", "32000.00"))])
def test_salida_item_serializa_dinero_dos_decimales(precio, subtotal, esperado):
    from app.modules.ordenes.schemas import ItemRespuesta
    from decimal import Decimal

    item = ItemRespuesta(repuesto_id=2, codigo="FRE-010", descripcion="Pastillas", cantidad=3,
                         precio_unitario=Decimal(precio), subtotal=Decimal(subtotal))
    assert item.model_dump(mode="json")["precio_unitario"] == esperado[0]
    assert item.model_dump(mode="json")["subtotal"] == esperado[1]
