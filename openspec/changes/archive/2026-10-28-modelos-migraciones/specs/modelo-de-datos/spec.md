# Spec Delta — modelo-de-datos

## Purpose

Define las 13 tablas del dominio del taller con los nombres obligatorios de la consigna, y las garantías que da la propia base: tipos, nulabilidad, CHECK, UNIQUE, índices únicos parciales, estados por clave foránea al catálogo e índice por FK. Los nombres de restricción son estables, y la navegación entre entidades no hace consultas implícitas (Ejercicio 2).

## ADDED Requirements

### Requirement: Tablas y columnas obligatorias
Después de migrar, la base SHALL tener exactamente las 13 tablas de la consigna (pp. 5-6), cada una con exactamente sus columnas y con esos nombres. `usuario` MUST NOT tener una columna `rol`: los roles viven en `asignacion_rol` (DD-01).

#### Scenario: S1 — Columnas textuales de la consigna
- **GIVEN** Dada la base de prueba migrada a la última versión
- **WHEN** Cuando se leen las columnas de cada tabla del catálogo de la base
- **THEN** Entonces `usuario`, `asignacion_rol`, `intento_acceso`, `evento_seguridad`, `cliente`, `vehiculo`, `repuesto`, `estado_orden`, `orden_trabajo`, `item_orden`, `historial_estado_orden`, `movimiento_stock` e `historial_precio_repuesto` tienen exactamente las columnas que lista la consigna, ni una más ni una menos

#### Scenario: S2 — `usuario` sin columna `rol`
- **GIVEN** Dada la base de prueba migrada
- **WHEN** Cuando se buscan las columnas de `usuario`
- **THEN** Entonces ninguna se llama `rol`

### Requirement: Nulabilidad
Sólo las columnas marcadas «(nulo)» en la consigna SHALL admitir NULL; todas las demás MUST ser `NOT NULL` (DA-20). Las que admiten NULL son: `usuario.password_cambiada_en`; `asignacion_rol.vence_en`, `revocada_en` y `otorgada_por`; `cliente.usuario_id`; `vehiculo.borrado_en`; `repuesto.borrado_en`; `orden_trabajo.mecanico_id`; `historial_estado_orden.desde_estado`; `movimiento_stock.orden_id`.

#### Scenario: S3 — Sólo las marcadas «(nulo)» admiten NULL
- **GIVEN** Dada la base de prueba migrada
- **WHEN** Cuando se lee la nulabilidad de todas las columnas de las 13 tablas
- **THEN** Entonces admiten NULL exactamente las diez columnas listadas y ninguna otra

#### Scenario: K13 — Una columna obligatoria rechaza NULL
- **GIVEN** Dado un cliente existente
- **WHEN** Cuando se inserta un vehículo con `patente` nula
- **THEN** Entonces la base lo rechaza por violación de `NOT NULL`

### Requirement: Tipos de dinero y de fecha
El dinero SHALL guardarse como `NUMERIC` (`precio`, `precio_unitario`, `precio_anterior` y `precio_nuevo` con 10,2; `total` con 12,2) y leerse en la aplicación como decimal exacto, nunca como `float`. Toda fecha SHALL ser `timestamptz` y leerse con zona horaria.

#### Scenario: S4 — Tipos en la base
- **GIVEN** Dada la base de prueba migrada
- **WHEN** Cuando se leen los tipos de las columnas
- **THEN** Entonces `repuesto.precio`, `item_orden.precio_unitario`, `historial_precio_repuesto.precio_anterior` y `precio_nuevo` son `numeric(10,2)`, `orden_trabajo.total` es `numeric(12,2)`, y toda columna de fecha es `timestamp with time zone`

#### Scenario: T1 — El dinero vuelve como decimal exacto
- **GIVEN** Dado un repuesto guardado con precio 8500.00
- **WHEN** Cuando se lo vuelve a leer desde otra sesión
- **THEN** Entonces el precio es el decimal exacto `8500.00` y no un `float`

#### Scenario: T2 — La fecha vuelve con zona
- **GIVEN** Dado un vehículo dado de baja con un `borrado_en` en UTC
- **WHEN** Cuando se lo vuelve a leer
- **THEN** Entonces `borrado_en` trae zona horaria y representa el mismo instante

