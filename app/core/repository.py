"""BaseRepository[T] y SoftDeleteRepository[T]: ningún repositorio confirma (Ejercicio 6)."""

from datetime import datetime, timezone
from typing import Any

from sqlmodel import SQLModel, func, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.sql.expression import SelectOfScalar


class BaseRepository[T: SQLModel]:
    # Recibe la clase del modelo porque los genéricos se borran en tiempo de ejecución (6.4.3).
    def __init__(self, session: AsyncSession, modelo: type[T]) -> None:
        self.session = session
        self.modelo = modelo

    def _consulta(self) -> SelectOfScalar[T]:
        """Punto único de partida de toda consulta: SoftDeleteRepository le agrega su filtro."""
        return select(self.modelo)

    async def _por_id(self, stmt: SelectOfScalar[T], id: int) -> T | None:
        return (await self.session.exec(stmt.where(self.modelo.id == id))).first()

    async def _listar(self, stmt: SelectOfScalar[T], offset: int, limit: int) -> list[T]:
        # El id va siempre al final del ORDER BY: sin orden fijo, las páginas son inestables.
        # Un método con nombre que ya ordenó por otra columna lo conserva; el id desempata.
        stmt = stmt.order_by(self.modelo.id).offset(offset).limit(limit)
        return list((await self.session.exec(stmt)).all())

    async def _contar(self, stmt: SelectOfScalar[T]) -> int:
        """Cuenta con exactamente el mismo filtro que _listar, si recibe el mismo stmt."""
        return (await self.session.exec(select(func.count()).select_from(stmt.subquery()))).one()

    async def get_by_id(self, id: int) -> T | None:
        return await self._por_id(self._consulta(), id)

    async def get_all(self, offset: int, limit: int) -> list[T]:
        return await self._listar(self._consulta(), offset, limit)

    async def count(self) -> int:
        return await self._contar(self._consulta())

    async def add(self, entidad: T) -> T:
        self.session.add(entidad)
        await self.session.flush()  # flush, nunca commit: confirma el Unit of Work
        return entidad

    async def update(self, entidad: T, datos: dict[str, Any]) -> T:
        """Aplica sólo los campos recibidos (model_dump(exclude_unset=True) del DTO de PATCH)."""
        # Se valida todo antes de aplicar nada: un modelo table=True no valida asignaciones,
        # y una clave mal escrita en un DTO pasaría en silencio. Es un bug, no un error de dominio.
        # No especificado en la consigna (decisión de la alumna).
        campos = self.modelo.model_fields.keys() - {"id"}
        for clave in datos:
            if clave not in campos:
                raise ValueError(f"{clave!r} no es un campo modificable de {self.modelo.__name__}")
        for clave, valor in datos.items():
            setattr(entidad, clave, valor)
        await self.session.flush()
        return entidad

    async def delete(self, entidad: T) -> None:
        await self.session.delete(entidad)
        await self.session.flush()  # una FK violada salta acá y se traduce como el resto


class SoftDeleteRepository[T: SQLModel](BaseRepository[T]):
    """Filtra los dados de baja en toda consulta que parta de _consulta() (6.4.2)."""

    def __init__(self, session: AsyncSession, modelo: type[T]) -> None:
        # Construirlo sobre un modelo sin baja lógica falla acá, no en la primera consulta.
        if "borrado_en" not in modelo.model_fields:
            raise TypeError(f"{modelo.__name__} no tiene borrado_en: no admite baja lógica")
        super().__init__(session, modelo)

    def _consulta(self) -> SelectOfScalar[T]:
        return super()._consulta().where(self.modelo.borrado_en.is_(None))

    async def get_by_id_including_deleted(self, id: int) -> T | None:
        """Sin el filtro de baja: p. ej. terminar una orden con un repuesto dado de baja (DA-21)."""
        return await self._por_id(select(self.modelo), id)

    async def soft_delete(self, entidad: T) -> None:
        # Idempotente: una segunda baja conserva la fecha original (No especificado en la consigna).
        if entidad.borrado_en is not None:
            return
        # Hora de Python con zona: un func.now() asignado quedaría expirado tras el flush.
        entidad.borrado_en = datetime.now(timezone.utc)
        await self.session.flush()
