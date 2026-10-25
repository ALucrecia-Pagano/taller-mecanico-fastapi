"""Aplicación, lifespan y grupos de rutas."""

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from app.core.config import get_settings
from app.core.database import crear_fabrica_de_sesiones, crear_motor
from app.modules.health.router import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Los recursos se crean acá y no al importar: así quedan atados al bucle de eventos que corre.
    settings = get_settings()
    engine = crear_motor(settings)  # perezoso: no se conecta hasta el primer uso
    app.state.engine = engine
    app.state.session_factory = crear_fabrica_de_sesiones(engine)
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(title="Taller Mecánico", lifespan=lifespan)

# Primero se arman los grupos con todos sus routers; al final se incluyen en la app.
rutas_abiertas = APIRouter()
rutas_abiertas.include_router(health_router)

app.include_router(rutas_abiertas)
