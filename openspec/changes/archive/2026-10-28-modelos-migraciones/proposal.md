# Proposal — CH-03 `modelos-migraciones`

## Why

Ningún módulo del dominio puede existir sin sus tablas. La consigna exige crearlas sólo con Alembic, con los nombres obligatorios del PDF y con las garantías en la base: UNIQUE, tres índices únicos parciales, CHECK, estados por clave foránea al catálogo y un disparador de sólo agregado. Este change carga el Ejercicio 2 (14 %) y la parte del disparador del Ejercicio 7 (10 %). Además, «no crea su esquema con `alembic upgrade head` sobre una base vacía» es una condición excluyente de la corrección. CH-04 y todos los changes de módulo dependen de él.

Las decisiones de este change se tomaron en el explore: [docs/evidencias/explore-CH-03.md](../../../docs/evidencias/explore-CH-03.md), incluida la corrección de la alumna sobre C-14. Son definitivas.

## What Changes

- **Modelos SQLModel** en sus módulos (las carpetas nacen acá, cada una con `__init__.py` y `models.py`):
  - `usuarios`: `Usuario`, `AsignacionRol`, `IntentoAcceso`, `EventoSeguridad` y el enum `Rol`;
  - `clientes`: `Cliente`, `Vehiculo`;
  - `repuestos`: `Repuesto`, `MovimientoStock`, `HistorialPrecio` (tabla `historial_precio_repuesto`);
  - `ordenes`: `OrdenTrabajo`, `EstadoOrden` (catálogo), `ItemOrden`, `HistorialEstadoOrden` y el enum `CodigoEstado`.
  
  Son 13 tablas con las columnas textuales del PDF, `usuario` sin columna `rol`, el dinero en `NUMERIC(10,2)`/`NUMERIC(12,2)` y toda fecha en `timestamptz`. Son `NOT NULL` todas las columnas que no dicen «(nulo)».
- **Restricciones con nombres estables**: `naming_convention` en `SQLModel.metadata`, aplicada en `app/core/database.py`. Los tres índices parciales llevan nombre explícito.
  - Todos los CHECK de la consigna; `rol` es `VARCHAR` con CHECK, sin ENUM nativo.
  - Los UNIQUE.
  - Los tres índices únicos parciales con `postgresql_where`.
  - Los estados (`estado`, `desde_estado`, `hasta_estado`) son FK a `estado_orden.codigo`, sin CHECK.
  - Toda FK encabeza un índice.
  
  Los nombres son el contrato de los mapas restricción → mensaje de cada UoW (pedido de CH-02).
- **Navegación ORM** en los dos extremos de cada relación de la Figura 1. `Usuario.cliente` es un objeto. Todas las relaciones llevan `lazy="raise"`, para que ninguna se cargue sin precarga declarada.
- **Migración `0001_esquema_inicial`**: generada con `--autogenerate` contra la base de desarrollo vacía. Crea las 13 tablas y deja el catálogo vacío. Se lee antes de aplicarla y lleva un comentario que lo dice.
- **Migración `0002_disparador_solo_agregado`**, escrita a mano:
  - una función y tres disparadores `BEFORE UPDATE OR DELETE … FOR EACH ROW` sobre `historial_estado_orden`, `movimiento_stock` e `historial_precio_repuesto`;
  - un `downgrade` que los borra;
  - el mismo comentario de lectura previa.
- **Configuración de Alembic**:
  - `migrations/env.py` importa los cuatro `models.py`;
  - `migrations/script.py.mako` gana `import sqlmodel`.
- **`test/solo_agregado.sql`** (C-14):
  - verifica primero que las tres tablas tienen filas y, si no, corta con «Corré python seed.py primero»;
  - después ejecuta los seis rechazos del disparador y el de la FK de una orden con estado inexistente, con la respuesta esperada en comentarios.
- **Suite pytest test-first**:
  - ciclo `upgrade → downgrade base → upgrade`;
  - forma del esquema leída de `pg_catalog`;
  - cada CHECK, UNIQUE, índice parcial y FK, con el rechazo y la aceptación;
  - disparador probado con filas propias;
  - modelos y migraciones sin diferencias;
  - ningún `create_all`.

### Refinamientos de alcance respecto de `CHANGES.md`

