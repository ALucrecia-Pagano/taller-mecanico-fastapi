# Explore de CH-03 `modelos-migraciones`

Resumen del explore (`/opsx:explore`) del tercer change, hecho el 2026-10-28 en **modo autónomo** a pedido de la alumna, antes del propose. No se escribió código.

Fuentes: `CHANGES.md` (CH-03, OB-05), `knowledge-base/04_modelo_de_datos.md`, `05_reglas_de_negocio.md` (RN-01, RN-03, RN-15, RN-16, RN-19, RN-20), `08_arquitectura_propuesta.md`, `09_decisiones_y_supuestos.md` (DA-00, DA-08, DA-09, DA-20, DA-31, DD-01, DD-02, DD-03, DD-10, DD-13, SU-01, SU-02), `11_casos_de_prueba.md` (C-14, C-19), `12_criterios_de_evaluacion.md`, `AGENTS.md`, las specs de `openspec/specs/` (sobre todo `migraciones`, `unidad-de-trabajo`, `errores-de-dominio`), `docs/evidencias/explore-CH-01.md` (notas 6b-6f y 8) y `explore-CH-02.md` (nota 8 y 7d), el código existente (`migrations/env.py`, `app/core/database.py`, `app/core/errores.py`, `app/core/unit_of_work.py`, `test/pytest/conftest.py`, `tablas_de_prueba.py`, `test_migraciones.py`) y la consigna: modelo de dominio (pp. 4-6), Ejercicio 2 y Ejercicio 7 (p. 14), requisitos no funcionales (p. 19), C-14 (p. 21) y criterios de evaluación (p. 22).

Versiones instaladas en `.venv` (para lo que se verifica en el apply): SQLModel 0.0.48, SQLAlchemy 2.1.6, Alembic 1.20.1, asyncpg 0.32.0, Pydantic 2.14.1.

En la columna «Decisión», **[Agente]** marca lo que decidió el agente en modo autónomo (la alumna puede revertirlo en el propose); lo que no lleva marca sale textual de la consigna, de la KB o de una DA/DD ya aceptada. Lo que la consigna no especifica está marcado como tal.

## Qué nace en CH-03

```
app/core/database.py           + convención de nombres en SQLModel.metadata (decisión 3)
app/modules/usuarios/models.py   Usuario, AsignacionRol, IntentoAcceso, EventoSeguridad, enum Rol
app/modules/clientes/models.py   Cliente, Vehiculo
app/modules/repuestos/models.py  Repuesto, MovimientoStock, HistorialPrecio
app/modules/ordenes/models.py    OrdenTrabajo, EstadoOrden, ItemOrden, HistorialEstadoOrden, enum CodigoEstado
app/modules/<módulo>/__init__.py (los 4)
migrations/env.py              + import de los 4 models.py
migrations/script.py.mako      + import sqlmodel
migrations/versions/0001_esquema_inicial.py           (autogenerada, leída antes de aplicarla)
migrations/versions/0002_disparador_solo_agregado.py  (a mano)
test/solo_agregado.sql         C-14
test/pytest/test_esquema*.py   suite test-first (escenarios de abajo)
```

```
  base vacía
      |  alembic upgrade 0001  (autogenerada: 13 tablas, catálogo vacío)
      v
  [esquema]
      |  alembic upgrade 0002  (a mano: 1 función + 3 disparadores de fila)
      v
  [esquema + sólo agregado] = head
      |  downgrade 0002 -> borra los 3 disparadores y la función
      |  downgrade 0001 -> borra las 13 tablas en orden inverso de FK
      v
  base vacía  --> upgrade head otra vez (Ej. 2)
```

## Decisiones

