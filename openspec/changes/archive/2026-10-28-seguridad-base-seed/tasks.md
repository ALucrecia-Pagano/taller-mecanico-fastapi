# Tasks — CH-04 `seguridad-base-seed`

Convenciones:
- **[PERMISO]**: se describe la acción y se espera la confirmación de Amanda antes de ejecutarla. Lo llevan:
  - la instalación de `bcrypt` y `PyJWT`;
  - **toda corrida contra una base** (cualquier test que use `taller_mecanico_test`, el seed por subproceso);
  - el cambio al test 19a de CH-03 (`test_m2`).
  
  Las corridas de `test_contrasena.py`, `test_hash.py` y `test_token.py` no tocan ninguna base.
- **FRENO**: el apply se detiene hasta que Amanda diga que siga. Se usa en el checkpoint de C-14.
- **TDD estricto**: en cada grupo, primero el test que falla (RED, con la falla confirmada al ejecutarlo), después el código mínimo (GREEN), y luego la triangulación y el refactor con los tests en verde.
  - Cada corrida RED se agrega, **sin borrar las anteriores**, a `docs/evidencias/CH-04-tdd-rojo.txt`.
  - Cada corrida GREEN se agrega a `docs/evidencias/CH-04-tdd-verde.txt`.
- Referencias:
  - Los IDs (C1, H7, T2, F3, S12, S15) son los escenarios de `specs/`.
  - D1-D8 y V1-V4 remiten a `design.md`.
- Governance **CRÍTICO**: este diseño ya está aprobado. Toda desviación de `design.md` se frena y se consulta antes de escribirla.
- El agente sólo toca la base `taller_mecanico_test`; `taller_mecanico` la toca sólo Amanda.
- No se commitea nada: los commits los hace Amanda.

## 1. Red de seguridad

- [x] 1.1 [PERMISO] Correr `pytest -v` contra `taller_mecanico_test` antes de tocar nada y anotar la línea base en el resumen del apply (CH-03 cerró en verde, ver `docs/evidencias/pytest-CH-03.txt`). Si algo falla, frenar y reportarlo como falla previa: no se arregla en CH-04.

## 2. Dependencias (design D1)

- [x] 2.1 Agregar a `requirements.txt` `bcrypt>=4.0,<6` y `PyJWT>=2.10,<3`, con el comentario de pisos y topes que ya tiene el archivo. Verificarlo leyendo el archivo.
- [x] 2.2 [PERMISO] Instalar con `pip install -r requirements.txt` en el `.venv`. Verificar con `pip show bcrypt PyJWT` y anotar las versiones instaladas en el resumen del apply.

## 3. Contrato de contraseña, sin base (spec `contrasenas`: C1-C4; design D3)

- [x] 3.1 RED: crear `test/pytest/test_contrasena.py` con C1-C4 sobre `TypeAdapter(Contrasena)`. C2 y C3 parametrizados con el par aceptada/rechazada. C4 con `""` y `"abc\x00"`. Correr `pytest test/pytest/test_contrasena.py -v` y confirmar que falla porque `app/core/security.py` no existe. Guardar la corrida en `CH-04-tdd-rojo.txt`.
- [x] 3.2 GREEN: crear `app/core/security.py` con el tipo `Contrasena` (`Field(min_length=1)` y un `AfterValidator` que rechaza `\x00` y más de 72 bytes UTF-8). `min_length` y `\x00` llevan el comentario «No especificado en la consigna». Correr el archivo y confirmar C1-C4 en verde. Guardar en `CH-04-tdd-verde.txt`.
- [x] 3.3 REFACTOR: nombres y mensajes de error. Verificar `test_contrasena.py` en verde.

## 4. Hash con bcrypt, sin base (spec `contrasenas`: H1-H7; design D2)

