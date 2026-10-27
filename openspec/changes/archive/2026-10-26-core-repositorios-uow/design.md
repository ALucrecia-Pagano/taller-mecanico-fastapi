# Design — CH-02 `core-repositorios-uow`

## Context

CH-01 dejó:
- `app/core/config.py` (`Settings`, `get_settings()` con `lru_cache`);
- `app/core/database.py`: `crear_motor`, `crear_fabrica_de_sesiones` con la `AsyncSession` **de SQLModel** y `expire_on_commit=False`, y `get_session`, que crea la sesión por petición y la **cierra** al terminar;
- `main.py`, con el lifespan y el grupo `rutas_abiertas`;
- `app/modules/health/router.py` (`/health/live`, `/health/ready`, 503 con `HTTPException`);
- el arnés de `test/pytest/`: guarda `_test` en `guarda.py`, `entorno_de_prueba`, `LifespanManager`, `puerto_cerrado` y un único bucle por sesión.

Todavía no hay modelos: CH-03 corre en paralelo.

Motivación y alcance: ver `proposal.md`. Requisitos y escenarios: ver `specs/`. Todas las decisiones salen del explore ([docs/evidencias/explore-CH-02.md](../../../docs/evidencias/explore-CH-02.md)); el número entre paréntesis remite a su tabla.

Restricciones que mandan:
- Ningún `commit()` en repositorios; el servicio nunca construye el UoW; el UoW no cierra la sesión.
- Nunca `create_all`.
- Choque con lo guardado → 409 con mensaje propio, nunca texto de la base ni 500.
- Paginación con `page`/`size`, nunca `limit`/`offset` en la API.
- Todos los handlers y dependencias `async def`.

## Goals / Non-Goals

**Goals:**
- Dejar fija, para todos los módulos, la forma de los repositorios, del UoW, de la paginación y de la traducción de errores, para que cada change de módulo sólo agregue sus repositorios, su UoW con su mapa de restricciones y su router con `route_class`.
- Probar todo eso sin modelos del dominio y sin `create_all`.

**Non-Goals:**
- Precarga (`selectinload`/`joinedload`): se declara en los métodos con nombre de cada repositorio de entidad.
- El repositorio de sólo lectura de `estado_orden` y los UoW de módulo.
- Las excepciones de 401, 403 y 429.
- Un helper que abra sesión + UoW para DD-05 (4f).

## Decisions

### D1. Archivos (1, 1-E, 6e)

```
app/core/repository.py      BaseRepository[T], SoftDeleteRepository[T]
app/core/unit_of_work.py    UnitOfWork
app/core/paginacion.py      parametros_de_pagina, Ventana, calcular_ventana, Pagina[T], armar_pagina
app/core/errores.py         ErrorDeDominio, NoEncontrado, Conflicto, PaginaInexistente, traductor de IntegrityError
app/core/rutas.py           RutaQueTraduceErrores (clase de ruta) + mapa excepción -> código HTTP
app/modules/health/router.py   (modificado) APIRouter(..., route_class=RutaQueTraduceErrores)

test/pytest/tablas_de_prueba.py   DDL a mano + modelos de prueba (MetaData propia) + crear/borrar con guarda
test/pytest/conftest.py           (modificado) fixtures de sesión: tablas prueba_* y fábrica de sesiones de prueba
test/pytest/test_repositorio.py   R1-R11, B1-B5
test/pytest/test_unit_of_work.py  U1-U10
test/pytest/test_paginacion.py    P1-P7
test/pytest/test_errores.py       E1-E6
test/pytest/test_rutas.py         T1-T4  (T5 = la suite de CH-01)
test/pytest/test_tablas_de_prueba.py  F1-F2
```

`errores.py` y `rutas.py` son **No especificado en la consigna** (R2). Las excepciones viven en su propio archivo porque mezclarlas en `unit_of_work.py` o en `repository.py` rompería «cada capa sabe lo suyo» (decisión de la alumna). `errores.py` no importa nada de FastAPI: lo HTTP vive sólo en `rutas.py`.

### D2. `BaseRepository[T]` (2, 2a-2g)

