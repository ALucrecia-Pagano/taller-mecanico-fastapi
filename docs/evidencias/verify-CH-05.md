# Verify de CH-05 — autenticacion

## Verificación manual

- **Fecha**: 2026-10-29.
- **Verificó**: Amanda Pagano, antes del archive.
- **Change**: CH-05 `autenticacion`, trabajado con **Codex**.
- **Fuente de esta sección**: verificación realizada y comunicada por Amanda; el agente no repitió estos pasos.

| # | Comando / acción | Resultado informado por Amanda |
|---|---|---|
| 1 | `pytest -v` | **349 passed**. |
| 2 | Arranque con `uvicorn` (argumentos exactos no informados) y apertura de `/docs` | Servidor levantado; documentación disponible para probar la API. |
| 3 | Desde `/docs`, `POST /auth/login` con `admin@example.com` | **200**, mensaje `Sesión iniciada`, sin token en el cuerpo. |
| 4 | Inspección de cookies en el navegador | Cookie **`access_token`** presente con **`HttpOnly`**. |

Estos son los resultados manuales confirmados por Amanda; no se atribuyen a esta verificación otros endpoints ni atributos de cookie. La evidencia automatizada y el detalle TDD se conservan abajo.

## Informe de implementación

El informe siguiente registra el estado al cerrar el apply, anterior a la verificación manual y al archive.

Implementado con Codex, desde `docs/evidencias/explore-CH-05.md` y los artefactos definitivos
de `openspec/changes/autenticacion/`. La consigna se consultó desde su conversión `.md`;
el PDF sigue mandando. Este informe no archiva el change ni sustituye la revisión de Amanda.

### Alcance y seguridad de las corridas

- Aprobación explícita de apply CRÍTICO autónomo; todas las conexiones de estas corridas se
  dirigieron a **taller_mecanico_test** mediante la guarda existente. No se tocó la base de desarrollo.
- No se abrió, mostró, copió ni modificó `.env`. Settings, pytest, Alembic y seed usaron su carga
  implícita, expresamente aclarada como permitida por Amanda. No se imprimieron Settings ni secretos.
- Sin `git add`, commit, push, instalaciones ni desinstalaciones; pypdf sigue sólo como herramienta.
- Baseline previo a producción: **262 passed**, registrado en `CH-05-tdd-verde.txt`.
- Pre-regresión completa: **345 passed**; luego se añadió triangulación contractual HTTP y
  la comprobación del intento exitoso desde otra sesión. El resultado final se consulta en
  `pytest-CH-05.txt` (última ejecución de tests, tarea 8.5).
- **Resultado final: 349 passed in 52.45s**, salida completa de `pytest -v`, código de salida 0.
  OpenSpec: 43/43 tareas completas; validación estricta del change correcta.

### Tabla escenario → test

Las rutas de test de esta tabla son relativas a `test/pytest/`. Los parámetros distinguen
las variantes cuando varios escenarios comparten un test. Son **47 escenarios de las specs**;
el test de arranque y los tres `.http` son verificaciones adicionales.

