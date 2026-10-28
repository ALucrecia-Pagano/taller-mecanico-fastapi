# Tasks — CH-03 `modelos-migraciones`

Convenciones:
- **[PERMISO]**: toda acción contra una base (`taller_mecanico` o `taller_mecanico_test`): correr tests que la tocan, autogenerar, `upgrade`/`downgrade`. Se describe y se espera la confirmación de Amanda antes de ejecutarla.
- **FRENO**: el apply se detiene y no sigue hasta que Amanda lo diga. Se usa para la lectura de cada migración antes de aplicarla.
- **TDD estricto**: en cada grupo, primero el test que falla (RED, con la falla confirmada al ejecutarlo), después el código mínimo (GREEN), y luego la triangulación y el refactor con los tests en verde.
  - Cada corrida RED se agrega, sin borrar las anteriores, a `docs/evidencias/CH-03-tdd-rojo.txt`.
  - Cada corrida GREEN se agrega a `docs/evidencias/CH-03-tdd-verde.txt`.
- Referencias:
  - Los IDs (M1, S7, K5, P2, F1, D3, X2, T4) son los escenarios de `specs/`.
  - D1-D9 y V1-V7 remiten a `design.md`.
- No se instala nada: CH-03 no suma dependencias.
- No se commitea nada: los commits los hace Amanda.

## 1. Red de seguridad

- [x] 1.1 [PERMISO] Correr `pytest -v` contra `taller_mecanico_test` antes de tocar nada y anotar la línea base en el resumen del apply (CH-02 cerró en verde, ver `docs/evidencias/pytest-CH-02.txt`). Si algo falla, frenar y reportarlo como falla previa: no se arregla en CH-03.

## 2. Modelos, sin base (specs `modelo-de-datos` y `migraciones`: M7, T5 y la parte de S1, S3 y S7 que se lee de la metadata; design D1-D5)

- [x] 2.1 RED: crear `test/pytest/test_modelos.py`, que importa los cuatro `models.py` igual que `env.py` y no toca la base. Escribir:
  - M7: `SQLModel.metadata.tables` tiene exactamente las 13 tablas y ninguna `prueba_*`;
  - columnas por tabla iguales a las de la consigna (S1, versión metadata) y `usuario` sin `rol` (S2);
  - columnas nulables exactamente las diez de la spec (S3, versión metadata);
  - nombres de restricción e índices iguales a la tabla de D2 (S7, versión metadata);
  - T5: `configure_mappers()` sin error.
  
  Confirmar que falla porque los módulos no existen.
- [x] 2.2 GREEN, convención: agregar `CONVENCION_DE_NOMBRES` a `app/core/database.py` y aplicarla a `SQLModel.metadata` (D2). [PERMISO] Verificar con `pytest test/pytest/test_ciclo_de_vida.py test/pytest/test_salud.py -v` que CH-01 sigue en verde.
- [x] 2.3 GREEN `usuarios`: crear `app/modules/usuarios/__init__.py` y `models.py`, con `import app.core.database` primero y estos contenidos:
  - `Rol(StrEnum)`;
  - `Usuario`, `AsignacionRol` (con `ck_asignacion_rol_rol` armado desde `Rol`, `uq_asignacion_rol_abierta` parcial, y `foreign_keys` en `roles`/`usuario`), `IntentoAcceso` (con `ix_intento_acceso_email_ip_cuando`) y `EventoSeguridad`.
  
  Resolver **V1** (fecha `NOT NULL` con `server_default` y `Optional` en Python) y **V2** (`rol` como `VARCHAR` sin `sa.Enum`), y anotar la forma que funcionó. Verificar que los tests de 2.1 que tocan esas cuatro tablas pasan.
