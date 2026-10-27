# Tasks — CH-02 `core-repositorios-uow`

Convenciones:
- **[PERMISO]**: acción con efectos (correr contra la base `taller_mecanico_test`, crear o borrar tablas). Se describe y se espera la confirmación de Amanda antes de ejecutarla.
- **TDD estricto**: en cada grupo, primero el test que falla (RED, con la falla confirmada al ejecutarlo), después el código mínimo (GREEN), luego la triangulación y el refactor con los tests en verde.
- Los IDs (R1, U3, E6…) son los escenarios de `specs/`; D1-D8 y V1-V4 remiten a `design.md`.
- No se instala nada: CH-02 no suma dependencias.
- No se commitea nada: los commits los hace Amanda.

## 1. Red de seguridad

- [x] 1.1 [PERMISO] Correr `pytest -v` contra `taller_mecanico_test` antes de tocar nada y anotar la línea base en el resumen del apply (CH-01 cerró con 40 passed). Si algo falla, frenar y reportarlo como falla previa: no se arregla en CH-02.

## 2. Arnés de las tablas `prueba_*` (spec `suite-de-pruebas`, F1-F2; design D7)

- [x] 2.1 RED: en `test/pytest/test_tablas_de_prueba.py`, escribir F1. Con una `Settings` cuyo `POSTGRES_DB` no termina en `_test` y `POSTGRES_PORT=puerto_cerrado`, `crear_tablas_de_prueba(settings)` falla con el `ValueError` de la guarda, no con `OSError`. Confirmar que falla porque `test/pytest/tablas_de_prueba.py` no existe.
- [x] 2.2 GREEN: en `test/pytest/tablas_de_prueba.py`, escribir `crear_tablas_de_prueba(settings)` y `borrar_tablas_de_prueba(settings)`. Las dos llaman a `verificar_base_de_prueba` **antes** de crear el motor, y ejecutan con `text()` el DDL de D7 (`DROP ... IF EXISTS` y después `CREATE`, con los nombres de restricción de D7). Sin `create_all`. Verificar F1 en verde.
- [x] 2.3 [PERMISO] TRIANGULAR F2 contra `taller_mecanico_test`: crear las tablas dos veces seguidas termina sin error, y quedan vacías. Verificar en verde.
- [x] 2.4 Resolver **V4**: declarar `ArticuloDePrueba` y `BajaDePrueba` (`table=True`) en `tablas_de_prueba.py` sobre una `MetaData` o un `registry` propio. Verificar con un test que `SQLModel.metadata.tables` no contiene `prueba_articulo` ni `prueba_baja`, y anotar en el resumen la forma que funcionó.
- [x] 2.5 En `conftest.py`, escribir las fixtures:
  - `tablas_de_prueba` (sesión): fija `POSTGRES_DB=<base>_test` con `pytest.MonkeyPatch.context()`, hace `get_settings.cache_clear()`, toma `get_settings()`, crea las tablas, hace `yield` y las borra;
  - `fabrica_de_prueba` (sesión): `crear_motor` + `crear_fabrica_de_sesiones` de CH-01, con `dispose()` al final;
  - `tablas_limpias` (por test): `TRUNCATE prueba_baja, prueba_articulo RESTART IDENTITY`.
  [PERMISO] Verificar con `pytest test/pytest/test_tablas_de_prueba.py -v` que la suite de CH-01 no se ve afectada (sin cambios en sus fixtures).

## 3. Paginación pura y primera excepción de dominio (spec `paginacion`, P1-P4; design D5, D6)

- [x] 3.1 RED: en `test/pytest/test_paginacion.py`, escribir P1 (`calcular_ventana(5, 1, 2)` → offset 0, limit 2, pages 3; con `page=3` → offset 4) y P2 (`calcular_ventana(4, 3, 2)` lanza `PaginaInexistente` con el mensaje exacto «La página 3 no existe: hay 2»). Confirmar que fallan porque no existen `app/core/paginacion.py` ni `app/core/errores.py`.
- [x] 3.2 GREEN: en `app/core/errores.py`, escribir `ErrorDeDominio(mensaje)` y `PaginaInexistente`, sin importar FastAPI. En `app/core/paginacion.py`, escribir `Ventana` y `calcular_ventana`. Verificar P1 y P2 en verde.
- [x] 3.3 TRIANGULAR: P3 (`total=0` → `pages=1`; página 1 válida; página 2 → «La página 2 no existe: hay 1») y P4 (`total=100, size=100` → 1; `total=101` → 2). Generalizar a `max(1, ceil(total / size))` hasta que pasen.
- [x] 3.4 REFACTOR: revisar nombres y verificar `pytest test/pytest/test_paginacion.py -v` en verde (sin base).