| Escenario | Archivo | Test / variante |
|---|---|---|
| R1 | test_auth_registro.py | test_r1_registro_crea_cuatro_filas |
| R2 | test_auth_registro.py | test_r2_r3_r4_duplicado_no_deja_filas — email |
| R3 | test_auth_registro.py | test_r2_r3_r4_duplicado_no_deja_filas — documento con usuario |
| R4 | test_auth_registro.py | test_r2_r3_r4_duplicado_no_deja_filas — ficha sin usuario |
| R5 | test_auth_registro.py | test_r5_fallo_tardio_revierte_todas_las_filas |
| L1 | test_auth_login.py | test_l1_login_activo |
| L2 | test_auth_login.py | test_l2_l3_inexistente_verifica_ficticio_una_vez — contraseña mala |
| L3 | test_auth_login.py | test_l2_l3_inexistente_verifica_ficticio_una_vez — inexistente / espía |
| L4 | test_auth_login.py | test_l4_l5_inactivo_registra_fallo — clave correcta |
| L5 | test_auth_login.py | test_l4_l5_inactivo_registra_fallo — clave incorrecta |
| L6 | test_auth_login.py | test_l6_token_solo_roles_vigentes |
| I1 | test_intentos_acceso.py; test_auth_login.py | test_i1_cinco_fallos_bloquean_y_no_agregan; test_i1_i6_429_no_bcrypt_no_fila_ni_ip_falsa |
| I2 | test_intentos_acceso.py | test_i2_i3_redondeo_consulta_unica_y_borde — ceil y una consulta |
| I3 | test_intentos_acceso.py | test_i2_i3_redondeo_consulta_unica_y_borde — salida exacta de ventana |
| I4 | test_intentos_acceso.py | test_i4_exito_reinicia_sin_borrar |
| I5 | test_intentos_acceso.py | test_i5_pares_independientes — otro correo / otra IP |
| I6 | test_auth_login.py | test_i1_i6_429_no_bcrypt_no_fila_ni_ip_falsa — X-Forwarded-For |
| I7 | test_intentos_acceso.py | test_i7_i8_intento_persistido_aunque_peticion_revierte — éxito y fallo |
| I8 | test_intentos_acceso.py; test_auth_login.py | test_i7_i8_intento_persistido_aunque_peticion_revierte; test_l1_login_activo — otra sesión ve exito=true al devolver cookie |
| K1 | test_auth_cookie.py | test_k1_k2_cookie_atributos |
| K2 | test_auth_cookie.py | test_k1_k2_cookie_atributos — Secure true / false |
| K3 | test_auth_dependencias.py | test_a1_k3_sin_cookie_no_autentica — Bearer firmado válido |
| K4 | test_auth_cookie.py | test_k4_logout_publico_con_y_sin_cookie |
| K5 | test_auth_dependencias.py | test_k5_cookie_valida_ignora_header |
| A1 | test_auth_dependencias.py | test_a1_k3_sin_cookie_no_autentica — sin Bearer |
| A2 | test_auth_dependencias.py | test_a2_token_invalido_mensaje_neutro — texto, firma, vencido, claims, algoritmo |
| A3 | test_auth_dependencias.py | test_a3_a4_usuario_no_valido — inexistente |
| A4 | test_auth_dependencias.py | test_a3_a4_usuario_no_valido — inactivo |
| A5 | test_auth_dependencias.py | test_a5_a6_a7_iat_microsegundos — 1 µs anterior |
| A6 | test_auth_dependencias.py | test_a5_a6_a7_iat_microsegundos — igualdad exacta |
| A7 | test_auth_dependencias.py; test_auth_login.py | test_a5_a6_a7_iat_microsegundos — posterior; cookie válida con fecha nula en login/perfil |
| A8 | test_auth_dependencias.py | test_a8_anterior_y_nuevo_en_mismo_segundo |
| P1 | test_auth_password.py | test_p1_cambio_actualiza_hash_fecha_bandera_y_evento |
| P2 | test_auth_password.py | test_p2_actual_incorrecta_no_cambia_nada |
| P3 | test_auth_password.py; test_auth_schemas.py | test_p3_p3b_igualdad_422_cero_bcrypt_sin_escrituras — pendiente; test_p3_p3b_contrato_rechaza_igualdad |
| P3b | test_auth_password.py; test_auth_schemas.py | test_p3_p3b_igualdad_422_cero_bcrypt_sin_escrituras — sin obligación; test_p3_p3b_contrato_rechaza_igualdad |
| P4 | test_auth_password.py | test_p4_fallo_del_evento_revierte_y_no_emite_cookie |
| P5 | test_auth_password.py | test_p5_y3_cookie_nueva_vale_y_anterior_no_mismo_segundo |
| Y1 | test_auth_yo.py | test_y1_forma_exacta_da16 |
| Y2 | test_auth_yo.py | test_y2_roles_revocados_o_vencidos_divergen — revocado / vencido |
| Y3 | test_auth_yo.py; test_auth_password.py | test_y3_yo_disponible_con_cambio_pendiente; test_p5_y3_cookie_nueva_vale_y_anterior_no_mismo_segundo |
| V1 | test_auth_schemas.py | test_v1_registro_acepta_72_bytes; test_v1_todos_los_campos_aceptan_72_bytes — ASCII / UTF-8 |
| V2 | test_auth_schemas.py | test_v2_v3_rechaza_73_bytes_vacio_nul; test_v2_v3_v4_api_422_sin_bcrypt — 73 bytes |
| V3 | test_auth_schemas.py | test_v2_v3_rechaza_73_bytes_vacio_nul; test_v2_v3_v4_api_422_sin_bcrypt — vacío / NUL |
| V4 | test_auth_schemas.py | test_v4_rechaza_extras; test_v2_v3_v4_api_422_sin_bcrypt — extra rol |
| E429 | test_rutas.py | test_e429_e429b_retry_after_en_handler_y_dependencia |
| E429b | test_rutas.py | test_e429_e429b_retry_after_en_handler_y_dependencia; test_t6_token_invalido; test_t7_todo_error_de_dominio_de_la_aplicacion_tiene_codigo_http; regresión T1–T5 |

Adicionales: `test_auth_arranque.py::test_auth_arranque_registra_modelos_sin_importar_seed`
y `test_http_auth.py::{test_http_c02_registro,test_http_c03_c04_login_cookie_y_credenciales,test_http_c05_limite_intentos}`.

### TDD Cycle Evidence

