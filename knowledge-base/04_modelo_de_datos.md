# Modelo de Datos

> **Los nombres de tablas y columnas son obligatorios**: los casos de prueba y la corrección los usan. Se pueden **agregar** columnas, pero no quitar ni renombrar las indicadas (consigna, p. 4).

Reglas generales (consigna, p. 6):
- Todas las fechas son `timestamptz`.
- El dinero es `NUMERIC` en la base y `Decimal` en Python, nunca `float`.
- **Cada clave foránea lleva un índice**, porque PostgreSQL no lo crea solo.
- Las columnas marcadas «(nulo)» admiten NULL; **todas las demás son `NOT NULL`** ([09 DA-20](09_decisiones_y_supuestos.md)).

## Dominios (módulos) y entidades

| Módulo | Entidades (clase → tabla) |
|---|---|
| `usuarios` | `Usuario` → `usuario`, `AsignacionRol` → `asignacion_rol`, `IntentoAcceso` → `intento_acceso`, `EventoSeguridad` → `evento_seguridad` |
| `clientes` | `Cliente` → `cliente`, `Vehiculo` → `vehiculo` |
| `repuestos` | `Repuesto` → `repuesto`, `MovimientoStock` → `movimiento_stock`, `HistorialPrecio` → `historial_precio_repuesto` |
| `ordenes` | `OrdenTrabajo` → `orden_trabajo`, `EstadoOrden` → `estado_orden`, `ItemOrden` → `item_orden`, `HistorialEstadoOrden` → `historial_estado_orden` |
| `health` | — (sólo `router.py`) |

Estereotipos (Figura 1): **«catalog»** = `estado_orden` (tabla de referencia que carga `seed.py`); **«appendOnly»** = `historial_estado_orden`, `movimiento_stock`, `historial_precio_repuesto` (sólo agregado, protegidas por el disparador). `IntentoAcceso` y `EventoSeguridad` no se relacionan con ninguna otra tabla.

## ERD (de la Figura 1 + columnas de las tablas)

```
                      0..1 ─── 1 a 1 ─── 0..1
        Cliente ◄──────────────────────────────► Usuario ───── roles 1 : 0..* ────► AsignacionRol
          ▲ 1                                      ▲ 0..1
          │ asociación                             │ «mecánico»
          │ 0..*                                   │
        Vehiculo ◄── 1 ── asociación ── 0..* ── OrdenTrabajo ── 0..* ── catálogo ── 1 ──► «catalog» EstadoOrden
                                                 ◆ 1        ◆ 1
                                  composición 1..*│          │ composición 1..*
                                               ItemOrden    «appendOnly» HistorialEstadoOrden
                                                  │ 0..*
                                                  │ asociación
                                                  ▼ 1
   «appendOnly» MovimientoStock ── 0..* ──────► Repuesto ◄────── 0..* ── «appendOnly» HistorialPrecio
                                                  (1)                          (1)
   IntentoAcceso, EventoSeguridad: sin relaciones
```

Relaciones (cardinalidades de la Figura 1):

| Desde | Hacia | Tipo | Cardinalidad | Columna FK |
|---|---|---|---|---|
| `OrdenTrabajo` | `Vehiculo` | Asociación | 0..* → 1 | `orden_trabajo.vehiculo_id` |
| `Vehiculo` | `Cliente` | Asociación | 0..* → 1 | `vehiculo.cliente_id` |
| `Cliente` | `Usuario` | Uno a uno opcional | 0..1 ↔ 0..1 | `cliente.usuario_id` (UNIQUE, nulo permitido) |
| `Usuario` | `AsignacionRol` | Asociación («roles») | 1 → 0..* | `asignacion_rol.usuario_id` |
| `OrdenTrabajo` | `Usuario` | Asociación («mecánico») | 0..* → 0..1 | `orden_trabajo.mecanico_id` (nulo) |
| `OrdenTrabajo` | `EstadoOrden` | Catálogo | 0..* → 1 | `orden_trabajo.estado` → `estado_orden.codigo` |
| `OrdenTrabajo` | `ItemOrden` | **Composición** | 1 ◆ 1..* | `item_orden.orden_id` |
| `OrdenTrabajo` | `HistorialEstadoOrden` | **Composición** | 1 ◆ 1..* | `historial_estado_orden.orden_id` |
| `ItemOrden` | `Repuesto` | Asociación | 0..* → 1 | `item_orden.repuesto_id` |
| `MovimientoStock` | `Repuesto` | Asociación | 0..* → 1 | `movimiento_stock.repuesto_id` |
| `HistorialPrecio` | `Repuesto` | Asociación | 0..* → 1 | `historial_precio_repuesto.repuesto_id` |