- [x] 2.4 GREEN `clientes`: `Cliente` (`uq_cliente_usuario_id`, `uq_cliente_documento`, `Cliente.usuario` ↔ `Usuario.cliente` con `uselist=False`) y `Vehiculo` (`ck_vehiculo_anio`, `uq_vehiculo_patente_vigente` parcial, `ix_vehiculo_cliente_id`). Verificar en verde sus tests.
- [x] 2.5 GREEN `repuestos`: `Repuesto` (`NUMERIC(10,2)`, `ck_repuesto_precio_positivo`, `ck_repuesto_stock_no_negativo`, `uq_repuesto_codigo_vigente` parcial), `MovimientoStock` (`ck_movimiento_stock_cantidad_distinta_de_cero`) y `HistorialPrecio` (`__tablename__ = "historial_precio_repuesto"`, sus dos CHECK). Verificar en verde sus tests.
- [x] 2.6 GREEN `ordenes`:
  - `CodigoEstado(StrEnum)` (R1);
  - `EstadoOrden` (PK `codigo`, `uq_estado_orden_posicion`);
  - `OrdenTrabajo` (`NUMERIC(12,2)`, `ck_orden_trabajo_total_no_negativo`, FK `estado` → `estado_orden.codigo` sin CHECK, relación `estado_orden`, `mecanico` con `foreign_keys`);
  - `ItemOrden` (dos CHECK, `uq_item_orden_orden_id_repuesto_id`);
  - `HistorialEstadoOrden` (tres FK hacia el catálogo y la orden).
  
  Todas las relaciones de D5 con `lazy="raise"`, y el índice de D4 en cada FK. Verificar **todo** `test_modelos.py` en verde.
- [x] 2.7 En `migrations/env.py`, agregar los cuatro `import app.modules.<módulo>.models  # noqa: F401` junto a `target_metadata` y reemplazar el comentario «se agregan en CH-03». Verificar M7 importando `env.py` por la misma lista de módulos (el test usa una constante compartida con un comentario que la vincula a `env.py`).
- [x] 2.8 REFACTOR: revisar nombres, comentarios y los imports bajo `TYPE_CHECKING`, y verificar `pytest test/pytest/test_modelos.py -v` en verde (sin base).

## 3. Tests del esquema contra la base, en rojo (specs `migraciones` y `modelo-de-datos`: M1, M3, M5, M6, S1-S8; design D9)

- [x] 3.1 En `conftest.py`, escribir las fixtures `esquema_al_dia` (sesión: guarda, después `python -m alembic upgrade head` por subproceso con `POSTGRES_DB=<base>_test`) y `conexion_revertida` (por test: transacción externa revertida, `AsyncSession` con `join_transaction_mode="create_savepoint"`). Resolver **V7**.
- [x] 3.2 RED: en `test/pytest/test_esquema.py`, escribir S1-S8 contra `information_schema`/`pg_catalog`, sobre `esquema_al_dia`:
  - columnas exactas y `usuario` sin `rol`;
  - nulabilidad;
  - `numeric(10,2)`/`numeric(12,2)` y `timestamptz`;
  - las 18 FK con su destino;
  - toda FK encabeza un índice, con la lista revisada de largo 18;
  - nombres exactos y la condición de los tres parciales;
  - `cuando` con `now()` al insertar sin enviarlo.
  
  En `test_migraciones.py`, escribir M1 (13 tablas y versión `0002`), M3 (catálogo con 0 filas), M5 (exactamente dos archivos en `migrations/versions/`, cada uno con «Leída antes de aplicarla», ninguno con `prueba_`) y M6 (ningún `create_all` en los `.py` fuera de `.venv`, con la lista revisada no vacía).
- [x] 3.3 [PERMISO] Correr `pytest test/pytest/test_esquema.py test/pytest/test_migraciones.py -v` contra `taller_mecanico_test` y confirmar que **fallan** porque no hay migraciones: `upgrade head` no crea tablas. M6 y los tests de CH-01 ya pasan, y queda anotado. Guardar la corrida en `CH-03-tdd-rojo.txt`.

