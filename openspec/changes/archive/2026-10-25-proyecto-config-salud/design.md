# Design — CH-01 `proyecto-config-salud`

## Context

Repositorio sin código: sólo hay KB, `CHANGES.md`, `openspec/` y un `.gitignore` que ya ignora `.env`, `.venv/`, `__pycache__/`, `*.pyc` y `.pytest_cache/`. El `.venv` (Python 3.13) existe pero sólo tiene `pip`. Las bases `taller_mecanico` y `taller_mecanico_test` existen y están vacías (PostgreSQL 17).

Motivación y alcance: ver `proposal.md`. Requisitos y escenarios: ver `specs/`. Todas las decisiones salen del explore ([docs/evidencias/explore-CH-01.md](../../../docs/evidencias/explore-CH-01.md)); el número entre paréntesis remite a su tabla.

Restricciones que mandan: la estructura obligatoria de la consigna (`main.py` en la raíz; `app/core/...`; `app/modules/<módulo>/...`; el módulo `health` sólo tiene `router.py`), todos los handlers `async def`, el esquema sólo con Alembic y ningún secreto en el código, en `alembic.ini` ni en el repo.

## Goals / Non-Goals

**Goals:**
- Dejar fijas, para todos los changes siguientes, la forma de `Settings`, del lifespan, de `get_session` y del arnés de pruebas.
- Que la app arranque con la base caída y lo informe por `/health/ready` («vivo y no listo»).
- Que la suite no pueda tocar la base de la aplicación.

**Non-Goals:**
- Hash ficticio en el lifespan (CH-04), seguridad, repositorios y UoW (CH-02), modelos y revisiones de Alembic (CH-03), grupo protegido (CH-06).
- Una fábrica `crear_app()`: no hace falta con un lifespan por test (8c).
- Un hook programático en `migrations/env.py` para los tests (6d).

## Decisions

### D1. Archivos que nacen (1, R1)

```
main.py                         lifespan + rutas_abiertas
app/__init__.py
app/core/__init__.py
app/core/config.py              Settings + get_settings()
app/core/database.py            crear_motor, crear_fabrica_de_sesiones, get_session
app/modules/__init__.py
app/modules/health/__init__.py
app/modules/health/router.py
alembic.ini                     sin sqlalchemy.url
migrations/env.py               plantilla async adaptada (D6)
migrations/script.py.mako, migrations/versions/   (de la plantilla; sin revisiones)
requirements.txt, requirements-dev.txt, env.example, pytest.ini, README.md
test/health.http
test/pytest/conftest.py         guarda + fixtures
test/pytest/test_*.py
```

### D2. `Settings` (2a-2d)

- `class Settings(BaseSettings)` con `model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")`. Se deja el `extra` por defecto de pydantic-settings, que rechaza las claves desconocidas del `.env` (S6).
- Atributos en snake_case (`postgres_password`, `jwt_secret_key`, …), mapeados sin distinguir mayúsculas a los nombres de DA-07.
- `postgres_password: SecretStr = Field(min_length=1)`; `jwt_secret_key: SecretStr = Field(min_length=32)` (decisión de la alumna). Sin default: si falta una, `ValidationError`.
- Rangos con `Field(gt=0)` / `Field(ge=4, le=31)` para `bcrypt_cost`.
- La URL: `@computed_field(repr=False)` + `@property`, armada con `sqlalchemy.engine.URL.create(drivername="postgresql+asyncpg", ...)` y devuelta como `str` con `render_as_string(hide_password=False)`. Nombre del atributo: `database_url`.
- `get_settings()` decorada con `@lru_cache`. **No hay instancia a nivel de módulo.** La llaman el lifespan y `migrations/env.py`.
- Alternativa descartada: `settings = Settings()` al importar. Haría fallar cualquier import (incluida la colección de pytest) y obligaría a tocar el entorno global para probar los faltantes.

### D3. Lifespan y `database.py` (3a-3e)

```python
@asynccontextmanager
async def lifespan(app):
    settings = get_settings()                      # falla acá si falta un secreto (L4)
    engine = crear_motor(settings)                 # perezoso: no conecta (L3)
    app.state.engine = engine
    app.state.session_factory = crear_fabrica_de_sesiones(engine)
    try:
        yield
    finally:
        await engine.dispose()                     # L2
```

- `crear_motor(settings)` → `create_async_engine(settings.database_url, pool_size=..., max_overflow=..., echo=settings.sql_echo)`.
- `crear_fabrica_de_sesiones(engine)` → `async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)`, con **la `AsyncSession` de SQLModel** (`sqlmodel.ext.asyncio.session.AsyncSession`). **Esto fija el contrato para CH-02.**
- `get_session(request: Request)` → `async with request.app.state.session_factory() as session: yield session`. No confirma (eso es del UoW de CH-02).
- Sin ping de arranque: la app tiene que levantar con la base caída.
- El hash ficticio se agrega en CH-04, como una línea antes del `yield`. **Sin placeholder en CH-01.**