FKs que salen de los nombres de columna y **no** aparecen en la Figura 1 (supuestos, [09 SU-02](09_decisiones_y_supuestos.md)):
- `historial_estado_orden.desde_estado` / `hasta_estado` → `estado_orden.codigo` (**explícito** en la tabla de la consigna).
- `historial_estado_orden.usuario_id`, `movimiento_stock.usuario_id`, `historial_precio_repuesto.usuario_id` → `usuario.id` (inferido).
- `movimiento_stock.orden_id` (nulo) → `orden_trabajo.id` (inferido).
- `asignacion_rol.otorgada_por` (nulo) → `usuario.id`: el ADMIN que asigna; nulo cuando lo asigna el registro o el seed ([09 DA-08](09_decisiones_y_supuestos.md)).

Navegación ORM (Ejercicio 2): declarar la navegación **en los dos extremos de cada relación que se lea**. `Usuario.cliente` devuelve **un objeto, no una lista**.

## Entidades

Columnas y restricciones textuales de la consigna (pp. 5-6).

### usuario
- Columnas: `id`, `email`, `nombre`, `password_hash`, `activo`, `debe_cambiar_password`, `password_cambiada_en` (con zona, nulo permitido).
- Restricciones: `email` UNIQUE.
- Tipos según la Figura 1: `int id`, `str email`, `str nombre`, `str password_hash`, `bool activo`, `bool debe_cambiar_password`. La figura no muestra `password_cambiada_en`; la tabla la exige (`timestamptz`, nulo).
- No tiene columna `rol`.

### asignacion_rol
- Columnas: `id`, `usuario_id`, `rol`, `desde`, `vence_en` (nulo), `revocada_en` (nulo), `otorgada_por` (nulo).
- Restricciones: CHECK de `rol` dentro de `ADMIN`, `RECEPCION`, `MECANICO`, `CLIENTE`; **índice único parcial** (`usuario_id`, `rol`) `WHERE revocada_en IS NULL`.
- Tipo de `rol` en la figura: `Rol` (enum).
- Revocar escribe `revocada_en`; **la fila nunca se borra**.
- `otorgada_por`: FK nullable a `usuario.id` (el ADMIN que asigna); `NULL` si la asigna el auto-registro o el seed ([09 DA-08](09_decisiones_y_supuestos.md)).

### intento_acceso
- Columnas: `id`, `cuando`, `email`, `ip`, `exito`.
- Restricciones: índice (`email`, `ip`, `cuando`).
- Se escribe en **sesión y transacción propias** que siempre se confirman (Ejercicio 7).

### evento_seguridad
- Columnas: `id`, `cuando`, `actor` (texto), `accion`.
- Restricciones: sin restricciones extra.
- `actor` es texto, no FK (los datos iniciales usan `SISTEMA`).

### cliente
- Columnas: `id`, `usuario_id` (nulo permitido), `nombre`, `documento`, `telefono`.
- Restricciones: `usuario_id` UNIQUE; `documento` UNIQUE.

### vehiculo
- Columnas: `id`, `cliente_id`, `patente`, `marca`, `modelo`, `anio`, `borrado_en` (nulo).
- Restricciones: **índice único parcial** (`patente`) `WHERE borrado_en IS NULL`; `CHECK anio BETWEEN 1950 AND 2100`.
- Borrado lógico.

