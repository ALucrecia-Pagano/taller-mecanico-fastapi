"""Conteo e intento independiente contra PostgreSQL real (I1-I8)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import event, text

from app.modules.usuarios.unit_of_work import IntentosUnitOfWork, RegistroIntentos
from app.modules.usuarios.repository import IntentoAccesoRepository
from app.core.errores import LimiteDeIntentos
from app.modules.usuarios.service import verificar_limite_intentos


async def test_i1_cinco_fallos_bloquean_y_no_agregan(base_sembrada):
    ahora = datetime.now(UTC)
    registrar = RegistroIntentos(base_sembrada, IntentosUnitOfWork)
    for _ in range(5):
        await registrar("limitado@example.com", "127.0.0.1", False, ahora)
    async with base_sembrada() as sesion:
        with pytest.raises(LimiteDeIntentos):
            await verificar_limite_intentos(IntentoAccesoRepository(sesion), "limitado@example.com", "127.0.0.1", ahora, 5, 60)
        assert (await sesion.exec(text("SELECT count(*) FROM intento_acceso"))).one().count == 5


@pytest.mark.parametrize("exito", [True, False])
async def test_i7_i8_intento_persistido_aunque_peticion_revierte(base_sembrada, exito):
    registrar = RegistroIntentos(base_sembrada, IntentosUnitOfWork)
    async with base_sembrada() as peticion:
        await peticion.exec(text("UPDATE usuario SET nombre='Sin confirmar' WHERE id=1"))
        await registrar("persona@example.com", "127.0.0.1", exito, datetime.now(UTC))
        await peticion.rollback()
    async with base_sembrada() as otra:
        intento = (await otra.exec(text("SELECT * FROM intento_acceso"))).one()
        assert intento.email == "persona@example.com" and intento.exito == exito
        assert (await otra.exec(text("SELECT nombre FROM usuario WHERE id=1"))).one().nombre == "Ana Admin"


async def test_i2_i3_redondeo_consulta_unica_y_borde(base_sembrada):
    ahora = datetime.now(UTC)
    registrar = RegistroIntentos(base_sembrada, IntentosUnitOfWork)
    for _ in range(5):
        await registrar("limite@example.com", "127.0.0.1", False, ahora - timedelta(seconds=58.8))
    sentencias = []
    def contar(conn, cursor, statement, parameters, context, executemany):
        sentencias.append(statement)
    engine = base_sembrada.kw["bind"].sync_engine
    event.listen(engine, "before_cursor_execute", contar)
    try:
        async with base_sembrada() as s:
            with pytest.raises(LimiteDeIntentos) as error:
                await verificar_limite_intentos(IntentoAccesoRepository(s), "limite@example.com", "127.0.0.1", ahora, 5, 60)
            assert error.value.segundos == 2
            assert len(sentencias) == 1
            await verificar_limite_intentos(IntentoAccesoRepository(s), "limite@example.com", "127.0.0.1", ahora + timedelta(seconds=1.2), 5, 60)
    finally:
        event.remove(engine, "before_cursor_execute", contar)


async def test_i4_exito_reinicia_sin_borrar(base_sembrada):
    ahora = datetime.now(UTC)
    registrar = RegistroIntentos(base_sembrada, IntentosUnitOfWork)
    for _ in range(4):
        await registrar("reinicio@example.com", "127.0.0.1", False, ahora)
    await registrar("reinicio@example.com", "127.0.0.1", True, ahora + timedelta(seconds=1))
    await registrar("reinicio@example.com", "127.0.0.1", False, ahora + timedelta(seconds=2))
    async with base_sembrada() as s:
        estado = await IntentoAccesoRepository(s).fallos_desde_ultimo_exito("reinicio@example.com", "127.0.0.1", ahora-timedelta(seconds=60), 5)
        assert estado.cantidad == 1
        assert (await s.exec(text("SELECT count(*) FROM intento_acceso"))).one().count == 6


@pytest.mark.parametrize("email,ip", [("otro@example.com", "127.0.0.1"), ("bloqueado@example.com", "127.0.0.2")])
async def test_i5_pares_independientes(base_sembrada, email, ip):
    ahora = datetime.now(UTC)
    registrar = RegistroIntentos(base_sembrada, IntentosUnitOfWork)
    for _ in range(5):
        await registrar("bloqueado@example.com", "127.0.0.1", False, ahora)
    async with base_sembrada() as s:
        await verificar_limite_intentos(IntentoAccesoRepository(s), email, ip, ahora, 5, 60)
