# Tasks — CH-01 `proyecto-config-salud`

Convenciones:
- **[PERMISO]**: acción con efectos (instalar, inicializar, correr contra la base, levantar el servidor). Se describe y se espera la confirmación de Amanda antes de ejecutarla.
- **[AMANDA]**: la hace Amanda a mano (secretos).
- TDD estricto: en cada grupo, primero el test que falla (RED, con la falla confirmada al ejecutarlo), después el código mínimo (GREEN), luego la triangulación y el refactor con los tests en verde.
- Los IDs (S1, L2, H4…) son los escenarios de `specs/`.
- No se commitea nada: los commits los hace Amanda.

## 1. Preparación del entorno

- [x] 1.1 Escribir `requirements.txt`, `requirements-dev.txt` y `pytest.ini` según design D7. Verificar que los pisos coinciden con la tabla de requisitos técnicos de la consigna.
- [x] 1.2 [PERMISO] `.venv/Scripts/python -m pip install -r requirements-dev.txt`. Verificar con `pip list` que están todas las dependencias y anotar las versiones instaladas en el resumen del apply.
- [x] 1.3 Crear los paquetes vacíos `app/__init__.py`, `app/core/__init__.py`, `app/modules/__init__.py` y `app/modules/health/__init__.py`, y `test/pytest/`. Verificar con `python -c "import app.modules.health"`.
- [x] 1.4 [AMANDA] Crear `.env` a partir de la plantilla de la tarea 4.2 (o, si todavía no existe, con `POSTGRES_PASSWORD` y `JWT_SECRET_KEY` generada con `python -c "import secrets; print(secrets.token_urlsafe(64))"`) y `POSTGRES_DB=taller_mecanico`. Verificar con `git check-ignore .env` que el archivo está ignorado.

## 2. Guarda de la base de prueba (spec `suite-de-pruebas`)

- [x] 2.1 RED: en `test/pytest/test_guarda.py` (importando de `test/pytest/guarda.py`, nunca de `conftest`), tests de `verificar_base_de_prueba` (T1: rechaza `taller_mecanico`, acepta `taller_mecanico_test`) y de `derivar_base_de_prueba` (deriva `taller_mecanico` → `taller_mecanico_test`; T2: con `taller_mecanico_test` levanta un error con el mensaje claro). Ejecutar y confirmar que fallan.
- [x] 2.2 GREEN: implementar las dos funciones puras en `test/pytest/guarda.py` (design D9). Verificar que los tests de 2.1 pasan. (El `pytest_sessionstart` se movió a la tarea 5.1, porque necesita `Settings`.)

## 3. Configuración (spec `configuracion`, S1-S8)

- [x] 3.1 RED: `test/pytest/test_config.py` con S1 (defaults) y S2 (faltan `POSTGRES_PASSWORD` y `JWT_SECRET_KEY`), aislando del `.env` real (`_env_file=None` + `monkeypatch`). Confirmar que fallan.
- [x] 3.2 GREEN: `app/core/config.py` con `Settings` (las 16 variables de DA-07, snake_case, secretos `SecretStr` sin default) y `get_settings()` con `@lru_cache` (design D2). Verificar S1 y S2 en verde.
- [x] 3.3 TRIANGULAR: S3 (contraseña vacía; clave de 31 y de 32 caracteres), S6 (clave desconocida en un `.env` temporal), S7 (`DB_POOL_SIZE=0`; `BCRYPT_COST` 3/4/31/32) y S8 (misma instancia; `cache_clear()` relee). Agregar `min_length` y los rangos hasta que pasen.
- [x] 3.4 TRIANGULAR: S4 (driver `postgresql+asyncpg`; contraseña con `@ / % :` intacta al parsear con `sqlalchemy.engine.make_url`) y S5 (`repr` sin contraseña, sin clave y sin URL). Implementar `database_url` con `@computed_field(repr=False)` y `URL.create`. Verificar en verde.
- [x] 3.5 REFACTOR: revisar nombres y agrupar los campos por bloque; verificar `pytest test/pytest/test_config.py -v` en verde.

## 4. Plantilla del entorno (spec `configuracion`, E1-E2)

- [x] 4.1 RED: `test/pytest/test_repo.py` con E1 (`env.example` declara exactamente los campos de `Settings` en mayúsculas, y los sensibles están vacíos) y E2 (`.env` está en `.gitignore`). Confirmar que E1 falla (no existe `env.example`).
- [x] 4.2 GREEN: escribir `env.example` según design D8 (16 variables agrupadas, sensibles vacías, defaults explícitos, comando fijo para la clave). Verificar E1 y E2 en verde.

## 5. Ciclo de vida (spec `ciclo-de-vida`, L1-L4, G1-G2)

