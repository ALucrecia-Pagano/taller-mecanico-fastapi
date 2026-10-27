"""UnitOfWork base: confirma o revierte al salir del bloque (Ejercicio 6, secciones 6.6 y 6.7)."""

from collections.abc import Mapping
from types import TracebackType
from typing import ClassVar, Self

from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.errores import traducir_integrity_error


class UnitOfWork:
    """El router lo construye con una dependencia; el servicio lo abre con async with y nunca lo construye.

    No cierra la sesión: no la creó (la crea y la cierra get_session). No ofrece commit() ni
    rollback() públicos: la única forma de confirmar es salir del bloque sin excepción.
    """

    # Cada UoW de módulo declara el mensaje propio de cada restricción que sus operaciones pueden violar.
    mensajes_de_restriccion: ClassVar[Mapping[str, str]] = {}

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._abierto = False

    async def __aenter__(self) -> Self:
        # Un bloque interno confirmaría a mitad de la operación (No especificado en la consigna).
        if self._abierto:
            raise RuntimeError("Unit of Work anidado: la operación ya tiene un bloque abierto")
        self._abierto = True
        return self

    async def __aexit__(
        self,
        tipo: type[BaseException] | None,
        error: BaseException | None,
        traza: TracebackType | None,
    ) -> bool:
        self._abierto = False
        if error is None:
            try:
                await self.session.commit()
                return False
            except IntegrityError as error_al_confirmar:
                error = error_al_confirmar  # una restricción que salta al confirmar se trata igual
        # Cualquier excepción revierte, también una de dominio lanzada después de un flush.
        # Además, sin rollback la sesión queda inutilizable hasta para leer.
        await self.session.rollback()
        if isinstance(error, IntegrityError):
            # Único punto de traducción: cubre el flush de cualquier repositorio del bloque y el commit.
            raise traducir_integrity_error(error, self.mensajes_de_restriccion) from error
        return False  # la excepción sigue su curso, sin cambios