| # | Pregunta | Decisión | Por qué | Alternativa descartada |
|---|---|---|---|---|
| 1 | ¿Qué nace en CH-03 y qué no? | Nacen los cuatro `models.py` (con su `__init__.py`), la convención de nombres, los imports en `env.py`, las dos migraciones, `test/solo_agregado.sql` y la suite. **No** nacen: `schemas.py`, `repository.py`, `unit_of_work.py`, `service.py`, `router.py` de los módulos (cada uno en su change), el repositorio de sólo lectura de `estado_orden` (CH-09), `seed.py` (CH-04). | Criterio de CH-01 y CH-02: nace sólo lo que se implementa y prueba. `CHANGES.md` asigna los modelos y las dos migraciones a CH-03 y es el único change con migraciones. | Crear los archivos vacíos de cada módulo «para respetar la estructura»: archivos sin código ni test. |
| 2 | Nombres de tablas, columnas y clases | Textuales del PDF (pp. 5-6) y de `04_modelo_de_datos.md`: 13 tablas, `HistorialPrecio` → `__tablename__ = "historial_precio_repuesto"`. `usuario` **sin** columna `rol` (DD-01). Ninguna columna agregada. | «Los nombres de tablas y columnas son obligatorios». Se puede agregar, pero nada lo pide. | Agregar `creado_en`/`actualizado_en` genéricos: no lo pide nadie y ensucia C-14. |
| 3 | ¿Cómo se fijan nombres de restricción estables (pedido 8 de CH-02)? | **[Agente]** `naming_convention` en `SQLModel.metadata`, definida y aplicada en `app/core/database.py`; cada `models.py` importa `app.core.database` antes de declarar tablas (con un comentario que dice por qué). Convención: `pk_%(table_name)s`, `fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s`, `uq_%(table_name)s_%(column_0_N_name)s`, `ck_%(table_name)s_%(constraint_name)s`, `ix_%(table_name)s_%(column_0_N_name)s`. Los tres índices parciales llevan nombre **explícito** (la convención no aplica a un `Index` con nombre). Un test lee `pg_constraint`/`pg_indexes` y compara contra la lista de la tabla «Nombres de restricción» (abajo). | El mapa restricción → mensaje de cada UoW (CH-02, 6b) depende del nombre que trae asyncpg; un nombre autogenerado por Postgres (`usuario_email_key`) cambia si cambia el orden de columnas. La convención tiene que estar puesta **antes** de declarar las tablas: SQLAlchemy la aplica al adjuntar la restricción. `database.py` ya es «la base»; no hace falta un archivo nuevo en el core. | (a) Nombre a mano en cada restricción: `Field(foreign_key=...)` no acepta nombre; habría que pasar `sa_column` en 18 FK. (b) Archivo nuevo `app/core/modelos.py`: suma un archivo «No especificado» sin necesidad. |
| 3a | Largo de los nombres | Todos ≤ 63 caracteres (límite de Postgres). El más largo: `fk_historial_estado_orden_desde_estado_estado_orden` (51). | Un nombre truncado por Postgres dejaría de coincidir con el mapa del UoW. | — |
| 3b | `unique=True` + `index=True` en la misma columna | Nunca juntos: `unique=True` sólo crea una **restricción** `uq_*`; con `index=True` SQLAlchemy crea un índice único `ix_*` y el nombre deja de ser `uq_`. | Gotcha de SQLAlchemy; rompe el mapa de mensajes sin que nada falle. | — |
| 4 | Enum `Rol`: ¿tipo nativo de Postgres o texto + CHECK? | **[Agente]** `VARCHAR` + `CHECK` nombrado `ck_asignacion_rol_rol` (`rol IN ('ADMIN','RECEPCION','MECANICO','CLIENTE')`), con la lista generada desde el `StrEnum` `Rol` de `usuarios/models.py`. Nada de `CREATE TYPE`. | La consigna dice literalmente «CHECK de rol dentro de ADMIN, RECEPCION, MECANICO, CLIENTE». Un `ENUM` nativo deja un `TYPE` que `downgrade` no borra (bug conocido de autogenerate) y rompería el ciclo `upgrade → downgrade → upgrade`. | `sa.Enum(Rol)` nativo (default de SQLModel para un campo enum): no es un CHECK y rompe el downgrade. |
| 5 | Enum espejo de los estados: ¿cómo se llama? | **[Agente]** `CodigoEstado(StrEnum)` en `ordenes/models.py`, con `PENDIENTE`, `EN_REPARACION`, `TERMINADA`, `CANCELADA`. Refinamiento **R1** respecto de `CHANGES.md`, que dice «Enums espejo `Rol` y `EstadoOrden`». | `EstadoOrden` ya es la clase del catálogo (Figura 1, tabla `estado_orden`) en el **mismo** `models.py`: dos `EstadoOrden` chocan. El PDF no nombra el enum («en el código los estados se nombran con un enum»). `CodigoEstado` dice lo que es: los valores válidos de `estado_orden.codigo`. | Renombrar la clase del catálogo (rompe el nombre de la Figura 1); `Estado` a secas (ambiguo en el servicio). |
| 6 | `orden_trabajo.estado` y el historial: ¿tipo enum o texto? | `VARCHAR` + FK a `estado_orden.codigo`, tipado `str` en el modelo (no `CodigoEstado`), **sin** CHECK. El enum vive en el contrato (schemas, CH-09) y en el servicio. | RN-19 y Ej. 2: «claves foráneas al catálogo, no un CHECK con la lista escrita adentro». Tipar la columna con el enum haría que SQLModel genere un tipo/CHECK. | Columna `CodigoEstado` con `native_enum=False`: agrega un CHECK que el PDF prohíbe. |
| 7 | Tipos | `id` `int` con autoincremento (default de SQLAlchemy en Postgres); textos `str` → `VARCHAR` sin largo (la consigna no fija largos); dinero `Decimal` con `max_digits`/`decimal_places` → `NUMERIC(10,2)` (`precio`, `precio_unitario`, `precio_anterior`, `precio_nuevo`) y `NUMERIC(12,2)` (`total`); cantidades, `stock`, `anio`, `posicion` `int`; `activo`, `exito`, `es_final`, `debe_cambiar_password` `bool`; **toda** fecha `DateTime(timezone=True)` → `timestamptz`. **[Agente]** `intento_acceso.ip` es `VARCHAR`, no `INET`. | Consigna p. 6 y regla dura «nunca `float`». `INET` devolvería objetos `ipaddress` de asyncpg sin aportar nada a RN-08 (que compara por igualdad). | `TEXT` explícito (es lo mismo en Postgres; `AutoString` es lo que genera SQLModel); `INET` para `ip`. |
| 7a | Nulabilidad | Sólo admiten NULL las marcadas «(nulo)»: `usuario.password_cambiada_en`, `asignacion_rol.vence_en/revocada_en/otorgada_por`, `cliente.usuario_id`, `vehiculo.borrado_en`, `repuesto.borrado_en`, `orden_trabajo.mecanico_id`, `historial_estado_orden.desde_estado`, `movimiento_stock.orden_id`. Todas las demás `NOT NULL`, incluidas las que tienen `server_default`. | DA-20 / SU-01. | — |
| 7b | `server_default` | **[Agente]** `now()` sólo en las fechas que registran «cuándo pasó»: `asignacion_rol.desde`, `intento_acceso.cuando`, `evento_seguridad.cuando`, `orden_trabajo.creada_en`, `historial_estado_orden.cuando`, `movimiento_stock.cuando`, `historial_precio_repuesto.cuando`. Booleanos y `stock` sin `server_default` (el servicio los escribe siempre). «No especificado en la consigna». | La fila nunca queda con una fecha inventada por el cliente; CH-02 verificó (2g) que el `RETURNING` trae el valor después del `flush` sin IO implícito. Costo declarado: `now()` es la hora de **inicio de la transacción**: dos líneas de historial de la misma transacción tienen el mismo `cuando` y se ordenan por `id`. | `default` en Python para todas: cada servicio tendría que acordarse; `server_default` también en booleanos: nadie lo necesita. |
| 8 | Índice en cada FK | 18 FK. Regla: toda columna FK es la **primera columna** de algún índice. 16 llevan `index=True` (`ix_*`); `cliente.usuario_id` queda cubierta por su `uq_cliente_usuario_id` y `item_orden.orden_id` por `uq_item_orden_orden_id_repuesto_id`. `asignacion_rol.usuario_id` **sí** lleva índice propio: el parcial no cubre las filas revocadas. Un test recorre `pg_constraint` (contype `f`) y `pg_index` y falla si alguna FK no encabeza un índice. **[Agente]** | Consigna p. 6: «cada clave foránea lleva un índice». Una restricción UNIQUE **es** un índice en Postgres; duplicarlo sólo cuesta escrituras. El test hace la regla verificable, no una promesa. | `index=True` en las 18 sin excepción: dos índices redundantes. |
| 9 | FK inferidas (SU-02) | FK sin navegación ORM: `historial_estado_orden.usuario_id`, `movimiento_stock.usuario_id`, `historial_precio_repuesto.usuario_id` → `usuario.id`; `movimiento_stock.orden_id` → `orden_trabajo.id`; `asignacion_rol.otorgada_por` → `usuario.id` (DA-08). `desde_estado`/`hasta_estado` → `estado_orden.codigo` (explícitas en el PDF). | SU-02 / DA-08. | Dejarlas sin FK: una fila de historial apuntando a un usuario inexistente. |
| 10 | `ON DELETE` | **[Agente]** Ninguna acción (`NO ACTION`, el default) en todas las FK, también en las composiciones. | Nada se borra físicamente: vehículo y repuesto tienen borrado lógico, las órdenes no tienen DELETE y el historial es de sólo agregado (un `CASCADE` hacia `historial_estado_orden` chocaría con el disparador). El `seed.py` vacía con `TRUNCATE … CASCADE` (DA-31), que no depende de `ON DELETE`. | `ON DELETE CASCADE` en `item_orden`/`historial_estado_orden` por ser composición: no hay ningún DELETE de orden que lo use. |
| 11 | Navegación ORM | Los dos extremos de cada relación de la Figura 1: `Usuario.roles` ↔ `AsignacionRol.usuario`; `Usuario.cliente` (**objeto**, `uselist=False`) ↔ `Cliente.usuario`; `Cliente.vehiculos` ↔ `Vehiculo.cliente`; `Vehiculo.ordenes` ↔ `OrdenTrabajo.vehiculo`; `Usuario.ordenes_asignadas` ↔ `OrdenTrabajo.mecanico`; `EstadoOrden.ordenes` ↔ `OrdenTrabajo.estado_orden`; `OrdenTrabajo.items` ↔ `ItemOrden.orden`; `OrdenTrabajo.historial` ↔ `HistorialEstadoOrden.orden`; `Repuesto.items` ↔ `ItemOrden.repuesto`; `Repuesto.movimientos` ↔ `MovimientoStock.repuesto`; `Repuesto.historial_precios` ↔ `HistorialPrecio.repuesto`. **[Agente]** Las FK inferidas (9) no llevan navegación: si un change la necesita, la agrega (una relación no cambia el esquema ni pide migración). | Ej. 2: «en los dos extremos de cada relación que se lea»; declarar todas las de la figura evita adivinar cuáles leerá cada change. La relación del catálogo se llama `estado_orden` porque `estado` ya es la columna. | Declarar sólo las que hoy se leen: CH-03 no tiene lecturas todavía. |
| 11a | Ambigüedad `Usuario` ↔ `AsignacionRol` | `AsignacionRol` tiene **dos** FK a `usuario` (`usuario_id`, `otorgada_por`): `Usuario.roles` y `AsignacionRol.usuario` declaran `foreign_keys` explícito. Igual `OrdenTrabajo.mecanico`. | Sin eso SQLAlchemy falla al configurar los mappers (`AmbiguousForeignKeysError`). | — |
| 11b | Estrategia de carga | **[Agente]** `lazy="raise"` en **todas** las relaciones. | Regla dura «nunca carga perezosa ni N+1»: un acceso a una relación no precargada falla al instante y con un mensaje claro, en vez de un `MissingGreenlet` en async o una consulta escondida. Obliga a que el repositorio declare `selectinload`/`joinedload`. | `lazy="raise_on_sql"`: permite resolver muchos-a-uno desde el identity map; menos predecible. `lazy="selectin"` por defecto: precarga todo siempre (la «precarga» quedaría en el modelo, no en el repositorio). |
| 11c | `cascade` | Default de SQLAlchemy (`save-update, merge`), sin `delete`/`delete-orphan`. | Agregar la orden con sus ítems y su historial en un solo `add` alcanza; un `delete-orphan` emitiría `DELETE` contra el historial. | — |
| 12 | `estado_orden` «catalog» | Modelo `EstadoOrden` con `codigo` `str` PK, `descripcion`, `posicion` (`uq_estado_orden_posicion`), `es_final`. Sin `id`. La migración la crea **vacía**; sin `bulk_insert`. Su repositorio de sólo lectura que no hereda de `BaseRepository` es de CH-09 (`/estados`). | PDF p. 7 y DD-02. CH-02 (2b) ya dejó dicho que el catálogo no hereda porque no tiene `id`. | Cargar las 4 filas en la migración: el PDF dice «sus filas son datos, y las carga `seed.py`». |
| 13 | ¿Qué importa `env.py`? | Cuatro imports explícitos (`import app.modules.<módulo>.models  # noqa: F401`), uno por módulo, junto a `target_metadata = SQLModel.metadata`. `env.py` sigue sin importar `main` ni la app (CH-01, 6b). | Visible y sin efectos colaterales; un test verifica que `SQLModel.metadata.tables` tiene exactamente las 13. | Un `app/modules/__init__.py` que importe todo: magia escondida. |
| 14 | `script.py.mako` | **[Agente]** Se agrega `import sqlmodel` a la plantilla **antes** de autogenerar. | La migración autogenerada escribe `sqlmodel.sql.sqltypes.AutoString()` para cada `str`; sin el import, `upgrade` falla con `NameError`. | `render_item` en `env.py` para traducir `AutoString` a `sa.String`: más código para lo mismo. |
| 15 | Nombres de las revisiones | **[Agente]** `--rev-id 0001` y `--rev-id 0002`, slugs `esquema_inicial` y `disparador_solo_agregado`; `file_template` por defecto. | La consigna no los fija (CH-01, 6f); con ids legibles el orden se ve en la carpeta y en `alembic_version`. | Hash aleatorio de Alembic. |
| 16 | Migración 1: ¿contra qué base se autogenera? | Contra la base **de desarrollo** (`taller_mecanico`), después de verificar que no tiene tablas (`\dt` vacío). Al leerla se comprueba que no menciona ninguna tabla `prueba_*` y que no tiene `drop_table`. | Si se generara contra `_test` con tablas `prueba_*` olvidadas (corrida de CH-02 interrumpida), Alembic propondría borrarlas (nota 7d de CH-02). | Autogenerar contra `_test`. |
| 16a | Lectura previa (Ej. 2: «cada migración se lee antes de aplicarla y lleva un comentario que lo diga») | El apply **frena** después de autogenerar y le muestra la migración a la alumna; con su visto bueno se agrega al docstring un bloque «Leída antes de aplicarla (fecha, por quién) — se revisó: 13 tablas, catálogo vacío, 3 índices parciales con `postgresql_where`, CHECK nombrados, FK con índice, sin `prueba_*`». La migración 2 lleva el mismo bloque. | El comentario tiene que ser verdad; governance ALTO de CH-03. | Escribir el comentario de antemano. |
| 17 | Migración 2: forma del disparador | Una función `rechazar_cambio_solo_agregado()` (plpgsql) y **tres** disparadores `BEFORE UPDATE OR DELETE … FOR EACH ROW`, uno por tabla, llamados `tg_<tabla>_solo_agregado`. La función hace `RAISE EXCEPTION 'La tabla % es de sólo agregado: no se permite %', TG_TABLE_NAME, TG_OP USING ERRCODE = 'restrict_violation'`. `downgrade` borra los tres disparadores y la función (`DROP … IF EXISTS` no: si falta, el downgrade debe fallar). SQL literal con `op.execute`, sin datos del usuario. | RN-15, DD-10 y DA-31 (de fila, para que `TRUNCATE` del seed pase). **[Agente]** El `ERRCODE` 23001 (`restrict_violation`) es de la clase 23: asyncpg lo levanta como violación de integridad y SQLAlchemy como `IntegrityError`, así que si un bug de la app llegara a hacer `UPDATE` saldría por la traducción de CH-02 (409 genérico + log), nunca un 500 con el texto de la base (RN-18). En `psql` se ve el mensaje propio. | `ERRCODE` por defecto (`P0001` `raise_exception`): llegaría como `DBAPIError` no traducido → 500. Un disparador de sentencia: no ve las filas y no cambia nada para C-14. Una función por tabla: triplica el código. |
| 18 | `test/solo_agregado.sql` (C-14) | **[Alumna, corrección del 2026-10-28]** Al principio, un bloque verifica que las tres tablas tienen al menos una fila y, si alguna está vacía, corta con «Corré python seed.py primero» (sin ejecutar ninguna de las siete sentencias). La captura de `psql` se hace en **CH-04**, después del seed; en CH-03 el disparador se prueba sólo con pytest, insertando filas propias. Supone el seed (consigna: «antes de cada archivo se corre `python seed.py`»), y apunta a filas con `WHERE id = (SELECT min(id) FROM <tabla>)`, no a ids fijos. Seis sentencias (`UPDATE` y `DELETE` por tabla) y un `INSERT INTO orden_trabajo` con `estado = 'INEXISTENTE'` sobre un vehículo existente. Cada sentencia con la respuesta esperada en un comentario (`ERROR:  La tabla movimiento_stock es de sólo agregado: no se permite UPDATE`; `ERROR: … viola la llave foránea «fk_orden_trabajo_estado_estado_orden»`). Sin `ON_ERROR_STOP`, para que `psql -f` muestre los siete errores. **[Agente]** | Un disparador de fila **no se dispara** si el `WHERE` no encuentra filas: un `UPDATE … WHERE id = 99` «pasaría» sin error y la evidencia mentiría. Con `min(id)` el archivo vale con cualquier dato y la suite pytest puede ejecutarlo (X1). La captura de `psql` se arma en CH-11. | Ids fijos (`WHERE id = 1`): dependen de que las secuencias estén reiniciadas. |
| 19 | ¿Cómo se prueba contra la base? | Fixture de sesión `esquema_al_dia`: corre `alembic upgrade head` por **subproceso** contra `_test` (guarda antes, como `test_a2` de CH-01, nota 6d). Cada test de restricciones usa una conexión con una transacción externa que se **revierte** al final, y cada rechazo esperado va dentro de un `SAVEPOINT` (`begin_nested`). **[Agente]** | No deja filas, no necesita `TRUNCATE` ni choca con el disparador. Sin mocks de la base (regla dura). | `TRUNCATE` entre tests (funciona, pero cada test de disparador dejaría filas hasta la limpieza); usar el seed (no existe hasta CH-04). |
| 19a | Ciclo `upgrade → downgrade base → upgrade` | Un test, por subproceso contra `_test`, que termina en `head` (para no dejar a los demás tests sin esquema). Verifica en cada paso la lista de tablas de `information_schema` y que la función del disparador existe/no existe. | Ej. 2 y condición excluyente de los criterios («no crea su esquema con `alembic upgrade head` sobre una base vacía»). Las tablas `prueba_*` no se ven afectadas: no tienen FK a las del dominio. | — |
| 20 | Modelos y migraciones coinciden (nota 7d de CH-02) | **[Agente]** Test que, después de `upgrade head`, compara `SQLModel.metadata` (con los mismos cuatro imports que `env.py`) contra la base con `alembic.autogenerate.compare_metadata` sobre una conexión sincrónica (`run_sync`), e **ignora explícitamente** sólo las diferencias `remove_table` de tablas `prueba_*`, con un comentario que cita 7d. La lista de diferencias que queda debe estar vacía. | Prueba que nadie tocó un `models.py` sin migrar. El filtro vive en el test, no en `env.py`: la configuración de producción no conoce los nombres de la suite, y el arnés de CH-02 (tablas de sesión) no se toca. Límite declarado: autogenerate **no** compara CHECK ni el `WHERE` de un índice parcial; esos los cubren S7 y los tests de K/P. | `alembic check` por subproceso: falla por las `prueba_*` vivas en la sesión. `include_object` en `env.py` que ignore `prueba_*`: mete nombres de test en producción. Cambiar el scope de las tablas `prueba_*` a módulo: toca un arnés ya cerrado. |
| 21 | «Ningún `create_all`» | Test estático: ningún `.py` del repo (fuera de `.venv`) contiene `create_all`. | Requisito no funcional «Esquema»; CH-02 ya no lo usa. | — |
| 22 | Contrato de datos en Python | Round-trip verificado: el dinero vuelve como `Decimal('8500.00')` (nunca `float`), las fechas vuelven con zona. | Regla dura de dinero y fechas. | — |
| 23 | `usuario.email` y mayúsculas | `UNIQUE` común sobre la columna, como dice el PDF. La normalización (si la hay) es del servicio de CH-05: «No especificado en la consigna». | No inventar: `email UNIQUE` es textual. | Índice único sobre `lower(email)`: cambia una restricción del PDF. |