### D4. Grupos de rutas (4)

`main.py` define `rutas_abiertas = APIRouter()`, le incluye el router de salud y al final hace `app.include_router(rutas_abiertas)`. `rutas_protegidas` nace en CH-06.

**Regla del orden de `include_router`:** primero se arman los grupos con todos sus routers y al final se incluyen en la app. `include_router` copia las rutas que el grupo tiene en ese momento: un router incluido en el grupo después no aparece, y no da error. CH-05 y CH-06 heredan esta regla.

### D5. Salud (5a-5e)

- `router = APIRouter(prefix="/health", tags=["health"])`. Sin `schemas.py`: las respuestas son dicts.
- `GET /live` → `{"estado": "vivo"}`. Sin dependencias: ni `get_session` ni `app.state`.
- `GET /ready` → `Depends(get_session)`. Dentro de `asyncio.timeout(TIMEOUT_READY_SEGUNDOS)` (constante = 3 en el router) ejecuta `SELECT 1`. Si captura `(SQLAlchemyError, OSError, TimeoutError)`, responde `HTTPException(503, "La base de datos no responde")`. Nunca captura `Exception`.
- **A verificar en el apply**: si `session.exec(text("SELECT 1"))` funciona con la versión instalada de SQLModel. Si no, se usa `session.execute(...)`, que está deprecado en SQLModel, y se anota.
- H6 reduce el plazo con `monkeypatch` sobre la constante del módulo.

### D6. Alembic (2e, 6a-6f)

- `alembic init -t async migrations` (acción con permiso).
- `alembic.ini`: se **borra** la línea `sqlalchemy.url` y queda un comentario: la URL sale de `Settings`. Se mantiene `prepend_sys_path = .` para que `app` sea importable.
- `migrations/env.py`: `target_metadata = SQLModel.metadata`. Online: `create_async_engine(get_settings().database_url, poolclass=NullPool)` en lugar de `async_engine_from_config`. Offline: `context.configure(url=get_settings().database_url, ...)`. **Nunca** `config.set_main_option` (configparser interpreta el `%` de la contraseña). No importa `main` ni la app.
- `file_template` por defecto; los slugs los decide CH-03.

### D7. Dependencias (7a-7d)

`requirements.txt` (piso de la consigna + tope de la siguiente mayor):

```
fastapi[standard]>=0.111,<1
sqlmodel>=0.0.24,<0.1
sqlalchemy[asyncio]>=2.0,<3
asyncpg>=0.30,<1
alembic>=1.13,<2
pydantic-settings>=2.0,<3
```

`requirements-dev.txt`: `-r requirements.txt`, `pytest>=8,<10` (acepta la 9, vigente al aplicar el change), `pytest-asyncio>=1.0,<2`, `httpx>=0.27,<1`, `asgi-lifespan>=2.1,<3`. Los topes del dev siguen el mismo criterio. Los pisos de `pytest` y `asgi-lifespan` no los fija la consigna: son los de las versiones con la API que se usa (`loop_scope` en pytest-asyncio 1.x).

`pytest.ini` en la raíz:

```ini
[pytest]
testpaths = test/pytest
pythonpath = .
asyncio_mode = auto
asyncio_default_fixture_loop_scope = session
asyncio_default_test_loop_scope = session
```

`pythonpath = .` agrega la raíz a `sys.path` para que `app` y `main` se importen también con el ejecutable `pytest` a secas (sin eso sólo funciona `python -m pytest`).

### D8. `env.example` (7e)

Las 16 variables, agrupadas con un comentario por bloque (base, JWT, bcrypt, pool, cookie, SQL, login). `POSTGRES_PASSWORD=` y `JWT_SECRET_KEY=` vacías; el resto con su default escrito explícito. Arriba de la clave va el comando fijo: `python -c "import secrets; print(secrets.token_urlsafe(64))"`. E1 compara las claves de `env.example` con `Settings.model_fields` (convertidas a mayúsculas).

### D9. Arnés de pruebas (8a-8d, 9a, 9c)

```
pytest_sessionstart
   base = Settings leída del .env
   si base.postgres_db termina en _test --> pytest.exit("el .env apunta a la base de prueba ...")   (T2)

fixture entorno_de_prueba (function)
   monkeypatch.setenv("POSTGRES_DB", <base>_test)  (+ ajustes del test)
   get_settings.cache_clear()
   s = get_settings()                 <-- la MISMA instancia que usara el lifespan
   verificar_base_de_prueba(s)        <-- pytest.fail si no termina en _test   (T1)
   yield s
   get_settings.cache_clear()

fixture cliente (function)
   async with LifespanManager(app) as manager:
       async with AsyncClient(transport=ASGITransport(app=manager.app), base_url="http://test") as c:
           yield c

subproceso alembic (A2)
   env = os.environ + {"POSTGRES_DB": <base>_test}; verificar antes de lanzar
```

