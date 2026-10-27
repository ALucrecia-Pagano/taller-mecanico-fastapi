# Spec Delta — repositorios

## Purpose

Ofrece a todos los módulos un acceso genérico a sus tablas —leer, listar, contar, dar de alta, modificar y dar de baja— que nunca confirma la transacción, y una variante para las tablas con borrado lógico que oculta las filas dadas de baja (Ejercicio 6).

## ADDED Requirements

### Requirement: Alta sin confirmar
El repositorio genérico SHALL recibir la sesión y la clase del modelo. `add` SHALL enviar la fila a la base (`flush`) sin confirmar: la fila queda con su `id` y sus valores por defecto de la base cargados y legibles sin consultas implícitas, y otra sesión no la ve hasta que la transacción se confirma.

#### Scenario: R1 — El alta deja el id y los defaults de la base cargados
- **GIVEN** Dado un repositorio sobre la tabla de prueba `prueba_articulo`, dentro de una transacción abierta
- **WHEN** Cuando se da de alta un artículo
- **THEN** Entonces el artículo tiene `id` asignado
- **AND** su `creado_en` (valor por defecto de la base) se lee sin disparar una consulta implícita

#### Scenario: R2 — El alta no se confirma sola
- **GIVEN** Dado un artículo dado de alta dentro de una transacción todavía abierta
- **WHEN** Cuando otra sesión busca ese artículo
- **THEN** Entonces no lo encuentra
- **AND** después de confirmar la transacción, la otra sesión sí lo encuentra

### Requirement: Lectura por id
`get_by_id` SHALL devolver la fila con ese `id`, o nada si no existe.

#### Scenario: R3 — Id existente e inexistente
- **GIVEN** Dado un artículo guardado
- **WHEN** Cuando se lo busca por su `id`, y luego por un `id` que no existe
- **THEN** Entonces la primera búsqueda devuelve el artículo y la segunda no devuelve nada

### Requirement: Listado ordenado por ventana
`get_all` SHALL devolver las filas ordenadas por `id` ascendente, salteando `offset` filas y devolviendo como máximo `limit`.

#### Scenario: R4 — Ventana en orden y ventana fuera de rango
- **GIVEN** Dados 5 artículos guardados (ids 1 a 5)
- **WHEN** Cuando se listan con `offset=2` y `limit=2`, y luego con un `offset` mayor que la cantidad de filas
- **THEN** Entonces el primer listado devuelve los ids 3 y 4, en ese orden, y el segundo devuelve una lista vacía

### Requirement: Conteo
`count` SHALL devolver la cantidad de filas visibles para el repositorio.

#### Scenario: R5 — Conteo con filas y sin filas
- **GIVEN** Dados 5 artículos guardados
- **WHEN** Cuando se cuentan, y luego se cuentan con la tabla vacía
- **THEN** Entonces el conteo da 5 y después 0

### Requirement: Listados filtrados coherentes
Un listado filtrado de un repositorio de entidad SHALL contar el total con exactamente el mismo filtro con el que trae las filas.

#### Scenario: R10 — Total e items con el mismo filtro
- **GIVEN** Dados artículos que cumplen y que no cumplen un filtro
- **WHEN** Cuando un método con nombre lista y cuenta con ese filtro, primero con un filtro y luego con otro distinto
- **THEN** Entonces en cada caso el total coincide con la cantidad de filas que cumplen el filtro, y las filas devueltas son sólo ésas

### Requirement: Modificación parcial sin confirmar
`update` SHALL aplicar sólo los campos recibidos y enviarlos a la base (`flush`) sin confirmar. Una clave que no es campo del modelo, o la clave `id`, SHALL rechazarse con un error que nombre la clave, sin modificar la fila. El rechazo y su forma: **No especificado en la consigna** (decisión de la alumna).

#### Scenario: R6 — Modifica sólo lo enviado
- **GIVEN** Dado un artículo guardado con `nombre` y `cantidad`
- **WHEN** Cuando se lo modifica con `{"cantidad": 7}` dentro de una transacción abierta
- **THEN** Entonces `cantidad` vale 7 y `nombre` no cambia
- **AND** otra sesión no ve el cambio hasta que la transacción se confirma