## Nombres de restricción (contrato para los UoW de cada módulo)

Los que la convención (3) o el nombre explícito producen. Los mapas restricción → mensaje de CH-05 a CH-10 se escriben contra esta lista; el test S7 la verifica.

| Tabla | UNIQUE / índice único | CHECK | FK (las 18) |
|---|---|---|---|
| `usuario` | `uq_usuario_email` | — | — |
| `asignacion_rol` | `uq_asignacion_rol_abierta` (parcial: `usuario_id, rol WHERE revocada_en IS NULL`) | `ck_asignacion_rol_rol` | `fk_asignacion_rol_usuario_id_usuario`, `fk_asignacion_rol_otorgada_por_usuario` |
| `intento_acceso` | — (índice `ix_intento_acceso_email_ip_cuando`) | — | — |
| `evento_seguridad` | — | — | — |
| `cliente` | `uq_cliente_usuario_id`, `uq_cliente_documento` | — | `fk_cliente_usuario_id_usuario` |
| `vehiculo` | `uq_vehiculo_patente_vigente` (parcial: `WHERE borrado_en IS NULL`) | `ck_vehiculo_anio` | `fk_vehiculo_cliente_id_cliente` |
| `repuesto` | `uq_repuesto_codigo_vigente` (parcial: `WHERE borrado_en IS NULL`) | `ck_repuesto_precio_positivo`, `ck_repuesto_stock_no_negativo` | — |
| `estado_orden` | `uq_estado_orden_posicion` | — | — |
| `orden_trabajo` | — | `ck_orden_trabajo_total_no_negativo` | `fk_orden_trabajo_vehiculo_id_vehiculo`, `fk_orden_trabajo_mecanico_id_usuario`, `fk_orden_trabajo_estado_estado_orden` |
| `item_orden` | `uq_item_orden_orden_id_repuesto_id` | `ck_item_orden_cantidad_positiva`, `ck_item_orden_precio_unitario_positivo` | `fk_item_orden_orden_id_orden_trabajo`, `fk_item_orden_repuesto_id_repuesto` |
| `historial_estado_orden` | — | — | `fk_historial_estado_orden_orden_id_orden_trabajo`, `fk_historial_estado_orden_desde_estado_estado_orden`, `fk_historial_estado_orden_hasta_estado_estado_orden`, `fk_historial_estado_orden_usuario_id_usuario` |
| `movimiento_stock` | — | `ck_movimiento_stock_cantidad_distinta_de_cero` | `fk_movimiento_stock_repuesto_id_repuesto`, `fk_movimiento_stock_orden_id_orden_trabajo`, `fk_movimiento_stock_usuario_id_usuario` |
| `historial_precio_repuesto` | — | `ck_historial_precio_repuesto_precio_nuevo_positivo`, `ck_historial_precio_repuesto_precio_cambia` | `fk_historial_precio_repuesto_repuesto_id_repuesto`, `fk_historial_precio_repuesto_usuario_id_usuario` |

