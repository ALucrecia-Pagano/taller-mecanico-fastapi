# CH-09 — Informe de implementación

Fecha: 2026-10-30. Trabajado con Codex. Change `ordenes-alta-consulta`, schema `spec-driven`.

## Resultado y alcance

Cinco operaciones implementadas dentro de `rutas_protegidas`: POST/GET `/ordenes`, GET
`/ordenes/{id}`, `/mis-ordenes` y `/estados-orden`. Alta atómica PENDIENTE con ítems y primera
línea de historial; precios copiados, total Decimal y ningún movimiento/reserva de stock.
Detalle con autorización de personal vigente o dueño por FK, precio histórico y carga explícita;
listados paginados con filtro estado y propias sin exigir CLIENTE. Catálogo sólo lectura.

La tabla de endpoints de la consigna p.16 **sólo incluye 201,409,422 en POST /ordenes**:
inexistente y dado de baja →409; GET inexistente →404. Verificación anotada en el explore.
No se implementaron transiciones CH-10. No se ejecutaron git add/commit/push, instalaciones
ni accesos a la base de desarrollo; no se abrió, mostró o modificó `.env`.

## Verificación automática

- Baseline anterior a producción: **505 passed in 138.10s**. Primer intento sandbox no pudo
  ejecutar Python por permisos; quedó conservado, y el reintento elevado pasó.
- **140 tests nuevos**, incluidos parametrizados, en ocho archivos `test_ordenes_*.py`.
- Suite completa `pytest -v`: **645 passed in 249.35s (0:04:09)**, sin fallos ni warnings.
- Evidencia completa: `pytest-CH-09.txt`; TDD acumulado en `CH-09-tdd-rojo.txt` y
  `CH-09-tdd-verde.txt` con encabezados, comandos y todas las corridas fallidas.
- Los cuatro `.http` se ejecutan literalmente por ASGI con PostgreSQL de prueba mediante
  `test_http_ch09_literales_sobre_asgi`; esto no acredita ejecución manual de Amanda.
- SQL real C-15: `C-15-consultas.txt`, sesiones nuevas por GET, mismo ADMIN y login/altas
  fuera de la medición. **5 SELECT HTTP por detalle con 2 y 4 ítems: 3 dominio + 2 auth/roles**.
  Se guardan sentencias sin valores de parámetros, resultados ni cookies.
- Validación `openspec validate ordenes-alta-consulta --strict`: **válida** tras propose y
  al cierre del apply. Sin migraciones nuevas ni cambios a seed.py.
- Limpieza final comprobada: **13 tablas del dominio, todas con 0 filas**, sólo en
  `taller_mecanico_test`. Se conserva `alembic_version` como metadato de esquema; FK del
  historial a usuario restaurada `NOT DEFERRABLE`. Evidencia al final del log verde.

## Escenario → test

Los nodos se encuentran bajo `test/pytest/`; cada familia parametrizada cubre las variantes
indicadas. **Escenarios SIN TEST: ninguno (0/22).**