```
BaseRepository[T: SQLModel]
  __init__(session, modelo: type[T])
  _consulta()                  -> select(modelo)                     punto único de partida
  _por_id(stmt, id)            -> T | None                           stmt.where(modelo.id == id)
  _listar(stmt, offset, limit) -> list[T]                            ORDER BY id + OFFSET/LIMIT
  _contar(stmt)                -> int                                SELECT count(*) FROM (stmt) sub

  get_by_id(id)                -> _por_id(_consulta(), id)
  get_all(offset, limit)       -> _listar(_consulta(), offset, limit)
  count()                      -> _contar(_consulta())
  add(entidad)                 -> session.add + flush; devuelve la entidad
  update(entidad, datos: dict) -> valida claves; setattr; flush; devuelve la entidad
  delete(entidad)              -> session.delete + flush
```

- **2a. Filtros.** La base no filtra. Los listados con filtro son métodos con nombre en el repositorio de cada entidad, que parten de `self._consulta().where(...)` y pasan **el mismo `stmt`** a `_listar` y `_contar`. Así, «`total` con los mismos filtros» se cumple por construcción.
  *Alternativa descartada:* `get_all(filtros=[...])`, porque el servicio terminaría armando expresiones del ORM.
- **2b. Orden.** `ORDER BY id` ascendente por defecto, porque sin orden las páginas son inestables. Los métodos con nombre pueden pasar otro orden. Todo `T` tiene `id`; el catálogo, que no lo tiene, no hereda.
- **2c. `offset`/`limit` en el repositorio.** `paginacion.py` traduce `page`/`size`. La prohibición de la regla dura es para la API.
- **2d. `get_by_id` con `select`** y no con `session.get`: `session.get` no admite filtros y devuelve el identity map sin ir a la base.
- **2e. `update(entidad, datos)`.** `datos` es `model_dump(exclude_unset=True)` del DTO de PATCH. **Antes de aplicar nada**, cada clave se valida contra los campos del modelo (`modelo.model_fields`). Una clave desconocida o `id` → `ValueError` que nombra la clave, y la entidad queda intacta. No se confía en `setattr`, porque un modelo `table=True` no valida asignaciones. Es un error de programación y no se traduce (decisión de la alumna; **No especificado en la consigna**).
- **2f. `delete` hace flush**, para que una FK violada salte en la llamada y se traduzca igual que el resto (E6).
- **2g. Defaults de la base.** Sin `refresh`. Se confía en que SQLAlchemy 2.0 con Postgres trae los `server_default` por `RETURNING` en el INSERT, y lo prueba R1 (ver V2).

### D3. `SoftDeleteRepository[T]` (3, 3a-3e)

```
SoftDeleteRepository(BaseRepository)
  __init__: si modelo no tiene borrado_en -> TypeError (3c)
  _consulta() -> super()._consulta().where(modelo.borrado_en.is_(None))     único override
  get_by_id_including_deleted(id) -> _por_id(select(modelo), id)            (3a)
  soft_delete(entidad): si borrado_en es None -> borrado_en = datetime.now(timezone.utc); flush   (3b, 3d)
```

- **3a.** No hay un flag `incluir_borrados`, que sería más fácil de usar mal.
- **3b.** La hora sale de Python con UTC y no de `func.now()`: una expresión SQL asignada queda expirada después del flush, y leerla dispara IO implícito.
- **3d.** Es idempotente: una segunda baja conserva la fecha original. Lanzar error sería una regla de negocio en el repositorio (**No especificado en la consigna**).
- **3e.** El `delete` físico heredado no se redefine: la consigna dice «hereda» y «agrega». Ningún servicio de vehículos o repuestos lo usa.

### D4. `UnitOfWork` (4, 4a-4g)

```
UnitOfWork
  mensajes_de_restriccion: ClassVar[dict[str, str]] = {}     cada UoW de módulo declara el suyo (6b)
  __init__(session)
  __aenter__(): si _abierto -> RuntimeError (4d); _abierto = True; return self
  __aexit__(tipo, exc, tb):
      _abierto = False
      si hubo excepción:
          await session.rollback()
          si es IntegrityError -> raise traducir_integrity_error(exc, mensajes_de_restriccion) from exc
          return False                                    (la excepción sigue sin cambios: U4)
      try: await session.commit()
      except IntegrityError as e: await session.rollback(); raise traducir_...(e, ...) from e   (4e, U8)
      nunca session.close()
```

- **Cualquier excepción revierte**, también las de dominio que lanza el servicio después de un flush (decisión de la alumna; U3).
- **4a.** Los UoW de módulo crean sus repositorios en `__init__`, todos con `session`:
  ```
  class UsuariosUoW(UnitOfWork):
      mensajes_de_restriccion = {"uq_usuario_email": "Ya existe un usuario con ese correo", ...}
      def __init__(self, session):
          super().__init__(session)
          self.usuarios = UsuarioRepository(session)
  ```
