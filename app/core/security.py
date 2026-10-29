"""Hash con bcrypt fuera del bucle, y emisión y verificación del token.

Mecanismo puro: no conoce la base ni HTTP, y no guarda estado. El semáforo y el costo llegan
por parámetro (los crea el lifespan, o seed.py en su propio proceso).
"""

import asyncio
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
import jwt
from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.core.config import Settings
from app.core.errores import TokenInvalido

# bcrypt no mira más allá de 72 bytes, y desde la versión 5 rechaza lo que pasa de ahí.
MAXIMO_BYTES_BCRYPT = 72


def _validar_contrasena(valor: str) -> str:
    # No especificado en la consigna (decisión de la alumna). bcrypt 5 acepta el NUL como un byte más;
    # se rechaza porque no tiene uso legítimo en una contraseña y suele traer problemas en otros sistemas.
    if "\x00" in valor:
        raise ValueError("La contraseña no puede contener el carácter NUL")
    if len(valor.encode("utf-8")) > MAXIMO_BYTES_BCRYPT:
        raise ValueError(f"La contraseña puede tener como máximo {MAXIMO_BYTES_BCRYPT} bytes")
    return valor


# Todo campo de contraseña de los contratos usa este tipo. Son bytes y no caracteres: una «ñ» ocupa dos.
# min_length=1: No especificado en la consigna (una cadena vacía no es contraseña).
Contrasena = Annotated[str, Field(min_length=1), AfterValidator(_validar_contrasena)]


async def hashear_password(password: str, *, costo: int, semaforo: asyncio.Semaphore) -> str:
    datos = password.encode("utf-8")
    # Defensa detrás del contrato: bcrypt 4 trunca en silencio y bcrypt 5 lanza; así responde igual.
    if len(datos) > MAXIMO_BYTES_BCRYPT:
        raise ValueError(f"La contraseña supera {MAXIMO_BYTES_BCRYPT} bytes")
    # Fuera del bucle (~250 ms con costo 12) y con un tope de llamadas a la vez.
    async with semaforo:
        hash_ = await asyncio.to_thread(bcrypt.hashpw, datos, bcrypt.gensalt(rounds=costo))
    return hash_.decode("ascii")


async def verificar_password(password: str, hash_: str, *, semaforo: asyncio.Semaphore) -> bool:
    # El costo sale del propio hash: subir BCRYPT_COST no invalida los hashes guardados.
    async with semaforo:
        return await asyncio.to_thread(bcrypt.checkpw, password.encode("utf-8"), hash_.encode("ascii"))


class DatosToken(BaseModel):
    """Lo que la aplicación usa de un token válido."""

    model_config = ConfigDict(frozen=True)

    usuario_id: int
    iat: float  # segundos con fracción: RN-07 lo compara sin truncar
    roles: list[str]  # informativos (los vigentes al emitir); la autorización consulta la base


def emitir_token(
    usuario_id: int, roles: Iterable[str], *, settings: Settings, ahora: datetime | None = None
) -> str:
    ahora = ahora or datetime.now(UTC)
    claims = {
        "sub": str(usuario_id),  # PyJWT >= 2.10 exige texto
        # float y no datetime: PyJWT convierte un datetime con timegm y lo trunca a segundos.
        "iat": ahora.timestamp(),
        "exp": ahora + timedelta(seconds=settings.jwt_expire_seconds),
        "roles": sorted(roles),
    }
    return jwt.encode(claims, settings.jwt_secret_key.get_secret_value(), algorithm=settings.jwt_algorithm)


def decodificar_token(token: str, *, settings: Settings) -> DatosToken:
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            # Lista fija: el algoritmo que declara el token no cuenta (bloquea "none" y la confusión).
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "iat", "exp"]},
        )
        return DatosToken(usuario_id=int(claims["sub"]), iat=claims["iat"], roles=claims["roles"])
    # ValueError incluye la ValidationError de Pydantic; el detalle de la biblioteca no sale de acá.
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        raise TokenInvalido("Token inválido") from None
