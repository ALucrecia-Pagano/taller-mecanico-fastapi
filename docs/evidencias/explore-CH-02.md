# Explore de CH-02 `core-repositorios-uow`

Resumen del explore (`/opsx:explore`) del segundo change, hecho entre el 2026-10-25 y el 2026-10-26, antes del propose. No se escribió código.

Fuentes: `CHANGES.md` (CH-02, OB-05), `knowledge-base/08_arquitectura_propuesta.md`, `knowledge-base/09_decisiones_y_supuestos.md` (DD-04, DD-05, DA-14, DA-21, DA-23), `knowledge-base/06_funcionalidades.md` (US-021, US-050, US-051), las specs que dejó CH-01 en `openspec/specs/`, `docs/evidencias/explore-CH-01.md` (nota para CH-02: `AsyncSession` de SQLModel), el código existente (`app/core/database.py`, `test/pytest/conftest.py`) y la consigna: Ejercicio 3 (paginación, §2.9), Ejercicio 6, requisitos no funcionales (Transacciones, Errores, Unicidad, Esquema) y criterios de evaluación («Dos jerarquías, clase del modelo, flush y no commit, precarga en el repositorio, quién crea, abre, confirma y cierra, operaciones de varias escrituras»).

En la columna «Decisión», **[Alumna]** marca lo que propuso o agregó la alumna; el resto lo propuso el agente y la alumna lo aceptó. Lo que la consigna no especifica está marcado como tal.

## Decisiones

