# Taller Mecánico — Instrucciones para Agentes

> Este archivo (y su copia `CLAUDE.md`) es lo PRIMERO que todo agente lee al entrar al repo.
> Generado a partir de `knowledge-base/` y `CHANGES.md`. No editar a mano sin re-sincronizar ambos archivos.

TP integrador individual de Programación III (prof. Giuliano). API REST asincrónica para un taller mecánico: clientes y vehículos, órdenes de trabajo con ítems y estados, stock de repuestos movido sólo por movimientos, y acceso con bcrypt + JWT en cookie `HttpOnly` y roles con vigencia consultados en la base.

**Única fuente de verdad**: `docs/consigna/consigna-taller-mecanico.pdf`. La KB la refleja; ante duda, manda el PDF.

---

## Stack Tecnológico

| Componente | Versión mínima (consigna) | En uso | Uso |
|---|---|---|---|
| Python | 3.12 | 3.13 (`.venv` existente) | Lenguaje |
| FastAPI | 0.111 | — | Framework web; todos los handlers con `async def` |
| SQLModel | 0.0.24 | — | Modelos de tabla |
| SQLAlchemy | 2.0, asincrónico | — | Motor, sesión y carga anticipada |
| asyncpg | 0.30 | asyncpg | Controlador asincrónico de PostgreSQL |
| PostgreSQL | 16 | 17 | Base de datos |
| Alembic | 1.13, plantilla asincrónica | — | Migraciones |
| pydantic-settings | 2.0 | — | Configuración leída del entorno |
| bcrypt | 4.0 | — | Hash de las contraseñas |
| PyJWT | 2.8 | — | Token firmado |
| uvicorn | El que instala `fastapi[standard]` | — | Servidor ASGI |

Arquitectura: `Router → Service → Unit of Work → Repository → Model`, por módulo (`health`, `usuarios`, `clientes`, `repuestos`, `ordenes`).

Detalle completo: [knowledge-base/02_descripcion_general.md](knowledge-base/02_descripcion_general.md)

---

## Base de Conocimiento

La fuente de verdad del dominio vive en `knowledge-base/`. **Leé el archivo relevante ANTES de implementar.**

| Archivo | Cuándo leerlo |
|---------|---------------|
| [README.md](knowledge-base/README.md) | Índice y quick start |
| [01_vision_y_objetivos.md](knowledge-base/01_vision_y_objetivos.md) | Propósito, alcance, lo que queda afuera |
| [02_descripcion_general.md](knowledge-base/02_descripcion_general.md) | Stack, capas, convenciones transversales de la API |
| [03_actores_y_roles.md](knowledge-base/03_actores_y_roles.md) | Roles, endpoints de referencia con códigos, RBAC |
| [04_modelo_de_datos.md](knowledge-base/04_modelo_de_datos.md) | Tablas y columnas obligatorias, restricciones, índices, migraciones, seed |
| [05_reglas_de_negocio.md](knowledge-base/05_reglas_de_negocio.md) | RN-01 a RN-20, máquina de estados, requisitos no funcionales |
| [06_funcionalidades.md](knowledge-base/06_funcionalidades.md) | Épicas por ejercicio con historias y criterios de aceptación |
| [07_flujos_principales.md](knowledge-base/07_flujos_principales.md) | Flujos de punta a punta |
| [08_arquitectura_propuesta.md](knowledge-base/08_arquitectura_propuesta.md) | Patrones, estructura obligatoria de carpetas, seguridad, variables de entorno |
| [09_decisiones_y_supuestos.md](knowledge-base/09_decisiones_y_supuestos.md) | Decisiones DA/DD y supuestos SU (citados por cada change) |
| [10_preguntas_abiertas.md](knowledge-base/10_preguntas_abiertas.md) | Inconsistencias y preguntas (hoy todas resueltas → ver 09) |
| [11_casos_de_prueba.md](knowledge-base/11_casos_de_prueba.md) | Casos C-01 a C-19 con request/response |
| [12_criterios_de_evaluacion.md](knowledge-base/12_criterios_de_evaluacion.md) | Pesos, condiciones excluyentes, formato de entrega |

