"""Datos iniciales de seed.py (spec datos-iniciales: S1-S13, S16; spec solo-agregado: S14).

Corre contra la base de prueba con la fixture base_sembrada, que la deja vacía al terminar.
"""

import asyncio
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlmodel import select

import seed
from app.core.security import verificar_password
from app.modules.clientes.models import Cliente, Vehiculo
from app.modules.ordenes.models import CodigoEstado, EstadoOrden, HistorialEstadoOrden, ItemOrden, OrdenTrabajo
from app.modules.repuestos.models import HistorialPrecio, MovimientoStock, Repuesto
from app.modules.usuarios.models import AsignacionRol, EventoSeguridad, Usuario
from fabricas import rechazada_sql
from guarda import verificar_base_de_prueba
from test_solo_agregado import RESTRICT_VIOLATION, SOLO_AGREGADO, _bloques_del_archivo

RAIZ = Path(__file__).resolve().parents[2]


async def todas(sesion, consulta):
    return (await sesion.exec(consulta)).all()


IDS_ESPERADOS = {
    "usuarios": (
        select(Usuario.id, Usuario.email).order_by(Usuario.id),
        [
            (1, "admin@example.com"),
            (2, "admin2@example.com"),
            (3, "recepcion@example.com"),
            (4, "mecanico@example.com"),
            (5, "mecanico2@example.com"),
            (6, "cliente@example.com"),
            (7, "nuevo@example.com"),
        ],
    ),
    "clientes": (select(Cliente.id, Cliente.nombre).order_by(Cliente.id), [(1, "Laura Cliente"), (2, "Jorge Pérez")]),
    "vehiculos": (
        select(Vehiculo.id, Vehiculo.patente, Vehiculo.cliente_id).order_by(Vehiculo.id),
        [(1, "AB123CD", 1), (2, "AC456EF", 1), (3, "AD789GH", 2)],
    ),
    "repuestos": (
        select(Repuesto.id, Repuesto.codigo).order_by(Repuesto.id),
        [(1, "FIL-001"), (2, "FRE-010"), (3, "BUJ-020"), (4, "ACE-530")],
    ),
    "ordenes": (select(OrdenTrabajo.id, OrdenTrabajo.vehiculo_id).order_by(OrdenTrabajo.id), [(1, 1), (2, 3)]),
}


@pytest.mark.parametrize("entidad", IDS_ESPERADOS)
async def test_s1_cada_id_con_su_clave_natural(base_sembrada, entidad):
    consulta, esperado = IDS_ESPERADOS[entidad]
    async with base_sembrada() as sesion:
        assert [tuple(fila) for fila in await todas(sesion, consulta)] == esperado


async def test_s2_totales_e_items(base_sembrada):
    async with base_sembrada() as sesion:
        ordenes = await todas(sesion, select(OrdenTrabajo.id, OrdenTrabajo.estado, OrdenTrabajo.mecanico_id, OrdenTrabajo.total).order_by(OrdenTrabajo.id))
        items = await todas(
            sesion,
            select(ItemOrden.orden_id, Repuesto.codigo, ItemOrden.cantidad, ItemOrden.precio_unitario)
            .join(Repuesto)
            .order_by(ItemOrden.orden_id, Repuesto.codigo),
        )
        bujia = (await sesion.exec(select(Repuesto.stock).where(Repuesto.codigo == "BUJ-020"))).one()

    assert [tuple(o) for o in ordenes] == [
        (1, "PENDIENTE", None, Decimal("56500.00")),
        (2, "EN_REPARACION", 4, Decimal("24000.00")),
    ]
    assert [tuple(i) for i in items] == [
        (1, "ACE-530", 4, Decimal("12000.00")),
        (1, "FIL-001", 1, Decimal("8500.00")),
        (2, "BUJ-020", 4, Decimal("6000.00")),
    ]
    assert bujia == 2  # la orden 2 no descuenta: el stock se mueve al terminar (C-11)