Como los Desvíos de `CHANGES.md`, no renombran, fusionan ni reordenan changes:

- **R1**: el enum espejo de los estados se llama **`CodigoEstado`**, no `EstadoOrden`, porque choca con la clase del catálogo en el mismo `models.py`. Lo usan CH-04 (seed) y CH-09 (contrato de órdenes).
- **R2**: la convención de nombres vive en `app/core/database.py`. No se suma ningún archivo al core.
- **R3**: `migrations/script.py.mako` importa `sqlmodel`. Sin eso, la migración autogenerada no corre (`AutoString`).
- **R4 (corrección de la alumna)**: la captura de `psql` de C-14 pasa de CH-11 a **CH-04**, después del seed. En CH-03 el disparador se prueba sólo con pytest, insertando filas propias, porque las tablas de sólo agregado todavía están vacías y un disparador de fila no salta sin filas.

### Queda afuera (y dónde va)

| Qué | Change |
|---|---|
| `seed.py` (carga del catálogo desde `CodigoEstado`, `TRUNCATE … RESTART IDENTITY CASCADE`) y la captura de `psql` de C-14 | CH-04 |
| Schemas, repositorios, UoW con su mapa restricción → mensaje, servicios y routers de cada módulo | CH-05 a CH-10 |
| Repositorio de sólo lectura de `estado_orden` y `GET /estados` | CH-09 |
| Navegación sobre las FK inferidas (`usuario_id` del historial, `movimiento_stock.orden_id`, `otorgada_por`) | El change que la lea; no requiere migración |

## Capabilities

### New Capabilities

- `modelo-de-datos`: las 13 tablas del dominio con sus columnas, tipos y nulabilidad, sus restricciones (CHECK, UNIQUE, índices únicos parciales, FK al catálogo, índice por FK) con nombres estables, y la navegación ORM sin carga implícita.
- `solo-agregado`: las tres tablas de sólo agregado rechazan en la base cualquier `UPDATE` o `DELETE`, y `test/solo_agregado.sql` lo demuestra (C-14).

### Modified Capabilities

- `migraciones`: suma las dos migraciones (la autogenerada y la escrita a mano, cada una con su comentario de lectura previa), el ciclo `upgrade head → downgrade base → upgrade head` sobre base vacía, el catálogo vacío después de migrar, la coincidencia entre modelos y migraciones, y la prohibición de `create_all`.

## Impact

- **Archivos nuevos**:
  - `app/modules/{usuarios,clientes,repuestos,ordenes}/__init__.py` y su `models.py`;
  - `migrations/versions/0001_esquema_inicial.py` y `0002_disparador_solo_agregado.py`;
  - `test/solo_agregado.sql`;
  - los tests en `test/pytest/` (esquema, restricciones, disparador y migraciones).
- **Archivos modificados**:
  - `app/core/database.py` (convención de nombres);
  - `migrations/env.py` (imports de los modelos);
  - `migrations/script.py.mako` (`import sqlmodel`);
  - `test/pytest/conftest.py` (fixture `esquema_al_dia`);
  - `test/pytest/test_migraciones.py` (ciclo y coincidencia);
  - `README.md` (CH-03 implementado; `alembic upgrade head` en la puesta en marcha);
  - `CHANGES.md` (CH-03 `[x]` y R1/R4 al archivar).
- **Dependencias**: ninguna nueva.
- **Base**:
  - `taller_mecanico`: se autogenera 0001 contra ella después de verificar que está vacía, y se aplica `upgrade head`, con permiso y después de que la alumna lea las migraciones;
  - `taller_mecanico_test`: `upgrade`/`downgrade` desde la suite.
- **API**: sin endpoints nuevos.
- **Governance**: ALTO. Esquema y migraciones afectan los datos: el diseño de las dos migraciones se revisa antes del apply, y cada migración se lee antes de aplicarla.
- **RN**: RN-01 y RN-03 (garantía en la base), RN-15 (disparador), RN-19 (FK al catálogo) y la base de RN-16 y RN-20 (CHECK). DA/DD aplicados: DA-00, DA-08, DA-20, DA-31, DD-01, DD-02, DD-03, DD-10, DD-13, SU-01 y SU-02. Caso propio: **C-14** (archivo y pytest; la captura va en CH-04).
