"""PE1-7: alta de personal por API y sus tres escrituras atómicas."""

import asyncio

import pytest
from sqlalchemy import event

from app.core.errores import Conflicto
from app.core.security import verificar_password
from app.modules.usuarios.models import EventoSeguridad
from auth_helpers import foto_auth
from test_autorizacion import cookie
from test_personal_schemas import ALTA


@pytest.mark.parametrize("rol", ["ADMIN", "RECEPCION", "MECANICO"])
async def test_pe1_alta_tres_filas_respuesta_sin_secretos(cliente, base_sembrada, rol):
    cookie(cliente)
    antes = await foto_auth(base_sembrada)
    r = await cliente.post("/usuarios", json={**ALTA, "rol": rol})
    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo == {"id": cuerpo["id"], "email": ALTA["email"], "nombre": ALTA["nombre"],
                      "activo": True, "debe_cambiar_password": True}
    despues = await foto_auth(base_sembrada)
    assert {t: len(despues[t])-len(antes[t]) for t in antes} == {
        "usuario": 1, "asignacion_rol": 1, "cliente": 0, "evento_seguridad": 1}
    usuario, asignacion, evento = (despues[t][-1] for t in ("usuario", "asignacion_rol", "evento_seguridad"))
    assert await verificar_password(ALTA["password_provisoria"], usuario.password_hash, semaforo=asyncio.Semaphore(1))
    assert asignacion.usuario_id == usuario.id == cuerpo["id"]
    assert asignacion.rol == rol and asignacion.otorgada_por == 1 and asignacion.vence_en is None
    assert evento.actor == "admin@example.com" and evento.accion == "Alta de personal personal@example.com"


async def test_pe2_correo_duplicado_sin_filas(cliente, base_sembrada):
    cookie(cliente)
    antes = await foto_auth(base_sembrada)
    r = await cliente.post("/usuarios", json={**ALTA, "email": "admin@example.com"})
    assert r.status_code == 409 and r.json() == {"detail": "El correo ya está registrado"}
    assert await foto_auth(base_sembrada) == antes


async def test_pe3_alta_rollback_del_evento(cliente, base_sembrada):
    cookie(cliente)
    antes = await foto_auth(base_sembrada)
    def fallar(mapper, connection, target):
        raise Conflicto("Fallo controlado del evento")
    event.listen(EventoSeguridad, "before_insert", fallar)
    try:
        r = await cliente.post("/usuarios", json=ALTA)
    finally:
        event.remove(EventoSeguridad, "before_insert", fallar)
    assert r.status_code == 409
    assert await foto_auth(base_sembrada) == antes


@pytest.mark.parametrize("cambios", [{"rol": "CLIENTE"}, {"rol": "JEFE"}, {"activo": False},
    {"password_provisoria": "a"*73}, {"password_provisoria": "ñ"*36+"a"},
    {"password_provisoria": ""}, {"password_provisoria": "clave\x00"}])
async def test_pe4_pe5_pe6_pe7_422_sin_bcrypt(cliente, base_sembrada, monkeypatch, cambios):
    import app.modules.usuarios.service as servicios
    cookie(cliente)
    antes = await foto_auth(base_sembrada)
    llamadas = []
    original = servicios.hashear_password
    async def observar(*args, **kwargs):
        llamadas.append(True)
        return await original(*args, **kwargs)
    monkeypatch.setattr(servicios, "hashear_password", observar)
    assert (await cliente.post("/usuarios", json={**ALTA, **cambios})).status_code == 422
    assert llamadas == [] and await foto_auth(base_sembrada) == antes
