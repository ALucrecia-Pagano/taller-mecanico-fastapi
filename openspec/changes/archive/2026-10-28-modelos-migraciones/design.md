# Design — CH-03 `modelos-migraciones`

## Context

CH-01 dejó:
- `migrations/env.py`, con la plantilla asincrónica, `target_metadata = SQLModel.metadata` todavía sin modelos y la URL tomada de `get_settings()` con `NullPool`;
- `alembic.ini` sin `sqlalchemy.url`;
- el patrón de correr Alembic por subproceso contra `_test` con la guarda (`test_a2`).

CH-02 dejó:
- `UnitOfWork`, que traduce un `IntegrityError` a `Conflicto` buscando el **nombre de la restricción** (`error.orig.__cause__.constraint_name`) en el mapa de cada módulo;
- el arnés de tablas `prueba_*`, de sesión, con `registry` propio y que nunca entra en `SQLModel.metadata`.

Todavía no hay modelos, migraciones ni `seed.py`.

Motivación y alcance: ver `proposal.md`. Requisitos y escenarios: ver `specs/`. Todas las decisiones salen del explore ([docs/evidencias/explore-CH-03.md](../../../docs/evidencias/explore-CH-03.md)); el número entre paréntesis remite a su tabla.

Versiones instaladas: SQLModel 0.0.48, SQLAlchemy 2.1.6, Alembic 1.20.1, asyncpg 0.32.0.

## Goals / Non-Goals

**Goals:**
- Que el esquema completo salga de dos migraciones reproducibles y legibles.
- Que cada restricción tenga un nombre fijo que los changes de módulo puedan mapear a un mensaje 409.
- Que la navegación ORM no pueda disparar consultas implícitas.
- Que el sólo agregado esté garantizado por la base y no por la aplicación.

**Non-Goals:**
- Carga de datos: el catálogo queda vacío; lo carga CH-04.
- Repositorios, UoW de módulo, schemas y endpoints.
- Un segundo mecanismo de sólo agregado por permisos del rol de base: el Ejercicio 7 dice que no se pide.
- Bloquear `TRUNCATE` (DA-31).

## Decisions

### D1. Archivos (1, 13, 14)

```
app/core/database.py                    (mod) CONVENCION_DE_NOMBRES aplicada a SQLModel.metadata
app/modules/usuarios/{__init__,models}.py     Rol, Usuario, AsignacionRol, IntentoAcceso, EventoSeguridad
app/modules/clientes/{__init__,models}.py     Cliente, Vehiculo
app/modules/repuestos/{__init__,models}.py    Repuesto, MovimientoStock, HistorialPrecio
app/modules/ordenes/{__init__,models}.py      CodigoEstado, EstadoOrden, OrdenTrabajo, ItemOrden, HistorialEstadoOrden
migrations/env.py                       (mod) import de los 4 models.py
migrations/script.py.mako               (mod) import sqlmodel
migrations/versions/0001_esquema_inicial.py
migrations/versions/0002_disparador_solo_agregado.py
test/solo_agregado.sql
test/pytest/conftest.py                 (mod) fixtures esquema_al_dia y conexion_revertida
test/pytest/test_modelos.py             M7, T5 y S1/S3/S7 leídos de la metadata (sin base)
test/pytest/test_migraciones.py         (mod) M1-M6
test/pytest/test_esquema.py             S1-S8
test/pytest/test_restricciones.py       K1-K13, P1-P6, F1-F3
test/pytest/test_solo_agregado.py       D1-D7, X1-X2
test/pytest/test_navegacion.py          T1-T6
```

Las relaciones cruzan módulos: `Cliente.usuario` apunta a `usuarios`, y `OrdenTrabajo.vehiculo` a `clientes`. Por eso se declaran con el nombre de la clase como string. Los imports que necesita el tipado van bajo `TYPE_CHECKING`, para evitar ciclos. SQLAlchemy resuelve los nombres al configurar los mappers. Por eso `env.py` y los tests importan **los cuatro** módulos antes de usarlos (T5).

### D2. Convención de nombres (3, 3a, 3b)

En `app/core/database.py`:

```python
CONVENCION_DE_NOMBRES = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
}
SQLModel.metadata.naming_convention = CONVENCION_DE_NOMBRES
```

