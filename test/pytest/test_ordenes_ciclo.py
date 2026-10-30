"""C-11, C-12 y C-13: ciclo transaccional de órdenes."""

import asyncio

import pytest
from sqlalchemy import text

from test_ordenes_catalogo import autenticar


async def test_iniciar_asigna_mecanico_y_agrega_historial(cliente, base_sembrada):
    autenticar(cliente, 4)
    respuesta = await cliente.post("/ordenes/1/iniciar")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "EN_REPARACION"
    assert respuesta.json()["mecanico_id"] == 4
    assert respuesta.json()["historial"][-1]["hasta_estado"] == "EN_REPARACION"


async def test_iniciar_orden_no_pendiente_da_409(cliente, base_sembrada):
    autenticar(cliente, 4)
    respuesta = await cliente.post("/ordenes/2/iniciar")
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "La orden no está en un estado que permita esta operación"


async def test_terminar_mecanico_no_asignado_da_403(cliente, base_sembrada):
    autenticar(cliente, 5)
    respuesta = await cliente.post("/ordenes/2/terminar")
    assert respuesta.status_code == 403
    assert respuesta.json()["detail"] == "Solo el mecánico asignado o un administrador pueden terminar la orden"


async def test_c11_terminar_sin_stock_revierte_todo(cliente, base_sembrada):
    autenticar(cliente, 4)
    async with base_sembrada() as sesion:
        antes = {
            tabla: (await sesion.exec(text(f"SELECT * FROM {tabla} ORDER BY id"))).all()
            for tabla in ("orden_trabajo", "repuesto", "movimiento_stock", "historial_estado_orden")
        }
    respuesta = await cliente.post("/ordenes/2/terminar")
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Stock insuficiente para el repuesto BUJ-020"
    async with base_sembrada() as sesion:
        despues = {
            tabla: (await sesion.exec(text(f"SELECT * FROM {tabla} ORDER BY id"))).all()
            for tabla in ("orden_trabajo", "repuesto", "movimiento_stock", "historial_estado_orden")
        }
    assert despues == antes


async def test_c12_reponer_terminar_y_avisar(cliente, base_sembrada, caplog):
    autenticar(cliente, 1)
    assert (await cliente.post("/repuestos/3/reponer", json={"cantidad": 2})).status_code == 200
    with caplog.at_level("INFO"):
        respuesta = await cliente.post("/ordenes/2/terminar")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "TERMINADA"
    assert respuesta.json()["historial"][-1]["hasta_estado"] == "TERMINADA"
    assert any("orden_id=2" in registro.message and "cliente_id=2" in registro.message for registro in caplog.records)
    async with base_sembrada() as sesion:
        stock = (await sesion.exec(text("SELECT stock FROM repuesto WHERE id = 3"))).scalar_one()
        movimiento = (
            await sesion.exec(
                text("SELECT cantidad, motivo, orden_id FROM movimiento_stock "
                     "WHERE repuesto_id = 3 ORDER BY id DESC LIMIT 1")
            )
        ).one()
    assert stock == 0
    assert movimiento == (-4, "Orden terminada", 2)


async def test_c13_dueno_cancela_orden_pendiente(cliente, base_sembrada):
    autenticar(cliente, 6)
    respuesta = await cliente.post("/ordenes/1/cancelar")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "CANCELADA"
    async with base_sembrada() as sesion:
        assert (await sesion.exec(text("SELECT stock FROM repuesto WHERE id = 1"))).scalar_one() == 10
        assert (await sesion.exec(text("SELECT count(*) FROM movimiento_stock WHERE orden_id = 1"))).scalar_one() == 0


async def test_c13_orden_ajena_da_403(cliente, base_sembrada):
    autenticar(cliente, 7)
    respuesta = await cliente.post("/ordenes/1/cancelar")
    assert respuesta.status_code == 403


async def test_c13_orden_terminada_no_se_cancela(cliente, base_sembrada):
    autenticar(cliente, 1)
    await cliente.post("/repuestos/3/reponer", json={"cantidad": 2})
    assert (await cliente.post("/ordenes/2/terminar")).status_code == 200
    respuesta = await cliente.post("/ordenes/2/cancelar")
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "La orden no está en un estado que permita esta operación"


