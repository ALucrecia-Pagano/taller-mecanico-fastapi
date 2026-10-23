# Decisiones y Supuestos

Tres orígenes, siempre identificados:
- **[Consigna]**: decisión de diseño explicada en el PDF.
- **[Profe]**: aclaración del profesor en clase, transmitida por la alumna (no está en el PDF).
- **[Alumna]**: aclaración o elección de la alumna.

## Decisiones documentadas

### DD-01 — Roles en tabla propia con vigencia [Consigna]
**Decisión**: `usuario` no tiene columna `rol`; los roles son filas vigentes de `asignacion_rol` (no revocadas, sin vencer). Revocar escribe `revocada_en`; la fila nunca se borra.
**Justificación**: queda el historial de quién tuvo qué rol y hasta cuándo (5.9); la autorización se decide en la base, no en el token.
**Trade-offs**: una consulta de roles por petición.

### DD-02 — Catálogo `estado_orden` en lugar de CHECK [Consigna]
**Decisión**: los estados son filas de un catálogo con PK `codigo`, referenciado por FK. La migración lo crea vacío; `seed.py` lo carga. En el código, un enum espejo es el contrato de la API.
**Justificación**: cada estado lleva datos propios (`es_final`, `posicion`) que la API muestra y las consultas cruzan; la PK textual se lee igual en psql y en la API.
**Trade-offs**: agregar un estado obliga a tocar el enum, el catálogo y el servicio.

### DD-03 — Unicidad parcial con borrado lógico [Consigna]
**Decisión**: índices únicos parciales `WHERE borrado_en IS NULL` para `patente` y `codigo`.
**Justificación**: con un UNIQUE común, el comprador de un auto vendido no podría registrarlo.

### DD-04 — Unicidad garantizada por la base, sin consulta previa [Consigna]
**Decisión**: se intenta escribir y se traduce el `IntegrityError` a 409 con mensaje propio.

### DD-05 — Intento de acceso en sesión propia [Consigna]
**Decisión**: única escritura que no comparte la transacción de la petición.
**Justificación**: el fallo que se quiere contar es el mismo que revierte la transacción del login.
**Trade-offs (declarados en un comentario en el código)**: deja filas aunque la petición falle.

### DD-06 — Hash antes de la transacción, fuera del bucle y con semáforo [Consigna]
**Justificación**: bcrypt tarda ~300 ms; dentro de la transacción retendría la conexión; en el bucle bloquearía el servidor.

### DD-07 — Dos grupos de rutas [Consigna]
**Decisión**: grupo abierto y grupo protegido en `main.py`; el protegido monta una vez el control de cambio obligatorio.
**Justificación**: FastAPI suma dependencias y no las resta (5.10).

### DD-08 — `iat` sin truncar [Consigna]
**Decisión**: el token se emite con la hora completa (fracciones de segundo) y se compara sin truncar con `password_cambiada_en`; el token nuevo se emite después de anotar el cambio.

### DD-09 — Cancelar sin `requiere_rol` [Consigna]
**Decisión**: el servicio evalúa primero la relación con la orden (403) y después el estado (409).

### DD-10 — Segunda migración escrita a mano [Consigna]
**Justificación**: `--autogenerate` no ve funciones ni disparadores.

### DD-11 — Driver asyncpg [Alumna]
**Decisión**: `postgresql+asyncpg` (la consigna acepta también psycopg 3 asincrónico).

### DD-12 — Python 3.13 y PostgreSQL 17 [Alumna]
**Decisión**: versiones del entorno de la alumna; cumplen los mínimos (3.12 y 16).

### DD-13 — Signo de `movimiento_stock.cantidad` [Alumna]
**Decisión**: entradas (stock inicial, reposición) positivas; salidas por terminar una orden **negativas**.
**Justificación**: consistente con `CHECK cantidad <> 0`; el stock resulta de sumar los movimientos.

### DD-14 — Códigos RN y C sin renumerar [Alumna]
**Decisión**: la KB usa RN-01…RN-20 y C-01…C-19 de la consigna, no el formato `RN-DOM-NN` de la plantilla de KB.

### DD-A1 — Tablas appendOnly sin CRUD propio [Profe]
**Decisión**: `historial_estado_orden`, `movimiento_stock` e `historial_precio_repuesto` no tienen endpoints de escritura ni CRUD propio: las escribe el servicio dentro de la misma transacción de la operación que las origina; un disparador impide UPDATE/DELETE.
**Consistencia con el PDF**: coincide con RN-13, RN-14, RN-15, RN-20 y el Ejercicio 7. Sólo hay endpoints de lectura (`/repuestos/{id}/movimientos`, `/repuestos/{id}/precios`, historial dentro del detalle de orden).