| # | Pregunta | Decisión | Por qué |
|---|---|---|---|
| 1 | ¿Qué nace en CH-02 y qué no? | Nacen `app/core/repository.py`, `app/core/unit_of_work.py`, `app/core/paginacion.py`, `app/core/errores.py`, `app/core/rutas.py` (ver 6e) y los tests en `test/pytest/`. **No** nacen: `dependencies.py` (CH-05), `security.py` (CH-04), el repositorio de sólo lectura de `estado_orden` (con su modelo), los UoW de cada módulo y sus dependencias (en el change de cada módulo), ni métodos con precarga (repositorios de cada entidad). La traducción de errores queda en CH-02. | Nace sólo lo que se implementa y prueba (criterio de CH-01). CHANGES.md asigna RN-18 a CH-02; dejarla para CH-05 la diseñaría dentro de un change CRÍTICO. |
| 1-E | ¿Dónde viven las excepciones de dominio? | **[Alumna]** En `app/core/errores.py`, nuevo, «No especificado en la consigna». Al cerrar el change se suma a la estructura que describen `AGENTS.md`/`CLAUDE.md`. | Agregar un archivo no rompe la estructura obligatoria; meterlas en `unit_of_work.py` o `repository.py` rompería «cada capa sabe lo suyo». |
| 2 | Forma de `BaseRepository[T]` | `__init__(session, modelo)`; helpers protegidos `_consulta()` (= `select(modelo)`), `_listar(stmt, offset, limit)` y `_contar(stmt)`; `get_by_id`, `get_all(offset, limit)`, `count()`, `add` (add + flush), `update(entidad, datos)` (setattr + flush), `delete` (delete + flush). | Un único punto de partida de las consultas permite que `SoftDeleteRepository` filtre sin reescribir métodos (decisión 3). |
| 2a | ¿Cómo filtra `get_all`? | La base no filtra. Los listados con filtro son métodos con nombre en el repositorio de cada entidad, armados sobre `self._consulta().where(...)`, que reutilizan `_listar` y `_contar` con el **mismo** `stmt`. | «Métodos que se nombran por lo que traen» (Ej. 6); «`total` cuenta con los mismos filtros» se cumple por construcción. Un `get_all(filtros=...)` haría que el servicio arme expresiones del ORM. |
| 2b | ¿Cómo ordena? | `ORDER BY id` ascendente por defecto; los métodos con nombre pueden pasar otro orden. Todo `T` tiene `id` (el catálogo, que no lo tiene, no hereda). | Paginar sin `ORDER BY` da páginas inestables. |
| 2c | ¿`offset`/`limit` o `page`/`size` en el repositorio? | `offset`/`limit`; `paginacion.py` traduce `page`/`size`. | Son conceptos de SQL; la regla dura prohíbe `limit`/`offset` **en la API**, no adentro. |
| 2d | ¿`get_by_id` con `session.get` o con `select`? | `select` sobre `_consulta()`. | `session.get` no admite filtros y devuelve el identity map sin ir a la base. |
| 2e | Firma de `update` | `update(entidad, datos: dict)`, con `datos = model_dump(exclude_unset=True)`. **[Alumna]** Rechaza con `ValueError` que nombra la clave toda clave que no sea campo del modelo, **y también `id`**. Comprobación explícita contra los campos del modelo, sin confiar en `setattr`. Es un error de programación: no se traduce a HTTP. | El PATCH parcial (Ej. 3) queda en un solo lugar. Un error de tipeo en un DTO falla fuerte en vez de pasar en silencio; un modelo `table=True` no valida asignaciones. El DTO con `extra="forbid"` ya dio 422 antes, así que si llega es un bug. |
| 2f | ¿`delete` hace `flush`? | Sí (la consigna sólo lo exige para `add`/`update`). | Una violación de FK salta en la llamada y se traduce igual que las demás (6a). |
| 2g | `server_default` después del flush | Sin `refresh` agregado: SQLAlchemy 2.0 con Postgres trae los defaults por `RETURNING` (`eager_defaults="auto"`). Se verifica con un test (R1). | Leer una columna expirada dispara IO implícito (`MissingGreenlet` en async). |
| 3 | Forma de `SoftDeleteRepository[T]` | Único override: `_consulta()` = `super()._consulta().where(borrado_en IS NULL)`. `get_by_id`, `get_all`, `count` y los métodos con nombre de cada entidad heredan el filtro. Agrega `get_by_id_including_deleted` y `soft_delete`. | El filtro vive en un solo lugar (DA-23: los dados de baja no aparecen). |
| 3a | Consulta sin filtro | Helper `_por_id(stmt, id)` en la base: `get_by_id` lo usa con `_consulta()`, `get_by_id_including_deleted` con `select(self.modelo)`. | Una línea, sin duplicar lógica; un flag `incluir_borrados` es más fácil de usar mal. |
| 3b | Hora de `soft_delete` | `datetime.now(timezone.utc)` desde Python, más flush. | `func.now()` deja el atributo expirado después del flush (IO implícito). Trade-off: reloj de la app, irrelevante con un solo proceso. |
| 3c | ¿Cómo sabe que el modelo tiene `borrado_en`? | El constructor lo verifica y lanza `TypeError` si falta. | Construir mal el repositorio falla al instante, no en la primera consulta. |
| 3d | `soft_delete` sobre una entidad ya dada de baja | No pisa un `borrado_en` existente (idempotente). En el flujo normal el servicio busca con `get_by_id`, recibe `None` y responde 404. | Se conserva la fecha original; lanzar error sería una regla de negocio en el repositorio. |
| 3e | `delete` físico heredado | Se deja heredado y no se usa; no se redefine. | La consigna dice «hereda» y «agrega»; redefinirlo para fallar rompe la sustitución y nadie lo pide. |
| 4 | Forma del `UnitOfWork` base | `__init__(session)`, `__aenter__() -> Self`, `__aexit__`: con excepción → rollback y propaga; sin excepción → commit; nunca `close()`. **[Alumna]** Revierte ante **cualquier** excepción, no sólo ante errores de la base (p. ej. una excepción de dominio lanzada por el servicio después de un flush). | Ej. 6 y requisito no funcional «Transacciones»: el UoW no cierra la sesión porque no la creó (la crea y cierra `get_session`, CH-01). |
| 4a | ¿Dónde se crean los repositorios del módulo? | En el `__init__` del UoW de cada módulo, todos con la misma sesión. | Atributos tipados y visibles; los repositorios no tienen estado. |
| 4b | ¿Dónde vive la dependencia que construye el UoW? | En `router.py` de cada módulo: `async def get_<modulo>_uow(session = Depends(get_session))`. | Literal al PDF («router.py: construyen el Unit of Work»). `async def`: FastAPI corre las dependencias `def` en un hilo aparte. |
| 4c | ¿El UoW expone `commit()`/`rollback()` públicos? | No: la única forma de confirmar es salir del `async with`. | «El servicio nunca hace commit directo» se cumple porque no hay con qué. |
| 4d | Bloques anidados y consecutivos | Un `async with uow` dentro de otro → `RuntimeError` (flag `_abierto`). Bloques consecutivos sobre el mismo UoW se permiten. | Un bloque interno confirmaría a mitad de la operación; la rúbrica mira «operaciones de varias escrituras». |
| 4e | Commit que falla | `__aexit__` hace rollback antes de propagar. | SQLAlchemy deja la sesión inutilizable hasta el rollback. |
| 4f | Sesión propia de `intento_acceso` (DD-05) | Sin código nuevo en CH-02: el patrón sale solo en CH-05 (`async with session_factory() as s: async with IntentosUoW(s): ...`). Se declara en el design y lo respalda un escenario (U10). | El UoW recibe la sesión y no la cierra; un helper sería código para un uso que todavía no existe. |
| 4g | Entidades después del bloque | Con `expire_on_commit=False` el servicio devuelve la entidad después del commit; las relaciones tienen que venir precargadas por el repositorio. | Restricción para el design, no código. |
| 5 | Recorrido de un listado | Dependencia `page`/`size` → servicio: `total = contar` → `calcular_ventana(total, page, size)` → `items = listar(offset, limit)` → `Pagina(...)`. | Ej. 3 y §2.9 de la consigna. |
| 5a | ¿Cómo se reciben `page`/`size`? | Dependencia reutilizable con `Query(ge=1)` y `Query(ge=1, le=100)`, default `page=1`, `size=20`; `size=500` → 422 por contrato. | Un modelo de query params con `extra="forbid"` obligaría a meter los filtros de cada listado en él y rechazaría parámetros desconocidos. |
| 5b | Cero resultados | `pages = max(1, ceil(total / size))`: con `total=0` hay una página vacía; `page=2` → 422. | Literal a «con cero resultados hay una página, vacía»; coincide con DA-14. |
| 5c | Orden de las consultas | Primero `count`, después validar, después el listado. | Una página inexistente no ejecuta la consulta de items. Riesgo aceptado y declarado: con READ COMMITTED, una inserción concurrente entre las dos consultas puede desfasarlas en una fila. |
| 5d | ¿Cómo sale el 422 de página inexistente? | Función pura `calcular_ventana(total, page, size)` que lanza `PaginaInexistente` (de `errores.py`); la traduce la clase de ruta (6e). `paginacion.py` no importa nada HTTP. | Se triangula sin base; `HTTPException` en el core mezclaría capas. |
| 5e | Cuerpo del 422 | `{"detail": "La página 3 no existe: hay 2"}`: `detail` como **string**, con el texto del PDF. Convive con el 422 de validación de FastAPI (`detail` lista). | Texto textual de la consigna; mismo formato que el 503 de CH-01. |
| 5f | Envoltorio | `Pagina[T]` genérico de Pydantic en `paginacion.py`, usado como `response_model=Pagina[XRespuesta]`. Verificar en el apply si la versión instalada de Pydantic acepta PEP 695 o hace falta `Generic[T]`. | Un solo envoltorio para todos los listados. |
| 5g | ¿Quién arma la página? | El servicio; `paginacion.py` ofrece `armar_pagina(items, total, ventana)`. Sin helper que reciba métodos del repositorio como callables. | Ese helper ahorraría tres líneas pero ocultaría las consultas y complicaría los tipos. |
| 6a | ¿Dónde se atrapa el `IntegrityError`? | En `UnitOfWork.__aexit__`, único punto: cubre el de un `flush` dentro del bloque y el del `commit`. Hace rollback y lanza en su lugar la excepción de dominio. | Atraparlo en cada método del repositorio dejaría sin cubrir el del commit y serían dos lugares. |
| 6b | ¿Cómo se elige el mensaje? | Por el nombre de la restricción (asyncpg lo trae en la excepción original junto al `sqlstate`; verificar el atributo en el apply). El mapa nombre → mensaje lo declara el UoW de cada módulo como atributo de clase; sin coincidencia → 409 genérico propio («La operación choca con datos existentes»). | El módulo conoce sus restricciones; un diccionario central acoplaría el core a cada módulo. |
| 6c | ¿Todo `IntegrityError` es 409? | Sí: UNIQUE, FK, CHECK y también NOT NULL, este último con 409 genérico y log de nivel **error** para que el bug se vea del lado del servidor. | DD-04, RN-18 y la regla dura «nunca 500 por un `IntegrityError`». Un CHECK que salta es la red de seguridad de algo que el servicio debía validar (C-11 espera 409). |
| 6d | Jerarquía de excepciones | `ErrorDeDominio(mensaje)` → `NoEncontrado` (404), `Conflicto` (409, incluye los `IntegrityError` traducidos), `PaginaInexistente` (422). Las de 401/403/429 nacen en CH-05/CH-06. El mapa clase → código vive en la capa HTTP: `errores.py` no sabe de HTTP. | Cada capa sabe lo suyo. |
| 6e | ¿Quién convierte la excepción de dominio en HTTP? | **[Alumna]** Opción C: clase de ruta propia `APIRouter(route_class=RutaQueTraduceErrores)` declarada en **cada `router.py`**, implementada una vez en `app/core/rutas.py` («No especificado en la consigna»). Cubre también los errores que salen de las dependencias. Refinamiento **R1** respecto de CHANGES.md (no hay handler en `main.py`). Un test recorre todas las rutas de la app y verifica el `route_class`, excluyendo sólo las propias de FastAPI. `rutas.py` se suma a la estructura de `AGENTS.md`/`CLAUDE.md` al cerrar el change. | Manda la letra del PDF: el router «traduce errores». Un handler global (opción A, lo que decía CHANGES) no deja nada visible en `router.py`; un try/except por ruta (B) se repite en ~30 rutas y olvidarlo da 500. |
| 6e-i | ¿Y las rutas de salud de CH-01? | `app/modules/health/router.py` también declara `route_class`; la suite de CH-01 sigue en verde. | Una regla con excepciones deja de ser regla; salud no lanza errores de dominio, así que no cambia su comportamiento (los 503 siguen como hoy). |
| 6f | Log | En el punto de traducción se registra el nombre de la restricción y el `sqlstate`; al cliente sólo le llega el mensaje propio. | Depurar sin filtrar el esquema (RN-18). |
| 7 | OB-05: ¿contra qué tabla se prueban los repositorios? | Opción B: tablas de prueba creadas con **DDL a mano** (`text()`) en una fixture, y modelos de prueba mapeados a ellas. Ningún `create_all` en ningún lado. **[Alumna]** La fixture que crea y borra las tablas `prueba_*` corre **sólo después** de verificar la base con la guarda de `_test`, aplicada a la misma `Settings` que usa el lifespan. | Cumple la regla dura «NUNCA `create_all`» sin excepción que defender, conserva el paralelismo con CH-03 y fija nombres de restricción conocidos para probar 6b. Descartadas: A (`create_all` en el test), C (CH-02 después de CH-03, fixtures encadenadas al dominio), D (migración de prueba que ensucia `migrations/`). Las tablas `TEMP` no sirven: son por conexión. |
| 7a | Tablas de prueba | `prueba_articulo`: `id`, `nombre` NOT NULL con UNIQUE nombrado, `cantidad` con CHECK nombrado, `creado_en timestamptz DEFAULT now()`. `prueba_baja`: `id`, `nombre`, `borrado_en timestamptz NULL` y **[Alumna]** `articulo_id` nullable con FK nombrada a `prueba_articulo` (para E6). | Cubren `id`, UNIQUE, CHECK, NOT NULL, FK, `server_default` y borrado lógico. |
| 7b | Ciclo de vida | Se crean una vez por sesión de pytest, con `DROP ... IF EXISTS` antes y después; entre tests, `TRUNCATE ... RESTART IDENTITY`. | Sobrevive a una corrida interrumpida. |
| 7c | Metadata | Los modelos de prueba usan un `registry`/`MetaData` propio, no `SQLModel.metadata`. Verificar en el apply cómo lo admite la versión instalada de SQLModel. | Nunca se mezclan con lo que ve Alembic. |
| 7d | Riesgo con CH-03 | Si CH-03 tiene un test de «autogenerate sin diferencias» contra `_test`, una tabla `prueba_*` olvidada aparecería como diferencia; el `DROP` al final de la sesión lo cubre. Va como nota para CH-03. | — |
| 8 | Escenarios | Los 46 escenarios automáticos de la lista de abajo (R1-R11, B1-B5, U1-U10, P1-P7, E1-E6, T1-T5, F1-F2). Sin `.http`: CH-02 no expone endpoints. **[Alumna]** E6 (FK). | Feliz, error y borde por pieza. Se dejaron afuera a propósito: un test de «el UoW no tiene `commit()` público» (sería casi tautológico; lo cubren R11 y 4c). |

