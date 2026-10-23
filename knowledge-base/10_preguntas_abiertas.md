# Preguntas Abiertas

> Todo lo marcado **No especificado en la consigna** en la KB está acá. **Decisora: la alumna** (o el profe, si ella lo consulta). Nada de esto se implementa adivinando: se responde antes del change que lo necesita. Las preguntas resueltas **no se borran**: se marcan con su decisión en [09](09_decisiones_y_supuestos.md).

## Inconsistencias detectadas

### IN-01 — La Figura 1 omite columnas que la tabla exige
**Estado**: **Resuelta → ver 09 DA-00** (resolución propuesta aceptada).
**Figura 1 dice**: `Usuario` sin `password_cambiada_en`; `AsignacionRol` sin `otorgada_por` ni `usuario_id`; las tablas appendOnly sin `usuario_id`; ninguna clase muestra sus FK.
**Tabla del modelo dice**: todas esas columnas son obligatorias.
**Impacto**: bajo; la figura muestra atributos de dominio, no columnas.
**Resolución propuesta**: la **tabla** manda («los nombres de tablas y columnas son obligatorios»); la figura sólo aporta cardinalidades y tipos.

### IN-02 — La tabla de endpoints no lista el 403 por rol
**Estado**: **Resuelta → ver 09 DA-00** (resolución propuesta aceptada).
**Tabla de endpoints dice**: p. ej. `POST /usuarios` → 201, 409, 422 (sin 403).
**Casos de prueba dicen**: C-06 «Sin rol, 403»; C-18 «la recepción recibe 403».
**Resolución propuesta**: toda ruta con `requiere_rol` responde también 403 ([09 SU-04](09_decisiones_y_supuestos.md)).

### IN-03 — Guion de los códigos de regla
**Estado**: **Resuelta → ver 09 DA-00** (resolución propuesta aceptada).
**PDF**: `RN‑01` usa U+2011 (guion no separable); el resto del texto y los casos usan `-` común (`C-01`, `RN-19` en el Ejercicio 2).
**Resolución propuesta**: escribir siempre `RN-NN` con guion ASCII (ya aplicado en la KB).

## Preguntas abiertas (priorizadas)

