"""Guarda de la base de prueba: la suite nunca toca la base de la aplicación (DA-29)."""

import pytest

SUFIJO_PRUEBA = "_test"


def derivar_base_de_prueba(postgres_db: str) -> str:
    """Nombre de la base de prueba a partir de la base de la aplicación."""
    if postgres_db.endswith(SUFIJO_PRUEBA):
        raise ValueError(
            f"El .env apunta a la base de prueba ({postgres_db}): "
            "POSTGRES_DB debe ser la base de la aplicación"
        )
    return postgres_db + SUFIJO_PRUEBA


def verificar_base_de_prueba(settings) -> None:
    """Corta la prueba si la configuración resuelta no apunta a una base *_test."""
    if not settings.postgres_db.endswith(SUFIJO_PRUEBA):
        pytest.fail(
            f"La suite sólo corre contra una base *{SUFIJO_PRUEBA}; "
            f"la configuración apunta a {settings.postgres_db}"
        )