### Requirement: Fechas de alta con valor de la base
Las fechas que registran cuándo pasó algo SHALL tomar por defecto la hora de la base si la aplicación no las envía. Son `asignacion_rol.desde`, `intento_acceso.cuando`, `evento_seguridad.cuando`, `orden_trabajo.creada_en` y el `cuando` de las tres tablas de sólo agregado. **No especificado en la consigna** (decisión del agente aceptada por la alumna).

#### Scenario: S8 — Una fila de historial sin `cuando` explícito
- **GIVEN** Dada una orden existente
- **WHEN** Cuando se inserta una línea de `historial_estado_orden` sin enviar `cuando`
- **THEN** Entonces la fila queda con `cuando` igual a la hora de la transacción, con zona

### Requirement: Valores válidos por CHECK
La base SHALL rechazar los valores que violan los CHECK de la consigna:
- `asignacion_rol.rol` fuera de ADMIN, RECEPCION, MECANICO, CLIENTE;
- `vehiculo.anio` fuera de 1950 a 2100;
- `repuesto.precio` ≤ 0 o `stock` < 0;
- `orden_trabajo.total` < 0;
- `item_orden.cantidad` o `precio_unitario` ≤ 0;
- `movimiento_stock.cantidad` = 0;
- `historial_precio_repuesto.precio_nuevo` ≤ 0 o igual a `precio_anterior`.

Los valores en el borde válido SHALL aceptarse.

#### Scenario: K1 — Stock negativo
- **GIVEN** Dado un repuesto nuevo
- **WHEN** Cuando se guarda con `stock = -1`, y luego con `stock = 0`
- **THEN** Entonces el primero se rechaza por `ck_repuesto_stock_no_negativo` y el segundo se acepta

#### Scenario: K2 — Precio no positivo
- **GIVEN** Dado un repuesto nuevo
- **WHEN** Cuando se guarda con `precio = 0`, y luego con `precio = 0.01`
- **THEN** Entonces el primero se rechaza por `ck_repuesto_precio_positivo` y el segundo se acepta

#### Scenario: K3 — Total negativo
- **GIVEN** Dados un vehículo y el estado `PENDIENTE` en el catálogo
- **WHEN** Cuando se guarda una orden con `total = -0.01`, y luego con `total = 0`
- **THEN** Entonces la primera se rechaza por `ck_orden_trabajo_total_no_negativo` y la segunda se acepta

#### Scenario: K4 — Ítem con cantidad o precio no positivos
- **GIVEN** Dados una orden y un repuesto
- **WHEN** Cuando se guarda un ítem con `cantidad = 0`, otro con `precio_unitario = 0`, y otro con `cantidad = 1` y precio positivo
- **THEN** Entonces el primero se rechaza por `ck_item_orden_cantidad_positiva`, el segundo por `ck_item_orden_precio_unitario_positivo`, y el tercero se acepta

#### Scenario: K5 — Movimiento de stock en cero
- **GIVEN** Dados un repuesto y un usuario
- **WHEN** Cuando se guarda un movimiento con `cantidad = 0`, otro con `+3` y otro con `-3`
- **THEN** Entonces el primero se rechaza por `ck_movimiento_stock_cantidad_distinta_de_cero`, y los de `+3` (entrada) y `-3` (salida, DD-13) se aceptan

#### Scenario: K6 — Cambio de precio que no cambia
- **GIVEN** Dados un repuesto y un usuario
- **WHEN** Cuando se guarda una línea de historial con `precio_nuevo` igual a `precio_anterior`, otra con `precio_nuevo = 0`, y otra con un precio que baja
- **THEN** Entonces la primera se rechaza por `ck_historial_precio_repuesto_precio_cambia`, la segunda por `ck_historial_precio_repuesto_precio_nuevo_positivo`, y la que baja se acepta (RN-20)

#### Scenario: K7 — Año fuera de rango
- **GIVEN** Dado un cliente
- **WHEN** Cuando se guardan vehículos con `anio` 1949, 2101, 1950 y 2100
- **THEN** Entonces 1949 y 2101 se rechazan por `ck_vehiculo_anio`, y 1950 y 2100 se aceptan

#### Scenario: K8 — Rol fuera de la lista
- **GIVEN** Dado un usuario
- **WHEN** Cuando se le guarda una asignación con `rol = 'JEFE'`, y luego una con cada uno de los cuatro roles válidos
- **THEN** Entonces `JEFE` se rechaza por `ck_asignacion_rol_rol` y los cuatro válidos se aceptan

