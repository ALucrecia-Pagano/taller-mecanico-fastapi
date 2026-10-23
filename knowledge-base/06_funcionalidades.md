# Funcionalidades

Organizadas por **épica** (una por ejercicio de la consigna, con su puntaje) y por **historia de usuario** (US-NNN). Los criterios de aceptación salen de la consigna; los casos de prueba relacionados están en [11_casos_de_prueba.md](11_casos_de_prueba.md).

---

## Épica 1 · Proyecto, configuración y ciclo de vida (Ejercicio 1 — 8 puntos)

### US-001 — Configuración desde el entorno
**Como** desarrollador **quiero** leer la configuración con `Settings` (pydantic-settings) desde el entorno o `.env` **para** no tener secretos en el código.

**Criterios de aceptación**:
- [ ] La URL de la base se arma con un `@computed_field` a partir de `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`, con driver `postgresql+asyncpg`.
- [ ] La clave de firma del token y la contraseña de la base **no tienen valor por defecto**: si faltan, la aplicación no arranca.
- [ ] El tamaño del pool y el costo de bcrypt se declaran en la configuración.
- [ ] Existe `env.example` con todas las variables y ningún secreto; `.env` no se versiona.

### US-002 — Ciclo de vida con lifespan
**Como** desarrollador **quiero** crear el motor y la fábrica de sesiones en el lifespan **para** que no se construyan al importar un módulo (EA-08).

**Criterios de aceptación**:
- [ ] Motor asincrónico (con pool configurado) y fábrica de sesiones creados en el lifespan y guardados en `app.state`.
- [ ] `get_session` toma la fábrica de `app.state`, entrega una sesión por petición con `expire_on_commit=False` y la cierra al terminar.
- [ ] El lifespan calcula **una vez** el hash ficticio del login.
- [ ] Al apagar, se cierra el motor con `dispose()`.

### US-003 — Salud
**Como** operador **quiero** sondas de vida y de disponibilidad **para** distinguir un proceso vivo de uno listo.

**Criterios de aceptación**:
- [ ] `GET /health/live` → 200, sin tocar la base.
- [ ] `GET /health/ready` ejecuta `SELECT 1` → 200; si la base no contesta → 503.

---

## Épica 2 · Modelos, relaciones y migraciones (Ejercicio 2 — 14 puntos)

### US-010 — Modelos con todas sus restricciones
**Como** desarrollador **quiero** modelos SQLModel con los nombres obligatorios **para** que la base garantice la integridad.

**Criterios de aceptación**:
- [ ] Todas las tablas, columnas y restricciones de [04_modelo_de_datos.md](04_modelo_de_datos.md).
- [ ] Tres índices únicos parciales con `postgresql_where`: `asignacion_rol` (`usuario_id`, `rol`), `vehiculo` (`patente`), `repuesto` (`codigo`).
- [ ] `orden_trabajo.estado`, `historial_estado_orden.desde_estado` y `hasta_estado` son FK a `estado_orden.codigo`, no un CHECK (RN-19).
- [ ] Navegación en los dos extremos de cada relación que se lea; `Usuario.cliente` devuelve un objeto.
- [ ] Índice en cada FK.

### US-011 — Migraciones con Alembic (plantilla async)
**Criterios de aceptación**:
- [ ] Primera migración con `--autogenerate`, con todas las tablas.
- [ ] Segunda migración **a mano**, con el disparador de sólo agregado sobre las tres tablas (RN-15).
- [ ] Cada migración lleva un comentario que indica que se leyó antes de aplicarla.
- [ ] `upgrade head` → `downgrade base` → `upgrade head` funciona sobre una base vacía.
- [ ] Las migraciones crean el catálogo vacío; no se usa `create_all`.