- La convención tiene que estar puesta **antes** de declarar cualquier tabla, porque SQLAlchemy la aplica al adjuntar la restricción. Cada `models.py` empieza con `import app.core.database  # noqa: F401`, con un comentario que lo explica. S7 detecta cualquier olvido.
- Los CHECK llevan un nombre corto (`CheckConstraint("stock >= 0", name="stock_no_negativo")`) y la convención le antepone `ck_<tabla>_`.
- Los índices parciales llevan nombre explícito. Con nombre, la convención `ix` no se aplica.
- Nunca `unique=True` junto con `index=True` en una columna: eso crea un índice único `ix_*` en lugar de la restricción `uq_*`.
- Todos los nombres tienen como máximo 63 caracteres. El más largo es `fk_historial_estado_orden_desde_estado_estado_orden`, con 51.

#### Nombres de restricción (contrato para los UoW de CH-05 a CH-10)

| Tabla | UNIQUE / índice único | CHECK (expresión) | FK |
|---|---|---|---|
| `usuario` | `uq_usuario_email` | — | — |
| `asignacion_rol` | `uq_asignacion_rol_abierta` = índice único (`usuario_id`, `rol`) `WHERE revocada_en IS NULL` | `ck_asignacion_rol_rol` (`rol IN ('ADMIN','RECEPCION','MECANICO','CLIENTE')`) | `fk_asignacion_rol_usuario_id_usuario`, `fk_asignacion_rol_otorgada_por_usuario` |
| `intento_acceso` | — (índice `ix_intento_acceso_email_ip_cuando`) | — | — |
| `evento_seguridad` | — | — | — |
| `cliente` | `uq_cliente_usuario_id`, `uq_cliente_documento` | — | `fk_cliente_usuario_id_usuario` |
| `vehiculo` | `uq_vehiculo_patente_vigente` = índice único (`patente`) `WHERE borrado_en IS NULL` | `ck_vehiculo_anio` (`anio BETWEEN 1950 AND 2100`) | `fk_vehiculo_cliente_id_cliente` |
| `repuesto` | `uq_repuesto_codigo_vigente` = índice único (`codigo`) `WHERE borrado_en IS NULL` | `ck_repuesto_precio_positivo` (`precio > 0`), `ck_repuesto_stock_no_negativo` (`stock >= 0`) | — |
| `estado_orden` | `uq_estado_orden_posicion` | — | — |
| `orden_trabajo` | — | `ck_orden_trabajo_total_no_negativo` (`total >= 0`) | `fk_orden_trabajo_vehiculo_id_vehiculo`, `fk_orden_trabajo_mecanico_id_usuario`, `fk_orden_trabajo_estado_estado_orden` |
| `item_orden` | `uq_item_orden_orden_id_repuesto_id` | `ck_item_orden_cantidad_positiva` (`cantidad > 0`), `ck_item_orden_precio_unitario_positivo` (`precio_unitario > 0`) | `fk_item_orden_orden_id_orden_trabajo`, `fk_item_orden_repuesto_id_repuesto` |
| `historial_estado_orden` | — | — | `fk_historial_estado_orden_orden_id_orden_trabajo`, `fk_historial_estado_orden_desde_estado_estado_orden`, `fk_historial_estado_orden_hasta_estado_estado_orden`, `fk_historial_estado_orden_usuario_id_usuario` |
| `movimiento_stock` | — | `ck_movimiento_stock_cantidad_distinta_de_cero` (`cantidad <> 0`) | `fk_movimiento_stock_repuesto_id_repuesto`, `fk_movimiento_stock_orden_id_orden_trabajo`, `fk_movimiento_stock_usuario_id_usuario` |
| `historial_precio_repuesto` | — | `ck_historial_precio_repuesto_precio_nuevo_positivo` (`precio_nuevo > 0`), `ck_historial_precio_repuesto_precio_cambia` (`precio_nuevo <> precio_anterior`) | `fk_historial_precio_repuesto_repuesto_id_repuesto`, `fk_historial_precio_repuesto_usuario_id_usuario` |

Además, las PK se llaman `pk_<tabla>`.

### D3. Tipos, nulabilidad y defaults (2, 4, 6, 7, 7a, 7b)

