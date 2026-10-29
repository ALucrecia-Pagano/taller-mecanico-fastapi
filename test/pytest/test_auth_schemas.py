"""Contratos públicos de autenticación (V1-V4, P3/P3b)."""

import pytest
from pydantic import ValidationError

from app.modules.usuarios.schemas import CambioPassword, Login, Registro


def test_v1_registro_acepta_72_bytes():
    datos = Registro(email="alta@example.com", nombre="Alta", password="a" * 72,
                     documento="40000001", telefono="2614000003")
    assert datos.password == "a" * 72


CONTRATOS = [
    (Registro, {"email": "alta@example.com", "nombre": "Alta", "password": "Clave99!",
                "documento": "40000001", "telefono": "2614000003"}, "password"),
    (Login, {"email": "alta@example.com", "password": "Clave99!"}, "password"),
    (CambioPassword, {"password_actual": "Actual99!", "password_nueva": "Nueva99!"}, "password_actual"),
    (CambioPassword, {"password_actual": "Actual99!", "password_nueva": "Nueva99!"}, "password_nueva"),
]


@pytest.mark.parametrize("contrato,datos,campo", CONTRATOS)
@pytest.mark.parametrize("valor", ["a" * 72, "ñ" * 36])
def test_v1_todos_los_campos_aceptan_72_bytes(contrato, datos, campo, valor):
    entrada = contrato(**{**datos, campo: valor})
    assert getattr(entrada, campo) == valor


@pytest.mark.parametrize("contrato,datos,campo", CONTRATOS)
@pytest.mark.parametrize("valor", ["a" * 73, "ñ" * 36 + "a", "", "abc\x00"])
def test_v2_v3_rechaza_73_bytes_vacio_nul(contrato, datos, campo, valor):
    with pytest.raises(ValidationError):
        contrato(**{**datos, campo: valor})


@pytest.mark.parametrize("contrato,datos,campo", CONTRATOS)
def test_v4_rechaza_extras(contrato, datos, campo):
    with pytest.raises(ValidationError):
        contrato(**datos, rol="ADMIN")


@pytest.mark.parametrize("clave", ["Provisoria99!", "Otra99!"])
def test_p3_p3b_contrato_rechaza_igualdad(clave):
    with pytest.raises(ValidationError):
        CambioPassword(password_actual=clave, password_nueva=clave)


@pytest.mark.parametrize("ruta,datos,campo", [
    ("/auth/registro", CONTRATOS[0][1], "password"),
    ("/auth/login", CONTRATOS[1][1], "password"),
    ("/auth/cambiar-password", CONTRATOS[2][1], "password_actual"),
    ("/auth/cambiar-password", CONTRATOS[3][1], "password_nueva"),
])
async def test_v2_v3_v4_api_422_sin_bcrypt(cliente, base_sembrada, monkeypatch, ruta, datos, campo):
    from app.core.config import get_settings
    from app.core.security import emitir_token
    from app.modules.usuarios import service as modulo
    from auth_helpers import foto_auth
    cliente.cookies.set("access_token", emitir_token(7, [], settings=get_settings()))
    antes = await foto_auth(base_sembrada)
    llamadas = []
    original_verificar, original_hashear = modulo.verificar_password, modulo.hashear_password
    async def verificar(*args, **kwargs):
        llamadas.append("verificar")
        return await original_verificar(*args, **kwargs)
    async def hashear(*args, **kwargs):
        llamadas.append("hashear")
        return await original_hashear(*args, **kwargs)
    monkeypatch.setattr(modulo, "verificar_password", verificar)
    monkeypatch.setattr(modulo, "hashear_password", hashear)
    for invalido in ["a" * 73, "ñ" * 36 + "a", "", "abc\x00"]:
        r = await cliente.post(ruta, json={**datos, campo: invalido})
        assert r.status_code == 422
    r = await cliente.post(ruta, json={**datos, "rol": "ADMIN"})
    assert r.status_code == 422
    assert llamadas == []
    assert await foto_auth(base_sembrada) == antes