### US-012 — Seed
**Criterios de aceptación**:
- [ ] `python seed.py` vacía las tablas y carga los datos de [04](04_modelo_de_datos.md#seed-data-inicial-seedpy), con el catálogo primero.

---

## Épica 3 · Contratos y CRUD (Ejercicio 3 — 10 puntos)

### US-020 — Contratos separados y estrictos
**Criterios de aceptación**:
- [ ] Schemas de entrada y salida separados de los modelos de tabla; entrada con `extra="forbid"`.
- [ ] Ninguna respuesta incluye `password_hash`.
- [ ] `PATCH` con `exclude_unset`.
- [ ] Códigos 201 / 204 / 404 / 409 / 422 según [02](02_descripcion_general.md#convenciones-transversales-de-la-api-ejercicio-3).

### US-021 — Listados paginados
**Criterios de aceptación**:
- [ ] Envoltorio `{items, total, page, size, pages}`; `page` desde 1; `size` 1..100, default 20.
- [ ] Página más allá de la última → 422 con mensaje («La página 3 no existe: hay 2»).
- [ ] `total` con los mismos filtros; cero resultados → una página vacía.

### US-022 — Clientes y vehículos (RECEPCION, ADMIN)
**Criterios de aceptación**:
- [ ] `POST /clientes` (201, 409 por `documento` repetido, 422).
- [ ] `GET /clientes/{id}` con sus vehículos vigentes; los dados de baja no aparecen (200, 404) ([09 DA-23](09_decisiones_y_supuestos.md)).
- [ ] `POST /clientes/{id}/vehiculos` (201, 404, 409 por patente vigente repetida, 422).
- [ ] `DELETE /vehiculos/{id}`: borrado lógico (204); 409 si tiene órdenes abiertas (RN-16); 404.
- [ ] Una patente dada de baja se puede volver a registrar (C-19).

### US-023 — Repuestos (ADMIN escribe; personal lee)
**Criterios de aceptación**:
- [ ] `GET /repuestos?q=&page=&size=` busca por descripción con parámetros ligados; excluye los dados de baja.
- [ ] `GET /repuestos/{id}`.
- [ ] `POST /repuestos` con `stock_inicial`, que genera un movimiento «Stock inicial» (RN-14); 409 por código vigente repetido.
- [ ] `PATCH /repuestos/{id}` sólo descripción y precio; intentar `stock` → 422 (RN-14, C-16).
- [ ] `DELETE /repuestos/{id}`: borrado lógico (204), permitido aunque esté en órdenes abiertas; esas órdenes se terminan normal ([09 DA-21](09_decisiones_y_supuestos.md)).

### US-024 — Catálogo de estados
**Criterios de aceptación**:
- [ ] `GET /estados-orden` (autenticado) devuelve las cuatro filas ordenadas por `posicion`, con `es_final`.
- [ ] Sin endpoints de escritura.

---

## Épica 4 · Autenticación (Ejercicio 4 — 16 puntos)

### US-030 — Auto-registro (RN-02)
**Como** cliente **quiero** registrarme solo **para** consultar mis vehículos.

**Criterios de aceptación**:
- [ ] Crea usuario + asignación `CLIENTE` + ficha de cliente en **un solo bloque UoW**: o las tres filas o ninguna.
- [ ] Correo o documento repetido → 409 con mensaje propio, sin filas sueltas; no se apropia de una ficha existente.
- [ ] El hash se calcula **antes** de abrir la transacción.
- [ ] Registra el alta en `evento_seguridad`.
- [ ] Cuerpo `{email, nombre, password, documento, telefono}` ([09 DA-16](09_decisiones_y_supuestos.md)).

### US-031 — Login (RN-08, RN-09)
**Criterios de aceptación**:
- [ ] Primero el límite: 5 fallos del mismo correo + IP en 60 s → 429 con `Retry-After`, sin calcular hash.
- [ ] Después la verificación contra el hash real, o contra el **hash ficticio** si el correo no existe: mismo cuerpo y tiempo parecido (401).
- [ ] Cada intento se anota en `intento_acceso` con sesión y transacción propias, siempre confirmadas.
- [ ] Éxito: cookie `access_token` con `HttpOnly`, `SameSite=Lax`, `Max-Age` = duración del token y `Secure` configurable; el cuerpo **no** trae el token: `{ "mensaje": "Sesión iniciada", "debe_cambiar_password": false, "expira_en_segundos": 1800 }`.
- [ ] JWT con `sub`, `iat` (con fracción de segundo), `exp` y los roles vigentes al emitirlo.

### US-032 — bcrypt sin bloquear
**Criterios de aceptación**:
- [ ] Toda llamada a bcrypt corre con `asyncio.to_thread` y bajo un semáforo.
- [ ] El costo sale de la configuración.
- [ ] Todo campo de contraseña acepta como máximo 72 bytes → 422.

### US-033 — Logout y `/auth/yo`
**Criterios de aceptación**:
- [ ] `POST /auth/logout` borra la cookie (200).
- [ ] `GET /auth/yo` devuelve el usuario, sus roles vigentes (de la base) y los que dice el token.

### US-034 — Cambio de contraseña (RN-07)
**Criterios de aceptación**:
- [ ] `POST /auth/cambiar-password` verifica la actual, anota `password_cambiada_en` y emite una cookie nueva **después** de anotar el cambio.
- [ ] Los tokens con `iat` anterior a `password_cambiada_en` (sin truncar) → 401, aunque sean del mismo segundo.
- [ ] Limpia `debe_cambiar_password`. Registra el evento de seguridad.

---

## Épica 5 · Autorización (Ejercicio 5 — 14 puntos)

### US-040 — Usuario actual y roles vigentes
**Criterios de aceptación**:
- [ ] `get_usuario_actual` → 401 si: no hay cookie, el token es inválido o venció, el usuario no existe o está inactivo, o el token es anterior al último cambio de contraseña.
- [ ] El token se lee **sólo** de `request.cookies` (con `Authorization: Bearer` → 401).
- [ ] `requiere_rol` → 403; consulta los roles vigentes en la base **en cada petición** (RN-04).

### US-041 — Alta de personal (ADMIN)
**Criterios de aceptación**:
- [ ] `POST /usuarios` crea personal con contraseña provisoria (201, 409, 422).
- [ ] Cuerpo `{email, nombre, password_provisoria, rol}`; `rol` sólo `ADMIN`, `RECEPCION` o `MECANICO` (otro → 422).
- [ ] Usuario + asignación + evento en un solo Unit of Work; deja `debe_cambiar_password = true` ([09 DA-17](09_decisiones_y_supuestos.md)).

### US-042 — Gestión de roles con vigencia (ADMIN)
**Criterios de aceptación**:
- [ ] `GET /usuarios/{id}/roles` devuelve todo el historial con el campo calculado `vigente` ([09 DA-25](09_decisiones_y_supuestos.md)).
- [ ] `POST /usuarios/{id}/roles` con vencimiento opcional; con zona y en el futuro, si no → 422; asignación abierta duplicada → 409 (RN-03); reasignar uno vencido cierra la fila anterior y abre otra.
- [ ] `DELETE /usuarios/{id}/roles/{rol}` escribe `revocada_en` sin borrar la fila; autoprotección → 409 (RN-05).
- [ ] Cada cambio de rol queda en `evento_seguridad`.

### US-043 — Cambio obligatorio de contraseña (RN-06)
**Criterios de aceptación**:
- [ ] Dos grupos de rutas en `main.py`: abierto y protegido; el protegido monta **una sola vez** el control → 403 mientras esté pendiente.

### US-044 — Eventos de seguridad (ADMIN)
**Criterios de aceptación**:
- [ ] `GET /eventos?page=&size=` paginado.

### US-045 — Lo propio (RN-17)
**Criterios de aceptación**:
- [ ] `GET /mis-vehiculos` y `GET /mis-ordenes` sólo piden estar autenticado y devuelven sólo lo del usuario; sin ficha de cliente → 200 con lista vacía ([09 DA-14](09_decisiones_y_supuestos.md)).
- [ ] `GET /ordenes/{id}` de un vehículo ajeno → 403 para el cliente.

---

## Épica 6 · Repositorios y Unit of Work (Ejercicio 6 — 20 puntos)

### US-050 — Jerarquía de repositorios
**Criterios de aceptación**:
- [ ] `BaseRepository[T]` recibe sesión y clase del modelo; ofrece al menos `get_by_id`, `get_all`, `count`, `add`, `update`, `delete`.
- [ ] `SoftDeleteRepository[T]` hereda, filtra los dados de baja y agrega `get_by_id_including_deleted` y `soft_delete`.
- [ ] `add`/`update` hacen `flush()`, nunca `commit()`.
- [ ] Repositorio por entidad con métodos nombrados por lo que traen; precarga declarada dentro del método.
- [ ] Repositorio del catálogo de sólo lectura que **no hereda** de `BaseRepository`.

### US-051 — Unit of Work
**Criterios de aceptación**:
- [ ] `UnitOfWork` base: gestor de contexto async; confirma al salir, revierte con excepción, no cierra la sesión.
- [ ] Un UoW por módulo, con sus repositorios sobre la misma sesión.
- [ ] El router lo construye con una dependencia; el servicio lo abre con `async with` y nunca lo construye.
- [ ] RN-02, RN-13 y RN-20, cada una en un solo bloque.

### US-052 — Órdenes de trabajo
**Criterios de aceptación**:
- [ ] `POST /ordenes` (RN-10): nace PENDIENTE, ≥ 1 ítem, sin repuestos repetidos, precio copiado, total calculado, primera línea de historial; repuesto inexistente → 409 sin crear la orden; catálogo vacío → 409 (RN-19).
- [ ] Repuestos repetidos en el alta → 422 en el contrato ([09 DA-19](09_decisiones_y_supuestos.md)).
- [ ] `GET /ordenes?estado=&page=&size=` (estado no declarado en el enum → 422); el MECANICO ve todas ([09 DA-24](09_decisiones_y_supuestos.md)).
- [ ] Terminar: `mecanico_id` con MECANICO vigente, o ADMIN vigente; si no → 403 ([09 DA-22](09_decisiones_y_supuestos.md)).
- [ ] `GET /ordenes/{id}` con vehículo, cliente, ítems, repuesto de cada ítem e historial.
- [ ] `POST /ordenes/{id}/iniciar` (MECANICO, queda asignado).
- [ ] `POST /ordenes/{id}/terminar` (RN-13): descuenta stock, un movimiento por salida, línea de historial; si no alcanza → 409 sin escrituras.
- [ ] `POST /ordenes/{id}/cancelar` (RN-12): sin `requiere_rol`; 403 antes que 409.

### US-053 — Stock e historial de precios
**Criterios de aceptación**:
- [ ] Punto único de escritura de stock (RN-14), usado por alta, reposición y terminación.
- [ ] `POST /repuestos/{id}/reponer` (200, 404, 422).
- [ ] `GET /repuestos/{id}/movimientos` y `GET /repuestos/{id}/precios`.
- [ ] Un PATCH que cambia el precio agrega una línea de historial en la misma transacción; si no cambia, ninguna (RN-20).

---

## Épica 7 · Integridad (Ejercicio 7 — 10 puntos)

### US-060 — Disparador de sólo agregado
**Criterios de aceptación**:
- [ ] Rechaza cualquier `UPDATE` o `DELETE` sobre las tres tablas, venga de donde venga (demostrado en `test/solo_agregado.sql`, C-14).

### US-061 — Intento de acceso en su propia transacción
**Criterios de aceptación**:
- [ ] Única escritura que no comparte la transacción de la petición; el código lo declara en un comentario junto con su costo (deja filas aunque la petición falle).

---

## Épica 8 · Lecturas sin N+1 y asincronía (Ejercicio 8 — 8 puntos)

### US-070 — Detalle de orden con consultas fijas
**Criterios de aceptación**:
- [ ] El detalle se resuelve con un número fijo de consultas, que no crece con la cantidad de ítems (C-15).
- [ ] Ninguna lectura depende de la carga perezosa.

### US-071 — Aviso en segundo plano
**Criterios de aceptación**:
- [ ] Al terminar una orden, `BackgroundTasks` agenda `await asyncio.sleep(0.5)` + mensaje en el registro, después de la respuesta y sólo si se confirmó.
- [ ] Todos los handlers `async def`; ninguna llamada bloqueante.