## 4. `BaseRepository` (spec `repositorios`, R1-R10; design D2)

- [x] 4.1 RED: en `test/pytest/test_repositorio.py`, con las fixtures del grupo 2, escribir R1 (alta: `id` cargado y `creado_en` legible sin IO implícito) y R2 (otra sesión no ve la fila hasta el commit). Confirmar que fallan porque `app/core/repository.py` no existe.
- [x] 4.2 [PERMISO] GREEN: en `app/core/repository.py`, escribir `BaseRepository[T]` con `__init__(session, modelo)`, `_consulta` y `add` (add + flush, sin commit). Resolver **V2** (si `creado_en` se lee después del flush sin IO implícito) y anotar el resultado. Verificar R1 y R2 en verde.
- [x] 4.3 [PERMISO] TRIANGULAR: R3 (`get_by_id` existente/inexistente con `_por_id`), R4 (`get_all(offset=2, limit=2)` → ids 3 y 4; offset fuera de rango → `[]`, con `_listar` y `ORDER BY id`), R5 (`count` 5 y 0, con `_contar`) y R9 (`delete` + flush). Implementar hasta que pasen.
- [x] 4.4 [PERMISO] TRIANGULAR: R6 (`update(e, {"cantidad": 7})` cambia sólo ese campo, con flush y sin commit), R7 (clave desconocida → `ValueError` que nombra la clave, entidad intacta) y R8 (`id` → `ValueError`). La validación contra los campos del modelo va **antes** de aplicar nada (D2, 2e). Verificar en verde.
- [x] 4.5 [PERMISO] TRIANGULAR R10: un repositorio de prueba con un método con nombre (p. ej. `listar_con_cantidad_mayor_a`) que arma un `stmt` filtrado sobre `_consulta()` y lo pasa a `_listar` y `_contar`. Probar con dos filtros distintos. Verificar en verde.
- [x] 4.6 REFACTOR: revisar firmas y tipos; [PERMISO] verificar `pytest test/pytest/test_repositorio.py -v` en verde.

## 5. `SoftDeleteRepository` (spec `repositorios`, B1-B5; design D3)

- [x] 5.1 RED: en `test/pytest/test_repositorio.py`, escribir B1 (`soft_delete` → `borrado_en` UTC; después, `get_by_id` `None`, `get_all` y `count` lo excluyen) y B4 (construirlo sobre `ArticuloDePrueba` → `TypeError`). Confirmar que fallan.
- [x] 5.2 [PERMISO] GREEN: escribir `SoftDeleteRepository[T]` con la verificación de `borrado_en` en `__init__`, el único override de `_consulta()` y `soft_delete` (`datetime.now(timezone.utc)` + flush). Verificar B1 y B4 en verde.
- [x] 5.3 [PERMISO] TRIANGULAR: B2 (`get_by_id_including_deleted` con `_por_id(select(modelo), id)`), B3 (una segunda baja conserva el `borrado_en` original) y B5 (método con nombre de una subclase, sin filtro propio, devuelve sólo los vigentes). Verificar en verde.
- [x] 5.4 REFACTOR: [PERMISO] verificar `pytest test/pytest/test_repositorio.py -v` en verde.

## 6. `UnitOfWork` (spec `unidad-de-trabajo`, U1-U7, U9, U10; design D4)

