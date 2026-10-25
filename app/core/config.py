"""Configuración leída del entorno o de un .env no versionado (DA-07)."""

from functools import lru_cache

from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Base de datos
    postgres_user: str = "postgres"
    postgres_password: SecretStr = Field(min_length=1)
    postgres_db: str = "taller_mecanico"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # Token
    # Al menos 32 caracteres: HS256 pide una clave de 256 bits (RFC 7518).
    jwt_secret_key: SecretStr = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_expire_seconds: int = Field(default=1800, gt=0)

    # bcrypt (acepta costos de 4 a 31)
    bcrypt_cost: int = Field(default=12, ge=4, le=31)
    bcrypt_max_concurrency: int = Field(default=4, gt=0)

    # Pool del motor
    db_pool_size: int = Field(default=5, gt=0)
    db_max_overflow: int = 10

    # Cookie y consola
    cookie_secure: bool = False
    sql_echo: bool = False

    # Límite de login (RN-08)
    login_max_fallos: int = 5
    login_ventana_segundos: int = 60

    # repr=False: la URL lleva la contraseña. URL.create escapa sus caracteres especiales.
    @computed_field(repr=False)
    @property
    def database_url(self) -> str:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        ).render_as_string(hide_password=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