### DD-A2 — `estado_orden` de sólo lectura, cargado por `seed.py` [Profe]
**Decisión**: catálogo de sólo lectura (como un enum en la base), sin endpoints de escritura.
**Consistencia con el PDF**: coincide con RN-19 y el Ejercicio 6.

### DD-A3 — Token sólo por cookie `HttpOnly` [Profe]
**Consistencia con el PDF**: coincide con el Ejercicio 4 y el requisito no funcional «Token».

### DD-A4 — Clave de firma fija generada una vez [Profe]
**Decisión**: `python -c "import secrets; print(secrets.token_urlsafe(64))"`, guardada en `.env`, fija. Nunca generada al arrancar, nunca en el código ni en el repo.
**Consistencia con el PDF**: coincide con «Requisitos técnicos» (p. 3-4: una clave inventada al arrancar cambia en cada reinicio y dos procesos se rechazan los tokens) y con «Formato de entrega» (README con cómo generar la clave).

## Decisiones de la alumna sobre las preguntas abiertas (DA)

Respuestas a [10_preguntas_abiertas.md](10_preguntas_abiertas.md). Todas son **[Alumna]**: completan lo que la consigna no especifica, sin contradecirla.

### DA-00 — Resolución de inconsistencias [Alumna]
**Decisión**: se aceptan las resoluciones propuestas de IN-01 (la tabla del modelo manda sobre la Figura 1), IN-02 (toda ruta con `requiere_rol` responde también 403) e IN-03 (códigos `RN-NN` con guion ASCII).

### DA-01 — Contraseña del seed [Alumna] (PA-01)
**Decisión**: una contraseña común y ficticia para todos los usuarios del seed: `Taller2026!`.
**Restricción**: vive **sólo** en `seed.py` (consigna: «las contraseñas son de mentira y viven sólo en ese archivo»).

### DA-02 — Usuarios del seed y sus ids [Alumna] (PA-02)
**Decisión**: alta en este orden, para que los ids coincidan con el ejemplo del PDF (recepción = `usuario_id 3`): 1 `admin@` «Ana Admin», 2 `admin2@` «Bruno Admin», 3 `recepcion@` «Rita Recepción», 4 `mecanico@` «Mario Mecánico», 5 `mecanico2@` «Martín Mecánico», 6 `cliente@` «Laura Cliente», 7 `nuevo@` «Nico Nuevo».

### DA-03 — Clientes del seed [Alumna] (PA-03)
**Decisión**: Laura → nombre «Laura Cliente», documento `30111222`, teléfono `2614000001`, usuario `cliente@`. Jorge → nombre «Jorge Pérez», documento `28333444`, teléfono `2614000002`, sin usuario.

### DA-04 — Vehículos del seed [Alumna] (PA-04)
**Decisión**: id 1 (Laura) `AB123CD` Toyota Corolla 2018; id 2 (Laura) `AC456EF` Ford Fiesta 2015; id 3 (Jorge) `AD789GH` Volkswagen Gol 2012.

### DA-05 — Repuestos del seed [Alumna] (PA-05)
**Decisión** (ids y datos alineados con los ejemplos del PDF): 1 `FIL-001` «Filtro de aceite» 8500 stock 10; 2 `FRE-010` «Pastillas de freno delanteras» 32000 stock 4; 3 `BUJ-020` «Bujía de encendido» 6000 stock 2; 4 `ACE-530` «Aceite 5W30 por litro» 12000 stock 20. Historial de precio: sólo el filtro, 8000 → 8500.

### DA-06 — Órdenes, historiales y autoría del seed [Alumna] (PA-06)
**Decisión**:
- Orden 1: vehículo 1, PENDIENTE, falla «Cambio de aceite y filtro», ítems 1 × filtro (8500) + 4 × aceite (12000) → total 56500.
- Orden 2: vehículo 3, EN_REPARACION, `mecanico_id` = `mecanico@` (4), falla «Falla de encendido», ítems 4 × bujía (6000) → total 24000.
- Historial: orden 1 `null → PENDIENTE` por recepción (3); orden 2 `null → PENDIENTE` por recepción (3) y `PENDIENTE → EN_REPARACION` por `mecanico@` (4).
- Movimientos «Stock inicial» e historial de precio del seed: `usuario_id` = `admin@` (1).
- `SISTEMA` queda sólo como actor de `evento_seguridad`.
- Todos los usuarios del seed con `activo = true` (supuesto confirmado por la alumna).