> Las preguntas de prioridad **Alta** de `10_preguntas_abiertas.md` ya están resueltas (ver `09`). Si aparece algo nuevo no especificado, se agrega ahí y se pregunta antes de implementarlo.

---

## Skills Disponibles

Instaladas a nivel proyecto en `.claude/skills/` (versionadas con `skills-lock.json`).

También están en `.agents/skills/`, el formato universal para otros agentes, que además incluye los comandos `source-command-opsx-*`. Las dos carpetas se mantienen sincronizadas: si se agrega o se quita una skill, se hace en ambas.

| Agente | Rol | Skills que carga |
|--------|-----|------------------|
| **Backend Core** (Agente A/B en `CHANGES.md`) | Routers, servicios, UoW, dependencias, auth | `fastapi`, `fastapi-patterns` |
| **Persistencia** | Modelos SQLModel, restricciones, índices, migraciones Alembic, consultas | `postgresql-table-design`, `sqlalchemy-alembic-expert-best-practices-code-review` |
| **Verificación** | Archivos `.http` con REST Client y `test/solo_agregado.sql` con psql | Verificación manual contra la base de la aplicación |
| **Verificación** (Agente C) | Revisión del TDD y auditoría contra la consigna (CH-11) | `sqlalchemy-alembic-expert-best-practices-code-review`, `python-testing-patterns` |
| **Orquestación** | OPSX / fundación | `opsx:*`, `kb-creator`, `roadmap-generator`, `agent-instruction`, `skill-registry` |

