"""Migraciones (spec migraciones: A1-A2 de CH-01; M1-M6 de CH-03; M7 está en test_modelos.py)."""

import os
import re
import subprocess
import sys
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import text
from sqlmodel import SQLModel

import esquema_esperado as esperado
from app.core.config import get_settings
from app.core.database import crear_motor
from guarda import verificar_base_de_prueba

RAIZ = Path(__file__).resolve().parents[2]
VERSIONES = RAIZ / "migrations" / "versions"
ULTIMA_VERSION = "0002"
TABLAS_DEL_DOMINIO = set(esperado.COLUMNAS)

TABLAS_SQL = text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")


def test_a1_alembic_ini_sin_direccion_de_la_base():
    lineas = (RAIZ / "alembic.ini").read_text(encoding="utf-8").splitlines()
    con_valor = [
        linea
        for linea in lineas
        if linea.strip().startswith("sqlalchemy.url") and linea.partition("=")[2].strip()
    ]

    assert con_valor == []


def test_a2_alembic_current_contra_la_base_de_prueba(entorno_de_prueba):
    verificar_base_de_prueba(get_settings())  # el subproceso hereda este mismo entorno

    resultado = subprocess.run(
        [sys.executable, "-m", "alembic", "current"],
        cwd=RAIZ,
        env=dict(os.environ),
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr  # alembic informa por stdout


async def test_m1_upgrade_crea_las_13_tablas_en_la_ultima_version(conexion_revertida):
    tablas = set((await conexion_revertida.exec(TABLAS_SQL)).scalars().all())
    version = (await conexion_revertida.exec(text("SELECT version_num FROM alembic_version"))).scalars().all()

    assert TABLAS_DEL_DOMINIO <= tablas
    assert version == [ULTIMA_VERSION]


async def test_m3_el_catalogo_queda_vacio(conexion_revertida):
    filas = (await conexion_revertida.exec(text("SELECT count(*) FROM estado_orden"))).one()

    assert filas == (0,)


def test_m5_dos_migraciones_leidas_y_sin_tablas_de_prueba():
    migraciones = sorted(VERSIONES.glob("*.py"))

    assert [m.name[:5] for m in migraciones] == ["0001_", "0002_"]
    for migracion in migraciones:
        contenido = migracion.read_text(encoding="utf-8")
        assert "Leída antes de aplicarla" in contenido, migracion.name
        assert "prueba_" not in contenido, migracion.name


def test_m6_ningun_create_all():
    excluidas = {".venv", "__pycache__", ".git"}
    # Este archivo se excluye a sí mismo: contiene el patrón que busca.
    revisados = [
        p
        for p in RAIZ.rglob("*.py")
        if not excluidas & set(p.relative_to(RAIZ).parts) and p != Path(__file__).resolve()
    ]
    # Cualquier acceso al método, también sin llamarlo (el uso asincrónico se pasa a run_sync).
    uso = re.compile(r"\.create_all\b")

    con_uso = [str(p.relative_to(RAIZ)) for p in revisados if uso.search(p.read_text(encoding="utf-8"))]

    assert RAIZ / "main.py" in revisados
    assert con_uso == []


async def _estado_de_la_base(settings) -> tuple[set[str], bool]:
    """Tablas de public y si existe la función del disparador, desde un motor propio."""
    engine = crear_motor(settings)
    try:
        async with engine.connect() as conexion:
            tablas = set((await conexion.execute(TABLAS_SQL)).scalars().all())
            funcion = await conexion.scalar(
                text("SELECT EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'rechazar_cambio_solo_agregado')")
            )
    finally:
        await engine.dispose()
    return tablas, funcion


async def test_m2_upgrade_downgrade_base_y_upgrade(
    alembic_de_prueba, esquema_al_dia, settings_de_prueba, tablas_de_prueba, motor_del_esquema
):
    try:
        alembic_de_prueba("downgrade", "base")
        tablas, funcion = await _estado_de_la_base(settings_de_prueba)
        assert TABLAS_DEL_DOMINIO & tablas == set()
        assert not funcion
        assert {"prueba_articulo", "prueba_baja"} <= tablas  # no las toca: no son del esquema

        alembic_de_prueba("upgrade", "head")
        tablas, funcion = await _estado_de_la_base(settings_de_prueba)
        assert TABLAS_DEL_DOMINIO <= tablas
        assert funcion
    finally:
        alembic_de_prueba("upgrade", "head")  # el resto de la sesión necesita el esquema
        # Las conexiones del pool tienen sentencias preparadas contra las tablas viejas.
        await motor_del_esquema.dispose()


async def test_m4_modelos_y_base_sin_diferencias(motor_del_esquema, tablas_de_prueba):
    def diferencias(conexion_sincronica):
        contexto = MigrationContext.configure(conexion_sincronica)
        return compare_metadata(contexto, SQLModel.metadata)

    async with motor_del_esquema.connect() as conexion:
        encontradas = await conexion.run_sync(diferencias)

    # Las tablas prueba_* de la suite de CH-02 viven en la misma base y no son del esquema (nota 7d de CH-02).
    restantes = [
        d for d in encontradas if not (d[0] == "remove_table" and d[1].name.startswith("prueba_"))
    ]
    assert restantes == []
