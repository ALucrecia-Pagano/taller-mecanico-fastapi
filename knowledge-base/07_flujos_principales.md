# Flujos Principales

Componentes: **Cliente HTTP** → **Router** → **Service** → **UoW** → **Repository** → **PostgreSQL**.

---

## Flujo 1: Petición al grupo protegido (autenticación + autorización)
**Disparador**: cualquier petición a una ruta protegida.

**Pasos**:
1. La dependencia lee `access_token` de `request.cookies` (nunca de `Authorization`). Sin cookie → **401**.
2. Decodifica y verifica el JWT con la clave de `Settings`. Inválido o vencido → **401**.
3. Carga el usuario por `sub`. No existe o `activo = false` → **401**.
4. Si `password_cambiada_en` no es nulo y `iat` (con fracción de segundo) < `password_cambiada_en` → **401** (RN-07).
5. Control del grupo protegido (montado una sola vez): si `debe_cambiar_password` → **403** (RN-06).
6. `requiere_rol(...)`, si la ruta lo lleva: consulta `asignacion_rol` vigente en la base → sin rol, **403** (RN-04).
7. El handler valida parámetros y cuerpo (contrato) → **422** antes de ejecutarse (C-01).

**Casos de error**: 401 siempre antes que 403; 403 por permiso antes que 409 por estado (RN-12).

---

## Flujo 2: Auto-registro (RN-02)
**Actor**: anónimo.

1. Router valida el contrato `{email, nombre, password, documento, telefono}` (`extra="forbid"`, contraseña ≤ 72 bytes) → 422 ([09 DA-16](09_decisiones_y_supuestos.md)).
2. Service calcula el hash bcrypt **antes** de abrir la transacción (`to_thread` + semáforo).
3. `async with uow:` agrega `usuario`, `asignacion_rol(CLIENTE, otorgada_por = NULL)`, `cliente` (con `usuario_id`) y el `evento_seguridad` (`actor` = email, `accion` = «Registro de cliente <email>») → `flush()`.
4. `IntegrityError` (email o documento) → rollback → **409** con mensaje propio, sin filas sueltas.
5. Salida al bloque → commit → **201**.

---

## Flujo 3: Login (RN-08, RN-09)
**Actor**: anónimo.

```
Cliente → Router → Service ─┬─ cuenta fallos(email, ip = request.client.host, últimos 60 s, desde el último éxito)
                            │     ≥ 5 → 429 + Retry-After (sin hash; este intento NO se anota)
                            ├─ busca usuario por email
                            ├─ verifica contraseña contra password_hash  o  contra hash ficticio
                            ├─ anota intento (éxito/fallo) en intento_acceso — sesión y transacción PROPIAS, commit siempre
                            ├─ fallo → 401 (mismo cuerpo exista o no el correo)
                            └─ éxito → JWT(sub, iat, exp, roles vigentes) → Set-Cookie access_token
                                       HttpOnly; SameSite=Lax; Max-Age; [Secure]
                                       body: {mensaje, debe_cambiar_password, expira_en_segundos}
```

- Un login correcto reinicia la cuenta: los fallos anteriores quedan en la tabla pero dejan de contar.
- `Retry-After` = segundos que faltan para salir de la ventana; el intento rechazado con 429 **no** se anota en `intento_acceso`: C-05 espera exactamente los cinco fallos ([09 DA-11](09_decisiones_y_supuestos.md)).
- `ip` = `request.client.host`; no se usa `X-Forwarded-For` ([09 DA-12](09_decisiones_y_supuestos.md)).

---

## Flujo 4: Cambio de contraseña (RN-07)
**Actor**: autenticado (también con el cambio pendiente: es ruta de `/auth`).