| Escenario | Cobertura | Archivo y test |
|---|---|---|
| E01 | C-10 literal, dinero, fechas, actor, persistencia y stock intacto | `test_ordenes_alta.py::test_alta_c10_ejemplo_atomico_y_dinero` |
| E02 | ADMIN crea uno/cuatro ítems sin ser dueño | `test_ordenes_alta.py::test_alta_admin_uno_y_cuatro_items_ajenos` |
| E03 | Vacío, cantidades inválidas, repetidos y requeridos; HTTP422 sin filas | `test_ordenes_schemas.py::test_entrada_orden_rechaza_items_invalidos`, `test_entrada_orden_exige_campos`; `test_ordenes_integracion.py::test_http_entrada_invalida_422_sin_escrituras` |
| E04 | Extras raíz/ítem y campos del servidor rechazados | `test_ordenes_schemas.py::test_entrada_orden_rechaza_campos_controlados`, `test_entrada_item_rechaza_extras`; `test_ordenes_integracion.py::test_http_entrada_invalida_422_sin_escrituras` |
| E05 | Vehículo/repuesto inexistente409, sin cambios | `test_ordenes_integridad.py::test_alta_referencia_inexistente_o_baja_409_sin_cambios` (baja=False); `test_ordenes_integracion.py::test_ids_fuera_integer_son_referencia_inexistente_409` |
| E06 | Baja409 y reutilización de patente/código no sustituye id | `test_ordenes_integridad.py::test_alta_referencia_inexistente_o_baja_409_sin_cambios` (baja=True) |
| E07 | Catálogo vacío/parcial sin reparación | `test_ordenes_integridad.py::test_alta_catalogo_vacio_o_sin_pendiente_409` |
| E08 | Centavos, máximo NUMERIC aceptado/exceso409, rango físico INTEGER | `test_ordenes_dinero.py::test_total_maximo_numeric_y_exceso_409`, `test_total_centavos_exacto`, `test_cantidad_fuera_integer_422_sin_driver_error`; `test_ordenes_schemas.py::test_salida_item_serializa_dinero_dos_decimales` |
| E09 | Alta permite superar stock/cero sin movimientos | `test_ordenes_alta.py::test_alta_no_exige_stock_ni_lo_mueve` |
| E10 | FK real falla en flush/commit, rollback completo y sesión usable | `test_ordenes_integridad.py::test_alta_fallo_historial_flush_o_commit_revierte_todo` |
| E11 | Precio anterior congelado y nueva alta con precio nuevo | `test_ordenes_integridad.py::test_alta_precio_copiado_persiste_tras_patch`; `test_ordenes_detalle.py::test_detalle_conserva_repuesto_baja_y_precio_copiado` |
| E12 | Cinco rutas sin cookie/Bearer401 y cambio pendiente403 | `test_ordenes_integracion.py::test_cinco_rutas_sesion_bearer_y_cambio` |
| E13 | Roles permitidos/prohibidos, revocados/vencidos sin privilegios JWT | `test_ordenes_integracion.py::test_personal_rol_insuficiente_403`, `test_roles_actuales_no_token_en_alta_listado_detalle`; `test_ordenes_listados.py::test_listado_personal_todas_sin_filtrar_mecanico`; altas E01/E02 |
| E14 | Dueño200, ajeno403, personal200, inexistente404, sin ficha403 | `test_ordenes_detalle.py::test_detalle_personal_dueno_ajeno_e_inexistente`, `test_detalle_sin_ficha_ni_rol_personal_403`; `test_ordenes_integracion.py::test_detalle_id_fuera_integer_404` |
| E15 | Propias, vacío sin ficha y sin exigir CLIENTE | `test_ordenes_listados.py::test_mis_ordenes_solo_dueno_y_sin_ficha_vacio`, `test_mis_ordenes_no_exige_cliente_y_personal_no_amplia` |
| E16 | Defaults, ventanas, límites, inválidos, vacío y página inexistente | `test_ordenes_listados.py::test_paginacion_invalida_422`, `test_paginas_primera_ultima_y_size100`, `test_listados_vacios_y_bajas_historicas`, `test_listado_personal_todas_sin_filtrar_mecanico` |
| E17 | MECANICO ve todas; filtros/count coherentes y enum422 | `test_ordenes_listados.py::test_listado_personal_todas_sin_filtrar_mecanico`, `test_filtro_estado_y_count_identicos`, `test_filtro_estado_desconocido_422` |
| E18 | Catálogo ordenado/finales, autenticación y vacío[] | `test_ordenes_catalogo.py::test_catalogo_estados_sembrado_orden_y_finales`, `test_catalogo_autenticacion_y_cambio`, `test_catalogo_vacio_no_se_repara` |
| E19 | SQL real con 2/4 ítems, sesiones nuevas, costo fijo | `test_ordenes_detalle.py::test_c15_sql_real_dos_y_cuatro_items_consultas_fijas` |
| E20 | Historial con igual cuando desempata por id sin exponerlo | `test_ordenes_detalle.py::test_detalle_historial_empate_y_formato` |
| E21 | Repuestos/vehículos de baja conservados en detalle/listados/propias | `test_ordenes_detalle.py::test_detalle_conserva_repuesto_baja_y_precio_copiado`, `test_detalle_conserva_vehiculo_finalizado_dado_baja`; `test_ordenes_listados.py::test_listados_vacios_y_bajas_historicas`; altas E06 |
| E22 | Cinco operaciones, traducción, sin CRUD extra e id no entero422 | `test_ordenes_integracion.py::test_superficie_cinco_operaciones_sin_crud_extra`; `test_ordenes_catalogo.py::test_catalogo_solo_lectura_y_router_traductor`; HTTP/formato `test_http_ch09_literales_sobre_asgi`, `test_http_formato_password_login_separadores_y_esperadas` |

## TDD Cycle Evidence

Safety net de producción previo: 505/505. Las pruebas de regresión de cada tarea se
acompañan por las familias previas pertinentes; el cierre ejecuta la suite completa.
Seams HTTP para contratos/permisos y repositorio/servicio con PostgreSQL real para SQL/atomicidad.

