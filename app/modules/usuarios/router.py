"""Rutas abiertas /auth; la autenticación individual se agrega donde corresponde."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.core.dependencies import ContextoAutenticado, UsuarioActualDep, requiere_rol
from app.core.rutas import RutaQueTraduceErrores
from app.modules.usuarios.schemas import CambioPassword, Login, Mensaje, Perfil, Registro, SesionIniciada
from app.modules.usuarios.service import AuthService
from app.modules.usuarios.service import UsuariosService
from app.modules.usuarios.schemas import AltaPersonal, AsignacionRespuesta, AsignarRol, PersonalRespuesta
from app.modules.usuarios.unit_of_work import IntentosUnitOfWork, RegistroIntentos, UsuariosUnitOfWork
from app.modules.usuarios.models import Rol
from app.modules.usuarios.schemas import EventoRespuesta
from app.core.paginacion import Pagina, ParametrosDePagina, parametros_de_pagina

router = APIRouter(prefix="/auth", tags=["Autenticación"], route_class=RutaQueTraduceErrores)
usuarios_router = APIRouter(prefix="/usuarios", tags=["Usuarios"], route_class=RutaQueTraduceErrores)
eventos_router = APIRouter(prefix="/eventos", tags=["Eventos"], route_class=RutaQueTraduceErrores)
AdminDep = Annotated[ContextoAutenticado, Depends(requiere_rol("ADMIN"))]


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


async def get_usuarios_service(request: Request, session: Annotated[AsyncSession, Depends(get_session)]) -> UsuariosService:
    return UsuariosService(UsuariosUnitOfWork(session), settings=get_settings(), semaforo=request.app.state.semaforo_bcrypt)


UsuariosDep = Annotated[UsuariosService, Depends(get_usuarios_service)]


@usuarios_router.post("", status_code=201, response_model=PersonalRespuesta)
async def alta_personal(datos: AltaPersonal, actual: AdminDep, service: UsuariosDep) -> PersonalRespuesta:
    return await service.alta(datos, actual)


@usuarios_router.post("/{id}/roles", status_code=201, response_model=AsignacionRespuesta)
async def asignar_rol(id: int, datos: AsignarRol, actual: AdminDep, service: UsuariosDep) -> AsignacionRespuesta:
    return await service.asignar_rol(id, datos, actual)


@usuarios_router.get("/{id}/roles", response_model=list[AsignacionRespuesta])
async def historial_roles(id: int, actual: AdminDep, service: UsuariosDep) -> list[AsignacionRespuesta]:
    return await service.historial_roles(id)


@usuarios_router.delete("/{id}/roles/{rol}", response_model=AsignacionRespuesta)
async def revocar_rol(id: int, rol: Rol, actual: AdminDep, service: UsuariosDep) -> AsignacionRespuesta:
    return await service.revocar_rol(id, rol, actual)


@eventos_router.get("", response_model=Pagina[EventoRespuesta])
async def eventos(actual: AdminDep, service: UsuariosDep,
                  pagina: Annotated[ParametrosDePagina, Depends(parametros_de_pagina)]) -> Pagina[EventoRespuesta]:
    return await service.eventos(pagina)
