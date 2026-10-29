# solo-agregado Specification

## Purpose

Garantiza en la propia base que `historial_estado_orden`, `movimiento_stock` e `historial_precio_repuesto` sean de sólo agregado: nadie puede modificar ni borrar sus filas, venga de donde venga (RN-15, Ejercicio 7). Además, `test/solo_agregado.sql` lo demuestra en `psql` (C-14).

## Requirements

### Requirement: Alta permitida
Las tres tablas de sólo agregado SHALL aceptar `INSERT`.

#### Scenario: D1 — Insertar en las tres tablas
- **GIVEN** Dada la base migrada, con una orden, un repuesto y un usuario
- **WHEN** Cuando se inserta una fila en `historial_estado_orden`, otra en `movimiento_stock` y otra en `historial_precio_repuesto`
- **THEN** Entonces las tres quedan guardadas

### Requirement: Modificación y borrado rechazados
La base SHALL rechazar todo `UPDATE` y todo `DELETE` que alcance filas de las tres tablas, con el código SQLSTATE `23001` y el mensaje propio «La tabla <tabla> es de sólo agregado: no se permite <operación>». El código y el texto son **No especificado en la consigna** (decisión del agente aceptada por la alumna).

#### Scenario: D2 — UPDATE rechazado en cada tabla
- **GIVEN** Dada una fila existente en cada una de las tres tablas
- **WHEN** Cuando se ejecuta un `UPDATE` sobre esa fila, tabla por tabla
- **THEN** Entonces los tres se rechazan con SQLSTATE `23001` y «La tabla <tabla> es de sólo agregado: no se permite UPDATE»
- **AND** la fila queda como estaba

#### Scenario: D3 — DELETE rechazado en cada tabla
- **GIVEN** Dada una fila existente en cada una de las tres tablas
- **WHEN** Cuando se ejecuta un `DELETE` sobre esa fila, tabla por tabla
- **THEN** Entonces los tres se rechazan con SQLSTATE `23001` y «… no se permite DELETE»
- **AND** la fila sigue en la tabla

#### Scenario: D4 — Un UPDATE que no alcanza filas no da error
- **GIVEN** Dada una de las tres tablas
- **WHEN** Cuando se ejecuta un `UPDATE` cuyo `WHERE` no encuentra ninguna fila
- **THEN** Entonces la sentencia termina sin error y no modifica nada (el rechazo es por fila: por eso C-14 exige filas)

#### Scenario: D7 — Las demás tablas siguen modificables
- **GIVEN** Dados una orden y un repuesto existentes
- **WHEN** Cuando se actualiza el total de la orden y el stock del repuesto
- **THEN** Entonces los dos cambios se aceptan

### Requirement: Vaciado para la puesta en marcha
`TRUNCATE` de las tres tablas SHALL seguir funcionando: es la única vía de vaciado, y la usa `seed.py` (DA-31). El trade-off está aceptado en DA-31: la consigna sólo pide rechazar `UPDATE` y `DELETE`.

#### Scenario: D5 — TRUNCATE permitido
- **GIVEN** Dadas filas en las tres tablas de sólo agregado
- **WHEN** Cuando se ejecuta `TRUNCATE` sobre ellas
- **THEN** Entonces las tres quedan vacías, sin error

### Requirement: Rechazo traducible por la aplicación
Si un error de la aplicación llegara a intentar un `UPDATE` o `DELETE` sobre esas tablas, el rechazo SHALL llegar como violación de integridad. Así lo traduce el mecanismo de errores de dominio a un 409 propio, nunca a un 500 con texto de la base (RN-18).

#### Scenario: D6 — El rechazo llega como violación de integridad
- **GIVEN** Dada una fila de `movimiento_stock`
- **WHEN** Cuando la aplicación ejecuta un `UPDATE` sobre ella a través de su sesión
- **THEN** Entonces recibe un error de violación de integridad (no un error genérico de la base), que el Unit of Work traduce a un conflicto

### Requirement: Demostración en psql (C-14)
`test/solo_agregado.sql` SHALL contener los seis rechazos del disparador (`UPDATE` y `DELETE` por tabla) y el rechazo por clave foránea de una orden con un estado que no está en el catálogo. Cada sentencia SHALL ir con la respuesta esperada en un comentario y SHALL apuntar a filas existentes, no a ids fijos. El archivo supone que antes se corrió `python seed.py`.

#### Scenario: X1 — Las siete sentencias fallan como se espera
- **GIVEN** Dada la base con al menos una fila en cada tabla de sólo agregado y un vehículo
- **WHEN** Cuando se ejecutan, una por una, las sentencias de `test/solo_agregado.sql`
- **THEN** Entonces las seis primeras se rechazan con SQLSTATE `23001`
- **AND** la séptima se rechaza con SQLSTATE `23503` por `fk_orden_trabajo_estado_estado_orden`

### Requirement: Corte si falta el seed
Antes de las siete sentencias, `test/solo_agregado.sql` SHALL verificar que las tres tablas de sólo agregado tienen al menos una fila. Si alguna está vacía, SHALL cortar con el mensaje «Corré python seed.py primero» sin ejecutar ninguna de las siete, porque un disparador de fila no salta sin filas y la evidencia no probaría nada. Decisión de la alumna.

#### Scenario: X2 — Tablas vacías
- **GIVEN** Dada la base migrada con alguna de las tres tablas de sólo agregado vacía
- **WHEN** Cuando se ejecuta `test/solo_agregado.sql`
- **THEN** Entonces la ejecución se detiene con «Corré python seed.py primero»
- **AND** no se ejecuta ninguna de las siete sentencias

### Requirement: Demostración sobre los datos iniciales
`test/solo_agregado.sql` SHALL funcionar sobre la base recién cargada por `python seed.py`. La verificación inicial pasa y las siete sentencias fallan como se espera, sin filas agregadas a mano.

#### Scenario: S14 — C-14 sobre el seed
- **GIVEN** Dada la base de prueba recién cargada por el seed
- **WHEN** Cuando se ejecutan la verificación inicial y, una por una, las siete sentencias de `test/solo_agregado.sql`
- **THEN** Entonces la verificación no corta
- **AND** las seis primeras se rechazan con SQLSTATE `23001` y la séptima con SQLSTATE `23503` por `fk_orden_trabajo_estado_estado_orden`

### Requirement: Evidencia de C-14
La entrega SHALL incluir la evidencia de `psql` de C-14, tomada sobre la base de la aplicación después de `python seed.py`: una captura (`docs/evidencias/capturas/C-14-solo-agregado.png`) y la misma salida en texto UTF-8 (`docs/evidencias/C-14-psql.txt`). El texto es decisión de la alumna. La toma la alumna.

#### Scenario: E1 — Salida en texto completa y legible
- **GIVEN** Dado `docs/evidencias/C-14-psql.txt`, generado con `psql -f test/solo_agregado.sql` sobre `taller_mecanico` recién cargada
- **WHEN** Cuando se inspecciona
- **THEN** Entonces es texto UTF-8, con los acentos legibles
- **AND** tiene 7 líneas `ERROR` y 6 con «sólo agregado»
- **AND** existe la captura `docs/evidencias/capturas/C-14-solo-agregado.png`
