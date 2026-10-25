"""Configuración desde el entorno (spec configuracion, S1-S8)."""

import pytest
from pydantic import ValidationError
from sqlalchemy.engine import make_url

from app.core.config import Settings, get_settings

VARIABLES = (
    "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "POSTGRES_HOST", "POSTGRES_PORT",
    "JWT_SECRET_KEY", "JWT_ALGORITHM", "JWT_EXPIRE_SECONDS",
    "BCRYPT_COST", "BCRYPT_MAX_CONCURRENCY",
    "DB_POOL_SIZE", "DB_MAX_OVERFLOW",
    "COOKIE_SECURE", "SQL_ECHO",
    "LOGIN_MAX_FALLOS", "LOGIN_VENTANA_SEGUNDOS",
)
CLAVE_VALIDA = "k" * 64


@pytest.fixture
def entorno(monkeypatch):
    """Entorno sin ninguna variable de la configuración, salvo los dos secretos."""
    for nombre in VARIABLES:
        monkeypatch.delenv(nombre, raising=False)
    monkeypatch.setenv("POSTGRES_PASSWORD", "secreta")
    monkeypatch.setenv("JWT_SECRET_KEY", CLAVE_VALIDA)
    return monkeypatch


def test_s1_carga_con_los_defaults_de_da07(entorno):
    settings = Settings(_env_file=None)

    assert settings.jwt_algorithm == "HS256"
    assert settings.db_pool_size == 5


def test_s2_falta_la_contrasena_de_la_base(entorno):
    entorno.delenv("POSTGRES_PASSWORD")

    with pytest.raises(ValidationError, match="postgres_password"):
        Settings(_env_file=None)


def test_s2_falta_la_clave_de_firma(entorno):
    entorno.delenv("JWT_SECRET_KEY")

    with pytest.raises(ValidationError, match="jwt_secret_key"):
        Settings(_env_file=None)


def test_s3_contrasena_de_la_base_vacia(entorno):
    entorno.setenv("POSTGRES_PASSWORD", "")

    with pytest.raises(ValidationError, match="postgres_password"):
        Settings(_env_file=None)


def test_s3_clave_de_firma_de_31_caracteres(entorno):
    entorno.setenv("JWT_SECRET_KEY", "k" * 31)

    with pytest.raises(ValidationError, match="jwt_secret_key"):
        Settings(_env_file=None)


def test_s3_clave_de_firma_de_32_caracteres(entorno):
    entorno.setenv("JWT_SECRET_KEY", "k" * 32)

    assert Settings(_env_file=None).jwt_secret_key.get_secret_value() == "k" * 32


def test_s6_clave_desconocida_en_el_env(entorno, tmp_path):
    archivo = tmp_path / ".env"
    archivo.write_text("JWT_SECRET=tipeo\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="jwt_secret"):
        Settings(_env_file=archivo)


@pytest.mark.parametrize("variable", ["DB_POOL_SIZE", "JWT_EXPIRE_SECONDS", "BCRYPT_MAX_CONCURRENCY"])
def test_s7_enteros_positivos_en_cero(entorno, variable):
    entorno.setenv(variable, "0")

    with pytest.raises(ValidationError, match=variable.lower()):
        Settings(_env_file=None)


@pytest.mark.parametrize("costo", ["3", "32"])
def test_s7_costo_de_bcrypt_fuera_de_rango(entorno, costo):
    entorno.setenv("BCRYPT_COST", costo)

    with pytest.raises(ValidationError, match="bcrypt_cost"):
        Settings(_env_file=None)


@pytest.mark.parametrize("costo", [4, 31])
def test_s7_costo_de_bcrypt_en_los_bordes(entorno, costo):
    entorno.setenv("BCRYPT_COST", str(costo))

    assert Settings(_env_file=None).bcrypt_cost == costo


def test_s8_una_lectura_por_proceso_y_relectura_explicita(entorno, tmp_path):
    entorno.chdir(tmp_path)  # sin .env: sólo cuenta el entorno
    entorno.setenv("POSTGRES_DB", "primera")
    get_settings.cache_clear()
    try:
        primera = get_settings()
        entorno.setenv("POSTGRES_DB", "segunda")

        assert get_settings() is primera
        get_settings.cache_clear()
        assert get_settings().postgres_db == "segunda"
    finally:
        get_settings.cache_clear()


def test_s4_url_asyncpg_con_contrasena_especial(entorno):
    entorno.setenv("POSTGRES_PASSWORD", "p@ss/w%rd:x")
    entorno.setenv("POSTGRES_HOST", "db.local")
    entorno.setenv("POSTGRES_PORT", "5433")

    url = make_url(Settings(_env_file=None).database_url)

    assert url.drivername == "postgresql+asyncpg"
    assert url.password == "p@ss/w%rd:x"
    assert (url.host, url.port, url.database) == ("db.local", 5433, "taller_mecanico")


def test_s5_la_representacion_no_expone_secretos(entorno):
    entorno.setenv("POSTGRES_PASSWORD", "contrasena-visible")
    settings = Settings(_env_file=None)

    for texto in (repr(settings), str(settings)):
        assert "contrasena-visible" not in texto
        assert CLAVE_VALIDA not in texto
        assert settings.database_url not in texto