#### Scenario: R7 — Clave desconocida rechazada
- **GIVEN** Dado un artículo guardado
- **WHEN** Cuando se lo modifica con una clave que no es campo del modelo
- **THEN** Entonces la modificación se rechaza con un error que nombra esa clave
- **AND** el artículo queda sin cambios

#### Scenario: R8 — El id no se modifica
- **GIVEN** Dado un artículo guardado
- **WHEN** Cuando se lo modifica con la clave `id`
- **THEN** Entonces la modificación se rechaza con un error que nombra `id`

### Requirement: Baja física sin confirmar
`delete` SHALL quitar la fila y enviarlo a la base (`flush`) sin confirmar.

#### Scenario: R9 — Baja física
- **GIVEN** Dado un artículo guardado
- **WHEN** Cuando se lo borra dentro de una transacción
- **THEN** Entonces dentro de la misma transacción ya no se lo encuentra por `id`
- **AND** después de confirmar, la fila no existe en la base

### Requirement: Ningún repositorio confirma
Ningún repositorio, ni el genérico ni los de los módulos, SHALL confirmar una transacción: la confirmación es del Unit of Work.

#### Scenario: R11 — Sin commit en los repositorios
- **GIVEN** Dados los archivos de repositorio del core y de todos los módulos
- **WHEN** Cuando se revisa su código fuente
- **THEN** Entonces ninguno contiene una llamada a `.commit(`

### Requirement: El borrado lógico oculta las filas dadas de baja
El repositorio con borrado lógico SHALL marcar la baja con la fecha y hora actual con zona (`borrado_en`), sin borrar la fila. Desde ese momento, la lectura por id, el listado, el conteo y todo método de un repositorio de entidad construido sobre él SHALL excluir esa fila.

#### Scenario: B1 — La fila dada de baja deja de verse
- **GIVEN** Dado un registro de `prueba_baja` guardado
- **WHEN** Cuando se le da la baja lógica
- **THEN** Entonces su `borrado_en` tiene fecha y hora con zona UTC
- **AND** ya no se lo encuentra por `id`, no aparece en el listado y no suma en el conteo

#### Scenario: B5 — Los métodos con nombre heredan el filtro
- **GIVEN** Dado un repositorio de entidad con un método con nombre, construido sobre el repositorio con borrado lógico y sin filtro de baja propio
- **WHEN** Cuando se lo usa con un registro dado de baja y otro vigente
- **THEN** Entonces sólo devuelve el vigente

### Requirement: Lectura que incluye los dados de baja
El repositorio con borrado lógico SHALL ofrecer `get_by_id_including_deleted`, que devuelve la fila aunque esté dada de baja (DA-21).

#### Scenario: B2 — Recuperar una fila dada de baja
- **GIVEN** Dado un registro de `prueba_baja` dado de baja
- **WHEN** Cuando se lo busca incluyendo los dados de baja
- **THEN** Entonces se lo encuentra, con su `borrado_en`

### Requirement: Baja lógica idempotente
Dar de baja una fila que ya estaba dada de baja SHALL conservar la fecha de baja original. **No especificado en la consigna.**

#### Scenario: B3 — Segunda baja
- **GIVEN** Dado un registro dado de baja en un momento conocido
- **WHEN** Cuando se le vuelve a dar la baja lógica
- **THEN** Entonces su `borrado_en` sigue siendo el original

### Requirement: Sólo modelos con borrado lógico
Construir el repositorio con borrado lógico sobre un modelo sin columna `borrado_en` SHALL fallar al construirlo, antes de cualquier consulta. **No especificado en la consigna.**

#### Scenario: B4 — Modelo sin borrado_en
- **GIVEN** Dado el modelo `prueba_articulo`, que no tiene `borrado_en`
- **WHEN** Cuando se construye un repositorio con borrado lógico sobre él
- **THEN** Entonces la construcción falla con un error de tipo
