"""Restricciones en la base: CHECK, UNIQUE, índices parciales y FK (spec modelo-de-datos: K1-K13, P1-P6, F1-F3).

Cada rechazo se afirma con su SQLSTATE y el nombre de la restricción, el mismo dato que usa la
traducción de CH-02 para elegir el mensaje 409.
"""

from decimal import Decimal

import pytest

import fabricas
from app.modules.clientes.models import Cliente, Vehiculo
from app.modules.ordenes.models import EstadoOrden, HistorialEstadoOrden, ItemOrden, OrdenTrabajo
from app.modules.repuestos.models import HistorialPrecio, MovimientoStock, Repuesto
from app.modules.usuarios.models import AsignacionRol, Rol, Usuario
from fabricas import AHORA, aceptado, rechazado

pytestmark = pytest.mark.usefixtures("esquema_al_dia")

CHECK, UNIQUE, FK, NOT_NULL = "23514", "23505", "23503", "23502"


def _repuesto(**datos) -> Repuesto:
    return Repuesto(**({"codigo": "K-1", "descripcion": "Filtro", "precio": Decimal("10.00"), "stock": 0} | datos))


# --- CHECK ---


async def test_k1_stock_negativo(conexion_revertida):
    await rechazado(conexion_revertida, _repuesto(codigo="K1-a", stock=-1), CHECK, "ck_repuesto_stock_no_negativo")
    await aceptado(conexion_revertida, _repuesto(codigo="K1-b", stock=0))


async def test_k2_precio_no_positivo(conexion_revertida):
    await rechazado(
        conexion_revertida, _repuesto(codigo="K2-a", precio=Decimal("0")), CHECK, "ck_repuesto_precio_positivo"
    )
    await aceptado(conexion_revertida, _repuesto(codigo="K2-b", precio=Decimal("0.01")))


async def test_k3_total_negativo(conexion_revertida):
    sesion = conexion_revertida
    vehiculo = await fabricas.vehiculo(sesion)
    await fabricas.estado(sesion)

    def orden(total):
        return OrdenTrabajo(vehiculo_id=vehiculo.id, estado="PENDIENTE", falla="Ruido", total=total)

    await rechazado(sesion, orden(Decimal("-0.01")), CHECK, "ck_orden_trabajo_total_no_negativo")
    await aceptado(sesion, orden(Decimal("0")))


async def test_k4_item_con_cantidad_o_precio_no_positivos(conexion_revertida):
    sesion = conexion_revertida
    orden = await fabricas.orden(sesion)
    repuestos = [await fabricas.repuesto(sesion) for _ in range(3)]

    def item(repuesto, cantidad, precio):
        return ItemOrden(orden_id=orden.id, repuesto_id=repuesto.id, cantidad=cantidad, precio_unitario=precio)

    await rechazado(sesion, item(repuestos[0], 0, Decimal("5.00")), CHECK, "ck_item_orden_cantidad_positiva")
    await rechazado(sesion, item(repuestos[1], 1, Decimal("0")), CHECK, "ck_item_orden_precio_unitario_positivo")
    await aceptado(sesion, item(repuestos[2], 1, Decimal("5.00")))


async def test_k5_movimiento_en_cero(conexion_revertida):
    sesion = conexion_revertida
    repuesto = await fabricas.repuesto(sesion)
    usuario = await fabricas.usuario(sesion)

    def movimiento(cantidad):
        return MovimientoStock(repuesto_id=repuesto.id, usuario_id=usuario.id, cantidad=cantidad, motivo="Prueba")

    await rechazado(sesion, movimiento(0), CHECK, "ck_movimiento_stock_cantidad_distinta_de_cero")
    await aceptado(sesion, movimiento(3))  # entrada
    await aceptado(sesion, movimiento(-3))  # salida (DD-13)