## 4. Migración `0001_esquema_inicial` (spec `migraciones`; design D6)

- [x] 4.1 Agregar `import sqlmodel` a `migrations/script.py.mako` (R3). Verificarlo leyendo la plantilla.
- [x] 4.2 [PERMISO] Verificar que la base de desarrollo `taller_mecanico` no tiene tablas en `public` y mostrar el resultado. Si tiene alguna, frenar y preguntar.
- [x] 4.3 [PERMISO] Con `POSTGRES_DB=taller_mecanico`, correr `alembic revision --autogenerate --rev-id 0001 -m "esquema inicial"`. Verificar que se creó `migrations/versions/0001_esquema_inicial.py`. Resolver **V4** (si renderiza `postgresql_where`, `op.f(...)` y los CHECK con nombre) y anotarlo.
- [x] 4.4 **FRENO — lectura de 0001 por Amanda**, antes de aplicarla en ninguna base. Mostrar el archivo completo junto con la lista de lectura de D6:
  - 13 `create_table` en orden de dependencias;
  - 10 CHECK con nombre;
  - 18 FK sin `ondelete`;
  - 5 UNIQUE;
  - 16 `ix_*` de FK, más el de `intento_acceso` y los 3 parciales con `postgresql_where`;
  - ningún `bulk_insert`, `sa.Enum`, `prueba_` ni `drop_table` en `upgrade()`.
  
  Si algo del esquema está mal, corregir el **modelo** y volver a 4.3; no se edita el esquema a mano. No seguir sin el visto bueno.
- [x] 4.5 Con el visto bueno, escribir en el docstring de 0001 el bloque «Leída antes de aplicarla: <fecha>, por Amanda. Revisado: …» de D6. Verificar que no cambió nada más del archivo.
- [x] 4.6 [PERMISO] GREEN: correr `pytest test/pytest/test_esquema.py test/pytest/test_migraciones.py -v` contra `taller_mecanico_test`; `esquema_al_dia` aplica 0001 allí. Verificar S1-S7, M3 y M6 en verde y **S8 en verde** (`cuando` con `now()`). M1 y M5 siguen en rojo hasta el grupo 7 (esperan 0002), y queda anotado. Guardar la corrida en `CH-03-tdd-verde.txt`.

## 5. Restricciones (spec `modelo-de-datos`: K1-K13, P1-P6, F1-F3; design D2, D9)

- [x] 5.1 Escribir en `test/pytest/test_restricciones.py` las factorías mínimas de D9 (usuario, cliente, vehículo, repuesto, estado `PENDIENTE`, orden) sobre `conexion_revertida`, y un helper que afirma `IntegrityError` con `sqlstate` y `constraint_name` esperados dentro de `begin_nested()`.
- [x] 5.2 [PERMISO] TRIANGULAR los CHECK: K1-K8 (rechazo con el nombre exacto y aceptación del borde válido, incluidos `+3`/`-3` de K5 y el precio que baja de K6). Verificar en verde.
- [x] 5.3 [PERMISO] TRIANGULAR la unicidad común: K9-K12 y K13 (`NOT NULL`, SQLSTATE `23502`). Verificar en verde.
- [x] 5.4 [PERMISO] TRIANGULAR los índices parciales: P1-P6. Resolver **V5** (si asyncpg trae el nombre del índice parcial como `constraint_name`) y anotarlo; si no lo trae, frenar y avisar antes de seguir, porque afecta los mapas de mensajes de CH-05 a CH-10. Verificar en verde.
- [x] 5.5 [PERMISO] TRIANGULAR las FK: F1-F3 (incluido `fk_orden_trabajo_estado_estado_orden` y `desde_estado` nulo aceptado). Verificar en verde.
- [x] 5.6 REFACTOR: unificar las factorías y el helper. [PERMISO] Verificar `pytest test/pytest/test_restricciones.py -v` en verde.

