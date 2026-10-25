"""Sondas de vida y de disponibilidad (spec salud, H1-H7)."""

import asyncio

from app.modules.health import router as modulo_salud

CAIDA = {"detail": "La base de datos no responde"}


async def test_h1_proceso_vivo(cliente):
    respuesta = await cliente.get("/health/live")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "vivo"}


async def test_h3_base_disponible(cliente):
    respuesta = await cliente.get("/health/ready")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "listo"}


def apuntar_a(entorno, puerto: int) -> None:
    entorno.setenv("POSTGRES_HOST", "127.0.0.1")
    entorno.setenv("POSTGRES_PORT", str(puerto))


async def test_h2_vivo_aunque_la_base_este_caida(crear_cliente, entorno_de_prueba, puerto_cerrado):
    apuntar_a(entorno_de_prueba, puerto_cerrado)

    async with crear_cliente() as cliente:
        respuesta = await cliente.get("/health/live")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "vivo"}


async def test_h4_conexion_rechazada(crear_cliente, entorno_de_prueba, puerto_cerrado):
    apuntar_a(entorno_de_prueba, puerto_cerrado)

    async with crear_cliente() as cliente:
        respuesta = await cliente.get("/health/ready")

    assert respuesta.status_code == 503
    assert respuesta.json() == CAIDA  # exacto: sin texto del error original


async def test_h5_credenciales_invalidas(crear_cliente, entorno_de_prueba):
    entorno_de_prueba.setenv("POSTGRES_PASSWORD", "contrasena-incorrecta-h5")

    async with crear_cliente() as cliente:
        respuesta = await cliente.get("/health/ready")

    assert respuesta.status_code == 503
    assert respuesta.json() == CAIDA


async def test_h6_base_que_no_contesta(crear_cliente, entorno_de_prueba, servidor_mudo):
    apuntar_a(entorno_de_prueba, servidor_mudo)
    entorno_de_prueba.setattr(modulo_salud, "TIMEOUT_READY_SEGUNDOS", 0.2)

    async with crear_cliente() as cliente:
        async with asyncio.timeout(5):  # límite externo: el test nunca se cuelga
            respuesta = await cliente.get("/health/ready")

    assert respuesta.status_code == 503
    assert respuesta.json() == CAIDA


async def test_h7_metodo_no_permitido(cliente):
    respuesta = await cliente.post("/health/ready")

    assert respuesta.status_code == 405
