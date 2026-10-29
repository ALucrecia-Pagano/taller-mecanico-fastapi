"""Deja la base en el estado inicial conocido: vacía las tablas y carga los datos iniciales del PDF.

Uso, después de `alembic upgrade head` y antes de cada archivo .http:
    python seed.py

Es parte de la puesta en marcha y no un extra: sin el catálogo de estados no se puede crear ninguna
orden. Los ids salen del orden de alta y coinciden con los ejemplos del PDF (DA-02 a DA-06).
"""

import asyncio
import sys
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlmodel import SQLModel

from app.core.config import Settings, get_settings
from app.core.database import crear_fabrica_de_sesiones, crear_motor
from app.core.security import hashear_password
from app.modules.clientes.models import Cliente, Vehiculo
from app.modules.ordenes.models import CodigoEstado, EstadoOrden, HistorialEstadoOrden, ItemOrden, OrdenTrabajo
from app.modules.repuestos.models import HistorialPrecio, MovimientoStock, Repuesto
from app.modules.usuarios.models import AsignacionRol, EventoSeguridad, Rol, Usuario

# Ficticia, común a todos los usuarios del seed, y vive sólo en este archivo (DA-01). Los tests la importan.
CONTRASENA_DEL_SEED = "Taller2026!"

# Sin esquema: mensaje propio en lugar de la traza (No especificado en la consigna, decisión de la alumna).
SIN_ESQUEMA = "Corré `alembic upgrade head` primero"
SQLSTATE_TABLA_INEXISTENTE = "42P01"  # undefined_table

# (descripción, posición, es_final). Las descripciones son No especificado en la consigna (decisión de la alumna).
CATALOGO = {
    CodigoEstado.PENDIENTE: ("Pendiente", 1, False),
    CodigoEstado.EN_REPARACION: ("En reparación", 2, False),
    CodigoEstado.TERMINADA: ("Terminada", 3, True),
    CodigoEstado.CANCELADA: ("Cancelada", 4, True),
}

# (email, nombre, rol, debe_cambiar_password), en el orden que da los ids 1 a 7 (DA-02).
USUARIOS = [
    ("admin@example.com", "Ana Admin", Rol.ADMIN, False),
    ("admin2@example.com", "Bruno Admin", Rol.ADMIN, False),
    ("recepcion@example.com", "Rita Recepción", Rol.RECEPCION, False),
    ("mecanico@example.com", "Mario Mecánico", Rol.MECANICO, False),
    ("mecanico2@example.com", "Martín Mecánico", Rol.MECANICO, False),
    ("cliente@example.com", "Laura Cliente", Rol.CLIENTE, False),
    ("nuevo@example.com", "Nico Nuevo", Rol.MECANICO, True),
]

# (nombre, documento, teléfono, email del usuario o None) (DA-03).
CLIENTES = [
    ("Laura Cliente", "30111222", "2614000001", "cliente@example.com"),
    ("Jorge Pérez", "28333444", "2614000002", None),
]

# (documento del dueño, patente, marca, modelo, año) (DA-04).
VEHICULOS = [
    ("30111222", "AB123CD", "Toyota", "Corolla", 2018),
    ("30111222", "AC456EF", "Ford", "Fiesta", 2015),
    ("28333444", "AD789GH", "Volkswagen", "Gol", 2012),
]

# (código, descripción, precio, stock) (DA-05).
REPUESTOS = [
    ("FIL-001", "Filtro de aceite", Decimal("8500.00"), 10),
    ("FRE-010", "Pastillas de freno delanteras", Decimal("32000.00"), 4),
    ("BUJ-020", "Bujía de encendido", Decimal("6000.00"), 2),
    ("ACE-530", "Aceite 5W30 por litro", Decimal("12000.00"), 20),
]

# Movimientos y precio del seed a nombre de admin@ (DA-06).
AUTOR_DEL_INVENTARIO = "admin@example.com"
# (código, precio anterior, precio nuevo) (DA-05).
HISTORIAL_DE_PRECIOS = [("FIL-001", Decimal("8000.00"), Decimal("8500.00"))]

