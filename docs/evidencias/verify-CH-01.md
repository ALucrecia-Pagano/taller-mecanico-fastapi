# Verify de CH-01 `proyecto-config-salud`

- **Fecha**: 2026-10-25
- **Verificó**: Amanda Pagano (verificación manual, antes del archive)
- **Change**: `openspec/changes/proyecto-config-salud/` (31/31 tareas; `openspec validate --strict` válido)
- **Entorno**: Windows 11, Python 3.13.6, PostgreSQL 17.11. Bases `taller_mecanico` (app) y `taller_mecanico_test` (suite).

## Comandos y resultado

| # | Comando | Resultado |
|---|---|---|
| 1 | `pytest -v` | **40 passed en 5,81 s** (contra `taller_mecanico_test`) |
| 2 | `uvicorn main:app --reload` | El servidor arranca contra `taller_mecanico` |
| 3 | `GET http://localhost:8000/health/live` (navegador) | `{"estado": "vivo"}` |
| 4 | `GET http://localhost:8000/health/ready` (navegador) | `{"estado": "listo"}` |
| 5 | `Ctrl+C` sobre uvicorn | `Application shutdown complete` (el lifespan cierra el motor con `dispose()`) |

Evidencia complementaria generada durante el apply:

- `docs/evidencias/pytest-CH-01.txt`: salida completa de `pytest -v` (40 passed en 5,56 s).
- `docs/evidencias/CH-01-tdd-rojo.txt` y `CH-01-tdd-verde.txt`: cada RED y cada GREEN, con un encabezado por grupo y tarea.
- Humo de la tarea 8.3, con dos uvicorn reales:

  | Servidor | live | ready |
  |---|---|---|
  | Contra `taller_mecanico` | 200 | 200 |
  | Con `POSTGRES_PORT` en un puerto cerrado, sin tocar el servicio ni el `.env` | 200 | 503 `{"detail": "La base de datos no responde"}` |

## Evidencia TDD por grupo

| Grupo | Archivo de test | Capa | RED (por qué falló) | GREEN | Triangulación | Refactor |
|---|---|---|---|---|---|---|
| 1. Preparación | — | — | — (scaffolding, sin tests) | — | — | — |
| 2. Guarda | `test/pytest/test_guarda.py` | Unidad | No existía `guarda.py` | 4/4 | T1 rechaza/acepta; derivación; T2 | Sin cambios |
| 3. Configuración | `test/pytest/test_config.py` | Unidad | No existía `app.core.config`; luego faltaban `min_length` y rangos (7 fallas); luego faltaba `database_url` (2 fallas) | 17/17 | S3, S6, S7 (×7), S8, S4, S5 | Sin cambios (campos ya agrupados) |
| 4. Plantilla | `test/pytest/test_repo.py` | Estático | No existía `env.example` | 3/3 | E1 ×2, E2 | — |
| 5. Ciclo de vida | `test/pytest/test_ciclo_de_vida.py` | Integración (base `_test`) | No existía `main` | 7/7 | L2, L3, G1, G2 (pasaron sin código nuevo; L2 verificado por mutación: sin `dispose()` falla) | Sin cambios |
| 6. Salud | `test/pytest/test_salud.py` | Integración HTTP | 404 (sin rutas); luego 503 ausente en H4/H5 y plazo inexistente en H6 | 7/7 | H2, H4, H5, H6, H7 | Constantes `TIMEOUT_READY_SEGUNDOS` y `MENSAJE_BASE_CAIDA` |
| 7. Migraciones | `test/pytest/test_migraciones.py` | Estático + subproceso | No existía `alembic.ini`; después del `init`, la plantilla traía `sqlalchemy.url = driver://...` | 2/2 | — | — |
| 8. Documentación | — (humo manual `test/health.http`) | Manual | — | Humo 8.3 OK | Base arriba / puerto cerrado | — |
| 9. Verificación | Suite completa | — | — | 40/40 | — | — |

## Escenario de la spec → test

