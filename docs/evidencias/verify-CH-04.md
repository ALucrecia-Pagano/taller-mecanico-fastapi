# Verify de CH-04 `seguridad-base-seed`

- **Fecha**: 2026-10-28
- **Verificó**: Amanda Pagano (verificación manual, antes del archive)
- **Change**: `openspec/changes/seguridad-base-seed/` (34/34 tareas; `openspec validate --strict` válido)
- **Entorno**: Windows 11, Git Bash, Python 3.13.6, PostgreSQL 17 (psql 17.11). Versiones: bcrypt 5.0.0 y PyJWT 2.15.1 (nuevas en este change), SQLModel 0.0.48, asyncpg 0.32.0, pytest 9.1.1, pytest-asyncio 1.4.0.
- **Bases**:
  - `taller_mecanico_test`: toda la suite y el seed por subproceso (S13, S15). Queda vacía al terminar.
  - `taller_mecanico`: sólo la tocó Amanda, en el checkpoint de C-14 (seed, psql y re-seed). El agente no corrió nada contra ella.
- **Governance**: CRÍTICO. El diseño se aprobó en el explore y en el propose, y las desviaciones del apply se consultaron o las pidió la alumna (ver Desvíos).

## Comandos y resultado

| # | Comando | Dónde | Resultado |
|---|---|---|---|
| 1 | `pytest -v` | `taller_mecanico_test` | **262 passed** (208 de CH-01 a CH-03 + 54 nuevos de CH-04), sin fallos |
| 2 | `pytest test/pytest/test_migraciones.py` (solo) | `taller_mecanico_test` | 8 passed, M4 incluido (corrección 1 de la alumna) |
| 3 | `alembic current` | `taller_mecanico` | `0002 (head)` |
| 4 | `python seed.py` | `taller_mecanico` | «Vaciando y cargando taller_mecanico en localhost:5432», «Datos iniciales cargados» |
| 5 | `psql -U postgres -d taller_mecanico -f test/solo_agregado.sql 2>&1 \| tee docs/evidencias/C-14-psql.txt` | `taller_mecanico` | `DO`, los 6 rechazos del disparador y el de la FK |
| 6 | `file` / `grep -c "ERROR"` / `grep -c "sólo agregado"` sobre `C-14-psql.txt` | — | UTF-8 text / 7 / 6 |
| 7 | `python seed.py` (re-seed) | `taller_mecanico` | Repone la secuencia de `orden_trabajo` que consumió la sentencia 7 |
| 8 | `openspec validate seguridad-base-seed --strict` | — | válido |

CH-04 no expone endpoints: no hay `.http` propios.

Evidencia generada:

- **`docs/evidencias/pytest-CH-04.txt`**: salida completa de `pytest -v` (262 passed en 36,41 s).
- **`docs/evidencias/CH-04-tdd-rojo.txt` y `CH-04-tdd-verde.txt`**: cada RED y cada GREEN, con un encabezado por grupo y tarea. Las corridas fallidas por errores propios están todas, con una `NOTA` que explica cada una; no se borró ninguna.
- **Red de seguridad (tarea 1.1)**: antes de tocar nada, 208 passed.
- **Revisión de reglas duras (tarea 11.1)**:
  - la contraseña literal está sólo en `seed.py`;
  - bcrypt sólo se llama dentro de `asyncio.to_thread`;
  - `time.sleep` sólo aparece en el espía de los tests, y corre dentro del hilo;
  - ningún `create_all` ni `commit()` fuera del UoW;
  - el SQL con f-string sólo interpola nombres que salen de la metadata o de constantes;
  - `config.py` y `env.example` sin cambios.

## Evidencia TDD por grupo

