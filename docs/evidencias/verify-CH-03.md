# Verify de CH-03 `modelos-migraciones`

- **Fecha**: 2026-10-28
- **Verificó**: Amanda Pagano (verificación manual, antes del archive)
- **Change**: `openspec/changes/modelos-migraciones/` (38/38 tareas; `openspec validate --strict` válido)
- **Entorno**: Windows 11, Python 3.13.6, PostgreSQL 17. SQLAlchemy 2.1.6, SQLModel 0.0.48, Alembic 1.20.1, asyncpg 0.32.0, Pydantic 2.14.1, pytest 9.1.1, pytest-asyncio 1.4.0.
- **Bases**:
  - `taller_mecanico_test`: la suite la migra sola, y le hace `downgrade base` y `upgrade head` en M2.
  - `taller_mecanico`: con permiso aparte, se autogeneró la 0001 contra ella (estaba vacía) y se aplicó `upgrade head` después de las dos lecturas.

## Comandos y resultado

| # | Comando | Resultado |
|---|---|---|
| 1 | `pytest -v` | **208 passed**: 94 de CH-01 y CH-02 y 114 de CH-03, contra `taller_mecanico_test` |
| 2 | `alembic current`, sobre `taller_mecanico` | `0002 (head)` |
| 3 | `\dt` en `psql`, sobre `taller_mecanico` | Las 13 tablas del dominio más `alembic_version` |

CH-03 no expone endpoints, así que no hay `.http` ni humo con el servidor levantado.

Evidencia complementaria generada durante el apply:

- `docs/evidencias/pytest-CH-03.txt`: salida completa de `pytest -v` (208 passed en 28,73 s, sin fallos ni errores). Después de la corrida, `taller_mecanico_test` quedó en `0002 (head)` y sin tablas `prueba_*`.
- `docs/evidencias/CH-03-tdd-rojo.txt` y `CH-03-tdd-verde.txt`: cada RED y cada GREEN, con un encabezado por grupo y tarea. Las corridas fallidas por errores propios están todas y anotadas (ver Desvíos, 8); no se borró ninguna.
- Red de seguridad (tarea 1.1): antes de tocar nada, la suite dio 94 passed.
- Disparadores en `taller_mecanico`: `tg_historial_estado_orden_solo_agregado`, `tg_movimiento_stock_solo_agregado` y `tg_historial_precio_repuesto_solo_agregado`.
- Punto de control de governance (tarea 10.1):
  - ningún uso de `.create_all` en el repo;
  - ningún `commit(` en los `models.py`;
  - las 22 puntas de relación (11 relaciones × 2) llevan `lazy="raise"`;
  - ningún `sa.Enum` ni `Enum(` en modelos ni migraciones;
  - los cuatro `models.py` importan `app.core.database` antes de declarar tablas;
  - las dos migraciones tienen el bloque «Leída antes de aplicarla»;
  - `env.py` no importa `main`.

## Lecturas de las migraciones

Las dos las leyó **Amanda Pagano**, el 2026-10-28, antes de aplicarlas en ninguna base. El bloque «Leída antes de aplicarla» de cada docstring se escribió recién con su visto bueno (frenos de las tareas 4.4 y 7.3).

| Migración | Cómo nació | Qué revisó Amanda |
|---|---|---|
| `0001_esquema_inicial` | `alembic revision --autogenerate --rev-id 0001`, contra `taller_mecanico` vacía | 13 tablas, con el catálogo vacío; `usuario` sin `rol`; los 10 CHECK con su página del PDF (p. 5: rol, anio, precio, stock, total, cantidad y precio_unitario de `item_orden`; p. 6: cantidad de `movimiento_stock`, precio_nuevo > 0 y precio_nuevo <> precio_anterior); los 3 índices únicos parciales; sin tablas de prueba; el `downgrade` |
| `0002_disparador_solo_agregado` | `alembic revision --rev-id 0002`, sin autogenerate, escrita a mano | `down_revision` 0001; la función con `ERRCODE restrict_violation` y su mensaje; los tres disparadores `BEFORE UPDATE OR DELETE FOR EACH ROW`, armados en un `for` sobre la tupla fija `TABLAS`; el `downgrade`, que borra los disparadores y después la función |

En la primera lectura de la 0001, Amanda vio `ISNULL` sin espacio en la línea 127. Se comprobó, byte por byte y con `grep`, que en el disco dice `IS NULL`: era un efecto del corte de línea de la vista. No se regeneró la migración.

## Evidencia TDD por grupo