CHECK textuales del PDF: `rol IN (…)`, `anio BETWEEN 1950 AND 2100`, `precio > 0`, `stock >= 0`, `total >= 0`, `cantidad > 0` (ítem), `precio_unitario > 0`, `cantidad <> 0` (movimiento), `precio_nuevo > 0`, `precio_nuevo <> precio_anterior`.

## Refinamientos respecto de CHANGES.md

Anotarlos en el proposal; no renombran ni reordenan changes.

- **R1**: el enum espejo de los estados se llama `CodigoEstado`, no `EstadoOrden` (choca con la clase del catálogo en el mismo módulo). Afecta a CH-09 (schemas y servicio de órdenes, `GET /ordenes?estado=`) y a CH-04 (el seed carga el catálogo desde ese enum).
- **R2**: la convención de nombres vive en `app/core/database.py` (no hay archivo nuevo en el core).
- **R3**: `migrations/script.py.mako` gana `import sqlmodel` (14).

## Escenarios de prueba

### M: migraciones

| # | Tipo | Escenario |
|---|---|---|
| M1 | feliz | `alembic upgrade head` sobre `_test` sin tablas del dominio → existen las 13 tablas y `alembic_version` = `0002`. |
| M2 | feliz | `downgrade base` → no queda ninguna de las 13 tablas ni la función `rechazar_cambio_solo_agregado`; las `prueba_*` (si existen) siguen. Otra vez `upgrade head` → las 13 de nuevo. |
| M3 | borde | Después de `upgrade head`, `estado_orden` tiene **0** filas (catálogo vacío). |
| M4 | feliz | `compare_metadata` entre `SQLModel.metadata` y la base no devuelve diferencias (ignorando sólo `remove_table` de `prueba_*`). |
| M5 | estático | Ninguna migración menciona `prueba_`; cada una tiene en el docstring el bloque «Leída antes de aplicarla». |
| M6 | estático | Ningún `.py` del repo (fuera de `.venv`) contiene `create_all`. |
| M7 | feliz | Con los imports de `env.py`, `SQLModel.metadata.tables` tiene exactamente las 13 tablas y ninguna `prueba_*`. |

