"""Autenticación por cookie; la autorización nace en CH-06."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Request
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.config import get_settings
from app.core.errores import PermisoDenegado, TokenInvalido
from app.core.security import DatosToken, decodificar_token
from app.modules.usuarios.models import Usuario
from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork

# [Alumna] D6 — No especificado en la consigna; no revela por qué una sesión fue rechazada.
SESION_NO_VALIDA = "Sesión no válida o vencida"


class ContextoAutenticado(BaseModel):
    usuario: Usuario
    token: DatosToken


async def get_usuario_actual(request: Request, session: Annotated[AsyncSession, Depends(get_session)]) -> ContextoAutenticado:
    # [Alumna] D6 — No especificado en la consigna: rechazo neutro, incluso sin cookie.
    try:
        cookie = request.cookies.get("access_token")
        if not cookie:
            raise TokenInvalido(SESION_NO_VALIDA)
        datos = decodificar_token(cookie, settings=get_settings())
        uow = UsuariosUnitOfWork(session)  # composición en dependencia, no en servicio
        async with uow:
            usuario = await uow.usuarios.get_by_id(datos.usuario_id)
        if usuario is None or not usuario.activo:
            raise TokenInvalido(SESION_NO_VALIDA)
        # RN-07: comparar float con timestamp, sin fromtimestamp ni truncar microsegundos.
        if usuario.password_cambiada_en is not None and datos.iat < usuario.password_cambiada_en.timestamp():
            raise TokenInvalido(SESION_NO_VALIDA)
        return ContextoAutenticado(usuario=usuario, token=datos)
    except TokenInvalido:
        raise TokenInvalido(SESION_NO_VALIDA) from None


UsuarioActualDep = Annotated[ContextoAutenticado, Depends(get_usuario_actual)]


def requiere_rol(*roles: str):
    """Cualquiera de los roles requeridos, siempre vigente en base (RN-04)."""
    async def comprobar(actual: UsuarioActualDep, session: Annotated[AsyncSession, Depends(get_session)]) -> ContextoAutenticado:
        async with UsuariosUnitOfWork(session) as uow:
            vigentes = await uow.usuarios.roles_vigentes(actual.usuario.id, datetime.now(UTC))
        if not set(roles).intersection(vigentes):
            # Texto exacto: No especificado en la consigna, D4 aprobado.
            raise PermisoDenegado("No tiene permisos para realizar esta operación")
        return actual
    return comprobar


async def controlar_cambio_obligatorio(actual: UsuarioActualDep) -> None:
    """RN-06: se declara una sola vez en el grupo protegido."""
    if actual.usuario.debe_cambiar_password:
        # Texto exacto: No especificado en la consigna, D4 aprobado.
        raise PermisoDenegado("Debe cambiar la contraseña para continuar")
