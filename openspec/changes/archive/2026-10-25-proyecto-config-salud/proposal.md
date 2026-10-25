# Proposal — CH-01 `proyecto-config-salud`

## Why

El repositorio todavía no tiene código: sin configuración leída del entorno, sin motor ni sesiones creados en el lifespan y sin Alembic ni arnés de pruebas, ningún otro change puede empezar (CH-01 es la raíz del camino crítico de `CHANGES.md`). Además, el Ejercicio 1 de la consigna (8 %) evalúa exactamente esto: «Estructura, Settings sin secretos por defecto, motor y fábrica creados en el lifespan, `get_session`, salud», y un secreto con valor por defecto o un `.env` versionado son condición excluyente de la entrega.

Las decisiones de este change se tomaron en el explore: [docs/evidencias/explore-CH-01.md](../../../docs/evidencias/explore-CH-01.md). Son definitivas.

## What Changes

- **Configuración** (`app/core/config.py`): `Settings` con pydantic-settings, leída del entorno o de `.env`, con las 16 variables de DA-07. `POSTGRES_PASSWORD` y `JWT_SECRET_KEY` sin valor por defecto, y no pueden estar vacías; la clave JWT tiene 32 caracteres como mínimo (decisión de la alumna). La URL de la base se arma con `@computed_field` y el driver `postgresql+asyncpg`. Si falta un secreto, la aplicación no arranca.
- **Ciclo de vida** (`main.py`, `app/core/database.py`): el lifespan crea el motor asincrónico (con el pool de la config) y la fábrica de sesiones (`expire_on_commit=False`), los guarda en `app.state` y hace `dispose()` al apagar. `get_session` entrega una sesión por petición y la cierra. Se registra el grupo `rutas_abiertas`.
- **Salud** (`app/modules/health/router.py`): `GET /health/live` (200, sin tocar la base) y `GET /health/ready` (`SELECT 1` → 200; base caída o sin respuesta en 3 s → 503).
- **Migraciones**: Alembic inicializado con la plantilla asincrónica; `alembic.ini` sin credenciales; `migrations/env.py` toma la URL de `Settings`. Sin revisiones todavía.
- **Entorno y dependencias**: `requirements.txt` y `requirements-dev.txt` (piso de la consigna + tope de la siguiente versión mayor), `env.example` con todas las variables y las sensibles vacías, y `pytest.ini`.
- **Arnés de pruebas** (`test/pytest/`): pytest + pytest-asyncio + httpx + asgi-lifespan contra `<POSTGRES_DB>_test`, con un único bucle de eventos por sesión y una guarda que se niega a correr sobre una base que no termine en `_test`. Humo manual en `test/health.http`.
- **README.md**: puesta en marcha desde cero (Git Bash, PowerShell y Linux) hasta probar `/health/*`.

### Refinamientos de alcance respecto de `CHANGES.md`

Como los Desvíos de `CHANGES.md`, estos ajustes no renombran, fusionan ni reordenan changes:

- **R1 — CH-01 crea sólo lo que implementa y prueba.** `CHANGES.md` hace nacer acá `seed.py` (vacío) y las carpetas de todos los módulos. Las carpetas `usuarios/`, `clientes/`, `repuestos/` y `ordenes/` pasan a **CH-03** (el primer change que les pone `models.py`), y `seed.py` pasa a **CH-04** (el que lo llena). `.gitignore` ya existe e ignora `.env`: se verifica, no se crea.
- **R2 — `README.md` nace en CH-01, no en CH-11**, y cada change le suma su paso: `alembic upgrade head` en CH-03 y `python seed.py` en CH-04. CH-11 hace la revisión final y agrega los `.http`. Quien clone el repo tiene que poder levantarlo en cualquier punto del camino (decisión de la alumna).

### Queda afuera (y dónde va)

| Qué | Change |
|---|---|
| `app/core/repository.py`, `unit_of_work.py`, `paginacion.py`, traducción de `IntegrityError` | CH-02 |
| Modelos, carpetas de los cuatro módulos de dominio, migraciones 1 y 2 | CH-03 |
| `app/core/security.py`, bcrypt y PyJWT (también en `requirements.txt`), **hash ficticio en el lifespan** (Desvío 2 de `CHANGES.md`), `seed.py` | CH-04 |
| `get_usuario_actual` y rutas de `/auth` | CH-05 |
| `rutas_protegidas` con el control del cambio obligatorio, `requiere_rol` | CH-06 |
| Revisión final del README, `.http` de los C-NN, evidencias | CH-11 |

## Capabilities

### New Capabilities

- `configuracion`: lectura de la configuración desde el entorno, secretos obligatorios y protegidos, validación de los valores y sincronía con `env.example`.
- `ciclo-de-vida`: recursos de base de datos creados en el arranque y liberados al apagar, y una sesión por petición.
- `salud`: sondas de vida y de disponibilidad.
- `migraciones`: configuración de Alembic sin credenciales, que toma la conexión de la configuración.
- `suite-de-pruebas`: la suite automática corre sólo contra la base de prueba.

### Modified Capabilities

Ninguna (no hay specs previas).

## Impact

- **Archivos nuevos**: `main.py`, `app/__init__.py`, `app/core/__init__.py`, `app/core/config.py`, `app/core/database.py`, `app/modules/__init__.py`, `app/modules/health/__init__.py`, `app/modules/health/router.py`, `alembic.ini`, `migrations/` (plantilla async), `requirements.txt`, `requirements-dev.txt`, `env.example`, `pytest.ini`, `README.md`, `test/health.http` y `test/pytest/` (conftest y tests).
- **Sin cambios**: `.gitignore` (sólo se verifica).
- **Dependencias** (con permiso antes de instalar): `fastapi[standard]`, `sqlmodel`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pydantic-settings`; en dev, además `pytest`, `pytest-asyncio`, `httpx` y `asgi-lifespan`.
- **Bases**: `taller_mecanico` (la app) y `taller_mecanico_test` (la suite), ya creadas y vacías. CH-01 no crea tablas.
- **API**: `GET /health/live` y `GET /health/ready`.
- **Governance**: MEDIO. Punto de control: `.env` ignorado y ningún secreto con valor por defecto.
- **RN**: ninguna de negocio; cumple los requisitos no funcionales de Credenciales, Esquema y Asincronía. DA/DD aplicados: DA-07, DA-26, DA-29, DD-11, DD-12, DD-A4. Casos C-NN propios: ninguno.
