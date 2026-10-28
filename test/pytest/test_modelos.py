"""Modelos leídos de la metadata, sin base (spec modelo-de-datos y migraciones: M7, T5, S1-S3 y S7).

Cada test por tabla importa sólo el módulo dueño de esa tabla; M7 y T5 necesitan los cuatro.
"""

import importlib
from pathlib import Path

import pytest
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, PrimaryKeyConstraint, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import configure_mappers
from sqlmodel import SQLModel

import esquema_esperado as esperado

RAIZ = Path(__file__).resolve().parents[2]
PREPARADOR = postgresql.dialect().identifier_preparer

MODULO_DE_CADA_TABLA = {
    "usuario": "usuarios",
    "asignacion_rol": "usuarios",
    "intento_acceso": "usuarios",
    "evento_seguridad": "usuarios",
    "cliente": "clientes",
    "vehiculo": "clientes",
    "repuesto": "repuestos",
    "movimiento_stock": "repuestos",
    "historial_precio_repuesto": "repuestos",
    "estado_orden": "ordenes",
    "orden_trabajo": "ordenes",
    "item_orden": "ordenes",
    "historial_estado_orden": "ordenes",
}
TABLAS = sorted(esperado.COLUMNAS)


def _tabla(nombre: str):
    importlib.import_module(f"app.modules.{MODULO_DE_CADA_TABLA[nombre]}.models")
    return SQLModel.metadata.tables[nombre]


def _importar_todos() -> None:
    for modulo in esperado.MODULOS_DE_MODELOS:
        importlib.import_module(modulo)


def _nombre(restriccion) -> str:
    """El nombre final, con la convención aplicada, como lo escribiría el DDL."""
    return PREPARADOR.format_constraint(restriccion)


def _de_la_tabla(esperados: dict, tabla: str) -> set[str]:
    return {nombre for nombre, datos in esperados.items() if (datos if isinstance(datos, str) else datos[0]) == tabla}


def test_m7_la_metadata_tiene_las_13_tablas():
    _importar_todos()

    assert set(SQLModel.metadata.tables) == set(esperado.COLUMNAS)


def test_m7_env_importa_los_mismos_modulos():
    env = (RAIZ / "migrations" / "env.py").read_text(encoding="utf-8")

    faltan = [m for m in esperado.MODULOS_DE_MODELOS if f"import {m}" not in env]

    assert faltan == []


@pytest.mark.parametrize("nombre", TABLAS)
def test_s1_columnas_de_la_consigna(nombre):
    assert {c.name for c in _tabla(nombre).columns} == esperado.COLUMNAS[nombre]


def test_s2_usuario_sin_columna_rol():
    assert "rol" not in _tabla("usuario").columns


@pytest.mark.parametrize("nombre", TABLAS)
def test_s3_solo_las_marcadas_nulo_admiten_null(nombre):
    nulables = {(nombre, c.name) for c in _tabla(nombre).columns if c.nullable}

    assert nulables == {par for par in esperado.NULABLES if par[0] == nombre}


@pytest.mark.parametrize("nombre", TABLAS)
def test_s7_nombres_de_pk_unique_check_y_fk(nombre):
    restricciones = _tabla(nombre).constraints

    def de_tipo(tipo):
        return {_nombre(c) for c in restricciones if isinstance(c, tipo)}

    assert de_tipo(PrimaryKeyConstraint) == {f"pk_{nombre}"}
    assert de_tipo(UniqueConstraint) == _de_la_tabla(esperado.UNIQUE, nombre)
    assert de_tipo(CheckConstraint) == _de_la_tabla(esperado.CHECK, nombre)
    assert de_tipo(ForeignKeyConstraint) == _de_la_tabla(esperado.FK, nombre)


@pytest.mark.parametrize("nombre", TABLAS)
def test_s7_nombres_de_indices_y_condicion_de_los_parciales(nombre):
    indices = _tabla(nombre).indexes

    assert {_nombre(i) for i in indices if not i.unique} == _de_la_tabla(esperado.INDICES, nombre)
    parciales = {_nombre(i): i for i in indices if i.unique}
    assert set(parciales) == _de_la_tabla(esperado.PARCIALES, nombre)
    for indice_nombre, indice in parciales.items():
        _, columnas, condicion = esperado.PARCIALES[indice_nombre]
        assert tuple(c.name for c in indice.columns) == columnas
        assert str(indice.dialect_options["postgresql"]["where"]) == condicion


def test_t5_los_mappers_configuran_sin_ambiguedad():
    _importar_todos()

    configure_mappers()