- **4b.** La dependencia vive en el `router.py` de cada módulo y es `async def` (las `def` corren en un hilo aparte):
  `async def get_<modulo>_uow(session: SesionDep) -> <Modulo>UoW: return <Modulo>UoW(session)`.
  El router la pasa al servicio sin abrirla, y el servicio hace `async with uow:`.
- **4c.** No hay `commit()` ni `rollback()` públicos: la única forma de confirmar es salir del bloque.
- **4d.** Anidar → `RuntimeError` (**No especificado en la consigna**). Como esa excepción sale por el bloque externo, ese bloque revierte (U6). Los bloques consecutivos se permiten, y SQLAlchemy arranca solo la transacción siguiente (U7).
- **4f. DD-05.** En CH-05: `async with session_factory() as s: async with IntentosUoW(s): ...`. Funciona porque el UoW recibe la sesión y no la cierra. CH-02 sólo lo prueba (U10).
- **4g.** Con `expire_on_commit=False`, el servicio devuelve la entidad después del bloque y el router la serializa sin IO. Las relaciones tienen que venir precargadas por el repositorio.

### D5. Paginación (5, 5a-5g)

```
parametros_de_pagina(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)) -> ParametrosDePagina   (async def)
calcular_ventana(total, page, size) -> Ventana(offset, limit, pages)
    pages = max(1, ceil(total / size))
    page > pages -> PaginaInexistente(f"La página {page} no existe: hay {pages}")
Pagina[T](BaseModel): items: list[T], total: int, page: int, size: int, pages: int
armar_pagina(items, total, page, size, ventana) -> Pagina

servicio:  total = await uow.repo.contar_x(...)
           ventana = calcular_ventana(total, p.page, p.size)
           items = await uow.repo.listar_x(..., ventana.offset, ventana.limit)
           return armar_pagina(items, total, p.page, p.size, ventana)
```

- **5a.** Se usa una dependencia con `Query` y no un modelo de query params con `extra="forbid"`, que obligaría a meter los filtros en él.
- **5b.** Con `total=0` hay una página vacía (coincide con DA-14).
- **5c.** El orden es `count` → validar → listar: una página inexistente no consulta filas. Riesgo declarado más abajo.
- **5d.** `calcular_ventana` es pura y se triangula sin base.
- **5e.** `detail` es un **string** con el texto exacto del PDF. Convive con el 422 de validación de FastAPI, que trae `detail` como lista.
- **5f.** `Pagina[T]` es genérico (ver V3).
- **5g.** El servicio arma la página: no hay un helper que reciba métodos del repositorio como callables.

### D6. Errores de dominio y traducción (6a-6f)

```
repo.add/update/delete -> flush --IntegrityError--+
                                                  +--> UnitOfWork.__aexit__: rollback
session.commit()           --IntegrityError-------+          |
                                                             v
                     traducir_integrity_error(error, mensajes_de_restriccion) -> Conflicto
                       nombre = restricción violada; sqlstate = código de la base   (V1)
                       nombre en el mapa          -> Conflicto(mensaje del módulo)      log WARNING
                       nombre fuera del mapa      -> Conflicto(MENSAJE_GENERICO)        log WARNING
                       sqlstate 23502 (NOT NULL)  -> Conflicto(MENSAJE_GENERICO)        log ERROR (6c)
                                                             |
servicio (no lo atrapa) -----------------------------------> |
                                                             v
router: APIRouter(route_class=RutaQueTraduceErrores)
   NoEncontrado -> 404 | Conflicto -> 409 | PaginaInexistente -> 422     {"detail": mensaje}
   otra excepción -> no se toca (500: un bug se ve como bug)
```