### DA-07 — Variables de configuración [Alumna] (PA-07)
**Decisión**: secretos sin valor por defecto; el resto con default.

| Variable | Default |
|---|---|
| `POSTGRES_USER` | `postgres` |
| `POSTGRES_DB` | `taller_mecanico` |
| `POSTGRES_HOST` | `localhost` |
| `POSTGRES_PORT` | `5432` |
| `POSTGRES_PASSWORD` | **sin default** |
| `JWT_SECRET_KEY` | **sin default** |
| `JWT_ALGORITHM` | `HS256` |
| `JWT_EXPIRE_SECONDS` | `1800` |
| `BCRYPT_COST` | `12` |
| `BCRYPT_MAX_CONCURRENCY` | `4` |
| `DB_POOL_SIZE` | `5` |
| `DB_MAX_OVERFLOW` | `10` |
| `COOKIE_SECURE` | `false` |
| `SQL_ECHO` | `false` |
| `LOGIN_MAX_FALLOS` | `5` |
| `LOGIN_VENTANA_SEGUNDOS` | `60` |

**Nota**: los defaults de `LOGIN_*` coinciden con RN-08 (5 fallos en 60 s) y no se cambian para la entrega.

### DA-08 — `asignacion_rol.otorgada_por` [Alumna] (PA-08)
**Decisión**: FK nullable a `usuario.id` (el ADMIN que asigna). `NULL` cuando lo asigna el auto-registro o el seed.

### DA-09 — Valores de `movimiento_stock.motivo` [Alumna] (PA-09)
**Decisión**: `"Stock inicial"`, `"Reposición"`, `"Orden terminada"` (este último con `orden_id` cargado).

### DA-10 — Contrato de `POST /repuestos/{id}/reponer` [Alumna] (PA-10)
**Decisión**: cuerpo `{"cantidad": int}` con `cantidad > 0` (si no, 422); responde 200 con el repuesto actualizado.

### DA-11 — Límite de login: `Retry-After` y registro del 429 [Alumna] (PA-11)
**Decisión**:
- `Retry-After` = los segundos que faltan para salir de la ventana.
- El intento rechazado con 429 **no** se anota en `intento_acceso`.
**Justificación**: no se verificó ninguna contraseña, y C-05 espera exactamente los cinco fallos en la tabla.

### DA-12 — Origen de `intento_acceso.ip` [Alumna] (PA-12)
**Decisión**: `request.client.host`. No se usa `X-Forwarded-For`.
**Justificación**: sin un proxy de confianza, cualquiera falsifica esa cabecera y se saltea el límite de intentos.

### DA-13 — `evento_seguridad.actor` y `accion` [Alumna] (PA-13)
**Decisión**: `actor` = email del usuario que hace la acción (`"SISTEMA"` sólo en el seed). `accion` = texto legible:

| Evento | `accion` |
|---|---|
| Seed | `Carga de los datos iniciales` |
| Auto-registro | `Registro de cliente <email>` |
| Alta de personal | `Alta de personal <email>` |
| Asignación de rol | `Asignación de rol <ROL> a <email>` |
| Revocación de rol | `Revocación de rol <ROL> a <email>` |
| Cambio de contraseña | `Cambio de contraseña` |

### DA-14 — `/mis-*` sin ficha de cliente [Alumna] (PA-14)
**Decisión**: 200 con lista vacía. En `/mis-ordenes`, con el envoltorio paginado vacío (`items: []`, `total: 0`, una página).

### DA-15 — Alcance de RN-05 [Alumna] (PA-15)
**Decisión**:
- Nadie se revoca su propio ADMIN → 409.
- Una revocación de ADMIN que deja **cero administradores vigentes** → 409 (aunque la haga otro admin).
- El vencimiento por tiempo (`vence_en`) **no** se controla: ver SU-11.

### DA-16 — Contratos no ejemplificados en la consigna [Alumna] (PA-16)
**Decisión** (todas las entradas con `extra="forbid"`; toda contraseña con máximo 72 bytes):

| Endpoint | Cuerpo / respuesta |
|---|---|
| `POST /auth/registro` | `{email, nombre, password, documento, telefono}` |
| `POST /auth/cambiar-password` | `{password_actual, password_nueva}` |
| `POST /usuarios` | `{email, nombre, password_provisoria, rol}` |
| `POST /clientes` | `{nombre, documento, telefono}` |
| `POST /clientes/{id}/vehiculos` | `{patente, marca, modelo, anio}` |
| `POST /usuarios/{id}/roles` | `{rol, vence_en}` (`vence_en` opcional; si viene, con zona y en el futuro) |
| `GET /auth/yo` (respuesta) | `{id, email, nombre, debe_cambiar_password, roles_vigentes, roles_token}` |

