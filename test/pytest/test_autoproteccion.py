"""AD1-4: RN-05, regla defensiva y excepción temporal acordada."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from app.core.errores import Conflicto
from app.modules.usuarios.service import proteger_revocacion_admin
from auth_helpers import foto_auth
from test_autorizacion import cookie


@pytest.mark.parametrize("actor,objetivo,respaldo,mensaje", [
    (1,1,1,"No puede revocarse su propio rol ADMIN"),
    (2,1,0,"No puede dejar el sistema sin administradores vigentes"),
])
def test_ad1_ad2_regla_defensiva(actor, objetivo, respaldo, mensaje):
    with pytest.raises(Conflicto, match=mensaje):
        proteger_revocacion_admin(actor, objetivo, respaldo)


async def test_ad1_autorrevo_con_respaldo_409(cliente, base_sembrada):
    cookie(cliente)
    antes = await foto_auth(base_sembrada)
    r = await cliente.delete("/usuarios/1/roles/ADMIN")
    assert r.status_code == 409 and r.json() == {"detail": "No puede revocarse su propio rol ADMIN"}
    assert await foto_auth(base_sembrada) == antes


async def test_ad3_revocar_otro_admin_con_respaldo(cliente, base_sembrada):
    cookie(cliente)
    r = await cliente.delete("/usuarios/2/roles/ADMIN")
    assert r.status_code == 200 and r.json()["vigente"] is False
    async with base_sembrada() as s:
        restantes = (await s.exec(text("SELECT usuario_id FROM asignacion_rol WHERE rol='ADMIN' AND revocada_en IS NULL"))).all()
    assert [r.usuario_id for r in restantes] == [1]


async def test_ad4_vencimiento_puede_dejar_cero_sin_evento(cliente, base_sembrada):
    cookie(cliente)
    antes = await foto_auth(base_sembrada)
    async with base_sembrada() as s:
        await s.exec(text("UPDATE asignacion_rol SET vence_en=:fecha WHERE rol='ADMIN'").bindparams(fecha=datetime.now(UTC)-timedelta(seconds=1)))
        await s.commit()
    r = await cliente.get("/auth/yo")
    assert r.status_code == 200 and r.json()["roles_vigentes"] == []
    assert (await foto_auth(base_sembrada))["evento_seguridad"] == antes["evento_seguridad"]
