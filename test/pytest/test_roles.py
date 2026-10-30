"""RO/RV/HI: contratos de roles, historial y transacciones PostgreSQL reales."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import event, text

from app.core.errores import Conflicto
from app.modules.usuarios.models import EventoSeguridad
from auth_helpers import foto_auth
from test_autorizacion import cookie


@pytest.mark.parametrize("fecha", ["omitida", None, "2099-01-01T12:00:00-03:00"])
async def test_ro1_asigna_con_autoria_y_evento(cliente, base_sembrada, fecha):
    cookie(cliente)
    antes = await foto_auth(base_sembrada)
    datos = {"rol": "MECANICO"}
    if fecha != "omitida":
        datos["vence_en"] = fecha
    r = await cliente.post("/usuarios/6/roles", json=datos)
    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["usuario_id"] == 6 and cuerpo["rol"] == "MECANICO" and cuerpo["vigente"] is True
    assert cuerpo["otorgada_por"] == 1 and cuerpo["revocada_en"] is None
    assert datetime.fromisoformat(cuerpo["desde"]).tzinfo is not None
    assert cuerpo["vence_en"] is None if fecha in (None, "omitida") else datetime.fromisoformat(cuerpo["vence_en"]) == datetime.fromisoformat(fecha)
    despues = await foto_auth(base_sembrada)
    assert len(despues["asignacion_rol"]) == len(antes["asignacion_rol"])+1
    assert len(despues["evento_seguridad"]) == len(antes["evento_seguridad"])+1
    assert despues["evento_seguridad"][-1].actor == "admin@example.com"
    assert despues["evento_seguridad"][-1].accion == "Asignación de rol MECANICO a cliente@example.com"


async def test_ro4_duplicado_vigente_409(cliente, base_sembrada):
    cookie(cliente)
    antes = await foto_auth(base_sembrada)
    r = await cliente.post("/usuarios/4/roles", json={"rol": "MECANICO"})
    assert r.status_code == 409 and r.json() == {"detail": "El usuario ya tiene ese rol vigente"}
    assert await foto_auth(base_sembrada) == antes


async def test_ro3_asignar_usuario_inexistente(cliente, base_sembrada):
    cookie(cliente)
    antes = await foto_auth(base_sembrada)
    r = await cliente.post("/usuarios/99999/roles", json={"rol": "MECANICO"})
    assert r.status_code == 404 and r.json() == {"detail": "Usuario no encontrado"}
    assert await foto_auth(base_sembrada) == antes


@pytest.mark.parametrize("datos", [{"rol": "CLIENTE"}, {"rol": "JEFE"}, {"rol": "ADMIN", "otorgada_por": 2},
    {"rol": "ADMIN", "vence_en": "2000-01-01T00:00:00Z"}, {"rol": "ADMIN", "vence_en": "2099-01-01T00:00:00"}])
async def test_ro2_pe4_pe5_asignacion_422_sin_filas(cliente, base_sembrada, datos):
    cookie(cliente)
    antes = await foto_auth(base_sembrada)
    assert (await cliente.post("/usuarios/6/roles", json=datos)).status_code == 422
    assert await foto_auth(base_sembrada) == antes


async def test_ro6_asigna_tras_revocacion(cliente, base_sembrada):
    cookie(cliente)
    async with base_sembrada() as s:
        await s.exec(text("UPDATE asignacion_rol SET revocada_en=:fecha WHERE usuario_id=4").bindparams(fecha=datetime.now(UTC)))
        await s.commit()
    antes = await foto_auth(base_sembrada)
    r = await cliente.post("/usuarios/4/roles", json={"rol": "MECANICO"})
    assert r.status_code == 201
    despues = await foto_auth(base_sembrada)
    assert despues["asignacion_rol"][:-1] == antes["asignacion_rol"]
    assert despues["asignacion_rol"][-1].id != antes["asignacion_rol"][3].id


@pytest.mark.parametrize("fallo", [False, True])
async def test_ro5_ro7_reasigna_vencido_o_revierte(cliente, base_sembrada, fallo):
    cookie(cliente)
    async with base_sembrada() as s:
        await s.exec(text("UPDATE asignacion_rol SET vence_en=:fecha, otorgada_por=2 WHERE usuario_id=4").bindparams(fecha=datetime.now(UTC)-timedelta(days=1)))
        await s.commit()
    antes = await foto_auth(base_sembrada)
    eventos_intentados = []
    def fallar(mapper, connection, target):
        eventos_intentados.append(target.accion)
        raise Conflicto("Fallo controlado del evento")
    if fallo:
        event.listen(EventoSeguridad, "before_insert", fallar)
    try:
        r = await cliente.post("/usuarios/4/roles", json={"rol": "MECANICO"})
    finally:
        if fallo:
            event.remove(EventoSeguridad, "before_insert", fallar)
    despues = await foto_auth(base_sembrada)
    if fallo:
        assert eventos_intentados == ["Asignación de rol MECANICO a mecanico@example.com"]
        assert r.status_code == 409 and despues == antes
    else:
        assert r.status_code == 201
        vieja = next(a for a in despues["asignacion_rol"] if a.usuario_id == 4 and a.id != r.json()["id"])
        assert vieja.revocada_en is not None and vieja.otorgada_por == 2
        assert r.json()["otorgada_por"] == 1
        assert len(despues["evento_seguridad"]) == len(antes["evento_seguridad"])+1
        assert despues["evento_seguridad"][-1].accion == "Asignación de rol MECANICO a mecanico@example.com"


async def test_hi1_historial_mixto_con_cliente_y_orden(cliente, base_sembrada):
    cookie(cliente)
    ahora = datetime.now(UTC)
    async with base_sembrada() as s:
        await s.exec(text("UPDATE asignacion_rol SET desde=:desde WHERE usuario_id=6").bindparams(desde=ahora-timedelta(days=2)))
        await s.exec(text("""INSERT INTO asignacion_rol(usuario_id,rol,desde,vence_en,revocada_en,otorgada_por)
            VALUES(6,'RECEPCION',:desde,:vence,NULL,1),(6,'MECANICO',:desde,NULL,:vence,2)""").bindparams(
                desde=ahora-timedelta(days=1), vence=ahora-timedelta(hours=1)))
        await s.commit()
    r = await cliente.get("/usuarios/6/roles")
    assert r.status_code == 200
    filas = r.json()
    assert [f["rol"] for f in filas] == ["CLIENTE", "RECEPCION", "MECANICO"]
    assert [f["vigente"] for f in filas] == [True, False, False]
    assert [f["otorgada_por"] for f in filas] == [None, 1, 2]
    assert all(set(f) == {"id","usuario_id","rol","desde","vence_en","revocada_en","otorgada_por","vigente"} for f in filas)
    assert all(datetime.fromisoformat(f["desde"]).tzinfo is not None for f in filas)


async def test_hi2_historial_vacio_y_igualdad(cliente, base_sembrada, monkeypatch):
    import app.modules.usuarios.service as servicios
    ahora = datetime.now(UTC)
    class Reloj(datetime):
        @classmethod
        def now(cls, tz=None):
            return ahora
    monkeypatch.setattr(servicios, "datetime", Reloj)
    async with base_sembrada() as s:
        await s.exec(text("INSERT INTO usuario(email,nombre,password_hash,activo,debe_cambiar_password) VALUES('sinrol@example.com','Sin rol','hash',true,false)"))
        sin_rol = (await s.exec(text("SELECT id FROM usuario WHERE email='sinrol@example.com'"))).one().id
        await s.exec(text("UPDATE asignacion_rol SET vence_en=:ahora WHERE usuario_id=6").bindparams(ahora=ahora))
        await s.commit()
    cookie(cliente)
    r = await cliente.get(f"/usuarios/{sin_rol}/roles")
    assert r.status_code == 200 and r.json() == []
    r = await cliente.get("/usuarios/6/roles")
    assert r.status_code == 200 and r.json()[0]["vigente"] is False


async def test_ro3_historial_usuario_inexistente(cliente, base_sembrada):
    cookie(cliente)
    r = await cliente.get("/usuarios/99999/roles")
    assert r.status_code == 404 and r.json() == {"detail": "Usuario no encontrado"}


@pytest.mark.parametrize("vencida,fallo", [(False, False), (True, False), (False, True)])
async def test_rv1_rv3_rv4_revoca_con_historia_o_rollback(cliente, base_sembrada, vencida, fallo):
    cookie(cliente)
    async with base_sembrada() as s:
        await s.exec(text("UPDATE asignacion_rol SET otorgada_por=2, vence_en=:vence WHERE usuario_id=4").bindparams(
            vence=datetime.now(UTC)-timedelta(days=1) if vencida else None))
        await s.commit()
    antes = await foto_auth(base_sembrada)
    intentados = []
    def fallar(mapper, connection, target):
        intentados.append(target.accion)
        raise Conflicto("Fallo controlado del evento")
    if fallo:
        event.listen(EventoSeguridad, "before_insert", fallar)
    try:
        r = await cliente.delete("/usuarios/4/roles/MECANICO")
    finally:
        if fallo:
            event.remove(EventoSeguridad, "before_insert", fallar)
    despues = await foto_auth(base_sembrada)
    if fallo:
        assert intentados == ["Revocación de rol MECANICO a mecanico@example.com"]
        assert r.status_code == 409 and despues == antes
    else:
        assert r.status_code == 200
        cuerpo = r.json()
        assert cuerpo["id"] == antes["asignacion_rol"][3].id
        assert cuerpo["vigente"] is False and cuerpo["revocada_en"] is not None and cuerpo["otorgada_por"] == 2
        historia = await cliente.get("/usuarios/4/roles")
        assert historia.json() == [cuerpo]
        assert despues["evento_seguridad"][-1].actor == "admin@example.com"
        assert despues["evento_seguridad"][-1].accion == "Revocación de rol MECANICO a mecanico@example.com"
        assert len(despues["asignacion_rol"]) == len(antes["asignacion_rol"])


@pytest.mark.parametrize("revocado", [False, True])
async def test_rv2_ausencia_asignacion_abierta(cliente, base_sembrada, revocado):
    cookie(cliente)
    if revocado:
        async with base_sembrada() as s:
            await s.exec(text("UPDATE asignacion_rol SET revocada_en=:fecha WHERE usuario_id=4").bindparams(fecha=datetime.now(UTC)))
            await s.commit()
    antes = await foto_auth(base_sembrada)
    r = await cliente.delete(f"/usuarios/4/roles/{'MECANICO' if revocado else 'RECEPCION'}")
    assert r.status_code == 404 and r.json() == {"detail": "No hay una asignación abierta de ese rol"}
    assert await foto_auth(base_sembrada) == antes


async def test_ro3_revocar_usuario_inexistente(cliente, base_sembrada):
    cookie(cliente)
    r = await cliente.delete("/usuarios/99999/roles/MECANICO")
    assert r.status_code == 404 and r.json() == {"detail": "Usuario no encontrado"}
