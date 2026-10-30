from pathlib import Path

import pytest
from sqlalchemy import event, text
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import get_settings
from app.core.security import emitir_token
from app.modules.clientes.repository import ClienteRepository
from seed import CONTRASENA_DEL_SEED


def autenticar(cliente, usuario_id: int, roles: list[str]):
    cliente.cookies.set("access_token", emitir_token(usuario_id, roles, settings=get_settings()))


@pytest.mark.parametrize(
    ("ruta", "metodo"),
    [
        ("/clientes", "post"),
        ("/clientes/1", "get"),
        ("/clientes/1/vehiculos", "post"),
        ("/vehiculos/1", "delete"),
        ("/mis-vehiculos", "get"),
    ],
)
async def test_clientes_rutas_recepcion_sin_sesion_401(cliente, base_sembrada, ruta, metodo):
    respuesta = await cliente.request(
        metodo.upper(), ruta, json={"nombre": "x", "documento": "x", "telefono": "x"}
    )
    assert respuesta.status_code == 401


@pytest.mark.parametrize(
    ("ruta", "metodo", "cuerpo"),
    [
        ("/clientes", "POST", {"nombre": "x", "documento": "90000001", "telefono": "x"}),
        ("/clientes/1", "GET", None),
        ("/clientes/1/vehiculos", "POST", {"patente": "ZZ999ZZ", "marca": "x", "modelo": "x", "anio": 2015}),
        ("/vehiculos/1", "DELETE", None),
    ],
)
async def test_clientes_rutas_recepcion_sin_rol_403(cliente, base_sembrada, ruta, metodo, cuerpo):
    autenticar(cliente, 4, ["MECANICO"])
    respuesta = await cliente.request(metodo, ruta, json=cuerpo)
    assert respuesta.status_code == 403


async def test_cliente_y_vehiculos_seed_y_mis_vehiculos(cliente, base_sembrada):
    autenticar(cliente, 1, ["ADMIN"])
    respuesta = await cliente.get("/clientes/1")
    assert respuesta.status_code == 200
    assert [vehiculo["id"] for vehiculo in respuesta.json()["vehiculos"]] == [1, 2]
    assert "password_hash" not in respuesta.json()

    assert (await cliente.delete("/vehiculos/2")).status_code == 204
    respuesta = await cliente.get("/clientes/1")
    assert [vehiculo["id"] for vehiculo in respuesta.json()["vehiculos"]] == [1]

    autenticar(cliente, 6, ["CLIENTE"])
    respuesta = await cliente.get("/mis-vehiculos")
    assert respuesta.status_code == 200
    assert [vehiculo["id"] for vehiculo in respuesta.json()] == [1]