- [x] 4.1 RED: crear `test/pytest/test_hash.py` con H1-H7, con `costo=4` y un `asyncio.Semaphore` creado en cada test. H6 y H7 usan el envoltorio de D2 sobre `bcrypt.hashpw`/`checkpw`, que registra el hilo y cuenta las llamadas activas con un `Lock`. Correr y confirmar que falla porque no existen `hashear_password` ni `verificar_password`. Guardar en `CH-04-tdd-rojo.txt`.
- [x] 4.2 GREEN: `hashear_password` y `verificar_password` en `security.py` (`async with semaforo` más `asyncio.to_thread`; `gensalt(rounds=costo)`; `ValueError` propio con más de 72 bytes antes de llamar a bcrypt). Confirmar H1-H7 en verde. Guardar en `CH-04-tdd-verde.txt`.
- [x] 4.3 **V1**: con la versión instalada, probar en una sesión de Python cómo responde bcrypt a `b"abc\x00"` y a 73 bytes en `hashpw` y en `checkpw`. Anotarlo en `design.md` (sección «Verificaciones del apply») y en el resumen. Si contradice D2 o D3, frenar y consultar.
- [x] 4.4 REFACTOR: revisar que ninguna llamada a bcrypt quede fuera de `to_thread` (buscar `bcrypt.` en `security.py`). Verificar `test_hash.py` en verde.

## 5. Token, sin base (spec `token-de-acceso`: T1-T8; design D5)

- [x] 5.1 RED: crear `test/pytest/test_token.py` con T1-T8. Las `Settings` del test se arman con una clave de prueba de 64 caracteres. Hay `ahora` fijo con `.123456` para T2 y `ahora` 2 h atrás para T4. T6 arma `none` y `HS512`, y T7 firma payloads a mano. Correr y confirmar que falla porque no existen `emitir_token`, `decodificar_token`, `DatosToken` ni `TokenInvalido`. Guardar en `CH-04-tdd-rojo.txt`.
- [x] 5.2 GREEN: `TokenInvalido(ErrorDeDominio)` en `app/core/errores.py`, con su docstring (lo lanza la validación del token y se traduce a 401, tarea 5.6). Además, `DatosToken`, `emitir_token` y `decodificar_token` en `security.py` (`iat` como `float`, `algorithms=[…]` fijo, `require`, y conversión de todo error a `TokenInvalido` con `from None`). Confirmar T1-T8 en verde. Guardar en `CH-04-tdd-verde.txt`.
- [x] 5.3 **V2**: confirmar con la versión instalada de PyJWT que T2 pasa sin trucos: el `iat` decodificado es el mismo `float`. Anotar la versión en `design.md` y marcar OB-09 como verificada en el resumen. Si PyJWT modificara el claim, frenar y consultar.
- [x] 5.4 REFACTOR: revisar que ningún mensaje de `TokenInvalido` incluya texto de PyJWT. Verificar `test_token.py`, `test_hash.py` y `test_contrasena.py` en verde.
- [x] 5.5 RED (spec `errores-de-dominio`: T6, T7; design D9): en `test/pytest/test_rutas.py`, agregar T6 (una dependencia lanza `TokenInvalido`: 401 y `{"detail": "Token inválido"}`) y T7 (`import main`, recorrido recursivo de las subclases de `ErrorDeDominio`, cada una con un código según `codigo_http`, y el conjunto no vacío y con `TokenInvalido`). Correr `pytest test/pytest/test_rutas.py -v` y confirmar que T6 y T7 fallan porque `TokenInvalido` no está en el mapa, y que T1-T5 siguen en verde. Guardar en `CH-04-tdd-rojo.txt`.
- [x] 5.6 GREEN: sumar `TokenInvalido: status.HTTP_401_UNAUTHORIZED` a `CODIGO_HTTP` en `app/core/rutas.py`. Correr `test_rutas.py` y confirmar T1-T7 en verde. Guardar en `CH-04-tdd-verde.txt`.
- [x] 5.7 REFACTOR: actualizar el docstring de `test_rutas.py` (T1-T7) y revisar que `rutas.py` no cambió más allá del mapa. Verificar `test_rutas.py` en verde.

## 6. Lifespan: semáforo y hash ficticio (spec `ciclo-de-vida`: F1-F5; design D4, D7)

- [x] 6.1 En `test/pytest/conftest.py`, sumar `monkeypatch.setenv("BCRYPT_COST", "4")` a `entorno_de_prueba`.
- [x] 6.2 RED: agregar F1-F5 a `test/pytest/test_ciclo_de_vida.py`:
  - F2 espía `main.hashear_password`;
  - F4 fija `BCRYPT_COST=5` antes de arrancar;
  - F5 fija `BCRYPT_MAX_CONCURRENCY=1` y usa el envoltorio de D2.
  
  [PERMISO] Correr `pytest test/pytest/test_ciclo_de_vida.py -v` contra `taller_mecanico_test` y confirmar que F1-F5 fallan (no hay `semaforo_bcrypt` ni `hash_ficticio` en `app.state`) y que L1-L4, G1 y G2 siguen en verde. Guardar en `CH-04-tdd-rojo.txt`.
