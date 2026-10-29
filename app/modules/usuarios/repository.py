"""Persistencia de usuarios y registros asociados; confirma el UoW."""

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from sqlalchemy import or_, text

from app.core.repository import BaseRepository
from app.modules.usuarios.models import AsignacionRol, Usuario


class UsuarioRepository(BaseRepository[Usuario]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Usuario)

    async def get_by_email(self, email: str) -> Usuario | None:
        return (await self.session.exec(select(Usuario).where(Usuario.email == email))).first()

    async def roles_vigentes(self, usuario_id, ahora) -> list[str]:
        consulta = select(AsignacionRol.rol).where(
            AsignacionRol.usuario_id == usuario_id, AsignacionRol.revocada_en.is_(None),
            or_(AsignacionRol.vence_en.is_(None), AsignacionRol.vence_en > ahora),
        ).order_by(AsignacionRol.rol)
        return list((await self.session.exec(consulta)).all())


class RegistroAgregadoRepository:
    """Sólo inserción: roles/eventos no tienen CRUD expuesto desde /auth."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, entidad):
        self.session.add(entidad)
        await self.session.flush()
        return entidad


class IntentoAccesoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def fallos_desde_ultimo_exito(self, email, ip, desde, maximo):
        # Una sentencia ligada, incluida la consulta del último éxito y el quinto fallo más reciente.
        consulta = text("""
            WITH fallos AS (
                SELECT cuando, row_number() OVER (ORDER BY cuando DESC, id DESC) AS posicion
                FROM intento_acceso
                WHERE email=:email AND ip=:ip AND NOT exito AND cuando>:desde
                  AND cuando>COALESCE((SELECT max(cuando) FROM intento_acceso
                      WHERE email=:email AND ip=:ip AND exito), '-infinity'::timestamptz)
            )
            SELECT count(*) AS cantidad,
                   max(cuando) FILTER (WHERE posicion=:maximo) AS desbloqueante
            FROM fallos
        """)
        return (await self.session.exec(consulta.bindparams(email=email, ip=ip, desde=desde, maximo=maximo))).one()