| Grupo | Archivo de test | Capa | RED (por qué falló) | GREEN | Triangulación | Refactor |
|---|---|---|---|---|---|---|
| 1. Red de seguridad | Suite de CH-01 y CH-02 | — | — | 94/94 | — | — |
| 2. Modelos, sin base | `test_modelos.py` | Unidad (metadata) | No existían los módulos (56 en rojo, por tabla) | 17 (usuarios) → 25 (clientes) → 37 (repuestos) → 55 (ordenes) → 56 (`env.py`) | Por tabla: S1, S3 y S7 de la metadata; T5 con los cuatro módulos | Suite completa 150/150 |
| 3. Esquema contra la base | `test_esquema.py`, `test_migraciones.py` | Integración (base `_test`) | Sin migraciones, `upgrade head` no crea tablas (12 en rojo) | — (en el grupo 4) | — | — |
| 4. Migración 0001 | `test_esquema.py`, `test_migraciones.py` | Integración | — | S1-S8, M3, M6 (13/15; M1 y M5 esperan la 0002) | — | — |
| 5. Restricciones | `test_restricciones.py` | Integración | Sin rojo propio: las restricciones ya existían por la 0001. Con el nombre esperado de P1 alterado, P1 falla | 22/22 | K1-K13, P1-P6, F1-F3 | Factorías y ayudantes en `fabricas.py` |
| 6. Tipos y navegación | `test_navegacion.py` | Integración | Sin rojo propio (el rojo registrado es un error del test, Desvíos 8) | 5/5 | T1-T4, T6 | — |
| 7. Migración 0002 | `test_solo_agregado.py`, `test_migraciones.py` | Integración | Sin disparador: D2 y D3 (6 casos) y D6 no fallaban; M1, M2 y M5 esperaban la 0002 | 21/21 | D1, D4, D5, D7, M4 (pasaban antes por diseño) | Sin cambios |
| 8. `solo_agregado.sql` | `test_solo_agregado.py` | Integración + archivo | No existía `test/solo_agregado.sql` | 3/3 | X1, X2 y la forma del archivo (1 bloque + 7 sentencias) | — |
| 9. Base de desarrollo y documentación | — | — | — | `taller_mecanico` en `0002 (head)` | — | README y CHANGES |
| 10. Verificación final | Suite completa | — | — | 208/208 | — | — |

## Escenario de la spec → test

