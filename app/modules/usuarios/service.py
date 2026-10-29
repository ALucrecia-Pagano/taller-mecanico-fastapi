"""Operaciones de autenticación; las transacciones pertenecen a los UoW recibidos."""

from datetime import UTC, datetime, timedelta
from math import ceil

from app.core.errores import LimiteDeIntentos, TokenInvalido
from app.core.security import emitir_token, hashear_password, verificar_password
from app.modules.clientes.models import Cliente
from app.modules.usuarios.models import AsignacionRol, EventoSeguridad, Rol, Usuario
from app.modules.usuarios.schemas import Perfil


async def verificar_limite_intentos(repo, email, ip, ahora, maximo, ventana):
    estado = await repo.fallos_desde_ultimo_exito(email, ip, ahora - timedelta(seconds=ventana), maximo)
    if estado.cantidad >= maximo:
        segundos = ceil((estado.desbloqueante + timedelta(seconds=ventana) - ahora).total_seconds())
        raise LimiteDeIntentos(segundos=max(1, segundos))


class AuthService:
    def __init__(self, uow, *, settings, semaforo, registrar_intento=None, hash_ficticio=None) -> None:
        self.uow = uow
        self.settings = settings
        self.semaforo = semaforo
        self.registrar_intento = registrar_intento
        self.hash_ficticio = hash_ficticio

    async def perfil(self, actual) -> Perfil:
        usuario = actual.usuario
        async with self.uow:
            roles = await self.uow.usuarios.roles_vigentes(usuario.id, datetime.now(UTC))
        return Perfil(id=usuario.id, email=usuario.email, nombre=usuario.nombre,
                      debe_cambiar_password=usuario.debe_cambiar_password,
                      roles_vigentes=roles, roles_token=sorted(actual.token.roles))

    async def cambiar_password(self, datos, actual):
        usuario = actual.usuario
        correcta = await verificar_password(datos.password_actual, usuario.password_hash, semaforo=self.semaforo)
        if not correcta:
            # Texto exacto: No especificado en la consigna. Es fallo de credenciales, no de sesión.
            raise TokenInvalido("La contraseña actual es incorrecta")
        hash_ = await hashear_password(datos.password_nueva, costo=self.settings.bcrypt_cost, semaforo=self.semaforo)
        cambio = datetime.now(UTC)  # fecha completa, después del hash y antes de la escritura
        async with self.uow:
            await self.uow.usuarios.update(usuario, {"password_hash": hash_, "password_cambiada_en": cambio,
                                                     "debe_cambiar_password": False})
            await self.uow.eventos.add(EventoSeguridad(actor=usuario.email, accion="Cambio de contraseña"))
            roles = await self.uow.usuarios.roles_vigentes(usuario.id, cambio)
        # Sólo después de confirmar; igualdad iat==cambio es válida por RN-07.
        return emitir_token(usuario.id, roles, settings=self.settings, ahora=datetime.now(UTC))

    async def login(self, datos, ip):
        ahora = datetime.now(UTC)
        async with self.uow:
            await verificar_limite_intentos(self.uow.intentos, datos.email, ip, ahora,
                                           self.settings.login_max_fallos, self.settings.login_ventana_segundos)
            usuario = await self.uow.usuarios.get_by_email(datos.email)
        hash_ = usuario.password_hash if usuario is not None else self.hash_ficticio
        verificada = await verificar_password(datos.password, hash_, semaforo=self.semaforo)
        # [Alumna] Un usuario inactivo cuenta como fallo incluso con contraseña correcta.
        correcto = usuario is not None and usuario.activo and verificada
        await self.registrar_intento(datos.email, ip, correcto, datetime.now(UTC))
        if not correcto:
            raise TokenInvalido("Correo o contraseña incorrectos")
        async with self.uow:
            roles = await self.uow.usuarios.roles_vigentes(usuario.id, datetime.now(UTC))
        return emitir_token(usuario.id, roles, settings=self.settings), usuario.debe_cambiar_password

    async def registrar(self, datos) -> None:
        hash_ = await hashear_password(datos.password, costo=self.settings.bcrypt_cost, semaforo=self.semaforo)
        async with self.uow:
            usuario = await self.uow.usuarios.add(Usuario(email=datos.email, nombre=datos.nombre, password_hash=hash_))
            await self.uow.roles.add(AsignacionRol(usuario_id=usuario.id, rol=Rol.CLIENTE, otorgada_por=None))
            await self.uow.clientes.add(Cliente(usuario_id=usuario.id, nombre=datos.nombre,
                                              documento=datos.documento, telefono=datos.telefono))
            await self.uow.eventos.add(EventoSeguridad(actor=datos.email, accion=f"Registro de cliente {datos.email}"))