| ID | Prioridad | Pregunta | Bloquea | Estado |
|---|---|---|---|---|
| PA-01 | Alta | **Seed — contraseñas**: ¿qué contraseña de mentira lleva cada usuario del seed (`admin@`, `admin2@`, `recepcion@`, `mecanico@`, `mecanico2@`, `cliente@`, `nuevo@`)? ¿Una común o una por usuario? | `seed.py`, todos los `.http` | **Resuelta → ver 09 DA-01** |
| PA-02 | Alta | **Seed — `nombre` de usuarios**: la columna es obligatoria pero la consigna no da los nombres (sólo «Laura Cliente» aparece en un ejemplo como nombre del **cliente**). | `seed.py` | **Resuelta → ver 09 DA-02** |
| PA-03 | Alta | **Seed — clientes**: `documento` y `telefono` de Laura y de Jorge; nombre completo de Jorge. ¿Laura se llama «Laura Cliente» en `cliente.nombre`? | `seed.py`, C-02 | **Resuelta → ver 09 DA-03** |
| PA-04 | Alta | **Seed — vehículos**: patente, marca, modelo y año del primer vehículo de Laura y del de Jorge. El segundo de Laura (id 2) tiene patente `AC456EF` (ejemplo); ¿marca/modelo/año? | `seed.py`, C-19 | **Resuelta → ver 09 DA-04** |
| PA-05 | Alta | **Seed — repuestos**: código y precio de la bujía (id 3) y precio inicial de pastillas/aceite (¿son 32000 y 12000 del ejemplo?). Descripciones exactas («Filtro de aceite», «Pastillas de freno delanteras», «Aceite 5W30 por litro» salen de ejemplos; la de la bujía no). | `seed.py`, C-10, C-16 | **Resuelta → ver 09 DA-05** |
| PA-06 | Alta | **Seed — órdenes e historiales**: ¿qué ítems tiene la orden 1? ¿La orden 2 tiene sólo las 4 bujías? Falla de cada orden. ¿Las órdenes del seed llevan historial (`null→PENDIENTE`, `PENDIENTE→EN_REPARACION`)? ¿Qué `usuario_id` se usa en historiales y movimientos «Stock inicial» del seed (la columna es NOT NULL y SISTEMA no es un usuario)? `total` de cada orden. | `seed.py`, C-11, C-12 | **Resuelta → ver 09 DA-06** |
| PA-07 | Alta | **Configuración**: nombres de las variables (clave JWT, duración del token, costo de bcrypt, pool, semáforo, `Secure`), valores por defecto no secretos (¿token 1800 s como el ejemplo?, ¿bcrypt 12?) y algoritmo de firma (¿HS256?). | change de proyecto/config | **Resuelta → ver 09 DA-07** |
| PA-08 | Media | **`asignacion_rol.otorgada_por`**: ¿FK a `usuario.id` (el ADMIN que asignó)? ¿Nulo cuando lo asigna el registro o el seed? | modelos | **Resuelta → ver 09 DA-08** |
| PA-09 | Media | **`movimiento_stock.motivo`**: sólo está fijado «Stock inicial». ¿Qué texto para la reposición y para la terminación de una orden? | repuestos, órdenes | **Resuelta → ver 09 DA-09** |
| PA-10 | Media | **`POST /repuestos/{id}/reponer`**: nombre del campo del cuerpo (¿`cantidad`?), si debe ser > 0, y qué devuelve el 200 (¿el repuesto actualizado?). | repuestos | **Resuelta → ver 09 DA-10** |
| PA-11 | Media | **Límite de login**: valor de `Retry-After` (¿segundos que faltan para que salga de la ventana el fallo más viejo, o 60 fijo?). ¿El intento rechazado con 429 también se anota en `intento_acceso`? | auth | **Resuelta → ver 09 DA-11** |
| PA-12 | Media | **`intento_acceso.ip`**: ¿`request.client.host` o respetar `X-Forwarded-For`? | auth | **Resuelta → ver 09 DA-12** |
| PA-13 | Media | **`evento_seguridad.actor` y `accion`**: cuando la acción la hace un usuario, ¿`actor` es su email, su id como texto, otra cosa? ¿Textos de `accion` para alta, cambio de rol y cambio de contraseña? | usuarios | **Resuelta → ver 09 DA-13** |
| PA-14 | Media | **`/mis-vehiculos` y `/mis-ordenes` sin ficha de cliente** (p. ej., un mecánico): ¿lista vacía (200) o error? | clientes, órdenes | **Resuelta → ver 09 DA-14** |
| PA-15 | Media | **RN-05 alcance**: ¿la regla «el sistema nunca queda sin administradores vigentes» también bloquea que un ADMIN le revoque el ADMIN al último otro admin vigente? ¿Y asignar ADMIN con `vence_en` al único admin? | usuarios | **Resuelta → ver 09 DA-15** (vencimiento no controlado: SU-11) |
| PA-16 | Media | **Contratos no ejemplificados**: campos de `POST /auth/registro` (¿email, nombre, password, documento, telefono?), `POST /auth/cambiar-password` (¿`password_actual`, `password_nueva`?), `POST /usuarios`, `POST /clientes`, `POST /clientes/{id}/vehiculos`, `POST /usuarios/{id}/roles`, respuesta de `GET /auth/yo`. | todos los módulos | **Resuelta → ver 09 DA-16** |
| PA-17 | Media | **`POST /usuarios` (alta de personal)**: ¿recibe el rol inicial en el cuerpo o se asigna después con `/usuarios/{id}/roles`? ¿Deja `debe_cambiar_password = true` por ser contraseña provisoria? | usuarios | **Resuelta → ver 09 DA-17** |
| PA-18 | Baja | **Reasignar un rol vencido**: ¿cerrar la fila vieja = escribir `revocada_en`? ([09 SU-03](09_decisiones_y_supuestos.md)) | usuarios | **Resuelta → ver 09 DA-18** |
| PA-19 | Baja | **`POST /ordenes` con repuestos repetidos**: ¿422 (contrato) o 409? Los códigos del endpoint admiten ambos. | órdenes | **Resuelta → ver 09 DA-19** |
| PA-20 | Baja | **Nulabilidad**: ¿todas las columnas sin «(nulo)» son NOT NULL? ([09 SU-01](09_decisiones_y_supuestos.md)) | modelos | **Resuelta → ver 09 DA-20** |
| PA-21 | Baja | **Baja de repuesto usado en órdenes abiertas**: RN-16 sólo prohíbe dar de baja un **vehículo** con órdenes abiertas. ¿Un repuesto se puede dar de baja aunque esté en una orden PENDIENTE/EN_REPARACION, y esa orden se puede terminar igual? | repuestos, órdenes | **Resuelta → ver 09 DA-21** |
| PA-22 | Baja | **Terminar por el mecánico asignado**: ¿requiere que siga teniendo el rol MECANICO vigente, o basta con ser el `mecanico_id`? | órdenes | **Resuelta → ver 09 DA-22** |
| PA-23 | Baja | **`GET /clientes/{id}` y `/mis-vehiculos`**: ¿incluyen los vehículos dados de baja? (RN-16 dice «deja de aparecer» → se asume que no). | clientes | **Resuelta → ver 09 DA-23** |
| PA-24 | Baja | **`GET /ordenes` del MECANICO**: ¿ve todas las órdenes o sólo las asignadas/pendientes? La tabla sólo dice el rol. | órdenes | **Resuelta → ver 09 DA-24** |
| PA-25 | Baja | **`GET /usuarios/{id}/roles`**: ¿devuelve sólo las vigentes o todo el historial (con revocadas y vencidas)? C-07 pide que «la fila revocada sigue». | usuarios | **Resuelta → ver 09 DA-25** |

## Discovery (estado del orquestador)

Los seis campos de `kb.discovery` se infirieron con confianza de la consigna; no hay entradas `[DISCOVERY]` pendientes.
