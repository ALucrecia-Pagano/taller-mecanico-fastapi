"""Cookie HttpOnly y cierre idempotente (K1/K2/K4)."""

from http.cookies import SimpleCookie
import pytest
from seed import CONTRASENA_DEL_SEED


@pytest.mark.parametrize("secure", [True, False])
async def test_k1_k2_cookie_atributos(crear_cliente, entorno_de_prueba, base_sembrada, secure):
    entorno_de_prueba.setenv("COOKIE_SECURE", str(secure))
    async with crear_cliente() as c:
        r = await c.post("/auth/login", json={"email": "admin@example.com", "password": CONTRASENA_DEL_SEED})
        assert r.status_code == 200
        cookie = SimpleCookie(r.headers["set-cookie"])["access_token"]
        assert cookie["httponly"] and cookie["samesite"].lower() == "lax"
        assert cookie["max-age"] == "1800" and cookie["path"] == "/" and not cookie["domain"]
        assert bool(cookie["secure"]) is secure
        assert set(r.json()) == {"mensaje", "debe_cambiar_password", "expira_en_segundos"}


@pytest.mark.parametrize("con_cookie", [True, False])
async def test_k4_logout_publico_con_y_sin_cookie(cliente, base_sembrada, con_cookie):
    if con_cookie:
        await cliente.post("/auth/login", json={"email": "admin@example.com", "password": CONTRASENA_DEL_SEED})
    r = await cliente.post("/auth/logout")
    assert r.status_code == 200
    cookie = SimpleCookie(r.headers["set-cookie"])["access_token"]
    assert cookie["max-age"] == "0" and cookie["path"] == "/" and not cookie["domain"]
    assert "access_token" not in cliente.cookies