- [x] 6.1 RED: en `test/pytest/test_unit_of_work.py`, escribir U1 (sale sin excepción → otra sesión ve la fila) y U3 (flush, excepción de dominio lanzada dentro del bloque → la fila no queda, y la excepción llega a quien abrió el bloque). Confirmar que fallan porque `app/core/unit_of_work.py` no existe.
- [x] 6.2 [PERMISO] GREEN: en `app/core/unit_of_work.py`, escribir `UnitOfWork` con `__init__(session)`, `__aenter__` y `__aexit__`: rollback ante **cualquier** excepción, commit si no hay excepción, nunca `close()`, sin `commit`/`rollback` públicos. Verificar U1 y U3 en verde.
- [x] 6.3 [PERMISO] TRIANGULAR: U2 (error de la base dentro del bloque → la fila no queda), U4 (`ValueError` → rollback y el mismo `ValueError` sale sin cambios) y U5 (después de confirmar y después de revertir, la sesión ejecuta `SELECT 1`). Verificar en verde.
- [x] 6.4 [PERMISO] TRIANGULAR: U6 (bloque anidado → `RuntimeError`, el bloque externo revierte; flag `_abierto`) y U7 (dos bloques consecutivos confirman los dos). Verificar en verde.
- [x] 6.5 [PERMISO] TRIANGULAR: U9 (`UoWDePrueba` con `articulos` y `bajas` creados en `__init__` sobre la misma sesión: con éxito confirman juntas, con excepción no queda ninguna) y U10 (sesión propia que confirma mientras la de la «petición» revierte: queda sólo la fila de la propia). Verificar en verde.
- [x] 6.6 REFACTOR: [PERMISO] verificar `pytest test/pytest/test_unit_of_work.py -v` en verde.

## 7. Traducción de `IntegrityError` (spec `errores-de-dominio`, E1-E6; spec `unidad-de-trabajo`, U8; design D6)

- [x] 7.1 RED: en `test/pytest/test_errores.py`, escribir E1 (UNIQUE mapeado → `Conflicto` con el mensaje propio, sin el nombre de la restricción, la tabla, la columna, `duplicate`, `violates` ni `unique`). Confirmar que falla (hoy sale el `IntegrityError` crudo).
- [x] 7.2 [PERMISO] GREEN: resolver **V1** (el atributo por el que se llega al nombre de la restricción y al SQLSTATE con asyncpg) y anotarlo. En `errores.py`, escribir `Conflicto` y `traducir_integrity_error(error, mensajes)`. En `UnitOfWork`, escribir `mensajes_de_restriccion` y la traducción en `__aexit__` (`raise ... from error`). Verificar E1 en verde.
- [x] 7.3 [PERMISO] TRIANGULAR: E2 (CHECK mapeado, mensaje distinto del de E1), E3 (UoW sin mapa → `MENSAJE_GENERICO`) y E6 (borrar con `delete` un `prueba_articulo` referenciado por `prueba_baja.articulo_id` → `Conflicto` con el mensaje mapeado de `fk_prueba_baja_articulo_id`, y el artículo sigue en la base). Verificar en verde.
- [x] 7.4 [PERMISO] TRIANGULAR: E4 (NOT NULL → `MENSAJE_GENERICO`, y `caplog` registra un nivel ERROR) y E5 (`caplog` tiene el nombre de la restricción y el SQLSTATE; el mensaje del `Conflicto`, no). Agregar el logger de `errores.py`. Verificar en verde.
- [x] 7.5 [PERMISO] TRIANGULAR U8 en `test_unit_of_work.py`: `session.add` de un nombre duplicado sin flush hace que el UNIQUE salte en el `commit` → rollback, `Conflicto`, el duplicado no queda y la sesión ejecuta `SELECT 1`. Implementar el `try/except` del commit en `__aexit__` hasta que pase.
- [x] 7.6 REFACTOR: escribir `NoEncontrado` en `errores.py` (lo usa el grupo 9) y revisar nombres; [PERMISO] verificar `pytest test/pytest/test_errores.py test/pytest/test_unit_of_work.py -v` en verde.

## 8. Paginación con FastAPI y con la base (spec `paginacion`, P5-P7; design D5)

- [x] 8.1 RED: en `test_paginacion.py`, escribir P5 sobre una app de prueba con una ruta que usa `parametros_de_pagina`. Sin parámetros recibe `page=1, size=20`; `size=100` → 200; `size=500`, `size=0`, `page=0` y `page=abc` → 422. Confirmar que falla.
- [x] 8.2 GREEN: escribir `parametros_de_pagina` (`async def`, `Query(1, ge=1)` y `Query(20, ge=1, le=100)`) en `paginacion.py`. Verificar P5 en verde.
- [x] 8.3 TRIANGULAR P6: resolver **V3** (`class Pagina[T](BaseModel)` con PEP 695, o `Generic[T]`) y anotarlo; escribir `Pagina[T]` y `armar_pagina`. Verificar que el JSON tiene exactamente `items`, `total`, `page`, `size` y `pages`.
- [x] 8.4 [PERMISO] TRIANGULAR P7: de punta a punta con el repositorio de prueba del grupo 4 (`count` → `calcular_ventana` → listar → `armar_pagina`). `total` cuenta con el mismo filtro que `items`. Verificar en verde.
- [x] 8.5 REFACTOR: [PERMISO] verificar `pytest test/pytest/test_paginacion.py -v` en verde.