### repuesto
- Columnas: `id`, `codigo`, `descripcion`, `precio` (NUMERIC 10,2), `stock`, `borrado_en` (nulo).
- Restricciones: **índice único parcial** (`codigo`) `WHERE borrado_en IS NULL`; `CHECK precio > 0`; `CHECK stock >= 0`.
- Borrado lógico. El stock sólo cambia por movimientos (RN-14).

### estado_orden «catalog»
- Columnas: `codigo` (clave primaria), `descripcion`, `posicion`, `es_final`.
- Restricciones: catálogo; `posicion` UNIQUE.
- La PK es el código y no un `id`, para que `orden_trabajo.estado` se lea igual en psql que en la API.
- La migración crea la tabla **vacía**; las filas las carga `seed.py`.
- Repositorio propio de **sólo lectura** que **no hereda** de `BaseRepository`.

### orden_trabajo
- Columnas: `id`, `vehiculo_id`, `mecanico_id` (nulo), `estado`, `falla`, `creada_en`, `total` (NUMERIC 12,2).
- Restricciones: `estado` es clave foránea a `estado_orden.codigo`; `CHECK total >= 0`.

### item_orden
- Columnas: `id`, `orden_id`, `repuesto_id`, `cantidad`, `precio_unitario` (NUMERIC 10,2).
- Restricciones: `CHECK cantidad > 0`; `CHECK precio_unitario > 0`; UNIQUE (`orden_id`, `repuesto_id`).

### historial_estado_orden «appendOnly»
- Columnas: `id`, `orden_id`, `desde_estado` (nulo), `hasta_estado`, `usuario_id`, `cuando`.
- Restricciones: `desde_estado` y `hasta_estado`, claves foráneas a `estado_orden.codigo`; sólo agregado.

### movimiento_stock «appendOnly»
- Columnas: `id`, `repuesto_id`, `orden_id` (nulo), `usuario_id`, `cantidad`, `motivo`, `cuando`.
- Restricciones: `CHECK cantidad <> 0`; sólo agregado.
- Signo: entradas positivas (stock inicial, reposición), salidas por terminar una orden **negativas** (aclaración de la alumna, [09 DD-13](09_decisiones_y_supuestos.md); consistente con `CHECK cantidad <> 0`).
- Valores de `motivo` ([09 DA-09](09_decisiones_y_supuestos.md)):

  | `motivo` | Origen | Signo de `cantidad` | `orden_id` |
  |---|---|---|---|
  | `Stock inicial` | Alta de repuesto (y seed) | + | `NULL` |
  | `Reposición` | `POST /repuestos/{id}/reponer` | + | `NULL` |
  | `Orden terminada` | `POST /ordenes/{id}/terminar` | − | id de la orden |

### historial_precio_repuesto «appendOnly»
- Columnas: `id`, `repuesto_id`, `usuario_id`, `precio_anterior` (NUMERIC 10,2), `precio_nuevo` (NUMERIC 10,2), `cuando`.
- Restricciones: `CHECK precio_nuevo > 0`; `CHECK precio_nuevo <> precio_anterior`; sólo agregado.
- El precio puede bajar; sólo tiene que cambiar (RN-20).

## Índices

| Tabla | Índice | Tipo |
|---|---|---|
| `usuario` | `email` | UNIQUE |
| `asignacion_rol` | (`usuario_id`, `rol`) `WHERE revocada_en IS NULL` | Único parcial (`postgresql_where`) |
| `intento_acceso` | (`email`, `ip`, `cuando`) | Compuesto |
| `cliente` | `usuario_id`; `documento` | UNIQUE |
| `vehiculo` | (`patente`) `WHERE borrado_en IS NULL` | Único parcial |
| `repuesto` | (`codigo`) `WHERE borrado_en IS NULL` | Único parcial |
| `estado_orden` | `posicion` | UNIQUE |
| `item_orden` | (`orden_id`, `repuesto_id`) | UNIQUE |
| Toda FK | la columna FK | Índice (PostgreSQL no lo crea solo) |

