"""Reglas de negocio de clientes y vehículos."""

from app.core.errores import Conflicto, NoEncontrado
from app.modules.clientes.models import Cliente, Vehiculo
from app.modules.clientes.schemas import ClienteRespuesta, EntradaCliente, EntradaVehiculo, VehiculoRespuesta


class ClientesService:
    def __init__(self, uow) -> None:
        self.uow = uow

    async def crear_cliente(self, datos: EntradaCliente) -> ClienteRespuesta:
        async with self.uow:
            cliente = await self.uow.clientes.add(
                Cliente(nombre=datos.nombre, documento=datos.documento, telefono=datos.telefono)
            )
        return ClienteRespuesta(
            id=cliente.id,
            usuario_id=cliente.usuario_id,
            nombre=cliente.nombre,
            documento=cliente.documento,
            telefono=cliente.telefono,
            vehiculos=[],
        )

    async def obtener_cliente(self, cliente_id: int) -> ClienteRespuesta:
        async with self.uow:
            cliente = await self.uow.clientes.get_by_id_with_vehiculos(cliente_id)
            if cliente is None:
                raise NoEncontrado("Cliente no encontrado")
            vehiculos = sorted(cliente.vehiculos, key=lambda vehiculo: vehiculo.id)
            return ClienteRespuesta(
                id=cliente.id,
                usuario_id=cliente.usuario_id,
                nombre=cliente.nombre,
                documento=cliente.documento,
                telefono=cliente.telefono,
                vehiculos=[VehiculoRespuesta.model_validate(v) for v in vehiculos],
            )

    async def crear_vehiculo(self, cliente_id: int, datos: EntradaVehiculo) -> VehiculoRespuesta:
        async with self.uow:
            if await self.uow.clientes.get_by_id(cliente_id) is None:
                raise NoEncontrado("Cliente no encontrado")
            vehiculo = await self.uow.vehiculos.add(
                Vehiculo(cliente_id=cliente_id, patente=datos.patente, marca=datos.marca,
                         modelo=datos.modelo, anio=datos.anio)
            )
        return VehiculoRespuesta.model_validate(vehiculo)

    async def dar_de_baja(self, vehiculo_id: int) -> None:
        async with self.uow:
            vehiculo = await self.uow.vehiculos.get_by_id(vehiculo_id)
            if vehiculo is None:
                raise NoEncontrado("Vehículo no encontrado")
            if await self.uow.vehiculos.tiene_orden_abierta(vehiculo_id):
                raise Conflicto("El vehículo tiene órdenes abiertas")
            await self.uow.vehiculos.soft_delete(vehiculo)

    async def mis_vehiculos(self, usuario_id: int) -> list[VehiculoRespuesta]:
        async with self.uow:
            cliente = await self.uow.clientes.get_by_usuario_id(usuario_id)
            if cliente is None:
                return []
            vehiculos = await self.uow.vehiculos.propios_vigentes(usuario_id)
            return [VehiculoRespuesta.model_validate(v) for v in vehiculos]
