# CHANGES — Secuencia de Implementación

> Índice canónico de todos los changes del proyecto **Taller Mecánico** (TP integrador de Programación III, prof. Giuliano).
> Cada change es una funcionalidad completa y chica: un agente puede implementarlo en una sesión.
> **Leer este archivo antes de ejecutar cualquier `/opsx:propose`.**
>
> **IDs**: los changes se llaman `CH-01 … CH-11`. Los `C-01 … C-19` son SIEMPRE los casos de prueba de la consigna (ver `knowledge-base/11_casos_de_prueba.md`), nunca changes.
> **Gobernanza**: BAJO = LOW, MEDIO = MEDIUM, ALTO = HIGH, CRITICO = CRITICAL (tabla de autonomía del `AGENTS.md`).
> **Alcance**: exactamente el de la consigna. No hay sección de futuro ni backlog.

---

## Cómo usar este documento

1. Identificá el próximo change con `[ ]` cuyas dependencias estén todas en `[x]` (mirá el árbol y los GATES).
2. Leé los archivos de la KB que figuran en **Leer antes** de ese change, y las filas de `09_decisiones_y_supuestos.md` que cita (DA-NN, DD-NN, SU-NN).
3. Corré `/opsx:propose <nombre-kebab>` (por ejemplo `/opsx:propose proyecto-config-salud`) y después `/opsx:apply`. Cada change se implementa con **TDD estricto** (primero el test que falla, después el código mínimo).
4. Cuando el change termina y sus `.http` / pytest pasan, `/opsx:archive <nombre-kebab>`.
5. Marcá el checkbox `[x]` en **Estado** de este archivo y actualizá las tablas de cobertura si cambió algo.

### Reglas transversales de verificación (valen para todos los changes)

- **Dos capas de prueba** por change: (a) la suite **pytest + pytest-asyncio + httpx** contra una **base de datos de prueba separada**, escrita test-first; (b) los archivos `.http` de `test/` con la respuesta esperada en un comentario (el PDF los exige), que se corren después de `python seed.py`.
- **Base de prueba separada**: nunca la base de desarrollo. El nombre se deriva de `POSTGRES_DB` (`<POSTGRES_DB>_test`) dentro del `conftest.py`, y el `conftest.py` **se niega a correr** si el nombre no termina en `_test` (el seed y las fixtures vacían tablas). El esquema de esa base se crea con `alembic upgrade head`, nunca con `create_all` en el código de la aplicación.
- **Dónde vive la suite pytest**: `test/pytest/` (con su `conftest.py`); las dependencias de prueba en `requirements-dev.txt` (DA-26). Los `.http` y `solo_agregado.sql` siguen en la raíz de `test/`.
- Los changes que no exponen endpoints (CH-02, CH-04) se prueban sólo con pytest; lo declaran en su ficha.
- El PDF reserva `test/` para los `.http` y `solo_agregado.sql`: los archivos pytest NO van ahí.

---

## Árbol de dependencias

```
CH-01 proyecto-config-salud                         (Ej. 1)
 ├── CH-02 core-repositorios-uow                    (Ej. 6 base, Ej. 3 paginación)
 │     │
 │     │   (CH-02 y CH-03 corren en paralelo)
 │     │
 ├── CH-03 modelos-migraciones                      (Ej. 2, Ej. 7 disparador)
 │     └── CH-04 seguridad-base-seed                (Ej. 4 base)
 │
 └── (CH-02 ✓ + CH-04 ✓)
       └── CH-05 autenticacion                      (Ej. 4, Ej. 7 intento de acceso)
             └── CH-06 autorizacion-usuarios-roles  (Ej. 5)
                   ├── CH-07 clientes-vehiculos     (Ej. 3, Ej. 6)      ─┐
                   └── CH-08 repuestos-stock-precios (Ej. 3, 6, 7)        ├─ ambos ✓
                                                                          ▼
                                       CH-09 ordenes-alta-consulta        (Ej. 6, 8)
                                             └── CH-10 ordenes-ciclo-aviso (Ej. 6, 8)
                                                   └── CH-11 cierre-entrega (entrega + auditoría)
```

Dependencias explícitas:

| Change | Depende de |
|--------|-----------|
| CH-01 | ninguna |
| CH-02 | CH-01 |
| CH-03 | CH-01 |
| CH-04 | CH-01, CH-03 |
| CH-05 | CH-02, CH-03, CH-04 |
| CH-06 | CH-05 |
| CH-07 | CH-02, CH-06 |
| CH-08 | CH-02, CH-06 |
| CH-09 | CH-07, CH-08 |
| CH-10 | CH-09 (y CH-08 por el punto único de stock) |
| CH-11 | CH-10 (todos) |

### Paralelismo por fase

```
GATE 0: —                                                      ← arranque
  → CH-01 proyecto-config-salud                 [Agente A]

GATE 1: CH-01 ✓                                                ← FORK (2 ramas)
  → CH-03 modelos-migraciones                   [Agente A]   (camino crítico)
  → CH-02 core-repositorios-uow                 [Agente B]   (se prueba con una tabla propia del test; ver OB-05)

GATE 2: CH-03 ✓
  → CH-04 seguridad-base-seed                   [Agente A]
  (CH-02 puede seguir corriendo en [Agente B])

GATE 3: CH-02 ✓ y CH-04 ✓
  → CH-05 autenticacion                         [Agente A]

GATE 4: CH-05 ✓
  → CH-06 autorizacion-usuarios-roles           [Agente A]

GATE 5: CH-06 ✓                                                ← FORK (2 ramas)
  → CH-07 clientes-vehiculos                    [Agente A]
  → CH-08 repuestos-stock-precios               [Agente B]

GATE 6: CH-07 ✓ y CH-08 ✓
  → CH-09 ordenes-alta-consulta                 [Agente A]

GATE 7: CH-09 ✓
  → CH-10 ordenes-ciclo-aviso                   [Agente A]

GATE 8: CH-10 ✓
  → CH-11 cierre-entrega                        [Agente A]   + revisión [Agente C]
```

Puntos de choque a coordinar cuando hay dos agentes a la vez: `main.py` (registro de routers) en los GATES 1 y 5, y `requirements.txt`. Son conflictos triviales de merge; no hay migraciones nuevas después de CH-03, así que no hay choque de revisiones de Alembic.

### Camino crítico (9 changes — mínimo irreducible)

```
CH-01 → CH-03 → CH-04 → CH-05 → CH-06 → CH-07* → CH-09 → CH-10 → CH-11
                                          CH-08*
```

`CH-07*` y `CH-08*`: los dos son necesarios para CH-09 y son hermanos; el camino mide lo mismo por cualquiera de los dos. `CH-02` queda fuera del camino crítico porque corre en paralelo con CH-03 y CH-04, pero **debe estar terminado antes de CH-05**.

### Plan óptimo con 3 agentes

> Este proyecto es sólo backend: no hay frontend. El «Agente C» se usa como **verificación independiente** (revisión del TDD, evidencias, auditoría contra la consigna), no como tercera línea de código. El paralelismo real es de 2 agentes y sólo en dos tramos (pasos 2-3 y 6). Si trabaja una sola persona/agente, el orden lineal por número de CH es válido.

| Paso | Agente A (camino crítico: seguridad y órdenes) | Agente B (core y dominio auxiliar) | Agente C (verificación) |
|------|-----------------------------------------------|------------------------------------|-------------------------|
| 1 | CH-01 proyecto-config-salud | — | — |
| 2 | CH-03 modelos-migraciones | CH-02 core-repositorios-uow | — |
| 3 | CH-04 seguridad-base-seed | (cierra CH-02 si falta) | — |
| 4 | CH-05 autenticacion | — | — |
| 5 | CH-06 autorizacion-usuarios-roles | — | — |
| 6 | CH-07 clientes-vehiculos | CH-08 repuestos-stock-precios | — |
| 7 | CH-09 ordenes-alta-consulta | — | — |
| 8 | CH-10 ordenes-ciclo-aviso | — | — |
| 9 | CH-11 cierre-entrega (README, evidencias) | — | CH-11 auditoría contra la consigna |