| Concepto | Declaración | En la base |
|---|---|---|
| `id` | `int \| None = Field(default=None, primary_key=True)` | `INTEGER` autoincremental (V3) |
| Texto | `str` | `VARCHAR` sin largo (`AutoString`) |
| `rol` | tipado `Rol` (`StrEnum`) con `sa_type` de texto, nunca `sa.Enum` nativo, más un `CheckConstraint` cuya lista se arma desde `Rol` (V2) | `VARCHAR` + `ck_asignacion_rol_rol` |
| `estado`, `desde_estado`, `hasta_estado` | `str` con `foreign_key="estado_orden.codigo"` | `VARCHAR` + FK, sin CHECK |
| Dinero | `Decimal = Field(max_digits=10, decimal_places=2)` (`total`: 12,2) | `NUMERIC(10,2)` / `NUMERIC(12,2)` |
| Enteros | `int` (`stock`, `cantidad`, `anio`, `posicion`) | `INTEGER` |
| Booleanos | `bool` con default de Python (`activo=True`, `debe_cambiar_password=False`), sin `server_default` | `BOOLEAN NOT NULL` |
| Fechas | `datetime` con `sa_type=DateTime(timezone=True)` | `timestamptz` |
| Fechas de evento (7b) | además `sa_column_kwargs={"server_default": text("now()")}` y `nullable=False`; en Python `datetime \| None = None` (V1) | `timestamptz NOT NULL DEFAULT now()` |
| `ip` | `str` | `VARCHAR` (no `INET`) |

- Las columnas que admiten NULL son exactamente las diez de la spec `modelo-de-datos` (`Optional` y `nullable=True`). Todas las demás son `NOT NULL`, incluidos los `Optional` de Python que existen sólo para que la base complete el valor (`id` y las fechas de evento).
- Enums:
  - `Rol(StrEnum)`: `ADMIN`, `RECEPCION`, `MECANICO`, `CLIENTE`, en `usuarios/models.py`.
  - `CodigoEstado(StrEnum)`: `PENDIENTE`, `EN_REPARACION`, `TERMINADA`, `CANCELADA`, en `ordenes/models.py` (R1). En CH-03 no lo usa ninguna columna; CH-04 lo usa para cargar el catálogo y CH-09 como contrato.

### D4. Índice por FK (8)

Regla: toda columna FK es la **primera** columna de algún índice.
- 16 FK llevan `index=True` y la convención las nombra `ix_<tabla>_<columna>`.
- `cliente.usuario_id` queda cubierta por `uq_cliente_usuario_id`.
- `item_orden.orden_id` queda cubierta por `uq_item_orden_orden_id_repuesto_id`.
- `asignacion_rol.usuario_id` lleva índice propio aunque encabeza el índice parcial: el parcial no cubre las filas revocadas.

S6 lo verifica leyendo `pg_constraint` (`contype = 'f'`) y `pg_index` (`indkey[0]`).

### D5. Relaciones (11, 11a-11c)

| Extremo «uno» | Atributo | Extremo «muchos» / otro | Atributo | Notas |
|---|---|---|---|---|
| `Usuario` | `roles` | `AsignacionRol` | `usuario` | `foreign_keys=[AsignacionRol.usuario_id]` en los dos lados |
| `Usuario` | `cliente` (`uselist=False`) | `Cliente` | `usuario` | uno a uno opcional |
| `Cliente` | `vehiculos` | `Vehiculo` | `cliente` | |
| `Vehiculo` | `ordenes` | `OrdenTrabajo` | `vehiculo` | |
| `Usuario` | `ordenes_asignadas` | `OrdenTrabajo` | `mecanico` | `foreign_keys=[OrdenTrabajo.mecanico_id]` |
| `EstadoOrden` | `ordenes` | `OrdenTrabajo` | `estado_orden` | `estado` ya es la columna |
| `OrdenTrabajo` | `items` | `ItemOrden` | `orden` | composición |
| `OrdenTrabajo` | `historial` | `HistorialEstadoOrden` | `orden` | composición |
| `Repuesto` | `items` | `ItemOrden` | `repuesto` | |
| `Repuesto` | `movimientos` | `MovimientoStock` | `repuesto` | |
| `Repuesto` | `historial_precios` | `HistorialPrecio` | `repuesto` | |

