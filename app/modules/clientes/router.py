"""Rutas protegidas de clientes y vehículos."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.dependencies import ContextoAutenticado, UsuarioActualDep, requiere_rol
from app.core.rutas import RutaQueTraduceErrores
from app.modules.clientes.schemas import ClienteRespuesta, EntradaCliente, EntradaVehiculo, VehiculoRespuesta
from app.modules.clientes.service import ClientesService
from app.modules.clientes.unit_of_work import ClientesUnitOfWork

router = APIRouter(tags=["Clientes"], route_class=RutaQueTraduceErrores)
RecepcionDep = Annotated[ContextoAutenticado, Depends(requiere_rol("RECEPCION", "ADMIN"))]


async def get_clientes_service(session: Annotated[AsyncSession, Depends(get_session)]) -> ClientesService:
    return ClientesService(ClientesUnitOfWork(session))


ServiceDep = Annotated[ClientesService, Depends(get_clientes_service)]


@router.post("/clientes", status_code=status.HTTP_201_CREATED, response_model=ClienteRespuesta)
async def crear_cliente(datos: EntradaCliente, actual: RecepcionDep, service: ServiceDep) -> ClienteRespuesta:
    return await service.crear_cliente(datos)


@router.get("/clientes/{id}", response_model=ClienteRespuesta)
async def obtener_cliente(id: int, actual: RecepcionDep, service: ServiceDep) -> ClienteRespuesta:
    return await service.obtener_cliente(id)


@router.post("/clientes/{id}/vehiculos", status_code=status.HTTP_201_CREATED, response_model=VehiculoRespuesta)
async def crear_vehiculo(id: int, datos: EntradaVehiculo, actual: RecepcionDep,
                         service: ServiceDep) -> VehiculoRespuesta:
    return await service.crear_vehiculo(id, datos)


@router.delete("/vehiculos/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def borrar_vehiculo(id: int, actual: RecepcionDep, service: ServiceDep) -> Response:
    await service.dar_de_baja(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/mis-vehiculos", response_model=list[VehiculoRespuesta])
async def mis_vehiculos(actual: UsuarioActualDep, service: ServiceDep) -> list[VehiculoRespuesta]:
    return await service.mis_vehiculos(actual.usuario.id)