### S: forma del esquema (leída de `information_schema`/`pg_catalog`)

| # | Tipo | Escenario |
|---|---|---|
| S1 | feliz | Cada tabla tiene **exactamente** las columnas de la consigna (pp. 5-6), con esos nombres. |
| S2 | borde | `usuario` no tiene columna `rol`. |
| S3 | feliz | Sólo las columnas «(nulo)» admiten NULL (lista de 7a); el resto `NOT NULL`. |
| S4 | feliz | `precio`, `precio_unitario`, `precio_anterior`, `precio_nuevo` son `numeric(10,2)`; `total`, `numeric(12,2)`; toda columna de fecha es `timestamp with time zone`. |
| S5 | feliz | Las 18 FK existen, con su tabla y columna destino (incluidas `estado`/`desde_estado`/`hasta_estado` → `estado_orden.codigo`). |
| S6 | feliz | Toda columna FK encabeza algún índice (8). |
| S7 | feliz | El conjunto de nombres de restricción e índices únicos es exactamente el de la tabla «Nombres de restricción»; los tres parciales tienen su `WHERE … IS NULL`. |

### K: CHECK y UNIQUE (cada rechazo, `IntegrityError` con el nombre esperado en `SAVEPOINT`)

| # | Tipo | Escenario |
|---|---|---|
| K1 | error / borde | `repuesto.stock = -1` rechazado (`ck_repuesto_stock_no_negativo`); `0` aceptado. |
| K2 | error / borde | `repuesto.precio = 0` rechazado; `0.01` aceptado. |
| K3 | error / borde | `orden_trabajo.total = -0.01` rechazado; `0` aceptado. |
| K4 | error / borde | `item_orden.cantidad = 0` rechazado; `1` aceptado. `precio_unitario = 0` rechazado. |
| K5 | error / feliz | `movimiento_stock.cantidad = 0` rechazado; `+3` y `-3` aceptados (DD-13). |
| K6 | error / feliz | `historial_precio_repuesto` con `precio_nuevo = precio_anterior` rechazado (`ck_…_precio_cambia`); con precio que **baja** aceptado (RN-20); `precio_nuevo = 0` rechazado. |
| K7 | error / borde | `vehiculo.anio` 1949 y 2101 rechazados; 1950 y 2100 aceptados. |
| K8 | error | `asignacion_rol.rol = 'JEFE'` rechazado (`ck_asignacion_rol_rol`); los cuatro del enum aceptados. |
| K9 | error | `usuario.email` repetido → `uq_usuario_email`. |
| K10 | error / borde | `cliente.documento` repetido → `uq_cliente_documento`; `cliente.usuario_id` repetido → `uq_cliente_usuario_id`; dos clientes con `usuario_id NULL` aceptados. |
| K11 | error | `estado_orden.posicion` repetida → `uq_estado_orden_posicion`. |
| K12 | error | Mismo `(orden_id, repuesto_id)` dos veces → `uq_item_orden_orden_id_repuesto_id`. |
| K13 | error | Una columna `NOT NULL` en NULL (p. ej. `vehiculo.patente`) rechazada. |