- Todas las relaciones llevan `sa_relationship_kwargs={"lazy": "raise", ...}`. Un acceso sin precarga lanza `InvalidRequestError` al instante (T4). El repositorio de cada change declara `selectinload`/`joinedload`.
- `cascade` queda en el default (`save-update, merge`): sin `delete` ni `delete-orphan`. Con eso alcanza para el alta conjunta de T6.
- Todas las FK quedan en `ON DELETE NO ACTION` (10).
- Las FK inferidas (usuario del historial, `movimiento_stock.orden_id`, `otorgada_por`) no llevan navegación (9). Agregarla después no requiere migración.

### D6. Migración `0001_esquema_inicial` (15, 16, 16a)

**Cómo se genera** (tarea con [PERMISO]):
1. Se verifica que `taller_mecanico` (la base de desarrollo) no tiene tablas (`\dt` vacío, o una consulta a `information_schema.tables` del esquema `public`).
2. Se corre `alembic revision --autogenerate --rev-id 0001 -m "esquema inicial"` con `POSTGRES_DB=taller_mecanico`.
3. El apply **frena** y le muestra el archivo a la alumna, que lo lee antes de cualquier `upgrade`.

**Qué tiene que contener** (lista de lectura, también para la alumna):
- `op.create_table` de las 13 tablas, en orden de dependencias:
  1. `usuario`, `estado_orden`, `intento_acceso`, `evento_seguridad`, `repuesto`;
  2. `asignacion_rol`, `cliente`;
  3. `vehiculo`;
  4. `orden_trabajo`;
  5. `item_orden`, `historial_estado_orden`, `movimiento_stock`, `historial_precio_repuesto`.
- En cada tabla:
  - PK `pk_<tabla>`;
  - `nullable=False` salvo las diez;
  - `sa.Numeric(precision=10, scale=2)` / `(12, 2)`;
  - `sa.DateTime(timezone=True)`;
  - `server_default=sa.text('now()')` en las siete fechas de evento;
  - `sqlmodel.sql.sqltypes.AutoString()` en los textos (por eso el `import sqlmodel` de la plantilla).
- `sa.CheckConstraint(..., name=op.f('ck_...'))` con las diez expresiones de D2; la de `rol` con los cuatro valores.
- `sa.ForeignKeyConstraint(..., name=op.f('fk_...'))` con las 18 FK y **ningún** `ondelete`.
- `sa.UniqueConstraint(..., name=op.f('uq_...'))`: `usuario.email`, `cliente.usuario_id`, `cliente.documento`, `estado_orden.posicion` e `item_orden(orden_id, repuesto_id)`.
- `op.create_index`:
  - los 16 `ix_*` de las FK;
  - `ix_intento_acceso_email_ip_cuando`;
  - los tres únicos parciales con `unique=True` y `postgresql_where=sa.text('revocada_en IS NULL')` / `'borrado_en IS NULL'`.
- **Ningún** `op.bulk_insert`: el catálogo queda vacío.
- **Ninguna** mención de `prueba_` ni `drop_table` en `upgrade()`. Ningún `sa.Enum` ni `CREATE TYPE`.
- `downgrade()` con `drop_index` y `drop_table` en orden inverso.

**Ajustes a mano permitidos después de leerla**: sólo de forma, sin cambiar el esquema. Por ejemplo, ordenar imports o agregar el docstring. Si algo del esquema está mal, se corrige el **modelo** y se vuelve a autogenerar, para que modelo y migración no se separen (M4).

**Comentario obligatorio** (docstring), escrito **después** de que la alumna la lee:

```
Leída antes de aplicarla: <fecha>, por Amanda.
Revisado: 13 tablas, catálogo estado_orden vacío, 3 índices únicos parciales con
postgresql_where, CHECK y FK con nombres de la convención, índice en cada FK,
sin tablas prueba_* ni tipos ENUM.
```

### D7. Migración `0002_disparador_solo_agregado` (17), escrita a mano

`alembic revision --rev-id 0002 -m "disparador solo agregado"` (sin `--autogenerate`), con `down_revision = "0001"`:

```python
TABLAS = ("historial_estado_orden", "movimiento_stock", "historial_precio_repuesto")

def upgrade() -> None:
    op.execute("""
        CREATE FUNCTION rechazar_cambio_solo_agregado() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'La tabla % es de sólo agregado: no se permite %',
                TG_TABLE_NAME, TG_OP
                USING ERRCODE = 'restrict_violation';
        END;
        $$
    """)
    for tabla in TABLAS:
        op.execute(f"""
            CREATE TRIGGER tg_{tabla}_solo_agregado
            BEFORE UPDATE OR DELETE ON {tabla}
            FOR EACH ROW EXECUTE FUNCTION rechazar_cambio_solo_agregado()
        """)

def downgrade() -> None:
    for tabla in TABLAS:
        op.execute(f"DROP TRIGGER tg_{tabla}_solo_agregado ON {tabla}")
    op.execute("DROP FUNCTION rechazar_cambio_solo_agregado()")
```

- **Una función, tres disparadores.** `TG_TABLE_NAME` y `TG_OP` arman el mensaje, así que no hace falta una función por tabla.
- **`BEFORE … FOR EACH ROW`**: rechaza antes de tocar la fila. Es de fila por DA-31, para que `TRUNCATE` del seed pase: `TRUNCATE` sólo dispara disparadores `ON TRUNCATE`, que no se crean. `RETURN` no hace falta, porque el `RAISE` corta siempre.
- **`ERRCODE = 'restrict_violation'` (23001, clase 23)**: asyncpg lo levanta como `RestrictViolationError`, subclase de `IntegrityConstraintViolationError`. El dialecto lo envuelve como `IntegrityError`, y la traducción de CH-02 lo convierte en `Conflicto` (409 genérico, porque no trae `constraint_name`) con log. Así, un bug que llegue a hacer `UPDATE` nunca da 500 (RN-18). En `psql` se ve el mensaje propio (D2/D3 de la spec).

  ```
  UPDATE movimiento_stock ...  --> BEFORE ROW trigger --> RAISE 23001
     --> asyncpg RestrictViolationError --> SQLAlchemy IntegrityError
     --> UnitOfWork.__aexit__ (rollback) --> Conflicto(MENSAJE_GENERICO) --> 409
  ```

- **Sin `IF EXISTS` en el `downgrade`**: si el disparador falta, el esquema no es el que la migración cree, y el downgrade debe fallar a la vista.
- El SQL es literal: el único dato interpolado es el nombre de tabla de la tupla `TABLAS`, nunca un dato del usuario.
- **Comentario obligatorio**: el mismo bloque «Leída antes de aplicarla», que enumera la función, los tres disparadores y el `downgrade`.

**Alternativa sin adoptar: disparador de sentencia.** El PDF no fija la granularidad: dice que el disparador «rechaza cualquier UPDATE o DELETE … venga de donde venga» (Ej. 7). «De fila» viene de DA-31. Un `BEFORE UPDATE OR DELETE … FOR EACH STATEMENT` rechazaría **toda** sentencia `UPDATE`/`DELETE` sobre esas tablas, incluso una que no alcanza filas. C-14 sería concluyente aun con las tablas vacías y desaparecería D4. Tampoco bloquea `TRUNCATE`, así que es compatible con DA-31. No se adopta porque la decisión vigente (DA-31, explore 17) es de fila. Cambiarla sería tocar sólo esta migración (`FOR EACH STATEMENT`) y los escenarios D4 y X2.

### D8. `test/solo_agregado.sql` (18, corrección de la alumna)

Estructura:

```sql
-- C-14: sólo agregado (RN-15) y estado por FK al catálogo (RN-19).
-- Correr DESPUÉS de `python seed.py`:  psql -d taller_mecanico -f test/solo_agregado.sql
\set ON_ERROR_STOP on
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM historial_estado_orden)
       OR NOT EXISTS (SELECT 1 FROM movimiento_stock)
       OR NOT EXISTS (SELECT 1 FROM historial_precio_repuesto)
       OR NOT EXISTS (SELECT 1 FROM vehiculo) THEN
        RAISE EXCEPTION 'Corré python seed.py primero';
    END IF;
END
$$;
\set ON_ERROR_STOP off

-- Esperado: ERROR:  La tabla historial_estado_orden es de sólo agregado: no se permite UPDATE
UPDATE historial_estado_orden SET cuando = cuando
 WHERE id = (SELECT min(id) FROM historial_estado_orden);
-- ... (DELETE de historial_estado_orden; UPDATE y DELETE de movimiento_stock y de historial_precio_repuesto)

-- Esperado: ERROR:  inserción o actualización en la tabla «orden_trabajo» viola la llave foránea
--           «fk_orden_trabajo_estado_estado_orden»
INSERT INTO orden_trabajo (vehiculo_id, estado, falla, total)
VALUES ((SELECT min(id) FROM vehiculo), 'INEXISTENTE', 'Prueba de C-14', 0);
```

- La verificación con `ON_ERROR_STOP on` corta `psql` en la primera falla, así que no se ejecuta ninguna de las siete. Después se apaga, para que se vean los siete errores. La verificación también exige un `vehiculo`, porque sin él la séptima fallaría por `NOT NULL` y no por la FK. Es una extensión mínima de lo pedido.
- `min(id)` en vez de ids fijos: vale con cualquier dato y lo puede ejecutar la suite.
- El texto exacto del mensaje de la FK depende del idioma de `lc_messages` del servidor. El comentario lo dice, y lo que importa es el nombre de la restricción.
- **La captura de `psql` se hace en CH-04**, después del seed (R4).
- **En pytest (X1, X2)**, un helper del test lee el archivo:
  - descarta los comentarios `--` y las líneas `\...` de `psql`;
  - corta sentencias en `;` de fin de línea, sin cortar dentro de un bloque `$$ … $$` (cuenta los `$$`);
  - ejecuta cada una en un `SAVEPOINT` de la transacción revertida.

  X2 ejecuta sólo el bloque `DO` con las tablas vacías y espera «Corré python seed.py primero». X1 inserta filas propias, ejecuta el bloque (pasa) y después las siete, y verifica los SQLSTATE `23001` ×6 y `23503` con el nombre de la FK.

### D9. Arnés de pruebas (19, 19a, 20, 21)

- **`esquema_al_dia`** (fixture de sesión, en `conftest.py`): aplica la guarda a `settings_de_prueba` y después corre `python -m alembic upgrade head` por subproceso con `POSTGRES_DB=<base>_test`, como `test_a2`. La usan todos los tests de CH-03 que necesitan tablas.
- **`conexion_revertida`** (por test): abre una conexión del motor de prueba y una transacción externa que se **revierte** al terminar. Entrega una `AsyncSession` (SQLModel) ligada a esa conexión con `join_transaction_mode="create_savepoint"`, y cada rechazo esperado se ejecuta dentro de `begin_nested()`. No deja filas ni necesita `TRUNCATE`, y por eso no choca con el disparador.

  Las secuencias **no** se revierten. Por eso ningún test asume ids fijos: usa el `id` devuelto o `min(id)`.
- **Helpers del test**: factorías mínimas que insertan un usuario, un cliente, un vehículo, un repuesto, el estado `PENDIENTE` y una orden en la conexión revertida. Sólo lo que cada escenario necesita.
- **Afirmación del rechazo**: `pytest.raises(IntegrityError)` y después:
  - `error.orig.sqlstate` (`23514` CHECK, `23505` UNIQUE, `23503` FK, `23502` NOT NULL, `23001` disparador);
  - `error.orig.__cause__.constraint_name`, el mismo camino que usa `errores.py` de CH-02.
- **M2 (ciclo)**: por subproceso `downgrade base` → verificación → `upgrade head` → verificación. Termina siempre en `head`, con un `finally` que reintenta `upgrade head`, para no dejar sin esquema al resto de la sesión.
- **M4 (coincidencia)**: dentro de `conn.run_sync`:
  1. `MigrationContext.configure(sync_conn)`;
  2. `compare_metadata(contexto, SQLModel.metadata)`, con los cuatro modelos importados;
  3. descarta sólo las tuplas `("remove_table", tabla)` cuyo nombre empieza con `prueba_`, con un comentario que cita la nota 7d de CH-02;
  4. afirma que la lista restante está vacía.

  No se usa `alembic check` por subproceso porque vería las `prueba_*` vivas de la sesión. Límite declarado: autogenerate no compara CHECK ni el `WHERE` de un índice parcial; esos los cubren S7 y K/P.
