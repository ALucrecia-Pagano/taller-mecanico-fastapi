"""Forma del esquema leída de la base migrada (spec modelo-de-datos: S1-S8)."""

import pytest
from sqlalchemy import func, select, text

import esquema_esperado as esperado
import fabricas
from app.modules.ordenes.models import HistorialEstadoOrden

pytestmark = pytest.mark.usefixtures("esquema_al_dia")

TABLAS = tuple(esperado.COLUMNAS)


async def _filas(sesion, sql: str):
    return (await sesion.exec(text(sql).bindparams(tablas=list(TABLAS)))).all()


COLUMNAS_SQL = """
    SELECT table_name, column_name, is_nullable, data_type, numeric_precision, numeric_scale
      FROM information_schema.columns
     WHERE table_schema = 'public' AND table_name = ANY(:tablas)
"""

FK_SQL = """
    SELECT c.conname, t.relname, a.attname, rt.relname, ra.attname
      FROM pg_constraint c
      JOIN pg_class t ON t.oid = c.conrelid
      JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
      JOIN pg_class rt ON rt.oid = c.confrelid
      JOIN pg_attribute ra ON ra.attrelid = c.confrelid AND ra.attnum = c.confkey[1]
     WHERE c.contype = 'f' AND t.relname = ANY(:tablas)
"""


async def test_s1_columnas_de_la_consigna(conexion_revertida):
    columnas: dict[str, set[str]] = {}
    for tabla, columna, *_ in await _filas(conexion_revertida, COLUMNAS_SQL):
        columnas.setdefault(tabla, set()).add(columna)

    assert columnas == esperado.COLUMNAS


async def test_s2_usuario_sin_columna_rol(conexion_revertida):
    columnas = {c for t, c, *_ in await _filas(conexion_revertida, COLUMNAS_SQL) if t == "usuario"}

    assert columnas and "rol" not in columnas


async def test_s3_solo_las_marcadas_nulo_admiten_null(conexion_revertida):
    nulables = {(t, c) for t, c, nulo, *_ in await _filas(conexion_revertida, COLUMNAS_SQL) if nulo == "YES"}

    assert nulables == esperado.NULABLES


async def test_s4_dinero_numeric_y_fechas_con_zona(conexion_revertida):
    filas = await _filas(conexion_revertida, COLUMNAS_SQL)
    numericas = {(t, c): (p, s) for t, c, _, tipo, p, s in filas if tipo == "numeric"}
    fechas = {(t, c): tipo for t, c, _, tipo, *_ in filas if tipo.startswith("timestamp")}

    assert numericas == esperado.DINERO
    assert set(fechas) == esperado.FECHAS
    assert set(fechas.values()) == {"timestamp with time zone"}


async def test_s5_las_18_fk_con_su_destino(conexion_revertida):
    fks = {nombre: (t, c, rt, rc) for nombre, t, c, rt, rc in await _filas(conexion_revertida, FK_SQL)}

    assert len(fks) == 18
    assert fks == esperado.FK


async def test_s6_toda_fk_encabeza_un_indice(conexion_revertida):
    revisadas = await _filas(
        conexion_revertida,
        """
        SELECT c.conname,
               EXISTS (SELECT 1 FROM pg_index i
                        WHERE i.indrelid = c.conrelid AND i.indkey[0] = c.conkey[1]) AS con_indice
          FROM pg_constraint c JOIN pg_class t ON t.oid = c.conrelid
         WHERE c.contype = 'f' AND t.relname = ANY(:tablas)
        """,
    )

    assert len(revisadas) == 18
    assert [nombre for nombre, con_indice in revisadas if not con_indice] == []


async def test_s7_nombres_exactos_de_restricciones(conexion_revertida):
    nombres = {
        n
        for (n,) in await _filas(
            conexion_revertida,
            """
            SELECT c.conname FROM pg_constraint c JOIN pg_class t ON t.oid = c.conrelid
             WHERE c.contype IN ('p', 'u', 'c', 'f') AND t.relname = ANY(:tablas)
            """,
        )
    }

    assert nombres == esperado.PK | set(esperado.UNIQUE) | set(esperado.CHECK) | set(esperado.FK)


async def test_s7_nombres_de_indices_y_condicion_de_los_parciales(conexion_revertida):
    indices = dict(
        await _filas(
            conexion_revertida,
            """
            SELECT i.indexname, i.indexdef FROM pg_indexes i
             WHERE i.schemaname = 'public' AND i.tablename = ANY(:tablas)
               AND NOT EXISTS (SELECT 1 FROM pg_constraint c WHERE c.conname = i.indexname)
            """,
        )
    )

    assert set(indices) == set(esperado.INDICES) | set(esperado.PARCIALES)
    for nombre, (_, _, condicion) in esperado.PARCIALES.items():
        assert "UNIQUE" in indices[nombre]
        assert indices[nombre].endswith(f"WHERE ({condicion})")


async def test_s8_cuando_toma_la_hora_de_la_base(conexion_revertida):
    sesion = conexion_revertida
    orden = await fabricas.orden(sesion)
    usuario = await fabricas.usuario(sesion)

    linea = await fabricas.guardar(
        sesion, HistorialEstadoOrden(orden_id=orden.id, hasta_estado="PENDIENTE", usuario_id=usuario.id)
    )
    ahora = await sesion.scalar(select(func.now()))

    assert linea.cuando == ahora
    assert linea.cuando.tzinfo is not None
