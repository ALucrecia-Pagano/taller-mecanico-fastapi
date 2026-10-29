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
| CH-03 `modelos-migraciones` | Las 13 tablas del dominio con sus restricciones (CHECK, UNIQUE, tres índices únicos parciales, estados por clave foránea al catálogo, un índice por clave foránea) y nombres de restricción fijos; navegación entre entidades sin carga implícita; dos migraciones: `0001` autogenerada y `0002` escrita a mano, con el disparador que rechaza UPDATE y DELETE en las tres tablas de sólo agregado; `test/solo_agregado.sql` (C-14). Paso nuevo de puesta en marcha: `alembic upgrade head` |
| CH-04 `seguridad-base-seed` | Contraseñas con bcrypt fuera del bucle y bajo un semáforo, costo desde la configuración y límite de 72 bytes; token JWT con `sub`, `iat` con fracción de segundo, `exp` y roles; hash ficticio del login calculado una vez en el lifespan; token inválido → 401; `seed.py` con los datos iniciales del PDF; evidencia de C-14. Sin endpoints nuevos. Paso nuevo de puesta en marcha: `python seed.py` |

**Planificado** (detalle en [CHANGES.md](CHANGES.md)):

| Change | Qué incluye |
|---|---|
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

### 5. Migraciones

Crea el esquema en la base de la aplicación (la que indica `POSTGRES_DB` en el `.env`):

```bash
alembic upgrade head
```

`alembic current` tiene que mostrar `0002 (head)`. Las tablas quedan vacías, incluido el catálogo de estados: los datos iniciales llegan con `python seed.py` (paso siguiente). La base de prueba no se migra a mano: la migra la suite al arrancar.

Para volver a la base vacía: `alembic downgrade base`.

### 6. Datos iniciales

Deja la base de la aplicación en el estado inicial conocido que usan los casos de prueba:

```bash
python seed.py
```

- **Primero muestra a qué base va** (nombre, host y puerto), y después **vacía todas las tablas** y carga los datos iniciales de la consigna: el catálogo de estados, 7 usuarios, 2 clientes, 3 vehículos, 4 repuestos con su stock inicial, las órdenes 1 y 2, y el historial de precios y de seguridad. Los ids coinciden con los ejemplos de la consigna.
- **No pide confirmación.** Si algo falla, la base queda como estaba, porque todo ocurre en una sola transacción.
- **Se puede correr las veces que haga falta**, y se corre **antes de cada archivo `.http`**, porque las pruebas cambian los datos.
- Sin esquema, corta con «Corré `alembic upgrade head` primero».
- Las contraseñas de los usuarios del seed son ficticias y están sólo en `seed.py`.

### 7. Levantar el servidor

```bash
uvicorn main:app --reload
```

### 8. Probar la salud

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

### Caso C-14 (sólo agregado)

`test/solo_agregado.sql` muestra en `psql` los seis rechazos del disparador y el de la clave foránea. Se corre **después** de `python seed.py`, sobre la base de la aplicación. Sin los datos iniciales, el archivo se detiene al principio con «Corré python seed.py primero».

Pasos en Git Bash, desde la raíz del repositorio. El `tee` deja en pantalla, para la captura, la misma salida que guarda en el archivo:

```bash
source .venv/Scripts/activate
alembic upgrade head                      # si la base no está en head
python seed.py
export PGCLIENTENCODING=UTF8
psql -U postgres -d taller_mecanico -f test/solo_agregado.sql 2>&1 | tee docs/evidencias/C-14-psql.txt
#   -> captura de esa ventana: docs/evidencias/capturas/C-14-solo-agregado.png
file docs/evidencias/C-14-psql.txt                     # esperado: UTF-8 text
grep -c "ERROR" docs/evidencias/C-14-psql.txt          # esperado: 7
grep -c "sólo agregado" docs/evidencias/C-14-psql.txt  # esperado: 6
python seed.py                            # repone la secuencia que consumió la sentencia 7
```

- **El `python seed.py` final es necesario.** La séptima sentencia falla por la clave foránea, pero consume un número de la secuencia de `orden_trabajo`. Sin volver a correr el seed, la próxima orden creada por la API no tendría el id que esperan los ejemplos.
- **No usar `winpty psql`:** con `winpty`, la consola usa la página de códigos 850 (los acentos salen rotos) y el `tee` deja de funcionar. En Git Bash, `psql` ya escribe UTF-8.

La evidencia queda en `docs/evidencias/C-14-psql.txt` (texto) y en `docs/evidencias/capturas/C-14-solo-agregado.png` (captura).