## 6. Tipos y navegación (spec `modelo-de-datos`: T1-T4, T6; design D3, D5)

- [x] 6.1 [PERMISO] En `test/pytest/test_navegacion.py`, escribir:
  - T1: `precio` vuelve como `Decimal('8500.00')`, no `float`;
  - T2: `borrado_en` vuelve con `tzinfo`;
  - T3: `selectinload(Usuario.cliente)` devuelve un `Cliente` o `None`, nunca una lista;
  - T4: una orden leída sin precargar `items` lanza la excepción de `lazy="raise"` al navegarla; se verifica que no se ejecutó ninguna consulta, con un contador de sentencias por evento del motor;
  - T6: una orden con dos ítems y una línea de historial en un solo `add` + `flush` deja las cuatro filas.
  
  Si alguno falla, corregir el modelo (y, si eso cambia el esquema, avisar antes: implicaría volver a 4.3). Verificar en verde.

## 7. Migración `0002_disparador_solo_agregado` (spec `solo-agregado`: D1-D7; spec `migraciones`: M1, M2, M4, M5; design D7, D9)

- [x] 7.1 RED: en `test/pytest/test_solo_agregado.py`, sobre `conexion_revertida` con filas propias, escribir:
  - D1: `INSERT` en las tres tablas;
  - D2 y D3: `UPDATE` y `DELETE` en cada tabla → `IntegrityError` con SQLSTATE `23001` y el mensaje «La tabla <tabla> es de sólo agregado: no se permite <op>»;
  - D4: `UPDATE` sin filas, sin error;
  - D5: `TRUNCATE` de las tres;
  - D6: el `UPDATE` hecho dentro de un `UnitOfWork` de CH-02 sale como `Conflicto` con el mensaje genérico;
  - D7: `orden_trabajo` y `repuesto` siguen aceptando `UPDATE`.
  
  En `test_migraciones.py`, escribir M2 (ciclo `downgrade base` → `upgrade head` por subproceso, verificando tablas, la función y que las `prueba_*` siguen; con `finally` que vuelve a `head`) y M4 (`compare_metadata` en `run_sync`, que ignora sólo `remove_table` de `prueba_*`). [PERMISO] Correr y confirmar que D2, D3 y D6 **fallan** (hoy el `UPDATE`/`DELETE` pasa). Guardar en `CH-03-tdd-rojo.txt`.
- [x] 7.2 GREEN: crear a mano `migrations/versions/0002_disparador_solo_agregado.py` (`alembic revision --rev-id 0002 -m "disparador solo agregado"`, **sin** `--autogenerate`). Contenido según D7: una función `rechazar_cambio_solo_agregado()` con `ERRCODE = 'restrict_violation'`, tres disparadores `tg_<tabla>_solo_agregado` `BEFORE UPDATE OR DELETE … FOR EACH ROW`, y un `downgrade` que borra los tres disparadores y la función sin `IF EXISTS`.
- [x] 7.3 **FRENO — lectura de 0002 por Amanda**, antes de aplicarla. Mostrar el archivo completo y la nota de D7 sobre la alternativa de sentencia (no adoptada). Con el visto bueno, escribir el docstring «Leída antes de aplicarla: <fecha>, por Amanda. Revisado: …».
- [x] 7.4 [PERMISO] GREEN: correr `pytest test/pytest/test_solo_agregado.py test/pytest/test_migraciones.py -v` contra `taller_mecanico_test`; `esquema_al_dia` aplica 0002. Resolver **V6** (`23001` como `IntegrityError`) y anotarlo. Verificar D1-D7, M1 (versión `0002`), M2, M4 y M5 en verde. Guardar en `CH-03-tdd-verde.txt`.
- [x] 7.5 REFACTOR: revisar nombres y comentarios de 0002, sin tocar el bloque de lectura salvo para reflejar un cambio, que exigiría volver a leerla. [PERMISO] Verificar el grupo en verde.

