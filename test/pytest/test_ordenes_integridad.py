"""Referencias, bajas y rollback real (sin mocks de base)."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from app.core.errores import Conflicto
from test_ordenes_alta import cuerpo_orden
from test_ordenes_catalogo import autenticar


@pytest.mark.parametrize("referencia", ["vehiculo", "repuesto"])
@pytest.mark.parametrize("baja", [False, True])
async def test_alta_referencia_inexistente_o_baja_409_sin_cambios(cliente, base_sembrada, foto_de_la_base, referencia, baja):
    autenticar(cliente, 1)
    cuerpo = cuerpo_orden()
    if baja:
        ruta = "/vehiculos/2" if referencia == "vehiculo" else "/repuestos/4"
        assert (await cliente.delete(ruta)).status_code == 204
        if referencia == "vehiculo":
            assert (await cliente.post("/clientes/1/vehiculos", json={"patente": "AC456EF", "marca": "Ford", "modelo": "Otro", "anio": 2020})).status_code == 201
        else:
            assert (await cliente.post("/repuestos", json={"codigo": "ACE-530", "descripcion": "Otro aceite", "precio": "1.00", "stock_inicial": 0})).status_code == 201
    elif referencia == "vehiculo":
        cuerpo["vehiculo_id"] = 999999
    else:
        cuerpo["items"][1]["repuesto_id"] = 999999
    async with base_sembrada() as s:
        antes = await foto_de_la_base(s)
    respuesta = await cliente.post("/ordenes", json=cuerpo)
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detail": "Vehículo inexistente o dado de baja" if referencia == "vehiculo" else "Repuesto inexistente o dado de baja"}
    async with base_sembrada() as s:
        assert await foto_de_la_base(s) == antes


@pytest.mark.parametrize("parcial", [False, True])
async def test_alta_catalogo_vacio_o_sin_pendiente_409(cliente, base_sembrada, parcial):
    async with base_sembrada() as s:
        await s.exec(text("TRUNCATE estado_orden CASCADE"))
        if parcial:
            await s.exec(text("INSERT INTO estado_orden(codigo,descripcion,posicion,es_final) VALUES ('TERMINADA','Terminada',3,true)"))
        await s.commit()
    autenticar(cliente, 3)
    respuesta = await cliente.post("/ordenes", json=cuerpo_orden())
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detail": "El catálogo de estados no está disponible"}
    async with base_sembrada() as s:
        assert (await s.exec(text("SELECT count(*) FROM orden_trabajo"))).scalar_one() == 0
        assert (await s.exec(text("SELECT count(*) FROM estado_orden"))).scalar_one() == int(parcial)


@pytest.mark.parametrize("diferida", [False, True])
async def test_alta_fallo_historial_flush_o_commit_revierte_todo(base_sembrada, foto_de_la_base, diferida):
    from app.modules.ordenes.schemas import EntradaOrden
    from app.modules.ordenes.service import OrdenesService
    from app.modules.ordenes.unit_of_work import OrdenesUnitOfWork

    # Actor inválido fuerza FK REAL después de flush de orden/ítems.
    # En variante diferida, FK se comprueba al commit; se restaura en finally.
    constraint = "fk_historial_estado_orden_usuario_id_usuario"
    async with base_sembrada() as s:
        antes = await foto_de_la_base(s)
    if diferida:
        async with base_sembrada() as s:
            await s.exec(text(f"ALTER TABLE historial_estado_orden ALTER CONSTRAINT {constraint} DEFERRABLE INITIALLY DEFERRED"))
            await s.commit()
    try:
        async with base_sembrada() as s:
            with pytest.raises(Conflicto) as error:
                await OrdenesService(OrdenesUnitOfWork(s)).crear(EntradaOrden.model_validate(cuerpo_orden()), 999999)
            assert str(error.value) == "No se pudo crear la orden"
            assert (await s.exec(text("SELECT 1"))).scalar_one() == 1
        async with base_sembrada() as s:
            assert await foto_de_la_base(s) == antes
    finally:
        if diferida:
            async with base_sembrada() as s:
                await s.exec(text(f"ALTER TABLE historial_estado_orden ALTER CONSTRAINT {constraint} NOT DEFERRABLE"))
                await s.commit()


async def test_alta_precio_copiado_persiste_tras_patch(cliente, base_sembrada):
    autenticar(cliente, 1)
    datos = cuerpo_orden(items=[{"repuesto_id": 1, "cantidad": 2}])
    primera = await cliente.post("/ordenes", json=datos)
    assert primera.status_code == 201 and primera.json()["total"] == "17000.00"
    assert (await cliente.patch("/repuestos/1", json={"precio": "10.10"})).status_code == 200
    segunda = await cliente.post("/ordenes", json=datos)
    assert segunda.status_code == 201 and segunda.json()["total"] == "20.20"
    # Seam repositorio precargado: el GET de detalle se agrega en tarea4.1.
    from app.modules.ordenes.repository import OrdenTrabajoRepository
    from app.modules.ordenes.service import detalle_respuesta
    async with base_sembrada() as s:
        detalle = detalle_respuesta(await OrdenTrabajoRepository(s).detalle(primera.json()["id"]))
        assert detalle.model_dump(mode="json")["items"][0]["precio_unitario"] == "8500.00"
        assert detalle.model_dump(mode="json")["total"] == "17000.00"