### P: índices únicos parciales

| # | Tipo | Escenario |
|---|---|---|
| P1 | error | Dos vehículos vigentes con la misma patente → `uq_vehiculo_patente_vigente`. |
| P2 | feliz | Con el primero dado de baja (`borrado_en` con fecha), la misma patente para otro cliente se acepta (base de C-19). |
| P3 | borde | Dos vehículos dados de baja con la misma patente se aceptan. |
| P4 | error / feliz | Igual para `repuesto.codigo` (`uq_repuesto_codigo_vigente`). |
| P5 | error | Dos asignaciones abiertas del mismo `(usuario_id, rol)` → `uq_asignacion_rol_abierta` (RN-03). |
| P6 | feliz | Con la primera revocada, una nueva del mismo rol se acepta; el mismo usuario con **otro** rol abierto también. |

### F: claves foráneas

| # | Tipo | Escenario |
|---|---|---|
| F1 | error | Orden con `estado = 'INEXISTENTE'` → `fk_orden_trabajo_estado_estado_orden` (RN-19, C-14). |
| F2 | error | Historial con `hasta_estado` inexistente rechazado; con `desde_estado NULL` aceptado. |
| F3 | error | Orden con `vehiculo_id` inexistente rechazada. |

### D: disparador de sólo agregado