## Refinamientos respecto de CHANGES.md

Anotarlos en el proposal, igual que los Desvíos de `CHANGES.md`; no renombran ni reordenan changes.

- **R1**: la traducción de excepciones de dominio a HTTP **no** es un handler registrado en `main.py`, sino la clase de ruta de `app/core/rutas.py`, que cada `router.py` declara con `route_class` (incluido el de salud de CH-01). Motivo: el PDF dice que el router «traduce errores».
- **R2**: CH-02 suma dos archivos al core que la consigna no lista: `app/core/errores.py` y `app/core/rutas.py` («No especificado en la consigna»).

## Escenarios de prueba (8)

### R: `BaseRepository` (tablas `prueba_*`)

| # | Tipo | Escenario |
|---|---|---|
| R1 | feliz | `add` deja el `id` cargado, y `creado_en` (`server_default`) se lee después del flush sin IO implícito. |
| R2 | feliz | Después de `add`, otra sesión **no** ve la fila; después del commit del UoW, sí. |
| R3 | feliz / borde | `get_by_id` de un id existente → la entidad; de uno inexistente → `None`. |
| R4 | feliz / borde | Con 5 filas, `get_all(offset=2, limit=2)` → ids 3 y 4, en orden; con `offset` más allá del final → `[]`. |
| R5 | feliz / borde | `count()` → 5; con la tabla vacía → 0. |
| R6 | feliz | `update(e, {"cantidad": 7})` cambia sólo ese campo, hace flush y otra sesión no lo ve hasta el commit. |
| R7 | error | `update` con una clave que no es campo del modelo → `ValueError` que nombra la clave; la entidad queda sin cambios. |
| R8 | error | `update` con `"id"` en `datos` → `ValueError`. |
| R9 | feliz | `delete` hace flush: dentro del bloque `get_by_id` → `None`; después del commit la fila no está. |
| R10 | feliz | Un método con nombre arma un `stmt` filtrado; `_contar` y `_listar` sobre el mismo `stmt` dan total e items coherentes (se triangula con dos filtros). |
| R11 | estático | Ningún `repository.py` (core y módulos) contiene `.commit(`. |

