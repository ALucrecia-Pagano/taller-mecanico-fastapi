# Verify de CH-02 `core-repositorios-uow`

- **Fecha**: 2026-10-26
- **Verificó**: Amanda Pagano (verificación manual, antes del archive)
- **Change**: `openspec/changes/core-repositorios-uow/` (49/49 tareas; `openspec validate --strict` válido)
- **Entorno**: Windows 11, Python 3.13.6, PostgreSQL 17.11. FastAPI 0.162.0, SQLAlchemy 2.1.6, SQLModel 0.0.48, asyncpg 0.32.0, Pydantic 2.14.1, pytest 9.1.1, pytest-asyncio 1.4.0. La suite corre contra `taller_mecanico_test`; la base `taller_mecanico` y el `.env` no se tocaron.

## Comandos y resultado

| # | Comando | Resultado |
|---|---|---|
| 1 | `pytest -v` | **94 passed**: 40 de CH-01 y 54 de CH-02, contra `taller_mecanico_test` |
| 2 | `\dt prueba_*` en `psql` sobre `taller_mecanico_test`, después de la corrida | Ninguna tabla: la fixture de sesión las borra al terminar |

CH-02 no expone endpoints, así que no hay `.http` ni humo con el servidor levantado.

Evidencia complementaria generada durante el apply:

- `docs/evidencias/pytest-CH-02.txt`: salida completa de `pytest -v` (94 passed en 5,24 s, sin fallos ni errores).
- `docs/evidencias/CH-02-tdd-rojo.txt` y `CH-02-tdd-verde.txt`: cada RED y cada GREEN, con un encabezado por grupo y tarea. Al final de cada archivo hay una sección **«Corridas eliminadas»** que documenta las dos corridas que se borraron durante el apply (ver Desvíos, 4).
- Red de seguridad (tarea 1.1): antes de tocar nada, la suite de CH-01 dio 40 passed. Después de cambiar el router de salud (tarea 9.5), la suite completa de CH-01 volvió a dar 40 passed.
- Punto de control de governance (tarea 11.1, con `grep`):
  - ningún `.commit(` en repositorios;
  - ningún `create_all` en el código (sólo aparece en dos docstrings que dicen «nunca `create_all`»);
  - ningún servicio construye un UoW (todavía no hay servicios);
  - `UnitOfWork` sin `close()`;
  - `errores.py` sin imports de FastAPI, y `paginacion.py` importa sólo `Query`;
  - todas las dependencias y los handlers nuevos son `async def`.

## Evidencia TDD por grupo

| Grupo | Archivo de test | Capa | RED (por qué falló) | GREEN | Triangulación | Refactor |
|---|---|---|---|---|---|---|
| 1. Red de seguridad | Suite de CH-01 | — | — | 40/40 | — | — |
| 2. Arnés `prueba_*` | `test_tablas_de_prueba.py` | Integración (base `_test`) | No existía `tablas_de_prueba.py`; después no existían los modelos de prueba | 3/3 | F2 (tablas ya existentes, con una fila de una corrida cortada) | Fixtures de sesión en `conftest.py` |
| 3. Paginación pura | `test_paginacion.py` | Unidad | No existían `paginacion.py` ni `errores.py`; después P3 falló (`hay 0` páginas con cero resultados) | 4/4 | P3, P4 | `Ventana` como `NamedTuple` |
| 4. `BaseRepository` | `test_repositorio.py` | Integración (base `_test`) | No existía `repository.py`; después faltaban `get_by_id`, `get_all`, `count`, `delete` y luego `update` | 11/11 | R3-R10; R10 con dos filtros (pasó sin código nuevo) | Sin cambios |
| 5. `SoftDeleteRepository` | `test_repositorio.py` | Integración (base `_test`) | No existía `SoftDeleteRepository`; después faltaba `get_by_id_including_deleted`; después B3 pisaba la fecha original | 16/16 | B2, B3, B5 (B5 pasó sin código nuevo: el filtro se hereda por diseño) | Sin cambios |
| 6. `UnitOfWork` | `test_unit_of_work.py` | Integración (base `_test`) | No existía `unit_of_work.py`; después U6 no lanzaba `RuntimeError` | 9/9 | U2, U4, U5, U7, U9, U10 (pasaron sin código nuevo) | Sin cambios |
| 7. Traducción de `IntegrityError` | `test_errores.py`, `test_unit_of_work.py` | Integración (base `_test`) | E1: salía el `IntegrityError` crudo, con texto de la base; E3: `KeyError` sin mapa; E4/E5: sin log; U8: `IntegrityError` crudo en el commit | 16/16 | E2, E3, E6, E4, E5, U8 | `__aexit__` con un solo punto de rollback y traducción; `NoEncontrado` |
| 8. Paginación con FastAPI | `test_paginacion.py` | Unidad + HTTP + integración | No existían `ParametrosDePagina`, `parametros_de_pagina` ni `Pagina` | 11/11 | P5 (×4 inválidos), P6, P7 | Sin cambios |
| 9. Clase de ruta y salud | `test_rutas.py` + suite de CH-01 | HTTP | No existía `rutas.py`; después T4 falló por `/health/live` y `/health/ready` | 7/7 + 40/40 | T2, T3, T4 con app falsa (pasaron sin código nuevo) | Sin cambios |
| 10. Estático y documentación | `test_repositorio.py` (R11) | Estático | — (verifica una propiedad que ya se cumplía) | 1/1 | — | Aserción anti-vacío simplificada |
| 11. Verificación final | Suite completa | — | — | 94/94 | — | — |

