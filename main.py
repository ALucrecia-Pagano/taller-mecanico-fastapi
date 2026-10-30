"""Aplicación, lifespan y grupos de rutas."""

import asyncio
import secrets
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI

# Registrar todos los modelos antes de resolver relaciones cruzadas: el seed corre en otro proceso.
import app.modules.clientes.models  # noqa: F401
import app.modules.ordenes.models  # noqa: F401
import app.modules.repuestos.models  # noqa: F401
import app.modules.usuarios.models  # noqa: F401

from app.core.config import get_settings
from app.core.database import crear_fabrica_de_sesiones, crear_motor
from app.core.dependencies import controlar_cambio_obligatorio
from app.core.security import hashear_password
from app.modules.health.router import router as health_router
from app.modules.clientes.router import router as clientes_router
from app.modules.usuarios.router import router as auth_router
from app.modules.usuarios.router import eventos_router, usuarios_router
from app.modules.repuestos.router import router as repuestos_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Los recursos se crean acá y no al importar: así quedan atados al bucle de eventos que corre.
    settings = get_settings()
    engine = crear_motor(settings)  # perezoso: no se conecta hasta el primer uso
    app.state.engine = engine
    try:  # desde acá, si algo falla, el motor se cierra igual
        app.state.session_factory = crear_fabrica_de_sesiones(engine)
        app.state.semaforo_bcrypt = asyncio.Semaphore(settings.bcrypt_max_concurrency)
        # Hash ficticio del login (RN-09): el correo inexistente se verifica contra él y tarda lo mismo.
        # La entrada es aleatoria y se descarta: nadie conoce el texto plano.
        app.state.hash_ficticio = await hashear_password(
            secrets.token_urlsafe(32), costo=settings.bcrypt_cost, semaforo=app.state.semaforo_bcrypt
        )
        yield
    finally:
        await engine.dispose()


app = FastAPI(title="Taller Mecánico", lifespan=lifespan)

# Primero se arman los grupos con todos sus routers; al final se incluyen en la app.
rutas_abiertas = APIRouter()
rutas_abiertas.include_router(health_router)
rutas_abiertas.include_router(auth_router)

rutas_protegidas = APIRouter(dependencies=[Depends(controlar_cambio_obligatorio)])
rutas_protegidas.include_router(usuarios_router)
rutas_protegidas.include_router(eventos_router)
rutas_protegidas.include_router(clientes_router)
rutas_protegidas.include_router(repuestos_router)

app.include_router(rutas_abiertas)
app.include_router(rutas_protegidas)