| Grupo | Tarea RED → GREEN | Test | Capa | RED (por qué falló) | GREEN | Triangulación / refactor |
|---|---|---|---|---|---|---|
| 1 Red de seguridad | 1.1 | Suite completa | — | — | 208 passed | — |
| 2 Dependencias | 2.1-2.2 | — | — | — | bcrypt 5.0.0 y PyJWT 2.15.1 instalados | — |
| 3 Contraseña | 3.1 → 3.2 | `test_contrasena.py` | Unitaria | No existía `app.core.security` | 5 passed | C2/C3 parametrizado (ASCII y «ñ») |
| 4 Hash | 4.1 → 4.2 | `test_hash.py` | Unitaria | No existía `hashear_password` | 7 passed | H3 (sal), H4 (costo 4 y 5); V1 |
| 5 Token | 5.1 → 5.2 | `test_token.py` | Unitaria | No existía `TokenInvalido` | 15 passed (1 corrida fallida propia, ver Desvíos 5) | T3 con 1800 y 60; T7 con 6 variantes; V2 |
| 5 401 y mapa | 5.5 → 5.6 | `test_rutas.py` | Integración ASGI | T6: `StopIteration` → 500; T7: `['TokenInvalido']` sin código | 10 passed | Prueba de detección de T7 con una subclase sin mapear |
| 6 Lifespan | 6.2 → 6.3 | `test_ciclo_de_vida.py` | Integración (`_test`) | F1-F5: sin `hash_ficticio` ni `semaforo_bcrypt` | 29 passed (con salud y rutas) | F4 con costo 5; F5 con concurrencia 1 |
| 7 Seed | 7.2 → 7.3 → 7.4 → 7.5 | `test_seed.py` | Integración (`_test`) | No existía `seed` | Verde parcial: 6, 10 y 18 passed; después 43 passed (1 corrida con S16 en rojo, ver Desvíos 6) | S1 parametrizado por entidad; S9, S10, S12; V4 |
| 7 Refactor | 7.6 | seed + sólo agregado + migraciones | Integración | — | 43 passed | Carga del catálogo simplificada |
| 8 Sin esquema | 8.2 → 8.3 | `test_migraciones.py::test_m2` | Integración (subproceso) | Traza del `ProgrammingError` en lugar del mensaje | 116 passed (toda la suite de CH-03) | V3 |
| 8 Corrección 1 | 8.4 | `test_migraciones.py` solo | Integración | M4: la metadata estaba vacía | 8 passed | — |
| 9 README | 9.1 | — | — | — | Comandos idénticos a los de 10.1 | — |
| 10 C-14 | 10.1 | Checkpoint de Amanda | Manual (`psql`) | — | 7 `ERROR`, 6 «sólo agregado», UTF-8 | — |
| 11 Cierre | 11.1-11.2 | Suite completa | — | — | 262 passed | — |

## Escenario de la spec → test

| Spec | Escenario | Test |
|---|---|---|
| `contrasenas` | C1 | `test_contrasena.py::test_c1_contrasena_comun` |
| | C2, C3 | `test_contrasena.py::test_c2_c3_borde_de_72_bytes[c2_ascii / c3_bytes_no_caracteres]` |
| | C4 | `test_contrasena.py::test_c4_vacia_o_con_nul[vacia / con_nul]` |
| | H1-H7 | `test_hash.py::test_h1_…` a `test_h7_el_semaforo_limita_la_concurrencia` |
| `token-de-acceso` | T1 | `test_token.py::test_t1_ida_y_vuelta` (+ `test_t1_el_token_valido_de_referencia_pasa`, control de T7) |
| | T2 | `test_token.py::test_t2_la_fraccion_de_segundo_sobrevive` |
| | T3 | `test_token.py::test_t3_vencimiento_desde_la_configuracion[1800 / 60]` |
| | T4-T6 | `test_token.py::test_t4_vencido`, `test_t5_otra_clave_o_contenido_alterado`, `test_t6_sin_firma_u_otro_algoritmo` |
| | T7 | `test_token.py::test_t7_claim_faltante_o_mal_formado[6 variantes]` |
| | T8 | `test_token.py::test_t8_no_es_un_token` |
| `ciclo-de-vida` | F1-F5 | `test_ciclo_de_vida.py::test_f1_…` a `test_f5_el_semaforo_sale_de_la_configuracion` |
| `errores-de-dominio` | T6 | `test_rutas.py::test_t6_token_invalido` |
| | T7 | `test_rutas.py::test_t7_el_recorrido_detecta_un_error_sin_codigo` y `test_t7_todo_error_de_dominio_de_la_aplicacion_tiene_codigo_http` |
| `datos-iniciales` | S1 | `test_seed.py::test_s1_cada_id_con_su_clave_natural[usuarios / clientes / vehiculos / repuestos / ordenes]` |
| | S2-S8 | `test_seed.py::test_s2_…` a `test_s8_un_evento_sistema` |
| | S9-S13 | `test_seed.py::test_s9_…` a `test_s13_corrida_real` |
| | S15 | `test_migraciones.py::test_m2_upgrade_downgrade_base_y_upgrade` |
| | S16 | `test_seed.py::test_s16_la_contrasena_vive_solo_en_el_seed` |
| `solo-agregado` | S14 | `test_seed.py::test_s14_c14_sobre_el_seed` |
| | E1 | Checkpoint 10.1: `docs/evidencias/C-14-psql.txt` y `docs/evidencias/capturas/C-14-solo-agregado.png` |

