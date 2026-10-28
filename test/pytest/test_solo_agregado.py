"""Sólo agregado en la base y el archivo de C-14 (spec solo-agregado: D1-D7, X1-X2).

Las tres tablas se prueban con filas propias dentro de la transacción revertida: en CH-03 todavía
no hay seed (la captura de psql de C-14 se hace en CH-04).
"""

from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

import fabricas
from app.core.errores import MENSAJE_GENERICO, Conflicto
from app.core.unit_of_work import UnitOfWork
from app.modules.ordenes.models import HistorialEstadoOrden
from app.modules.repuestos.models import HistorialPrecio, MovimientoStock
from fabricas import rechazada_sql

pytestmark = pytest.mark.usefixtures("esquema_al_dia")

SOLO_AGREGADO = ("historial_estado_orden", "movimiento_stock", "historial_precio_repuesto")
RESTRICT_VIOLATION = "23001"

# Una columna por tabla para el UPDATE (se asigna a sí misma: el rechazo no depende del valor).
COLUMNA = {"historial_estado_orden": "usuario_id", "movimiento_stock": "motivo", "historial_precio_repuesto": "usuario_id"}


async def _una_fila_por_tabla(sesion) -> dict[str, int]:
    orden = await fabricas.orden(sesion)
    usuario = await fabricas.usuario(sesion)
    repuesto = await fabricas.repuesto(sesion)
    historial = await fabricas.guardar(
        sesion, HistorialEstadoOrden(orden_id=orden.id, hasta_estado="PENDIENTE", usuario_id=usuario.id)
    )
    movimiento = await fabricas.guardar(
        sesion, MovimientoStock(repuesto_id=repuesto.id, usuario_id=usuario.id, cantidad=10, motivo="Stock inicial")
    )
    precio = await fabricas.guardar(
        sesion,
        HistorialPrecio(
            repuesto_id=repuesto.id,
            usuario_id=usuario.id,
            precio_anterior=Decimal("8000.00"),
            precio_nuevo=Decimal("8500.00"),
        ),
    )
    return {"historial_estado_orden": historial.id, "movimiento_stock": movimiento.id,
            "historial_precio_repuesto": precio.id}


async def _cantidad(sesion, tabla: str, id_: int) -> int:
    return await sesion.scalar(text(f"SELECT count(*) FROM {tabla} WHERE id = :id").bindparams(id=id_))


async def test_d1_insertar_en_las_tres_tablas(conexion_revertida):
    ids = await _una_fila_por_tabla(conexion_revertida)

    for tabla, id_ in ids.items():
        assert await _cantidad(conexion_revertida, tabla, id_) == 1, tabla


@pytest.mark.parametrize("tabla", SOLO_AGREGADO)
async def test_d2_update_rechazado(conexion_revertida, tabla):
    sesion = conexion_revertida
    id_ = (await _una_fila_por_tabla(sesion))[tabla]
    columna = COLUMNA[tabla]
    antes = await sesion.scalar(text(f"SELECT {columna} FROM {tabla} WHERE id = :id").bindparams(id=id_))

    error = await rechazada_sql(
        sesion, text(f"UPDATE {tabla} SET {columna} = {columna} WHERE id = :id").bindparams(id=id_), RESTRICT_VIOLATION
    )

    assert f"La tabla {tabla} es de sólo agregado: no se permite UPDATE" in str(error.orig)
    despues = await sesion.scalar(text(f"SELECT {columna} FROM {tabla} WHERE id = :id").bindparams(id=id_))
    assert despues == antes


@pytest.mark.parametrize("tabla", SOLO_AGREGADO)
async def test_d3_delete_rechazado(conexion_revertida, tabla):
    sesion = conexion_revertida
    id_ = (await _una_fila_por_tabla(sesion))[tabla]

    error = await rechazada_sql(
        sesion, text(f"DELETE FROM {tabla} WHERE id = :id").bindparams(id=id_), RESTRICT_VIOLATION
    )

    assert f"La tabla {tabla} es de sólo agregado: no se permite DELETE" in str(error.orig)
    assert await _cantidad(sesion, tabla, id_) == 1