### B: `SoftDeleteRepository`

| # | Tipo | Escenario |
|---|---|---|
| B1 | feliz | `soft_delete` escribe `borrado_en` con zona UTC; después `get_by_id` → `None`, y `get_all` y `count` la excluyen. |
| B2 | feliz | `get_by_id_including_deleted` devuelve la fila dada de baja. |
| B3 | borde | Un segundo `soft_delete` conserva el `borrado_en` original. |
| B4 | error | Construirlo con un modelo sin `borrado_en` → `TypeError`. |
| B5 | feliz | Un método con nombre de una subclase, armado sobre `_consulta()`, hereda el filtro sin escribirlo. |

### U: `UnitOfWork`

| # | Tipo | Escenario |
|---|---|---|
| U1 | feliz | Al salir sin excepción confirma: otra sesión ve la fila. |
| U2 | error | Error de la base dentro del bloque → rollback; la fila no queda. |
| U3 | error | Se escribe una fila (flush), el servicio lanza una excepción de dominio y la fila no queda en la base. |
| U4 | error | Una excepción cualquiera (`ValueError`) → rollback, y la excepción sale sin cambios. |
| U5 | borde | Por los dos caminos (commit y rollback), la sesión sigue abierta y usable (`SELECT 1` después del bloque). |
| U6 | error | Un `async with uow` dentro de otro → `RuntimeError`; el bloque externo revierte. |
| U7 | borde | Dos bloques consecutivos sobre el mismo UoW: los dos confirman. |
| U8 | error | Fallo en el commit (`session.add` de un duplicado sin flush): rollback, `Conflicto`, y la sesión queda usable. |
| U9 | feliz / error | Un UoW de prueba con dos repositorios escribe en las dos tablas: con éxito confirman juntas; con excepción no queda ninguna. |
| U10 | feliz | Patrón de sesión propia (DD-05): la sesión de la «petición» revierte, la propia confirma y su fila queda. |