| Spec | Escenario | Test |
|---|---|---|
| migraciones | M1 Upgrade sobre base vacía | `test_migraciones.py::test_m1_upgrade_crea_las_13_tablas_en_la_ultima_version` |
| migraciones | M2 Upgrade, downgrade base y upgrade | `test_migraciones.py::test_m2_upgrade_downgrade_base_y_upgrade` |
| migraciones | M3 Catálogo sin filas | `test_migraciones.py::test_m3_el_catalogo_queda_vacio` |
| migraciones | M4 Sin diferencias entre modelos y base | `test_migraciones.py::test_m4_modelos_y_base_sin_diferencias` |
| migraciones | M5 Comentario de lectura y sin tablas de prueba | `test_migraciones.py::test_m5_dos_migraciones_leidas_y_sin_tablas_de_prueba` |
| migraciones | M6 Ningún `create_all` | `test_migraciones.py::test_m6_ningun_create_all` |
| migraciones | M7 La metadata tiene las 13 tablas | `test_modelos.py::test_m7_la_metadata_tiene_las_13_tablas`, `test_m7_env_importa_los_mismos_modulos` |
| modelo-de-datos | S1 Columnas textuales | `test_esquema.py::test_s1_columnas_de_la_consigna` (+ `test_modelos.py::test_s1_…[tabla]` ×13) |
| modelo-de-datos | S2 `usuario` sin `rol` | `test_esquema.py::test_s2_usuario_sin_columna_rol` (+ `test_modelos.py`) |
| modelo-de-datos | S3 Nulabilidad | `test_esquema.py::test_s3_solo_las_marcadas_nulo_admiten_null` (+ `test_modelos.py` ×13) |
| modelo-de-datos | S4 Tipos en la base | `test_esquema.py::test_s4_dinero_numeric_y_fechas_con_zona` |
| modelo-de-datos | S5 Las 18 FK con su destino | `test_esquema.py::test_s5_las_18_fk_con_su_destino` |
| modelo-de-datos | S6 Toda FK encabeza un índice | `test_esquema.py::test_s6_toda_fk_encabeza_un_indice` |
| modelo-de-datos | S7 Nombres exactos | `test_esquema.py::test_s7_nombres_exactos_de_restricciones`, `test_s7_nombres_de_indices_y_condicion_de_los_parciales` (+ `test_modelos.py` ×26) |
| modelo-de-datos | S8 `cuando` con la hora de la base | `test_esquema.py::test_s8_cuando_toma_la_hora_de_la_base` |
| modelo-de-datos | K1-K8 CHECK | `test_restricciones.py::test_k1_stock_negativo` … `test_k8_rol_fuera_de_la_lista` |
| modelo-de-datos | K9-K12 UNIQUE | `test_restricciones.py::test_k9_correo_repetido` … `test_k12_repuesto_repetido_en_una_orden` |
| modelo-de-datos | K13 NOT NULL | `test_restricciones.py::test_k13_columna_obligatoria_en_null` |
| modelo-de-datos | P1-P6 Índices parciales | `test_restricciones.py::test_p1_patente_vigente_repetida` … `test_p6_rol_revocado_y_otro_rol` |
| modelo-de-datos | F1-F3 Claves foráneas | `test_restricciones.py::test_f1_orden_con_estado_inexistente` … `test_f3_orden_de_un_vehiculo_inexistente` |
| modelo-de-datos | T1 Decimal exacto | `test_navegacion.py::test_t1_el_dinero_vuelve_como_decimal_exacto` |
| modelo-de-datos | T2 Fecha con zona | `test_navegacion.py::test_t2_la_fecha_vuelve_con_zona` |
| modelo-de-datos | T3 `Usuario.cliente` es un objeto | `test_navegacion.py::test_t3_usuario_cliente_es_un_objeto_o_nada` |
| modelo-de-datos | T4 Relación no precargada | `test_navegacion.py::test_t4_relacion_no_precargada_falla_sin_consultar` |
| modelo-de-datos | T5 Relaciones sin ambigüedad | `test_modelos.py::test_t5_los_mappers_configuran_sin_ambiguedad` |
| modelo-de-datos | T6 Alta conjunta | `test_navegacion.py::test_t6_orden_con_items_e_historial_en_un_solo_alta` |
| solo-agregado | D1 Insertar en las tres tablas | `test_solo_agregado.py::test_d1_insertar_en_las_tres_tablas` |
| solo-agregado | D2 UPDATE rechazado | `test_solo_agregado.py::test_d2_update_rechazado[…]` ×3 |
| solo-agregado | D3 DELETE rechazado | `test_solo_agregado.py::test_d3_delete_rechazado[…]` ×3 |
| solo-agregado | D4 UPDATE sin filas no da error | `test_solo_agregado.py::test_d4_update_que_no_alcanza_filas_no_da_error[…]` ×3 |
| solo-agregado | D5 TRUNCATE permitido | `test_solo_agregado.py::test_d5_truncate_permitido` |
| solo-agregado | D6 El rechazo llega como violación de integridad | `test_solo_agregado.py::test_d6_el_rechazo_llega_como_conflicto` |
| solo-agregado | D7 Las demás tablas siguen modificables | `test_solo_agregado.py::test_d7_las_demas_tablas_siguen_modificables` |
| solo-agregado | X1 Las siete sentencias fallan | `test_solo_agregado.py::test_x1_las_siete_sentencias_fallan_como_se_espera` (+ `test_x_el_archivo_tiene_la_verificacion_y_siete_sentencias`) |
| solo-agregado | X2 Tablas vacías | `test_solo_agregado.py::test_x2_con_tablas_vacias_corta_antes_de_las_siete` |

## V1 a V7 (contra las versiones instaladas)

| # | Pregunta | Resultado |
|---|---|---|
| V1 | ¿Cómo se declara una fecha `NOT NULL` con `server_default` y `Optional` en Python? | `Field(default=None, nullable=False, sa_type=DateTime(timezone=True), sa_column_kwargs={"server_default": text("now()")})` da `timestamptz NOT NULL DEFAULT now()`. El `RETURNING` la trae después del `flush` (S8). |
| V2 | ¿Cómo queda `rol: Rol` como `VARCHAR` sin `sa.Enum`? | `rol: Rol = Field(sa_type=AutoString)`. El CHECK se arma desde el enum: `CheckConstraint(f"rol IN (...)", name="rol")`. |
| V3 | ¿`SERIAL` o `IDENTITY`? ¿Lo reinicia `TRUNCATE … RESTART IDENTITY`? | `SERIAL` (`usuario_id_seq`). Con `TRUNCATE usuario RESTART IDENTITY CASCADE`, el siguiente `id` vuelve a ser 1. Probado en `_test`, dentro de una transacción revertida. |
| V4 | ¿Autogenerate renderiza `postgresql_where`, `op.f(...)` y los CHECK con nombre? | Sí, los tres. Conteo de la 0001: 13 tablas, 10 CHECK, 18 FK sin `ondelete`, 5 UNIQUE, 17 `ix_`, 3 parciales. |
| V5 | ¿asyncpg trae `constraint_name` en una violación de índice único parcial? | Sí, con el nombre del índice (`uq_vehiculo_patente_vigente`, `uq_repuesto_codigo_vigente`, `uq_asignacion_rol_abierta`). Los mapas de mensajes de CH-05 a CH-10 pueden usarlos. |
| V6 | ¿El `23001` del disparador llega como `IntegrityError`? | Sí: `sqlstate == "23001"`, y el UoW de CH-02 lo traduce a `Conflicto` con el mensaje genérico (D6). |
| V7 | ¿`join_transaction_mode="create_savepoint"` funciona con la `AsyncSession` de SQLModel? | Sí. La transacción externa se revierte al final del test, y `commit`/`rollback` de la sesión sólo actúan sobre el SAVEPOINT (lo usa D6). |

