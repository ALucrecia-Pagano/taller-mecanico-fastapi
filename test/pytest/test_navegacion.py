"""Tipos y navegación ORM (spec modelo-de-datos: T1-T4 y T6; T5 está en test_modelos.py)."""

from decimal import Decimal

import pytest
from sqlalchemy import event, func
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import selectinload
from sqlmodel import select

import fabricas
from app.modules.clientes.models import Cliente, Vehiculo
from app.modules.ordenes.models import HistorialEstadoOrden, ItemOrden, OrdenTrabajo
from app.modules.repuestos.models import Repuesto
from app.modules.usuarios.models import Usuario
from fabricas import AHORA

pytestmark = pytest.mark.usefixtures("esquema_al_dia")


async def _releer(sesion, modelo, id_, *precargas):
    """Vuelve a leer de la base: sin el identity map, el valor sale de la fila guardada."""
    sesion.expunge_all()
    consulta = select(modelo).where(modelo.id == id_).options(*precargas)
    return (await sesion.exec(consulta)).one()


async def test_t1_el_dinero_vuelve_como_decimal_exacto(conexion_revertida):
    repuesto = await fabricas.repuesto(conexion_revertida, precio=Decimal("8500.00"))

    releido = await _releer(conexion_revertida, Repuesto, repuesto.id)

    assert type(releido.precio) is Decimal
    assert releido.precio == Decimal("8500.00")
    assert str(releido.precio) == "8500.00"


async def test_t2_la_fecha_vuelve_con_zona(conexion_revertida):
    vehiculo = await fabricas.vehiculo(conexion_revertida, borrado_en=AHORA)

    releido = await _releer(conexion_revertida, Vehiculo, vehiculo.id)

    assert releido.borrado_en.tzinfo is not None
    assert releido.borrado_en == AHORA


async def test_t3_usuario_cliente_es_un_objeto_o_nada(conexion_revertida):
    sesion = conexion_revertida
    con_ficha = await fabricas.usuario(sesion)
    await fabricas.cliente(sesion, usuario_id=con_ficha.id, documento="T3-1")
    sin_ficha = await fabricas.usuario(sesion)

    leido_con = await _releer(sesion, Usuario, con_ficha.id, selectinload(Usuario.cliente))
    leido_sin = await _releer(sesion, Usuario, sin_ficha.id, selectinload(Usuario.cliente))

    assert isinstance(leido_con.cliente, Cliente)
    assert leido_con.cliente.documento == "T3-1"
    assert leido_sin.cliente is None


async def test_t4_relacion_no_precargada_falla_sin_consultar(conexion_revertida, motor_del_esquema):
    sesion = conexion_revertida
    orden = await fabricas.orden(sesion)
    leida = await _releer(sesion, OrdenTrabajo, orden.id)
    sentencias = []

    def contar(*_):
        sentencias.append(1)

    event.listen(motor_del_esquema.sync_engine, "before_cursor_execute", contar)
    try:
        with pytest.raises(InvalidRequestError, match="lazy='raise'"):
            leida.items
    finally:
        event.remove(motor_del_esquema.sync_engine, "before_cursor_execute", contar)

    assert sentencias == []


async def test_t6_orden_con_items_e_historial_en_un_solo_alta(conexion_revertida):
    sesion = conexion_revertida
    vehiculo = await fabricas.vehiculo(sesion)
    usuario = await fabricas.usuario(sesion)
    filtro, aceite = await fabricas.repuesto(sesion), await fabricas.repuesto(sesion)
    await fabricas.estado(sesion)

    orden = OrdenTrabajo(
        vehiculo_id=vehiculo.id,
        estado="PENDIENTE",
        falla="Cambio de aceite y filtro",
        total=Decimal("56500.00"),
        items=[
            ItemOrden(repuesto_id=filtro.id, cantidad=1, precio_unitario=Decimal("8500.00")),
            ItemOrden(repuesto_id=aceite.id, cantidad=4, precio_unitario=Decimal("12000.00")),
        ],
        historial=[HistorialEstadoOrden(hasta_estado="PENDIENTE", usuario_id=usuario.id)],
    )
    await fabricas.guardar(sesion, orden)

    items = await sesion.scalar(select(func.count()).select_from(ItemOrden).where(ItemOrden.orden_id == orden.id))
    historial = await sesion.scalar(
        select(func.count()).select_from(HistorialEstadoOrden).where(HistorialEstadoOrden.orden_id == orden.id)
    )
    assert orden.id is not None
    assert (items, historial) == (2, 1)
