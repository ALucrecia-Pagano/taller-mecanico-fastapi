# Skill Registry

**Delegator use only.** Any agent that launches sub-agents reads this registry to resolve compact rules, then injects them directly into sub-agent prompts. Sub-agents do NOT read this registry or individual SKILL.md files.

See `_shared/skill-resolver.md` for the full resolution protocol.

Project: Taller mecanico (Programacion III) - Python 3.13, FastAPI, SQLModel, SQLAlchemy 2 async, asyncpg, PostgreSQL 17, Alembic async, pydantic-settings, bcrypt, PyJWT. Skills are installed at project level (`.claude/skills/`, locked in `skills-lock.json`). `python-pro` was intentionally removed (conflicts with course rules) - do not use.

## User Skills

| Trigger | Skill | Path |
|---------|-------|------|
| FastAPI APIs, Pydantic models, dependencies, routers, SSE | fastapi | .claude/skills/fastapi/SKILL.md |
| Building/reviewing FastAPI apps: schemas, DI, async handlers, auth, service layer, httpx/pytest tests | fastapi-patterns | .claude/skills/fastapi-patterns/SKILL.md |
| Writing/reviewing SQLAlchemy models, Alembic migrations, indexes, constraints, query patterns | sqlalchemy-alembic-expert-best-practices-code-review | .claude/skills/sqlalchemy-alembic-expert-best-practices-code-review/SKILL.md |
| Designing/reviewing PostgreSQL schema: types, keys, constraints, indexes | postgresql-table-design | .claude/skills/postgresql-table-design/SKILL.md |
| Build features or fix bugs test-first, red-green-refactor, integration tests | tdd | .claude/skills/tdd/SKILL.md |
| Writing Python tests, pytest suites, fixtures, mocking, coverage | python-testing-patterns | .claude/skills/python-testing-patterns/SKILL.md |

## Compact Rules

Pre-digested rules per skill. Delegators copy matching blocks into sub-agent prompts as `## Project Standards (auto-resolved)`.

### fastapi
- Use `Annotated` for all params and deps (`Path`, `Query`, `Depends`); make reusable aliases: `CurrentUserDep = Annotated[dict, Depends(get_current_user)]`.
- Never use `...` (Ellipsis) as default for required params/model fields; never use Pydantic `RootModel` (use `Annotated[list[int], Field(min_length=1), Body()]`).
- Prefer return type annotations (`-> Item`); use `response_model` when public schema differs from internal return. Do not use `ORJSONResponse`/`UJSONResponse` (deprecated).
- Put `prefix`, `tags`, shared `dependencies` on the `APIRouter`, not in `include_router()`.
- One HTTP operation per function; never mix methods in one handler.
- `async def` only if everything inside is non-blocking and awaited; otherwise plain `def` (threadpool). Never run blocking code inside `async def`.
- Run with `fastapi dev` / `fastapi run`; entrypoint can be declared in `[tool.fastapi]` of pyproject.
- Skill suggests SQLModel over raw SQLAlchemy and uv/Ruff - consistent with this stack (SQLModel); here DB access is ASYNC (asyncpg), so use `async def` + `AsyncSession`.

### fastapi-patterns
- Structure: app factory + lifespan in `app/main.py`; config via pydantic-settings in `app/config.py`; layers: routers -> services -> models/schemas; deps in `app/dependencies.py`.
- Pydantic v2 schemas: separate Create/Update/Response models; Response never exposes password hashes or internal fields. Always declare a typed `response_model`.
- Routes must be thin: business logic and transactions (commit/rollback, catching DB integrity errors) live in the service layer, not in handlers.
- Alias DB dep: `DbDep = Annotated[AsyncSession, Depends(get_db)]`. Use `await db.execute(select(...))` + `.scalars()`; never sync `Session` in async routes.
- Translate domain errors to HTTPException in the router (e.g. duplicate -> 400/409); use proper status codes (`status_code=201` on create).
- Auth: keep authentication dependency separate from authorization checks so 401 vs 403 are precise; parse JWT claims defensively (str/int casts).
- Paginated endpoints must have deterministic sort (`.order_by(Model.id)`) with limit/offset.
- Tests: httpx `AsyncClient` with ASGI transport + pytest fixtures in `tests/conftest.py`; override deps (`app.dependency_overrides`) for the test DB.