- [x] 6.3 GREEN: en el lifespan de `main.py`, crear `app.state.semaforo_bcrypt` y calcular `app.state.hash_ficticio` **dentro del `try`** (D4), con el comentario de la entrada aleatoria descartada. [PERMISO] Correr `pytest test/pytest/test_ciclo_de_vida.py test/pytest/test_salud.py test/pytest/test_rutas.py -v` y confirmar F1-F5 y todo CH-01 y CH-02 en verde. Guardar en `CH-04-tdd-verde.txt`.

## 7. Seed (spec `datos-iniciales`: S1-S13, S16; spec `solo-agregado`: S14; design D6, D7)

- [x] 7.1 En `conftest.py`, escribir la fixture `base_sembrada` (D7): guarda, `Settings` con `bcrypt_cost=4` y `sembrar`; en el teardown, el `TRUNCATE` de D6, que deja `_test` vacía. Agregar el helper de la foto de S9.
- [x] 7.2 RED: crear `test/pytest/test_seed.py` con S1-S14 y S16. S7 y S16 usan `seed.CONTRASENA_DEL_SEED`, S12 usa `monkeypatch` sobre el último paso de carga y S14 importa `_bloques_del_archivo` de `test_solo_agregado.py`. [PERMISO] Correr `pytest test/pytest/test_seed.py -v` contra `taller_mecanico_test` y confirmar que falla porque `seed.py` no existe. Guardar en `CH-04-tdd-rojo.txt`.
- [x] 7.3 GREEN, catálogo y usuarios: crear `seed.py` con `CONTRASENA_DEL_SEED`, `calcular_hashes` (7 hashes con `gather` bajo su propio semáforo, antes de la transacción), `sembrar` (motor propio, una sola transacción, `dispose` en `finally`) y `cargar_datos_iniciales` con:
  - el `TRUNCATE` de la metadata;
  - el catálogo desde `CodigoEstado`, con las descripciones «Pendiente», «En reparación», «Terminada» y «Cancelada», marcadas «No especificado en la consigna»;
  - los usuarios 1 a 7 y sus asignaciones.
  
  **V4**: comprobar que `session.exec(text("TRUNCATE …"))` funciona con la versión instalada. [PERMISO] Correr `test_seed.py` y confirmar en verde S5, S6, S7 y la parte de usuarios de S1. Guardar en `CH-04-tdd-verde.txt`.
- [x] 7.4 GREEN, clientes, vehículos y repuestos: clientes 1 y 2, vehículos 1 a 3, y repuestos 1 a 4 con su «Stock inicial» y la línea de precio del filtro. El stock directo lleva el comentario de excepción acotada (R2 del proposal). [PERMISO] Correr `test_seed.py` y confirmar S1 (salvo órdenes), S3 y la parte de precio de S4 en verde. Guardar en `CH-04-tdd-verde.txt`.
- [x] 7.5 GREEN, órdenes y evento: órdenes 1 y 2, con sus ítems, el total calculado y los tres historiales de estado, y al final el evento `SISTEMA` / «Carga de los datos iniciales». Agregar `main()` (imprime base, host y puerto, y corre `asyncio.run(sembrar(...))`) y el bloque `if __name__ == "__main__"`. [PERMISO] Correr `test_seed.py` y confirmar S1-S14 y S16 en verde. Guardar en `CH-04-tdd-verde.txt`.
- [x] 7.6 REFACTOR: nombres, comentarios (DA-01 a DA-06 citados donde corresponde) y el orden de alta igual al de `CHANGES.md`. [PERMISO] Correr `test_seed.py`, `test_solo_agregado.py` y `test_migraciones.py` y confirmar todo en verde: la base `_test` vacía después del seed no rompe M3, X1, X2 ni D5.

## 8. Seed sin esquema dentro del ciclo de CH-03 (spec `datos-iniciales`: S15; design D6, D7)

