# Explore de CH-01 `proyecto-config-salud`

Resumen del explore (`/opsx:explore`) del primer change, hecho el 2026-10-25 antes del propose. No se escribió código.

Fuentes: `CHANGES.md` (CH-01, Desvíos y Observaciones), `knowledge-base/08_arquitectura_propuesta.md`, `knowledge-base/09_decisiones_y_supuestos.md` (DA-07, DD-07, DD-11, DD-A4, DA-26, DA-29) y la consigna: requisitos técnicos (pp. 3-4), Ejercicio 1 (p. 10), tabla de endpoints, requisitos no funcionales y criterios de evaluación.

En la columna «Decisión», **[Alumna]** marca lo que propuso o agregó la alumna; el resto lo propuso el agente y la alumna lo aceptó. Lo que la consigna no especifica está marcado como tal.

## Decisiones

| # | Pregunta | Decisión | Por qué |
|---|---|---|---|
| 1 | ¿Qué archivos de la estructura obligatoria nacen en CH-01? | CH-01 crea sólo lo que implementa y prueba: `main.py`, `app/__init__.py`, `app/core/{__init__,config,database}.py`, `app/modules/{__init__.py,health/__init__.py,health/router.py}`, `migrations/` (Alembic), `alembic.ini`, `test/pytest/`, `test/health.http`, `pytest.ini`, `requirements.txt`, `requirements-dev.txt`, `env.example` y `README.md`. Las carpetas `usuarios/`, `clientes/`, `repuestos/` y `ordenes/` nacen en CH-03; `seed.py`, en CH-04. `.gitignore` ya existe e ignora `.env`: sólo se verifica. | Un archivo vacío no aporta a la corrección y ningún test lo justifica (TDD estricto). La estructura se evalúa en la entrega, no al cerrar CH-01. |
| 1-R | README | **[Alumna]** `README.md` nace en CH-01 y cada change le suma su paso (`alembic upgrade head` en CH-03, `python seed.py` en CH-04); CH-11 hace la revisión final con los `.http`. En CH-01 lleva: qué está implementado y qué está planificado (remite a `CHANGES.md`), requisitos, y la puesta en marcha desde cero en Git Bash, PowerShell y Linux: `.venv`, dependencias, `.env` desde `env.example` con el comando fijo para `JWT_SECRET_KEY`, crear las bases, levantar con uvicorn y probar `/health/live` y `/health/ready`. | Quien clone el repo tiene que poder levantarlo en cualquier punto del camino. |
| 2a | ¿Cómo se garantiza que la app no arranque sin secretos? | `POSTGRES_PASSWORD` y `JWT_SECRET_KEY` sin default y con `min_length=1` (vacía = faltante). **[Alumna]** `JWT_SECRET_KEY` con mínimo 32 caracteres. | `env.example` trae las sensibles vacías: sin `min_length`, copiarlo sin completar arrancaría la app con una clave vacía. El mínimo de 32 sigue a RFC 7518 (HS256: clave ≥ 256 bits) y al aviso de PyJWT con claves cortas; el comando fijo genera ~86 caracteres. Es validación de configuración, no una regla de la consigna. |
| 2b | ¿Cómo se evita filtrar secretos? | Los dos secretos como `SecretStr`; la URL con `@computed_field(repr=False)`, armada con `sqlalchemy.engine.URL.create(...)`. | El `computed_field` aparece en `repr` y en `model_dump` y lleva la contraseña. `URL.create` escapa `@ / : %`; un f-string arma una URL rota. |
| 2c | ¿Cuándo se valida `Settings`? | `get_settings()` con `@lru_cache`, llamada desde el lifespan (y desde `migrations/env.py`). Nada de `settings = Settings()` a nivel de módulo. | La app falla al arrancar si falta un secreto; los tests pueden construir `Settings` aislada y la configuración se cambia con `monkeypatch` + `cache_clear()`. Es el patrón oficial de FastAPI. |
| 2d | Detalles de `Settings` | Se mantiene el rechazo de claves desconocidas en el `.env` (default de pydantic-settings). Rangos: `DB_POOL_SIZE`, `JWT_EXPIRE_SECONDS` y `BCRYPT_MAX_CONCURRENCY` > 0; `BCRYPT_COST` entre 4 y 31 (no especificado en la consigna). Atributos en snake_case, mapeados sin distinción de mayúsculas a los nombres de DA-07. | Un error de tipeo en el `.env` falla fuerte en lugar de ignorarse. Los rangos son los que acepta cada componente. |
| 2e | URL en Alembic | **[Alumna]** `migrations/env.py` no usa `config.set_main_option` ni `async_engine_from_config`: crea el motor con `create_async_engine(<URL de get_settings()>, poolclass=NullPool)`. | configparser interpreta el `%` de la contraseña. |
| 3a | ¿El lifespan se conecta a la base al arrancar? | No: el motor es perezoso y no se agrega ningún ping de arranque. | Con la base caída la app debe arrancar, `/health/live` dar 200 y `/health/ready` 503 («vivo y no listo», Ej. 1). |
| 3b | Apagado | `try/finally` alrededor del `yield`, con `await engine.dispose()` en el `finally`. | El `dispose()` corre aunque falle algo después de crear el motor. |
| 3c | ¿Qué `AsyncSession`? | La de SQLModel (`sqlmodel.ext.asyncio.session.AsyncSession`): `async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)`. | El stack es SQLModel y `session.exec(select(...))` devuelve resultados tipados. **Fija el contrato para CH-02.** |
| 3d | Nombres | En `database.py`: `crear_motor(settings)`, `crear_fabrica_de_sesiones(engine)` y `get_session(request)` (nombre del PDF). En `app.state`: `engine` y `session_factory`. | El PDF fija sólo `get_session`; lo demás va en castellano. |
| 3e | Hash ficticio del login | Se queda en CH-04 (Desvío 2 de `CHANGES.md`), sin placeholder en CH-01. | Necesita bcrypt, que nace en CH-04. La rúbrica del Ej. 1 mira «motor y fábrica creados en el lifespan, `get_session`, salud»; el hash ficticio se evalúa en la fila del Ej. 4. Un `None` o un TODO no lo justifica ningún test. |
| 4 | ¿Los dos grupos de rutas se crean ya? | `rutas_abiertas` nace en CH-01 con el router de salud (`prefix="/health"`, `tags=["health"]`); `rutas_protegidas` nace en CH-06 junto con su dependencia. Regla para el design: **primero se arman los grupos con todos sus routers y al final se incluyen en la app.** | El grupo protegido existe para llevar el control del cambio obligatorio; sin él sería engañoso. `app.include_router` copia las rutas que el grupo tiene en ese momento: lo que se agrega después no aparece y no da error. |
| 5a | ¿Con qué corre `/health/ready` el `SELECT 1`? | Con `Depends(get_session)` y `SELECT 1` literal. Verificar en el apply si `session.exec` acepta `text()` con la versión instalada de SQLModel (`execute` está deprecado). | Usa de verdad la pieza que evalúa la rúbrica. Las dos rutas son **GET**: la tabla del PDF sale desalineada al extraer el texto; manda el párrafo del Ej. 1. |
| 5b | Timeout | El chequeo va envuelto en `asyncio.timeout(3)`; los 3 s son una constante en el router (no especificado en la consigna; no se agrega variable a DA-07). | Con un host que no contesta, asyncpg espera 60 s por defecto: un readiness que tarda un minuto no sirve. |
| 5c | ¿Qué errores dan 503? | Sólo `SQLAlchemyError`, `OSError` y `TimeoutError`; nunca `Exception`. | Un bug propio se tiene que ver como bug, no como «base caída». |
| 5d | Cuerpos (no especificados en la consigna) | live → 200 `{"estado": "vivo"}`; ready → 200 `{"estado": "listo"}`; ready caído → 503 `{"detail": "La base de datos no responde"}`, sin el texto de la excepción. | Mismo formato `detail` que el resto de la API; nada interno de la base (espíritu de RN-18). El módulo `health` sólo tiene `router.py`: no hay schemas. |
| 5e | Dependencias de live | `/health/live` no depende de `get_session` ni de `app.state`. | Tiene que responder 200 con la base caída. |
| 6a | `sqlalchemy.url` en `alembic.ini` | Se borra la línea que genera `alembic init -t async migrations` y queda un comentario: la URL sale de `Settings`. | Condición excluyente: sin credenciales en `alembic.ini`. |
| 6b | `target_metadata` | `SQLModel.metadata`, todavía sin modelos; CH-03 agrega los imports. `env.py` no importa `main` ni la app. | Correr una migración no debe tener efectos colaterales. |
| 6c | Modo offline | Se mantiene (`alembic upgrade --sql`), con la URL de `get_settings()`. | Sirve para leer el SQL de la migración autogenerada en CH-03. |
| 6d | ¿Cómo apuntar Alembic a la base de prueba? | Subproceso con `POSTGRES_DB=<base>_test` en el entorno, con la guarda de `_test` aplicada antes de lanzarlo. | `env.py` no cambia; es lo que haría un humano. Un hook programático sería código que hoy ningún test pide. |
| 6e | Tests de Alembic en CH-01 | Uno estático (`alembic.ini` sin `sqlalchemy.url` con valor) y uno de humo (`alembic current` contra `_test` termina con código 0). | Sin revisiones todavía; `upgrade/downgrade` se prueban en CH-03. |
| 6f | Nombres de las revisiones | `file_template` por defecto; los slugs se deciden en CH-03. | La consigna no los fija. |
| 7a | Versiones en los requirements | Piso del PDF + tope de la siguiente versión mayor (p. ej. `bcrypt>=4.0,<6`, `sqlmodel>=0.0.24,<0.1`). `requirements.txt` en CH-01: `fastapi[standard]`, `sqlmodel`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pydantic-settings`. | Respeta los mínimos y corta las rupturas de una versión mayor. |
| 7b | bcrypt y PyJWT | Entran en CH-04, el change que los usa. | Mismo principio que la decisión 1. |
| 7c | `requirements-dev.txt` | `-r requirements.txt`, `pytest>=8`, `pytest-asyncio>=1.0`, `httpx>=0.27`, `asgi-lifespan`. | `httpx` llega con `fastapi[standard]`, pero es dependencia directa de los tests. |
| 7d | Config de pytest | `pytest.ini` en la raíz (`testpaths = test/pytest`). | El proyecto no es un paquete y no usa Poetry: un `pyproject.toml` confundiría. |
| 7e | `env.example` | Las 16 variables de DA-07 agrupadas con comentarios; `POSTGRES_PASSWORD=` y `JWT_SECRET_KEY=` vacías; el resto con su default explícito; arriba de la clave, `python -c "import secrets; print(secrets.token_urlsafe(64))"` (anda igual en Git Bash, PowerShell y Linux). Tests estáticos: `env.example` coincide con los campos de `Settings` y tiene las sensibles vacías; `.env` está en `.gitignore`. | Que no se desincronicen al agregar una variable, y cuidar el punto de control del governance de CH-01. |
| 8a | OB-06: ¿quién ejecuta el lifespan en los tests? | `asgi-lifespan` (`LifespanManager`), en `requirements-dev.txt`. | Corre el lifespan real por el protocolo ASGI, como uvicorn, y es lo que recomiendan los docs de FastAPI. Armar `app.state` a mano hace divergir tests y producción (el síntoma que advierte el Ej. 1); `TestClient` corre en otro bucle y rompe asyncpg; `app.router.lifespan_context` queda como plan B. |
| 8b | Bucle de eventos | Un solo bucle por sesión: `asyncio_mode = auto`, `asyncio_default_fixture_loop_scope = session`, `asyncio_default_test_loop_scope = session` en `pytest.ini`. | Las conexiones de asyncpg quedan atadas al bucle en el que se crearon. |
| 8c | Alcance del lifespan | Lifespan y cliente por test (scope `function`); las configs especiales se arman con `monkeypatch` sobre el entorno + `get_settings.cache_clear()`. | Un lifespan de sesión haría que el test del 503 pise `app.state.engine` del `app` compartido. El motor es perezoso: crearlo por test casi no cuesta. No hace falta una fábrica `crear_app()`. |
| 8d | Guarda de `_test` | **[Alumna]** La guarda verifica la `Settings` que devuelve `get_settings()` después del `monkeypatch` y del `cache_clear()`, la misma que usa el lifespan, no una copia. Si `postgres_db` no termina en `_test`, el test no corre. | Lo que se protege es la base que efectivamente se va a tocar. |
| 9a | Forma de la guarda | Función pura `verificar_base_de_prueba(settings)`, con su propio test; se llama en la fixture antes del `LifespanManager`, antes de cada subproceso de Alembic y en `pytest_sessionstart` (con `pytest.exit`). Si el `.env` ya apunta a una base `*_test`, se aborta con un mensaje claro. | Una guarda sin test es un supuesto. Derivar `<base>_test` sobre una base que ya es de prueba daría `*_test_test`, un error confuso. |
| 9b | Escenarios | Los 27 escenarios automáticos de la lista de abajo (S1-S8, L1-L4, G1-G2, H1-H7, A1-A2, E1-E2, T1-T2), más `test/health.http` como humo manual (no corresponde a ningún C-NN). | Feliz, error y borde por requisito. |
| 9c | ¿Cómo se verifica `dispose()` sin mocks? | Por el reemplazo del pool: la identidad de `engine.pool` cambia después del shutdown. | Es determinista; `pg_stat_activity` fallaría al azar si hay otras conexiones abiertas. |

## Escenarios de prueba (9b)

| # | Tipo | Escenario |
|---|---|---|
| S1 | feliz | Con todas las variables, `Settings` carga y aplica los defaults de DA-07 (se triangula con `JWT_ALGORITHM` y `DB_POOL_SIZE`). |
| S2 | error | Falta `POSTGRES_PASSWORD` → error; falta `JWT_SECRET_KEY` → error. |
| S3 | borde | `POSTGRES_PASSWORD=""` → error; JWT de 31 caracteres → error, de 32 → ok. |
| S4 | borde | La URL usa `postgresql+asyncpg`; una contraseña con `@ / % :` vuelve intacta al parsear la URL. |
| S5 | seguridad | `repr(settings)` no contiene la contraseña, la clave JWT ni la URL. |
| S6 | error | Una clave desconocida en el `.env` → error. |
| S7 | borde | `DB_POOL_SIZE=0` → error; `BCRYPT_COST` 3 y 32 → error, 4 y 31 → ok. |
| S8 | feliz | `get_settings()` devuelve la misma instancia; después de `cache_clear()`, relee. |
| L1 | feliz | Después del startup existen `app.state.engine` (pool de la config) y `app.state.session_factory` (`expire_on_commit=False`). |
| L2 | feliz | Al apagar se hace `dispose()` (el pool cambia de identidad). |
| L3 | borde | Con la base caída, el arranque igual funciona. |
| L4 | error | Sin `JWT_SECRET_KEY`, el startup falla y `LifespanManager` propaga el error. |
| G1 | feliz | `get_session` entrega una `AsyncSession` de SQLModel desde `app.state`; dos peticiones reciben sesiones distintas (se llama con un `Request` sobre el `app` real y un `SELECT 1` real). |
| G2 | feliz | Al terminar, la sesión se cierra y la conexión vuelve al pool (`checkedout() == 0`). |
| H1 | feliz | `GET /health/live` → 200 `{"estado": "vivo"}`. |
| H2 | borde | Con la base caída (puerto cerrado), live → 200. |
| H3 | feliz | `GET /health/ready` → 200 `{"estado": "listo"}`. |
| H4 | error | Puerto cerrado → 503 con el `detail` propio y sin texto interno (rama `OSError`). |
| H5 | error | Contraseña incorrecta → 503 (rama `SQLAlchemyError`). |
| H6 | error | Servidor TCP propio del test que acepta y no contesta + timeout reducido por `monkeypatch` → 503 (rama `TimeoutError`). |
| H7 | borde | `POST /health/ready` → 405. |
| A1 | estático | `alembic.ini` sin `sqlalchemy.url` con valor. |
| A2 | humo | `alembic current` contra `_test` (subproceso, con guarda) → código 0. |
| E1 | estático | `env.example` = campos de `Settings`; sensibles vacías. |
| E2 | estático | `.env` está en `.gitignore`. |
| T1 | guarda | `verificar_base_de_prueba` rechaza `taller_mecanico` y acepta `taller_mecanico_test`. |
| T2 | guarda | Si el `.env` ya apunta a `*_test`, se aborta con mensaje claro. |

## Pedidos para el propose

1. **Refinamientos de alcance** (anotarlos en el proposal, igual que los Desvíos de `CHANGES.md`; no renombran ni reordenan changes):
   - **R1**: CH-01 crea sólo lo que implementa y prueba. Las carpetas `usuarios/`, `clientes/`, `repuestos/` y `ordenes/` pasan a CH-03; `seed.py`, a CH-04. `.gitignore` ya existe: se verifica, no se crea.
   - **R2**: `README.md` nace en CH-01 (no en CH-11) y cada change le suma su paso; CH-11 hace la revisión final con los `.http`.
2. En el **design**: la forma del lifespan y de `database.py` (3a a 3d), la regla del orden de `include_router` (4) y el arnés de pruebas (8a a 8d, 9a, 9c).
3. En las **specs**: los 27 escenarios automáticos de arriba más el humo manual de `test/health.http`, agrupados por requisito (configuración, lifespan y sesión, salud, Alembic y repo, guarda).
4. Marcar como **«No especificado en la consigna»**: los cuerpos de `/health/*` (5d), el timeout de 3 s (5b), los rangos de 2d y el mínimo de 32 de la clave JWT (2a, decisión de la alumna).
5. **Acciones con efectos que el apply debe pedir antes de correr**: crear el `.venv` e instalar `requirements-dev.txt`, `alembic init -t async migrations` y la corrida de la suite contra `taller_mecanico_test`.
6. **Notas para CH-04** (no van en CH-01):
   - bcrypt 5.x lanza `ValueError` con contraseñas de más de 72 bytes, en lugar de truncar; nuestro validador las rechaza antes.
   - PyJWT ≥ 2.10 exige `sub` string: `str(usuario.id)`.
   - Con un lifespan por test, la fixture fija `BCRYPT_COST=4` para que el hash ficticio no sume ~250 ms por test.
7. **Nota para CH-02**: la `AsyncSession` es la de SQLModel (3c); los repositorios usan `session.exec(...)`.
8. **Nota para CH-03**: Alembic se prueba contra `_test` por subproceso con `POSTGRES_DB` en el entorno (6d); `env.py` suma los imports de los modelos.