### DA-17 — Alta de personal [Alumna] (PA-17)
**Decisión**: `POST /usuarios` recibe el rol inicial, que sólo puede ser `ADMIN`, `RECEPCION` o `MECANICO` (`CLIENTE` sólo por auto-registro; otro valor → 422 por contrato). Crea usuario + asignación (`otorgada_por` = el ADMIN que la hace) + evento de seguridad en **un solo Unit of Work**, y deja `debe_cambiar_password = true`.

### DA-18 — Reasignar un rol vencido [Alumna] (PA-18)
**Decisión**: escribe `revocada_en` en la fila vieja (la saca del índice único parcial) y abre una nueva. Confirma SU-03.

### DA-19 — Repuestos repetidos en `POST /ordenes` [Alumna] (PA-19)
**Decisión**: **422**, validado en el contrato (RN-10: el garante es el DTO).

### DA-20 — Nulabilidad [Alumna] (PA-20)
**Decisión**: toda columna sin «(nulo)» en la tabla de la consigna es `NOT NULL`. Confirma SU-01.

### DA-21 — Baja de repuesto con órdenes abiertas [Alumna] (PA-21)
**Decisión**: se permite (`DELETE /repuestos/{id}` no tiene 409). El repuesto dado de baja no se usa en órdenes nuevas (→ 409 al crear), pero las órdenes existentes se terminan normal y descuentan su stock.
**Implicancia**: al terminar, el servicio lee el repuesto con `get_by_id_including_deleted` (el repositorio con borrado lógico lo filtra por defecto); el detalle de la orden también lo muestra.

### DA-22 — Quién termina una orden [Alumna] (PA-22)
**Decisión**: el usuario que es `mecanico_id` de la orden **y** tiene `MECANICO` vigente, o un usuario con `ADMIN` vigente (RN-04: roles en la base, en cada petición). Si no → 403.

### DA-23 — Vehículos dados de baja en listados [Alumna] (PA-23)
**Decisión**: no aparecen en `GET /clientes/{id}` ni en `/mis-vehiculos` (RN-16: «deja de aparecer»).

### DA-24 — Listado de órdenes del MECANICO [Alumna] (PA-24)
**Decisión**: el MECANICO ve todas las órdenes, con filtro opcional por `estado`.

### DA-25 — Historial de roles [Alumna] (PA-25)
**Decisión**: `GET /usuarios/{id}/roles` devuelve **todas** las asignaciones (vigentes, vencidas y revocadas) con un campo calculado `vigente` (no revocada y sin vencer), para que C-07 muestre que la fila revocada sigue.

### DA-26 — Ubicación de la suite pytest [Alumna] (OB-01 de CHANGES.md)
**Decisión**: la suite pytest vive en `test/pytest/` (no `tests/` en la raíz, para no tener `test/` y `tests/` juntos). Las dependencias de prueba (`pytest`, `pytest-asyncio`, `httpx` y las que haga falta para el lifespan) van en `requirements-dev.txt`; `requirements.txt` queda con las de la aplicación.
**Consistencia con el PDF**: `test/` sigue conteniendo los `.http` y `solo_agregado.sql` en su raíz.

### DA-27 — `stock_inicial` en `POST /repuestos` [Alumna] (OB-07)
**Decisión**: `stock_inicial >= 0` en el contrato (negativo → 422). Con `0` se crea el repuesto **sin** movimiento (el `CHECK cantidad <> 0` no lo admitiría); con `> 0` se crea el movimiento «Stock inicial» en el **mismo Unit of Work** que el alta.

### DA-28 — Formato de `/repuestos/{id}/movimientos` y `/precios` [Alumna] (OB-08)
**Decisión**: lista simple, **sin** envoltorio paginado.
**Justificación**: la consigna sólo les da 200 y 404, y los listados paginados siempre tienen 422.

### DA-29 — Base de prueba [Alumna] (OB-11)
**Decisión**: se deriva como `<POSTGRES_DB>_test` en el `conftest`; el `conftest` se niega a correr si el nombre no termina en `_test`. No se agrega ninguna variable a `env.example`.

### DA-30 — Evidencias de C-14 y C-15 [Alumna] (OB-12)
**Decisión**: se guardan en `docs/evidencias/`.