- Las configs especiales (puerto cerrado, contraseña incorrecta) se arman con `monkeypatch.setenv` antes de pedir el cliente. Como el lifespan es por test, no hay estado compartido que se pise.
- Para los secretos de prueba, la suite usa los del `.env` local: la suite exige un `.env` completo, como la app.
- `verificar_base_de_prueba(settings)` y `derivar_base_de_prueba(postgres_db)` son funciones puras que viven en `test/pytest/guarda.py`. Los tests y el `conftest` las importan de ahí; nunca se importa desde `conftest`, porque pytest lo desaconseja.
- **Un solo bucle de eventos por sesión** (D7): las conexiones de asyncpg quedan atadas a su bucle.
- **L2** (dispose): se guarda `engine.pool` dentro del `LifespanManager`; después de salir, `engine.pool is not pool_anterior`.
- **G1/G2**: `get_session` se llama directamente con `Request({"type": "http", "app": app})` dentro del lifespan; dos generadores dan dos sesiones distintas; después de cerrar el generador, `engine.pool.checkedout() == 0`. Sin mocks: el `SELECT 1` es real contra `_test`.
- **H6**: `asyncio.start_server` en `127.0.0.1:0` que acepta y no contesta nunca; `POSTGRES_PORT` = ese puerto; el plazo, reducido por `monkeypatch`.
- **Tests de `Settings`** (S1-S8): `Settings(_env_file=None, ...)` o `_env_file=<tmp>` con `monkeypatch.delenv`, para aislar del `.env` real.
- **L4**: `monkeypatch.delenv("JWT_SECRET_KEY")` + `Settings` sin `.env` → `LifespanManager(app)` levanta la excepción. Como `get_settings()` lee el `.env`, el test apunta `env_file` a un archivo temporal sin la clave, o parchea `get_settings` para que lo cree sin `.env`. Lo resuelve el apply; ninguna de las dos variantes toca la base.

### D10. README (R2)

Secciones en CH-01:
- Estado: qué está implementado y qué está planificado, remitiendo a `CHANGES.md`.
- Requisitos: Python ≥ 3.12 y PostgreSQL ≥ 16.
- Puesta en marcha en Git Bash, PowerShell y Linux: crear el `.venv`, `pip install -r requirements.txt`, copiar `env.example` a `.env` y generar la clave con el comando fijo, crear las bases (`createdb`/`psql`), `uvicorn main:app --reload` y probar `/health/live` y `/health/ready`.
- Correr los tests: `pip install -r requirements-dev.txt`, `pytest -v`.

## Notas para los changes siguientes

- **CH-02**: la `AsyncSession` es la de SQLModel; los repositorios usan `session.exec(...)`. `get_session` no confirma: confirma el UoW.
- **CH-03**: suma los imports de los `models.py` en `migrations/env.py`. Prueba `upgrade/downgrade` contra `_test` por subproceso, con `POSTGRES_DB` en el entorno y la guarda antes de lanzarlo. Agrega `alembic upgrade head` al README.
- **CH-04**:
  - bcrypt y PyJWT entran recién acá en `requirements.txt` (`bcrypt>=4.0,<6`, `PyJWT>=2.8,<3`).
  - bcrypt 5.x lanza `ValueError` con más de 72 bytes en lugar de truncar; el validador las rechaza antes.
  - PyJWT ≥ 2.10 exige `sub` string: `str(usuario.id)`.
  - El hash ficticio va en el lifespan antes del `yield`. La fixture fija `BCRYPT_COST=4` para no sumar ~250 ms por test.
  - Agrega `python seed.py` al README.
- **CH-05/CH-06**: regla del orden de `include_router` (D4). Las rutas que requieren sesión pero deben funcionar con el cambio pendiente (`cambiar-password`) van en `rutas_abiertas` con su propia dependencia.

## Risks / Trade-offs

- [Lifespan por test: más lento que uno de sesión] → El motor es perezoso; el costo es casi nulo hasta CH-04, que fija `BCRYPT_COST=4` en la suite.
- [`session.exec` con `text()` según la versión de SQLModel] → Se verifica en el apply (D5); el comportamiento observable no cambia.
- [H6 depende de un servidor TCP propio y de un plazo reducido] → Es determinista y local; no depende de la red.
- [Topes de versión mayor: una versión nueva compatible queda afuera] → Se sube el tope a mano cuando haga falta; es preferible a una ruptura silenciosa al clonar.
- [La suite exige un `.env` completo] → Es lo mismo que exige la app; el README lo explica.
- [`asyncio.timeout` cubre la consulta y la conexión; si asyncpg ignora la cancelación, el plazo se excede] → H6 lo detecta.

## Migration Plan

No hay datos ni esquema previos. El rollback es borrar los archivos nuevos; las bases no se tocan (CH-01 no crea tablas; `alembic current` sólo lee).
