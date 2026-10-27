# Taller Mecánico — API REST

Trabajo práctico integrador de Programación III (prof. Giuliano). Es una API REST asincrónica para un taller mecánico, construida con FastAPI, SQLModel, SQLAlchemy asincrónico (asyncpg), PostgreSQL y Alembic.

La consigna está en `docs/consigna/consigna-taller-mecanico.pdf`. El plan de implementación completo, con los 11 changes, sus dependencias y su alcance, está en [CHANGES.md](CHANGES.md).

## Estado

El proyecto se construye change por change. Este README se actualiza en cada uno, para que el repositorio se pueda levantar en cualquier punto del camino.

**Implementado:**

| Change | Qué incluye |
|---|---|
| CH-01 `proyecto-config-salud` | Configuración desde el entorno (sin secretos por defecto); motor y fábrica de sesiones creados en el lifespan; `GET /health/live` y `GET /health/ready`; Alembic con la plantilla asincrónica (todavía sin migraciones); suite de pruebas contra la base de prueba |
| CH-02 `core-repositorios-uow` | Repositorios genéricos (`BaseRepository`, `SoftDeleteRepository`) que nunca confirman; Unit of Work que confirma o revierte al salir; paginación `{items, total, page, size, pages}`; traducción de los choques con la base a 409 con mensaje propio y de los errores de dominio a HTTP en cada router. Sin endpoints nuevos ni pasos nuevos de puesta en marcha |

**Planificado** (detalle en [CHANGES.md](CHANGES.md)):

| Change | Qué incluye |
|---|---|
| CH-03 | Modelos, restricciones y las dos migraciones |
| CH-04 | bcrypt, JWT y `seed.py` |
| CH-05 a CH-06 | Autenticación, roles y los dos grupos de rutas |
| CH-07 a CH-10 | Clientes, vehículos, repuestos, stock y órdenes de trabajo |
| CH-11 | Verificación final y evidencias |

## Requisitos

- Python 3.12 o superior (el proyecto se desarrolla con 3.13).
- PostgreSQL 16 o superior (el proyecto se desarrolla con 17), con `psql` disponible en la terminal.

## Puesta en marcha desde cero

Los comandos se corren desde la raíz del proyecto. Cuando cambian según la terminal, se indican las tres variantes.

### 1. Entorno virtual

Git Bash:

```bash
python -m venv .venv
source .venv/Scripts/activate
```

PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Dependencias

```bash
pip install -r requirements.txt
```

### 3. Archivo `.env`

Copiá la plantilla. El `.env` no se versiona.

Git Bash y Linux:

```bash
cp env.example .env
```

PowerShell:

```powershell
Copy-Item env.example .env
```

Después completá en el `.env` las dos variables que vienen vacías:

- `POSTGRES_PASSWORD`: la contraseña de tu usuario de PostgreSQL.
- `JWT_SECRET_KEY`: la clave de firma de los tokens. Se genera **una sola vez** con este comando (es el mismo en las tres terminales), se pega en el `.env` y queda fija:

  ```
  python -c "import secrets; print(secrets.token_urlsafe(64))"
  ```

Si alguna de las dos falta o está vacía, la aplicación no arranca. La clave tiene que tener al menos 32 caracteres.

El resto de las variables ya tiene su valor por defecto en la plantilla. No agregues al `.env` variables que no estén en `env.example`: la configuración rechaza las desconocidas, para que un error de tipeo no pase en silencio.

### 4. Bases de datos

Se crean dos bases: la de la aplicación y la de las pruebas, que se llama igual con el sufijo `_test`.

```bash
psql -U postgres -c "CREATE DATABASE taller_mecanico;"
psql -U postgres -c "CREATE DATABASE taller_mecanico_test;"
```

En esta etapa las bases quedan vacías: las tablas llegan con las migraciones de CH-03.

### 5. Levantar el servidor

```bash
uvicorn main:app --reload
```

### 6. Probar la salud

Con el servidor levantado, desde otra terminal:

Git Bash y Linux:

```bash
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

PowerShell:

```powershell
Invoke-RestMethod http://localhost:8000/health/live
Invoke-RestMethod http://localhost:8000/health/ready
```

También se pueden ejecutar las peticiones de `test/health.http` desde el editor (por ejemplo, con la extensión REST Client de VS Code).

Respuestas esperadas:

| Sonda | Base disponible | Base caída o sin respuesta en 3 s |
|---|---|---|
| `GET /health/live` | 200 `{"estado": "vivo"}` | 200 `{"estado": "vivo"}` |
| `GET /health/ready` | 200 `{"estado": "listo"}` | 503 `{"detail": "La base de datos no responde"}` |

La aplicación arranca aunque la base esté caída: el proceso puede estar vivo y no estar listo.

## Pruebas

La suite automática vive en `test/pytest/` y corre **sólo** contra la base `<POSTGRES_DB>_test` (por ejemplo, `taller_mecanico_test`). Si la configuración apunta a una base cuyo nombre no termina en `_test`, la prueba no corre. Necesita el `.env` completo y la base de prueba creada (paso 4).

```bash
pip install -r requirements-dev.txt
pytest -v
```

`POSTGRES_DB` en el `.env` tiene que ser la base de la aplicación, no la de prueba: la suite deriva sola el nombre `_test`, y aborta con un mensaje si el `.env` ya apunta a una base de prueba.