async def test_k6_cambio_de_precio_que_no_cambia(conexion_revertida):
    sesion = conexion_revertida
    repuesto = await fabricas.repuesto(sesion)
    usuario = await fabricas.usuario(sesion)

    def linea(anterior, nuevo):
        return HistorialPrecio(
            repuesto_id=repuesto.id, usuario_id=usuario.id, precio_anterior=Decimal(anterior), precio_nuevo=Decimal(nuevo)
        )

    await rechazado(sesion, linea("8500.00", "8500.00"), CHECK, "ck_historial_precio_repuesto_precio_cambia")
    await rechazado(sesion, linea("8500.00", "0"), CHECK, "ck_historial_precio_repuesto_precio_nuevo_positivo")
    await aceptado(sesion, linea("8500.00", "8000.00"))  # el precio puede bajar (RN-20)


async def test_k7_anio_fuera_de_rango(conexion_revertida):
    sesion = conexion_revertida
    cliente = await fabricas.cliente(sesion)

    def vehiculo(anio):
        return Vehiculo(cliente_id=cliente.id, patente=f"K7-{anio}", marca="Ford", modelo="Ka", anio=anio)

    for anio in (1949, 2101):
        await rechazado(sesion, vehiculo(anio), CHECK, "ck_vehiculo_anio")
    for anio in (1950, 2100):
        await aceptado(sesion, vehiculo(anio))


async def test_k8_rol_fuera_de_la_lista(conexion_revertida):
    sesion = conexion_revertida
    usuario = await fabricas.usuario(sesion)

    await rechazado(sesion, AsignacionRol(usuario_id=usuario.id, rol="JEFE"), CHECK, "ck_asignacion_rol_rol")
    for rol in Rol:
        await aceptado(sesion, AsignacionRol(usuario_id=usuario.id, rol=rol))


# --- UNIQUE y NOT NULL ---


async def test_k9_correo_repetido(conexion_revertida):
    sesion = conexion_revertida
    await fabricas.usuario(sesion, email="k9@example.com")

    await rechazado(
        sesion, Usuario(email="k9@example.com", nombre="Otro", password_hash="x"), UNIQUE, "uq_usuario_email"
    )


async def test_k10_documento_repetido_usuario_repetido_y_clientes_sin_usuario(conexion_revertida):
    sesion = conexion_revertida
    usuario = await fabricas.usuario(sesion)
    await fabricas.cliente(sesion, documento="30111222", usuario_id=usuario.id)

    await rechazado(
        sesion, Cliente(nombre="Otro", documento="30111222", telefono="1"), UNIQUE, "uq_cliente_documento"
    )
    await rechazado(
        sesion,
        Cliente(nombre="Otro", documento="K10-b", telefono="1", usuario_id=usuario.id),
        UNIQUE,
        "uq_cliente_usuario_id",
    )
    await aceptado(sesion, Cliente(nombre="Sin usuario 1", documento="K10-c", telefono="1"))
    await aceptado(sesion, Cliente(nombre="Sin usuario 2", documento="K10-d", telefono="1"))


async def test_k11_posicion_repetida_en_el_catalogo(conexion_revertida):
    sesion = conexion_revertida
    await fabricas.estado(sesion, "PENDIENTE", posicion=1)

    await rechazado(
        sesion,
        EstadoOrden(codigo="EN_REPARACION", descripcion="En reparación", posicion=1, es_final=False),
        UNIQUE,
        "uq_estado_orden_posicion",
    )


async def test_k12_repuesto_repetido_en_una_orden(conexion_revertida):
    sesion = conexion_revertida
    orden = await fabricas.orden(sesion)
    repuesto = await fabricas.repuesto(sesion)

    def item():
        return ItemOrden(orden_id=orden.id, repuesto_id=repuesto.id, cantidad=1, precio_unitario=Decimal("5.00"))

    await aceptado(sesion, item())
    await rechazado(sesion, item(), UNIQUE, "uq_item_orden_orden_id_repuesto_id")


async def test_k13_columna_obligatoria_en_null(conexion_revertida):
    sesion = conexion_revertida
    cliente = await fabricas.cliente(sesion)

    await rechazado(
        sesion, Vehiculo(cliente_id=cliente.id, patente=None, marca="Ford", modelo="Ka", anio=2015), NOT_NULL
    )


# --- Índices únicos parciales ---


