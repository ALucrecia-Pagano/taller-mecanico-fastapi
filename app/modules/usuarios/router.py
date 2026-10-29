"""Rutas abiertas /auth; la autenticación individual se agrega donde corresponde."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.core.dependencies import UsuarioActualDep
from app.core.rutas import RutaQueTraduceErrores
from app.modules.usuarios.schemas import CambioPassword, Login, Mensaje, Perfil, Registro, SesionIniciada
from app.modules.usuarios.service import AuthService
from app.modules.usuarios.unit_of_work import IntentosUnitOfWork, RegistroIntentos, UsuariosUnitOfWork

router = APIRouter(prefix="/auth", tags=["Autenticación"], route_class=RutaQueTraduceErrores)


async def get_auth_service(request: Request, session: Annotated[AsyncSession, Depends(get_session)]) -> AuthService:
    return AuthService(UsuariosUnitOfWork(session), settings=get_settings(), semaforo=request.app.state.semaforo_bcrypt,
                       hash_ficticio=request.app.state.hash_ficticio,
                       registrar_intento=RegistroIntentos(request.app.state.session_factory, IntentosUnitOfWork))


AuthDep = Annotated[AuthService, Depends(get_auth_service)]

COOKIE_SESION = "access_token"


def opciones_cookie() -> dict:
    # Path=/ sin Domain: No especificado en la consigna, confirmado en el explore.
    return {"httponly": True, "samesite": "lax", "secure": get_settings().cookie_secure, "path": "/"}


def poner_cookie(response: Response, token: str) -> None:
    response.set_cookie(COOKIE_SESION, token, max_age=get_settings().jwt_expire_seconds, **opciones_cookie())


@router.post("/registro", status_code=201, response_model=Mensaje)
async def registro(datos: Registro, service: AuthDep) -> Mensaje:
    await service.registrar(datos)
    return Mensaje(mensaje="Registro completado")


@router.post("/login", response_model=SesionIniciada)
async def login(datos: Login, request: Request, response: Response, service: AuthDep) -> SesionIniciada:
    token, debe_cambiar = await service.login(datos, request.client.host)
    settings = get_settings()
    poner_cookie(response, token)
    return SesionIniciada(mensaje="Sesión iniciada", debe_cambiar_password=debe_cambiar,
                         expira_en_segundos=settings.jwt_expire_seconds)


@router.post("/logout", response_model=Mensaje)
async def logout(response: Response) -> Mensaje:
    response.delete_cookie(COOKIE_SESION, **opciones_cookie())
    return Mensaje(mensaje="Sesión cerrada")


@router.get("/yo", response_model=Perfil)
async def yo(actual: UsuarioActualDep, service: AuthDep) -> Perfil:
    return await service.perfil(actual)


@router.post("/cambiar-password", response_model=Mensaje)
async def cambiar_password(datos: CambioPassword, actual: UsuarioActualDep, response: Response,
                           service: AuthDep) -> Mensaje:
    token = await service.cambiar_password(datos, actual)
    poner_cookie(response, token)
    return Mensaje(mensaje="Contraseña actualizada")
