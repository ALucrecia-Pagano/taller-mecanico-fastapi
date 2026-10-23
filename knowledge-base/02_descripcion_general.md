# Descripción General

## Stack tecnológico

Versiones mínimas: tabla «Requisitos técnicos» de la consigna (p. 3). Versión en uso: entorno del alumno.

| Componente | Versión mínima (consigna) | En uso | Uso |
|---|---|---|---|
| Python | 3.12 | 3.13 (`.venv` existente) | Lenguaje |
| FastAPI | 0.111 | — | Framework web; todos los handlers con `async def` |
| SQLModel | 0.0.24 | — | Modelos de tabla |
| SQLAlchemy | 2.0, asincrónico | — | Motor, sesión y carga anticipada |
| asyncpg | 0.30 | asyncpg | Controlador asincrónico de PostgreSQL (la consigna acepta también psycopg 3 asincrónico; se eligió asyncpg) |
| PostgreSQL | 16 | 17 | Base de datos |
| Alembic | 1.13, plantilla asincrónica | — | Migraciones |
| pydantic-settings | 2.0 | — | Configuración leída del entorno |
| bcrypt | 4.0 | — | Hash de las contraseñas |
| PyJWT | 2.8 | — | Token firmado |
| uvicorn | El que instala `fastapi[standard]` | — | Servidor ASGI |

Versiones exactas a fijar en `requirements.txt`: No especificado en la consigna (sólo mínimos).

## Arquitectura general

API asincrónica en capas, organizada por **módulo funcional**, con las mismas seis capas en todos los módulos:

```
HTTP ──► Router ──► Service ──► Unit of Work ──► Repository ──► Model (SQLModel)
           │           │              │                │
           │           │              │                └─ flush(), nunca commit(); precarga declarada en el método
           │           │              └─ async with: confirma al salir, revierte con excepción, NO cierra la sesión
           │           └─ reglas de negocio; recibe el UoW y lo abre; nunca lo construye
           └─ construye el UoW con una dependencia, llama al servicio y traduce errores
```

- Módulos mínimos: `health`, `usuarios`, `clientes`, `repuestos`, `ordenes` (detalle en [08_arquitectura_propuesta.md](08_arquitectura_propuesta.md)).
- Motor asincrónico y fábrica de sesiones creados en el **lifespan** y guardados en `app.state`; una sesión por petición (`get_session`).
- Dos grupos de rutas en `main.py`: **abierto** y **protegido** (el protegido lleva montado una sola vez el control del cambio obligatorio de contraseña).
- Esquema creado exclusivamente con Alembic (nunca `create_all`).

## Integraciones externas

| Servicio | Propósito | Tipo |
|---|---|---|
| PostgreSQL | Persistencia, unicidad, FK, CHECK, disparador de sólo agregado | Base de datos (asyncpg) |
| Aviso al cliente | Notificar al terminar una orden | **Simulado**: `BackgroundTasks` con `await asyncio.sleep(0.5)` y un mensaje en el registro (log) |

No hay otras integraciones externas en la consigna.

## API REST — resumen

Tabla completa con roles y códigos en [03_actores_y_roles.md](03_actores_y_roles.md#endpoints-de-referencia).

| Recurso | Endpoints |
|---|---|
| Salud | `GET /health/live`, `GET /health/ready` |
| Auth | `POST /auth/registro`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/yo`, `POST /auth/cambiar-password` |
| Usuarios y roles | `POST /usuarios`, `GET/POST /usuarios/{id}/roles`, `DELETE /usuarios/{id}/roles/{rol}`, `GET /eventos` |
| Clientes y vehículos | `POST /clientes`, `GET /clientes/{id}`, `POST /clientes/{id}/vehiculos`, `DELETE /vehiculos/{id}`, `GET /mis-vehiculos` |
| Repuestos | `GET /repuestos`, `GET/PATCH/DELETE /repuestos/{id}`, `POST /repuestos`, `POST /repuestos/{id}/reponer`, `GET /repuestos/{id}/movimientos`, `GET /repuestos/{id}/precios` |
| Órdenes | `POST /ordenes`, `GET /ordenes`, `GET /ordenes/{id}`, `POST /ordenes/{id}/iniciar`, `POST /ordenes/{id}/terminar`, `POST /ordenes/{id}/cancelar`, `GET /mis-ordenes` |
| Catálogo | `GET /estados-orden` |

### Convenciones transversales de la API (Ejercicio 3)

- Contratos (schemas) separados de los modelos de tabla; los de entrada con `extra="forbid"`.
- Ninguna respuesta incluye `password_hash`.
- `PATCH` aplica sólo los campos enviados (`exclude_unset`).
- Códigos: **201** al crear, **204** al dar de baja, **404** si el recurso de la ruta no existe, **409** si choca con lo guardado, **422** si el cuerpo o los parámetros no cumplen el contrato.
- Listados con el envoltorio `{items, total, page, size, pages}`: `page` empieza en 1; `size` de 1 a 100 (por defecto 20); página más allá de la última → 422 (ej.: «La página 3 no existe: hay 2»); `total` cuenta con los mismos filtros que la página; con cero resultados hay una página, vacía.
- Dinero como `NUMERIC` en la base y `Decimal` en Python, nunca `float`; en JSON viaja como string (ej. `"68000.00"`).
- Fechas `timestamptz`; en JSON con zona (ej. `"2026-10-23T02:18:54.332849Z"`).
