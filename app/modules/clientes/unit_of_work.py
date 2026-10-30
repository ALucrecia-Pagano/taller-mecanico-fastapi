"""Unit of Work del módulo de clientes."""

from app.core.unit_of_work import UnitOfWork
from app.modules.clientes.repository import ClienteRepository, VehiculoRepository


class ClientesUnitOfWork(UnitOfWork):
    mensajes_de_restriccion = {
        "uq_cliente_documento": "Ya existe un cliente con ese documento",
        "uq_vehiculo_patente_vigente": "Ya existe un vehículo vigente con esa patente",
    }

    def __init__(self, session) -> None:
        super().__init__(session)
        self.clientes = ClienteRepository(session)
        self.vehiculos = VehiculoRepository(session)
