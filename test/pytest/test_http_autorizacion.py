"""Ejecuta C07-C09 literales con cookies independientes y PostgreSQL de prueba."""

import json
import re
from pathlib import Path

import pytest

from seed import CONTRASENA_DEL_SEED


async def ejecutar_http_autorizacion(cliente, archivo):
    nombradas = {}
    respuestas = []
    def sustituir(valor):
        valor = valor.replace("{{base}}", "").replace("{{password_seed}}", CONTRASENA_DEL_SEED)
        return re.sub(r"\{\{(\w+)\.response\.headers\.Set-Cookie\}\}",
                      lambda m: nombradas[m[1]].headers["set-cookie"], valor)
    contenido = (Path(__file__).resolve().parents[1]/archivo).read_text(encoding="utf-8")
    for bloque in contenido.split("###"):
        lineas = bloque.splitlines()
        indice = next((i for i,l in enumerate(lineas) if l.startswith(("POST ","GET ","DELETE "))), None)
        if indice is None:
            continue
        metodo, url = lineas[indice].split()
        nombre = next((l.removeprefix("# @name ") for l in lineas if l.startswith("# @name ")), None)
        assert "# @no-cookie-jar" in lineas
        headers = {"Cookie": ""}
        cuerpo = None
        for linea in lineas[indice+1:]:
            if not linea or linea.startswith("#"):
                continue
            linea = sustituir(linea)
            if linea.startswith("{"):
                cuerpo = json.loads(linea)
            elif ":" in linea:
                clave, valor = linea.split(":",1)
                headers[clave] = valor.strip()
        r = await cliente.request(metodo,sustituir(url),headers=headers,json=cuerpo)
        if nombre:
            nombradas[nombre] = r
        respuestas.append(r)
    return respuestas


@pytest.mark.parametrize("archivo,codigos", [
    ("c07_roles_vigencia.http",[200,200,200,200,200,403,200,200,422,422]),
    ("c08_autoproteccion.http",[200,409,200,200]),
    ("c09_cambio_obligatorio.http",[200,403,200,422,403,200,200,401,403]),
])
async def test_http_c07_c08_c09(cliente,base_sembrada,archivo,codigos):
    r = await ejecutar_http_autorizacion(cliente,archivo)
    assert [x.status_code for x in r] == codigos
    if archivo.startswith("c07"):
        assert r[2].request.headers["cookie"] == r[5].request.headers["cookie"]
        assert r[6].json()["roles_vigentes"] == [] and r[6].json()["roles_token"] == ["ADMIN"]
        assert r[7].json()[0]["revocada_en"] is not None and r[7].json()[0]["vigente"] is False
    elif archivo.startswith("c08"):
        assert r[1].json() == {"detail":"No puede revocarse su propio rol ADMIN"}
        assert r[2].json()[0]["vigente"] is True and r[2].json()[0]["revocada_en"] is None
        assert r[3].json()["total"] == 1
    else:
        assert r[2].json()["debe_cambiar_password"] is True
        assert r[6].json()["debe_cambiar_password"] is False
        assert r[1].json() == r[4].json() == {"detail":"Debe cambiar la contraseña para continuar"}
        assert r[7].json() == {"detail":"Sesión no válida o vencida"}
        assert r[8].json() == {"detail":"No tiene permisos para realizar esta operación"}
