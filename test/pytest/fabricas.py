"""Factorías mínimas sobre la sesión revertida (design D9): sólo lo que cada escenario necesita.

Los valores únicos (correo, documento, patente, código) salen de un contador, porque las filas
de un test se revierten pero las secuencias no: nada asume ids fijos.
"""

from datetime import datetime, timezone
from decimal import Decimal
from itertools import count

import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.clientes.models import Cliente, Vehiculo
from app.modules.ordenes.models import EstadoOrden, OrdenTrabajo
from app.modules.repuestos.models import Repuesto
from app.modules.usuarios.models import Usuario

_numero = count(1)

AHORA = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)


async def guardar(sesion, entidad):
    sesion.add(entidad)
    await sesion.flush()
    return entidad


async def usuario(sesion, **datos) -> Usuario:
    n = next(_numero)
    datos = {"email": f"u{n}@example.com", "nombre": f"Usuario {n}", "password_hash": "x"} | datos
    return await guardar(sesion, Usuario(**datos))


async def cliente(sesion, **datos) -> Cliente:
    n = next(_numero)
    datos = {"nombre": f"Cliente {n}", "documento": f"D{n}", "telefono": "2614000000"} | datos
    return await guardar(sesion, Cliente(**datos))


async def vehiculo(sesion, **datos) -> Vehiculo:
    if "cliente_id" not in datos:
        datos["cliente_id"] = (await cliente(sesion)).id
    datos = {"patente": f"P{next(_numero)}", "marca": "Ford", "modelo": "Fiesta", "anio": 2015} | datos
    return await guardar(sesion, Vehiculo(**datos))


async def repuesto(sesion, **datos) -> Repuesto:
    n = next(_numero)
    datos = {"codigo": f"R-{n}", "descripcion": f"Repuesto {n}", "precio": Decimal("100.00"), "stock": 10} | datos
    return await guardar(sesion, Repuesto(**datos))


async def estado(sesion, codigo: str = "PENDIENTE", posicion: int = 1, es_final: bool = False) -> EstadoOrden:
    existente = await sesion.get(EstadoOrden, codigo)
    if existente is not None:
        return existente
    return await guardar(sesion, EstadoOrden(codigo=codigo, descripcion=codigo, posicion=posicion, es_final=es_final))


async def orden(sesion, **datos) -> OrdenTrabajo:
    if "vehiculo_id" not in datos:
        datos["vehiculo_id"] = (await vehiculo(sesion)).id
    await estado(sesion)
    datos = {"estado": "PENDIENTE", "falla": "Ruido", "total": Decimal("0")} | datos
    return await guardar(sesion, OrdenTrabajo(**datos))


async def rechazado(sesion, entidad, sqlstate: str, restriccion: str | None = None) -> IntegrityError:
    """Afirma que guardar la entidad viola la restricción esperada, dentro de un SAVEPOINT."""
    with pytest.raises(IntegrityError) as error:
        async with sesion.begin_nested():
            await guardar(sesion, entidad)
    if entidad in sesion:  # la entidad rechazada no sigue pendiente en la sesión
        sesion.expunge(entidad)
    original = error.value.orig
    assert original.sqlstate == sqlstate
    if restriccion is not None:
        assert original.__cause__.constraint_name == restriccion
    return error.value


async def rechazada_sql(sesion, sentencia, sqlstate: str, restriccion: str | None = None) -> IntegrityError:
    """Igual que `rechazado`, para una sentencia SQL (UPDATE, DELETE o INSERT literal)."""
    with pytest.raises(IntegrityError) as error:
        async with sesion.begin_nested():
            await sesion.exec(sentencia)
    original = error.value.orig
    assert original.sqlstate == sqlstate
    if restriccion is not None:
        assert original.__cause__.constraint_name == restriccion
    return error.value


async def aceptado(sesion, entidad):
    """Guarda la entidad dentro de un SAVEPOINT; si la base la rechaza, el test falla."""
    async with sesion.begin_nested():
        return await guardar(sesion, entidad)