# Órdenes 1 y 2 (DA-06): la 2 pide 4 bujías cuando hay 2; no descuenta nada hasta terminarse (C-11).
ORDENES = [
    {
        "patente": "AB123CD",
        "estado": CodigoEstado.PENDIENTE,
        "mecanico": None,
        "falla": "Cambio de aceite y filtro",
        "items": [("FIL-001", 1), ("ACE-530", 4)],
        "historial": [(None, CodigoEstado.PENDIENTE, "recepcion@example.com")],
    },
    {
        "patente": "AD789GH",
        "estado": CodigoEstado.EN_REPARACION,
        "mecanico": "mecanico@example.com",
        "falla": "Falla de encendido",
        "items": [("BUJ-020", 4)],
        "historial": [
            (None, CodigoEstado.PENDIENTE, "recepcion@example.com"),
            (CodigoEstado.PENDIENTE, CodigoEstado.EN_REPARACION, "mecanico@example.com"),
        ],
    },
]

# El actor es un texto y no un usuario (DA-13).
EVENTO_DEL_SEED = ("SISTEMA", "Carga de los datos iniciales")


def sentencia_de_vaciado():
    # TRUNCATE y no DELETE: el disparador de sólo agregado es de fila y TRUNCATE no lo dispara (DA-31).
    # Las tablas salen de la metadata (nunca de una entrada), así que no toca alembic_version.
    tablas = ", ".join(tabla.name for tabla in SQLModel.metadata.sorted_tables)
    return text(f"TRUNCATE {tablas} RESTART IDENTITY CASCADE")


async def calcular_hashes(settings: Settings) -> list[str]:
    """Un hash por usuario, cada uno con su sal, antes de abrir la transacción (DD-06)."""
    semaforo = asyncio.Semaphore(settings.bcrypt_max_concurrency)  # el seed corre en su propio proceso
    return list(
        await asyncio.gather(
            *(hashear_password(CONTRASENA_DEL_SEED, costo=settings.bcrypt_cost, semaforo=semaforo) for _ in USUARIOS)
        )
    )


async def _cargar_catalogo(sesion) -> None:
    # Se carga primero: todo lo que tiene un estado apunta a él. Un estado nuevo sin fila acá hace fallar el seed.
    for codigo in CodigoEstado:
        descripcion, posicion, es_final = CATALOGO[codigo]
        sesion.add(EstadoOrden(codigo=codigo, descripcion=descripcion, posicion=posicion, es_final=es_final))
    await sesion.flush()


async def _cargar_usuarios(sesion, hashes: list[str]) -> dict[str, Usuario]:
    usuarios = {}
    for (email, nombre, _, debe_cambiar), hash_ in zip(USUARIOS, hashes, strict=True):
        usuarios[email] = Usuario(email=email, nombre=nombre, password_hash=hash_, debe_cambiar_password=debe_cambiar)
        sesion.add(usuarios[email])
        await sesion.flush()  # uno por vez: el orden de alta fija los ids
    # Sin vencimiento ni otorgante: los asigna el seed (DA-08).
    sesion.add_all(AsignacionRol(usuario_id=usuarios[email].id, rol=rol) for email, _, rol, _ in USUARIOS)
    await sesion.flush()
    return usuarios


async def _cargar_clientes_y_vehiculos(sesion, usuarios: dict[str, Usuario]) -> dict[str, Vehiculo]:
    clientes = {}
    for nombre, documento, telefono, email in CLIENTES:
        usuario_id = usuarios[email].id if email else None
        clientes[documento] = Cliente(nombre=nombre, documento=documento, telefono=telefono, usuario_id=usuario_id)
        sesion.add(clientes[documento])
        await sesion.flush()
    vehiculos = {}
    for documento, patente, marca, modelo, anio in VEHICULOS:
        vehiculos[patente] = Vehiculo(
            cliente_id=clientes[documento].id, patente=patente, marca=marca, modelo=modelo, anio=anio
        )
        sesion.add(vehiculos[patente])
        await sesion.flush()
    return vehiculos