@pytest.mark.parametrize("tabla", SOLO_AGREGADO)
async def test_d4_update_que_no_alcanza_filas_no_da_error(conexion_revertida, tabla):
    columna = COLUMNA[tabla]

    resultado = await conexion_revertida.exec(text(f"UPDATE {tabla} SET {columna} = {columna} WHERE id = -1"))

    assert resultado.rowcount == 0


async def test_d5_truncate_permitido(conexion_revertida):
    sesion = conexion_revertida
    await _una_fila_por_tabla(sesion)

    await sesion.exec(text(f"TRUNCATE {', '.join(SOLO_AGREGADO)}"))

    for tabla in SOLO_AGREGADO:
        assert await sesion.scalar(text(f"SELECT count(*) FROM {tabla}")) == 0, tabla


async def test_d6_el_rechazo_llega_como_conflicto(conexion_revertida):
    sesion = conexion_revertida
    id_ = (await _una_fila_por_tabla(sesion))["movimiento_stock"]
    await sesion.commit()  # libera el SAVEPOINT de la sesión; la transacción externa sigue y se revierte

    with pytest.raises(Conflicto) as error:
        async with UnitOfWork(sesion):
            await sesion.exec(text("UPDATE movimiento_stock SET cantidad = 99 WHERE id = :id").bindparams(id=id_))

    assert error.value.mensaje == MENSAJE_GENERICO


async def test_d7_las_demas_tablas_siguen_modificables(conexion_revertida):
    sesion = conexion_revertida
    orden = await fabricas.orden(sesion)
    repuesto = await fabricas.repuesto(sesion, stock=10)

    orden.total = Decimal("100.00")
    repuesto.stock = 4
    await sesion.flush()

    assert await sesion.scalar(text("SELECT total FROM orden_trabajo WHERE id = :id").bindparams(id=orden.id)) == 100
    assert await sesion.scalar(text("SELECT stock FROM repuesto WHERE id = :id").bindparams(id=repuesto.id)) == 4


# --- test/solo_agregado.sql (C-14): X1-X2 ---

ARCHIVO_C14 = Path(__file__).resolve().parents[1] / "solo_agregado.sql"


def _bloques_del_archivo() -> list[str]:
    """Las sentencias SQL del archivo, sin comentarios ni comandos de psql.

    Corta en un ';' de fin de línea, salvo dentro de un bloque $$ ... $$ (cantidad impar de $$).
    """
    bloques, actual = [], []
    for linea in ARCHIVO_C14.read_text(encoding="utf-8").splitlines():
        limpia = linea.strip()
        if not limpia or limpia.startswith("--") or limpia.startswith("\\"):
            continue
        actual.append(linea)
        texto = "\n".join(actual)
        if limpia.endswith(";") and texto.count("$$") % 2 == 0:
            bloques.append(texto.rstrip().rstrip(";"))
            actual = []
    return bloques


def test_x_el_archivo_tiene_la_verificacion_y_siete_sentencias():
    bloques = _bloques_del_archivo()

    assert len(bloques) == 8
    assert bloques[0].lstrip().startswith("DO $$")


async def test_x2_con_tablas_vacias_corta_antes_de_las_siete(conexion_revertida):
    sesion = conexion_revertida
    verificacion, *_ = _bloques_del_archivo()

    with pytest.raises(DBAPIError, match="Corré python seed.py primero"):
        async with sesion.begin_nested():
            await sesion.exec(text(verificacion))


async def test_x1_las_siete_sentencias_fallan_como_se_espera(conexion_revertida):
    sesion = conexion_revertida
    await _una_fila_por_tabla(sesion)  # incluye un vehículo, por la orden
    verificacion, *sentencias = _bloques_del_archivo()

    async with sesion.begin_nested():
        await sesion.exec(text(verificacion))  # con filas, la verificación pasa

    for sentencia in sentencias[:6]:
        await rechazada_sql(sesion, text(sentencia), RESTRICT_VIOLATION)
    await rechazada_sql(sesion, text(sentencias[6]), "23503", "fk_orden_trabajo_estado_estado_orden")