### sqlalchemy-alembic-expert-best-practices-code-review
- Create indexes in Alembic with `postgresql_concurrently=True` inside an autocommit block (`op.get_context().autocommit_block()`).
- Every query pattern (filters/joins/sorts) must be backed by an index; FK columns need manual indexes.
- Unique constraints on populated tables: create unique index concurrently first, then add constraint using that index.
- Foreign keys and CHECK constraints: add `NOT VALID` first, then `VALIDATE CONSTRAINT` in a separate step.
- Column type changes: multi-step (add new column, backfill, swap) to avoid long table locks.
- Non-unique indexes: max 3 columns; do not add indexes already covered by a composite index's leftmost prefix.
- Note: concurrency rules target live production tables; for fresh/empty tables in this TP they are low-risk, but keep migrations reversible (downgrade) and async env.py correct.

### postgresql-table-design
- PK: `BIGINT GENERATED ALWAYS AS IDENTITY` (UUID only if opaque/global ids needed); never `serial`.
- Types: `TIMESTAMPTZ` (never bare `timestamp`), `NUMERIC(p,s)` for money (never `money`), `TEXT` (not `varchar(n)`/`char(n)`; use CHECK for length), `BOOLEAN NOT NULL`.
- Add `NOT NULL` wherever semantically required, sensible `DEFAULT`s; CHECK passes on NULL so combine with NOT NULL (`CHECK (stock >= 0)`).
- PostgreSQL does NOT auto-index FK columns: index every FK; specify `ON DELETE/UPDATE` behavior explicitly.
- UNIQUE allows multiple NULLs; use `NULLS NOT DISTINCT` (PG15+) when needed. Case-insensitive uniqueness: unique index on `LOWER(col)`.
- Enums only for small stable sets; otherwise `TEXT` + CHECK or lookup table. `snake_case` unquoted identifiers.
- Normalize to 3NF; denormalize only with measured need. Partial/expression/composite indexes (leftmost-prefix rule) for real query paths.
- Identity gaps are normal, do not "fix".

### tdd
- Red before green: write the failing test first, then only enough code to pass; no speculative features.
- One vertical slice at a time (one seam, one test, one implementation); never write all tests first then all code.
- Test behavior through public interfaces (seams), not internals; do not mock internal collaborators or test private methods; do not verify via side channels (e.g. querying DB directly instead of the API).
- Agree seams under test with the user before writing any test (give each seam a one-line note: what it catches / misses).
- No tautological assertions: expected values come from an independent source (literal, worked example, spec), never recomputed like the code does.
- Refactoring is NOT part of the red-green loop; it belongs to review stage.
- Read `GLOSSARY.md` if present so test names use domain language.

### python-testing-patterns
- Structure tests AAA (Arrange/Act/Assert); keep tests independent with no shared state; clean up after each test.
- Layout: `tests/conftest.py` for shared fixtures, `tests/test_unit/`, `tests/test_integration/`, `tests/test_e2e/`.
- Naming: `test_<unit>_<scenario>_<expected>` - descriptive, not `test_1`/`test_works`.
- Use fixtures for setup/teardown, `pytest.mark.parametrize` for input variations, markers (`slow`, `integration`) registered and selectable with `-m`.
- Mock only external boundaries (time, network, I/O); freeze time with freezegun when testing time logic.
- Coverage: `pytest --cov=app --cov-report=term-missing`; aim for meaningful coverage, not a percentage.
- Async tests need pytest-asyncio (or anyio) configured consistently.

## Project Conventions

| File | Path | Notes |
|------|------|-------|
| (none) | - | No AGENTS.md / CLAUDE.md / .cursorrules at project root yet. Project docs: `knowledge-base/` (KB), `CHANGES.md` (roadmap), `openspec/` |

Read the convention files listed above for project-specific patterns and rules. All referenced paths have been extracted - no need to read index files to discover more.
