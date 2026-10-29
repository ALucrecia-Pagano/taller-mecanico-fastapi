"""Perfil DA-16 y roles actuales versus roles informativos del JWT (Y1-Y3)."""

import pytest
from datetime import UTC, datetime, timedelta
from sqlalchemy import text
from app.core.config import get_settings
from app.core.security import emitir_token


async def test_y1_forma_exacta_da16(cliente, base_sembrada):
    cliente.cookies.set("access_token", emitir_token(1, ["ADMIN"], settings=get_settings()))
    r = await cliente.get("/auth/yo")
    assert r.status_code == 200
    assert r.json() == {"id": 1, "email": "admin@example.com", "nombre": "Ana Admin",
                        "debe_cambiar_password": False, "roles_vigentes": ["ADMIN"], "roles_token": ["ADMIN"]}


@pytest.mark.parametrize("revocado", [True, False])
async def test_y2_roles_revocados_o_vencidos_divergen(cliente, base_sembrada, revocado):
    cliente.cookies.set("access_token", emitir_token(1, ["ADMIN"], settings=get_settings()))
    async with base_sembrada() as s:
        columna = "revocada_en" if revocado else "vence_en"
        await s.exec(text(f"UPDATE asignacion_rol SET {columna}=:fecha WHERE usuario_id=1").bindparams(fecha=datetime.now(UTC)-timedelta(seconds=1)))
        await s.commit()
    r = await cliente.get("/auth/yo")
    assert r.status_code == 200
    assert r.json()["roles_token"] == ["ADMIN"]
    assert r.json()["roles_vigentes"] == []


async def test_y3_yo_disponible_con_cambio_pendiente(cliente, base_sembrada):
    cliente.cookies.set("access_token", emitir_token(7, ["MECANICO"], settings=get_settings()))
    r = await cliente.get("/auth/yo")
    assert r.status_code == 200 and r.json()["debe_cambiar_password"] is True