### DA-31 — Cómo vacía las tablas `seed.py` [Alumna] (OB-04)
**Decisión**: `seed.py` vacía todas las tablas con `TRUNCATE … RESTART IDENTITY CASCADE`. Es la única vía de escape al sólo agregado y sólo se usa en la puesta en marcha.
**Justificación**: el disparador de RN-15 es de fila (`BEFORE UPDATE OR DELETE`), así que un `DELETE` lo dispara y se rechaza; `TRUNCATE` no dispara triggers de fila. `RESTART IDENTITY` reinicia las secuencias para que los ids coincidan con los ejemplos del PDF.
**Alternativas descartadas**: trigger de sentencia `BEFORE TRUNCATE` con excepción para el seed (más complejo, fuera de lo que pide la consigna); `DISABLE TRIGGER` + `DELETE` (no reinicia ids y requiere ser dueño de la tabla).
**Trade-off aceptado**: cualquiera con acceso a la base puede hacer `TRUNCATE` sobre las tablas de sólo agregado; la consigna sólo pide rechazar `UPDATE` y `DELETE` (C-14).

## Supuestos inferidos

### SU-01 — Columnas sin «(nulo)» son NOT NULL
**Origen**: la tabla del modelo marca explícitamente las nulas.
**Riesgo si es falso**: bajo; agregar NULL es compatible.
**Estado**: **confirmado** por DA-20.

### SU-02 — Columnas `*_id` y `usuario_id` son FK a su tabla
**Origen**: nombres de columna + Figura 1 (que no dibuja las FK de usuario en las tablas appendOnly).
**Riesgo si es falso**: bajo. `otorgada_por` → `usuario.id` confirmado por DA-08.

### SU-03 — Reasignar un rol vencido = escribir `revocada_en` en la fila vieja
**Origen**: «reasignar un rol vencido cierra la fila anterior y abre una nueva» + el índice único parcial `WHERE revocada_en IS NULL` (la fila vieja tiene que salir del índice para poder abrir otra).
**Estado**: **confirmado** por DA-18.

### SU-04 — Falta de rol → 403 aunque la tabla de endpoints no lo liste
**Origen**: C-06 («Sin rol, 403»), C-18 («la recepción recibe 403») y el garante de RN-06/RN-17.

### SU-05 — «El personal»
**Supuesto**: `ADMIN`, `RECEPCION` y `MECANICO` (los roles que listan `GET /ordenes`).

### SU-06 — Los ids del seed siguen el orden de la tabla de datos iniciales
**Origen**: el ejemplo de `POST /ordenes` usa `vehiculo_id 2` (de Laura) y `usuario_id 3` en el historial; los repuestos 1, 2 y 4 coinciden con el orden filtro, pastillas, bujía, aceite.
**Riesgo si es falso**: los `.http` con ids fijos fallarían.
**Estado**: **confirmado** por DA-02, DA-04, DA-05 y DA-06 (orden de alta fijado por la alumna).

### SU-07 — Vehículo inexistente o dado de baja en `POST /ordenes` → 409
**Origen**: RN-16 («no se puede usar en órdenes nuevas») + códigos del endpoint (201, 409, 422) + C-10 (repuesto inexistente → 409). No hay 404 porque el vehículo no es el recurso de la ruta.

### SU-08 — Repuesto dado de baja en `POST /ordenes` → 409
**Origen**: igual que SU-07.

### SU-09 — La ficha del dueño se identifica por `cliente.usuario_id`
**Origen**: uno a uno `Cliente`–`Usuario`. Dueño de una orden = usuario de la ficha del cliente del vehículo de la orden.

### SU-10 — Repuesto con stock insuficiente al terminar → 409 con mensaje propio
**Origen**: RN-13 + C-11. El `CHECK stock >= 0` es la red de seguridad; la comprobación en el servicio da el mensaje propio.

### SU-11 — El vencimiento de roles no se controla para RN-05
**Supuesto**: la regla «el sistema nunca queda sin administradores vigentes» se garantiza sólo al **revocar** (DA-15). Si todas las asignaciones ADMIN vencen por `vence_en`, el sistema puede quedar sin administradores.
**Origen**: decisión de la alumna (PA-15). Impedirlo exigiría una tarea programada, fuera del alcance (sin colas ni tareas, capítulo 8).
**Riesgo si es falso**: que el profe espere también una validación al asignar ADMIN con vencimiento.
**Cómo validar**: consultarlo con el profe si hace falta.