## V1 a V4 (contra las versiones instaladas)

| | Qué se verificó | Resultado |
|---|---|---|
| **V1** | bcrypt 5.0.0 con `\x00` y con más de 72 bytes | `hashpw(b"abc\x00")` devuelve un hash sin error, y `checkpw(b"abc\x00", hash de "abc")` da `False`: el NUL es un byte más. **La premisa del explore («daría un 500») era falsa.** Con 73 bytes, `hashpw` y `checkpw` lanzan `ValueError`. `Contrasena` sigue rechazando `\x00`, con el motivo corregido (ver Desvíos 3). Nota para CH-05: `verificar_password` no tiene guarda propia de 72 bytes, así que todo campo de contraseña tiene que usar `Contrasena`. |
| **V2** | PyJWT 2.15.1 con un `iat` `float` (OB-09) | `_validate_iat` hace `int()` sobre una variable local, sólo para comparar, y **no modifica el claim**: `1793235710.824109` vuelve idéntico. Pasado como `datetime`, se trunca (`1793235710`). **OB-09 resuelta.** |
| **V3** | Tabla inexistente al correr el seed | `sqlalchemy.exc.ProgrammingError` con `orig.sqlstate == "42P01"` («no existe la relación «estado_orden»», en el `TRUNCATE`). `main()` captura sólo ese caso. |
| **V4** | `sesion.exec(text("TRUNCATE …"))` con SQLModel 0.0.48 | Funciona dentro de la transacción del seed, y se revierte con ella (S12). |

## Desvíos

1. **`TokenInvalido` → 401 adelantado de CH-05 a CH-04**, a pedido de la alumna después del propose. Se suma un test (T7) que exige un código HTTP para cada error de dominio de `app/`. El design (D9), la spec `errores-de-dominio` y las tareas 5.5 a 5.7 se actualizaron antes del apply.
2. **Corrección 1 (tarea 8.4), a pedido de la alumna**: `test_m4` fallaba con `test_migraciones.py` corrido solo, porque el archivo no importaba los modelos. Era una falla previa de CH-03; ahora importa `MODULOS_DE_MODELOS`.
3. **Corrección 2, a pedido de la alumna**: el motivo del rechazo de `\x00` pasa a ser «no tiene uso legítimo en una contraseña y suele traer problemas en otros sistemas», no un error de bcrypt (V1). Se actualizó en la spec `contrasenas`, en el design (D3 y V1) y en el comentario de `security.py`.
4. **Un helper compartido que el design no listaba**: `test/pytest/espia_bcrypt.py`, usado por H6, H7 y F5.
5. **Corrida fallida por error propio (5.2)**: el helper `configuracion()` de `test_token.py` no admitía sobrescribir `jwt_secret_key` (T5). Se corrigió el helper, no el código.
6. **Corrida fallida esperada por el design (7.5)**: S16 detectó el literal de la contraseña en `test_ciclo_de_vida.py`, `test_contrasena.py` y `test_hash.py`. Se reemplazó por `seed.CONTRASENA_DEL_SEED`.
7. **T7 sólo recorre los errores de dominio de `app/`**: así la clase sin código que crea la prueba de detección no contamina el recorrido real. Coincide con la spec («de la aplicación»).

## Casos C-NN

| Caso | Qué aporta CH-04 |
|---|---|
| **C-14** (propio) | Probado sobre los datos del seed con pytest (S14). La evidencia la tomó Amanda sobre `taller_mecanico`: **captura** `docs/evidencias/capturas/C-14-solo-agregado.png` y **texto** `docs/evidencias/C-14-psql.txt` (UTF-8, 7 `ERROR`: los seis «La tabla … es de sólo agregado: no se permite UPDATE/DELETE» y «… viola la llave foránea «fk_orden_trabajo_estado_estado_orden»»). |
| C-02 a C-19 | `python seed.py` deja el estado inicial que usan todos los `.http`: ids del PDF, las órdenes 1 y 2, 4 bujías contra stock 2 (C-11, C-12), el catálogo (C-17), el historial de precios del filtro (C-18) y el segundo vehículo de Laura sin órdenes (C-19). |
| C-03 | Base: `JWT_EXPIRE_SECONDS` como duración del token (T3); la cookie llega en CH-05. |
| C-04 | Base de RN-09: el hash ficticio, calculado una vez en el lifespan con el costo de la configuración (F1-F4). |
| C-09 | Base de RN-07: el `iat` conserva la fracción de segundo (T2, V2); la comparación con `password_cambiada_en` llega en CH-05. |