### Requirement: Unicidad común
La base SHALL rechazar un segundo `usuario.email`, `cliente.documento`, `cliente.usuario_id` no nulo, `estado_orden.posicion` o par `item_orden(orden_id, repuesto_id)` igual a uno existente. Varios clientes sin usuario (`usuario_id` NULL) SHALL aceptarse.

#### Scenario: K9 — Correo repetido
- **GIVEN** Dado un usuario con `email` `a@example.com`
- **WHEN** Cuando se guarda otro usuario con el mismo `email`
- **THEN** Entonces se rechaza por `uq_usuario_email`

#### Scenario: K10 — Documento repetido, usuario repetido y clientes sin usuario
- **GIVEN** Dado un cliente con documento `30111222` y un usuario asociado
- **WHEN** Cuando se guarda otro cliente con el mismo documento, otro con el mismo usuario, y dos clientes con `usuario_id` nulo
- **THEN** Entonces el primero se rechaza por `uq_cliente_documento`, el segundo por `uq_cliente_usuario_id`, y los dos sin usuario se aceptan

#### Scenario: K11 — Posición repetida en el catálogo
- **GIVEN** Dado el estado `PENDIENTE` en la posición 1
- **WHEN** Cuando se guarda otro estado en la posición 1
- **THEN** Entonces se rechaza por `uq_estado_orden_posicion`

#### Scenario: K12 — Repuesto repetido en una orden
- **GIVEN** Dada una orden con un ítem del repuesto 1
- **WHEN** Cuando se le agrega otro ítem del mismo repuesto
- **THEN** Entonces se rechaza por `uq_item_orden_orden_id_repuesto_id`

### Requirement: Unicidad sólo entre los vigentes
La patente de un vehículo y el código de un repuesto SHALL ser únicos sólo entre las filas sin `borrado_en`. Un usuario SHALL tener a lo sumo una asignación abierta (sin `revocada_en`) por rol. Las filas dadas de baja o revocadas no cuentan (RN-01, RN-03, DD-03).

#### Scenario: P1 — Patente vigente repetida
- **GIVEN** Dado un vehículo vigente con patente `AB123CD`
- **WHEN** Cuando se guarda otro vehículo vigente con la misma patente
- **THEN** Entonces se rechaza por `uq_vehiculo_patente_vigente`

#### Scenario: P2 — Patente de un vehículo dado de baja
- **GIVEN** Dado un vehículo con patente `AB123CD` dado de baja
- **WHEN** Cuando se guarda un vehículo vigente con la misma patente, para otro cliente
- **THEN** Entonces se acepta (base de C-19)

#### Scenario: P3 — Dos bajas con la misma patente
- **GIVEN** Dado un vehículo dado de baja con patente `AB123CD`
- **WHEN** Cuando se guarda otro vehículo con la misma patente, también dado de baja
- **THEN** Entonces se acepta

#### Scenario: P4 — Código de repuesto vigente y dado de baja
- **GIVEN** Dado un repuesto vigente con código `FIL-001`
- **WHEN** Cuando se guarda otro vigente con el mismo código, y luego, con el primero dado de baja, uno vigente con ese código
- **THEN** Entonces el primero se rechaza por `uq_repuesto_codigo_vigente` y el segundo se acepta

#### Scenario: P5 — Dos asignaciones abiertas del mismo rol
- **GIVEN** Dado un usuario con el rol `MECANICO` abierto
- **WHEN** Cuando se le guarda otra asignación abierta de `MECANICO`
- **THEN** Entonces se rechaza por `uq_asignacion_rol_abierta`

#### Scenario: P6 — Rol revocado y otro rol
- **GIVEN** Dado un usuario con el rol `MECANICO` revocado
- **WHEN** Cuando se le guarda una nueva asignación abierta de `MECANICO`, y una abierta de `ADMIN`
- **THEN** Entonces las dos se aceptan

### Requirement: Estados por clave foránea al catálogo
`orden_trabajo.estado`, `historial_estado_orden.desde_estado` y `hasta_estado` SHALL ser claves foráneas a `estado_orden.codigo`, sin CHECK con la lista de estados (RN-19, DD-02). Un estado que no está en el catálogo MUST rechazarse.

#### Scenario: F1 — Orden con estado inexistente
- **GIVEN** Dado un vehículo y el catálogo con `PENDIENTE`
- **WHEN** Cuando se guarda una orden con `estado = 'INEXISTENTE'`
- **THEN** Entonces se rechaza por `fk_orden_trabajo_estado_estado_orden` (C-14)