1. Valida contrato `{password_actual, password_nueva}` (ambas ≤ 72 bytes).
2. Verifica la contraseña actual (bcrypt fuera del bucle) y calcula el nuevo hash, antes de la transacción.
3. `async with uow:` actualiza `password_hash`, `password_cambiada_en = now()`, `debe_cambiar_password = false`; agrega el `evento_seguridad` (`accion` = «Cambio de contraseña»).
4. **Después** de anotar el cambio, emite un JWT nuevo con `iat` de hora completa → cookie nueva → 200.
5. La cookie anterior da 401 en la petición siguiente, aunque sea del mismo segundo (C-09).

---

## Flujo 5: Asignar y revocar roles (RN-03, RN-05)
**Actor**: ADMIN.

- **Alta de personal** (`POST /usuarios`, [09 DA-17](09_decisiones_y_supuestos.md)): contrato `{email, nombre, password_provisoria, rol}` con `rol` ∈ {ADMIN, RECEPCION, MECANICO} (CLIENTE u otro → 422). Hash antes de la transacción; `async with uow:` usuario (`debe_cambiar_password = true`) + asignación (`otorgada_por` = actor) + evento «Alta de personal <email>» → 201; email repetido → 409.
- **Asignar** (`{rol, vence_en?}`): valida `vence_en` (con zona y futuro, si no 422). Si hay una fila abierta **vencida** del mismo rol, la cierra escribiendo `revocada_en` y abre una nueva ([09 DA-18](09_decisiones_y_supuestos.md)); si hay una abierta vigente → 409 (índice único parcial). `otorgada_por` = actor. Evento «Asignación de rol <ROL> a <email>» → 201.
- **Revocar**: usuario inexistente → 404. Si es el propio ADMIN del actor, o si revocar ese ADMIN deja **cero administradores vigentes** → 409 ([09 DA-15](09_decisiones_y_supuestos.md)). Escribe `revocada_en` (no borra). Evento «Revocación de rol <ROL> a <email>» → 200.
- El vencimiento por tiempo no se controla para RN-05 ([09 SU-11](09_decisiones_y_supuestos.md)).
- Efecto inmediato: la sesión abierta del afectado recibe 403 en la petición siguiente (C-07).

---

## Flujo 6: Alta de orden (RN-10, RN-16, RN-19)
**Actor**: RECEPCION o ADMIN.

1. Contrato: `vehiculo_id`, `falla`, `items[{repuesto_id, cantidad}]` (≥ 1 ítem, `cantidad > 0`, sin `repuesto_id` repetidos → **422**, [09 DA-19](09_decisiones_y_supuestos.md)); precio, total, estado y fecha no viajan (`extra="forbid"`).
2. `async with uow:`
   - Catálogo vacío → **409** con mensaje propio (RN-19).
   - Vehículo inexistente o dado de baja → 409 (supuesto, [09 SU-07](09_decisiones_y_supuestos.md)).
   - Repuesto inexistente o dado de baja → **409** y la orden no queda creada (C-10).
   - Copia `precio_unitario` de cada repuesto; calcula `total` = Σ cantidad × precio_unitario.
   - Agrega `orden_trabajo` (estado PENDIENTE), los `item_orden` y la línea de `historial_estado_orden` (`desde_estado = null`, `hasta_estado = PENDIENTE`, `usuario_id` = actor).
