# Verificación CH-06 — autorizacion-usuarios-roles

## Verificación manual

- **Fecha**: 2026-10-30.
- **Verificó**: Amanda Pagano.
- **Change**: CH-06 `autorizacion-usuarios-roles`, implementado con **Codex** y cerrado con **Copilot**.
- **Base utilizada**: `taller_mecanico` (no `taller_mecanico_test`).
- **Preparación**: se ejecutó `python seed.py` antes de cada archivo `.http`; la contraseña del seed se escribió sólo en REST Client y no se guardó.

| Caso | Comandos / acción | Resultados reales |
|---|---|---|
| C-07 | `python seed.py`; ejecución de `test/c07_roles_vigencia.http` desde REST Client | **200, 200, 200, 200, 200, 403, 200, 200, 422, 422** |
| C-08 | `python seed.py`; ejecución de `test/c08_autoproteccion.http` desde REST Client | **200, 409, 200, 200** |
| C-09 | `python seed.py`; ejecución de `test/c09_cambio_obligatorio.http` desde REST Client | **200, 403, 200, 422, 403, 200, 200, 401, 403** |

Los tres casos coincidieron con los resultados esperados.

## Informe de implementación

Fecha: 2026-10-29. Trabajo realizado con **Codex**. Governance CRÍTICO: Amanda aprobó las 12 decisiones del explore y D1=B, D2=A, D3=A, D4=A; autorizó captura, propose y apply en este alcance sin checkpoints rutinarios. Este informe describe implementación y pruebas automáticas; el espacio anterior queda para la verificación manual de Amanda, todavía sin completar.

### Resultado y alcance

Implementadas las cinco rutas administrativas, requiere_rol con roles vigentes desde base, control único de cambio obligatorio, alta atómica de personal, vigencia/historial/reasignación/revocación, eventos y paginación. Se preservan autenticación CH-05 D6/D7, excepciones DA-15/SU-11 y límites del roadmap.

- Baseline confirmado por ejecución: **349 pruebas pasan**.
- Propose: CLI validó estrictamente el change, 4/4 artefactos completos, **antes de la suite final**.
- Resultado de la suite final: **470 passed in 151.86s (0:02:31), exit 0, sin warnings**, según [pytest-CH-06.txt](./pytest-CH-06.txt).
- Refactor de DTO explícito y tipo AdminDep: **84/84 pruebas de contrato pasan en 62.99 s, sin warnings**.
- Desvíos de alcance/contrato: **ninguno**. D1–D4 son decisiones aprobadas, no desviaciones.
- C-06 completo se conserva para CH-09; C-07/C-08/C-09 se entregan y ejecutan automáticamente sobre ASGI y PostgreSQL _test.
- Sin migraciones, instalaciones, .env, commits ni push. No se ejecutó seed en la base de desarrollo.

### Decisiones y revisión independiente

Se verificó lectura de roles desde columnas en cada petición y ausencia de bypass ADMIN; 401 antes de 403 y control del cambio heredado una sola vez. Los modelos de respuesta filtran secretos; contratos de entrada rechazan extras, CLIENTE administrativo y contraseñas inválidas. Hash previo al UoW y escrituras/evento en un bloque.

La coordinación ADMIN usa pg_advisory_xact_lock con clave fija606005 ligada por parámetro en la misma transacción de alta ADMIN, asignación/reasignación ADMIN o revocación ADMIN. Después de esperar se consulta nuevamente el rol del actor y se toman tiempos frescos; objetivo y respaldo se consultan antes de decidir. La consulta scalar evita reutilizar roles de un identity map. La carrera real conserva un ADMIN y produce200/403 con un solo evento.

AD2 se verifica mediante guardia pura realmente utilizada por el servicio: una petición HTTP legítima de otro ADMIN ya aporta respaldo, por lo que no se inventó un bypass de autorización para alcanzar el branch defensivo. Se mantiene SU-11: cero ADMIN por vencimiento temporal es posible y no genera tarea/evento automático.

Revisión independiente de código y tests (sin ejecutar comandos con efectos): no se identificaron defectos concretos en autenticación/autorización, UoW/hash, roles, coordinación, eventos, composición de rutas ni demostraciones. Las pruebas de concurrencia observan pg_locks no otorgados en conexiones independientes antes de soltar la barrera; no suponen simultaneidad sólo por crear tasks.

### Archivos nuevos

