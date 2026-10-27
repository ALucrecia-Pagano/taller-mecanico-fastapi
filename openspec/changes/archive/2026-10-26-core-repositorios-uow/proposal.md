# Proposal — CH-02 `core-repositorios-uow`

## Why

Ningún módulo del dominio puede leer ni escribir sin una forma común de acceder a la base, de agrupar escrituras en una transacción, de paginar listados y de convertir un choque con lo guardado en un 409 propio. Además, el Ejercicio 6 de la consigna (20 %, el de mayor peso) evalúa exactamente esto: «Dos jerarquías, clase del modelo, `flush` y no `commit`, precarga en el repositorio, quién crea, abre, confirma y cierra, operaciones de varias escrituras». También carga la paginación del Ejercicio 3 (10 %) y RN-18. CH-02 tiene que estar terminado antes de CH-05.

Las decisiones de este change se tomaron en el explore: [docs/evidencias/explore-CH-02.md](../../../docs/evidencias/explore-CH-02.md). Son definitivas.

## What Changes

- **Repositorios** (`app/core/repository.py`):
  - `BaseRepository[T]` recibe la sesión y la clase del modelo, y ofrece `get_by_id`, `get_all`, `count`, `add`, `update` y `delete`.
  - `add`, `update` y `delete` hacen `flush()`, nunca `commit()`.
  - `update` aplica sólo los campos enviados y rechaza claves que no son campos del modelo, y también `id` (decisión de la alumna).
  - `SoftDeleteRepository[T]` hereda, filtra los dados de baja y agrega `get_by_id_including_deleted` y `soft_delete`.
- **Unit of Work** (`app/core/unit_of_work.py`): `UnitOfWork` base, gestor de contexto asincrónico.
  - Confirma al salir del bloque y revierte ante **cualquier** excepción (decisión de la alumna).
  - No cierra la sesión y rechaza los bloques anidados.
  - Traduce todo `IntegrityError`, del `flush` o del `commit`, a un error de dominio con mensaje propio.
- **Paginación** (`app/core/paginacion.py`):
  - Parámetros `page` (desde 1) y `size` (1 a 100, por defecto 20).
  - Envoltorio `{items, total, page, size, pages}`.
  - Página más allá de la última → 422 «La página 3 no existe: hay 2».
  - Con cero resultados, una página vacía.
- **Errores de dominio** (`app/core/errores.py`, nuevo): `ErrorDeDominio` con `NoEncontrado`, `Conflicto` y `PaginaInexistente`, más el traductor de `IntegrityError`: por nombre de restricción, con un 409 genérico si no hay mapa, y sin texto de la base.
- **Traducción a HTTP** (`app/core/rutas.py`, nuevo): una clase de ruta que cada `router.py` declara con `route_class` y que convierte los errores de dominio en 404, 409 o 422 con `{"detail": "<mensaje>"}`. `app/modules/health/router.py` (CH-01) pasa a declararla.
- **Arnés de pruebas**: tablas `prueba_articulo` y `prueba_baja`, creadas con DDL escrito a mano después de la guarda de `_test`, sin `create_all`, y 46 escenarios automáticos. CH-02 no expone endpoints: no hay `.http`.

### Refinamientos de alcance respecto de `CHANGES.md`

Como los Desvíos de `CHANGES.md`, estos ajustes no renombran, fusionan ni reordenan changes:

- **R1 — la traducción de errores de dominio a HTTP la declara el router.** `CHANGES.md` pone un «handler de excepciones de dominio → HTTP registrado en `main.py`». En su lugar, cada `router.py` declara la clase de ruta de `app/core/rutas.py`, incluido el de salud de CH-01. Motivo: el PDF dice que `router.py` «traduce errores», y manda la letra del PDF (decisión de la alumna).
- **R2 — dos archivos del core que la consigna no lista**: `app/core/errores.py` (excepciones de dominio, decisión de la alumna) y `app/core/rutas.py` (clase de ruta). Los dos son **No especificado en la consigna**. Se suman a la estructura descrita en `AGENTS.md` y `CLAUDE.md` al cerrar el change.

### Queda afuera (y dónde va)

| Qué | Change |
|---|---|
| Modelos del dominio, `naming_convention` con nombres de restricción estables, migraciones | CH-03 |
| `app/core/security.py` | CH-04 |
| UoW de `usuarios` con su mapa restricción → mensaje, dependencia `get_usuarios_uow`, sesión propia de `intento_acceso` (DD-05), `app/core/dependencies.py` | CH-05 |
| Excepciones de 401, 403 y 429 | CH-05 y CH-06 |
| Repositorios de cada entidad con sus métodos con nombre y su precarga; UoW y dependencia de cada módulo | CH-05, CH-07, CH-08 y CH-09 |
| Repositorio de sólo lectura del catálogo `estado_orden` (no hereda de `BaseRepository`) | El change que crea su modelo y lo usa (CH-03 / CH-09) |

## Capabilities

### New Capabilities

- `repositorios`: acceso genérico a las tablas (lectura por id, listado ordenado y paginable, conteo, alta, modificación parcial y baja sin confirmar) y su variante con borrado lógico.
- `unidad-de-trabajo`: una operación de negocio es una transacción que se confirma al terminar bien y se revierte ante cualquier error, sin cerrar la sesión.
- `paginacion`: parámetros, envoltorio y cálculo de páginas de todos los listados.
- `errores-de-dominio`: traducción de los choques con la base a errores propios, y de los errores de dominio a respuestas HTTP sin texto interno.

### Modified Capabilities

- `suite-de-pruebas`: se agrega el requisito de las tablas de prueba de la suite, creadas sólo después de la guarda de `_test` y sin `create_all`.

## Impact

- **Archivos nuevos**: `app/core/repository.py`, `app/core/unit_of_work.py`, `app/core/paginacion.py`, `app/core/errores.py`, `app/core/rutas.py` y, en `test/pytest/`, los tests y el arnés de las tablas `prueba_*`.
- **Archivos modificados**: `app/modules/health/router.py` (declara `route_class`; la suite de CH-01 es la red de seguridad), `test/pytest/conftest.py` (fixture de las tablas `prueba_*`), `AGENTS.md` y `CLAUDE.md` (estructura con `errores.py` y `rutas.py`), y `CHANGES.md` (CH-02 `[x]` al archivar).
- **Dependencias**: ninguna nueva.
- **Base**: sólo `taller_mecanico_test`, donde se crean y borran las tablas `prueba_*`. Ningún cambio de esquema en la aplicación.
- **API**: sin endpoints nuevos. Las rutas de salud mantienen su comportamiento.
- **Governance**: MEDIO. Es la columna vertebral de las transacciones: ningún `commit` en repositorios, y el servicio nunca construye el UoW.
- **RN**: RN-18 y la parte de 409 de RN-01. DA/DD aplicados: DD-04, DD-05 (patrón declarado), DA-00, DA-14, DA-21 y DA-23. Casos C-NN propios: ninguno (habilita C-02, C-11, C-16 y C-19).