- **6a.** Hay un único punto de captura, `__aexit__`, que cubre el `flush` dentro del bloque y el `commit`. Se lanza `Conflicto(...) from error`: la causa queda para el log, nunca para la respuesta.
- **6b.** El mapa nombre → mensaje es un atributo de clase del UoW de cada módulo; la base lo consulta. Sin coincidencia, sale `MENSAJE_GENERICO = "La operación choca con datos existentes"` (**No especificado en la consigna**). Los nombres estables los pone CH-03 (ver notas).
- **6c.** Todo `IntegrityError` es 409: UNIQUE, FK, CHECK y NOT NULL. NOT NULL lleva log de nivel `ERROR`, porque es un bug que el contrato debía impedir.
- **6d.** La jerarquía es `ErrorDeDominio(mensaje)` → `NoEncontrado`, `Conflicto`, `PaginaInexistente`. Las clases no conocen su código HTTP: el mapa vive en `rutas.py`.
- **6e. Opción C** (decisión de la alumna, R1):
  - `RutaQueTraduceErrores(APIRoute)` redefine `get_route_handler()`. Envuelve el handler original en un `try/except ErrorDeDominio` que devuelve un `JSONResponse(status_code=MAPA[type], content={"detail": mensaje})`, buscando por la clase más específica en el MRO.
  - Como el handler de la ruta resuelve también las dependencias, cubre los errores lanzados en ellas (T2).
  - Cada `router.py` lo declara: `APIRouter(prefix=..., tags=..., route_class=RutaQueTraduceErrores)`.
  - `app/modules/health/router.py` también (6e-i): su `HTTPException(503)` no es de dominio y sigue igual.
  - Descartadas: handler global en `main.py` (A), porque no deja nada visible en el router que el PDF dice que traduce, y try/except por ruta (B), porque se repite y olvidarlo da 500.
- **6f.** Log con `logging.getLogger(__name__)` en `errores.py`: restricción y SQLSTATE. Al cliente sólo llega el mensaje propio.

### D7. Tablas de prueba (7, 7a-7d)

```
prueba_articulo:
  id         serial PRIMARY KEY
  nombre     text NOT NULL            CONSTRAINT uq_prueba_articulo_nombre UNIQUE
  cantidad   integer NOT NULL DEFAULT 0  CONSTRAINT ck_prueba_articulo_cantidad CHECK (cantidad >= 0)
  creado_en  timestamptz NOT NULL DEFAULT now()

prueba_baja:
  id          serial PRIMARY KEY
  nombre      text NOT NULL
  articulo_id integer NULL  CONSTRAINT fk_prueba_baja_articulo_id REFERENCES prueba_articulo(id)
  borrado_en  timestamptz NULL
```

- **Opción B.** DDL escrito a mano y ejecutado con `text()`, sin `create_all` en ningún lado. Las tablas `TEMP` no sirven, porque son por conexión y R2/U1 usan dos conexiones.
- **Guarda primero** (decisión de la alumna). `crear_tablas_de_prueba(settings)` llama a `verificar_base_de_prueba(settings)` **antes** de crear el motor. `settings` es la de `get_settings()` después de fijar `POSTGRES_DB=<base>_test` en el entorno (`pytest.MonkeyPatch.context()` en una fixture de sesión) y de `cache_clear()`: la misma resolución que usa el lifespan. F1 lo prueba con `puerto_cerrado`.
- **7b. Ciclo de vida:**
  - fixture de **sesión**: `DROP TABLE IF EXISTS prueba_baja, prueba_articulo` → `CREATE` al empezar, y `DROP` al terminar;
  - fixture **por test**: `TRUNCATE prueba_baja, prueba_articulo RESTART IDENTITY`, para que R4 espere ids 3 y 4.
- **Motor y sesiones de prueba.** Se crean con `crear_motor` y `crear_fabrica_de_sesiones` de CH-01, sin levantar la app; T1-T4 sí usan apps.
- **7c. Modelos de prueba.** `ArticuloDePrueba` y `BajaDePrueba` llevan `table=True` sobre una `MetaData` propia, **no** `SQLModel.metadata` (ver V4), y viven en `test/pytest/tablas_de_prueba.py`.
- **UoW de prueba.** `UoWDePrueba(UnitOfWork)` declara `articulos` y `bajas`, y un mapa para `uq_prueba_articulo_nombre`, `ck_prueba_articulo_cantidad` y `fk_prueba_baja_articulo_id`. E3 usa una variante sin mapa.

### D8. Escenarios (8)

Los 46 escenarios del explore están en `specs/` con sus IDs:

| Grupo | Escenarios | Spec |
|---|---|---|
| R | R1-R11 | `repositorios` |
| B | B1-B5 | `repositorios` |
| U | U1-U10 | `unidad-de-trabajo` |
| P | P1-P7 | `paginacion` |
| E | E1-E6 | `errores-de-dominio` |
| T | T1-T5 | `errores-de-dominio` |
| F | F1-F2 | `suite-de-pruebas` |