- docs/evidencias/explore-CH-06.md — decisiones confirmadas, pedidos al propose y notas CH07–CH10.
- docs/evidencias/verify-CH-06.md — este informe, sin completar la verificación manual.
- docs/evidencias/CH-06-tdd-rojo.txt y CH-06-tdd-verde.txt — corridas acumuladas por tarea, incluidos fallos.
- openspec/changes/autorizacion-usuarios-roles/.openspec.yaml, proposal.md, design.md, tasks.md.
- openspec/changes/autorizacion-usuarios-roles/specs/{autorizacion,administracion-de-usuarios,eventos-de-seguridad,errores-de-dominio}/spec.md — 13 requisitos y52 escenarios.
- test/c07_roles_vigencia.http, test/c08_autoproteccion.http, test/c09_cambio_obligatorio.http.
- test/pytest/test_autorizacion_errores.py, test_autorizacion.py, test_cambio_obligatorio.py, test_personal_schemas.py, test_personal.py, test_roles.py, test_autoproteccion.py, test_admin_concurrencia.py, test_eventos.py, test_rutas_protegidas.py, test_http_autorizacion.py.

### Archivos modificados

- main.py — grupo protegido y routers administrativos.
- app/core/dependencies.py — roles y control obligatorio.
- app/core/errores.py y rutas.py — autorización403.
- app/modules/usuarios/{schemas,repository,unit_of_work,service,router}.py — contratos, persistencia, transacciones y rutas.
- README.md — contratos CH-06, instrucciones HTTP y C06 diferido.
- No se modifican schema de tabla, migraciones ni requirements.

### TDD Cycle Evidence

Los conteos de cortes son ejecuciones parciales acumulativas y no deben sumarse como pruebas distintas. Cada encabezado de los logs identifica la tarea y la transición. Los casos parametrizados se describen semánticamente en la matriz, no como nodeids literales del runner.

| Tarea | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 1.1 | suite existente | Integración PostgreSQL | 349/349 | No aplica | 349 pasan | Baseline | No aplica |
| 1.2 | test_autorizacion_errores.py + test_rutas.py/test_errores.py | HTTP/core | 349/349 | Import PermisoDenegado inexistente | 20 pasan con regresiones | 2 mensajes | Incluido refactor final |
| 1.3 | test_autorizacion.py | API/DB | 349/349 | Import requiere_rol inexistente | 10 pasan | Roles,revocación,vencimiento,borde | Incluido refactor final |
| 1.4 | test_cambio_obligatorio.py; test_rutas_protegidas.py | API/DB | 349/349 | Control/grupo inexistentes | 5 iniciales;26 matriz/C09 | Grupo sólo identidad y ADMIN mismo segundo | Incluido refactor final |
| 2.1 | test_personal_schemas.py | Unidad contratos | 349/349 | Schemas inexistentes | 20 pasan | Bytes,extras,roles,fechas | Incluido refactor final |
| 2.2 | test_personal.py | API/DB | 349/349 | 12 respuestas404 | 12 pasan | 3roles,errores,rollback | Incluido refactor final |
| 3.1 | test_roles.py | API/DB | 349/349 | 11 respuestas404 | 11 pasan | Fechas,autoría,duplicado404/409 | Incluido refactor final |
| 3.2 | test_roles.py | API/DB | 349/349 | Reasignación409 incorrecta | 13 roles incluyendo2 nuevos | Reasignación y rollback | Incluido refactor final |
| 3.3 | test_roles.py | API/DB | 349/349 | 3 GET405 | 3 pasan | Mixto,vacío,igualdad | Incluido refactor final |
| 3.4 | test_roles.py | API/DB | 349/349 | 6 DELETE404 | 6 pasan | Vigente,vencida,ausencia,rollback | Incluido refactor final |
| 4.1 | test_autoproteccion.py | Unidad/API/DB | 349/349 | Guardia inexistente | 5 pasan | Autorrevo,respaldo,cero,vencimiento | Incluido refactor final |
| 4.2 | test_admin_concurrencia.py | API/DB concurrente | 349/349 | Import y espera real ausentes | 6 pasan | 4operaciones esperan;cruce;rollback | Incluido refactor final |
| 5.1 | test_eventos.py | API/DB | 349/349 | 10 /eventos404 | 10 pasan | Paginación,auditoría,compatibilidad | Incluido refactor final |
| 5.2 | test_http_autorizacion.py + tres .http | API/DB documentación ejecutada | 349/349 | No aplica: archivos de demostración | 3 pasan | C07,C08,C09 literales | Sin código productivo adicional |
| 6.1 | suite completa y OpenSpec estricto | Integración global | 349/349 | Evidencias previas conservadas | 470 pasan en 151.86 s, exit 0, sin warnings | 52 escenarios mapeados | Contratos84/84 sin warnings; OpenSpec estricto pasó antes de la suite final |

### Corridas fallidas preservadas

Los RED por imports/símbolos inexistentes, rutas404/405 y reasignación que aún daba409 se conservaron; acreditan que el test se escribió antes de implementar su comportamiento. La coordinación tiene además RED conductual: sin protocolo de bloqueo las solicitudes no aparecían esperando en pg_locks y la comprobación agotaba el timeout; después la espera real queda observada.