## Desvíos

Ninguno respecto de las specs.

1. **Archivos auxiliares de test que el design no listaba**:
   - `test/pytest/esquema_esperado.py`: el esquema esperado, compartido por los tests de metadata y los de base;
   - `test/pytest/fabricas.py`: factorías y ayudantes de rechazo. La tarea 5.1 las ponía en `test_restricciones.py`, pero S8 ya las necesitaba en el grupo 3.
2. **`test_modelos.py` por tabla.** El primer RED importaba los cuatro módulos a nivel de archivo: ningún test podía pasar hasta tener los cuatro. Se reorganizó por tabla, para que cada módulo pasara a verde por su cuenta. Las dos corridas en rojo están en la evidencia.
3. **Fixture `alembic_de_prueba`** en `conftest.py`, además de `esquema_al_dia` y `conexion_revertida`. Corre Alembic por subproceso con la guarda, y la usan `esquema_al_dia` y M2. M2 también hace `dispose()` del motor del esquema después del ciclo, porque las conexiones del pool tienen sentencias preparadas contra las tablas borradas.
4. **Docstrings de las migraciones.** Evitan el texto `prueba_`, porque M5 exige que ninguna migración lo contenga. «Sin tablas prueba_*» quedó como «Sin las tablas de prueba de la suite de pytest». Al reemplazar el docstring de la 0001 se perdió el espacio final de la línea `Revises:`, sin efecto.
5. **La 0002 no importa `sa` ni `sqlmodel`**, que la plantilla agrega y la migración no usa.
6. **`solo_agregado.sql` también exige un `vehiculo`** en la verificación inicial, además de las tres tablas de sólo agregado (ya estaba en el design D8). Sin un vehículo, la séptima sentencia fallaría por `NOT NULL` y no por la FK.
7. **Triangulaciones sin rojo propio.** Los grupos 5 y 6, y en el 7 los escenarios D1, D4, D5, D7 y M4, cubren comportamiento que ya existía por la migración aplicada. Figuran sólo en el archivo de verdes. Control de que no pasan en vacío: con el nombre esperado de P1 alterado, P1 falla.
8. **Corridas fallidas por errores propios**, todas en la evidencia:
   - **3.3:** el patrón de M6 encontraba el nombre del propio test y un docstring. Hicieron falta dos corridas para corregirlo: el patrón pasó a `\.create_all\b`, que también detecta `run_sync(metadata.create_all)`, y el test se excluye a sí mismo.
   - **4.6:** S8 comparaba la fecha contra la fila `(datetime,)` en vez del valor.
   - **6.1:** se usó el `select` de SQLAlchemy en vez del de SQLModel. Esta corrida no se capturó con `tee`: está anotada a mano en `CH-03-tdd-rojo.txt`, y la anotación lo dice.

## Casos C-NN

| Caso | Qué aporta CH-03 |
|---|---|
| **C-14** (propio) | `test/solo_agregado.sql`: la verificación inicial, los seis rechazos del disparador y el de la FK de una orden con estado inexistente, con la respuesta esperada en comentarios. Lo cubren D1-D7, X1 y X2 con filas propias. **La captura de `psql` pasa a CH-04** (R4), porque en CH-03 las tablas de sólo agregado están vacías y un disparador de fila no salta sin filas. |
| C-02 | La garantía en la base: `uq_usuario_email` y `uq_cliente_documento` (K9, K10) |
| C-11 | `ck_repuesto_stock_no_negativo` como red de seguridad del stock (K1) |
| C-17 | El catálogo `estado_orden` con FK desde `orden_trabajo.estado` (F1), `posicion` única y `es_final` |
| C-18 | `ck_historial_precio_repuesto_precio_cambia`: un PATCH que no cambia el precio no puede dejar línea (K6) |
| C-19 | `uq_vehiculo_patente_vigente`: una patente dada de baja se puede volver a registrar, y dos vigentes iguales no (P1-P3) |