| # | Tipo | Escenario |
|---|---|---|
| D1 | feliz | `INSERT` en cada una de las tres tablas funciona. |
| D2 | error | `UPDATE` de una fila existente en cada tabla → error SQLSTATE `23001` con «La tabla <tabla> es de sólo agregado: no se permite UPDATE». (3 casos) |
| D3 | error | `DELETE` de una fila existente en cada tabla → igual, con `DELETE`. (3 casos) |
| D4 | borde | Un `UPDATE` que no encuentra filas no da error (por eso C-14 apunta a filas existentes, decisión 18). |
| D5 | borde | `TRUNCATE` de las tres tablas funciona (DA-31; lo usará `seed.py`). |
| D6 | borde | Desde SQLAlchemy, el `UPDATE` rechazado llega como `IntegrityError` (no `DBAPIError` genérico), así que la traducción de CH-02 lo convierte en `Conflicto`. |
| D7 | borde | Las tablas que **no** son de sólo agregado (`orden_trabajo`, `repuesto`) siguen aceptando `UPDATE`. |

### X: `test/solo_agregado.sql`

| # | Tipo | Escenario |
|---|---|---|
| X1 | feliz | Ejecutado sentencia por sentencia sobre `_test` con al menos una fila por tabla (transacción revertida): las seis primeras fallan con `23001` y la séptima con `23503` y `fk_orden_trabajo_estado_estado_orden`. |
| X2 | error | Con alguna de las tres tablas vacía, la verificación inicial del archivo corta con «Corré python seed.py primero» y no se ejecuta ninguna de las siete sentencias. |

