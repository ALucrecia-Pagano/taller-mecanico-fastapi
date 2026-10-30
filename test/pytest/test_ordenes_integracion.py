"""Controles transversales CH-09 y artefactos de demostración."""

from pathlib import Path

import pytest
from sqlalchemy import text

from test_ordenes_alta import cuerpo_orden
from test_ordenes_catalogo import autenticar

RUTAS = [("POST", "/ordenes"), ("GET", "/ordenes"), ("GET", "/ordenes/1"),
         ("GET", "/mis-ordenes"), ("GET", "/estados-orden")]
ARCHIVOS = ["c06_401_403_propio.http", "c10_alta_orden.http", "c15_detalle_sin_n1.http", "c17_catalogo_estados.http"]


@pytest.mark.parametrize("metodo,ruta", RUTAS)
@pytest.mark.parametrize("modo,codigo", [("sin_cookie", 401), ("bearer", 401), ("cambio", 403)])
async def test_cinco_rutas_sesion_bearer_y_cambio(cliente, base_sembrada, metodo, ruta, modo, codigo):
    if modo == "cambio":
        autenticar(cliente, 7, ["MECANICO"])
    elif modo == "bearer":
        autenticar(cliente, 1, ["ADMIN"])
        token = cliente.cookies.get("access_token")
        cliente.cookies.clear()
        cliente.headers["Authorization"] = f"Bearer {token}"
    respuesta = await cliente.request(metodo, ruta, json=cuerpo_orden() if metodo == "POST" else None)
    assert respuesta.status_code == codigo


@pytest.mark.parametrize("usuario,metodo,ruta", [(6, "POST", "/ordenes"), (6, "GET", "/ordenes"), (4, "POST", "/ordenes")])
async def test_personal_rol_insuficiente_403(cliente, base_sembrada, usuario, metodo, ruta):
    autenticar(cliente, usuario, ["ADMIN", "RECEPCION"])
    assert (await cliente.request(metodo, ruta, json=cuerpo_orden() if metodo == "POST" else None)).status_code == 403


@pytest.mark.parametrize("tipo", ["revocado", "vencido"])
async def test_roles_actuales_no_token_en_alta_listado_detalle(cliente, base_sembrada, tipo):
    autenticar(cliente, 3, ["RECEPCION", "ADMIN"])
    async with base_sembrada() as s:
        sql = "UPDATE asignacion_rol SET revocada_en=now() WHERE usuario_id=3" if tipo == "revocado" else "UPDATE asignacion_rol SET vence_en=now()-interval '1 second' WHERE usuario_id=3"
        await s.exec(text(sql))
        await s.commit()
    for metodo, ruta in (("POST", "/ordenes"), ("GET", "/ordenes"), ("GET", "/ordenes/1")):
        assert (await cliente.request(metodo, ruta, json=cuerpo_orden() if metodo == "POST" else None)).status_code == 403


@pytest.mark.parametrize("campo", ["vehiculo_id", "repuesto_id"])
@pytest.mark.parametrize("id_invalido", [10**30, -(10**30)])
async def test_ids_fuera_integer_son_referencia_inexistente_409(cliente, base_sembrada, campo, id_invalido):
    autenticar(cliente, 1)
    cuerpo = cuerpo_orden()
    if campo == "vehiculo_id":
        cuerpo[campo] = id_invalido
    else:
        cuerpo["items"][0][campo] = id_invalido
    assert (await cliente.post("/ordenes", json=cuerpo)).status_code == 409


@pytest.mark.parametrize("id_invalido", [10**30, -(10**30)])
async def test_detalle_id_fuera_integer_404(cliente, base_sembrada, id_invalido):
    autenticar(cliente, 6)
    assert (await cliente.get(f"/ordenes/{id_invalido}")).status_code == 404


async def test_superficie_cinco_operaciones_sin_crud_extra(cliente, base_sembrada):
    from main import app
    from test_rutas import rutas_de
    from app.core.rutas import RutaQueTraduceErrores

    rutas = [r for r in rutas_de(app.routes) if getattr(r, "path", "") in {"/ordenes", "/ordenes/{id}", "/mis-ordenes", "/estados-orden", "/ordenes/{id}/iniciar", "/ordenes/{id}/terminar", "/ordenes/{id}/cancelar"}]
    assert {(metodo, r.path) for r in rutas for metodo in r.methods} == {
        ("POST", "/ordenes"), ("GET", "/ordenes"), ("GET", "/ordenes/{id}"), ("GET", "/mis-ordenes"),
        ("GET", "/estados-orden"), ("POST", "/ordenes/{id}/iniciar"),
        ("POST", "/ordenes/{id}/terminar"), ("POST", "/ordenes/{id}/cancelar"),
    }
    assert all(isinstance(r, RutaQueTraduceErrores) for r in rutas)
    autenticar(cliente, 1)
    assert (await cliente.get("/ordenes/no-entero")).status_code == 422
    for metodo, ruta in (("PATCH", "/ordenes/1"), ("DELETE", "/ordenes/1"), ("POST", "/ordenes/1/historial")):
        assert (await cliente.request(metodo, ruta, json={})).status_code in (404, 405)


