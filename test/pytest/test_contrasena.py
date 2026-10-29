"""Contrato de contraseña: 72 bytes, no vacía y sin NUL (spec contrasenas, C1-C4). No toca la base."""

import pytest
from pydantic import TypeAdapter, ValidationError

from app.core.security import Contrasena
from seed import CONTRASENA_DEL_SEED

contrato = TypeAdapter(Contrasena)


def test_c1_contrasena_comun():
    assert contrato.validate_python(CONTRASENA_DEL_SEED) == CONTRASENA_DEL_SEED


@pytest.mark.parametrize(
    ("aceptada", "rechazada"),
    [
        ("a" * 72, "a" * 73),  # C2: ASCII, un byte por carácter
        ("ñ" * 36, "ñ" * 36 + "a"),  # C3: 36 caracteres = 72 bytes; 37 caracteres = 73 bytes
    ],
    ids=["c2_ascii", "c3_bytes_no_caracteres"],
)
def test_c2_c3_borde_de_72_bytes(aceptada, rechazada):
    assert contrato.validate_python(aceptada) == aceptada
    with pytest.raises(ValidationError, match="72 bytes"):
        contrato.validate_python(rechazada)


@pytest.mark.parametrize("invalida", ["", "abc\x00"], ids=["vacia", "con_nul"])
def test_c4_vacia_o_con_nul(invalida):
    with pytest.raises(ValidationError):
        contrato.validate_python(invalida)
