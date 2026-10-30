from decimal import Decimal

from sqlalchemy import text

from app.core.config import get_settings
from app.core.security import emitir_token


def autenticar(cliente, usuario_id: int, roles: list[str]):
    cliente.cookies.set("access_token", emitir_token(usuario_id, roles, settings=get_settings()))


def repuesto_nuevo(codigo="NUE-001", stock=3):
    return {"codigo": codigo, "descripcion": "Nuevo repuesto", "precio": "10.00", "stock_inicial": stock}


async def test_repuestos_rutas_sin_sesion_y_recepcion_403(cliente, base_sembrada):
    assert (await cliente.get("/repuestos")).status_code == 401
    autenticar(cliente, 3, ["RECEPCION"])
    for metodo, ruta, cuerpo in [
        ("POST", "/repuestos", repuesto_nuevo()),
        ("PATCH", "/repuestos/1", {"descripcion": "x"}),
        ("DELETE", "/repuestos/1", None),
        ("POST", "/repuestos/1/reponer", {"cantidad": 1}),
        ("GET", "/repuestos/1/movimientos", None),
        ("GET", "/repuestos/1/precios", None),
    ]:
        assert (await cliente.request(metodo, ruta, json=cuerpo)).status_code == 403


async def test_alta_repuesto_stock_inicial_y_codigo_vigente(cliente, base_sembrada):
    autenticar(cliente, 1, ["ADMIN"])
    alta = await cliente.post("/repuestos", json=repuesto_nuevo(stock=4))
    assert alta.status_code == 201
    assert alta.json()["stock"] == 4
    movimientos = await cliente.get(f"/repuestos/{alta.json()['id']}/movimientos")
    assert [(m["cantidad"], m["motivo"]) for m in movimientos.json()] == [(4, "Stock inicial")]
    repetido = await cliente.post("/repuestos", json=repuesto_nuevo())
    assert repetido.status_code == 409
    assert repetido.json() == {"detail": "Ya existe un repuesto vigente con ese código"}


async def test_alta_cero_busqueda_y_paginacion(cliente, base_sembrada):
    autenticar(cliente, 1, ["ADMIN"])
    alta = await cliente.post("/repuestos", json=repuesto_nuevo("CERO-001", 0))
    assert alta.status_code == 201
    assert (await cliente.get(f"/repuestos/{alta.json()['id']}/movimientos")).json() == []
    pagina = await cliente.get("/repuestos", params={"q": "freno", "size": 1})
    assert pagina.status_code == 200
    assert pagina.json()["total"] == 1
    assert pagina.json()["pages"] == 1
    assert (await cliente.get("/repuestos", params={"q": "freno", "size": 1, "page": 2})).status_code == 422
    assert (await cliente.get("/repuestos", params={"size": 500})).status_code == 422
    assert (await cliente.get("/repuestos", params={"q": "' OR '1'='1"})).json()["total"] == 0
    for q in ("", "no-existe"):
        vacia = await cliente.get("/repuestos", params={"q": q})
        assert vacia.status_code == 200
        assert vacia.json()["items"] == []
        assert vacia.json()["total"] == 0


async def test_reponer_atomico_y_baja_reutiliza_codigo(cliente, base_sembrada):
    autenticar(cliente, 1, ["ADMIN"])
    alta = await cliente.post("/repuestos", json=repuesto_nuevo("BAJ-001", 2))
    repuesto_id = alta.json()["id"]
    repuesto = await cliente.post(f"/repuestos/{repuesto_id}/reponer", json={"cantidad": 3})
    assert repuesto.status_code == 200
    assert repuesto.json()["stock"] == 5
    movimientos = await cliente.get(f"/repuestos/{repuesto_id}/movimientos")
    assert [(m["cantidad"], m["motivo"]) for m in movimientos.json()][-1:] == [(3, "Reposición")]
    assert (await cliente.post(f"/repuestos/{repuesto_id}/reponer", json={"cantidad": 0})).status_code == 422
    assert (await cliente.post(f"/repuestos/{repuesto_id}/reponer", json={"cantidad": -1})).status_code == 422
    assert (await cliente.delete(f"/repuestos/{repuesto_id}")).status_code == 204
    assert (await cliente.get(f"/repuestos/{repuesto_id}")).status_code == 404
    assert (await cliente.delete(f"/repuestos/{repuesto_id}")).status_code == 404
    assert (await cliente.get(f"/repuestos/{repuesto_id}/precios")).status_code == 404
    assert (await cliente.post("/repuestos", json=repuesto_nuevo("BAJ-001", 0))).status_code == 201


async def test_patch_precio_historial_parcial_y_rechazos(cliente, base_sembrada):
    autenticar(cliente, 1, ["ADMIN"])
    original = (await cliente.get("/repuestos/1")).json()
    cambio = await cliente.patch("/repuestos/1", json={"precio": "8501.00"})
    assert cambio.status_code == 200
    precios = await cliente.get("/repuestos/1/precios")
    assert [(p["precio_anterior"], p["precio_nuevo"]) for p in precios.json()][-1] == ("8500.00", "8501.00")
    async with base_sembrada() as sesion:
        historial = (
            await sesion.exec(
                text(
                    "SELECT precio_anterior, precio_nuevo FROM historial_precio_repuesto "
                    "WHERE repuesto_id = 1 ORDER BY id DESC LIMIT 1"
                )
            )
        ).one()
    assert historial == (Decimal("8500.00"), Decimal("8501.00"))
    cantidad = len(precios.json())
    assert (await cliente.patch("/repuestos/1", json={"descripcion": "Filtro nuevo"})).status_code == 200
    assert len((await cliente.get("/repuestos/1/precios")).json()) == cantidad
    igual = await cliente.patch("/repuestos/1", json={"precio": "8501.00"})
    assert igual.status_code == 422
    assert igual.json() == {"detail": "El precio nuevo debe ser distinto del actual"}
    assert (await cliente.patch("/repuestos/1", json={})).status_code == 422
    assert (await cliente.patch("/repuestos/1", json={"stock": 10})).status_code == 422
    assert (await cliente.get("/repuestos/1")).json()["stock"] == original["stock"]


async def test_stock_negativo_se_traduce_a_409_y_no_deja_movimiento(cliente, base_sembrada):
    autenticar(cliente, 1, ["ADMIN"])
    respuesta = await cliente.post("/repuestos/1/reponer", json={"cantidad": 1})
    assert respuesta.status_code == 200
    async with base_sembrada() as sesion:
        await sesion.exec(text("UPDATE repuesto SET stock = 0 WHERE id = 1"))
        await sesion.commit()
    respuesta = await cliente.request("POST", "/repuestos/1/reponer", json={"cantidad": -1})
    assert respuesta.status_code == 422
