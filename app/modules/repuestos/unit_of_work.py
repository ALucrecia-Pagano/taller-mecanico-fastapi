from app.core.unit_of_work import UnitOfWork
from app.modules.repuestos.repository import HistorialPrecioRepository, MovimientoStockRepository, RepuestoRepository


class RepuestosUnitOfWork(UnitOfWork):
    mensajes_de_restriccion = {
        "uq_repuesto_codigo_vigente": "Ya existe un repuesto vigente con ese código",
        "ck_historial_precio_repuesto_precio_cambia": "El precio nuevo debe ser distinto del actual",
        "ck_repuesto_stock_no_negativo": "El stock no puede quedar negativo",
    }

    def __init__(self, session) -> None:
        super().__init__(session)
        self.repuestos = RepuestoRepository(session)
        self.movimientos = MovimientoStockRepository(session)
        self.precios = HistorialPrecioRepository(session)
