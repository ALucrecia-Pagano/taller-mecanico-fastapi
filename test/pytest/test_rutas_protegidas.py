"""AU1,6-12 / EV3: cinco rutas reales con control heredado y renovación C09."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from auth_helpers import foto_auth
from seed import CONTRASENA_DEL_SEED
from test_autorizacion import cookie
from test_personal_schemas import ALTA


RUTAS = [("POST","/usuarios",ALTA,201), ("GET","/usuarios/4/roles",None,200),
         ("POST","/usuarios/6/roles",{"rol":"MECANICO"},201),
         ("DELETE","/usuarios/4/roles/MECANICO",None,200), ("GET","/eventos",None,200)]


@pytest.mark.parametrize("metodo,ruta,cuerpo,codigo", RUTAS)
@pytest.mark.parametrize("actor", ["anonimo","bearer","sinadmin","pendiente","admin"])
async def test_au1_au6_au7_au8_cinco_rutas(cliente, base_sembrada, metodo, ruta, cuerpo, codigo, actor):
    headers = {}
    if actor == "bearer":
        cookie(cliente)
        headers["Authorization"] = "Bearer "+cliente.cookies["access_token"]
        cliente.cookies.clear()
    elif actor in ("sinadmin","pendiente","admin"):
        cookie(cliente, {"sinadmin":6,"pendiente":7,"admin":1}[actor], ("ADMIN",))
    antes = await foto_auth(base_sembrada)
    r = await cliente.request(metodo, ruta, json=cuerpo, headers=headers)
    esperado = 401 if actor in ("anonimo","bearer") else 403 if actor != "admin" else codigo
    assert r.status_code == esperado
    if actor != "admin":
        mensaje = "Sesión no válida o vencida" if esperado == 401 else "Debe cambiar la contraseña para continuar" if actor == "pendiente" else "No tiene permisos para realizar esta operación"
        assert r.json() == {"detail": mensaje}
        assert await foto_auth(base_sembrada) == antes


async def test_au9_au10_au11_admin_provisional_mismo_segundo(cliente, base_sembrada, monkeypatch):
    import app.core.security as seguridad
    import app.modules.usuarios.service as servicio
    reloj = [(datetime.now(UTC)-timedelta(seconds=3)).replace(microsecond=100000)]
    class Reloj(datetime):
        @classmethod
        def now(cls, tz=None):
            return reloj[0]
    monkeypatch.setattr(seguridad,"datetime",Reloj)
    monkeypatch.setattr(servicio,"datetime",Reloj)
    async with base_sembrada() as s:
        await s.exec(text("UPDATE usuario SET debe_cambiar_password=true WHERE id=2"))
        await s.commit()
    cookie(cliente,2,("ADMIN",))
    anterior = cliente.cookies["access_token"]
    assert (await cliente.get("/eventos")).json() == {"detail":"Debe cambiar la contraseña para continuar"}
    assert (await cliente.get("/auth/yo")).status_code == 200
    antes = await foto_auth(base_sembrada)
    igual = await cliente.post("/auth/cambiar-password",json={"password_actual":CONTRASENA_DEL_SEED,"password_nueva":CONTRASENA_DEL_SEED})
    assert igual.status_code == 422 and await foto_auth(base_sembrada) == antes
    assert (await cliente.get("/eventos")).status_code == 403
    reloj[0] = reloj[0].replace(microsecond=200000)
    cambio = await cliente.post("/auth/cambiar-password",json={"password_actual":CONTRASENA_DEL_SEED,"password_nueva":"NuevaAdmin99!"})
    assert cambio.status_code == 200
    nuevo = cambio.cookies["access_token"]
    cliente.cookies.clear()
    assert (await cliente.get("/eventos",headers={"Cookie":"access_token="+nuevo})).status_code == 200
    assert (await cliente.get("/eventos",headers={"Cookie":"access_token="+anterior})).status_code == 401
