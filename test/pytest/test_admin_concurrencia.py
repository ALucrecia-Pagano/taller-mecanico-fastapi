"""CO1-4: coordinación con conexiones PostgreSQL reales, sin sleeps ni mocks DB."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import event, text

from app.core.config import get_settings
from app.core.errores import Conflicto
from app.core.security import emitir_token
from app.modules.usuarios.models import EventoSeguridad
from app.modules.usuarios.repository import CLAVE_BLOQUEO_ADMIN
from auth_helpers import foto_auth
from test_personal_schemas import ALTA


def sesion(usuario):
    return {"Cookie": "access_token="+emitir_token(usuario, ["ADMIN"], settings=get_settings())}


async def esperar_bloqueados(conexion, cantidad):
    # Observar espera real en PostgreSQL, no asumirla por haber creado tasks de asyncio.
    async with asyncio.timeout(10):
        while True:
            n = (await conexion.exec(text("""SELECT count(*) FROM pg_locks WHERE locktype='advisory'
                AND objid=:clave AND NOT granted AND database=(SELECT oid FROM pg_database WHERE datname=current_database())""")
                .bindparams(clave=CLAVE_BLOQUEO_ADMIN))).one().count
            if n == cantidad:
                return


async def bloquear(conexion):
    await conexion.exec(text("SELECT pg_advisory_xact_lock(:clave)").bindparams(clave=CLAVE_BLOQUEO_ADMIN))


async def test_co1_dos_admins_revocan_cruzado(cliente, base_sembrada):
    antes = await foto_auth(base_sembrada)
    tareas = []
    try:
        async with base_sembrada() as barrera:
            await bloquear(barrera)
            tareas.append(asyncio.create_task(cliente.delete("/usuarios/2/roles/ADMIN", headers=sesion(1))))
            await esperar_bloqueados(barrera, 1)
            tareas.append(asyncio.create_task(cliente.delete("/usuarios/1/roles/ADMIN", headers=sesion(2))))
            await esperar_bloqueados(barrera, 2)
            await barrera.commit()
        respuestas = await asyncio.wait_for(asyncio.gather(*tareas), 10)
    finally:
        for tarea in tareas:
            if not tarea.done():
                tarea.cancel()
        await asyncio.gather(*tareas, return_exceptions=True)
    assert [r.status_code for r in respuestas] == [200, 403]
    assert respuestas[1].json() == {"detail": "No tiene permisos para realizar esta operación"}
    despues = await foto_auth(base_sembrada)
    assert [a.usuario_id for a in despues["asignacion_rol"] if a.rol == "ADMIN" and a.revocada_en is None] == [1]
    assert len(despues["evento_seguridad"]) == len(antes["evento_seguridad"])+1


@pytest.mark.parametrize("operacion", ["revocar", "alta", "asignar", "reasignar"])
async def test_co2_co3_actor_pierde_admin_esperando(cliente, base_sembrada, operacion):
    if operacion == "reasignar":
        async with base_sembrada() as s:
            await s.exec(text("INSERT INTO asignacion_rol(usuario_id,rol,vence_en) VALUES(6,'ADMIN',:fecha)").bindparams(fecha=datetime.now(UTC)-timedelta(days=1)))
            await s.commit()
    tarea = None
    try:
        async with base_sembrada() as barrera:
            await bloquear(barrera)
            if operacion == "revocar":
                pedido = cliente.delete("/usuarios/2/roles/ADMIN", headers=sesion(1))
            elif operacion == "alta":
                pedido = cliente.post("/usuarios", headers=sesion(1), json={**ALTA, "rol": "ADMIN"})
            else:
                pedido = cliente.post("/usuarios/6/roles", headers=sesion(1), json={"rol": "ADMIN"})
            tarea = asyncio.create_task(pedido)
            await esperar_bloqueados(barrera, 1)
            await barrera.exec(text("UPDATE asignacion_rol SET revocada_en=:fecha WHERE usuario_id=1 AND rol='ADMIN'").bindparams(fecha=datetime.now(UTC)))
            await barrera.commit()
        antes = await foto_auth(base_sembrada)
        r = await asyncio.wait_for(tarea, 10)
        assert r.status_code == 403 and r.json() == {"detail": "No tiene permisos para realizar esta operación"}
        assert await foto_auth(base_sembrada) == antes
    finally:
        if tarea is not None and not tarea.done():
            tarea.cancel()
            await asyncio.gather(tarea, return_exceptions=True)


async def test_co4_rollback_libera_lock_y_segundo_completa(cliente, base_sembrada):
    antes = await foto_auth(base_sembrada)
    def fallar_primero(mapper, connection, target):
        if target.actor == "admin@example.com":
            raise Conflicto("Fallo controlado del primer ADMIN")
    event.listen(EventoSeguridad, "before_insert", fallar_primero)
    tareas = []
    try:
        async with base_sembrada() as barrera:
            await bloquear(barrera)
            tareas.append(asyncio.create_task(cliente.post("/usuarios/6/roles", json={"rol": "ADMIN"}, headers=sesion(1))))
            await esperar_bloqueados(barrera, 1)
            tareas.append(asyncio.create_task(cliente.post("/usuarios/4/roles", json={"rol": "ADMIN"}, headers=sesion(2))))
            await esperar_bloqueados(barrera, 2)
            await barrera.commit()
        respuestas = await asyncio.wait_for(asyncio.gather(*tareas), 10)
    finally:
        event.remove(EventoSeguridad, "before_insert", fallar_primero)
        for tarea in tareas:
            if not tarea.done():
                tarea.cancel()
        await asyncio.gather(*tareas, return_exceptions=True)
    assert [r.status_code for r in respuestas] == [409, 201]
    despues = await foto_auth(base_sembrada)
    nuevas = despues["asignacion_rol"][len(antes["asignacion_rol"]):]
    assert len(nuevas) == 1 and nuevas[0].usuario_id == 4 and nuevas[0].otorgada_por == 2
    assert len(despues["evento_seguridad"]) == len(antes["evento_seguridad"])+1