## 8. `test/solo_agregado.sql` — C-14 (spec `solo-agregado`: X1, X2; design D8)

- [x] 8.1 RED: en `test_solo_agregado.py`, escribir:
  - el helper que lee el archivo (descarta comentarios `--` y líneas `\…`, y corta en `;` de fin de línea fuera de `$$ … $$`);
  - X2: con las tablas vacías, el bloque `DO` falla con «Corré python seed.py primero»;
  - X1: con filas propias, el bloque pasa, las seis sentencias siguientes fallan con `23001` y la séptima con `23503` y `fk_orden_trabajo_estado_estado_orden`; además, el helper encontró exactamente 1 bloque y 7 sentencias.
  
  [PERMISO] Confirmar que falla porque el archivo no existe. Guardar en `CH-03-tdd-rojo.txt`.
- [x] 8.2 GREEN: escribir `test/solo_agregado.sql` según D8:
  - encabezado que pide correr `python seed.py` antes y aclara que la captura se hace en CH-04;
  - `\set ON_ERROR_STOP on`, bloque `DO` de verificación (las tres tablas y `vehiculo`) y `\set ON_ERROR_STOP off`;
  - las seis sentencias con `WHERE id = (SELECT min(id) …)` y el `INSERT` con estado `INEXISTENTE`;
  - la respuesta esperada en un comentario sobre cada una, con la nota de que el texto de la FK depende del idioma del servidor.
  
  [PERMISO] Verificar X1 y X2 en verde y guardar en `CH-03-tdd-verde.txt`.

## 9. Base de desarrollo y documentación

- [x] 9.1 [PERMISO] **Sólo después de las lecturas de 4.4 y 7.3**: correr `alembic upgrade head` sobre `taller_mecanico` y mostrar `alembic current` (`0002 (head)`) y `\dt` (13 tablas más `alembic_version`).
- [x] 9.2 Actualizar `README.md`:
  - mover CH-03 de «Planificado» a «Implementado», con su descripción;
  - verificar que los pasos de puesta en marcha incluyen `alembic upgrade head` (y agregarlo si falta);
  - anotar que `test/solo_agregado.sql` se corre después de `python seed.py` (CH-04).
  
  Verificar releyendo la sección.
- [x] 9.3 Anotar en `CHANGES.md`, dentro de CH-04, la nota R4: «la captura de `psql -f test/solo_agregado.sql` (C-14) se hace acá, después del seed, y se guarda en `docs/evidencias/`; el seed carga el catálogo desde `CodigoEstado` y un test verifica que coinciden». En CH-03, anotar R1 junto a «Enums espejo». Verificar con `git diff CHANGES.md` que sólo cambiaron esas líneas.

## 10. Verificación final

- [x] 10.1 Revisar el punto de control de governance con `git grep` y anotar el resultado:
  - ningún `create_all`;
  - ningún `commit(` en `models.py`;
  - ninguna relación sin `lazy="raise"`;
  - ningún `sa.Enum`;
  - los cuatro `models.py` empiezan importando `app.core.database`;
  - las dos migraciones tienen el bloque de lectura;
  - `env.py` no importa `main`.
- [x] 10.2 Correr `openspec validate modelos-migraciones --strict` y verificar que no hay errores.
- [x] 10.3 [PERMISO] Correr `pytest -v` completo contra `taller_mecanico_test` y guardar la salida completa en `docs/evidencias/pytest-CH-03.txt`. Verificar que:
  - todos los escenarios (M1-M7, S1-S8, K1-K13, P1-P6, F1-F3, D1-D7, X1-X2, T1-T6) tienen al menos un test en verde;
  - las suites de CH-01 y CH-02 siguen en verde;
  - no hay fallos ni errores;
  - la base de prueba queda en `0002 (head)` y sin tablas `prueba_*`.
  
  Dejar el change listo para que Amanda revise y commitee (`feat(CH-03): ...`).
