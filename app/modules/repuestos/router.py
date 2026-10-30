from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.dependencies import ContextoAutenticado, UsuarioActualDep, requiere_rol
from app.core.paginacion import Pagina, ParametrosDePagina, parametros_de_pagina
from app.core.rutas import RutaQueTraduceErrores
from app.modules.repuestos.schemas import (
    EntradaReponer,
    EntradaRepuesto,
    EntradaRepuestoPatch,
    MovimientoRespuesta,
    PrecioRespuesta,
    RepuestoRespuesta,
)
from app.modules.repuestos.service import RepuestosService
from app.modules.repuestos.unit_of_work import RepuestosUnitOfWork

router = APIRouter(tags=["Repuestos"], route_class=RutaQueTraduceErrores)
LecturaDep = Annotated[ContextoAutenticado, Depends(requiere_rol("ADMIN", "RECEPCION", "MECANICO"))]
AdminDep = Annotated[ContextoAutenticado, Depends(requiere_rol("ADMIN"))]


async def get_service(session: Annotated[AsyncSession, Depends(get_session)]) -> RepuestosService:
    return RepuestosService(RepuestosUnitOfWork(session))


ServiceDep = Annotated[RepuestosService, Depends(get_service)]


@router.get("/repuestos", response_model=Pagina[RepuestoRespuesta])
async def listar_repuestos(
    request: Request,
    actual: LecturaDep,
    service: ServiceDep,
    pagina: Annotated[ParametrosDePagina, Depends(parametros_de_pagina)],
    q: str | None = None,
):
    if q is None and "q" in request.query_params:
        q = ""
    return await service.listar(q, pagina.page, pagina.size)


@router.get("/repuestos/{id}", response_model=RepuestoRespuesta)
async def obtener_repuesto(id: int, actual: LecturaDep, service: ServiceDep):
    return await service.obtener(id)


@router.post("/repuestos", status_code=status.HTTP_201_CREATED, response_model=RepuestoRespuesta)
async def crear_repuesto(datos: EntradaRepuesto, actual: AdminDep, service: ServiceDep):
    return await service.crear(datos, actual.usuario.id)


@router.patch("/repuestos/{id}", response_model=RepuestoRespuesta)
async def actualizar_repuesto(id: int, datos: EntradaRepuestoPatch, actual: AdminDep, service: ServiceDep):
    return await service.actualizar(id, datos, actual.usuario.id)


@router.delete("/repuestos/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def borrar_repuesto(id: int, actual: AdminDep, service: ServiceDep) -> Response:
    await service.borrar(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/repuestos/{id}/reponer", response_model=RepuestoRespuesta)
async def reponer_repuesto(id: int, datos: EntradaReponer, actual: AdminDep, service: ServiceDep):
    return await service.reponer(id, datos, actual.usuario.id)


@router.get("/repuestos/{id}/movimientos", response_model=list[MovimientoRespuesta])
async def movimientos_repuesto(id: int, actual: AdminDep, service: ServiceDep):
    return await service.movimientos(id)


@router.get("/repuestos/{id}/precios", response_model=list[PrecioRespuesta])
async def precios_repuesto(id: int, actual: AdminDep, service: ServiceDep):
    return await service.precios(id)