---

## FASE 1 — Fundaciones

> CH-02 y CH-03 son independientes entre sí y pueden ir en paralelo después de CH-01.

### [CH-01] `proyecto-config-salud`
- **Estado**: `[x]` completado (verify: `docs/evidencias/verify-CH-01.md`)
- **Ejercicio / peso**: Ej. 1 — Proyecto, configuración y ciclo de vida (**8 %**).
- **Scope**:
  - Estructura de carpetas obligatoria: `main.py`, `seed.py` (vacío por ahora), `app/core/`, `app/modules/{health,usuarios,clientes,repuestos,ordenes}/`, `migrations/`, `test/`, `requirements.txt` (con mínimos de la consigna), `.gitignore` (con `.env`).
  - `app/core/config.py`: `Settings` (pydantic-settings) con `@computed_field` para la URL `postgresql+asyncpg://…`; **sin default** en `POSTGRES_PASSWORD` y `JWT_SECRET_KEY` (la app no arranca si faltan); el resto con los defaults de DA-07 (`JWT_ALGORITHM`, `JWT_EXPIRE_SECONDS`, `BCRYPT_COST`, `BCRYPT_MAX_CONCURRENCY`, `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `COOKIE_SECURE`, `SQL_ECHO`, `LOGIN_MAX_FALLOS`, `LOGIN_VENTANA_SEGUNDOS`).
  - `env.example` con **todas** las variables (las dos sensibles vacías) y el comentario de cómo generar la clave: `python -c "import secrets; print(secrets.token_urlsafe(64))"`.
  - `app/core/database.py`: funciones que crean el motor async (con pool configurado, `echo=SQL_ECHO`) y la fábrica de sesiones (`expire_on_commit=False`); `get_session` toma la fábrica de `app.state`, una sesión por petición, la cierra al terminar.
  - `main.py`: `lifespan` que crea motor y fábrica y los guarda en `app.state`, y en el apagado hace `dispose()`. Registra el grupo **abierto** con el router de salud. (El hash ficticio del login se agrega en CH-04: ver OB-03.)
  - `app/modules/health/router.py`: `GET /health/live` (200, sin tocar la base) y `GET /health/ready` (`SELECT 1` → 200; si la base no contesta → 503).
  - Alembic inicializado con la **plantilla asincrónica** (`alembic init -t async migrations`): `alembic.ini` **sin credenciales**, `migrations/env.py` toma la URL de `Settings`. Sin migraciones todavía.
  - Arnés de pruebas en `test/pytest/` (DA-26): `pytest.ini`/`pyproject` con `asyncio_mode`, `test/pytest/conftest.py` con la base `<POSTGRES_DB>_test` y la guarda `_test` (DA-29), el cliente `httpx.AsyncClient` y el manejo del lifespan (ver OB-06); `requirements-dev.txt` con `pytest`, `pytest-asyncio`, `httpx` y lo que pida el lifespan.
  - Tests pytest (test-first): `Settings` falla sin `POSTGRES_PASSWORD`/`JWT_SECRET_KEY`; la URL calculada tiene el driver `asyncpg`; `/health/live` 200 sin base; `/health/ready` 200 y 503 (motor apuntando a una base caída); `get_session` entrega una sesión por petición y la cierra; `app.state` queda poblado por el lifespan.
  - `.http` propios: `test/health.http` (humo de salud; **no corresponde a ningún C-NN**).
- **RN cubiertas**: ninguna de negocio (cumple los requisitos no funcionales de Credenciales, Esquema, Asincronía).
- **DA / DD aplicados**: DA-07, DD-11, DD-12, DD-A4.
- **Casos C-NN propios**: ninguno.
- **Dependencias**: ninguna
- **Governance**: MEDIO — punto de control: que `.env` esté ignorado y que ningún secreto tenga valor por defecto (condición excluyente de la entrega).
- **Leer antes**:
  - `knowledge-base/02_descripcion_general.md` §Stack tecnológico y §Arquitectura general
  - `knowledge-base/06_funcionalidades.md` §Épica 1 (US-001 a US-003)
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios, §Variables de entorno, §Seguridad (Secretos)
  - `knowledge-base/09_decisiones_y_supuestos.md` DA-07, DD-A4
  - `knowledge-base/12_criterios_de_evaluacion.md` §Condiciones excluyentes

### [CH-02] `core-repositorios-uow`
- **Estado**: `[x]` completado (verify: `docs/evidencias/verify-CH-02.md`). Refinamientos R1 (la traducción de errores la declara cada router con `route_class`, sin handler en `main.py`) y R2 (`app/core/errores.py` y `app/core/rutas.py`): ver el change archivado.
- **Ejercicio / peso**: Ej. 6 — Repositorios y Unit of Work (**20 %**, base) y parte de Ej. 3 (paginación, 10 %).
- **Scope**:
  - `app/core/repository.py`: `BaseRepository[T]` (recibe sesión y **clase del modelo**; `get_by_id`, `get_all`, `count`, `add`, `update`, `delete`; `add`/`update` hacen `flush()`, **nunca `commit()`**) y `SoftDeleteRepository[T]` (hereda; filtra los dados de baja; agrega `get_by_id_including_deleted` y `soft_delete` que escribe `borrado_en`).
  - `app/core/unit_of_work.py`: `UnitOfWork` base, gestor de contexto async: confirma al salir, revierte con excepción, **no cierra la sesión**; el servicio nunca lo construye.
  - `app/core/paginacion.py`: envoltorio genérico `{items, total, page, size, pages}`; `page` ≥ 1, `size` 1..100 (default 20); página más allá de la última → 422 con mensaje («La página 3 no existe: hay 2»); cero resultados → una página vacía; dependencia/parámetros reutilizables.
  - Traducción de `IntegrityError` a excepciones de dominio (409 con mensaje propio, sin texto de la base ni nombre de constraint) y su traducción a HTTP: utilidad central reutilizada por todos los módulos (RN-18, DD-04). Handler de excepciones de dominio → HTTP registrado en `main.py`.
  - Tests pytest (test-first, sin endpoints): `add`/`update` hacen flush y no commit (otra sesión no ve el dato hasta el commit); `SoftDeleteRepository` oculta y recupera con `get_by_id_including_deleted`; UoW confirma, revierte con excepción y deja la sesión abierta; paginación (caso feliz, `size=500`, `page` inexistente, cero resultados, `pages`); traducción de `IntegrityError` no filtra texto interno (triangular con unique y check). Se prueba con una tabla propia del test (ver OB-05).
  - `.http`: ninguno (no expone endpoints).
- **RN cubiertas**: RN-18 (traducción del `IntegrityError`, ninguna entrada inválida en 500) y la parte de 409 de RN-01.
- **DA / DD aplicados**: DD-04, DD-05 (declara el patrón de sesión propia), DA-21 (`get_by_id_including_deleted`), DA-00.
- **Casos C-NN propios**: ninguno (habilita C-02, C-16, C-19, C-11).
- **Dependencias**: `CH-01`
- **Governance**: MEDIO — es la columna vertebral de transacciones; sin commit en repositorios ni UoW construido en servicios.
- **Leer antes**:
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones aplicados y §Responsabilidades por capa
  - `knowledge-base/06_funcionalidades.md` §Épica 6 (US-050, US-051) y §Épica 3 (US-021)
  - `knowledge-base/05_reglas_de_negocio.md` RN-18 y §Excepciones globales (Transacciones, Errores, Unicidad)
  - `knowledge-base/02_descripcion_general.md` §Convenciones transversales de la API

### [CH-03] `modelos-migraciones`
- **Estado**: `[x]` completado (verify: `docs/evidencias/verify-CH-03.md`). Refinamientos R1 (enum `CodigoEstado`), R2 (convención de nombres en `app/core/database.py`), R3 (`import sqlmodel` en `script.py.mako`) y R4 (captura de C-14 en CH-04): ver el change archivado.
- **Ejercicio / peso**: Ej. 2 — Modelos, relaciones y migraciones (**14 %**) y Ej. 7 — Integridad, disparador (**10 %**).
- **Scope**:
  - Modelos SQLModel con los **nombres obligatorios** de tablas y columnas, en sus módulos: `usuarios` (`Usuario`, `AsignacionRol`, `IntentoAcceso`, `EventoSeguridad`), `clientes` (`Cliente`, `Vehiculo`), `repuestos` (`Repuesto`, `MovimientoStock`, `HistorialPrecio` → `historial_precio_repuesto`), `ordenes` (`OrdenTrabajo`, `EstadoOrden`, `ItemOrden`, `HistorialEstadoOrden`). Enums espejo `Rol` y `EstadoOrden` (**R1 de CH-03**: el enum de los estados se llama `CodigoEstado`, porque `EstadoOrden` es la clase del catálogo en el mismo módulo).
  - Restricciones: UNIQUE (`usuario.email`, `cliente.usuario_id`, `cliente.documento`, `estado_orden.posicion`, `item_orden(orden_id, repuesto_id)`); tres **índices únicos parciales** con `postgresql_where` (`asignacion_rol(usuario_id, rol) WHERE revocada_en IS NULL`, `vehiculo(patente) WHERE borrado_en IS NULL`, `repuesto(codigo) WHERE borrado_en IS NULL`); todos los CHECK de `04_modelo_de_datos.md`; `orden_trabajo.estado` y `historial_estado_orden.desde_estado/hasta_estado` como **FK a `estado_orden.codigo`** (no CHECK); `NUMERIC(10,2)`/`NUMERIC(12,2)`; `timestamptz`; un **índice por cada FK**; columnas sin «(nulo)» → `NOT NULL`.
  - Navegación ORM en los dos extremos de cada relación que se lea; `Usuario.cliente` devuelve un objeto, no una lista; sin carga perezosa (`lazy` que no dispare IO implícito).
  - **Migración 1**: generada con `--autogenerate`, todas las tablas, catálogo `estado_orden` **vacío**; leída antes de aplicarla y con un comentario que lo diga.
  - **Migración 2 escrita a mano**: función y disparador (row-level, `BEFORE UPDATE OR DELETE`) que rechaza modificaciones sobre `historial_estado_orden`, `movimiento_stock` e `historial_precio_repuesto`; con `downgrade` que los elimina; comentario de lectura previa. El disparador es de fila y no cubre `TRUNCATE`, que sólo usa `seed.py` (DA-31).
  - `test/solo_agregado.sql`: los seis rechazos del disparador (UPDATE y DELETE por cada tabla) y el rechazo por FK de una orden con estado inexistente (**C-14**), con la respuesta esperada en comentarios.
  - Tests pytest (test-first): `alembic upgrade head` → `downgrade base` → `upgrade head` sobre base vacía; cada CHECK/UNIQUE/índice parcial rechaza el dato inválido y acepta el válido (p. ej. patente repetida con la anterior dada de baja se acepta; doble asignación abierta de rol se rechaza); `UPDATE`/`DELETE` sobre las tres tablas lanzan error y `INSERT` funciona; estado inexistente rechazado por FK; ningún `create_all` en el código de la aplicación.
- **RN cubiertas**: RN-01 (garantía en la base), RN-03 (índice único parcial), RN-15 (disparador), RN-19 (FK al catálogo), y base de RN-16.
- **DA / DD aplicados**: DA-00, DA-08, DA-20, DD-01, DD-02, DD-03, DD-10, DD-13, SU-01, SU-02.
- **Casos C-NN propios**: **C-14** (`test/solo_agregado.sql`; la captura de `psql` como evidencia se arma en CH-04, después del seed: R4).
- **Dependencias**: `CH-01`
- **Governance**: ALTO — esquema y migraciones afectan los datos; proponer el diseño de las dos migraciones y esperar revisión antes de escribirlas.
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` (entero: §Entidades, §Índices, §Integridad en la base, §Migraciones)
  - `knowledge-base/05_reglas_de_negocio.md` RN-01, RN-03, RN-15, RN-19
  - `knowledge-base/06_funcionalidades.md` §Épica 2 (US-010, US-011) y §Épica 7 (US-060)
  - `knowledge-base/11_casos_de_prueba.md` C-14
  - `knowledge-base/09_decisiones_y_supuestos.md` DD-01, DD-02, DD-03, DD-10, DA-20

### [CH-04] `seguridad-base-seed`
- **Estado**: `[ ]` pendiente
- **Ejercicio / peso**: Ej. 4 — Autenticación, parte base (**16 %** compartido con CH-05); `seed.py` es parte de la puesta en marcha (Ej. 2).
- **Scope**:
  - `app/core/security.py`: hash y verificación con **bcrypt siempre fuera del bucle** (`asyncio.to_thread`) y bajo un **`asyncio.Semaphore`** (`BCRYPT_MAX_CONCURRENCY`), costo desde `BCRYPT_COST`; emisión y verificación de JWT con PyJWT (`sub`, `iat` con fracción de segundo, `exp`, roles vigentes al emitir; HS256 desde `Settings`). Validador de contraseña ≤ **72 bytes** (no caracteres) reutilizable por los schemas.
  - Lifespan (`main.py`): calcula **una sola vez** el hash ficticio del login y lo guarda en `app.state` (US-002; queda aquí y no en CH-01 porque necesita bcrypt: ver OB-03).
  - `seed.py`: vacía las tablas (`TRUNCATE … RESTART IDENTITY CASCADE`, DA-31) y carga, **en este orden**, catálogo de estados → usuarios (ids 1..7) → asignaciones de rol (`otorgada_por = NULL`) → clientes → vehículos → repuestos (+ movimiento «Stock inicial» y línea de historial de precio del filtro) → órdenes 1 y 2 (+ ítems e historiales) → evento de seguridad `SISTEMA`/«Carga de los datos iniciales». Contraseña común ficticia `Taller2026!` que vive **sólo** en `seed.py`. Los ids deben coincidir con los ejemplos del PDF.
  - Tests pytest (test-first, sin endpoints): hash ≠ contraseña, verifica ok y falla; el bcrypt corre en un hilo y el semáforo limita la concurrencia (tarea concurrente > límite no excede); contraseña de 73 bytes rechazada y de 72 aceptada (incluida una con «ñ»); JWT round-trip, `exp` vencido falla, firma incorrecta falla, el `iat` conserva la fracción de segundo (verificar contra la versión de PyJWT instalada); `seed.py` es repetible (corrido dos veces deja el mismo estado), ids y totales exactos (orden 1 = 56500.00, orden 2 = 24000.00), un movimiento «Stock inicial» por repuesto.
  - `.http`: ninguno (no expone endpoints).
- **RN cubiertas**: base de RN-09 (hash ficticio) y RN-07 (`iat` sin truncar); requisitos no funcionales de Asincronía y Credenciales.
- **DA / DD aplicados**: DA-01, DA-02, DA-03, DA-04, DA-05, DA-06, DA-07, DA-13 (evento del seed), DD-06, DD-08.
- **Casos C-NN propios**: ninguno (habilita C-02 a C-09 y todos los `.http`, que dependen de `python seed.py`).
- **Nota de CH-03 (R4)**: la captura de `psql -f test/solo_agregado.sql` (C-14) se hace acá, después del seed, y se guarda en `docs/evidencias/`; el seed carga el catálogo desde `CodigoEstado` y un test verifica que coinciden.
- **Dependencias**: `CH-01`, `CH-03`
- **Governance**: CRITICO — seguridad (bcrypt, JWT) y credenciales de seed: describir el diseño y esperar aprobación humana antes de escribir código. La contraseña `Taller2026!` es ficticia y sólo vive en `seed.py`.
- **Leer antes**:
  - `knowledge-base/08_arquitectura_propuesta.md` §Seguridad
  - `knowledge-base/06_funcionalidades.md` US-032 y US-012
  - `knowledge-base/04_modelo_de_datos.md` §Seed data inicial y §Detalle del seed
  - `knowledge-base/09_decisiones_y_supuestos.md` DA-01 a DA-06, DD-06, DD-08
  - `knowledge-base/05_reglas_de_negocio.md` §Excepciones globales (Asincronía, Credenciales)

---

## FASE 2 — Acceso y seguridad

### [CH-05] `autenticacion`
- **Estado**: `[ ]` pendiente
- **Ejercicio / peso**: Ej. 4 — Autenticación (**16 %**) y Ej. 7 — intento de acceso en su propia sesión (parte del 10 %).
- **Scope**:
  - Módulo `usuarios` (primeras capas): `repository.py`, `unit_of_work.py`, `schemas.py` (todos `extra="forbid"`, contraseñas ≤ 72 bytes), `service.py`, `router.py` bajo `/auth`. El UoW de `usuarios` incluye un repositorio mínimo de `Cliente` (`app/modules/clientes/repository.py`, sólo `add`; CH-07 lo extiende: ver OB-02).
  - `POST /auth/registro` (201/409/422): `{email, nombre, password, documento, telefono}`; el servicio calcula el hash **antes** de abrir la transacción; **un solo `async with uow`** crea `usuario` + `asignacion_rol(CLIENTE, otorgada_por NULL)` + `cliente` (con `usuario_id`) + `evento_seguridad` («Registro de cliente <email>»); `IntegrityError` por correo o documento → rollback → 409 con mensaje propio, sin filas sueltas, sin apropiarse de una ficha existente.
  - `POST /auth/login` (200/401/422/429): primero el límite (5 fallos del mismo correo + IP en 60 s desde el último éxito, **una consulta**, 429 con `Retry-After` = segundos restantes, sin calcular hash, el intento rechazado **no** se anota); después verificación contra el hash real o el **ficticio**; mismo cuerpo 401 exista o no el correo; anota el intento en `intento_acceso` con **sesión y transacción propias** que siempre se confirman (comentario en el código con el trade-off); éxito → cookie `access_token` (`HttpOnly`, `SameSite=Lax`, `Max-Age = JWT_EXPIRE_SECONDS`, `Secure` configurable), cuerpo `{mensaje, debe_cambiar_password, expira_en_segundos}` **sin token**; `ip = request.client.host`.
  - `get_usuario_actual` en `app/core/dependencies.py`: lee **sólo** `request.cookies` (con `Authorization: Bearer` → 401); 401 si no hay cookie, token inválido/vencido, usuario inexistente o inactivo, o `iat` < `password_cambiada_en` sin truncar (RN-07). Se adelanta desde US-040 porque `/auth/yo` y `/auth/cambiar-password` lo necesitan (ver OB-02).
  - `POST /auth/logout` (200, borra la cookie); `GET /auth/yo` (`{id, email, nombre, debe_cambiar_password, roles_vigentes, roles_token}`, roles vigentes leídos de la base); `POST /auth/cambiar-password` (`{password_actual, password_nueva}`): verifica la actual, un UoW actualiza `password_hash`, `password_cambiada_en = now()`, `debe_cambiar_password = false` y agrega el evento «Cambio de contraseña»; emite la cookie nueva **después** de anotar el cambio.
  - Tests pytest (test-first, httpx contra la base de prueba con seed): registro ok y 409 por correo y por documento sin filas sueltas (cuenta de filas antes/después); cookie con todos sus atributos y cuerpo sin token; sin cookie y con `Authorization: Bearer` → 401; 401 idéntico con correo existente/inexistente y tiempos del mismo orden de magnitud; sexto intento → 429 con `Retry-After`, sin llamar a bcrypt (se verifica con un espía), con exactamente 5 filas en `intento_acceso`; un login correcto reinicia la cuenta; `iat` fraccionario: token anterior al cambio da 401 en el mismo segundo y el nuevo vale; contraseña > 72 bytes → 422; el intento de acceso queda aunque la petición falle.
  - `.http`: `test/c02_registro.http` (C-02), `test/c03_c04_login.http` (C-03, C-04), `test/c05_limite_intentos.http` (C-05), todos tras `python seed.py`.
- **RN cubiertas**: RN-02, RN-07, RN-08, RN-09; aplica RN-01 (409 por email y documento) y RN-18.
- **DA / DD aplicados**: DA-11, DA-12, DA-13, DA-16, DD-04, DD-05, DD-06, DD-08, DD-A3.
- **Casos C-NN propios**: **C-02**, **C-03**, **C-04**, **C-05** (la mitad «cookie nueva vale / anterior 401» de C-09 se prueba con pytest acá; el caso C-09 completo pertenece a CH-06).
- **Dependencias**: `CH-02`, `CH-03`, `CH-04`
- **Governance**: CRITICO — autenticación: describir el diseño (orden del login, cookie, `iat`) y esperar aprobación humana antes de escribir.
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` Flujos 1 (pasos 1-4), 2, 3 y 4
  - `knowledge-base/06_funcionalidades.md` §Épica 4 (US-030 a US-034)
  - `knowledge-base/05_reglas_de_negocio.md` RN-02, RN-07, RN-08, RN-09 y §Reglas operativas (Ej. 4, Ej. 7)
  - `knowledge-base/11_casos_de_prueba.md` C-02 a C-05
  - `knowledge-base/09_decisiones_y_supuestos.md` DA-11, DA-12, DA-13, DA-16, DD-05

### [CH-06] `autorizacion-usuarios-roles`
- **Estado**: `[ ]` pendiente
- **Ejercicio / peso**: Ej. 5 — Autorización (**14 %**).
- **Scope**:
  - `app/core/dependencies.py`: `requiere_rol(*roles)` (consulta `asignacion_rol` vigente —no revocada y sin vencer— **en la base en cada petición**, 403 sin rol) y el **control del cambio obligatorio** (`debe_cambiar_password` → 403).
  - `main.py`: **dos grupos de rutas** — abierto (salud, `/auth/*`) y protegido (el control del cambio obligatorio se monta **una sola vez** en el grupo), RN-06.
  - `POST /usuarios` (ADMIN; 201/409/422): `{email, nombre, password_provisoria, rol}`, `rol` ∈ {ADMIN, RECEPCION, MECANICO} (otro → 422); hash antes de la transacción; **un solo UoW**: usuario (`debe_cambiar_password = true`) + asignación (`otorgada_por` = actor) + evento «Alta de personal <email>».
  - `GET /usuarios/{id}/roles` (200/404): todo el historial con el campo calculado `vigente`; `POST /usuarios/{id}/roles` (201/404/409/422): `{rol, vence_en?}`, `vence_en` con zona y en el futuro (si no, **422**); asignación abierta vigente duplicada → 409 (RN-03); reasignar un rol vencido cierra la fila anterior con `revocada_en` y abre otra; evento «Asignación de rol <ROL> a <email>». `DELETE /usuarios/{id}/roles/{rol}` (200/404/409): escribe `revocada_en` sin borrar; **autoprotección** (nadie se revoca su propio ADMIN; nunca cero administradores vigentes → 409, RN-05); evento «Revocación de rol …».
  - `GET /eventos?page=&size=` (ADMIN, paginado con `app/core/paginacion.py`).
  - Tests pytest (test-first): 401 antes que 403; sin rol → 403 en cada ruta con `requiere_rol`; revocar un rol con la sesión abierta → la misma cookie da 403 en la petición siguiente y `/auth/yo` muestra `roles_vigentes` ≠ `roles_token`; la fila revocada sigue en el historial; `vence_en` en el pasado o sin zona → 422; doble asignación → 409; reasignar vencido; autorrevocación → 409 y revocar al último admin → 409 (aunque lo haga otro admin); con `debe_cambiar_password` sólo pasan `/auth/*` y salud (403 en el resto); tras cambiar la contraseña la cookie nueva pasa y la anterior da 401 (C-09 completo); `POST /usuarios` deja las tres filas o ninguna; `/eventos` pagina y registra altas, cambios de rol y de contraseña.
  - `.http`: `test/c07_roles_vigencia.http` (C-07; usa dos sesiones con `# @name` y `# @no-cookie-jar`), `test/c08_autoproteccion.http` (C-08), `test/c09_cambio_obligatorio.http` (C-09, con `nuevo@example.com`).
- **RN cubiertas**: RN-03, RN-04, RN-05, RN-06; aplica RN-07 (C-09 en conjunto) y RN-12/RN-17 (la base del 403).
- **DA / DD aplicados**: DA-08, DA-13, DA-15, DA-16, DA-17, DA-18, DA-25, DD-01, DD-07, SU-03, SU-04, SU-11.
- **Casos C-NN propios**: **C-07**, **C-08**, **C-09**.
- **Dependencias**: `CH-05`
- **Governance**: CRITICO — roles, autoprotección y auditoría de seguridad: describir y esperar aprobación humana antes de escribir.
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` §Cómo se determinan los roles, §RBAC y §Reglas de autorización especiales
  - `knowledge-base/07_flujos_principales.md` Flujos 1 (pasos 5-6) y 5
  - `knowledge-base/06_funcionalidades.md` §Épica 5 (US-040 a US-044)
  - `knowledge-base/05_reglas_de_negocio.md` RN-03, RN-04, RN-05, RN-06
  - `knowledge-base/11_casos_de_prueba.md` C-07, C-08, C-09

---

## FASE 3 — Dominio del taller

> CH-07 y CH-08 son independientes entre sí y pueden ir en paralelo después de CH-06. CH-09 necesita ambos.

### [CH-07] `clientes-vehiculos`
- **Estado**: `[ ]` pendiente
- **Ejercicio / peso**: Ej. 3 — Contratos y CRUD (**10 %**) y Ej. 6 (**20 %**, módulo `clientes`).
- **Scope**:
  - Módulo `clientes` completo: `schemas.py` (entrada `extra="forbid"`, salida sin datos internos), `repository.py` (`ClienteRepository` extiende el mínimo de CH-05; `VehiculoRepository(SoftDeleteRepository)` con precarga declarada en el método), `unit_of_work.py`, `service.py`, `router.py`.
  - `POST /clientes` (RECEPCION, ADMIN; 201/409 por `documento`/422): `{nombre, documento, telefono}`; `GET /clientes/{id}` (200/404) con sus **vehículos vigentes** (los dados de baja no aparecen); `POST /clientes/{id}/vehiculos` (201/404/409 por patente vigente repetida/422): `{patente, marca, modelo, anio}` (`anio` 1950..2100 → 422 por contrato); `DELETE /vehiculos/{id}` (204/404/409): borrado lógico; 409 si tiene órdenes **abiertas** (estado con `es_final = false`, consulta al catálogo por join, sin depender del módulo `ordenes`); una patente dada de baja se puede volver a registrar.
  - `GET /mis-vehiculos` (sólo autenticado): los vehículos vigentes del usuario; sin ficha de cliente → 200 con lista vacía.
  - Tests pytest (test-first): 201/409/422 por cada endpoint; `documento` y patente repetidos → 409 con mensaje propio (sin texto de la base); campo extra en el cuerpo → 422; `anio` fuera de rango → 422; baja con orden PENDIENTE/EN_REPARACION → 409 y con orden TERMINADA/CANCELADA → 204; patente reutilizable tras la baja y segunda vigente igual → 409; `/mis-vehiculos` de Laura (2 vehículos), de un usuario sin ficha (lista vacía) y no incluye los dados de baja; 403 para MECANICO y CLIENTE en las rutas de recepción.
  - `.http`: `test/c01_parametro_invalido.http` (C-01), `test/c19_baja_vehiculo.http` (C-19).
- **RN cubiertas**: RN-01 (documento, patente), RN-16 (parte vehículo), RN-17 (parte `/mis-vehiculos`); aplica RN-18.
- **DA / DD aplicados**: DA-14, DA-16, DA-23, DA-20, DD-03, SU-09.
- **Casos C-NN propios**: **C-01**, **C-19**.
- **Dependencias**: `CH-02`, `CH-06`
- **Governance**: BAJO — CRUD con borrado lógico y una regla de baja; autonomía plena si los tests pasan.
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` US-020, US-022, US-045 (parte `mis-vehiculos`)
  - `knowledge-base/07_flujos_principales.md` Flujo 12
  - `knowledge-base/03_actores_y_roles.md` §Endpoints de referencia (clientes, vehículos)
  - `knowledge-base/05_reglas_de_negocio.md` RN-01, RN-16, RN-17
  - `knowledge-base/11_casos_de_prueba.md` C-01, C-19

### [CH-08] `repuestos-stock-precios`
- **Estado**: `[ ]` pendiente
- **Ejercicio / peso**: Ej. 3 (**10 %**), Ej. 6 (**20 %**, punto único de stock) y Ej. 7 (**10 %**, historial de precios en la misma transacción).
- **Scope**:
  - Módulo `repuestos` completo: `schemas.py`, `repository.py` (`RepuestoRepository(SoftDeleteRepository)` con búsqueda por descripción con **parámetros ligados**, `MovimientoStockRepository` y `HistorialPrecioRepository` de sólo agregado, sin CRUD propio), `unit_of_work.py`, `service.py`, `router.py`.
  - **Punto único de escritura de stock** (en el servicio/UoW de `repuestos`): ajusta `stock` y agrega el `movimiento_stock` en la misma operación; lo usan el alta, la reposición y (en CH-10) la terminación de órdenes. `stock` nunca se edita por PATCH.
  - `GET /repuestos?q=&page=&size=` (ADMIN, RECEPCION, MECANICO; 200/422; excluye dados de baja); `GET /repuestos/{id}` (200/404); `POST /repuestos` (ADMIN; 201/409/422) con `stock_inicial >= 0` (negativo → 422): con `> 0`, movimiento «Stock inicial» en el mismo UoW; con `0`, sin movimiento (DA-27); `PATCH /repuestos/{id}` (ADMIN) sólo `descripcion` y `precio` con `exclude_unset`, `stock` → 422; si el precio cambia, línea en `historial_precio_repuesto` **en el mismo UoW**, si no cambia, ninguna; `DELETE /repuestos/{id}` (204/404, borrado lógico, permitido aunque haya órdenes abiertas); `POST /repuestos/{id}/reponer` `{cantidad > 0}` (200 con el repuesto actualizado/404/422) → movimiento «Reposición»; `GET /repuestos/{id}/movimientos` y `GET /repuestos/{id}/precios` (ADMIN; 200/404; **lista simple, sin envoltorio**: DA-28).
  - Tests pytest (test-first): búsqueda `' OR '1'='1` → lista vacía, total 0; `q=freno&size=1` → `total 1`, `pages 1`, `page=2` → 422; `size=500` → 422; `GET /repuestos?size=2` coincide con el ejemplo de la consigna (`total 4`, `pages 2`); PATCH parcial sólo cambia lo enviado; PATCH con `stock` → 422; PATCH de precio crea una línea y un PATCH sólo de descripción no crea ninguna; precio igual al actual no crea línea; si el historial falla se revierte el cambio de precio; reposición suma y deja movimiento positivo; alta con `stock_inicial = 0` no crea movimiento, con `> 0` crea uno, negativo → 422; `/movimientos` y `/precios` devuelven lista simple; código duplicado vigente → 409 y tras la baja se puede reusar; 403 para RECEPCION en escritura y en `/precios`.
  - `.http`: `test/c16_busqueda_paginacion.http` (C-16), `test/c18_historial_precios.http` (C-18).
- **RN cubiertas**: RN-14, RN-20; RN-16 (parte repuesto); aplica RN-01 (código) y RN-15 (sólo se agrega).
- **DA / DD aplicados**: DA-09, DA-10, DA-21, DA-27, DA-28, DD-03, DD-13, DD-A1, SU-10 (base de la comprobación de stock).
- **Casos C-NN propios**: **C-16**, **C-18**.
- **Dependencias**: `CH-02`, `CH-06`
- **Governance**: MEDIO — lógica de negocio con integridad de stock y precio; implementar con checkpoints.
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` US-023, US-053 y US-021
  - `knowledge-base/07_flujos_principales.md` Flujos 10 y 11
  - `knowledge-base/05_reglas_de_negocio.md` RN-14, RN-16, RN-20
  - `knowledge-base/04_modelo_de_datos.md` §repuesto, §movimiento_stock, §historial_precio_repuesto
  - `knowledge-base/11_casos_de_prueba.md` C-16, C-18

### [CH-09] `ordenes-alta-consulta`
- **Estado**: `[ ]` pendiente
- **Ejercicio / peso**: Ej. 6 (**20 %**, módulo `ordenes`) y Ej. 8 (**8 %**, lecturas sin N+1).
- **Scope**:
  - Módulo `ordenes` (primera mitad): `schemas.py` (entrada `extra="forbid"`; el precio, el total, el estado y la fecha **no viajan**; `items` ≥ 1, `cantidad > 0`, sin `repuesto_id` repetidos → 422), `repository.py` (`OrdenTrabajoRepository` con **precarga declarada en el método**; `EstadoOrdenRepository` de **sólo lectura que NO hereda** de `BaseRepository`; repositorio de ítems/historial), `unit_of_work.py` (compone órdenes, ítems, historial, catálogo, repuestos y vehículos sobre la misma sesión), `service.py`, `router.py`.
  - `POST /ordenes` (RECEPCION, ADMIN; 201/409/422): **un solo UoW**: catálogo vacío → 409; vehículo inexistente o dado de baja → 409; repuesto inexistente o dado de baja → 409 y la orden no queda creada; copia `precio_unitario` de cada repuesto, calcula `total` = Σ cantidad × precio (Decimal), estado PENDIENTE, `item_orden` y primera línea de `historial_estado_orden` (`desde_estado null`, `usuario_id` = actor); responde el detalle con el formato del ejemplo de la consigna.
  - `GET /ordenes?estado=&page=&size=` (ADMIN, RECEPCION, MECANICO ven todas; `estado` no declarado en el enum → 422); `GET /ordenes/{id}` (el personal, o el dueño del vehículo; otro cliente → 403; 404): detalle con vehículo, cliente, ítems, repuesto de cada ítem e historial, resuelto con **número fijo de consultas** (`selectinload`/`joinedload` en el repositorio, nada de carga perezosa); `GET /mis-ordenes?page=&size=` (sólo autenticado; sin ficha → 200 con envoltorio vacío); `GET /estados-orden` (autenticado; las cuatro filas por `posicion`, con `es_final`; sin escritura).
  - Tests pytest (test-first): alta feliz (ejemplo de la consigna: orden 3, total `68000.00`); precio y total del cuerpo → 422; repetidos → 422; repuesto inexistente → 409 y `orden_trabajo` sin fila nueva; catálogo vacío → 409; detalle: la cantidad de consultas (contador de eventos SQL del motor) es igual con 2 que con 4 ítems; cliente dueño 200 y ajeno 403; sin sesión 401; `/estados-orden` ordenado y 401 sin sesión; `estado=XYZ` → 422; `/mis-ordenes` de Laura (la 1) y de usuario sin ficha (vacío); Decimal serializado como string.
  - `.http`: `test/c06_401_403_propio.http` (C-06), `test/c10_alta_orden.http` (C-10), `test/c15_detalle_sin_n1.http` (C-15; correr con `SQL_ECHO=true`), `test/c17_catalogo_estados.http` (C-17).
- **RN cubiertas**: RN-10, RN-17 (órdenes propias y 403 ajeno), RN-19 (endpoint del catálogo y 409 por catálogo vacío); aplica RN-16 (no usar vehículos/repuestos dados de baja en órdenes nuevas) y RN-04.
- **DA / DD aplicados**: DA-14, DA-19, DA-21, DA-24, DD-02, DD-A2, SU-05, SU-07, SU-08, SU-09.
- **Casos C-NN propios**: **C-06**, **C-10**, **C-15**, **C-17**.
- **Dependencias**: `CH-07`, `CH-08`
- **Governance**: MEDIO — transacción multi-escritura y reglas de pertenencia; implementar con checkpoints y exponer las decisiones no obvias.
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` Flujos 6 y 13
  - `knowledge-base/06_funcionalidades.md` US-052 (alta, listado, detalle), US-024, US-070, US-045
  - `knowledge-base/05_reglas_de_negocio.md` RN-10, RN-17, RN-19 y §Máquina de estados
  - `knowledge-base/04_modelo_de_datos.md` §orden_trabajo, §item_orden, §historial_estado_orden, §estado_orden
  - `knowledge-base/11_casos_de_prueba.md` C-06, C-10, C-15, C-17 y §Ejemplos de la consigna

### [CH-10] `ordenes-ciclo-aviso`
- **Estado**: `[ ]` pendiente
- **Ejercicio / peso**: Ej. 6 (**20 %**, operaciones de varias escrituras) y Ej. 8 (**8 %**, asincronía y aviso en segundo plano).
- **Scope**:
  - `POST /ordenes/{id}/iniciar` (MECANICO; 200/404/409): estado ≠ PENDIENTE → 409; un UoW: `estado = EN_REPARACION`, `mecanico_id` = actor, línea de historial.
  - `POST /ordenes/{id}/terminar` (el mecánico asignado con MECANICO vigente, o ADMIN vigente; 200/403/404/409): 404 → **403 por permiso antes que 409 por estado** → estado ≠ EN_REPARACION → 409; **un solo UoW** que, por cada ítem y a través del punto único de stock de CH-08, descuenta el stock y agrega un `movimiento_stock` **negativo** («Orden terminada», con `orden_id`); si `stock < cantidad` → excepción de dominio → rollback → 409 con mensaje propio y **ninguna** escritura queda (estado, stock, movimientos e historial intactos); cambia a TERMINADA y agrega la línea de historial. Los repuestos dados de baja después del alta se leen con `get_by_id_including_deleted`.
  - `POST /ordenes/{id}/cancelar` (**sin `requiere_rol`**; 200/403/404/409): permiso del actor (rol vigente RECEPCION/ADMIN, o usuario de la ficha del cliente dueño del vehículo) → 403; **después** estado ≠ PENDIENTE → 409; UoW: `CANCELADA` + historial.
  - `BackgroundTasks` en el router: agenda el aviso (`await asyncio.sleep(0.5)` + mensaje en el log) **después** de enviar la respuesta y **sólo si la operación se confirmó**; ningún `time.sleep` ni llamada bloqueante; todos los handlers `async def`.
  - Tests pytest (test-first): transiciones válidas e inválidas (409); terminar con stock insuficiente → 409 y el estado, el stock, los movimientos y el historial quedan **exactamente** como estaban (comparar snapshots); reponer y terminar la orden 2 → baja el stock, aparecen los movimientos negativos y la línea de historial; el aviso se agenda sólo en el caso exitoso (espía) y no en 409/403; mecánico no asignado → 403; ADMIN puede terminar; MECANICO que perdió su rol → 403; repuesto dado de baja entre el alta y la terminación se descuenta igual; cancelar: dueño 200, orden ajena 403, terminada 409, y 403 antes que 409 (cliente ajeno sobre una orden terminada → 403); recepción cancela.
  - `.http`: `test/c11_c12_terminar_orden.http` (C-11 y luego C-12 sobre la orden 2; el aviso se observa en el log del servidor), `test/c13_cancelar.http` (C-13).
- **RN cubiertas**: RN-11, RN-12, RN-13; aplica RN-14 (vía el punto único), RN-04, RN-15 y RN-18.
- **DA / DD aplicados**: DA-09, DA-21, DA-22, DD-09, DD-13, DD-A1, SU-10, SU-09.
- **Casos C-NN propios**: **C-11**, **C-12**, **C-13**.
- **Dependencias**: `CH-09` (y `CH-08` por el punto único de stock, ya transitivo)
- **Governance**: MEDIO — máquina de estados y descuento de stock transaccional; implementar con checkpoints.
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` Flujos 7, 8 y 9
  - `knowledge-base/05_reglas_de_negocio.md` RN-11, RN-12, RN-13 y §Máquina de estados
  - `knowledge-base/06_funcionalidades.md` US-052 (iniciar, terminar, cancelar) y US-071
  - `knowledge-base/11_casos_de_prueba.md` C-11, C-12, C-13 y §Observaciones para armar los casos con el seed
  - `knowledge-base/09_decisiones_y_supuestos.md` DA-21, DA-22, DD-09, SU-10

---

## FASE 4 — Cierre

### [CH-11] `cierre-entrega`
- **Estado**: `[ ]` pendiente
- **Ejercicio / peso**: transversal — Formato de entrega y condiciones excluyentes (`12_criterios_de_evaluacion.md`); respalda Ej. 7 (C-14) y Ej. 8 (C-15) con las evidencias.
- **Scope**:
  - `README.md` con los pasos desde cero: entorno virtual, `pip install -r requirements.txt`, `.env` desde `env.example` (con cómo generar la clave de firma), crear la base, `alembic upgrade head`, `python seed.py`, arranque con uvicorn; cómo correr los `.http` y la suite pytest.
  - **Evidencia C-14**: verificar que la captura de `psql` con los seis rechazos del disparador y el rechazo por FK (corriendo `test/solo_agregado.sql` después del seed) que se hizo en CH-04 sigue en `docs/evidencias/` (DA-30) y vale para el esquema final.
  - **Evidencia C-15**: fragmento de la consola (`SQL_ECHO=true`) con las consultas del detalle de una orden de 2 ítems y de otra de 4, guardado en `docs/evidencias/` (DA-30).
  - **Auditoría contra la consigna** (checklist de `12_criterios_de_evaluacion.md`): `.env` ignorado y `env.example` sin secretos; ningún secreto con default en `Settings`; `alembic.ini` sin URL con contraseña; `upgrade head` → `downgrade base` → `upgrade head` sobre base vacía; `python seed.py` corre sobre el esquema migrado; los 19 casos con su respuesta esperada en comentarios; búsqueda de `commit()` en repositorios, de `create_all`, de `lazy` implícito, de SQL por concatenación y de llamadas bloqueantes; las tablas «Caso → Change» y «RN → Change» de este archivo siguen verdes; corrida completa de pytest.
  - Tests: la corrida completa de pytest y de los 19 casos `.http` desde una base vacía (`alembic upgrade head` + `python seed.py`).
- **RN cubiertas**: ninguna nueva (verifica RN-01 a RN-20 de punta a punta).
- **DA / DD aplicados**: DA-07 (variables en README), DA-26 (cómo correr pytest desde `test/pytest/` con `requirements-dev.txt`), DA-30, DD-A4 (generación de la clave).
- **Casos C-NN propios**: ninguno nuevo (evidencias de **C-14** y **C-15**).
- **Dependencias**: `CH-10`
- **Governance**: BAJO — documentación y verificación; el único cambio de código admitido son correcciones que surjan de la auditoría (cada una con su test).
- **Leer antes**:
  - `knowledge-base/12_criterios_de_evaluacion.md` (entero)
  - `knowledge-base/08_arquitectura_propuesta.md` §Entrega (formato)
  - `knowledge-base/11_casos_de_prueba.md` (entero)
  - `knowledge-base/05_reglas_de_negocio.md` §Excepciones globales

---

## Cobertura: Caso → Change

Los 19 casos de `11_casos_de_prueba.md` tienen **exactamente un** change dueño (el que escribe su `.http`).

| Caso | Qué demuestra | Change dueño | Archivo en `test/` |
|------|---------------|--------------|--------------------|
| C-01 | Parámetro de ruta no entero → 422 | CH-07 | `c01_parametro_invalido.http` |
| C-02 | Registro; correo y documento repetidos | CH-05 | `c02_registro.http` |
| C-03 | Cookie del login; 401 sin cookie / con `Authorization` | CH-05 | `c03_c04_login.http` |
| C-04 | Anti-enumeración (mismo cuerpo y tiempo) | CH-05 | `c03_c04_login.http` |
| C-05 | Seis intentos → 429 con `Retry-After` | CH-05 | `c05_limite_intentos.http` |
| C-06 | 401 vs 403; lo propio (200 / 403) | CH-09 | `c06_401_403_propio.http` |
| C-07 | Revocar rol con sesión abierta; vencimientos inválidos | CH-06 | `c07_roles_vigencia.http` |
| C-08 | Autoprotección ADMIN | CH-06 | `c08_autoproteccion.http` |
| C-09 | Cambio obligatorio de contraseña e `iat` | CH-06 | `c09_cambio_obligatorio.http` |
| C-10 | Alta de orden con dos ítems; repuesto inexistente | CH-09 | `c10_alta_orden.http` |
| C-11 | Terminar sin stock suficiente (rollback total) | CH-10 | `c11_c12_terminar_orden.http` |
| C-12 | Reponer y terminar; aviso en segundo plano | CH-10 | `c11_c12_terminar_orden.http` |
| C-13 | Cancelar (dueño, ajena, terminada) | CH-10 | `c13_cancelar.http` |
| C-14 | Disparador de sólo agregado y FK del catálogo | CH-03 | `solo_agregado.sql` (evidencia en CH-04, después del seed) |
| C-15 | Detalle con 2 y 4 ítems: mismas consultas | CH-09 | `c15_detalle_sin_n1.http` (evidencia en CH-11) |
| C-16 | Inyección, paginación, PATCH parcial, PATCH del stock | CH-08 | `c16_busqueda_paginacion.http` |
| C-17 | Catálogo de estados; estado no declarado → 422 | CH-09 | `c17_catalogo_estados.http` |
| C-18 | Historial de precios | CH-08 | `c18_historial_precios.http` |
| C-19 | Baja y reuso de patente | CH-07 | `c19_baja_vehiculo.http` |

Resultado: **19 de 19 casos cubiertos, sin huecos y sin duplicados** (CH-01, CH-02, CH-04 y CH-11 no poseen casos propios).

## Cobertura: RN → Change

Cada regla tiene un change **principal** (el que la implementa/garantiza) y los que **también** la aplican.

| Regla | Change principal | También aplica |
|-------|------------------|----------------|
| RN-01 | CH-03 (UNIQUE e índices parciales) | CH-02 (409), CH-05, CH-07, CH-08 |
| RN-02 | CH-05 | — |
| RN-03 | CH-06 | CH-03 (índice) |
| RN-04 | CH-06 | CH-09, CH-10 |
| RN-05 | CH-06 | — |
| RN-06 | CH-06 | — |
| RN-07 | CH-05 | CH-04 (`iat`), CH-06 (C-09) |
| RN-08 | CH-05 | — |
| RN-09 | CH-05 | CH-04 (hash ficticio) |
| RN-10 | CH-09 | — |
| RN-11 | CH-10 | CH-09 (estado inicial) |
| RN-12 | CH-10 | — |
| RN-13 | CH-10 | CH-08 (punto único de stock) |
| RN-14 | CH-08 | CH-10 |
| RN-15 | CH-03 (disparador) | CH-08, CH-10 |
| RN-16 | CH-07 (vehículo) y CH-08 (repuesto) | CH-09 (no usar en órdenes nuevas) |
| RN-17 | CH-09 (órdenes) | CH-07 (`/mis-vehiculos`), CH-06 |
| RN-18 | CH-02 | todos los módulos |
| RN-19 | CH-09 (endpoint y 409 por catálogo vacío) | CH-03 (FK) |
| RN-20 | CH-08 | — |

Resultado: **20 de 20 reglas con dueño**, sin huecos.

## Cobertura: Ejercicio → Change

| Ejercicio (peso) | Changes |
|------------------|---------|
| Ej. 1 (8 %) | CH-01 |
| Ej. 2 (14 %) | CH-03 (+ seed en CH-04) |
| Ej. 3 (10 %) | CH-02 (paginación), CH-07, CH-08, CH-09 |
| Ej. 4 (16 %) | CH-04, CH-05 |
| Ej. 5 (14 %) | CH-05 (`get_usuario_actual`), CH-06, CH-07 y CH-09 (lo propio) |
| Ej. 6 (20 %) | CH-02, CH-07, CH-08, CH-09, CH-10 |
| Ej. 7 (10 %) | CH-03 (disparador), CH-05 (intento de acceso), CH-08 (historial de precios), CH-11 (evidencia) |
| Ej. 8 (8 %) | CH-09 (N+1), CH-10 (aviso y asincronía), CH-11 (evidencia) |

---

## Desvíos respecto de la propuesta

El desglose CH-01 a CH-11, sus nombres y su orden **se respetan tal cual**. **No se fusionó, dividió, renombró ni reordenó ningún change.** Los únicos ajustes son refinamientos de alcance dentro de la propuesta, y se listan acá para que no pasen en silencio:

1. **`get_usuario_actual` se adelanta de CH-06 a CH-05** (US-040 → CH-05). Motivo: `GET /auth/yo` y `POST /auth/cambiar-password` (Ej. 4) requieren autenticación, y no pueden esperar a CH-06. En CH-06 quedan `requiere_rol`, el control del cambio obligatorio y los dos grupos de rutas.
2. **El hash ficticio del lifespan se mueve de CH-01 a CH-04.** El Ejercicio 1 (US-002) lo incluye en el lifespan, pero necesita bcrypt, que nace en CH-04. CH-01 deja el lifespan armado y CH-04 le agrega el cálculo.
3. **El repositorio mínimo de `Cliente` nace en CH-05** y no en CH-07 (el auto-registro lo necesita dentro de su UoW); CH-07 lo completa.
4. **CH-03 depende sólo de CH-01** (no de CH-02), lo que habilita el paralelismo CH-02 ∥ CH-03. Si se prefiere estricto orden lineal, queda igual de válido.
5. **C-09 se asigna a CH-06** aunque su segunda mitad (cookie nueva vs. cookie anterior) depende de CH-05; esa mitad también se prueba con pytest en CH-05.
6. **Se agregan secciones de primer nivel** (coberturas, Desvíos, Observaciones) sobre el formato base de `CHANGES.md`, porque la alumna las pidió explícitamente.
7. **El «Agente C» no es frontend**: el proyecto no tiene frontend; se lo usa como verificación independiente.

## Observaciones para la alumna

Cosas que hay que decidir o confirmar; **ninguna se resolvió en silencio**. Las contradicciones reales de la KB no aparecieron (las inconsistencias IN-01 a IN-03 ya estaban resueltas por DA-00); estas son restricciones y huecos.

- **OB-01 — Dónde vive la suite pytest. ✅ Resuelta → `test/pytest/` + `requirements-dev.txt` (KB 09 DA-26).** El PDF reserva `test/` para los `.http` y `solo_agregado.sql`. Propuesta: carpeta **`tests/`** en la raíz (`tests/conftest.py`, `tests/unit/`, `tests/integration/`). Contra: `test/` y `tests/` se parecen y pueden confundir al corrector. Alternativa: `test/pytest/`. También hay que decidir si la suite se entrega (se sube al repo) y si las dependencias de prueba (`pytest`, `pytest-asyncio`, `httpx`, y lo que haga falta para el lifespan) van en `requirements.txt` o en un `requirements-dev.txt`. Recomendación provisoria: `tests/` + `requirements-dev.txt`. Se aplica a todos los changes.
- **OB-02 — `get_usuario_actual` y `Cliente` anticipados.** Ver Desvíos 1 y 3. No cambian el desglose, pero mueven un poco de alcance entre CH-05, CH-06 y CH-07.
- **OB-03 — Hash ficticio en el lifespan.** Ver Desvío 2. La consigna lo pide en el lifespan; se implementa en CH-04 porque antes no existe bcrypt.
- **OB-04 — El seed «vacía las tablas» y el disparador. ✅ Resuelta → `TRUNCATE … RESTART IDENTITY CASCADE` sólo en `seed.py`; disparador de fila `BEFORE UPDATE OR DELETE` (KB 09 DA-31).** El disparador (RN-15) rechaza `UPDATE` y `DELETE` fila por fila. Si `seed.py` vaciara con `DELETE FROM`, el disparador lo rechazaría. Hay que vaciar con **`TRUNCATE … RESTART IDENTITY CASCADE`** (que no dispara triggers de fila) y el disparador tiene que ser sólo de fila para `UPDATE OR DELETE`, **no** para `TRUNCATE`. `RESTART IDENTITY` además es lo que hace que los ids coincidan con los del PDF. Confirmar que ese `TRUNCATE` del seed es aceptable (es una vía de escape deliberada, sólo para la puesta en marcha).
- **OB-05 — CH-02 corre antes de tener modelos propios.** Si CH-02 se hace en paralelo con CH-03, la suite del repositorio genérico necesita una tabla de prueba definida dentro del propio test. Es una excepción acotada a «el esquema sólo con Alembic» (la regla es para la aplicación, no para tablas descartables de un test). Alternativa: hacer CH-02 después de CH-03 (queda lineal; el camino crítico no cambia).
- **OB-06 — Arnés pytest-asyncio + asyncpg + lifespan.** `httpx.AsyncClient` con `ASGITransport` **no ejecuta el lifespan**; hace falta ejecutarlo en la fixture (por ejemplo con `asgi-lifespan`, que sería otra dependencia de prueba) o crear `app.state` a mano. Además, conviene un solo bucle de eventos por sesión de pruebas para que el pool de asyncpg no se rompa. A resolver en CH-01 y dejar fijo para el resto.
- **OB-07 — `stock_inicial` en `POST /repuestos`. ✅ Resuelta → `>= 0`; con 0 sin movimiento, con > 0 movimiento en el mismo UoW (KB 09 DA-27).** `movimiento_stock` tiene `CHECK cantidad <> 0`, así que un `stock_inicial = 0` no puede generar movimiento. La KB (Flujo 10) dice «stock 0 o directamente el inicial, según el punto único» sin fijar nada. Hay que decidir: (a) `stock_inicial > 0` obligatorio, o (b) `stock_inicial ≥ 0` y con 0 no se crea movimiento. Y el repuesto nace con `stock = 0` más el movimiento aplicado por el punto único (recomendado, para que RN-14 tenga un solo camino). Hay que definirlo antes de CH-08.
- **OB-08 — Formato de `/repuestos/{id}/movimientos` y `/precios`. ✅ Resuelta → lista simple, sin envoltorio (KB 09 DA-28).** La tabla de endpoints no lista `page`/`size` para ellos, pero la convención dice que los listados llevan el envoltorio. Decidir: lista simple o envoltorio paginado. Antes de CH-08.
- **OB-09 — `iat` con fracción de segundo en PyJWT.** La KB exige conservarlo sin truncar (RN-07). Habrá que verificar en CH-04, con la versión instalada de PyJWT, que un `iat` en `float` sobrevive a la codificación y a la validación; el test de CH-04 y el de C-09 lo comprueban.
- **OB-10 — Un solo `.http` por varios casos.** C-03/C-04 y C-11/C-12 comparten archivo (el segundo depende del estado dejado por el primero, o son de la misma sesión). Si el corrector espera un archivo por caso, se pueden separar sin cambiar el dueño.
- **OB-11 — Base de prueba derivada del nombre. ✅ Resuelta → `<POSTGRES_DB>_test` con guarda en el `conftest` (KB 09 DA-29).** Para no sumar una variable que no está en la tabla de `env.example` (DA-07), la base de prueba se deriva como `<POSTGRES_DB>_test` en el `conftest`. Si se prefiere una variable explícita (`POSTGRES_TEST_DB`), hay que agregarla a DA-07 y a `env.example`.
- **OB-12 — Evidencias fuera de `test/`. ✅ Resuelta → `docs/evidencias/` (KB 09 DA-30).** El PDF pide capturas de C-14 y C-15 pero no dice dónde guardarlas; CH-11 propone `docs/evidencias/`. Confirmar.