### P: paginación

| # | Tipo | Escenario |
|---|---|---|
| P1 | feliz | `calcular_ventana(5, page=1, size=2)` → offset 0, limit 2, 3 páginas; con `page=3` → offset 4. |
| P2 | error | `calcular_ventana(4, page=3, size=2)` → `PaginaInexistente` con el texto exacto «La página 3 no existe: hay 2». |
| P3 | borde | `total=0`: 1 página, `page=1` vale, `page=2` → «La página 2 no existe: hay 1». |
| P4 | borde | `total=100, size=100` → 1 página; `total=101` → 2. |
| P5 | error / borde | Dependencia (app de prueba): sin parámetros → `page=1, size=20`; `size=100` vale; `size=500`, `size=0`, `page=0` y `page=abc` → 422. |
| P6 | feliz | `Pagina[T]` serializa exactamente `{items, total, page, size, pages}`. |
| P7 | feliz | De punta a punta con el repositorio: el `total` cuenta con el mismo filtro que los `items`. |

### E: traducción de `IntegrityError`

| # | Tipo | Escenario |
|---|---|---|
| E1 | error | UNIQUE mapeado → `Conflicto` con el mensaje del módulo; el mensaje no contiene el nombre de la restricción, de la tabla ni de la columna, ni `duplicate`, `violates` o `unique`. |
| E2 | error | CHECK mapeado → `Conflicto` con su mensaje (triangula con E1). |
| E3 | borde | Restricción sin mapear → 409 genérico propio. |
| E4 | error | NOT NULL → 409 genérico y log de nivel ERROR (`caplog`). |
| E5 | feliz | En un caso mapeado, el log tiene el nombre de la restricción y el `sqlstate`; el mensaje al cliente no. |
| E6 | error | Borrar con `delete` (flush, 2f) un `prueba_articulo` referenciado por `prueba_baja.articulo_id` → `Conflicto` con el mensaje mapeado de la FK. |