| Tarea | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 1.1 | `test_ordenes_schemas.py` | Unit | 505/505 | Import ausente;4 fallos de validación;2 salida | 1→19→21 passed | Requeridos/extras/repetidos/cantidades/dinero | Contratos separados, verde21 |
| 2.1 | `test_ordenes_catalogo.py` | HTTP+DB | 505/505 + schemas21 | 6 fallos ruta/repo ausentes | 27 passed con schemas | Seed/vacío/auth/cambio/sólo lectura | Sin CRUD heredado, verde27 |
| 3.1 | `test_ordenes_alta.py` | HTTP+DB | 505/505 + catálogo | 5 fallos404 | 5 passed | Uno/cuatro ítems, stockcero, ejemplo | Serializer compartido, verde5 |
| 3.2 | `test_ordenes_integridad.py` | HTTP/service+DB | Alta5 | 8 fallos y1pass | 14 passed con alta | Inexistentes/bajas/reuso, catálogo parcial, flush/commit | Mapa constraints, verde14 |
| 3.3 | `test_ordenes_dinero.py` | HTTP+DB | Altas/integridad14 | 3 fallos y3pass | 27 passed con schemas | Centavos, máximo/exceso y INTEGER | Límite físico sin catch genérico, verde27 |
| 4.1 | `test_ordenes_detalle.py` | HTTP+DB/SQL | Tareas previas verdes | 15 fallos404 | 15 passed | Dueño/personal/ajeno/bajas/historial/SQL | Precarga declarada, verde15 |
| 5.1 | `test_ordenes_listados.py` | HTTP+DB | Detalle15 | 31 fallos rutas ausentes | 31 passed | Estado/propietario/páginas/vacío | Filtro único count/filas, verde31 |
| 6.1 | `test_ordenes_integracion.py` | HTTP+DB/artifacts | Familias anteriores verdes | 11 fallos y21pass | 47 passed | Sesión/roles, IDs,11entradas inválidas,4HTTP literales | Guards físicos y docs, verde47 |

Corrida fallida adicional conservada: primer GREEN2.1 tuvo 1 fallo/26pasados porque el test
recorría `app.routes` plano. FastAPI0.162 mantiene routers incluidos como envoltorios; se usó
el recorrido `rutas_de` ya existente. No fue defecto de producción ni se borró evidencia.

## No especificado en la consigna y desvíos

Se mantienen las decisiones aprobadas y su autoría `[Agente]` del explore: resumen/orden de
listados, orden de ítems/historial, mensajes, catálogo parcial409/GETvacío[], precarga concreta,
DTO dentro del UoW, lectura histórica y ausencia de locking adicional. No se convirtieron en DA.

- **Precisión del fallback**: una constraint desconocida conserva el mensaje transversal
  `La operación choca con datos existentes` de la spec durable `errores-de-dominio`, en vez del
  genérico `No se pudo crear la orden` propuesto en explore. Las constraints conocidas de alta
  sí tienen mensajes del módulo. Mantiene RN-18 y evita modificar core por esta entrega.
- **Rango físico** `[Agente]`: cantidad >2147483647 →422, no es límite comercial arbitrario.
  IDs fuera de INTEGER no pueden existir y se resuelven como inexistentes antes de enlazarlos:
  POST409 y GET404, sin convertir errores de driver genéricos en respuestas engañosas.
- **C-15**: evidencia automática de sentencias reales durante peticiones ASGI, no captura de una
  sesión manual de uvicorn. README y `.http` incluyen el procedimiento manual SQL_ECHO pendiente.
- **Rollback**: usa actor inexistente para forzar una FK real después de escribir orden/ítems;
  variante diferida prueba commit. El ajuste temporal de esa FK ocurre sólo en `_test` y se
  restaura en `finally`; no cambia migraciones ni producción.
- No se identificaron contradicciones con la consigna. Se respetan nombres de change, alcance
  y las dependencias. No se archivó CH-09 ni se marcó CHANGES.md como verificado manualmente.

## Verificación manual

Fecha: **2026-10-30**. Responsable: **Amanda Pagano**. Registro trabajado con **Codex**.

Amanda informó la ejecución manual de `python seed.py` contra `taller_mecanico` y de las
peticiones mediante REST Client. C-06 coincidió con los códigos esperados indicados abajo.
La contraseña se ingresó únicamente en el editor, sin guardar. El agente registra lo informado:
no ejecutó el seed, REST Client ni accedió a la base de desarrollo durante este cierre.

| Archivo | Códigos esperados en orden | Fecha | Resultado / observaciones |
|---|---|---|---|
| `test/c06_401_403_propio.http` | 401;200 login;403 general;200 propia;403 ajena;200 propias | 2026-10-30 | Amanda Pagano: coincide con lo esperado, según confirmación manual por REST Client. |
| `test/c10_alta_orden.http` | 200 login;201 alta total68000.00;409 inexistente | 2026-10-30 | Cubierto por tests automáticos; no se registra una ejecución manual individual adicional. |
| `test/c15_detalle_sin_n1.http` | 200 login;201 alta4ítems;200 detalle2;200 detalle4; SQL igual | 2026-10-30 | Cubierto por tests automáticos y SQL real en `C-15-consultas.txt`; no se atribuye captura SQL manual. |
| `test/c17_catalogo_estados.http` | 401 sin sesión;200 login;200 catálogo;200 general;200 filtro;422 XYZ | 2026-10-30 | Cubierto por tests automáticos; no se registra una ejecución manual individual adicional. |

Comandos y acciones reportados: `python seed.py`; envío de las peticiones C-06 desde REST
Client. Amanda indicó que el resto de los casos queda cubierto por los tests automáticos.
La confirmación recibida no contiene una secuencia individual de C-10; no se inventan salidas
ni verificaciones manuales adicionales. Evidencia automática previa: **645 passed**, E01–E22
sin escenarios SIN TEST; no se repitieron tests en este cierre.