#### Scenario: F2 — Historial con estados
- **GIVEN** Dada una orden existente
- **WHEN** Cuando se guarda una línea de historial con `hasta_estado` inexistente, y otra con `desde_estado` nulo y `hasta_estado = 'PENDIENTE'`
- **THEN** Entonces la primera se rechaza por `fk_historial_estado_orden_hasta_estado_estado_orden` y la segunda se acepta

#### Scenario: F3 — Orden de un vehículo inexistente
- **GIVEN** Dado el catálogo con `PENDIENTE`
- **WHEN** Cuando se guarda una orden con un `vehiculo_id` que no existe
- **THEN** Entonces se rechaza por `fk_orden_trabajo_vehiculo_id_vehiculo`

### Requirement: Claves foráneas e índices
La base SHALL tener las 18 claves foráneas del modelo: las de la Figura 1, las de los estados, y las inferidas de SU-02 y DA-08. Toda columna FK SHALL ser la primera columna de algún índice, porque PostgreSQL no lo crea solo. Un UNIQUE que la encabeza cuenta como índice.

#### Scenario: S5 — Las 18 FK con su destino
- **GIVEN** Dada la base de prueba migrada
- **WHEN** Cuando se leen las claves foráneas
- **THEN** Entonces existen exactamente las 18 de la tabla de nombres de restricción, cada una con su tabla y columna destino, incluidas `estado`, `desde_estado` y `hasta_estado` hacia `estado_orden.codigo`

#### Scenario: S6 — Toda FK encabeza un índice
- **GIVEN** Dada la base de prueba migrada
- **WHEN** Cuando se cruza cada columna FK con las primeras columnas de los índices
- **THEN** Entonces ninguna FK queda sin índice, y la lista revisada tiene 18 FK

### Requirement: Nombres de restricción estables
Cada restricción e índice único SHALL tener el nombre fijo de la tabla «Nombres de restricción» del design, derivado de una convención y no generado por la base. Los tres índices parciales SHALL tener su condición `WHERE … IS NULL`. Esos nombres son el contrato de los mensajes 409 de cada módulo. **No especificado en la consigna** (pedido de CH-02).

#### Scenario: S7 — Nombres exactos
- **GIVEN** Dada la base de prueba migrada
- **WHEN** Cuando se leen los nombres de las restricciones UNIQUE, CHECK y FK y de los índices únicos
- **THEN** Entonces el conjunto coincide exactamente con la tabla del design
- **AND** `uq_asignacion_rol_abierta`, `uq_vehiculo_patente_vigente` y `uq_repuesto_codigo_vigente` son parciales, con `revocada_en IS NULL` y `borrado_en IS NULL` como condición

### Requirement: Navegación sin carga implícita
Cada relación de la Figura 1 SHALL poder navegarse desde sus dos extremos. `Usuario.cliente` SHALL devolver un objeto o nada, nunca una lista. Navegar una relación que no fue precargada MUST fallar de inmediato, sin consultar la base. Agregar una orden con sus ítems y su historial SHALL guardar todas las filas juntas.

#### Scenario: T3 — `Usuario.cliente` es un objeto
- **GIVEN** Dados un usuario con ficha de cliente y otro sin ficha
- **WHEN** Cuando se los lee precargando su cliente
- **THEN** Entonces el primero trae un cliente (no una lista) y el segundo trae nada

#### Scenario: T4 — Relación no precargada
- **GIVEN** Dada una orden leída sin precargar sus ítems
- **WHEN** Cuando se navega a sus ítems
- **THEN** Entonces falla de inmediato con el error de carga prohibida, sin ejecutar ninguna consulta

#### Scenario: T5 — Relaciones sin ambigüedad
- **GIVEN** Dados los modelos de los cuatro módulos, con dos FK de `asignacion_rol` hacia `usuario`
- **WHEN** Cuando se configuran todas las relaciones
- **THEN** Entonces no hay ningún error de configuración

#### Scenario: T6 — Orden con sus ítems y su historial en un solo alta
- **GIVEN** Dados un vehículo, dos repuestos, un usuario y el catálogo con `PENDIENTE`
- **WHEN** Cuando se agrega una orden con dos ítems y una línea de historial en la misma operación
- **THEN** Entonces quedan las cuatro filas, vinculadas a la orden
