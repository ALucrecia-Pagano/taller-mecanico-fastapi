"""Composición del Unit of Work de órdenes."""

from app.core.unit_of_work import UnitOfWork
from app.modules.ordenes.repository import EstadoOrdenRepository, OrdenTrabajoRepository, ItemOrdenRepository, HistorialEstadoRepository
from app.modules.clientes.repository import VehiculoRepository
from app.modules.repuestos.repository import RepuestoRepository
from app.modules.usuarios.repository import UsuarioRepository


class OrdenesUnitOfWork(UnitOfWork):
    mensajes_de_restriccion = {
        "fk_orden_trabajo_vehiculo_id_vehiculo": "Vehículo inexistente o dado de baja",
        "fk_orden_trabajo_estado_estado_orden": "El catálogo de estados no está disponible",
        "fk_item_orden_repuesto_id_repuesto": "Repuesto inexistente o dado de baja",
        "fk_historial_estado_orden_usuario_id_usuario": "No se pudo crear la orden",
        "fk_historial_estado_orden_hasta_estado_estado_orden": "No se pudo crear la orden",
        "fk_item_orden_orden_id_orden_trabajo": "No se pudo crear la orden",
        "uq_item_orden_orden_id_repuesto_id": "No se pudo crear la orden",
        "ck_item_orden_cantidad_positiva": "No se pudo crear la orden",
        "ck_item_orden_precio_unitario_positivo": "No se pudo crear la orden",
        "ck_orden_trabajo_total_no_negativo": "No se pudo crear la orden",
    }

    def __init__(self, session) -> None:
        super().__init__(session)
        self.estados = EstadoOrdenRepository(session)
        self.ordenes = OrdenTrabajoRepository(session)
        self.items = ItemOrdenRepository(session)
        self.historial = HistorialEstadoRepository(session)
        self.vehiculos = VehiculoRepository(session)
        self.repuestos = RepuestoRepository(session)
        self.usuarios = UsuarioRepository(session)
