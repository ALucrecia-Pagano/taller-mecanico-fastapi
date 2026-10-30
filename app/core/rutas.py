"""Clase de ruta que traduce los errores de dominio a HTTP.

Cada router.py la declara con APIRouter(route_class=RutaQueTraduceErrores): el router «traduce
errores», como dice la consigna. No especificado en la consigna (archivo propio del core).
"""

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from app.core.errores import Conflicto, EntradaInvalida, ErrorDeDominio, NoEncontrado, PaginaInexistente, TokenInvalido
from app.core.errores import LimiteDeIntentos, PermisoDenegado

# Todo error de dominio necesita su código acá: sin él terminaría en 500 (lo controla test_rutas, T7).
CODIGO_HTTP: dict[type[ErrorDeDominio], int] = {
    NoEncontrado: status.HTTP_404_NOT_FOUND,
    Conflicto: status.HTTP_409_CONFLICT,
    PaginaInexistente: status.HTTP_422_UNPROCESSABLE_CONTENT,
    EntradaInvalida: status.HTTP_422_UNPROCESSABLE_CONTENT,
    TokenInvalido: status.HTTP_401_UNAUTHORIZED,
    LimiteDeIntentos: status.HTTP_429_TOO_MANY_REQUESTS,
    PermisoDenegado: status.HTTP_403_FORBIDDEN,
}


def codigo_http(error: ErrorDeDominio) -> int:
    # La clase más específica del error que tenga código; así una subclase hereda el de su padre.
    return next(CODIGO_HTTP[clase] for clase in type(error).__mro__ if clase in CODIGO_HTTP)


class RutaQueTraduceErrores(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler_original = super().get_route_handler()

        async def handler(request: Request) -> Response:
            # El handler original también resuelve las dependencias: sus errores se traducen igual.
            try:
                return await handler_original(request)
            except ErrorDeDominio as error:
                headers = {"Retry-After": str(error.segundos)} if isinstance(error, LimiteDeIntentos) else None
                return JSONResponse(status_code=codigo_http(error), content={"detail": error.mensaje}, headers=headers)

        return handler
