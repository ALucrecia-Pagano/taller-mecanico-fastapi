# Arquitectura Propuesta

## Patrones aplicados

| Patrón | Dónde se usa | Por qué (consigna) |
|---|---|---|
| Arquitectura en capas Router → Service → UoW → Repository → Model | Todos los módulos | Cada capa sabe lo suyo y nada más |
| Organización por módulo funcional | `app/modules/<módulo>/` | Las mismas seis capas en todos los módulos |
| Repository genérico (`BaseRepository[T]`, `SoftDeleteRepository[T]`) | `app/core/repository.py` | Reutilizar CRUD; el constructor recibe la clase del modelo porque los genéricos se borran en tiempo de ejecución (6.4.3) |
| Repositorio de sólo lectura (sin herencia) | Catálogo `estado_orden` | Su PK no es `id` y no debe ofrecer `add`/`update`/`delete` |
| Unit of Work (gestor de contexto async) | `app/core/unit_of_work.py` + uno por módulo | Una operación de negocio = una transacción; confirma o revierte al salir |
| Inyección de dependencias de FastAPI | `get_session`, UoW, `get_usuario_actual`, `requiere_rol` | El router construye; el servicio sólo abre |
| Borrado lógico + índice único parcial | `vehiculo`, `repuesto` | Unicidad sólo entre vigentes |
| Tabla de catálogo con FK | `estado_orden` | En lugar de un CHECK con la lista |
| Sólo agregado por disparador | Tres tablas de historial/movimientos | La base garantiza que no se corrigen |
| Punto único de escritura | Stock de repuestos | El stock sólo cambia por movimientos (RN-14) |
| Lifespan | `main.py` | Recursos creados con el bucle de eventos ya existente (EA-08) |
| Tarea en segundo plano | `BackgroundTasks` al terminar una orden | Aviso simulado después de la respuesta |

## Estructura de directorios (obligatoria)

Textual de la consigna (pp. 9-10):

| Ruta | Contenido |
|---|---|
| `main.py` | Aplicación, lifespan y los dos grupos de rutas |
| `seed.py` | Deja la base en el estado inicial conocido |
| `app/core/config.py` | Settings con pydantic-settings |
| `app/core/database.py` | Las funciones que crean el motor y la fábrica de sesiones (las llama el lifespan), y `get_session` |
| `app/core/security.py` | Hash con bcrypt fuera del bucle, y emisión y verificación del token |
| `app/core/dependencies.py` | Usuario actual, roles vigentes, control del cambio obligatorio y `requiere_rol` |
| `app/core/repository.py` | `BaseRepository[T]` y `SoftDeleteRepository[T]` |
| `app/core/paginacion.py` | El envoltorio de los listados y el cálculo de las páginas |
| `app/core/unit_of_work.py` | UnitOfWork base: confirma o revierte al salir del bloque |
| `app/modules/<módulo>/models.py` | Modelos de tabla, restricciones y relaciones |
| `app/modules/<módulo>/schemas.py` | Contratos de entrada y de salida |
| `app/modules/<módulo>/repository.py` | Los repositorios de cada entidad del módulo |
| `app/modules/<módulo>/unit_of_work.py` | El Unit of Work del módulo, con los repositorios que sus operaciones necesitan |
| `app/modules/<módulo>/service.py` | Las reglas de negocio. Recibe el Unit of Work y lo abre |
| `app/modules/<módulo>/router.py` | Rutas HTTP: construyen el Unit of Work, llaman al servicio y traducen errores |
| `migrations/` | Configuración de Alembic y sus versiones |
| `test/` | Archivos `.http` y `solo_agregado.sql` con los casos de prueba |

Módulos mínimos: `health`, `usuarios`, `clientes`, `repuestos` y `ordenes`. El módulo `health` sólo tiene `router.py`.

```
Taller_mecanico_giuliano/
├── main.py
├── seed.py
├── requirements.txt
├── env.example
├── alembic.ini                 # sin credenciales
├── README.md
├── app/
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── security.py
│   │   ├── dependencies.py
│   │   ├── repository.py
│   │   ├── paginacion.py
│   │   └── unit_of_work.py
│   └── modules/
│       ├── health/      router.py
│       ├── usuarios/    models.py schemas.py repository.py unit_of_work.py service.py router.py
│       │                (Usuario, AsignacionRol, IntentoAcceso, EventoSeguridad)
│       ├── clientes/    … (Cliente, Vehiculo)
│       ├── repuestos/   … (Repuesto, MovimientoStock, HistorialPrecio)
│       └── ordenes/     … (OrdenTrabajo, EstadoOrden, ItemOrden, HistorialEstadoOrden)
├── migrations/
│   ├── env.py                  # plantilla async
│   └── versions/
│       ├── <rev1>_esquema_inicial.py       # --autogenerate (leída y comentada)
│       └── <rev2>_solo_agregado.py         # a mano: función + disparador
├── requirements-dev.txt        # pytest, pytest-asyncio, httpx… (DA-26)
├── docs/
│   └── evidencias/             # capturas de C-14 y C-15 (DA-30)
└── test/
    ├── *.http                  # C-01 … C-19, respuesta esperada en un comentario
    ├── solo_agregado.sql       # C-14
    └── pytest/                 # suite TDD (DA-26); conftest usa <POSTGRES_DB>_test (DA-29)
```

> Los archivos `__init__.py` y los nombres de las revisiones de Alembic no están fijados por la consigna.

## Responsabilidades por capa