## Escenario de la spec → test

| Spec | Escenario | Test |
|---|---|---|
| repositorios | R1 El alta deja el id y los defaults cargados | `test_repositorio.py::test_r1_el_alta_deja_el_id_y_los_defaults_de_la_base_cargados` |
| repositorios | R2 El alta no se confirma sola | `test_repositorio.py::test_r2_el_alta_no_se_confirma_sola` |
| repositorios | R3 Id existente e inexistente | `test_repositorio.py::test_r3_lectura_por_id_existente_e_inexistente` |
| repositorios | R4 Ventana en orden y fuera de rango | `test_repositorio.py::test_r4_ventana_en_orden_y_ventana_fuera_de_rango` |
| repositorios | R5 Conteo con filas y sin filas | `test_repositorio.py::test_r5_conteo_con_filas_y_sin_filas` |
| repositorios | R6 Modifica sólo lo enviado | `test_repositorio.py::test_r6_modifica_solo_lo_enviado` |
| repositorios | R7 Clave desconocida rechazada | `test_repositorio.py::test_r7_clave_desconocida_rechazada` |
| repositorios | R8 El id no se modifica | `test_repositorio.py::test_r8_el_id_no_se_modifica` |
| repositorios | R9 Baja física | `test_repositorio.py::test_r9_baja_fisica` |
| repositorios | R10 Total e items con el mismo filtro | `test_repositorio.py::test_r10_total_e_items_con_el_mismo_filtro[5, 15]` |
| repositorios | R11 Sin commit en los repositorios | `test_repositorio.py::test_r11_ningun_repositorio_confirma` |
| repositorios | B1 La fila dada de baja deja de verse | `test_repositorio.py::test_b1_la_fila_dada_de_baja_deja_de_verse` |
| repositorios | B2 Recuperar una fila dada de baja | `test_repositorio.py::test_b2_recuperar_una_fila_dada_de_baja` |
| repositorios | B3 Segunda baja | `test_repositorio.py::test_b3_una_segunda_baja_conserva_la_fecha_original` |
| repositorios | B4 Modelo sin `borrado_en` | `test_repositorio.py::test_b4_modelo_sin_borrado_en` |
| repositorios | B5 Los métodos con nombre heredan el filtro | `test_repositorio.py::test_b5_los_metodos_con_nombre_heredan_el_filtro` |
| unidad-de-trabajo | U1 Bloque exitoso | `test_unit_of_work.py::test_u1_bloque_exitoso` |
| unidad-de-trabajo | U2 Error de la base | `test_unit_of_work.py::test_u2_error_de_la_base` |
| unidad-de-trabajo | U3 Excepción de dominio después de escribir | `test_unit_of_work.py::test_u3_excepcion_de_dominio_despues_de_escribir` |
| unidad-de-trabajo | U4 Excepción cualquiera | `test_unit_of_work.py::test_u4_excepcion_cualquiera_sale_sin_cambios` |
| unidad-de-trabajo | U5 Sesión usable después del bloque | `test_unit_of_work.py::test_u5_la_sesion_sigue_usable_despues_del_bloque` |
| unidad-de-trabajo | U6 Bloque dentro de otro | `test_unit_of_work.py::test_u6_bloque_dentro_de_otro` |
| unidad-de-trabajo | U7 Bloques consecutivos | `test_unit_of_work.py::test_u7_bloques_consecutivos` |
| unidad-de-trabajo | U8 La restricción salta en la confirmación | `test_unit_of_work.py::test_u8_la_restriccion_salta_en_la_confirmacion` |
| unidad-de-trabajo | U9 Escrituras en dos tablas | `test_unit_of_work.py::test_u9_escrituras_en_dos_tablas` |
| unidad-de-trabajo | U10 La sesión propia sobrevive al rollback | `test_unit_of_work.py::test_u10_la_sesion_propia_sobrevive_al_rollback_de_la_peticion` |
| paginacion | P1 Ventana de cada página | `test_paginacion.py::test_p1_ventana_de_cada_pagina` |
| paginacion | P2 Más allá de la última | `test_paginacion.py::test_p2_mas_alla_de_la_ultima` |
| paginacion | P3 Listado sin resultados | `test_paginacion.py::test_p3_cero_resultados_es_una_pagina_vacia` |
| paginacion | P4 Bordes del redondeo | `test_paginacion.py::test_p4_bordes_del_redondeo` |
| paginacion | P5 Defaults, límites y valores inválidos | `test_paginacion.py::test_p5_defaults_y_limites`, `test_p5_valores_invalidos[size=500, size=0, page=0, page=abc]` |
| paginacion | P6 Forma del envoltorio | `test_paginacion.py::test_p6_forma_del_envoltorio` |
| paginacion | P7 De punta a punta con la base | `test_paginacion.py::test_p7_total_con_los_mismos_filtros` |
| errores-de-dominio | E1 UNIQUE mapeado | `test_errores.py::test_e1_unique_mapeado` |
| errores-de-dominio | E2 CHECK mapeado | `test_errores.py::test_e2_check_mapeado` |
| errores-de-dominio | E3 Restricción sin mapear | `test_errores.py::test_e3_restriccion_sin_mapear` |
| errores-de-dominio | E4 NOT NULL | `test_errores.py::test_e4_not_null` |
| errores-de-dominio | E5 Log con el detalle, mensaje sin el detalle | `test_errores.py::test_e5_log_con_el_detalle_mensaje_sin_el_detalle` |
| errores-de-dominio | E6 FK mapeada al borrar un referenciado | `test_errores.py::test_e6_fk_mapeada_al_borrar_un_referenciado` |
| errores-de-dominio | T1 Los tres códigos | `test_rutas.py::test_t1_los_tres_codigos[404, 409, 422]` |
| errores-de-dominio | T2 Error lanzado desde una dependencia | `test_rutas.py::test_t2_error_lanzado_desde_una_dependencia` |
| errores-de-dominio | T3 Excepción que no es de dominio | `test_rutas.py::test_t3_excepcion_que_no_es_de_dominio` |
| errores-de-dominio | T4 Recorrido de las rutas de la aplicación | `test_rutas.py::test_t4_toda_ruta_de_la_aplicacion_traduce_errores_de_dominio`, `test_t4_el_recorrido_detecta_una_ruta_sin_traduccion` |
| errores-de-dominio | T5 Salud sin cambios de comportamiento | La suite de CH-01 (40 passed después de la tarea 9.5) |
| suite-de-pruebas | F1 La guarda va antes que el DDL | `test_tablas_de_prueba.py::test_f1_la_guarda_va_antes_que_el_ddl` |
| suite-de-pruebas | F2 Tablas de una corrida interrumpida | `test_tablas_de_prueba.py::test_f2_tablas_que_quedaron_de_una_corrida_interrumpida` |