| Spec | Escenario | Test |
|---|---|---|
| configuracion | S1 Carga con defaults | `test_config.py::test_s1_carga_con_los_defaults_de_da07` |
| configuracion | S2 Falta la contraseña de la base | `test_config.py::test_s2_falta_la_contrasena_de_la_base` |
| configuracion | S2 Falta la clave de firma | `test_config.py::test_s2_falta_la_clave_de_firma` |
| configuracion | S3 Contraseña vacía | `test_config.py::test_s3_contrasena_de_la_base_vacia` |
| configuracion | S3 Largo mínimo de la clave | `test_config.py::test_s3_clave_de_firma_de_31_caracteres`, `test_s3_clave_de_firma_de_32_caracteres` |
| configuracion | S4 Driver y contraseña especial | `test_config.py::test_s4_url_asyncpg_con_contrasena_especial` |
| configuracion | S5 Representación sin secretos | `test_config.py::test_s5_la_representacion_no_expone_secretos` |
| configuracion | S6 Clave desconocida en el `.env` | `test_config.py::test_s6_clave_desconocida_en_el_env` |
| configuracion | S7 Enteros positivos en cero | `test_config.py::test_s7_enteros_positivos_en_cero[DB_POOL_SIZE / JWT_EXPIRE_SECONDS / BCRYPT_MAX_CONCURRENCY]` |
| configuracion | S7 Bordes del costo de bcrypt | `test_config.py::test_s7_costo_de_bcrypt_fuera_de_rango[3, 32]`, `test_s7_costo_de_bcrypt_en_los_bordes[4, 31]` |
| configuracion | S8 Una lectura por proceso | `test_config.py::test_s8_una_lectura_por_proceso_y_relectura_explicita` |
| configuracion | E1 `env.example` sincronizado | `test_repo.py::test_e1_env_example_declara_las_variables_de_settings`, `test_e1_env_example_deja_vacios_los_secretos` |
| configuracion | E2 `.env` ignorado | `test_repo.py::test_e2_env_esta_ignorado` |
| ciclo-de-vida | L1 Estado poblado por el arranque | `test_ciclo_de_vida.py::test_l1_el_arranque_puebla_el_estado`, `test_l1_el_pool_sale_de_la_configuracion` |
| ciclo-de-vida | L2 El apagado libera el pool | `test_ciclo_de_vida.py::test_l2_el_apagado_libera_el_pool` |
| ciclo-de-vida | L3 Arranque con la base caída | `test_ciclo_de_vida.py::test_l3_arranca_con_la_base_caida` |
| ciclo-de-vida | L4 Arranque sin la clave de firma | `test_ciclo_de_vida.py::test_l4_sin_clave_de_firma_el_arranque_falla` |
| ciclo-de-vida | G1 Sesiones distintas por petición | `test_ciclo_de_vida.py::test_g1_cada_peticion_recibe_su_propia_sesion` |
| ciclo-de-vida | G2 La sesión se cierra al terminar | `test_ciclo_de_vida.py::test_g2_la_sesion_se_cierra_y_devuelve_la_conexion` |
| salud | H1 Proceso vivo | `test_salud.py::test_h1_proceso_vivo` |
| salud | H2 Vivo con la base caída | `test_salud.py::test_h2_vivo_aunque_la_base_este_caida` |
| salud | H3 Base disponible | `test_salud.py::test_h3_base_disponible` |
| salud | H4 Conexión rechazada | `test_salud.py::test_h4_conexion_rechazada` |
| salud | H5 Credenciales inválidas | `test_salud.py::test_h5_credenciales_invalidas` |
| salud | H6 Base que no contesta | `test_salud.py::test_h6_base_que_no_contesta` |
| salud | H7 Método no permitido | `test_salud.py::test_h7_metodo_no_permitido` |
| salud | Humo con el servidor levantado | Manual: `test/health.http` (tarea 8.3 y verify de Amanda) |
| migraciones | A1 `alembic.ini` sin URL | `test_migraciones.py::test_a1_alembic_ini_sin_direccion_de_la_base` |
| migraciones | A2 Humo contra la base de prueba | `test_migraciones.py::test_a2_alembic_current_contra_la_base_de_prueba` |
| suite-de-pruebas | T1 Base de la aplicación rechazada / de prueba aceptada | `test_guarda.py::test_t1_rechaza_la_base_de_la_aplicacion`, `test_t1_acepta_la_base_de_prueba` |
| suite-de-pruebas | T2 El `.env` ya apunta a la base de prueba | `test_guarda.py::test_t2_aborta_si_el_env_ya_apunta_a_la_base_de_prueba` (+ `test_deriva_la_base_de_prueba_desde_la_de_la_aplicacion`) |

Los 27 escenarios automáticos (S1-S8, L1-L4, G1-G2, H1-H7, A1-A2, E1-E2, T1-T2) tienen al menos un test en verde; el humo manual se verificó a mano.

## Desvíos aprobados durante el apply

| # | Desvío | Dónde quedó | Motivo |
|---|---|---|---|
| 1 | `pytest>=8,<10` en lugar de `>=8,<9` | `requirements-dev.txt`, design D7 | pytest 9 era la versión vigente; el tope anterior la dejaba afuera |
| 2 | La guarda vive en `test/pytest/guarda.py` y no en `conftest.py`; el `pytest_sessionstart` pasó de la tarea 2.2 a la 5.1 | design D9, tasks 2.1/2.2/5.1 | pytest desaconseja importar desde `conftest`; el hook necesita `Settings`, que nace en el grupo 3 |
| 3 | `pythonpath = .` en `pytest.ini` | `pytest.ini`, design D7 | Sin eso, el ejecutable `pytest` a secas no encuentra `app` |
| 4 | `migrations/versions/.gitkeep` | `migrations/versions/` | git no versiona carpetas vacías y `alembic` necesita `versions/` |
| 5 | Primer caso de L1 compara con `get_settings().db_pool_size` en lugar de un 5 fijo | `test_ciclo_de_vida.py` | Que el test no dependa del `.env` (el default lo prueba S1) |

Además, dentro de lo que ya decía D9 se agregaron fixtures con nombre propio: `arrancar_app`, `crear_cliente`, `puerto_cerrado` y `servidor_mudo`. Respetan su orden: `cache_clear()`, después la guarda sobre `get_settings()` y por último el lifespan.

Los refinamientos de alcance R1 (CH-01 crea sólo lo que implementa) y R2 (el README nace en CH-01) se decidieron en el explore y están en `proposal.md`.

## Casos C-NN de la consigna

**CH-01 no cubre ningún caso C-NN** (`CHANGES.md`: «Casos C-NN propios: ninguno»; ninguno de C-01 a C-19 usa `/health`). Cumple el Ejercicio 1 (8 %) y los requisitos no funcionales de Credenciales, Esquema y Asincronía. Deja lista la variable `SQL_ECHO`, que C-15 usa más adelante (CH-09/CH-11). `test/health.http` es humo manual y no corresponde a ningún C-NN.
