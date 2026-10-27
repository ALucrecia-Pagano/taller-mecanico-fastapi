"""Clase de ruta que traduce los errores de dominio a HTTP.

Cada router.py la declara con APIRouter(route_class=RutaQueTraduceErrores): el router «traduce
errores», como dice la consigna. No especificado en la consigna (archivo propio del core).
"""

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from app.core.errores import Conflicto, ErrorDeDominio, NoEncontrado, PaginaInexistente

CODIGO_HTTP: dict[type[ErrorDeDominio], int] = {
    NoEncontrado: status.HTTP_404_NOT_FOUND,
    Conflicto: status.HTTP_409_CONFLICT,
    PaginaInexistente: status.HTTP_422_UNPROCESSABLE_CONTENT,
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
                return JSONResponse(status_code=codigo_http(error), content={"detail": error.mensaje})

        return handler
