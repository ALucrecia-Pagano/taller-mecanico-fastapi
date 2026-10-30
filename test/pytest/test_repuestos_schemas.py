from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.repuestos.schemas import (
    EntradaReponer,
    EntradaRepuesto,
    EntradaRepuestoPatch,
    MovimientoRespuesta,
    PrecioRespuesta,
)


def test_schemas_repuestos_validan_limites_y_extras():
    assert EntradaRepuesto(codigo="X", descripcion="Y", precio=Decimal("1.00"), stock_inicial=0)
    assert EntradaReponer(cantidad=1)
    assert EntradaRepuestoPatch(descripcion="Nueva").model_dump(exclude_unset=True) == {"descripcion": "Nueva"}

    with pytest.raises(ValidationError):
        EntradaRepuesto(codigo="X", descripcion="Y", precio=Decimal("1.00"), stock_inicial=-1)
    with pytest.raises(ValidationError):
        EntradaReponer(cantidad=0)
    with pytest.raises(ValidationError):
        EntradaRepuestoPatch(stock=1)
    with pytest.raises(ValidationError):
        EntradaRepuestoPatch()
    with pytest.raises(ValidationError):
        EntradaRepuesto(codigo="X", descripcion="Y", precio=Decimal("1.00"), stock_inicial=0, extra="x")


def test_schemas_historiales_son_planos():
    assert "usuario_id" in MovimientoRespuesta.model_fields
    assert "usuario" not in MovimientoRespuesta.model_fields
    assert "usuario_id" in PrecioRespuesta.model_fields
    assert "usuario" not in PrecioRespuesta.model_fields