async def test_dos_terminaciones_concurrentes_solo_descuentan_una(crear_cliente, base_sembrada):
    async with crear_cliente() as primero, crear_cliente() as segundo:
        autenticar(primero, 1)
        autenticar(segundo, 1)
        await primero.post("/repuestos/3/reponer", json={"cantidad": 2})
        respuestas = await asyncio.gather(
            primero.post("/ordenes/2/terminar"),
            segundo.post("/ordenes/2/terminar"),
        )
    assert sorted(respuesta.status_code for respuesta in respuestas) == [200, 409]
    async with base_sembrada() as sesion:
        assert (await sesion.exec(text("SELECT stock FROM repuesto WHERE id = 3"))).scalar_one() == 0
        assert (await sesion.exec(text(
            "SELECT count(*) FROM movimiento_stock WHERE orden_id = 2 AND motivo = 'Orden terminada'"
        ))).scalar_one() == 1


async def test_transiciones_requieren_sesion(cliente, base_sembrada):
    for ruta in ("/ordenes/1/iniciar", "/ordenes/1/terminar", "/ordenes/1/cancelar"):
        assert (await cliente.post(ruta)).status_code == 401


async def test_repuesto_dado_de_baja_se_descuenta_al_terminar(cliente, base_sembrada):
    autenticar(cliente, 1)
    async with base_sembrada() as sesion:
        await sesion.exec(text("UPDATE repuesto SET stock = 4, borrado_en = now() WHERE id = 3"))
        await sesion.commit()
    respuesta = await cliente.post("/ordenes/2/terminar")
    assert respuesta.status_code == 200
    async with base_sembrada() as sesion:
        stock = (await sesion.exec(text("SELECT stock FROM repuesto WHERE id = 3"))).scalar_one()
        movimiento = (await sesion.exec(text(
            "SELECT cantidad, motivo, orden_id FROM movimiento_stock "
            "WHERE repuesto_id = 3 ORDER BY id DESC LIMIT 1"
        ))).one()
    assert stock == 0
    assert movimiento == (-4, "Orden terminada", 2)


async def test_falla_del_aviso_no_afecta_terminacion(cliente, base_sembrada, monkeypatch):
    autenticar(cliente, 1)
    await cliente.post("/repuestos/3/reponer", json={"cantidad": 2})

    async def aviso_fallido(orden_id, cliente_id):
        raise RuntimeError("fallo simulado")

    import app.modules.ordenes.service as service_module
    monkeypatch.setattr(service_module, "enviar_aviso", aviso_fallido)
    respuesta = await cliente.post("/ordenes/2/terminar")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "TERMINADA"
    async with base_sembrada() as sesion:
        assert (await sesion.exec(text("SELECT stock FROM repuesto WHERE id = 3"))).scalar_one() == 0


@pytest.mark.parametrize(
    ("ruta", "usuario"),
    [
        ("/ordenes/999999/iniciar", 4),
        ("/ordenes/999999/terminar", 1),
        ("/ordenes/999999/cancelar", 6),
    ],
)
async def test_orden_inexistente_en_transicion_da_404(cliente, base_sembrada, ruta, usuario):
    autenticar(cliente, usuario)
    assert (await cliente.post(ruta)).status_code == 404


async def test_ordenes_distintas_compiten_por_un_stock(crear_cliente, base_sembrada):
    async with crear_cliente() as recepcion, crear_cliente() as mecanico, crear_cliente() as admin:
        autenticar(recepcion, 3)
        autenticar(mecanico, 4)
        autenticar(admin, 1)
        alta = await recepcion.post("/ordenes", json={
            "vehiculo_id": 2,
            "falla": "Misma pieza",
            "items": [{"repuesto_id": 1, "cantidad": 1}],
        })
        assert alta.status_code == 201
        assert (await mecanico.post("/ordenes/1/iniciar")).status_code == 200
        assert (await mecanico.post("/ordenes/3/iniciar")).status_code == 200
    async with base_sembrada() as sesion:
        await sesion.exec(text("UPDATE repuesto SET stock = 1 WHERE id = 1"))
        await sesion.commit()
    async with crear_cliente() as primero, crear_cliente() as segundo:
        autenticar(primero, 1)
        autenticar(segundo, 1)
        respuestas = await asyncio.gather(
            primero.post("/ordenes/1/terminar"),
            segundo.post("/ordenes/3/terminar"),
        )
    assert sorted(respuesta.status_code for respuesta in respuestas) == [200, 409]
    async with base_sembrada() as sesion:
        assert (await sesion.exec(text("SELECT stock FROM repuesto WHERE id = 1"))).scalar_one() == 0
        assert (await sesion.exec(text("SELECT min(stock) FROM repuesto WHERE id = 1"))).scalar_one() >= 0