- [x] 8.1 [PERMISO] Modificar `test_m2_upgrade_downgrade_base_y_upgrade` en `test/pytest/test_migraciones.py` (el test 19a de CH-03). Después de `downgrade base` y antes de volver a `head`, corre `python seed.py` por subproceso (`POSTGRES_DB=<base>_test`, `BCRYPT_COST=4`) y verifica `returncode != 0` y «Corré `alembic upgrade head` primero» en la salida. El `finally` existente se mantiene.
- [x] 8.2 RED: [PERMISO] Correr `pytest test/pytest/test_migraciones.py -v` y confirmar que `test_m2` falla porque el seed termina con la traza de la tabla inexistente y no con el mensaje. Guardar en `CH-04-tdd-rojo.txt`.
- [x] 8.3 GREEN: **V3**. Confirmar la excepción y el SQLSTATE con que llega la tabla inexistente (se espera `ProgrammingError` con `42P01`). En `main()` de `seed.py`, capturar sólo ese caso y terminar con `sys.exit("Corré `alembic upgrade head` primero")`; cualquier otro error se propaga. [PERMISO] Correr `pytest test/pytest/test_migraciones.py test/pytest/test_esquema.py test/pytest/test_solo_agregado.py test/pytest/test_restricciones.py test/pytest/test_navegacion.py test/pytest/test_modelos.py -v` y confirmar **toda la suite de CH-03 en verde**, con S15. Guardar en `CH-04-tdd-verde.txt`.

- [x] 8.4 (Corrección pedida por Amanda durante el apply.) Hacer que `test_m4` pase con `test_migraciones.py` corrido solo: el archivo importa los modelos de `esquema_esperado.MODULOS_DE_MODELOS`, la misma lista de `migrations/env.py`. RED: `pytest test/pytest/test_migraciones.py` con M4 en rojo. GREEN: 8 passed. Las dos corridas quedan en las evidencias.

## 9. README (design D1, D8)

- [x] 9.1 Actualizar `README.md`:
  - la fila de CH-04 en «Estado»;
  - en «Puesta en marcha», el paso nuevo `python seed.py` después de `alembic upgrade head`, con lo que hace (vacía y carga los datos iniciales, muestra a qué base va, y sin esquema pide `alembic upgrade head`) y que se corre antes de cada archivo `.http`;
  - la contraseña ficticia **no** se escribe en el README;
  - en «Caso C-14», los pasos en Git Bash de la tarea 10.1, incluido el re-seed final, y la aclaración de no usar `winpty`.
  
  Verificar leyendo el README que los comandos coinciden con los de 10.1.

## 10. Checkpoint de C-14, a cargo de Amanda (spec `solo-agregado`: E1; design D8)

- [x] 10.1 **FRENO — evidencia de C-14 por Amanda.** El agente no corre nada contra `taller_mecanico`. Amanda ejecuta en Git Bash, en la raíz del repo:
  ```bash
  source .venv/Scripts/activate
  alembic upgrade head                      # si taller_mecanico no está en head
  python seed.py
  export PGCLIENTENCODING=UTF8
  psql -U postgres -d taller_mecanico -f test/solo_agregado.sql 2>&1 | tee docs/evidencias/C-14-psql.txt
  #   -> captura de esa ventana: docs/evidencias/capturas/C-14-solo-agregado.png
  file docs/evidencias/C-14-psql.txt                     # esperado: UTF-8 text
  grep -c "ERROR" docs/evidencias/C-14-psql.txt          # esperado: 7
  grep -c "sólo agregado" docs/evidencias/C-14-psql.txt  # esperado: 6
  python seed.py                            # repone la secuencia que consumió la sentencia 7
  ```
  No usar `winpty psql`. La tarea se marca cuando Amanda confirma y existen los dos archivos. El agente lo verifica con `file` y `grep -c` sobre el `.txt` (lectura) y con la existencia del `.png`.

## 11. Cierre

- [x] 11.1 Revisión de reglas duras sobre los archivos del change, por lectura:
  - ninguna contraseña ni clave en el código, salvo `CONTRASENA_DEL_SEED` en `seed.py` (S16);
  - ninguna llamada a bcrypt fuera de `to_thread`;
  - ningún `time.sleep` fuera de los hilos de prueba;
  - ningún `create_all` (M6);
  - `env.example` sin cambios necesarios (sin variables nuevas).
  
  Anotar el resultado en el resumen del apply.
- [x] 11.2 [PERMISO] Correr la suite completa con `pytest -v` contra `taller_mecanico_test` y guardar la salida completa en `docs/evidencias/pytest-CH-04.txt`. Verificar que todo está en verde y que el archivo existe.