async def test_s3_stock_igual_a_la_suma_de_movimientos(base_sembrada):
    async with base_sembrada() as sesion:
        repuestos = await todas(sesion, select(Repuesto).order_by(Repuesto.id))
        movimientos = await todas(sesion, select(MovimientoStock).order_by(MovimientoStock.id))

    assert [r.stock for r in repuestos] == [10, 4, 2, 20]
    for repuesto in repuestos:
        propios = [m for m in movimientos if m.repuesto_id == repuesto.id]
        assert [(m.motivo, m.cantidad, m.orden_id, m.usuario_id) for m in propios] == [
            ("Stock inicial", repuesto.stock, None, 1)
        ]
        assert repuesto.stock == sum(m.cantidad for m in propios)


async def test_s4_historiales_de_precio_y_de_estado(base_sembrada):
    async with base_sembrada() as sesion:
        precios = await todas(sesion, select(HistorialPrecio))
        estados = await todas(sesion, select(HistorialEstadoOrden).order_by(HistorialEstadoOrden.id))

    assert [(p.repuesto_id, p.precio_anterior, p.precio_nuevo, p.usuario_id) for p in precios] == [
        (1, Decimal("8000.00"), Decimal("8500.00"), 1)
    ]
    assert [(h.orden_id, h.desde_estado, h.hasta_estado, h.usuario_id) for h in estados] == [
        (1, None, "PENDIENTE", 3),
        (2, None, "PENDIENTE", 3),
        (2, "PENDIENTE", "EN_REPARACION", 4),
    ]


async def test_s5_catalogo_igual_al_contrato(base_sembrada):
    async with base_sembrada() as sesion:
        catalogo = await todas(sesion, select(EstadoOrden).order_by(EstadoOrden.posicion))

    assert {e.codigo for e in catalogo} == {c.value for c in CodigoEstado}
    assert [(e.codigo, e.posicion, e.es_final, e.descripcion) for e in catalogo] == [
        ("PENDIENTE", 1, False, "Pendiente"),
        ("EN_REPARACION", 2, False, "En reparación"),
        ("TERMINADA", 3, True, "Terminada"),
        ("CANCELADA", 4, True, "Cancelada"),
    ]


async def test_s6_roles_y_banderas(base_sembrada):
    async with base_sembrada() as sesion:
        usuarios = await todas(sesion, select(Usuario).order_by(Usuario.id))
        asignaciones = await todas(sesion, select(AsignacionRol).order_by(AsignacionRol.usuario_id))

    roles = {a.usuario_id: a.rol for a in asignaciones}
    assert len(asignaciones) == 7 and len(roles) == 7  # una sola asignación por usuario
    assert [roles[u.id] for u in usuarios] == ["ADMIN", "ADMIN", "RECEPCION", "MECANICO", "MECANICO", "CLIENTE", "MECANICO"]
    assert all(a.vence_en is None and a.revocada_en is None and a.otorgada_por is None for a in asignaciones)
    assert all(u.activo and u.password_cambiada_en is None for u in usuarios)
    assert [u.email for u in usuarios if u.debe_cambiar_password] == ["nuevo@example.com"]


async def test_s7_contrasena_comun_con_hashes_distintos(base_sembrada):
    async with base_sembrada() as sesion:
        hashes = (await sesion.exec(select(Usuario.password_hash))).all()

    semaforo = asyncio.Semaphore(4)
    verificadas = await asyncio.gather(
        *(verificar_password(seed.CONTRASENA_DEL_SEED, h, semaforo=semaforo) for h in hashes)
    )
    assert len(hashes) == 7
    assert all(verificadas)
    assert len(set(hashes)) == 7


async def test_s8_un_evento_sistema(base_sembrada):
    async with base_sembrada() as sesion:
        eventos = await todas(sesion, select(EventoSeguridad))

    assert [(e.actor, e.accion) for e in eventos] == [("SISTEMA", "Carga de los datos iniciales")]


def _sin_hashes(foto: dict) -> dict:
    # El password_hash cambia en cada corrida (sal nueva): S7 lo verifica aparte.
    columna = 3  # id, email, nombre, password_hash, ...
    return foto | {"usuario": [fila[:columna] + fila[columna + 1 :] for fila in foto["usuario"]]}


async def test_s9_dos_corridas_el_mismo_estado(base_sembrada, settings_de_prueba, foto_de_la_base):
    async with base_sembrada() as sesion:
        antes = await foto_de_la_base(sesion)

    await seed.sembrar(settings_de_prueba.model_copy(update={"bcrypt_cost": 4}))

    async with base_sembrada() as sesion:
        despues = await foto_de_la_base(sesion)
    assert len(antes) == 13
    assert _sin_hashes(despues) == _sin_hashes(antes)