### T: clase de ruta (`rutas.py`)

| # | Tipo | Escenario |
|---|---|---|
| T1 | feliz | App de prueba con la clase de ruta: `NoEncontrado` → 404, `Conflicto` → 409 y `PaginaInexistente` → 422, con cuerpo `{"detail": "<mensaje>"}`. |
| T2 | feliz | Un error de dominio lanzado desde una dependencia también se traduce. |
| T3 | error | Una excepción que no es de dominio (`ValueError`) no se traduce: sale como 500. |
| T4 | estático | Toda ruta de `main.app` usa la clase de ruta, salvo `/openapi.json`, `/docs`, `/docs/oauth2-redirect` y `/redoc`; la lista verificada no está vacía e incluye `/health/live`. |
| T5 | regresión | La suite de CH-01 sigue en verde después de que salud declara `route_class`. |

### F: arnés de las tablas `prueba_*`

| # | Tipo | Escenario |
|---|---|---|
| F1 | guarda | Con `POSTGRES_DB` que no termina en `_test`, la creación de las tablas falla con el error de la guarda antes de conectarse (apuntando a `puerto_cerrado`: si intentara conectar daría `OSError`). |
| F2 | borde | Crear las tablas cuando ya existen (corrida interrumpida) funciona, por el `DROP ... IF EXISTS` previo. |

