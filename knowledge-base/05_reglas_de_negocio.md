# Reglas de Negocio

> Se usan los códigos **RN-01 a RN-20 de la consigna** (pp. 7-9), sin renumerar, para que coincidan con la corrección. Enunciado y garante esperado van textuales. En el PDF el guion de los códigos es U+2011 (guion no separable); acá se escribe `-` ASCII.

## Tabla de reglas

| Regla | Enunciado | Garante esperado |
|---|---|---|
| **RN-01** | El correo de un usuario y el documento de un cliente son únicos. La patente de un vehículo y el código de un repuesto son únicos entre los que no están dados de baja. | UNIQUE e índices únicos parciales en la base; 409 con mensaje propio |
| **RN-02** | El auto-registro crea el usuario, su rol CLIENTE y su ficha de cliente: o quedan las tres filas, o ninguna. Si el documento ya es de un cliente del taller, el registro da 409 y no se apropia de esa ficha. | Un solo Unit of Work |
| **RN-03** | Un usuario tiene a lo sumo una asignación abierta por rol. | Índice único parcial; 409 |
| **RN-04** | Los permisos se deciden con los roles vigentes en la base, en cada petición. Los roles que trae el token son informativos. | Dependencia que consulta `asignacion_rol` |
| **RN-05** | Un administrador no puede revocarse su propio rol ADMIN, y el sistema nunca queda sin administradores vigentes. | Comprobación en el servicio; 409 |
| **RN-06** | Mientras un usuario tenga el cambio de contraseña pendiente, sólo puede usar las rutas de `/auth` y las de salud. | Dos grupos de rutas; 403 |
| **RN-07** | Al cambiar la contraseña, las sesiones emitidas antes dejan de valer, aunque sean del mismo segundo que el cambio; la que devuelve el propio cambio, no. | Comparación de `iat` con `password_cambiada_en`, sin truncar; 401 |
| **RN-08** | Después de 5 intentos fallidos con el mismo correo desde la misma dirección en 60 segundos, el login responde 429 sin verificar la contraseña. Un login correcto reinicia la cuenta: los fallos anteriores siguen en la tabla, pero dejan de contar. | Conteo sobre `intento_acceso`; `Retry-After` |
| **RN-09** | El login responde lo mismo, y tarda lo mismo, exista o no el correo. | Mismo mensaje; verificación contra un hash ficticio |
| **RN-10** | Una orden nace PENDIENTE con al menos un ítem y sin repuestos repetidos. El precio de cada ítem se copia del repuesto, y el total lo calcula el servidor. | DTO; el precio y el total nunca viajan en el cuerpo |
| **RN-11** | Las transiciones de una orden son PENDIENTE → EN_REPARACION (la inicia un mecánico, que queda asignado), EN_REPARACION → TERMINADA (la termina el mecánico asignado o un administrador) y PENDIENTE → CANCELADA. | Servicio; 409 si el estado no lo permite |
| **RN-12** | Cancelan una orden la recepción, el administrador o el dueño del vehículo. El permiso se evalúa antes que el estado. | Servicio; 403 antes que 409 |
| **RN-13** | Terminar una orden descuenta el stock de cada ítem, deja un movimiento por cada salida y una línea de historial. Si un repuesto no alcanza, no queda ninguna de esas escrituras. | Un solo Unit of Work; 409 |
| **RN-14** | El stock de un repuesto sólo cambia a través de movimientos: el alta con stock inicial, la reposición y la terminación de órdenes. No se edita por PATCH. | Punto único de escritura de stock |
| **RN-15** | `historial_estado_orden`, `movimiento_stock` y `historial_precio_repuesto` son de sólo agregado: nadie puede modificar ni borrar sus filas. | Disparador en la base, instalado por migración |
| **RN-16** | Un vehículo o un repuesto dado de baja deja de aparecer y no se puede usar en órdenes nuevas, pero sus datos se conservan. Un vehículo con órdenes abiertas —en un estado que el catálogo no marca como final— no se da de baja. | Borrado lógico; `es_final`; 409 |
| **RN-17** | Lo propio sólo pide estar autenticado: un cliente ve sus vehículos y las órdenes de sus vehículos, y ninguna otra. | `/mis-*` y comprobación de dueño; 403 |
| **RN-18** | Ningún error devuelve al cliente texto interno de la base, que le entregaría el mapa del esquema (sección 4.13). Ninguna entrada inválida termina en un 500. | Traducción del `IntegrityError`; validación en el contrato |
| **RN-19** | Los estados posibles de una orden son las filas del catálogo `estado_orden`. El catálogo se consulta desde la API y no se edita desde ella. Si está vacío, crear una orden responde 409 con un mensaje propio. | Clave foránea; repositorio de sólo lectura |
| **RN-20** | Cada cambio del precio de un repuesto deja una línea en `historial_precio_repuesto`, en la misma transacción que el cambio. Un PATCH que no cambia el precio no deja línea. | Un solo Unit of Work; `CHECK precio_nuevo <> precio_anterior` |

