"""Registro por API y atomicidad observada en una sesión independiente (C-02)."""

from auth_helpers import REGISTRO, foto_auth
import pytest
from sqlalchemy import event
from app.modules.usuarios.models import EventoSeguridad


async def test_r1_registro_crea_cuatro_filas(cliente, base_sembrada):
    antes = await foto_auth(base_sembrada)
    respuesta = await cliente.post("/auth/registro", json=REGISTRO)
    assert respuesta.status_code == 201
    assert "password" not in respuesta.text
    despues = await foto_auth(base_sembrada)
    assert {t: len(despues[t]) - len(antes[t]) for t in antes} == {
        "usuario": 1, "asignacion_rol": 1, "cliente": 1, "evento_seguridad": 1}
    usuario = despues["usuario"][-1]
    assert usuario.email == REGISTRO["email"] and usuario.activo and not usuario.debe_cambiar_password
    assert despues["cliente"][-1].usuario_id == usuario.id
    assert despues["asignacion_rol"][-1].rol == "CLIENTE"
    assert despues["asignacion_rol"][-1].otorgada_por is None
    assert despues["evento_seguridad"][-1].accion == "Registro de cliente alta@example.com"


@pytest.mark.parametrize("cambios,mensaje", [
    ({"email": "admin@example.com"}, "El correo ya está registrado"),
    ({"documento": "30111222"}, "El documento ya está registrado"),
    ({"documento": "28333444"}, "El documento ya está registrado"),
])
async def test_r2_r3_r4_duplicado_no_deja_filas(cliente, base_sembrada, cambios, mensaje):
    antes = await foto_auth(base_sembrada)
    respuesta = await cliente.post("/auth/registro", json={**REGISTRO, **cambios})
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detail": mensaje}
    assert await foto_auth(base_sembrada) == antes


async def test_r5_fallo_tardio_revierte_todas_las_filas(cliente, base_sembrada):
    antes = await foto_auth(base_sembrada)

    def fallar(mapper, connection, target):
        raise ValueError("fallo controlado antes del evento")

    event.listen(EventoSeguridad, "before_insert", fallar)
    try:
        with pytest.raises(ValueError, match="fallo controlado"):
            await cliente.post("/auth/registro", json=REGISTRO)
    finally:
        event.remove(EventoSeguridad, "before_insert", fallar)
    assert await foto_auth(base_sembrada) == antes