- [x] 5.1 RED: en `conftest.py`, el `pytest_sessionstart` que llama a `derivar_base_de_prueba` con la base de `Settings` y `pytest.exit` si falla (T2), y las fixtures `entorno_de_prueba` y `cliente`, que importan la guarda de `guarda.py` (design D9). En `test/pytest/test_ciclo_de_vida.py`: L1 (estado poblado: `pool.size()` = `DB_POOL_SIZE`; fábrica con `expire_on_commit=False`) y L4 (sin `JWT_SECRET_KEY` el arranque falla). Confirmar que fallan (no existe `main.py`).
- [x] 5.2 GREEN: `app/core/database.py` (`crear_motor`, `crear_fabrica_de_sesiones` con la `AsyncSession` de SQLModel, `get_session`) y `main.py` con el `lifespan` (design D3) y `rutas_abiertas` vacío incluido en la app (D4). Verificar L1 y L4 en verde.
- [x] 5.3 [PERMISO] TRIANGULAR contra `taller_mecanico_test`: L2 (después del apagado, `engine.pool` fue reemplazado), L3 (arranque con `POSTGRES_PORT` cerrado sin error), G1 (dos sesiones distintas, `SELECT 1` real) y G2 (después de cerrar, `checkedout() == 0`). Verificar en verde.
- [x] 5.4 REFACTOR: verificar `pytest test/pytest/test_ciclo_de_vida.py -v` en verde y que ningún módulo crea motor ni sesiones al importarse (`python -c "import main"` no abre conexiones).

## 6. Salud (spec `salud`, H1-H7)

- [x] 6.1 RED: `test/pytest/test_salud.py` con H1 (live 200 `{"estado": "vivo"}`) y H3 (ready 200 `{"estado": "listo"}`). Confirmar que fallan con 404.
- [x] 6.2 GREEN: `app/modules/health/router.py` (design D5) e incluirlo en `rutas_abiertas` **antes** de `app.include_router` (regla de D4). Verificar si `session.exec(text("SELECT 1"))` funciona con la versión instalada de SQLModel y anotar el resultado. Verificar H1 y H3 en verde.
- [x] 6.3 [PERMISO] TRIANGULAR: H2 (live 200 con el puerto cerrado), H4 (ready 503 con el puerto cerrado; el cuerpo es exactamente el `detail` propio), H5 (contraseña incorrecta → 503), H6 (servidor TCP mudo + plazo reducido → 503) y H7 (`POST /health/ready` → 405). Agregar `asyncio.timeout` y la captura acotada `(SQLAlchemyError, OSError, TimeoutError)` hasta que pasen.
- [x] 6.4 REFACTOR: extraer la constante `TIMEOUT_READY_SEGUNDOS = 3` y el mensaje; verificar `pytest test/pytest/test_salud.py -v` en verde.

## 7. Migraciones (spec `migraciones`, A1-A2)

- [x] 7.1 RED: `test/pytest/test_migraciones.py` con A1 (`alembic.ini` sin `sqlalchemy.url` con valor) y A2 (subproceso `alembic current` con `POSTGRES_DB=<base>_test`, guarda antes de lanzarlo, código 0). Confirmar que fallan (no existe `alembic.ini`).
- [x] 7.2 [PERMISO] Ejecutar `alembic init -t async migrations`. Confirmar que A1 sigue fallando (la plantilla trae `sqlalchemy.url = driver://...`).
- [x] 7.3 GREEN: borrar la línea `sqlalchemy.url` de `alembic.ini` y dejar el comentario; adaptar `migrations/env.py` (design D6: `SQLModel.metadata`, `create_async_engine(get_settings().database_url, poolclass=NullPool)` online, la URL de `get_settings()` offline, sin `set_main_option`). Verificar A1 en verde.
- [x] 7.4 [PERMISO] Correr A2 contra `taller_mecanico_test` y verificar en verde. Verificar con `git grep -n "password\|sqlalchemy.url" alembic.ini migrations/` que no queda ninguna credencial.

## 8. Documentación y humo manual

- [x] 8.1 Escribir `test/health.http` con `GET /health/live` y `GET /health/ready` y la respuesta esperada de cada una en un comentario (no corresponde a ningún C-NN).
- [x] 8.2 Escribir `README.md` según design D10 (estado implementado/planificado con remisión a `CHANGES.md`, requisitos, puesta en marcha en Git Bash, PowerShell y Linux, cómo correr los tests). Verificar que cada comando del README existe y está escrito igual que en `env.example` y `requirements*.txt`.
- [x] 8.3 [PERMISO] Levantar `uvicorn main:app` contra `taller_mecanico` siguiendo el README y ejecutar `test/health.http`: live 200 y ready 200. Después, con PostgreSQL detenido o con un puerto erróneo en el entorno, ready 503 y live 200. Anotar el resultado en el resumen del apply.

## 9. Verificación final

- [x] 9.1 [PERMISO] Correr `pytest -v` completo contra `taller_mecanico_test` y guardar la salida en `docs/evidencias/pytest-CH-01.txt`. Verificar que los 27 escenarios automáticos (S1-S8, L1-L4, G1-G2, H1-H7, A1-A2, E1-E2, T1-T2) tienen al menos un test en verde y que no hay fallos ni errores.
- [x] 9.2 Revisar el punto de control de governance: ningún secreto con default en `Settings`; `.env` ignorado y fuera del repo (`git status` no lo lista); `alembic.ini` y `env.example` sin secretos; ningún `create_all`; todos los handlers con `async def`. Verificar con `git grep` y anotar el resultado.
- [x] 9.3 Correr `openspec validate proyecto-config-salud` y verificar que no hay errores. Dejar el change listo para que Amanda revise y commitee (`feat(CH-01): ...`).