## 9. Clase de ruta y rutas de salud (spec `errores-de-dominio`, T1-T5; design D6, 6e)

- [x] 9.1 RED: en `test/pytest/test_rutas.py`, escribir T1 sobre una app de prueba con `APIRouter(route_class=RutaQueTraduceErrores)` y tres rutas que lanzan `NoEncontrado`, `Conflicto` y `PaginaInexistente` → 404, 409 y 422, con `{"detail": "<mensaje>"}`. Confirmar que falla porque `app/core/rutas.py` no existe.
- [x] 9.2 GREEN: en `app/core/rutas.py`, escribir `RutaQueTraduceErrores(APIRoute)`, que redefine `get_route_handler()`, y el mapa excepción → código buscado por MRO. Verificar T1 en verde.
- [x] 9.3 TRIANGULAR: T2 (la dependencia de una ruta lanza `Conflicto` → 409) y T3 (`ValueError` → no se traduce; 500 con un `ASGITransport(raise_app_exceptions=False)`). Verificar en verde.
- [x] 9.4 RED: escribir T4. Recorre `main.app.routes`, excluye `/openapi.json`, `/docs`, `/docs/oauth2-redirect` y `/redoc`, y verifica que cada `APIRoute` es `RutaQueTraduceErrores`, que el conjunto no está vacío y que contiene `/health/live`. Confirmar que **falla** por las rutas de salud.
- [x] 9.5 [PERMISO] GREEN con red de seguridad (T5): en `app/modules/health/router.py`, agregar `route_class=RutaQueTraduceErrores` al `APIRouter`. No hay ningún otro cambio en el archivo: la `HTTPException(503)` sigue igual. Verificar T4 en verde, y con `pytest test/pytest/test_salud.py test/pytest/test_ciclo_de_vida.py -v` que la suite de CH-01 sigue en verde (H1-H7, L1-L4, G1-G2).
- [x] 9.6 REFACTOR: [PERMISO] verificar `pytest test/pytest/test_rutas.py -v` en verde.

## 10. Verificación estática y documentación

- [x] 10.1 R11: en `test_repositorio.py`, escribir un test que lee `app/core/repository.py` y todo `app/modules/*/repository.py` y verifica que ninguno contiene `.commit(`. Para que no pase en vacío, verificar también que la lista de archivos revisados incluye `app/core/repository.py`. Verificar en verde.
- [x] 10.2 Actualizar `AGENTS.md` y `CLAUDE.md`, en los dos archivos y con el mismo texto: sumar `errores.py` y `rutas.py` a la estructura de `app/core/` en la regla «Estructura obligatoria del PDF», con la marca «No especificado en la consigna», y la regla de que cada `router.py` declara `route_class=RutaQueTraduceErrores`. Verificar con `git diff --no-index AGENTS.md CLAUDE.md` que los dos archivos siguen idénticos.
- [x] 10.3 Actualizar `README.md`: mover CH-02 de «Planificado» a «Implementado», con su descripción. No hay pasos nuevos de puesta en marcha. Verificar que la tabla de «Implementado» lista CH-01 y CH-02.

## 11. Verificación final

- [x] 11.1 Revisar el punto de control de governance con `git grep` y anotar el resultado:
  - ningún `.commit(` en repositorios;
  - ningún `create_all` en el repo;
  - ningún servicio construye un UoW (hoy no hay servicios);
  - `UnitOfWork` sin `close()`;
  - `errores.py` y `paginacion.py` sin imports de FastAPI (`paginacion.py` sólo `Query`);
  - todas las funciones de dependencia y handlers nuevos son `async def`.
- [x] 11.2 Correr `openspec validate core-repositorios-uow --strict` y verificar que no hay errores.
- [x] 11.3 [PERMISO] Correr `pytest -v` completo contra `taller_mecanico_test` y guardar la salida completa en `docs/evidencias/pytest-CH-02.txt`. Verificar que:
  - los 46 escenarios (R1-R11, B1-B5, U1-U10, P1-P7, E1-E6, T1-T5, F1-F2) tienen al menos un test en verde;
  - la suite de CH-01 sigue en verde;
  - no hay fallos ni errores, y no quedan tablas `prueba_*` en la base después de la corrida.
  
  Dejar el change listo para que Amanda revise y commitee (`feat(CH-02): ...`).