Los 46 escenarios tienen al menos un test en verde. Hay además un test de apoyo para V4: `test_tablas_de_prueba.py::test_los_modelos_de_prueba_no_tocan_la_metadata_de_alembic`.

**T4 no pasa en vacío:**
- tiene una triangulación con una app falsa que incluye una ruta sin `route_class` dentro de un grupo anidado, y la detecta;
- después del apply se verificó con una sonda temporal que, si `original_router` deja de existir en los envoltorios de `main.app`, T4 falla con `AttributeError: '_IncludedRouter' object has no attribute 'path'`. Si el envoltorio tuviera `path`, igual fallaría la aserción de `/health/live`.

## V1 a V4 (contra las versiones instaladas)

| # | Pregunta | Resultado |
|---|---|---|
| V1 | ¿Por qué atributo se llega al nombre de la restricción y al SQLSTATE? | SQLSTATE en `error.orig.sqlstate` (también `pgcode`). Nombre de la restricción en `error.orig.__cause__.constraint_name`, es decir, la excepción de asyncpg. Con NOT NULL, `constraint_name` es `None` y el SQLSTATE es `23502`. |
| V2 | ¿El `server_default` queda cargado después del flush? | Sí: el INSERT trae `creado_en` por `RETURNING` y se lee sin IO implícito. No hace falta `refresh`. |
| V3 | ¿Pydantic acepta `class Pagina[T](BaseModel)` (PEP 695)? | Sí, sin `Generic[T]`. Una sonda temporal confirmó además que `response_model=Pagina[X]` serializa filas ORM reales. |
| V4 | ¿Cómo se declaran modelos de prueba fuera de `SQLModel.metadata`? | `class BaseDePrueba(SQLModel, registry=registry())`, y los modelos `table=True` heredan de ella. |

