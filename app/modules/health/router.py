"""Sondas de salud: el proceso puede estar vivo y no estar listo."""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.rutas import RutaQueTraduceErrores

# Sin plazo, un host que no contesta deja la sonda esperando los 60 s de asyncpg.
TIMEOUT_READY_SEGUNDOS = 3
MENSAJE_BASE_CAIDA = "La base de datos no responde"

SesionDep = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter(prefix="/health", tags=["health"], route_class=RutaQueTraduceErrores)


@router.get("/live")
async def live() -> dict[str, str]:
    """No toca la base."""
    return {"estado": "vivo"}


@router.get("/ready")
async def ready(sesion: SesionDep) -> dict[str, str]:
    try:
        async with asyncio.timeout(TIMEOUT_READY_SEGUNDOS):
            await sesion.exec(text("SELECT 1"))
    # Sólo fallas de la base: un bug propio tiene que verse como bug, no como "base caída".
    except (SQLAlchemyError, OSError, TimeoutError):
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, MENSAJE_BASE_CAIDA)
    return {"estado": "listo"}
