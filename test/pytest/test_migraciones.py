"""Configuración de migraciones (spec migraciones, A1-A2)."""

import os
import subprocess
import sys
from pathlib import Path

from app.core.config import get_settings
from guarda import verificar_base_de_prueba

RAIZ = Path(__file__).resolve().parents[2]


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