async def test_s10_base_con_datos_de_solo_agregado(base_sembrada, settings_de_prueba):
    async with base_sembrada() as sesion:
        sesion.add_all(
            [
                HistorialEstadoOrden(orden_id=1, desde_estado="PENDIENTE", hasta_estado="CANCELADA", usuario_id=6),
                MovimientoStock(repuesto_id=1, usuario_id=1, cantidad=5, motivo="Reposición"),
                HistorialPrecio(repuesto_id=1, usuario_id=1, precio_anterior=Decimal("8500.00"), precio_nuevo=Decimal("9000.00")),
            ]
        )
        await sesion.commit()

    await seed.sembrar(settings_de_prueba.model_copy(update={"bcrypt_cost": 4}))

    async with base_sembrada() as sesion:
        cantidades = {t: await sesion.scalar(text(f"SELECT count(*) FROM {t}")) for t in SOLO_AGREGADO}
    assert cantidades == {"historial_estado_orden": 3, "movimiento_stock": 4, "historial_precio_repuesto": 1}


async def test_s11_version_de_migraciones_intacta(base_sembrada, settings_de_prueba):
    consulta = text("SELECT version_num FROM alembic_version")
    async with base_sembrada() as sesion:
        antes = (await sesion.exec(consulta)).scalars().all()

    await seed.sembrar(settings_de_prueba.model_copy(update={"bcrypt_cost": 4}))

    async with base_sembrada() as sesion:
        assert (await sesion.exec(consulta)).scalars().all() == antes == ["0002"]


async def test_s12_falla_a_mitad(base_sembrada, settings_de_prueba, foto_de_la_base, monkeypatch):
    async with base_sembrada() as sesion:
        antes = await foto_de_la_base(sesion)

    async def falla(sesion):
        raise RuntimeError("falla provocada después del vaciado")

    monkeypatch.setattr(seed, "_cargar_evento", falla)
    with pytest.raises(RuntimeError, match="falla provocada"):
        await seed.sembrar(settings_de_prueba.model_copy(update={"bcrypt_cost": 4}))

    async with base_sembrada() as sesion:
        assert await foto_de_la_base(sesion) == antes  # ni el TRUNCATE quedó: todo o nada


async def test_s13_corrida_real(base_sembrada, settings_de_prueba, base_de_prueba):
    verificar_base_de_prueba(settings_de_prueba)
    resultado = subprocess.run(
        [sys.executable, "seed.py"],
        cwd=RAIZ,
        env={**os.environ, "POSTGRES_DB": base_de_prueba, "BCRYPT_COST": "4"},
        capture_output=True,
        text=True,
        timeout=120,
    )
    salida = resultado.stdout + resultado.stderr

    assert resultado.returncode == 0, salida
    assert base_de_prueba in salida
    assert f"{settings_de_prueba.postgres_host}:{settings_de_prueba.postgres_port}" in salida
    assert settings_de_prueba.postgres_password.get_secret_value() not in salida
    async with base_sembrada() as sesion:
        assert await sesion.scalar(text("SELECT count(*) FROM usuario")) == 7


async def test_s14_c14_sobre_el_seed(base_sembrada):
    verificacion, *sentencias = _bloques_del_archivo()

    async with base_sembrada() as sesion:
        async with sesion.begin_nested():
            await sesion.exec(text(verificacion))  # con el seed, la verificación no corta
        for sentencia in sentencias[:6]:
            await rechazada_sql(sesion, text(sentencia), RESTRICT_VIOLATION)
        await rechazada_sql(sesion, text(sentencias[6]), "23503", "fk_orden_trabajo_estado_estado_orden")


def test_s16_la_contrasena_vive_solo_en_el_seed():
    excluidas = {".venv", "__pycache__", ".git"}
    revisados = [p for p in RAIZ.rglob("*.py") if not excluidas & set(p.relative_to(RAIZ).parts)]

    con_la_contrasena = [
        str(p.relative_to(RAIZ)) for p in revisados if seed.CONTRASENA_DEL_SEED in p.read_text(encoding="utf-8")
    ]

    assert RAIZ / "main.py" in revisados
    assert con_la_contrasena == ["seed.py"]
