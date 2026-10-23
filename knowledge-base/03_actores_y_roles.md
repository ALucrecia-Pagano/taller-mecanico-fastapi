# Actores y Roles

## Actores del sistema

| Actor | Rol en `asignacion_rol` | Descripción | Cómo interactúa |
|---|---|---|---|
| Anónimo | — | Cualquiera sin sesión | Rutas de salud, registro, login, logout |
| Cliente | `CLIENTE` | Persona que se registra sola en la web | Ve sus vehículos y las órdenes de sus vehículos; cancela su orden pendiente |
| Recepción | `RECEPCION` | Personal de mostrador | Clientes, vehículos, alta y cancelación de órdenes |
| Mecánico | `MECANICO` | Personal de taller | Inicia órdenes (queda asignado) y termina las suyas |
| Administrador | `ADMIN` | Gestor del taller | Repuestos, stock, personal, roles, eventos de seguridad |
| Sistema | — (texto `SISTEMA`) | Actor no humano de `evento_seguridad` | Registra los datos iniciales («Carga de los datos iniciales»). Es un texto, no un usuario |

Roles válidos (CHECK en `asignacion_rol.rol`): `ADMIN`, `RECEPCION`, `MECANICO`, `CLIENTE`.

### Cómo se determinan los roles

- `usuario` **no** tiene columna `rol`. Los roles de una persona son las filas de `asignacion_rol` **vigentes**: no revocadas (`revocada_en IS NULL`) y sin vencer (`vence_en` nulo o futuro).
- Los permisos se deciden con los roles vigentes **en la base, en cada petición** (RN-04). Los roles del token son informativos.
- Un usuario puede tener varios roles (p. ej., el dueño de un vehículo con rol `CLIENTE`).
- «El personal» (detalle de orden) = `ADMIN`, `RECEPCION`, `MECANICO` (inferido: los roles de personal; ver [09](09_decisiones_y_supuestos.md#su-05--el-personal)).

## Endpoints de referencia

Textual de la consigna (pp. 15-17). **Toda ruta del grupo protegido responde además 401 sin sesión y 403 con el cambio de contraseña pendiente.**

| Grupo | Método | Ruta | Quién | Códigos |
|---|---|---|---|---|
| Abierto | GET | `/health/live` | Cualquiera | 200 |
| Abierto | GET | `/health/ready` | Cualquiera | 200, 503 |
| Abierto | POST | `/auth/registro` | Cualquiera | 201, 409, 422 |
| Abierto | POST | `/auth/login` | Cualquiera | 200, 401, 422, 429 |
| Abierto | POST | `/auth/logout` | Cualquiera | 200 |
| Abierto | GET | `/auth/yo` | Autenticado | 200, 401 |
| Abierto | POST | `/auth/cambiar-password` | Autenticado | 200, 401, 422 |
| Protegido | POST | `/usuarios` (alta de personal, con contraseña provisoria) | ADMIN | 201, 409, 422 |
| Protegido | GET | `/usuarios/{id}/roles` | ADMIN | 200, 404 |
| Protegido | POST | `/usuarios/{id}/roles` | ADMIN | 201, 404, 409, 422 |
| Protegido | DELETE | `/usuarios/{id}/roles/{rol}` | ADMIN | 200, 404, 409 |
| Protegido | GET | `/eventos` (`page`, `size`) | ADMIN | 200, 422 |
| Protegido | POST | `/clientes` | RECEPCION, ADMIN | 201, 409, 422 |
| Protegido | GET | `/clientes/{id}` (con sus vehículos) | RECEPCION, ADMIN | 200, 404 |
| Protegido | POST | `/clientes/{id}/vehiculos` | RECEPCION, ADMIN | 201, 404, 409, 422 |
| Protegido | DELETE | `/vehiculos/{id}` | RECEPCION, ADMIN | 204, 404, 409 |
| Protegido | GET | `/mis-vehiculos` | Autenticado | 200 |
| Protegido | GET | `/repuestos` (`q`, `page`, `size`) | ADMIN, RECEPCION, MECANICO | 200, 422 |
| Protegido | GET | `/repuestos/{id}` | ADMIN, RECEPCION, MECANICO | 200, 404 |
| Protegido | POST | `/repuestos` (con `stock_inicial`) | ADMIN | 201, 409, 422 |
| Protegido | PATCH | `/repuestos/{id}` (descripción y precio) | ADMIN | 200, 404, 422 |
| Protegido | DELETE | `/repuestos/{id}` | ADMIN | 204, 404 |
| Protegido | POST | `/repuestos/{id}/reponer` | ADMIN | 200, 404, 422 |
| Protegido | GET | `/repuestos/{id}/movimientos` | ADMIN | 200, 404 |
| Protegido | GET | `/repuestos/{id}/precios` (historial de precios) | ADMIN | 200, 404 |
| Protegido | POST | `/ordenes` | RECEPCION, ADMIN | 201, 409, 422 |
| Protegido | GET | `/ordenes` (`estado`, `page`, `size`) | ADMIN, RECEPCION, MECANICO | 200, 422 |
| Protegido | GET | `/ordenes/{id}` | El personal, o el dueño del vehículo | 200, 403, 404 |
| Protegido | POST | `/ordenes/{id}/iniciar` | MECANICO | 200, 404, 409 |
| Protegido | POST | `/ordenes/{id}/terminar` | El mecánico asignado, o ADMIN | 200, 403, 404, 409 |
| Protegido | POST | `/ordenes/{id}/cancelar` | RECEPCION, ADMIN o el dueño | 200, 403, 404, 409 |
| Protegido | GET | `/estados-orden` (el catálogo, por posición) | Autenticado | 200 |
| Protegido | GET | `/mis-ordenes` (`page`, `size`) | Autenticado | 200, 422 |

> La tabla de códigos no lista el 403 por falta de rol en las rutas con `requiere_rol`, pero C-06 («Sin rol, 403») y C-18 («la recepción recibe 403») lo exigen. Ver [09 SU-04](09_decisiones_y_supuestos.md).

## RBAC — Matriz de permisos

| Recurso / acción | ADMIN | RECEPCION | MECANICO | CLIENTE / autenticado | Anónimo |
|---|---|---|---|---|---|
| Alta de personal (`POST /usuarios`) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Ver / asignar / revocar roles | ✅ | ❌ | ❌ | ❌ | ❌ |
| Ver eventos de seguridad | ✅ | ❌ | ❌ | ❌ | ❌ |
| Alta de cliente, ver cliente, alta de vehículo, baja de vehículo | ✅ | ✅ | ❌ | ❌ | ❌ |
| Mis vehículos / mis órdenes | ✅* | ✅* | ✅* | ✅ | ❌ |
| Listar y ver repuestos | ✅ | ✅ | ✅ | ❌ | ❌ |
| Alta, edición, baja, reposición de repuestos; movimientos; historial de precios | ✅ | ❌ | ❌ | ❌ | ❌ |
| Alta de orden | ✅ | ✅ | ❌ | ❌ | ❌ |
| Listar órdenes | ✅ | ✅ | ✅ | ❌ | ❌ |
| Ver detalle de orden | ✅ | ✅ | ✅ | sólo si es dueño del vehículo | ❌ |
| Iniciar orden | ❌ | ❌ | ✅ | ❌ | ❌ |
| Terminar orden | ✅ | ❌ | sólo el asignado | ❌ | ❌ |
| Cancelar orden | ✅ | ✅ | ❌ | sólo si es dueño del vehículo | ❌ |
| Ver catálogo de estados | ✅ | ✅ | ✅ | ✅ | ❌ |

\* «Lo propio sólo pide estar autenticado» (RN-17). Un usuario sin ficha de cliente recibe 200 con lista vacía (`/mis-ordenes` con el envoltorio paginado vacío) ([09 DA-14](09_decisiones_y_supuestos.md)).

### Reglas de autorización especiales

- **Cancelar no lleva `requiere_rol`**: el dueño no tiene rol de personal. El servicio decide: primero quién es y qué relación tiene con la orden (403), y recién después si el estado lo permite (409) (RN-12).
- **Terminar**: el usuario que es `mecanico_id` de la orden **y** tiene `MECANICO` vigente, o un `ADMIN` vigente (RN-11, RN-04, [09 DA-22](09_decisiones_y_supuestos.md)); 403 antes que 409.
- **Listar órdenes**: el MECANICO ve todas, con filtro opcional por `estado` ([09 DA-24](09_decisiones_y_supuestos.md)).
- **Historial de roles**: `GET /usuarios/{id}/roles` devuelve todas las asignaciones (vigentes, vencidas y revocadas) con el campo calculado `vigente` ([09 DA-25](09_decisiones_y_supuestos.md)).
- **Autoprotección**: un administrador no puede revocarse su propio rol `ADMIN`, y el sistema nunca queda sin administradores vigentes (RN-05) → 409. Se controla al revocar; el vencimiento por tiempo no ([09 DA-15, SU-11](09_decisiones_y_supuestos.md)).
- **Alta de personal**: `POST /usuarios` sólo asigna `ADMIN`, `RECEPCION` o `MECANICO`; `CLIENTE` sólo por auto-registro ([09 DA-17](09_decisiones_y_supuestos.md)).
- **Cambio obligatorio pendiente**: sólo rutas de `/auth` y de salud (RN-06) → 403 en el resto.

## Rutas públicas (grupo abierto)

Sin autenticación: `GET /health/live`, `GET /health/ready`, `POST /auth/registro`, `POST /auth/login`, `POST /auth/logout`.

Grupo abierto pero que piden autenticación (sin control de cambio obligatorio): `GET /auth/yo`, `POST /auth/cambiar-password`.