async def _cargar_repuestos(sesion, usuarios: dict[str, Usuario]) -> dict[str, Repuesto]:
    autor = usuarios[AUTOR_DEL_INVENTARIO].id
    repuestos = {}
    for codigo, descripcion, precio, stock in REPUESTOS:
        # Excepción acotada a la puesta en marcha: el stock se escribe directo junto con su movimiento,
        # porque el punto único de stock llega en CH-08. El test S3 garantiza stock == suma de movimientos.
        repuestos[codigo] = Repuesto(codigo=codigo, descripcion=descripcion, precio=precio, stock=stock)
        sesion.add(repuestos[codigo])
        await sesion.flush()
        sesion.add(
            MovimientoStock(repuesto_id=repuestos[codigo].id, usuario_id=autor, cantidad=stock, motivo="Stock inicial")
        )
    sesion.add_all(
        HistorialPrecio(repuesto_id=repuestos[codigo].id, usuario_id=autor, precio_anterior=anterior, precio_nuevo=nuevo)
        for codigo, anterior, nuevo in HISTORIAL_DE_PRECIOS
    )
    await sesion.flush()
    return repuestos


async def _cargar_ordenes(sesion, usuarios, vehiculos, repuestos) -> None:
    for datos in ORDENES:
        items = [(repuestos[codigo], cantidad) for codigo, cantidad in datos["items"]]
        mecanico = datos["mecanico"]
        orden = OrdenTrabajo(
            vehiculo_id=vehiculos[datos["patente"]].id,
            mecanico_id=usuarios[mecanico].id if mecanico else None,
            estado=datos["estado"],
            falla=datos["falla"],
            # Calculado de los ítems, no escrito a mano: el test lo compara con los totales del PDF.
            total=sum((repuesto.precio * cantidad for repuesto, cantidad in items), Decimal("0.00")),
        )
        sesion.add(orden)
        await sesion.flush()
        sesion.add_all(
            ItemOrden(orden_id=orden.id, repuesto_id=repuesto.id, cantidad=cantidad, precio_unitario=repuesto.precio)
            for repuesto, cantidad in items
        )
        # Todas las filas comparten el now() de la transacción: el historial se ordena por (cuando, id).
        for desde, hasta, autor in datos["historial"]:
            sesion.add(
                HistorialEstadoOrden(orden_id=orden.id, desde_estado=desde, hasta_estado=hasta, usuario_id=usuarios[autor].id)
            )
            await sesion.flush()


async def _cargar_evento(sesion) -> None:
    actor, accion = EVENTO_DEL_SEED
    sesion.add(EventoSeguridad(actor=actor, accion=accion))
    await sesion.flush()


async def cargar_datos_iniciales(sesion, hashes: list[str]) -> None:
    """Vacía y carga, en el orden de CHANGES.md. No confirma: lo hace quien abrió la transacción."""
    await sesion.exec(sentencia_de_vaciado())
    await _cargar_catalogo(sesion)
    usuarios = await _cargar_usuarios(sesion, hashes)
    vehiculos = await _cargar_clientes_y_vehiculos(sesion, usuarios)
    repuestos = await _cargar_repuestos(sesion, usuarios)
    await _cargar_ordenes(sesion, usuarios, vehiculos, repuestos)
    await _cargar_evento(sesion)


async def sembrar(settings: Settings) -> None:
    """Todo en una sola transacción: si algo falla, la base queda como estaba (también el TRUNCATE)."""
    hashes = await calcular_hashes(settings)
    motor = crear_motor(settings)
    try:
        async with crear_fabrica_de_sesiones(motor)() as sesion, sesion.begin():
            await cargar_datos_iniciales(sesion, hashes)
    finally:
        await motor.dispose()


def main() -> None:
    settings = get_settings()
    # A qué base va, antes de vaciarla. Nunca la dirección completa: lleva la contraseña.
    print(f"Vaciando y cargando {settings.postgres_db} en {settings.postgres_host}:{settings.postgres_port}")
    try:
        asyncio.run(sembrar(settings))
    except ProgrammingError as error:
        # Sólo la tabla inexistente tiene mensaje propio; cualquier otro error se ve tal cual.
        if getattr(error.orig, "sqlstate", None) != SQLSTATE_TABLA_INEXISTENTE:
            raise
        sys.exit(SIN_ESQUEMA)  # código 1
    print("Datos iniciales cargados")


if __name__ == "__main__":
    main()