| Capa | Hace | Nunca |
|---|---|---|
| Router | Construye el UoW (dependencia), llama al servicio, traduce excepciones de dominio a HTTP, agenda `BackgroundTasks` | Abre el UoW; contiene reglas de negocio |
| Service | Reglas de negocio; abre el UoW con `async with`; calcula hashes **antes** de abrir | Construye el UoW; hace `commit()` directo |
| UoW | Compone los repositorios del módulo sobre una sesión; commit al salir, rollback con excepción | Cierra la sesión (no la creó) |
| Repository | Consultas; `flush()` en `add`/`update`; precarga declarada en el método | `commit()`; carga perezosa |
| Model | Tablas, restricciones, índices, relaciones | — |

## Seguridad

- **Autenticación**: contraseña con bcrypt (costo configurable; `asyncio.to_thread` + semáforo; ≤ 72 bytes). JWT firmado (PyJWT) con `sub`, `iat` (con fracción de segundo), `exp`, roles vigentes. Algoritmo de firma: `HS256` (`JWT_ALGORITHM`, [09 DA-07](09_decisiones_y_supuestos.md)).
- **Transporte del token**: **sólo** cookie `access_token`; `HttpOnly`, `SameSite=Lax`, `Max-Age` = duración del token, `Secure` configurable. Nunca en el cuerpo, nunca leído de `Authorization`.
- **Autorización**: `requiere_rol` consulta `asignacion_rol` vigente en cada petición; 401 vs 403 siempre distinguidos; grupo protegido con control del cambio obligatorio montado una sola vez.
- **Anti-enumeración**: mismo cuerpo y tiempo con o sin correo existente (hash ficticio calculado una vez en el lifespan).
- **Límite de intentos**: conteo sobre `intento_acceso` (5 fallos / 60 s por correo + IP) → 429 + `Retry-After`.
- **Validación de input**: contratos Pydantic con `extra="forbid"`; parámetros ligados en SQL; ninguna entrada inválida → 500.
- **Errores**: traducción de `IntegrityError` a 409 con mensaje propio; nunca texto de la base ni traza (RN-18).
- **Secretos**: clave de firma y contraseña de la base sin valor por defecto (la app no arranca si faltan); `.env` fuera del repo; `env.example` sin secretos; `alembic.ini` sin credenciales (Alembic toma la URL de `Settings`).
- **Clave de firma** (aclaración del profe): se genera **una sola vez** con
  ```
  python -c "import secrets; print(secrets.token_urlsafe(64))"
  ```
  se guarda en `.env` y queda fija. Nunca se genera al arrancar la app (cambiaría en cada reinicio y dos procesos se rechazarían los tokens), nunca va en el código ni en el repo.

## Variables de entorno

Nombres y valores por defecto: [09 DA-07](09_decisiones_y_supuestos.md). Regla: **los secretos no tienen valor por defecto** (si faltan, la app no arranca); el resto sí.

| Variable | Descripción | Default en `Settings` | Sensible | Origen del nombre |
|---|---|---|---|---|
| `POSTGRES_USER` | Usuario de la base | `postgres` | N | Consigna |
| `POSTGRES_PASSWORD` | Contraseña de la base | **sin default** | **Y** | Consigna |
| `POSTGRES_DB` | Nombre de la base | `taller_mecanico` | N | Consigna |
| `POSTGRES_HOST` | Host | `localhost` | N | Consigna |
| `POSTGRES_PORT` | Puerto | `5432` | N | Consigna |
| `JWT_SECRET_KEY` | Clave de firma; se genera una vez con `python -c "import secrets; print(secrets.token_urlsafe(64))"` | **sin default** | **Y** | DA-07 |
| `JWT_ALGORITHM` | Algoritmo de firma | `HS256` | N | DA-07 |
| `JWT_EXPIRE_SECONDS` | Duración del token; también `Max-Age` de la cookie y `expira_en_segundos` del login | `1800` | N | DA-07 |
| `BCRYPT_COST` | Rondas de bcrypt | `12` | N | DA-07 |
| `BCRYPT_MAX_CONCURRENCY` | Tamaño del semáforo de bcrypt | `4` | N | DA-07 |
| `DB_POOL_SIZE` | Pool del motor async | `5` | N | DA-07 |
| `DB_MAX_OVERFLOW` | Conexiones extra sobre el pool | `10` | N | DA-07 |
| `COOKIE_SECURE` | Atributo `Secure` de la cookie | `false` | N | DA-07 |
| `SQL_ECHO` | Muestra las consultas en consola (C-15) | `false` | N | Consigna |
| `LOGIN_MAX_FALLOS` | Fallos que disparan el 429 (RN-08) | `5` | N | DA-07 |
| `LOGIN_VENTANA_SEGUNDOS` | Ventana del conteo (RN-08) | `60` | N | DA-07 |

> `LOGIN_MAX_FALLOS` y `LOGIN_VENTANA_SEGUNDOS` son configurables, pero RN-08 y C-05 fijan **5** y **60**: los defaults no se cambian para la entrega.
>
> `env.example` lista **todas** las variables, con `POSTGRES_PASSWORD` y `JWT_SECRET_KEY` vacías.

## Entrega (formato)

Repositorio con: código fuente completo, `requirements.txt`, `env.example`, `alembic.ini`, `migrations/`, `test/`; `.env` no se sube. `README.md` con los pasos desde cero: entorno virtual, dependencias, `.env` (con cómo generar la clave de firma), `alembic upgrade head`, `python seed.py` y arranque del servidor. Evidencias de C-14 y C-15 ([12](12_criterios_de_evaluacion.md)).