- T4 recorre `main.app.routes`, excluye `/openapi.json`, `/docs`, `/docs/oauth2-redirect` y `/redoc`, y verifica que cada `APIRoute` sea instancia de `RutaQueTraduceErrores`. Además, que el conjunto no esté vacío y contenga `/health/live`.
- T5 no es un test nuevo: es la suite de CH-01 en verde.

## Puntos a verificar contra las versiones instaladas

Se resuelven en el apply, cada uno con el test que lo cubre. El resultado se anota en el resumen del apply:

- **V1** (6b, E1-E6): por qué atributo se llega al nombre de la restricción y al SQLSTATE con asyncpg a través del `IntegrityError` de SQLAlchemy (`error.orig.__cause__.constraint_name`, `error.orig.sqlstate` u otro).
- **V2** (2g, R1): que después del `flush` de un INSERT, `creado_en` (`server_default`) queda cargado sin IO implícito.
- **V3** (5f, P6): si la versión instalada de Pydantic acepta `class Pagina[T](BaseModel)` (PEP 695) o hace falta `Generic[T]`.
- **V4** (7c): cómo declarar modelos `table=True` de SQLModel sobre una `MetaData` o un `registry` propio, sin registrarlos en `SQLModel.metadata`.

## Notas para los changes siguientes

**Para CH-03** (no van en CH-02):
- **Nombres de restricción explícitos y estables**, con una `naming_convention` en `SQLModel.metadata` (o nombres a mano). El mapa restricción → mensaje de cada UoW (D6) depende de ellos; no puede depender de nombres autogenerados.
- Si CH-03 tiene un test de «autogenerate sin diferencias» contra `_test`, una tabla `prueba_*` olvidada aparecería como diferencia. El `DROP` al final de la sesión de pytest de CH-02 lo cubre (7d).

**Para los changes de módulo** (CH-05 en adelante):
- cada `router.py` declara `route_class=RutaQueTraduceErrores` (T4 falla si no);
- cada UoW de módulo declara `mensajes_de_restriccion`;
- `get_<modulo>_uow` vive en `router.py` y es `async def`;
- los listados usan `parametros_de_pagina`, `calcular_ventana` y `armar_pagina`.

## Risks / Trade-offs

- **[`include_router` y la clase de ruta]** → *Corregido en el apply, contra FastAPI 0.162.0.* `include_router` ya **no copia** las rutas: agrega a `routes` un envoltorio interno (`_IncludedRouter`) que referencia al router original (`original_router`) y lo despacha con el contexto del include (prefijo, dependencias). La clase de ruta se conserva, porque la ruta que atiende es la del router original: verificado con dos niveles de `include_router`, y una ruta que lanza un error de dominio responde con su código traducido. T4 recorre `main.app.routes` descendiendo por `original_router`. Si ese atributo interno desaparece en otra versión, T4 falla en rojo (`AttributeError`, o la aserción de `/health/live`) y no pasa en vacío, porque se verificó quitándolo a mano.
- **[La regla de CH-01 «`include_router` copia las rutas que el grupo tiene en ese momento» ya no aplica con FastAPI 0.162]** → Un router agregado a un grupo **después** de incluir el grupo en la app sí aparece: responde y figura en OpenAPI. Igual se mantiene el orden de CH-01 (primero se arman los grupos con todos sus routers y al final se incluyen en la app), por compatibilidad con versiones anteriores y porque no cuesta nada.
- **[Un router nuevo se olvida de `route_class`]** → T4 falla en la suite.
- **[`total` e `items` desfasados por una inserción concurrente entre el `count` y el listado (READ COMMITTED)]** → aceptado y declarado; irrelevante para el TP.
- **[DDL de prueba y modelo de prueba divergen]** → son dos tablas chicas, y cualquier divergencia rompe R1-R10 al instante.
- **[Una tabla `prueba_*` queda en `_test` tras una corrida abortada]** → `DROP ... IF EXISTS` al empezar (F2) y al terminar.
- **[`soft_delete` con el reloj de la app y no el de la base]** → un solo proceso, sin impacto.
- **[Un NOT NULL como 409 oculta un bug al cliente]** → log de nivel `ERROR` en el servidor (E4).

## Migration Plan

Sin migraciones ni cambios de esquema en la aplicación. Las tablas `prueba_*` existen sólo durante la corrida de la suite en `taller_mecanico_test`. Para revertir, se borran los archivos nuevos y se restaura `app/modules/health/router.py`.