## Desvíos

Ninguno respecto de las specs.

1. **FastAPI 0.162 cambió `include_router`.** Ya no copia las rutas: agrega un envoltorio interno (`_IncludedRouter`) que referencia al router original.
   - La clase de ruta se conserva con includes anidados (verificado).
   - T4 desciende por `original_router`, un atributo interno; si desaparece, T4 falla en rojo (ver arriba).
   - Se corrigió la nota de riesgo del design de CH-02.
2. **La regla de CH-01 «`include_router` copia las rutas que el grupo tiene en ese momento» ya no aplica con FastAPI 0.162.**
   - Un router agregado a un grupo después de incluir el grupo en la app sí aparece: responde y figura en OpenAPI (verificado con una sonda).
   - Igual se mantiene el orden de CH-01 (primero se arman los grupos con todos sus routers y al final se incluyen), por compatibilidad.
   - La regla no figura en `openspec/specs/` ni en `AGENTS.md`/`CLAUDE.md`. Sólo está en el design archivado de CH-01 y en `explore-CH-01.md`, que son registros históricos y quedan como están: esta constancia los corrige.
3. **Tarea 2.1.** Decía que F1 falla con `ValueError`, pero la guarda de CH-01 corta con `pytest.fail`, y F1 espera `pytest.fail.Exception`. El spec dice «el error de la guarda», así que no cambia.
4. **Evidencia TDD.** Durante el apply se borraron dos corridas: un `NameError` del arnés en el archivo de rojos, y un verde fallido por un mensaje de prueba con la palabra «nombre». Las dos quedan documentadas en la sección «Corridas eliminadas» de cada archivo. Desde CH-03, las corridas fallidas por errores propios se dejan y se anotan, no se borran.
5. **Modelo de prueba.** `ArticuloDePrueba.nombre` es opcional en el modelo, aunque la tabla lo declara NOT NULL, para poder provocar E4. Es sólo código de prueba.
6. **Triangulaciones sin rojo propio.** B5, U2, U4, U5, U7, U9, U10, E2, E6, R10, P7, T2, T3 y la T4 con app falsa cubren comportamiento que ya existía por diseño: figuran sólo en el archivo de verdes.

## Casos C-NN

CH-02 no tiene casos propios (ver `CHANGES.md`). Habilita estos, que se prueban en los changes de módulo:

| Caso | Qué aporta CH-02 |
|---|---|
| C-02 | El 409 con mensaje propio por correo o documento repetido, sin filas sueltas: traducción del `IntegrityError` y rollback del UoW |
| C-11 | El 409 y el «todo queda como estaba» al terminar una orden sin stock: rollback del UoW ante cualquier excepción, y CHECK traducido a 409 |
| C-16 | Paginación con filtro (`total 1`, `pages 1`, `page=2` → 422, `size=500` → 422) |
| C-19 | La patente repetida vigente → 409 con mensaje propio; el borrado lógico oculta el vehículo dado de baja |