Los logs conservan cada ejecución y encabezado grupo/tarea en `CH-05-tdd-rojo.txt` y
`CH-05-tdd-verde.txt`, siempre anexados con `tee -a`. No se borraron corridas fallidas.
El punto de partida fue 262/262. Las triangulaciones que ya pasaron con código existente
no se forzaron a rojo artificial ni motivaron producción adicional. Refactor incluye revisión
sin cambio cuando no había duplicación que resolver; cada cambio efectivo se volvió a ejecutar.

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 1.1–1.2 | — | Preparación | Aprobación / skills cargadas | N/A | N/A | N/A | N/A |
| 1.3 | suite existente | Integración/unit | 262/262 | N/A | Baseline | N/A | N/A |
| 2.1–2.2 | test_auth_schemas.py | Contrato | Nuevo archivo | Import ausente | 1 passed | — | — |
| 2.3 | test_auth_schemas.py | Contrato | 1 passed | Login/Cambio ausentes | 29 passed | ASCII/UTF-8, 72/73, vacío/NUL, extras | — |
| 2.4 | test_auth_schemas.py | Contrato | 29 passed | Igualdad no rechazada | 31 passed | Dos claves distintas | — |
| 2.5 | test_auth_schemas.py | Contrato | 31 passed | — | 31 passed | Preservada | EntradaAuth, verde |
| 3.1–3.2 | test_auth_registro.py | API/DB | 262/262 core | 404 | 1 passed | — | — |
| 3.3 | test_auth_registro.py | API/DB | 1 passed | Mensaje genérico | 4 passed | Email y dos documentos | — |
| 3.4 | test_auth_registro.py | API/DB | UoW ya implementado | Sin producción nueva | 5 passed | Excepción tardía y snapshot | — |
| 3.5–3.6 | test_auth_registro.py; test_http_auth.py; test_rutas.py | API/DB | Verde previo | Sin producción nueva | 16 passed | C-02 real desde archivo | Revisión verde |
| 4.1–4.2 | test_intentos_acceso.py | DB | UoW baseline | Adaptador ausente | 2 passed | Éxito/fallo e independencia | — |
| 4.3 | test_intentos_acceso.py | DB | 2 passed | Repo/función ausentes | 3 passed | Cinco fallos | — |
| 4.4 | test_intentos_acceso.py; test_auth_login.py | DB/API | Verde previo | Base del límite en 4.3 | 7 passed + integración grupo 5 | Ventana, ceil, pares, reinicio, XFF | — |
| 4.5 | test_rutas.py | HTTP | Baseline rutas | 500 y T7 sin mapa | 12 passed | Handler/dependencia | — |
| 4.6 | test_intentos_acceso.py; test_rutas.py | DB/HTTP | Verde previo | — | 19 passed | Preservada | Revisión verde |
| 5.1–5.2 | test_auth_login.py | API/DB | Verde anterior | 404 | 1 passed | — | — |
| 5.3 | test_auth_login.py | API/DB/espía | 1 passed | Cero verificaciones ficticias | 2 passed | Real/ficticio y mismo cuerpo | — |
| 5.4 | test_auth_login.py | API/DB/espía | 2 passed | Inactivo 200, roles vacíos | 6 passed | Dos claves inactivo, roles y XFF/cero bcrypt | — |
| 5.5 | test_auth_cookie.py | API | Verde anterior | Logout 404 | 4 passed | Secure y cookie presente/ausente | — |
| 5.6 | login/cookie/intentos | API/DB | Verde previo | — | 17 passed | Preservada | Repo compuesto en UoW |
| 5.7 | test_http_auth.py | Archivo HTTP/API/DB | Verde previo | Sin producción nueva | 2 passed | C-02/C-05 reales | Revisión |
| 6.1–6.2 | test_auth_dependencias.py | API/DB | Verde anterior | /yo 404 | 2 passed | Sin cookie y Bearer | — |
| 6.3 | test_auth_dependencias.py | API/DB | 2 passed | Cookie válida aún rechazada | 10 passed | Tokens/usuarios inválidos y header extra | — |
| 6.4 | test_auth_dependencias.py | API/DB | 10 passed | Token anterior admitido | 14 passed | Antes/igual/después y mismo segundo | — |
| 6.5 | test_auth_yo.py | API/DB | Verde anterior | Forma mínima incompleta | 4 passed | Roles revocados/vencidos, pendiente | — |
| 6.6 | dependencias/yo/rutas | API/DB | Verde previo | — | 30 passed | Preservada | D6 constante, T6 intacto |
| 7.1–7.2 | test_auth_password.py | API/DB | Verde anterior | 404 | 1 passed | — | — |
| 7.3 | test_auth_password.py | API/DB | UoW/contrato existentes | Sin producción nueva | 3 passed | Actual incorrecta y fallo evento | — |
| 7.4 | test_auth_password.py | API/DB/espía/reloj | 3 passed | Contrato/iat ya rojos en 2.4/6.4 | 6 passed | Igualdad con/sin obligación, Y3/P5 | — |
| 7.5 | password/cookie/arranque | API + proceso aislado | Verde previo | Arranque sin OrdenTrabajo | 1 pasado aislado; 11 passed conjunto | Regresión sin imports de seed | Cookie centralizada, verde |
| 8.1 | test_http_auth.py | Archivo HTTP/API/DB | Verde previo | Runner ignoraba no-cookie-jar | 3 passed | Bearer JWT real, tres archivos | Soporte mínimo del runner |
| 8.2 | suite y schemas/login | Integración | 345 passed pre-regresión | Sin producción nueva | Triangulación API y login | 422/cero bcrypt por campo; intento éxito visible | Auditoría sin cambios de producción |
| 8.3 | Este informe | Documentación | Logs conservados | N/A | N/A | Mapa de 47 escenarios | N/A |
| 8.4 | OpenSpec | Artefactos | Planning existente | N/A | validate --strict | N/A | N/A |
| 8.5 | suite completa | Unit/integración | Regresión previa verde | N/A | 349 passed (pytest-CH-05.txt) | Suite completa | Sin cambios posteriores de código |