## Integridad en la base

- **Disparador de sólo agregado** (segunda migración, escrita a mano): rechaza cualquier `UPDATE` o `DELETE` sobre `historial_estado_orden`, `movimiento_stock` e `historial_precio_repuesto`, venga de donde venga (RN-15).
- **Estados por FK, no por CHECK** (RN-19): un estado inexistente lo rechaza la FK.
- **Enum en el código**: los estados también se nombran con un enum, que es el contrato de la API (un estado no declarado da 422) y el vocabulario del servicio para las transiciones. El enum y el catálogo tienen que coincidir; agregar un estado obliga a tocar los dos y el servicio.

## Migraciones

1. **Primera**: generada con `--autogenerate`, con todas las tablas (catálogo vacío).
2. **Segunda**: escrita **a mano**, con la función y el disparador de sólo agregado sobre las tres tablas (la comparación automática no ve funciones ni disparadores).
- Cada migración se lee antes de aplicarla y lleva **un comentario que lo diga**.
- Deben funcionar `alembic upgrade head` sobre base vacía → `alembic downgrade base` → `alembic upgrade head`.
- Plantilla asincrónica de Alembic; no se usa `create_all`.

## Seed data inicial (`seed.py`)

`seed.py` **vacía las tablas** (con `TRUNCATE … RESTART IDENTITY CASCADE`, la única vía que no choca con el disparador de sólo agregado: [09 DA-31](09_decisiones_y_supuestos.md)) y carga, como mínimo, estos datos (consigna, p. 19). Las contraseñas son de mentira y viven sólo en ese archivo. Se corre antes de cada archivo de prueba. Es parte de la puesta en marcha, no un extra.

| Qué | Datos |
|---|---|
| Catálogo de estados (se carga **primero**) | `PENDIENTE` (posición 1), `EN_REPARACION` (2), `TERMINADA` (3, final) y `CANCELADA` (4, final), cada uno con su descripción |
| Usuarios | `admin@example.com` y `admin2@example.com` (ADMIN), `recepcion@example.com` (RECEPCION), `mecanico@example.com` y `mecanico2@example.com` (MECANICO), `cliente@example.com` (CLIENTE) y `nuevo@example.com` (MECANICO, con el cambio de contraseña obligatorio) |
| Clientes | Laura, con usuario (`cliente@example.com`) y dos vehículos; Jorge, sin usuario, con un vehículo |
| Repuestos | Filtro de aceite (stock 10), pastillas de freno (4), bujía (2) y aceite por litro (20), cada stock cargado como un movimiento «Stock inicial» |
| Órdenes | La 1, PENDIENTE, del primer vehículo de Laura; la 2, EN_REPARACION, del vehículo de Jorge, asignada a `mecanico@example.com`, con 4 bujías cuando hay 2 |
| Historial de precios | Una línea del filtro de aceite: de 8000 a 8500 |
| Historial de seguridad | Una línea con el actor `SISTEMA`: «Carga de los datos iniciales» |

### Detalle del seed

Lo que la consigna no fija lo decidió la alumna ([09 DA-01 a DA-06, DA-08, DA-09](09_decisiones_y_supuestos.md)). Los ids siguen el orden de alta y coinciden con los ejemplos del PDF. Orden de carga: catálogo → usuarios → asignaciones → clientes → vehículos → repuestos (+ movimientos y precio) → órdenes (+ ítems e historiales) → evento de seguridad.

**Contraseña común (ficticia)**: `Taller2026!` — vive **sólo** en `seed.py` (DA-01).

**Usuarios** (DA-02):

| id | email | nombre | rol | `debe_cambiar_password` |
|---|---|---|---|---|
| 1 | `admin@example.com` | Ana Admin | ADMIN | false |
| 2 | `admin2@example.com` | Bruno Admin | ADMIN | false |
| 3 | `recepcion@example.com` | Rita Recepción | RECEPCION | false |
| 4 | `mecanico@example.com` | Mario Mecánico | MECANICO | false |
| 5 | `mecanico2@example.com` | Martín Mecánico | MECANICO | false |
| 6 | `cliente@example.com` | Laura Cliente | CLIENTE | false |
| 7 | `nuevo@example.com` | Nico Nuevo | MECANICO | **true** |