- **M6**: recorre los `.py` del repo excluyendo `.venv`, `__pycache__` y `.git`, y verifica que la lista revisada no está vacía.

## Risks / Trade-offs

- **[`server_default now()` es la hora de inicio de la transacción]** → dos líneas del mismo historial creadas en una transacción tienen el mismo `cuando`. El orden cronológico se decide por `id`. Queda declarado aquí y en el explore (7b).
- **[Un `UPDATE` que no alcanza filas no da error (D4)]** → C-14 verifica filas antes de las siete sentencias (X2) y apunta a `min(id)`. La alternativa de sentencia (D7) lo eliminaría, pero no se adopta.
- **[`TRUNCATE` evita el sólo agregado]** → trade-off aceptado en DA-31: la consigna pide rechazar `UPDATE` y `DELETE`.
- **[Olvidar `import app.core.database` en un `models.py`]** → la convención no se aplica a esas tablas y los nombres vuelven a ser los de Postgres. Lo detecta S7: M4 no compara nombres de restricción, así que no alcanza.
- **[`lazy="raise"` sobre objetos recién creados]** → navegar una colección de un objeto *pendiente* recién construido devuelve la lista vacía sin consultar. Sólo los objetos persistentes no precargados fallan. T4 lo prueba sobre un objeto leído de la base.
- **[Autogenerate no ve CHECK ni `WHERE` parcial]** → un cambio futuro de esas expresiones no aparecería en M4. Lo cubren S7 y los tests de K/P, y no hay migraciones después de CH-03 (`CHANGES.md`).
- **[Mensaje de la FK en el idioma del servidor]** → el comentario de C-14 cita el nombre de la restricción, que no depende del idioma.
- **[Tablas `prueba_*` vivas durante la sesión]** → M2 no las toca (no tienen FK al dominio), M4 las filtra explícitamente, y la migración 0001 se genera contra la base de desarrollo, no contra `_test`.

## Migration Plan

1. **[PERMISO]** Verificar que `taller_mecanico` está vacía y generar `0001` con `--autogenerate` contra ella.
2. **FRENO**: la alumna lee `0001` con la lista de D6. Se escribe el docstring de lectura.
3. Escribir `0002` a mano. **FRENO**: la alumna la lee y se escribe su docstring.
4. Correr la suite contra `taller_mecanico_test`, que hace `upgrade`/`downgrade` (en cada corrida, [PERMISO]).
5. **[PERMISO]** `alembic upgrade head` sobre `taller_mecanico`, después del visto bueno de las dos lecturas.

**Rollback**: `alembic downgrade base` deja la base vacía. Las tablas están vacías hasta CH-04, así que no se pierde ningún dato.

## Verificar en el apply (V)

- **V1**: cómo declara SQLModel 0.0.48 una fecha `NOT NULL` con `server_default` y tipo `Optional` en Python (`nullable=False` en `Field` junto con `sa_column_kwargs`), y que el `RETURNING` la trae después del `flush` (como verificó CH-02, 2g).
- **V2**: la forma de declarar `rol: Rol` como `VARCHAR` sin que SQLModel genere `sa.Enum`. Puede ser `sa_type=AutoString` o una columna `String` explícita. También, que la lectura devuelve un valor comparable con `Rol`.
- **V3**: si SQLAlchemy 2.1 genera `SERIAL` o `IDENTITY` para el `id`, y que `TRUNCATE … RESTART IDENTITY` reinicia ambos (lo necesita CH-04).
- **V4**: que autogenerate renderiza `postgresql_where`, los `op.f(...)` y los CHECK con nombre.
- **V5**: que asyncpg trae `constraint_name` para la violación de un índice único **parcial**. Es un índice, no una restricción, y el nombre que llega es el del índice.
- **V6**: que `23001` llega como `IntegrityError` con el dialecto asyncpg instalado (D6 de la spec).
- **V7**: que `join_transaction_mode="create_savepoint"` funciona con la `AsyncSession` de SQLModel sobre una conexión con transacción externa.