## Pedidos para el propose

1. **Refinamientos de alcance**: R1 y R2 (arriba), anotados en el proposal.
2. En el **design**: las firmas de `BaseRepository`/`SoftDeleteRepository` (2, 2a-2g, 3, 3a-3e), el `UnitOfWork` y cómo se compone (4, 4a-4g, incluido el patrón de sesión propia de DD-05), el recorrido de la paginación (5, 5a-5g), la traducción de errores (6a-6f, con el diagrama `flush`/`commit` → `__aexit__` → `Conflicto` → clase de ruta → HTTP) y el arnés de las tablas `prueba_*` (7, 7a-7c, con la guarda antes del DDL).
3. En las **specs**: los 46 escenarios automáticos de arriba, agrupados por requisito (repositorio base, borrado lógico, Unit of Work, paginación, traducción de errores, clase de ruta, arnés).
4. Marcar como **«No especificado en la consigna»**: `app/core/errores.py` y `app/core/rutas.py`, el mensaje del 409 genérico, el `ValueError` de `update`, el `RuntimeError` del anidado y la idempotencia de `soft_delete`.
5. **Verificar en el apply** (contra las versiones instaladas): el atributo por el que se llega a `constraint_name`/`sqlstate` de asyncpg (6b); que el `RETURNING` trae los `server_default` después del flush (2g); PEP 695 en `Pagina[T]` con Pydantic (5f); `registry`/`MetaData` propio para los modelos de prueba en SQLModel (7c).
6. **Acciones con efectos que el apply debe pedir antes de correr**: la corrida de la suite contra `taller_mecanico_test` (crea y borra las tablas `prueba_*`).
7. **Al cerrar el change** (archive): sumar `errores.py` y `rutas.py` a la estructura que describen `AGENTS.md` y `CLAUDE.md`, en los dos archivos.
8. **Notas para CH-03** (no van en CH-02):
   - **Nombres de restricción explícitos y estables**, con una `naming_convention` en `SQLModel.metadata` (o nombres a mano): el mapa restricción → mensaje de cada UoW (6b) depende de ellos; no puede depender de nombres autogenerados.
   - Si CH-03 tiene un test de «autogenerate sin diferencias» contra `_test`, una tabla `prueba_*` olvidada aparecería como diferencia; el `DROP` al final de la sesión de pytest de CH-02 lo cubre (7d).
9. **Nota para los changes de módulo** (CH-05 en adelante): cada `router.py` declara `route_class` de `app/core/rutas.py` (T4 falla si no); cada UoW de módulo declara su mapa restricción → mensaje; la dependencia `get_<modulo>_uow` vive en `router.py` y es `async def`.