- Asignaciones de rol del seed: `vence_en = NULL`, `revocada_en = NULL`, `otorgada_por = NULL` (DA-08).
- `activo = true` (confirmado por la alumna, [09 DA-06](09_decisiones_y_supuestos.md)) y `password_cambiada_en = NULL` en todos.

**Clientes** (DA-03):

| id | nombre | documento | telefono | usuario |
|---|---|---|---|---|
| 1 | Laura Cliente | 30111222 | 2614000001 | 6 (`cliente@example.com`) |
| 2 | Jorge Pérez | 28333444 | 2614000002 | — (`NULL`) |

**Vehículos** (DA-04):

| id | cliente | patente | marca | modelo | anio |
|---|---|---|---|---|---|
| 1 | Laura (1) | AB123CD | Toyota | Corolla | 2018 |
| 2 | Laura (1) | AC456EF | Ford | Fiesta | 2015 |
| 3 | Jorge (2) | AD789GH | Volkswagen | Gol | 2012 |

**Repuestos** (DA-05):

| id | codigo | descripcion | precio | stock |
|---|---|---|---|---|
| 1 | FIL-001 | Filtro de aceite | 8500.00 | 10 |
| 2 | FRE-010 | Pastillas de freno delanteras | 32000.00 | 4 |
| 3 | BUJ-020 | Bujía de encendido | 6000.00 | 2 |
| 4 | ACE-530 | Aceite 5W30 por litro | 12000.00 | 20 |

- Un `movimiento_stock` por repuesto: `motivo = "Stock inicial"`, `cantidad` = stock, `orden_id = NULL`, `usuario_id = 1` (DA-06, DA-09).
- `historial_precio_repuesto`: una línea, repuesto 1, `precio_anterior 8000.00` → `precio_nuevo 8500.00`, `usuario_id = 1` (DA-05, DA-06).

**Órdenes** (DA-06):

| id | vehículo | estado | `mecanico_id` | falla | ítems | total |
|---|---|---|---|---|---|---|
| 1 | 1 (Laura, AB123CD) | PENDIENTE | `NULL` | Cambio de aceite y filtro | 1 × FIL-001 (8500.00) + 4 × ACE-530 (12000.00) | 56500.00 |
| 2 | 3 (Jorge, AD789GH) | EN_REPARACION | 4 (`mecanico@`) | Falla de encendido | 4 × BUJ-020 (6000.00) — hay 2 en stock | 24000.00 |

**Historial de estados** (DA-06):

| orden | `desde_estado` | `hasta_estado` | `usuario_id` |
|---|---|---|---|
| 1 | `NULL` | PENDIENTE | 3 (recepción) |
| 2 | `NULL` | PENDIENTE | 3 (recepción) |
| 2 | PENDIENTE | EN_REPARACION | 4 (`mecanico@`) |

**Historial de seguridad**: una línea con `actor = "SISTEMA"`, `accion = "Carga de los datos iniciales"`. `SISTEMA` es sólo actor de `evento_seguridad`; nunca un `usuario_id` (DA-06).

**Coherencia con los ejemplos de la consigna** (verificada):
- `POST /ordenes` del ejemplo crea la orden **3** (hay 2 en el seed), con `usuario_id 3` (recepción) en el historial, sobre el vehículo **2** (`AC456EF`, de «Laura Cliente»): 1 × 32000 + 3 × 12000 = 68000.00.
- `GET /repuestos?size=2` → `FIL-001` 8500.00 stock 10 y `FRE-010` 32000.00 stock 4, `total 4`, `pages 2`.
- C-16: sólo «Pastillas de freno delanteras» contiene «freno» → `total 1`.
- C-19: el vehículo 2 no tiene órdenes en el seed.
