"""Detalle autorizado, histórico y SQL real de C-15."""

import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text

from test_ordenes_alta import cuerpo_orden
from test_ordenes_catalogo import autenticar


@pytest.mark.parametrize("usuario,orden_id,codigo", [(6, 1, 200), (6, 2, 403), (1, 1, 200), (1, 2, 200),
    (3, 1, 200), (3, 2, 200), (4, 1, 200), (4, 2, 200), (5, 2, 200), (6, 999999, 404)])
async def test_detalle_personal_dueno_ajeno_e_inexistente(cliente, base_sembrada, usuario, orden_id, codigo):
    autenticar(cliente, usuario)
    respuesta = await cliente.get(f"/ordenes/{orden_id}")
    assert respuesta.status_code == codigo
    if codigo == 404:
        assert respuesta.json() == {"detail": "Orden no encontrada"}
    if codigo == 403:
        assert respuesta.json() == {"detail": "No tiene permisos para realizar esta operación"}


async def test_detalle_sin_ficha_ni_rol_personal_403(cliente, base_sembrada):
    async with base_sembrada() as s:
        await s.exec(text("UPDATE asignacion_rol SET revocada_en=now() WHERE usuario_id=5"))
        await s.commit()
    autenticar(cliente, 5, ["MECANICO"])
    assert (await cliente.get("/ordenes/1")).status_code == 403


async def test_detalle_historial_empate_y_formato(cliente, base_sembrada):
    autenticar(cliente, 4)
    respuesta = await cliente.get("/ordenes/2")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert [(h["desde_estado"], h["hasta_estado"], h["usuario_id"]) for h in datos["historial"]] == [
        (None, "PENDIENTE", 3), ("PENDIENTE", "EN_REPARACION", 4)]
    assert datos["historial"][0]["cuando"] == datos["historial"][1]["cuando"]
    assert all(set(h) == {"desde_estado", "hasta_estado", "usuario_id", "cuando"} for h in datos["historial"])
    assert set(datos) == {"id", "estado", "patente", "total", "creada_en", "mecanico_id", "falla", "cliente", "items", "historial"}
    assert "password_hash" not in respuesta.text


async def test_detalle_conserva_repuesto_baja_y_precio_copiado(cliente, base_sembrada):
    autenticar(cliente, 1)
    assert (await cliente.patch("/repuestos/1", json={"precio": "1.00"})).status_code == 200
    assert (await cliente.delete("/repuestos/1")).status_code == 204
    detalle = await cliente.get("/ordenes/1")
    assert detalle.status_code == 200
    assert detalle.json()["total"] == "56500.00"
    assert detalle.json()["items"][0]["precio_unitario"] == "8500.00"


async def test_detalle_conserva_vehiculo_finalizado_dado_baja(cliente, base_sembrada):
    # Preparación de estado final de fixture; las transiciones públicas pertenecen a CH-10.
    async with base_sembrada() as s:
        await s.exec(text("UPDATE orden_trabajo SET estado='TERMINADA' WHERE id=1"))
        await s.commit()
    autenticar(cliente, 1)
    assert (await cliente.delete("/vehiculos/1")).status_code == 204
    autenticar(cliente, 6)
    respuesta = await cliente.get("/ordenes/1")
    assert respuesta.status_code == 200
    assert respuesta.json()["patente"] == "AB123CD"
    assert respuesta.json()["cliente"] == "Laura Cliente"


async def test_c15_sql_real_dos_y_cuatro_items_consultas_fijas(cliente, base_sembrada):
    from main import app
    autenticar(cliente, 1)
    cuatro = await cliente.post("/ordenes", json=cuerpo_orden(items=[{"repuesto_id": i, "cantidad": 1} for i in (1, 2, 3, 4)]))
    assert cuatro.status_code == 201
    mediciones = []
    for orden_id, cantidad in ((1, 2), (cuatro.json()["id"], 4)):
        sentencias = []

        def registrar(conn, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                sentencias.append(statement)

        event.listen(app.state.engine.sync_engine, "before_cursor_execute", registrar)
        try:
            # Sesión HTTP nueva → get_session nueva → identity map vacío en cada GET.
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as nuevo:
                autenticar(nuevo, 1)
                respuesta = await nuevo.get(f"/ordenes/{orden_id}")
                assert respuesta.status_code == 200
                assert len(respuesta.json()["items"]) == cantidad
        finally:
            event.remove(app.state.engine.sync_engine, "before_cursor_execute", registrar)
        dominio = [s for s in sentencias if any(f"FROM {tabla}" in s for tabla in ("orden_trabajo", "item_orden", "historial_estado_orden"))]
        assert len(dominio) == 3
        mediciones.append((cantidad, sentencias, dominio))
    assert len(mediciones[0][1]) == len(mediciones[1][1])
    if os.environ.get("CH09_CAPTURAR_SQL") == "1":
        lineas = ["C-15 — SQL real capturado desde before_cursor_execute durante GET ASGI de app real.",
                  "Base exclusiva: taller_mecanico_test. Sesión nueva por petición; mismo actor ADMIN id1.",
                  "No se registran valores de parámetros ni cookies. Login y altas fuera de medición."]
        for cantidad, sentencias, dominio in mediciones:
            lineas += [f"\n=== GET detalle {cantidad} ítems: {len(sentencias)} SELECT HTTP; {len(dominio)} dominio ==="]
            for numero, sql in enumerate(sentencias, 1):
                lineas += [f"\nSELECT {numero} ({'dominio' if sql in dominio else 'autenticación/roles'}):", sql]
        lineas += ["\nResultado: misma cantidad con2 y4 ítems; sin SELECT por ítem; JSON serializado dentro de medición."]
        Path("docs/evidencias/C-15-consultas.txt").write_text("\n".join(lineas) + "\n", encoding="utf-8")
