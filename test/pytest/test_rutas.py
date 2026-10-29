"""Traducción de errores de dominio a HTTP en el router (spec errores-de-dominio, T1-T4, T6 y T7)."""

import pytest
from fastapi import APIRouter, Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.errores import Conflicto, ErrorDeDominio, NoEncontrado, PaginaInexistente, TokenInvalido
from app.core.errores import LimiteDeIntentos
from app.core.rutas import RutaQueTraduceErrores, codigo_http


def app_de_prueba(router: APIRouter) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


async def llamar(app: FastAPI, ruta: str, **transporte):
    async with AsyncClient(transport=ASGITransport(app=app, **transporte), base_url="http://test") as cliente:
        return await cliente.get(ruta)


router_de_errores = APIRouter(prefix="/errores", route_class=RutaQueTraduceErrores)


@router_de_errores.get("/no-encontrado")
async def no_encontrado():
    raise NoEncontrado("El repuesto no existe")


@router_de_errores.get("/conflicto")
async def conflicto():
    raise Conflicto("Ese artículo ya está cargado")


@router_de_errores.get("/pagina")
async def pagina():
    raise PaginaInexistente("La página 3 no existe: hay 2")


@pytest.mark.parametrize(
    ("ruta", "codigo", "mensaje"),
    [
        ("/errores/no-encontrado", 404, "El repuesto no existe"),
        ("/errores/conflicto", 409, "Ese artículo ya está cargado"),
        ("/errores/pagina", 422, "La página 3 no existe: hay 2"),
    ],
)
async def test_t1_los_tres_codigos(ruta, codigo, mensaje):
    respuesta = await llamar(app_de_prueba(router_de_errores), ruta)

    assert respuesta.status_code == codigo
    assert respuesta.json() == {"detail": mensaje}


async def dependencia_que_choca():
    raise Conflicto("Ese documento ya pertenece a un cliente")


router_con_dependencia = APIRouter(route_class=RutaQueTraduceErrores)


@router_con_dependencia.get("/con-dependencia", dependencies=[Depends(dependencia_que_choca)])
async def con_dependencia():
    return {"llego": True}


@router_con_dependencia.get("/bug")
async def bug():
    raise ValueError("un bug no se disfraza")


async def test_t2_error_lanzado_desde_una_dependencia():
    respuesta = await llamar(app_de_prueba(router_con_dependencia), "/con-dependencia")

    assert respuesta.status_code == 409
    assert respuesta.json() == {"detail": "Ese documento ya pertenece a un cliente"}


async def test_t3_excepcion_que_no_es_de_dominio():
    respuesta = await llamar(app_de_prueba(router_con_dependencia), "/bug", raise_app_exceptions=False)

    assert respuesta.status_code == 500
    assert "bug" not in respuesta.text


RUTAS_PROPIAS_DE_FASTAPI = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}


def rutas_de(rutas):
    # FastAPI 0.162: include_router no copia las rutas, agrega un envoltorio con el router original.
    for ruta in rutas:
        incluido = getattr(ruta, "original_router", None)
        if incluido is not None:
            yield from rutas_de(incluido.routes)
        else:
            yield ruta


def recorrer(app: FastAPI) -> tuple[list[str], list[str]]:
    """(rutas recorridas, rutas que no traducen errores de dominio), sin las propias de FastAPI."""
    recorridas = [r for r in rutas_de(app.routes) if r.path not in RUTAS_PROPIAS_DE_FASTAPI]
    sin_traduccion = [r.path for r in recorridas if not isinstance(r, RutaQueTraduceErrores)]
    return [r.path for r in recorridas], sin_traduccion


def test_t4_el_recorrido_detecta_una_ruta_sin_traduccion():
    plano = APIRouter()  # sin route_class

    @plano.get("/plano")
    async def ruta_plana():
        return {}

    grupo = APIRouter()
    grupo.include_router(plano)
    grupo.include_router(router_de_errores)
    app = FastAPI()
    app.include_router(grupo)

    recorridas, sin_traduccion = recorrer(app)

    assert "/errores/conflicto" in recorridas
    assert sin_traduccion == ["/plano"]


def test_t4_toda_ruta_de_la_aplicacion_traduce_errores_de_dominio():
    from main import app

    recorridas, sin_traduccion = recorrer(app)

    assert "/health/live" in recorridas  # no pasa en vacío
    assert sin_traduccion == []


async def dependencia_con_token_invalido():
    raise TokenInvalido("Token inválido")


router_con_token = APIRouter(route_class=RutaQueTraduceErrores)


@router_con_token.get("/protegida", dependencies=[Depends(dependencia_con_token_invalido)])
async def protegida():
    return {"llego": True}


async def test_t6_token_invalido():
    respuesta = await llamar(app_de_prueba(router_con_token), "/protegida")

    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": "Token inválido"}


def subclases(clase):
    for subclase in clase.__subclasses__():
        yield subclase
        yield from subclases(subclase)


def sin_codigo_http(clases) -> list[str]:
    """Nombres de las clases cuyo error terminaría en 500 por no tener código en el mapa."""
    faltantes = []
    for clase in clases:
        try:
            codigo_http(clase("x"))
        except StopIteration:
            faltantes.append(clase.__name__)
    return faltantes


def test_t7_el_recorrido_detecta_un_error_sin_codigo():
    class ErrorSinMapear(Conflicto.__base__):  # subclase directa de ErrorDeDominio, sin código
        pass

    assert sin_codigo_http([Conflicto, ErrorSinMapear]) == ["ErrorSinMapear"]


def test_t7_todo_error_de_dominio_de_la_aplicacion_tiene_codigo_http():
    import main  # noqa: F401  (importa todos los routers y, con ellos, todos los errores de dominio)

    de_la_aplicacion = [c for c in subclases(ErrorDeDominio) if c.__module__.startswith("app.")]

    assert TokenInvalido in de_la_aplicacion  # no pasa en vacío
    assert sin_codigo_http(de_la_aplicacion) == []


@pytest.mark.parametrize("dependencia,segundos", [(False, 2), (True, 17)])
async def test_e429_e429b_retry_after_en_handler_y_dependencia(dependencia, segundos):
    router = APIRouter(route_class=RutaQueTraduceErrores)
    async def limite():
        raise LimiteDeIntentos(segundos=segundos)
    @router.get("/limite", dependencies=[Depends(limite)] if dependencia else [])
    async def pedido():
        await limite()
    respuesta = await llamar(app_de_prueba(router), "/limite", raise_app_exceptions=False)
    assert respuesta.status_code == 429
    assert respuesta.headers["Retry-After"] == str(segundos)
    assert respuesta.json() == {"detail": "Demasiados intentos"}