async def test_alta_cliente_normaliza_documento_y_rechaza_repetido(cliente, base_sembrada):
    autenticar(cliente, 3, ["RECEPCION"])
    respuesta = await cliente.post(
        "/clientes", json={"nombre": "Nuevo", "documento": "  50000001  ", "telefono": "x"}
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["documento"] == "50000001"

    respuesta = await cliente.post(
        "/clientes", json={"nombre": "Otro", "documento": "50000001", "telefono": "x"}
    )
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detail": "Ya existe un cliente con ese documento"}


async def test_alta_vehiculo_normaliza_patente_y_rechaza_equivalente(cliente, base_sembrada):
    autenticar(cliente, 3, ["RECEPCION"])
    alta = await cliente.post(
        "/clientes/2/vehiculos",
        json={"patente": "zz 999 zz", "marca": "Ford", "modelo": "Fiesta", "anio": 2015},
    )
    assert alta.status_code == 201
    assert alta.json()["patente"] == "ZZ999ZZ"
    assert "borrado_en" not in alta.json()

    respuesta = await cliente.post(
        "/clientes/2/vehiculos",
        json={"patente": " ac 456 ef ", "marca": "Ford", "modelo": "Fiesta", "anio": 2015},
    )
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detail": "Ya existe un vehículo vigente con esa patente"}


async def test_alta_vehiculo_reutiliza_patente_dada_de_baja(cliente, base_sembrada):
    autenticar(cliente, 3, ["RECEPCION"])
    assert (await cliente.delete("/vehiculos/2")).status_code == 204
    respuesta = await cliente.post(
        "/clientes/2/vehiculos",
        json={"patente": "ac 456 ef", "marca": "Ford", "modelo": "Fiesta", "anio": 2015},
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["patente"] == "AC456EF"


async def test_alta_vehiculo_cliente_inexistente_y_anio_invalido_404_422(cliente, base_sembrada):
    autenticar(cliente, 3, ["RECEPCION"])
    assert (
        await cliente.post(
            "/clientes/999/vehiculos",
            json={"patente": "ZZ999ZZ", "marca": "x", "modelo": "x", "anio": 2015},
        )
    ).status_code == 404
    for anio in (1949, 2101):
        assert (
            await cliente.post(
                "/clientes/1/vehiculos",
                json={"patente": "ZZ999ZZ", "marca": "x", "modelo": "x", "anio": anio},
            )
        ).status_code == 422


async def test_consultas_de_cliente_inexistente_y_baja_de_vehiculo_inexistente_404(cliente, base_sembrada):
    autenticar(cliente, 1, ["ADMIN"])
    assert (await cliente.get("/clientes/999")).status_code == 404
    assert (await cliente.delete("/vehiculos/999")).status_code == 404


async def test_baja_vehiculo_abierto_409_y_final_204(cliente, base_sembrada):
    autenticar(cliente, 1, ["ADMIN"])
    respuesta = await cliente.delete("/vehiculos/1")
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detail": "El vehículo tiene órdenes abiertas"}

    respuesta = await cliente.delete("/vehiculos/3")
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detail": "El vehículo tiene órdenes abiertas"}

    respuesta = await cliente.delete("/vehiculos/2")
    assert respuesta.status_code == 204
    repetida = await cliente.delete("/vehiculos/2")
    assert repetida.status_code == 404


@pytest.mark.parametrize("estado", ["TERMINADA", "CANCELADA"])
async def test_baja_permitida_con_cada_estado_final(cliente, base_sembrada, estado):
    autenticar(cliente, 1, ["ADMIN"])
    async with base_sembrada() as sesion:
        await sesion.exec(
            text("UPDATE orden_trabajo SET estado = :estado WHERE vehiculo_id = 3").bindparams(estado=estado)
        )
        await sesion.commit()
    assert (await cliente.delete("/vehiculos/3")).status_code == 204


async def test_mis_vehiculos_usuario_sin_ficha_lista_vacia(cliente, base_sembrada):
    autenticar(cliente, 5, ["MECANICO"])
    respuesta = await cliente.get("/mis-vehiculos")
    assert respuesta.status_code == 200
    assert respuesta.json() == []


async def test_cambio_obligatorio_bloquea_todas_las_rutas_de_clientes(cliente, base_sembrada):
    rutas = [
        ("POST", "/clientes", {"nombre": "x", "documento": "90000002", "telefono": "x"}),
        ("GET", "/clientes/1", None),
        ("POST", "/clientes/1/vehiculos", {"patente": "ZZ999ZZ", "marca": "x", "modelo": "x", "anio": 2015}),
        ("DELETE", "/vehiculos/1", None),
        ("GET", "/mis-vehiculos", None),
    ]
    autenticar(cliente, 7, ["MECANICO"])
    for metodo, ruta, cuerpo in rutas:
        respuesta = await cliente.request(metodo, ruta, json=cuerpo)
        assert respuesta.status_code == 403
        assert respuesta.json() == {"detail": "Debe cambiar la contraseña para continuar"}


async def test_detalle_cliente_usa_carga_anticipada_sin_n_mas_uno(base_sembrada, motor_del_esquema):
    consultas = 0

    def contar(*_args):
        nonlocal consultas
        consultas += 1

    event.listen(motor_del_esquema.sync_engine, "before_cursor_execute", contar)
    try:
        async with AsyncSession(motor_del_esquema) as sesion:
            cliente = await ClienteRepository(sesion).get_by_id_with_vehiculos(1)
            assert cliente is not None
            assert [vehiculo.id for vehiculo in cliente.vehiculos] == [1, 2]
        assert consultas <= 2
    finally:
        event.remove(motor_del_esquema.sync_engine, "before_cursor_execute", contar)


async def test_contratos_y_parametro_invalido_422(cliente, base_sembrada):
    autenticar(cliente, 3, ["RECEPCION"])
    assert (await cliente.get("/clientes/no-entero")).status_code == 422
    assert (
        await cliente.post(
            "/clientes/1/vehiculos",
            json={"patente": "ZZ999ZZ", "marca": "x", "modelo": "x", "anio": 1949, "extra": True},
        )
    ).status_code == 422


def test_archivos_http_ch07_contienen_password_de_entorno():
    raiz = Path(__file__).resolve().parents[1]
    assert "{{$processEnv TALLER_PASSWORD_PRUEBA}}" in (raiz / "c01_parametro_invalido.http").read_text()
    assert "{{$processEnv TALLER_PASSWORD_PRUEBA}}" in (raiz / "c19_baja_vehiculo.http").read_text()
