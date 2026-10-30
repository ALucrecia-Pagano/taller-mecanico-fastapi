"""Rutas de órdenes montadas bajo rutas_protegidas."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.dependencies import ContextoAutenticado, UsuarioActualDep, requiere_rol
from app.core.rutas import RutaQueTraduceErrores
from app.core.paginacion import Pagina, ParametrosDePagina, parametros_de_pagina
from app.modules.ordenes.models import CodigoEstado
from app.modules.ordenes.schemas import EntradaOrden, EstadoRespuesta, OrdenDetalle, OrdenResumen
from app.modules.ordenes.service import OrdenesService
from app.modules.ordenes.unit_of_work import OrdenesUnitOfWork

router = APIRouter(tags=["Órdenes"], route_class=RutaQueTraduceErrores)


async def get_ordenes_service(session: Annotated[AsyncSession, Depends(get_session)]) -> OrdenesService:
    return OrdenesService(OrdenesUnitOfWork(session))


ServiceDep = Annotated[OrdenesService, Depends(get_ordenes_service)]
RecepcionDep = Annotated[ContextoAutenticado, Depends(requiere_rol("RECEPCION", "ADMIN"))]
PersonalDep = Annotated[ContextoAutenticado, Depends(requiere_rol("ADMIN", "RECEPCION", "MECANICO"))]
MecanicoDep = Annotated[ContextoAutenticado, Depends(requiere_rol("MECANICO"))]
PaginaDep = Annotated[ParametrosDePagina, Depends(parametros_de_pagina)]


@router.get("/ordenes", response_model=Pagina[OrdenResumen])
async def listar_ordenes(actual: PersonalDep, service: ServiceDep, pagina: PaginaDep,
                         estado: Annotated[CodigoEstado | None, Query()] = None) -> Pagina[OrdenResumen]:
    return await service.listar(pagina.page, pagina.size, estado=estado)


@router.get("/mis-ordenes", response_model=Pagina[OrdenResumen])
async def mis_ordenes(actual: UsuarioActualDep, service: ServiceDep, pagina: PaginaDep) -> Pagina[OrdenResumen]:
    return await service.listar(pagina.page, pagina.size, usuario_id=actual.usuario.id)


@router.post("/ordenes", response_model=OrdenDetalle, status_code=201)
async def crear_orden(datos: EntradaOrden, actual: RecepcionDep, service: ServiceDep) -> OrdenDetalle:
    return await service.crear(datos, actual.usuario.id)


@router.get("/ordenes/{id}", response_model=OrdenDetalle)
async def obtener_orden(id: int, actual: UsuarioActualDep, service: ServiceDep) -> OrdenDetalle:
    return await service.obtener(id, actual.usuario.id)


@router.get("/estados-orden", response_model=list[EstadoRespuesta])
async def estados_orden(actual: UsuarioActualDep, service: ServiceDep) -> list[EstadoRespuesta]:
    return await service.estados()


@router.post("/ordenes/{id}/iniciar", response_model=OrdenDetalle)
async def iniciar_orden(id: int, actual: MecanicoDep, service: ServiceDep) -> OrdenDetalle:
    return await service.iniciar(id, actual.usuario.id)


@router.post("/ordenes/{id}/terminar", response_model=OrdenDetalle)
async def terminar_orden(
    id: int,
    background_tasks: BackgroundTasks,
    actual: UsuarioActualDep,
    service: ServiceDep,
) -> OrdenDetalle:
    detalle, cliente_id = await service.terminar(id, actual.usuario.id)
    from app.modules.ordenes.service import avisar_cliente

    background_tasks.add_task(avisar_cliente, detalle.id, cliente_id)
    return detalle


@router.post("/ordenes/{id}/cancelar", response_model=OrdenDetalle)
async def cancelar_orden(id: int, actual: UsuarioActualDep, service: ServiceDep) -> OrdenDetalle:
    return await service.cancelar(id, actual.usuario.id)
