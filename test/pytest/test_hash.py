"""Hash y verificación con bcrypt fuera del bucle y bajo un semáforo (spec contrasenas, H1-H7). No toca la base."""

import asyncio
import threading

import pytest

from app.core.security import hashear_password, verificar_password
from espia_bcrypt import espiar_bcrypt
from seed import CONTRASENA_DEL_SEED

COSTO = 4  # el mínimo de bcrypt: la suite no paga los ~250 ms del costo 12


@pytest.fixture
def semaforo() -> asyncio.Semaphore:
    return asyncio.Semaphore(4)


async def test_h1_hash_y_verificacion_correcta(semaforo):
    hash_ = await hashear_password(CONTRASENA_DEL_SEED, costo=COSTO, semaforo=semaforo)

    assert hash_ != CONTRASENA_DEL_SEED
    assert hash_.startswith("$2b$04$")
    assert await verificar_password(CONTRASENA_DEL_SEED, hash_, semaforo=semaforo) is True


async def test_h2_otra_contrasena(semaforo):
    hash_ = await hashear_password(CONTRASENA_DEL_SEED, costo=COSTO, semaforo=semaforo)

    assert await verificar_password("OtraClave99", hash_, semaforo=semaforo) is False


async def test_h3_sal_nueva_en_cada_hash(semaforo):
    primero = await hashear_password(CONTRASENA_DEL_SEED, costo=COSTO, semaforo=semaforo)
    segundo = await hashear_password(CONTRASENA_DEL_SEED, costo=COSTO, semaforo=semaforo)

    assert primero != segundo
    assert await verificar_password(CONTRASENA_DEL_SEED, primero, semaforo=semaforo) is True
    assert await verificar_password(CONTRASENA_DEL_SEED, segundo, semaforo=semaforo) is True


async def test_h4_el_costo_viaja_en_el_hash(semaforo):
    con_costo_5 = await hashear_password(CONTRASENA_DEL_SEED, costo=5, semaforo=semaforo)
    con_costo_4 = await hashear_password(CONTRASENA_DEL_SEED, costo=COSTO, semaforo=semaforo)

    assert con_costo_5.startswith("$2b$05$")
    # La verificación no recibe costo: lo lee del hash guardado.
    assert await verificar_password(CONTRASENA_DEL_SEED, con_costo_4, semaforo=semaforo) is True


async def test_h5_mas_de_72_bytes_al_calcular_el_hash(semaforo, monkeypatch):
    espia = espiar_bcrypt(monkeypatch)

    with pytest.raises(ValueError, match="72 bytes"):
        await hashear_password("ñ" * 36 + "a", costo=COSTO, semaforo=semaforo)
    assert espia.hilos == []  # se rechaza antes de llamar a bcrypt


async def test_h6_bcrypt_corre_fuera_del_hilo_del_bucle(semaforo, monkeypatch):
    espia = espiar_bcrypt(monkeypatch)
    hilo_del_bucle = threading.get_ident()

    hash_ = await hashear_password(CONTRASENA_DEL_SEED, costo=COSTO, semaforo=semaforo)
    await verificar_password(CONTRASENA_DEL_SEED, hash_, semaforo=semaforo)

    assert len(espia.hilos) == 2
    assert hilo_del_bucle not in espia.hilos


async def test_h7_el_semaforo_limita_la_concurrencia(monkeypatch):
    espia = espiar_bcrypt(monkeypatch, pausa=0.05)
    semaforo = asyncio.Semaphore(2)

    await asyncio.gather(*(hashear_password(CONTRASENA_DEL_SEED, costo=COSTO, semaforo=semaforo) for _ in range(6)))

    assert len(espia.hilos) == 6
    # == y no <=: además del límite, prueba que las llamadas sí corren en paralelo.
    assert espia.pico == 2