### T: tipos y navegación

| # | Tipo | Escenario |
|---|---|---|
| T1 | feliz | Un `Repuesto` guardado y releído trae `precio` como `Decimal('8500.00')`, nunca `float`. |
| T2 | feliz | Una fecha guardada con zona vuelve con `tzinfo` (UTC). |
| T3 | feliz | Con `selectinload(Usuario.cliente)`, `usuario.cliente` es un `Cliente` (no una lista); con un usuario sin ficha, `None`. |
| T4 | error | Acceder a una relación **no** precargada de una entidad persistente lanza la excepción de `lazy="raise"`, sin consultar la base. |
| T5 | feliz | Los mappers configuran sin error (`configure_mappers()`): las relaciones con dos FK a `usuario` no son ambiguas. |
| T6 | feliz | Una orden agregada con dos ítems y una línea de historial en un solo `add` + `flush` deja las cuatro filas (cascade por defecto). |

## Pedidos para el propose

1. **Governance ALTO**: el design describe las dos migraciones (tablas, restricciones con sus nombres, función y disparadores, `downgrade`) y el propose **frena** para revisión antes de cualquier apply.
2. **Refinamientos** R1-R3 en el proposal.
3. En el **design**: la convención de nombres y la tabla «Nombres de restricción» como contrato para CH-05 a CH-10 (3, 3a, 3b); tipos, nulabilidad y `server_default` (7, 7a, 7b); la regla del índice por FK (8); navegación, `foreign_keys`, `lazy="raise"` y `cascade` (11, 11a-11c); el catálogo (12); la forma del disparador y su `ERRCODE` (17), con el diagrama `UPDATE` → disparador → `23001` → `IntegrityError` → `Conflicto` → 409; el arnés de pruebas (19, 19a, 20) y por qué el `.sql` usa `min(id)` (18).
4. En las **specs**: los escenarios de arriba (M, S, K, P, F, D, X, T), agrupados por requisito (migraciones, esquema, restricciones, índices parciales, catálogo con FK, sólo agregado, C-14, navegación). La spec `migraciones` de CH-01 gana los requisitos del ciclo y de la coincidencia modelos-migraciones.
5. Marcar como **«No especificado en la consigna»**: los nombres de restricción, `server_default now()`, `VARCHAR` para `ip`, el `ERRCODE` del disparador, el texto de su mensaje, los nombres de las revisiones y el nombre `CodigoEstado`.
6. **Verificar en el apply** (contra las versiones instaladas): cómo declara SQLModel 0.0.48 un `str` NOT NULL con `server_default` y tipo `Optional` en Python; cómo poner una columna `rol` tipada `Rol` como `VARCHAR` + `CHECK` (sin `sa.Enum` nativo); que SQLAlchemy 2.1 sigue generando `SERIAL` (o `IDENTITY`) para el `id` y que `TRUNCATE … RESTART IDENTITY` lo reinicia igual; que autogenerate renderiza `postgresql_where` y los nombres `op.f(...)`; que asyncpg trae `constraint_name` para un índice único **parcial** (es un índice, no una restricción); que `23001` llega como `IntegrityError` con el dialecto asyncpg.
7. **Acciones con efectos que el apply debe pedir antes de correr**: `alembic revision --autogenerate` contra la base de desarrollo (y la verificación previa de que está vacía), **frenar para la lectura de la migración 1** y luego de la 2 antes de cualquier `upgrade`, `alembic upgrade head` sobre la base de desarrollo, y la suite contra `taller_mecanico_test` (que hace `upgrade`/`downgrade`).
8. **Al cerrar el change** (archive): marcar CH-03 `[x]` en `CHANGES.md` y anotar R1 donde `CHANGES.md` dice «Enums espejo `Rol` y `EstadoOrden`».
9. **Notas para los changes siguientes**:
   - **CH-04** (`seed.py`): carga el catálogo desde `CodigoEstado` y un test verifica que las filas del catálogo coinciden con el enum (DD-02: «el enum y el catálogo tienen que coincidir»); vacía con `TRUNCATE … RESTART IDENTITY CASCADE` (D5 lo garantiza). **[Alumna]** La captura de `psql -f test/solo_agregado.sql` (C-14) se hace en CH-04, después del seed, y se guarda en `docs/evidencias/` (DA-30).
   - **Granularidad del disparador**: el PDF no fija «de fila» (sólo «rechaza cualquier UPDATE o DELETE … venga de donde venga»); «de fila» viene de DA-31. El design menciona la alternativa de sentencia (`FOR EACH STATEMENT`, que rechazaría incluso un `UPDATE` sin filas) sin adoptarla.
   - **CH-05 a CH-10**: los mapas restricción → mensaje se escriben contra la tabla «Nombres de restricción»; ninguna relación se lee sin `selectinload`/`joinedload` en el repositorio (`lazy="raise"` lo hace fallar); una navegación nueva sobre una FK inferida (9) se agrega en el modelo sin migración.
   - **CH-11**: verifica que la captura de C-14 hecha en CH-04 sigue vigente.
