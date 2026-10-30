"""Persistencia de usuarios y registros asociados; confirma el UoW."""

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import func, select
from sqlalchemy import or_, text

from app.core.repository import BaseRepository
from app.modules.usuarios.models import AsignacionRol, EventoSeguridad, Usuario

# [Alumna] D3 — No especificado en la consigna. Namespace fijo compartido de RN-05.
CLAVE_BLOQUEO_ADMIN = 606005


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


class AsignacionRolRepository(RegistroAgregadoRepository):
    async def bloquear_admin(self) -> None:
        # [Alumna] D3: mismo candado para TODAS las mutaciones ADMIN; lo libera commit/rollback.
        await self.session.exec(text("SELECT pg_advisory_xact_lock(:clave)").bindparams(clave=CLAVE_BLOQUEO_ADMIN))

    async def abierta(self, usuario_id: int, rol: str) -> AsignacionRol | None:
        consulta = select(AsignacionRol).where(AsignacionRol.usuario_id == usuario_id,
                                               AsignacionRol.rol == rol, AsignacionRol.revocada_en.is_(None))
        return (await self.session.exec(consulta)).first()

    async def cerrar(self, asignacion: AsignacionRol, ahora) -> None:
        asignacion.revocada_en = ahora
        await self.session.flush()

    async def historial(self, usuario_id: int) -> list[AsignacionRol]:
        return list((await self.session.exec(select(AsignacionRol).where(AsignacionRol.usuario_id == usuario_id)
                                             .order_by(AsignacionRol.desde, AsignacionRol.id))).all())

    async def contar_admin_respaldo(self, excluida_id: int, ahora) -> int:
        consulta = select(func.count()).select_from(AsignacionRol).where(
            AsignacionRol.id != excluida_id, AsignacionRol.rol == "ADMIN", AsignacionRol.revocada_en.is_(None),
            or_(AsignacionRol.vence_en.is_(None), AsignacionRol.vence_en > ahora))
        return (await self.session.exec(consulta)).one()


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


class EventoSeguridadRepository(RegistroAgregadoRepository):
    async def contar(self) -> int:
        return (await self.session.exec(select(func.count()).select_from(EventoSeguridad))).one()

    async def pagina(self, offset: int, limit: int) -> list[EventoSeguridad]:
        consulta = select(EventoSeguridad).order_by(EventoSeguridad.cuando.desc(), EventoSeguridad.id.desc()).offset(offset).limit(limit)
        return list((await self.session.exec(consulta)).all())
