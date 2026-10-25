"""Plantilla del entorno y secretos fuera del repositorio (spec configuracion, E1-E2)."""

from pathlib import Path

from app.core.config import Settings

RAIZ = Path(__file__).resolve().parents[2]
SENSIBLES = {"POSTGRES_PASSWORD", "JWT_SECRET_KEY"}


def leer_env_example() -> dict[str, str]:
    variables = {}
    for linea in (RAIZ / "env.example").read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#"):
            nombre, _, valor = linea.partition("=")
            variables[nombre.strip()] = valor.strip()
    return variables


def test_e1_env_example_declara_las_variables_de_settings():
    assert set(leer_env_example()) == {campo.upper() for campo in Settings.model_fields}


def test_e1_env_example_deja_vacios_los_secretos():
    variables = leer_env_example()

    assert {nombre: variables[nombre] for nombre in SENSIBLES} == {
        "POSTGRES_PASSWORD": "",
        "JWT_SECRET_KEY": "",
    }


def test_e2_env_esta_ignorado():
    entradas = (RAIZ / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert ".env" in [entrada.strip() for entrada in entradas]
