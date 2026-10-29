"""Ejecuta las peticiones reales de los .http sobre ASGI y la base de prueba sembrada."""

import json
from pathlib import Path

from auth_helpers import foto_auth


async def ejecutar_http(cliente, nombre, variables=None):
    """Subconjunto usado en estos archivos: método, URL, cabeceras y cuerpo JSON."""
    variables = variables or {}
    respuestas = []
    archivo = Path(__file__).resolve().parents[1] / nombre
    for bloque in archivo.read_text(encoding="utf-8").split("###"):
        lineas = bloque.splitlines()
        pedido = next((i for i, linea in enumerate(lineas) if linea.startswith(("POST ", "GET "))), None)
        if pedido is None:
            continue
        metodo, url = lineas[pedido].split()
        headers = {"Cookie": ""} if "# @no-cookie-jar" in lineas else {}
        variables = {**variables, "token_solo": cliente.cookies.get("access_token", "")}
        cuerpo = None
        for linea in lineas[pedido + 1:]:
            if linea.startswith("#"):
                continue
            for clave, valor in variables.items():
                linea = linea.replace("{{" + clave + "}}", valor)
            if linea.startswith("{"):
                cuerpo = json.loads(linea)
            elif ":" in linea:
                clave, valor = linea.split(":", 1)
                headers[clave] = valor.strip()
        respuestas.append(await cliente.request(metodo, url.replace("{{base}}", ""), headers=headers, json=cuerpo))
    return respuestas


async def test_http_c02_registro(cliente, base_sembrada):
    antes = await foto_auth(base_sembrada)
    respuestas = await ejecutar_http(cliente, "c02_registro.http")
    assert [r.status_code for r in respuestas] == [201, 409, 409, 409]
    assert respuestas[1].json() == {"detail": "El correo ya está registrado"}
    assert respuestas[2].json() == respuestas[3].json() == {"detail": "El documento ya está registrado"}
    despues = await foto_auth(base_sembrada)
    assert all(len(despues[t]) == len(antes[t]) + 1 for t in antes)
    assert next(c for c in despues["cliente"] if c.documento == "28333444").usuario_id is None


async def test_http_c05_limite_intentos(cliente, base_sembrada):
    from sqlalchemy import text
    respuestas = await ejecutar_http(cliente, "c05_limite_intentos.http")
    assert [r.status_code for r in respuestas] == [401, 401, 401, 401, 401, 429]
    assert int(respuestas[-1].headers["retry-after"]) > 0
    async with base_sembrada() as s:
        assert (await s.exec(text("SELECT count(*) FROM intento_acceso WHERE NOT exito"))).one().count == 5


async def test_http_c03_c04_login_cookie_y_credenciales(cliente, base_sembrada):
    from seed import CONTRASENA_DEL_SEED
    respuestas = await ejecutar_http(cliente, "c03_c04_login.http", {"password_seed": CONTRASENA_DEL_SEED})
    assert [r.status_code for r in respuestas] == [200, 200, 401, 401, 401, 401]
    assert set(respuestas[0].json()) == {"mensaje", "debe_cambiar_password", "expira_en_segundos"}
    assert "httponly" in respuestas[0].headers["set-cookie"].lower()
    assert respuestas[-1].json() == respuestas[-2].json() == {"detail": "Correo o contraseña incorrectos"}
    assert respuestas[2].json() == respuestas[3].json() == {"detail": "Sesión no válida o vencida"}
    from app.core.security import decodificar_token
    from app.core.config import get_settings
    bearer = respuestas[3].request.headers["authorization"].removeprefix("Bearer ")
    assert decodificar_token(bearer, settings=get_settings()).usuario_id == 1
    assert not respuestas[3].request.headers.get("cookie")