3. Commit → **201** con el detalle (ejemplo en [11](11_casos_de_prueba.md#ejemplos-de-la-consigna)).

---

## Flujo 7: Iniciar orden (RN-11)
**Actor**: MECANICO.

1. Orden inexistente → 404. Estado ≠ PENDIENTE → 409.
2. `async with uow:` `estado = EN_REPARACION`, `mecanico_id = actor`, línea de historial → 200.

---

## Flujo 8: Terminar orden (RN-11, RN-13, RN-14) — operación de varias escrituras
**Actor**: el mecánico asignado o ADMIN.

1. Orden inexistente → 404. Permiso: el actor es `mecanico_id` **y** tiene MECANICO vigente, o tiene ADMIN vigente; si no → **403** (antes que el estado, [09 DA-22](09_decisiones_y_supuestos.md)). Estado ≠ EN_REPARACION → 409.
2. `async with uow:` para cada ítem, a través del **punto único de escritura de stock**:
   - si `stock < cantidad` → excepción → rollback → **409**: estado, stock, movimientos e historial quedan exactamente como estaban (C-11);
   - si no, `stock -= cantidad` y agrega `movimiento_stock` con `cantidad` **negativa** y `orden_id`.
   - Cambia `estado = TERMINADA` y agrega la línea de historial.
   - Los repuestos dados de baja después del alta de la orden se descuentan igual: se leen con `get_by_id_including_deleted` ([09 DA-21](09_decisiones_y_supuestos.md)). El movimiento lleva `motivo = "Orden terminada"`.
3. Commit → 200. **Recién entonces** corre la tarea `BackgroundTasks` del aviso (`await asyncio.sleep(0.5)` + log), después de enviar la respuesta (C-12).

> Fuera de alcance: dos terminaciones simultáneas pueden pisarse el stock (actualización perdida, capítulo 7).

---

## Flujo 9: Cancelar orden (RN-11, RN-12)
**Actor**: RECEPCION, ADMIN o el dueño del vehículo. **Sin `requiere_rol`.**

1. Orden inexistente → 404.
2. Permiso: el actor tiene rol vigente RECEPCION/ADMIN, o es el usuario de la ficha de cliente dueña del vehículo; si no → **403**.
3. Estado ≠ PENDIENTE → **409**.
4. `async with uow:` `estado = CANCELADA` + línea de historial → 200.

---

## Flujo 10: Reposición y alta de repuesto (RN-14)
**Actor**: ADMIN.

- **Alta**: contrato con `stock_inicial >= 0` (negativo → 422). `async with uow:` agrega `repuesto`; si `stock_inicial > 0`, a través del punto único, el `movimiento_stock` «Stock inicial» en el mismo UoW; si es `0`, sin movimiento ([09 DA-27](09_decisiones_y_supuestos.md)). Código vigente repetido → 409.
- **Consultas**: `GET /repuestos/{id}/movimientos` y `/precios` devuelven una lista simple, sin envoltorio ([09 DA-28](09_decisiones_y_supuestos.md)).
- **Reponer**: cuerpo `{"cantidad": int}` con `cantidad > 0` (si no, 422). `async with uow:` punto único de stock: `stock += cantidad` y un movimiento positivo con `motivo = "Reposición"` → 200 con el repuesto actualizado ([09 DA-09, DA-10](09_decisiones_y_supuestos.md)).
- `motivo` del alta: `"Stock inicial"`; de la terminación: `"Orden terminada"` (con `orden_id`).

---

## Flujo 11: Edición de repuesto con historial de precio (RN-20)
**Actor**: ADMIN.

1. Contrato del PATCH: sólo `descripcion` y `precio`; `stock` → 422 (`extra="forbid"`).
2. `async with uow:` aplica sólo lo enviado (`exclude_unset`). Si `precio` viene **y es distinto** del actual, agrega `historial_precio_repuesto(precio_anterior, precio_nuevo)` en la misma transacción. Si no cambia, ninguna línea.
3. 200.

---

## Flujo 12: Baja de vehículo (RN-16)
**Actor**: RECEPCION o ADMIN.

1. Inexistente (o ya dado de baja) → 404.
2. Tiene órdenes en un estado con `es_final = false` → **409**.
3. `soft_delete` (escribe `borrado_en`) → **204**. La patente queda libre para un nuevo registro (C-19).

---

## Flujo 13: Detalle de orden sin N+1
**Actor**: el personal, o el dueño del vehículo (otro cliente → 403).

- El repositorio declara en el método la carga anticipada de vehículo → cliente, ítems → repuesto, e historial (p. ej. `selectinload`/`joinedload`). La cantidad de consultas es la misma con 2 que con 4 ítems (C-15), visible con `SQL_ECHO=true`.
