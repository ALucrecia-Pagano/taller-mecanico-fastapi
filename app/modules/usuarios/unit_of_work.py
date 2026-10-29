"""Repositorios de autenticación sobre una única sesión."""

from app.core.unit_of_work import UnitOfWork
from app.modules.clientes.repository import ClienteRepository
from app.modules.usuarios.repository import IntentoAccesoRepository, RegistroAgregadoRepository, UsuarioRepository
from app.modules.usuarios.models import IntentoAcceso


class UsuariosUnitOfWork(UnitOfWork):
    # Textos exactos: No especificado en la consigna, confirmados por la alumna.
    mensajes_de_restriccion = {
        "uq_usuario_email": "El correo ya está registrado",
        "uq_cliente_documento": "El documento ya está registrado",
    }

    def __init__(self, session) -> None:
        super().__init__(session)
        self.usuarios = UsuarioRepository(session)
        self.clientes = ClienteRepository(session)
        self.roles = RegistroAgregadoRepository(session)
        self.eventos = RegistroAgregadoRepository(session)
        self.intentos = IntentoAccesoRepository(session)


class IntentosUnitOfWork(UnitOfWork):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.intentos = RegistroAgregadoRepository(session)


class RegistroIntentos:
    """Adaptador compuesto por la dependencia; no es el servicio de negocio."""

    def __init__(self, fabrica, crear_uow) -> None:
        self.fabrica = fabrica
        self.crear_uow = crear_uow

    async def __call__(self, email, ip, exito, cuando) -> None:
        # DD-05: sesión/transacción propias. Costo: estas filas quedan aunque la petición falle.
        async with self.fabrica() as session, self.crear_uow(session) as uow:
            await uow.intentos.add(IntentoAcceso(email=email, ip=ip, exito=exito, cuando=cuando))
