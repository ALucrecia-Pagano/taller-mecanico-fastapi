# Skills del proyecto

Las skills están instaladas dentro del repo, en dos carpetas: `.claude/skills/` (para Claude Code) y `.agents/skills/` (formato universal para otros agentes). Así, quien clone el repo ya las tiene, sin instalar nada aparte. Las versiones instaladas quedan registradas en `skills-lock.json`, y el registro de skills con sus compact rules, `.atl/skill-registry.md`, también se versiona.

Los comandos del ciclo OPSX también viajan con el proyecto: en `.claude/commands/opsx/` (`apply`, `archive`, `explore`, `propose`, `sync` y `update`) y, como skills, en `.agents/skills/source-command-opsx-*`.

Las dos carpetas de skills se mantienen sincronizadas: si se agrega o se quita una skill, se hace en las dos.

Lo que no está en el repo es el orquestador de Active Stack con sus fases (`kb-creator`, `roadmap-generator`, `agent-instruction`, `skill-registry`) y Engram: para usarlos hay que tener Active Stack instalado.

Si una skill contradice `AGENTS.md`, manda `AGENTS.md`. Y ante cualquier duda, manda la consigna (`docs/consigna/consigna-taller-mecanico.pdf`).

## Decisión por skill

| Skill | Origen | Por qué la elegí | Se usa en |
|---|---|---|---|
| `fastapi` | `fastapi/fastapi` | Es la skill oficial del repositorio de FastAPI: convenciones actuales del framework, `Annotated`, dependencias y Pydantic. | CH-01, CH-02, CH-05 a CH-10 |
| `fastapi-patterns` | `affaan-m/ecc` | Cubre lo que la consigna evalúa en la capa web: schemas Pydantic v2, inyección de dependencias, autenticación, autorización y servicios transaccionales. | CH-01, CH-02, CH-05 a CH-10 |
| `sqlalchemy-alembic-expert-best-practices-code-review` | `wispbit-ai/skills` | Revisa modelos, migraciones Alembic y consultas: carga anticipada, N+1 y migraciones seguras. También sirve para auditar. | CH-02, CH-03, CH-09, CH-11 |
| `postgresql-table-design` | `wshobson/agents` | Diseño de tablas en PostgreSQL: tipos (`NUMERIC`, `timestamptz`), restricciones, índices por FK e índices únicos parciales. | CH-03 |
| `tdd` | `mattpocock/skills` | El proyecto se implementa con TDD estricto: ciclo rojo-verde-refactor y pruebas por la interfaz pública. | CH-01 a CH-10 |
| `python-testing-patterns` | `wshobson/agents` | Patrones de pytest: fixtures, pruebas asincrónicas y organización de la suite. | CH-01 a CH-11 |

La columna «Se usa en» se dedujo cruzando los roles de `AGENTS.md` con el alcance de cada change en `CHANGES.md`.

## Descartadas

| Skill | Origen | Motivo |
|---|---|---|
| `python-pro` | `jeffallan/claude-skills` | Al instalarla quedó marcada como *Critical Risk*, y sus reglas chocan con la consigna: Poetry en vez de `requirements.txt`, dataclasses en vez de Pydantic, y `mypy --strict` y más de 90 % de cobertura, que la consigna no pide. Se quitó del proyecto; la instalación global no se tocó. |
| `fastapi-templates` | `wshobson/agents` | Empuja una estructura de carpetas distinta de la obligatoria del PDF. |
| `fastapi-expert` | `jeffallan/claude-skills` | Se superpone con `fastapi` y `fastapi-patterns`. |

## Choques con la consigna

| Skill | Qué dice | Qué manda en este proyecto |
|---|---|---|
| `fastapi-patterns` | Estructura con `app/main.py`, `app/config.py` y `app/dependencies.py`. | La estructura obligatoria del PDF: `main.py` en la raíz, `app/core/{config,database,security,dependencies,repository,paginacion,unit_of_work}.py` y `app/modules/<módulo>/{models,schemas,repository,unit_of_work,service,router}.py`. |
| `fastapi-patterns`, `fastapi` | Paginación con `skip`/`limit` u `offset`/`limit`. | `page` (desde 1) y `size` (1 a 100, default 20), con el envoltorio `{items, total, page, size, pages}`. Página inexistente → 422. Nunca `limit`/`offset` en la API. |
| `fastapi-patterns` | Correo ya registrado → `400`. | Choque con lo guardado → **409**, nunca 400. |
| `fastapi` | «Ante la duda, usar `def` común», que corre en un threadpool. | Todos los handlers con `async def`, sin excepción. |
| `sqlalchemy-alembic-expert-best-practices-code-review`, `postgresql-table-design` | Agregar FK y CHECK con `NOT VALID` y validar aparte; crear índices con `CONCURRENTLY`. | Migraciones sin `CONCURRENTLY` ni `NOT VALID`: las tablas arrancan vacías y la primera migración es autogenerada. |
| `fastapi-patterns`, `python-testing-patterns` | La suite pytest va en `tests/` en la raíz. | La suite vive en `test/pytest/`, porque el PDF reserva `test/` para los `.http` y `solo_agregado.sql`. |
| `tdd` | Probar por la interfaz; verificar consultando la base es un acoplamiento a la implementación. | Excepción: C-05 se verifica en la base porque `intento_acceso` no tiene endpoint; C-02 y C-11, porque hay que comprobar que el rollback no dejó filas sueltas, y eso no se ve desde la API. |

## Verificación de que viajan con el proyecto

Se corrió desde la raíz del repo, el 2026-10-25.

**1. Que `.atl/` no esté ignorada por git** (sin salida y `exit=1` significa que no la ignora):

```
$ git check-ignore -v .atl .atl/skill-registry.md
(sin salida, exit=1)
```

**2. Que no haya enlaces simbólicos** (si los hubiera, las skills dependerían de archivos fuera del repo):

```
$ find .claude .agents .atl -type l
(sin salida, exit=0)
```

No hay ninguno: las skills están copiadas en el repo.

**3. Que no haya rutas a la carpeta del usuario:**

```
$ grep -rnI -E '~/\.claude|C:\\Users|C:/Users|/c/Users|\$HOME|USERPROFILE' .claude .agents .atl AGENTS.md CLAUDE.md skills-lock.json
AGENTS.md:93:> Reglas globales ya definidas en `~/.claude/CLAUDE.md` (orquestador, governance, TDD, engram): el proyecto las hereda. Acá viven solo las reglas **específicas de este proyecto** + las universales que el global no cubra.
CLAUDE.md:93:> Reglas globales ya definidas en `~/.claude/CLAUDE.md` (orquestador, governance, TDD, engram): el proyecto las hereda. Acá viven solo las reglas **específicas de este proyecto** + las universales que el global no cubra.
```

En `.claude/`, `.agents/`, `.atl/` y `skills-lock.json` no aparece ninguna ruta al usuario. El único hallazgo es la línea 93 de `AGENTS.md` (y de su copia `CLAUDE.md`). Es una referencia en el texto, no una ruta que algo cargue: ninguna skill ni comando depende de ese archivo para funcionar. Lo que indica es que las reglas globales (orquestador, governance, TDD estricto y Engram) no están en el repo: llegan al instalar Active Stack, que es la herramienta de la cátedra.