## Agrupación por dominio (índice, sin renumerar)

| Dominio | Reglas |
|---|---|
| Unicidad e integridad | RN-01, RN-15, RN-18, RN-19 |
| Autenticación | RN-02, RN-07, RN-08, RN-09 |
| Autorización y roles | RN-03, RN-04, RN-05, RN-06, RN-12, RN-17 |
| Órdenes de trabajo | RN-10, RN-11, RN-12, RN-13, RN-16, RN-19 |
| Stock y repuestos | RN-13, RN-14, RN-16, RN-20 |
| Operaciones de una sola transacción (un solo bloque UoW) | RN-02, RN-13, RN-20 |

## Máquina de estados de la orden (RN-11, RN-12, RN-19)

```
            iniciar (MECANICO; queda asignado)          terminar (mecánico asignado o ADMIN)
 PENDIENTE ─────────────────────────────────► EN_REPARACION ─────────────────────────────► TERMINADA (final)
     │
     │ cancelar (RECEPCION, ADMIN o dueño del vehículo)
     ▼
 CANCELADA (final)
```

- Cualquier otra transición → **409**.
- Cancelar y terminar: **403 antes que 409** (permiso antes que estado).
- Cada transición agrega una línea a `historial_estado_orden` (la creación agrega `desde_estado = null`, `hasta_estado = PENDIENTE`).
- «Orden abierta» = estado con `es_final = false` en el catálogo (RN-16).

## Reglas operativas complementarias (de los ejercicios)

| Origen | Regla |
|---|---|
| Ej. 3 | Los contratos de entrada rechazan campos no declarados (`extra="forbid"`): nadie se registra con un rol ni edita el stock por PATCH. |
| Ej. 3 | Paginación: `page` ≥ 1; `size` 1..100 (default 20); página inexistente → 422; con cero resultados hay una página vacía. |
| Ej. 3 | La búsqueda de repuestos por descripción usa parámetros ligados. |
| Ej. 4 | Todo campo que termina en bcrypt (contraseña de registro, alta, login, actual y nueva del cambio) acepta como máximo **72 bytes** (no caracteres: «ñ» ocupa dos) → 422, nunca 500. |
| Ej. 4 | Orden del login: primero el límite (RN-08, una consulta, 429 + `Retry-After` sin calcular hash); después la verificación contra el hash real o el ficticio (RN-09). |
| Ej. 5 | Vencimiento de un rol: con zona horaria y en el futuro. Sin zona o en el pasado → **422**, no 409. |
| Ej. 5 | Reasignar un rol vencido cierra la fila anterior y abre una nueva. |
| Ej. 5 | El historial de seguridad registra las altas, los cambios de rol y de contraseña, y los datos iniciales (actor `SISTEMA`). |
| Ej. 7 | Cada intento de login, correcto o fallido, se anota en `intento_acceso` con sesión y transacción propias que siempre se confirman. |
| Ej. 8 | Al terminar una orden se agenda el aviso al cliente con `BackgroundTasks`, que corre después de enviar la respuesta y **sólo si la operación se confirmó**. |

## Excepciones globales (requisitos no funcionales, consigna pp. 19-20)

| Requisito | Detalle |
|---|---|
| Asincronía | Todos los handlers con `async def`; bcrypt siempre fuera del bucle |
| Credenciales | Ninguna contraseña ni clave de firma en el código —tampoco como valor por defecto—, en `alembic.ini` ni en el repositorio |
| Token | Sólo en la cookie `HttpOnly`; nunca en el cuerpo ni leído de la cabecera `Authorization` |
| Esquema | Sólo con Alembic; la aplicación no usa `create_all` |
| Transacciones | Ningún repositorio confirma; ningún servicio construye su Unit of Work; el Unit of Work no cierra la sesión |
| Carga perezosa | Prohibida: toda relación que se lee se precarga en el repositorio |
| SQL | Nunca armado por concatenación con datos del usuario |
| Errores | Mensajes propios; nunca el texto de la base ni una traza; ninguna entrada inválida termina en un 500 |
| Unicidad | Garantizada por la base; no se verifica con una consulta previa |
| Diagnóstico | Las consultas se pueden ver en la consola (`SQL_ECHO=true` o equivalente) |

## Aclaraciones del profesor en clase (no están en el PDF)

Registradas como decisiones en [09_decisiones_y_supuestos.md](09_decisiones_y_supuestos.md) (DD-A1 a DD-A4):
- Las tablas appendOnly no tienen CRUD propio: las escribe el servicio dentro de la misma transacción de la operación; el disparador impide UPDATE/DELETE.
- `estado_orden` es un catálogo de solo lectura (como un enum en la base): sin endpoints de escritura, cargado por `seed.py`.
- El token viaja SOLO por cookie `HttpOnly`.
- La clave de firma del JWT se genera una sola vez con `python -c "import secrets; print(secrets.token_urlsafe(64))"`, se guarda en `.env` y queda fija.
