"""Emisión y validación del token (spec token-de-acceso, T1-T8). No toca la base."""

import base64
import json
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import Settings
from app.core.errores import TokenInvalido
from app.core.security import decodificar_token, emitir_token

CLAVE = "k" * 64


def configuracion(**cambios) -> Settings:
    valores = {"postgres_password": "secreta", "jwt_secret_key": CLAVE, "jwt_algorithm": "HS256"}
    return Settings(_env_file=None, **(valores | cambios))


def hace_un_segundo_con_fraccion() -> datetime:
    # Un segundo atrás: PyJWT rechaza un iat en el futuro, y la fracción fija no debe adelantarlo.
    return (datetime.now(UTC) - timedelta(seconds=1)).replace(microsecond=123456)


def claims_sin_verificar(token: str) -> dict:
    return jwt.decode(token, options={"verify_signature": False})


def firmar(payload: dict) -> str:
    return jwt.encode(payload, CLAVE, algorithm="HS256")


def test_t1_ida_y_vuelta():
    settings = configuracion()
    ahora = hace_un_segundo_con_fraccion()

    datos = decodificar_token(emitir_token(3, ["RECEPCION"], settings=settings, ahora=ahora), settings=settings)

    assert datos.usuario_id == 3
    assert datos.roles == ["RECEPCION"]
    assert datos.iat == ahora.timestamp()


def test_t2_la_fraccion_de_segundo_sobrevive():
    settings = configuracion()
    ahora = hace_un_segundo_con_fraccion()

    datos = decodificar_token(emitir_token(1, ["ADMIN"], settings=settings, ahora=ahora), settings=settings)

    assert isinstance(datos.iat, float)
    assert datos.iat == ahora.timestamp()
    assert datos.iat % 1 != 0  # no se truncó a segundos (OB-09)


@pytest.mark.parametrize("duracion", [1800, 60])
def test_t3_vencimiento_desde_la_configuracion(duracion):
    settings = configuracion(jwt_expire_seconds=duracion)

    claims = claims_sin_verificar(emitir_token(1, ["ADMIN"], settings=settings, ahora=hace_un_segundo_con_fraccion()))

    assert claims["exp"] - int(claims["iat"]) == duracion


def test_t4_vencido():
    settings = configuracion()
    token = emitir_token(1, ["ADMIN"], settings=settings, ahora=datetime.now(UTC) - timedelta(hours=2))

    with pytest.raises(TokenInvalido):
        decodificar_token(token, settings=settings)


def _alterar_sub(token: str) -> str:
    cabecera, contenido, firma = token.split(".")
    claims = json.loads(base64.urlsafe_b64decode(contenido + "=" * (-len(contenido) % 4)))
    claims["sub"] = "1"  # el 2 se hace pasar por el 1, con la firma original
    nuevo = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    return f"{cabecera}.{nuevo}.{firma}"


def test_t5_otra_clave_o_contenido_alterado():
    settings = configuracion()
    con_otra_clave = emitir_token(2, ["CLIENTE"], settings=configuracion(jwt_secret_key="z" * 64))
    alterado = _alterar_sub(emitir_token(2, ["CLIENTE"], settings=settings))

    for token in (con_otra_clave, alterado):
        with pytest.raises(TokenInvalido):
            decodificar_token(token, settings=settings)


def test_t6_sin_firma_u_otro_algoritmo():
    settings = configuracion()
    claims = claims_sin_verificar(emitir_token(1, ["ADMIN"], settings=settings))
    sin_firma = jwt.encode(claims, None, algorithm="none")
    con_hs512 = jwt.encode(claims, CLAVE, algorithm="HS512")

    for token in (sin_firma, con_hs512):
        with pytest.raises(TokenInvalido):
            decodificar_token(token, settings=settings)


def _claims_validos() -> dict:
    ahora = hace_un_segundo_con_fraccion()
    return {"sub": "1", "iat": ahora.timestamp(), "exp": ahora + timedelta(minutes=30), "roles": ["ADMIN"]}


@pytest.mark.parametrize(
    "cambio",
    [
        {"sub": None},
        {"iat": None},
        {"exp": None},
        {"roles": None},
        {"sub": "abc"},
        {"roles": "ADMIN"},
    ],
    ids=["sin_sub", "sin_iat", "sin_exp", "sin_roles", "sub_no_numerico", "roles_no_lista"],
)
def test_t7_claim_faltante_o_mal_formado(cambio):
    claims = _claims_validos()
    for clave, valor in cambio.items():
        if valor is None:
            del claims[clave]
        else:
            claims[clave] = valor

    with pytest.raises(TokenInvalido):
        decodificar_token(firmar(claims), settings=configuracion())


def test_t8_no_es_un_token():
    with pytest.raises(TokenInvalido):
        decodificar_token("no-es-un-token", settings=configuracion())


def test_t1_el_token_valido_de_referencia_pasa():
    # Control de T7: los claims de referencia, sin cambios, sí se aceptan.
    datos = decodificar_token(firmar(_claims_validos()), settings=configuracion())

    assert datos.usuario_id == 1