Cargá la skill correspondiente al contexto ANTES de escribir código. Si una skill contradice la consigna, manda la sección [Cuando una skill choca con la consigna](#cuando-una-skill-choca-con-la-consigna-manda-esto).

> Los compact rules de cada skill los resuelve el orquestador desde `.atl/skill-registry.md` (generado por `skill-registry`; se versiona con el repo).

---

## Roadmap de Changes

El plan de implementación completo está en [CHANGES.md](CHANGES.md). Resumen:

- **Total**: 11 changes (`CH-01` … `CH-11`) en 4 fases: Fundaciones, Acceso y seguridad, Dominio del taller, Cierre.
- **Camino crítico** (9): `CH-01 → CH-03 → CH-04 → CH-05 → CH-06 → CH-07/CH-08 → CH-09 → CH-10 → CH-11`. `CH-02` corre en paralelo con CH-03/CH-04 y debe estar listo antes de CH-05.
- **Primer change**: `CH-01` (`proyecto-config-salud`).
- **IDs**: `CH-NN` son changes; `C-NN` son SIEMPRE los casos de prueba del PDF.

**Antes de cualquier `/opsx:propose`**: leé [CHANGES.md](CHANGES.md), identificá las dependencias del change, su nivel de governance y los archivos de "Leer antes".

---

## Reglas Duras (específicas del proyecto)

> Reglas globales ya definidas en `~/.claude/CLAUDE.md` (orquestador, governance, TDD, engram): el proyecto las hereda. Acá viven solo las reglas **específicas de este proyecto** + las universales que el global no cubra.

Son contrato; romperlas es un defecto.

### Trabajo

- NUNCA commitear ni pushear → los commits los hace Amanda.
- NUNCA escribir archivos, correr comandos con efectos ni despachar sub-agentes sin confirmación → describir la acción y frenar en cada checkpoint.
- NUNCA inventar lo que el PDF no dice → marcar «No especificado en la consigna» y preguntar. Nombres de tablas, columnas, endpoints, códigos, RN y casos: textuales de la consigna.
- NUNCA instalar paquetes ni skills sin pedido → proponer y esperar.

### Arquitectura y persistencia

- NUNCA `commit()` en repositorios → `flush()`; confirma el UoW (`async with`), y el servicio nunca construye el UoW.
- NUNCA `create_all` → esquema sólo con Alembic async; leer cada migración autogenerada antes de aplicarla.
- NUNCA carga perezosa ni N+1 → precarga declarada en el método del repositorio (`selectinload`/`joinedload`).
- NUNCA `UPDATE`/`DELETE` ni CRUD propio sobre las tablas appendOnly (`historial_estado_orden`, `movimiento_stock`, `historial_precio_repuesto`) → las escribe el servicio en la misma transacción. NUNCA editar `stock` directo → sólo por el punto único de stock, con su `movimiento_stock`.

### Contratos de la API

- Schemas separados de los modelos de tabla; los de entrada con `extra="forbid"`. NUNCA `password_hash` en una respuesta.
- NUNCA `float` para dinero → `NUMERIC` + `Decimal` (string en JSON). Fechas `timestamptz`, con zona en JSON.
- NUNCA SQL por concatenación → parámetros ligados.
- NUNCA 500 ni texto de la base por un `IntegrityError` → excepción de dominio → 409 con mensaje propio.

### Async, seguridad y tests

- Todos los handlers `async def`. NUNCA `time.sleep` ni IO bloqueante → bcrypt con `asyncio.to_thread` bajo un `asyncio.Semaphore`.
- JWT SÓLO en cookie `HttpOnly` (`Authorization: Bearer` → 401). Roles vigentes consultados en la base en cada petición.
- NUNCA secretos en código, en el repo ni con default en `Settings` → la clave JWT se genera una vez, va fija en `.env`, nunca se genera al arrancar.
- La verificación se hace con los archivos `.http` de `test/` mediante REST Client, ejecutando `python seed.py` antes de cada archivo, y con `test/solo_agregado.sql` mediante `psql` para C-14. C-15 se documenta con `SQL_ECHO=true uvicorn main:app` y el fragmento de consultas del detalle.

### Cuando una skill choca con la consigna, manda esto

- **Estructura obligatoria del PDF**: `main.py` en la raíz, `app/core/{config,database,security,dependencies,repository,paginacion,unit_of_work}.py` y `app/modules/<módulo>/{models,schemas,repository,unit_of_work,service,router}.py`. Además, desde CH-02, `app/core/errores.py` (excepciones de dominio y traducción del `IntegrityError`) y `app/core/rutas.py` (clase de ruta que traduce los errores de dominio a HTTP): «No especificado en la consigna». Ignorar `app/main.py`, `app/config.py` y `app/dependencies.py` de las skills.
- **Cada `router.py` declara `route_class=RutaQueTraduceErrores`** (de `app/core/rutas.py`): el router traduce los errores de dominio, como dice el PDF; NUNCA un handler global en `main.py`. Un test recorre las rutas de la app y falla si alguna no la declara.
- **Paginación** con `page` (desde 1) y `size` (1 a 100, default 20) y envoltorio `{items, total, page, size, pages}`; página inexistente → 422. NUNCA `limit`/`offset` en la API.
- Choque con lo guardado → **409**, nunca 400.
- Todos los handlers `async def`, aunque una skill diga usar `def`.
- Migraciones sin `CONCURRENTLY` ni `NOT VALID`: las tablas arrancan vacías y la primera migración es autogenerada.
- Excepción a `tdd`: C-02, C-05 y C-11 también se verifican consultando la base (`intento_acceso` no tiene endpoint).
- Dependencias en `requirements.txt` (no Poetry); contratos con Pydantic (no dataclasses).
- Commits: los hace Amanda, uno por change, en español, p. ej. `feat(CH-03): ...`. Los changes son `CH-NN` y `C-NN` son los casos de prueba del PDF.

---

## Flujo de Trabajo

```
1. Leer la KB relevante (knowledge-base/)        → entender el dominio
2. Identificar el change en CHANGES.md           → respetar dependencias y governance
3. /opsx:propose <nombre-kebab>                  → proposal + design + specs + tasks
4. /opsx:apply (TDD estricto, cargando skills)   → respetando las reglas duras
5. /opsx:archive <nombre-kebab> + marcar [x]     → cerrar el change; Amanda commitea
```

Aplicar TODAS las reglas duras en cada paso. Ante conflicto entre la KB y este archivo, las reglas duras prevalecen; ante conflicto con la consigna, manda el PDF.
