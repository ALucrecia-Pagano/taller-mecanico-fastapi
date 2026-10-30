import asyncio

import pytest
from sqlalchemy import text

from app.core.errores import Conflicto
from app.modules.repuestos.unit_of_work import RepuestosUnitOfWork


async def test_busqueda_repuestos_total_y_bajas(base_sembrada):
    async with base_sembrada() as sesion:
        uow = RepuestosUnitOfWork(sesion)
        filas, total = await uow.repuestos.buscar("freno", 0, 1)
        assert total == 1
        assert len(filas) == 1
        await sesion.exec(text("UPDATE repuesto SET borrado_en = now() WHERE id = 1"))
        await sesion.commit()
        filas, total = await uow.repuestos.buscar(None, 0, 20)
        assert all(fila.id != 1 for fila in filas)
        assert total == 3


async def test_repuesto_dado_de_baja_se_recupera_incluyendo_deleted(base_sembrada):
    async with base_sembrada() as sesion:
        uow = RepuestosUnitOfWork(sesion)
        repuesto = await uow.repuestos.get_by_id(1)
        await uow.repuestos.soft_delete(repuesto)
        await sesion.commit()

    async with base_sembrada() as sesion:
        repuesto = await RepuestosUnitOfWork(sesion).repuestos.get_by_id_including_deleted(1)

    assert repuesto is not None
    assert repuesto.id == 1
    assert repuesto.borrado_en is not None


async def test_dos_reposiciones_concurrentes_se_suman(base_sembrada):
    fabrica = base_sembrada

    async def reponer(cantidad):
        async with fabrica() as sesion:
            async with RepuestosUnitOfWork(sesion) as uow:
                await uow.repuestos.ajustar_stock(1, cantidad, 1, "Reposición")

    await asyncio.gather(reponer(3), reponer(4))
    async with fabrica() as sesion:
        stock = (await sesion.exec(text("SELECT stock FROM repuesto WHERE id = 1"))).one()[0]
        movimientos = (
            await sesion.exec(
                text("SELECT count(*) FROM movimiento_stock WHERE repuesto_id = 1 AND motivo = 'Reposición'")
            )
        ).one()[0]
    assert stock == 17
    assert movimientos == 2


async def test_ajuste_negativo_rechaza_y_revierte(base_sembrada):
    async with base_sembrada() as sesion:
        await sesion.exec(text("UPDATE repuesto SET stock = 0 WHERE id = 1"))
        await sesion.commit()
        with pytest.raises(Conflicto):
            async with RepuestosUnitOfWork(sesion) as uow:
                await uow.repuestos.ajustar_stock(1, -1, 1, "Orden terminada")
        stock = (await sesion.exec(text("SELECT stock FROM repuesto WHERE id = 1"))).one()[0]
        movimientos = (
            await sesion.exec(
                text("SELECT count(*) FROM movimiento_stock WHERE repuesto_id = 1 AND motivo = 'Orden terminada'")
            )
        ).one()[0]
    assert stock == 0
    assert movimientos == 0