También se conservaron fallos del arnés durante triangulación: ids del seed mal usados (id2 es admin2, no recepción; se corrigieron a3 recepción y4 mecánico), y CookieConflict por combinar cookie sin dominio con cookie renovada test.local (se corrigió leyendo la cookie de la respuesta y controlando el transporte explícito). No fueron fallos preexistentes ni motivos para alterar reglas de negocio.

Warnings enum/str en model_dump motivaron proyección DTO explícita; AdminDep recibió tipo concreto. La regresión posterior pasó 84/84 en 62.99 s sin warnings. No se eliminaron pruebas ni salidas fallidas.

### Matriz de los 52 escenarios

Todos los paths de tests de esta tabla son relativos a test/pytest/. Las etiquetas entre corchetes describen parametrizaciones de forma legible.

| Escenario | Prueba concreta |
|---|---|
| AU1 | `test_rutas_protegidas.py::test_au1_au6_au7_au8_cinco_rutas[admin]`; `test_autorizacion.py::test_au1_admin_desde_base` |
| AU2 | `test_autorizacion.py::test_au2_revocado_mismo_token`; `test_http_autorizacion.py::test_http_c07_c08_c09[c07]` |
| AU3 | `test_autorizacion.py::test_au3_asignacion_tras_login` |
| AU4 | `test_autorizacion.py::test_au4_vencimiento_y_igualdad[-1,0]` |
| AU5 | `test_autorizacion.py::test_au5_roles_alternativos_sin_bypass[RECEPCION,MECANICO,ADMIN]` |
| AU6 | `test_rutas_protegidas.py::test_au1_au6_au7_au8_cinco_rutas[anonimo,bearer]`; `test_autorizacion.py::test_au6_401_antes_rol` |
| AU7 | `test_rutas_protegidas.py::test_au1_au6_au7_au8_cinco_rutas[sinadmin]` |
| AU8 | `test_rutas_protegidas.py::test_au1_au6_au7_au8_cinco_rutas[pendiente]`; `test_cambio_obligatorio.py::test_au8_grupo_solo_identidad`; `test_au8_control_declarado_una_vez` |
| AU9 | `test_rutas_protegidas.py::test_au9_au10_au11_admin_provisional_mismo_segundo`; `test_cambio_obligatorio.py::test_au9_au10_auth_y_salud_no_bloqueadas` |
| AU10 | `test_rutas_protegidas.py::test_au9_au10_au11_admin_provisional_mismo_segundo`; `test_cambio_obligatorio.py::test_au9_au10_auth_y_salud_no_bloqueadas` |
| AU11 | `test_rutas_protegidas.py::test_au9_au10_au11_admin_provisional_mismo_segundo`; `test_cambio_obligatorio.py::test_au11_cookie_nueva_desbloquea_identidad` |
| AU12 | `test_http_autorizacion.py::test_http_c07_c08_c09[c09_cambio_obligatorio.http]` |
| PE1 | `test_personal.py::test_pe1_alta_tres_filas_respuesta_sin_secretos[ADMIN,RECEPCION,MECANICO]` |
| PE2 | `test_personal.py::test_pe2_correo_duplicado_sin_filas` |
| PE3 | `test_personal.py::test_pe3_alta_rollback_del_evento` |
| PE4 | `test_personal_schemas.py::test_pe4_roles_no_personal_422`; `test_personal.py::test_pe4_pe5_pe6_pe7_422_sin_bcrypt`; `test_roles.py::test_ro2_pe4_pe5_asignacion_422_sin_filas` |
| PE5 | `test_personal_schemas.py::test_pe5_extras_rechazados`; `test_personal.py::test_pe4_pe5_pe6_pe7_422_sin_bcrypt` |
| PE6 | `test_personal_schemas.py::test_pe6_72_bytes_aceptados`; `test_pe6_pe7_password_invalida`; `test_personal.py::test_pe4_pe5_pe6_pe7_422_sin_bcrypt` |
| PE7 | `test_personal_schemas.py::test_pe6_pe7_password_invalida`; `test_personal.py::test_pe4_pe5_pe6_pe7_422_sin_bcrypt` |
| RO1 | `test_roles.py::test_ro1_asigna_con_autoria_y_evento[omitida,null,fecha]`; `test_personal_schemas.py::test_ro1_schema_futuro_omitido_null` |
| RO2 | `test_personal_schemas.py::test_ro2_fecha_invalida[igual,pasada,sin_zona]`; `test_roles.py::test_ro2_pe4_pe5_asignacion_422_sin_filas` |
| RO3 | `test_roles.py::test_ro3_asignar_usuario_inexistente`; `test_ro3_historial_usuario_inexistente`; `test_ro3_revocar_usuario_inexistente` |
| RO4 | `test_roles.py::test_ro4_duplicado_vigente_409` |
| RO5 | `test_roles.py::test_ro5_ro7_reasigna_vencido_o_revierte[False]` |
| RO6 | `test_roles.py::test_ro6_asigna_tras_revocacion` |
| RO7 | `test_roles.py::test_ro5_ro7_reasigna_vencido_o_revierte[True]` |
| RV1 | `test_roles.py::test_rv1_rv3_rv4_revoca_con_historia_o_rollback[False-False]` |
| RV2 | `test_roles.py::test_rv2_ausencia_asignacion_abierta[False,True]` |
| RV3 | `test_roles.py::test_rv1_rv3_rv4_revoca_con_historia_o_rollback[True-False]` |
| RV4 | `test_roles.py::test_rv1_rv3_rv4_revoca_con_historia_o_rollback[False-True]` |
| HI1 | `test_roles.py::test_hi1_historial_mixto_con_cliente_y_orden` |
| HI2 | `test_roles.py::test_hi2_historial_vacio_y_igualdad` |
| AD1 | `test_autoproteccion.py::test_ad1_autorrevo_con_respaldo_409`; `test_ad1_ad2_regla_defensiva[actor=objetivo]` |
| AD2 | `test_autoproteccion.py::test_ad1_ad2_regla_defensiva[actor=2,objetivo=1,respaldo=0]` |
| AD3 | `test_autoproteccion.py::test_ad3_revocar_otro_admin_con_respaldo` |
| AD4 | `test_autoproteccion.py::test_ad4_vencimiento_puede_dejar_cero_sin_evento` |
| CO1 | `test_admin_concurrencia.py::test_co1_dos_admins_revocan_cruzado` |
| CO2 | `test_admin_concurrencia.py::test_co2_co3_actor_pierde_admin_esperando[revocar]` |
| CO3 | `test_admin_concurrencia.py::test_co2_co3_actor_pierde_admin_esperando[alta,asignar,reasignar]` |
| CO4 | `test_admin_concurrencia.py::test_co4_rollback_libera_lock_y_segundo_completa` |
| EV1 | `test_personal.py::test_pe1_alta_tres_filas_respuesta_sin_secretos`; `test_roles.py::test_ro1_asigna_con_autoria_y_evento`; `test_rv1_rv3_rv4_revoca_con_historia_o_rollback` |
| EV2 | `test_roles.py::test_ro5_ro7_reasigna_vencido_o_revierte[False]` |
| EV3 | `test_rutas_protegidas.py::test_au1_au6_au7_au8_cinco_rutas[denegados]`; `snapshots en PE2,PE3,RO2,RO4,RO7,RV2,RV4 (filas anteriores en esta tabla)` |
| EV4 | `test_eventos.py::test_ev4_preserva_eventos_ch05` |
| EV5 | `test_eventos.py::test_ev5_lecturas_login_logout_no_agregan_eventos` |
| EV6 | `test_eventos.py::test_ev6_paginas_orden_estable_y_formato` |
| EV7 | `test_eventos.py::test_ev7_eventos_vacios` |
| EV8 | `test_eventos.py::test_ev8_parametros_invalidos[page0,size0,size101,page2]` |
| EV9 | `test_eventos.py::test_ev9_tamanos_limite[1,100]` |
| E403a | `test_autorizacion_errores.py::test_e403a_e403b_dependencia_traduce_permiso[sin_rol]` |
| E403b | `test_autorizacion_errores.py::test_e403a_e403b_dependencia_traduce_permiso[cambio_pendiente]` |
| E403c | `test_rutas.py y test_errores.py (regresiones de rutas, mapa completo y códigos)`; `test_autorizacion_errores.py` |

### Archivos HTTP ejecutables

- C07:200,200,200,200,200,403,200,200,422,422; dos sesiones explícitas aisladas, misma cookie afectada, /yo divergente e historial.
- C08:200,409,200,200; autorevo rechazado y permiso intacto.
- C09:200,403,200,422,403,200,200,401,403; nueva cookie válida en /yo y anterior rechazada. Nuevo es MECANICO: /eventos sigue403 por rol después del cambio.
- El test ADMIN provisional con reloj controlado acredita nueva cookie200 en grupo protegido y anterior401 dentro del mismo segundo.
- La ejecución automática no sustituye el espacio de verificación manual anterior ni afirma capturas REST Client.

### Estado final de implementación

Las 15/15 tareas del apply están completas (`remaining=0`, `all_done`). La validación estricta de OpenSpec pasó antes de la suite final. La suite completa terminó con **470 passed in 151.86s (0:02:31), exit 0, sin warnings**; su salida queda enlazada en [pytest-CH-06.txt](./pytest-CH-06.txt). Amanda completa la Verificación manual cuando realice sus pruebas. Archivar, sincronizar specs principales, marcar `CHANGES.md` o commitear no forma parte de este informe.