async def test_p1_patente_vigente_repetida(conexion_revertida):
    sesion = conexion_revertida
    await fabricas.vehiculo(sesion, patente="AB123CD")

    await rechazado(sesion, await _vehiculo_nuevo(sesion, "AB123CD"), UNIQUE, "uq_vehiculo_patente_vigente")


async def test_p2_patente_de_un_vehiculo_dado_de_baja(conexion_revertida):
    sesion = conexion_revertida
    await fabricas.vehiculo(sesion, patente="AB123CD", borrado_en=AHORA)

    await aceptado(sesion, await _vehiculo_nuevo(sesion, "AB123CD"))  # otro cliente (base de C-19)


async def test_p3_dos_bajas_con_la_misma_patente(conexion_revertida):
    sesion = conexion_revertida
    await fabricas.vehiculo(sesion, patente="AB123CD", borrado_en=AHORA)

    vehiculo = await _vehiculo_nuevo(sesion, "AB123CD")
    vehiculo.borrado_en = AHORA
    await aceptado(sesion, vehiculo)


async def test_p4_codigo_vigente_y_dado_de_baja(conexion_revertida):
    sesion = conexion_revertida
    primero = await fabricas.repuesto(sesion, codigo="FIL-001")

    await rechazado(sesion, _repuesto(codigo="FIL-001"), UNIQUE, "uq_repuesto_codigo_vigente")
    async with sesion.begin_nested():
        primero.borrado_en = AHORA
    await aceptado(sesion, _repuesto(codigo="FIL-001"))


async def test_p5_dos_asignaciones_abiertas_del_mismo_rol(conexion_revertida):
    sesion = conexion_revertida
    usuario = await fabricas.usuario(sesion)
    await aceptado(sesion, AsignacionRol(usuario_id=usuario.id, rol=Rol.MECANICO))

    await rechazado(
        sesion, AsignacionRol(usuario_id=usuario.id, rol=Rol.MECANICO), UNIQUE, "uq_asignacion_rol_abierta"
    )


async def test_p6_rol_revocado_y_otro_rol(conexion_revertida):
    sesion = conexion_revertida
    usuario = await fabricas.usuario(sesion)
    await aceptado(sesion, AsignacionRol(usuario_id=usuario.id, rol=Rol.MECANICO, revocada_en=AHORA))

    await aceptado(sesion, AsignacionRol(usuario_id=usuario.id, rol=Rol.MECANICO))
    await aceptado(sesion, AsignacionRol(usuario_id=usuario.id, rol=Rol.ADMIN))


async def _vehiculo_nuevo(sesion, patente: str) -> Vehiculo:
    otro_cliente = await fabricas.cliente(sesion)
    return Vehiculo(cliente_id=otro_cliente.id, patente=patente, marca="Fiat", modelo="Uno", anio=2010)


# --- Claves foráneas ---


async def test_f1_orden_con_estado_inexistente(conexion_revertida):
    sesion = conexion_revertida
    vehiculo = await fabricas.vehiculo(sesion)
    await fabricas.estado(sesion)

    await rechazado(
        sesion,
        OrdenTrabajo(vehiculo_id=vehiculo.id, estado="INEXISTENTE", falla="Ruido", total=Decimal("0")),
        FK,
        "fk_orden_trabajo_estado_estado_orden",
    )


async def test_f2_historial_con_estados(conexion_revertida):
    sesion = conexion_revertida
    orden = await fabricas.orden(sesion)
    usuario = await fabricas.usuario(sesion)

    def linea(desde, hasta):
        return HistorialEstadoOrden(orden_id=orden.id, desde_estado=desde, hasta_estado=hasta, usuario_id=usuario.id)

    await rechazado(sesion, linea(None, "INEXISTENTE"), FK, "fk_historial_estado_orden_hasta_estado_estado_orden")
    await aceptado(sesion, linea(None, "PENDIENTE"))


async def test_f3_orden_de_un_vehiculo_inexistente(conexion_revertida):
    sesion = conexion_revertida
    await fabricas.estado(sesion)

    await rechazado(
        sesion,
        OrdenTrabajo(vehiculo_id=-1, estado="PENDIENTE", falla="Ruido", total=Decimal("0")),
        FK,
        "fk_orden_trabajo_vehiculo_id_vehiculo",
    )