### Desvíos, hallazgos y límites

1. **Sin desvíos de conducta respecto a design/specs.** La comprobación HTTP I6 se completó
   en el grupo 5, una vez disponible login; el checkbox 4.4 se dejó pendiente hasta comprobarla.
2. **Arranque independiente de seed:** al probar un proceso limpio, SQLAlchemy no encontraba
   OrdenTrabajo en la relación de Usuario. El seed importado por otras pruebas ocultaba el problema.
   RED aislado seguido de imports explícitos de los cuatro módulos de modelos en main lo corrigió,
   sin migraciones, cambios de modelos ni nuevas políticas. La regresión permanece en la suite.
3. **Lanzador Windows:** dos invocaciones iniciales fallaron antes de pytest por quoting/selección
   de shell; se anotaron y se usó un script temporal de Git Bash. Desde la tarea 3.3 se fija
   PYTHONUTF8=1 para nuevas salidas; no se reescribió la evidencia previa ni sus caracteres originales.
4. **Demos HTTP:** el runner lee y ejecuta los pedidos de los archivos reales sobre ASGI y `_test`,
   con seed antes de cada archivo. Para C-03 respeta no-cookie-jar por pedido y usa el JWT real del
   login en Bearer, cuya validez se comprueba aunque el transporte se rechace.
5. **Tiempos:** ningún test mide tiempos. `CH-05-http.txt` contiene muestras de una demo standalone
   adicional, sin umbrales ni aserciones temporales. C-04 observado: 8.247 ms y 6.530 ms; sexto C-05:
   3.679 ms, 429 y Retry-After=60. Son muestras para revisión humana, no una prueba de igualdad
   temporal ni una medición representativa de producción (la demo usa costo 4).
6. **Concurrencia:** no se añadió serialización de logins concurrentes ni política nueva de carreras;
   se conserva el alcance secuencial de C-05 y el trade-off de costos bcrypt históricos de CH-04.

### Archivos nuevos y modificados en apply

**Nuevos de producción:** `app/core/dependencies.py`, `app/modules/clientes/repository.py`,
`app/modules/usuarios/{schemas,repository,unit_of_work,service,router}.py`.

**Modificados:** `main.py` (router y registro de modelos), `app/core/errores.py`,
`app/core/rutas.py` (429 y Retry-After), `README.md`, `test/pytest/test_rutas.py`,
`openspec/changes/autenticacion/tasks.md` (seguimiento).

**Nuevos de pruebas:** `test/pytest/auth_helpers.py`, `test_auth_schemas.py`, `test_auth_registro.py`,
`test_intentos_acceso.py`, `test_auth_login.py`, `test_auth_cookie.py`, `test_auth_dependencias.py`,
`test_auth_yo.py`, `test_auth_password.py`, `test_auth_arranque.py`, `test_http_auth.py`;
los tres archivos `test/c02_registro.http`, `test/c03_c04_login.http`, `test/c05_limite_intentos.http`.

**Evidencias:** `CH-05-tdd-rojo.txt`, `CH-05-tdd-verde.txt`, `CH-05-http.txt`, este informe
y `pytest-CH-05.txt`. `docs/consigna/consigna-taller-mecanico.md`, `explore-CH-05.md` y los
artefactos de propose ya existían antes del apply; no son código creado durante esta fase.

**Intactos:** `.env`, arnés conftest, `security.py`, modelos, migraciones y requirements.
Próximo paso: revisión de Amanda, sin archive ni commits automáticos.