@pytest.mark.parametrize("archivo", ARCHIVOS)
def test_http_formato_password_login_separadores_y_esperadas(archivo):
    lineas = Path("test", archivo).read_text(encoding="utf-8").splitlines()
    assert "@password_seed = {{$processEnv TALLER_PASSWORD_PRUEBA}}" in lineas
    contenido = "\n".join(lineas)
    assert '"password":"{{password_seed}}"' in contenido or '"password": "{{password_seed}}"' in contenido
    assert "/auth/login" in contenido
    for i, linea in enumerate(lineas):
        if linea.startswith("###"):
            assert i > 0 and lineas[i - 1] == ""
        if linea.startswith(("GET ", "POST ", "PATCH ", "DELETE ")):
            assert any(l.startswith("# Esperado:") for l in lineas[max(0, i - 4):i])


def test_readme_documenta_cinco_endpoints_y_evidencias_ch09():
    contenido = Path("README.md").read_text(encoding="utf-8")
    assert "CH-09 `ordenes-alta-consulta`" in contenido
    assert all(ruta in contenido for ruta in ("/ordenes", "/ordenes/{id}", "/mis-ordenes", "/estados-orden"))
    assert "C-15-consultas.txt" in contenido


@pytest.mark.parametrize("cambio", ["vacio", "cero", "negativo", "fraccion", "repetido", "sin_falla", "total", "precio_item", "estado", "fecha", "mecanico"])
async def test_http_entrada_invalida_422_sin_escrituras(cliente, base_sembrada, foto_de_la_base, cambio):
    autenticar(cliente, 3)
    datos = cuerpo_orden()
    if cambio == "vacio": datos["items"] = []
    elif cambio in ("cero", "negativo", "fraccion"): datos["items"][0]["cantidad"] = {"cero": 0, "negativo": -1, "fraccion": 1.5}[cambio]
    elif cambio == "repetido": datos["items"].append({"repuesto_id": 2, "cantidad": 1})
    elif cambio == "sin_falla": del datos["falla"]
    elif cambio == "precio_item": datos["items"][0]["precio_unitario"] = "0.01"
    else: datos[{"total": "total", "estado": "estado", "fecha": "creada_en", "mecanico": "mecanico_id"}[cambio]] = "x"
    async with base_sembrada() as s:
        antes = await foto_de_la_base(s)
    respuesta = await cliente.post("/ordenes", json=datos)
    assert respuesta.status_code == 422
    async with base_sembrada() as s:
        assert await foto_de_la_base(s) == antes


@pytest.mark.parametrize("archivo,codigos", [
    ("c06_401_403_propio.http", [401, 200, 403, 200, 403, 200]),
    ("c10_alta_orden.http", [200, 201, 409]),
    ("c15_detalle_sin_n1.http", [200, 201, 200, 200]),
    ("c17_catalogo_estados.http", [401, 200, 200, 200, 200, 422]),
])
async def test_http_ch09_literales_sobre_asgi(cliente, base_sembrada, archivo, codigos):
    from test_http_autorizacion import ejecutar_http_autorizacion

    respuestas = await ejecutar_http_autorizacion(cliente, archivo)
    assert [r.status_code for r in respuestas] == codigos
    if archivo.startswith("c06"):
        assert respuestas[3].json()["id"] == 1
        assert [i["id"] for i in respuestas[5].json()["items"]] == [1]
        assert respuestas[2].request.headers["cookie"] == respuestas[3].request.headers["cookie"]
    elif archivo.startswith("c10"):
        assert respuestas[1].json()["total"] == "68000.00"
        async with base_sembrada() as s:
            assert (await s.exec(text("SELECT count(*) FROM orden_trabajo"))).scalar_one() == 3
    elif archivo.startswith("c15"):
        assert [len(r.json()["items"]) for r in respuestas[2:]] == [2, 4]
    else:
        assert [e["codigo"] for e in respuestas[2].json()] == ["PENDIENTE", "EN_REPARACION", "TERMINADA", "CANCELADA"]
