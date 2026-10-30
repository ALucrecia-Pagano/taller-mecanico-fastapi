# contrasenas Specification

## Purpose

Guarda y verifica las contraseñas con bcrypt sin bloquear el servidor: costo configurable, cada cálculo fuera del bucle de eventos y con concurrencia limitada, y un contrato de contraseña que nunca deja llegar a bcrypt una entrada que lo haría fallar (Ejercicio 4).

## Requirements

### Requirement: Contrato de contraseña
Todo campo de contraseña SHALL aceptar como máximo 72 bytes en UTF-8, contados en bytes y no en caracteres, y rechazar lo que pasa de ahí con un error de validación (422 en un contrato de entrada). SHALL rechazar también la cadena vacía y toda contraseña con un carácter NUL. bcrypt 5 acepta el NUL; se rechaza porque no tiene uso legítimo en una contraseña y suele traer problemas en otros sistemas. Estas dos reglas son «No especificado en la consigna» (decisión de la alumna).

#### Scenario: C1 — Contraseña común
- **GIVEN** Dada la contraseña `la contraseña ficticia definida en seed.py`
- **WHEN** Cuando se valida contra el contrato de contraseña
- **THEN** Entonces es válida

#### Scenario: C2 — Borde de 72 bytes ASCII
- **GIVEN** Dadas una contraseña de 72 caracteres ASCII y otra de 73
- **WHEN** Cuando se validan contra el contrato de contraseña
- **THEN** Entonces la de 72 es válida
- **AND** la de 73 se rechaza con un error de validación

#### Scenario: C3 — Se cuentan bytes, no caracteres
- **GIVEN** Dadas una contraseña de 36 «ñ» (36 caracteres, 72 bytes) y otra de 36 «ñ» más una «a» (37 caracteres, 73 bytes)
- **WHEN** Cuando se validan contra el contrato de contraseña
- **THEN** Entonces la primera es válida
- **AND** la segunda se rechaza con un error de validación

#### Scenario: C4 — Vacía o con NUL (No especificado en la consigna)
- **GIVEN** Dadas la contraseña vacía y la contraseña `abc` seguida de un carácter NUL
- **WHEN** Cuando se validan contra el contrato de contraseña
- **THEN** Entonces las dos se rechazan con un error de validación

### Requirement: Hash con costo configurable
El hash de una contraseña SHALL calcularse con bcrypt, con el costo que se le indica (tomado de `BCRYPT_COST`), nunca fijo en el código, y con una sal nueva en cada cálculo. El resultado SHALL ser distinto de la contraseña.

#### Scenario: H1 — Hash y verificación correcta
- **GIVEN** Dada la contraseña `la contraseña ficticia definida en seed.py` y el costo 4
- **WHEN** Cuando se calcula su hash y se verifica la misma contraseña contra él
- **THEN** Entonces el hash es distinto de la contraseña y empieza con `$2b$04$`
- **AND** la verificación da verdadero

#### Scenario: H3 — Sal nueva en cada hash
- **GIVEN** Dada la misma contraseña
- **WHEN** Cuando se calcula su hash dos veces
- **THEN** Entonces los dos hashes son distintos
- **AND** la contraseña verifica contra los dos

#### Scenario: H4 — El costo viaja en el hash
- **GIVEN** Dados un hash calculado con costo 5 y otro calculado con costo 4
- **WHEN** Cuando se inspecciona el primero y se verifica la contraseña contra el segundo
- **THEN** Entonces el primero empieza con `$2b$05$`
- **AND** la verificación contra el segundo da verdadero sin indicar ningún costo

### Requirement: Verificación de una contraseña incorrecta
Verificar una contraseña contra un hash que no le corresponde SHALL dar falso, sin error.

#### Scenario: H2 — Otra contraseña
- **GIVEN** Dado el hash de `la contraseña ficticia definida en seed.py`
- **WHEN** Cuando se verifica `OtraClave99` contra él
- **THEN** Entonces la verificación da falso

### Requirement: Rechazo propio de más de 72 bytes al calcular el hash
Calcular el hash de una contraseña de más de 72 bytes SHALL lanzar un error propio de valor, igual con cualquier versión de bcrypt admitida (una versión trunca en silencio y otra lanza su excepción). Es la defensa en profundidad detrás del contrato.

#### Scenario: H5 — 73 bytes
- **GIVEN** Dada una contraseña de 73 bytes
- **WHEN** Cuando se calcula su hash
- **THEN** Entonces se lanza el error de valor propio y no se calcula ningún hash

### Requirement: bcrypt fuera del bucle de eventos
Toda llamada a bcrypt, para calcular o para verificar, SHALL ejecutarse en un hilo aparte y nunca en el hilo del bucle de eventos (requisito no funcional «Credenciales»).

#### Scenario: H6 — Hilo distinto del bucle
- **GIVEN** Dado un registro del hilo en el que corre cada llamada a bcrypt
- **WHEN** Cuando se calcula un hash y se verifica una contraseña desde una tarea asincrónica
- **THEN** Entonces ninguna de las dos llamadas corrió en el hilo del bucle de eventos

### Requirement: Concurrencia de bcrypt limitada
Las llamadas a bcrypt SHALL pasar por un semáforo que limita cuántas corren a la vez. Su tamaño sale de `BCRYPT_MAX_CONCURRENCY`.

#### Scenario: H7 — Pico igual al límite
- **GIVEN** Dado un semáforo de tamaño 2
- **WHEN** Cuando se lanzan seis cálculos de hash a la vez
- **THEN** Entonces el máximo de llamadas a bcrypt activas al mismo tiempo es exactamente 2


### Requirement: Contratos de autenticación
Las entradas de registro, login y cambio SHALL rechazar extras y aplicar el contrato de contraseña existente a todos sus campos de contraseña. Vacío/NUL siguen siendo No especificado en la consigna, decisión previa. No SHALL agregarse complejidad no acordada.

#### Scenario: V1 — 72 bytes
- **GIVEN** Dado cada campo password, password_actual y password_nueva en su contrato
- **WHEN** Cuando se valida con 72 ASCII o 36 ñ y datos restantes válidos
- **THEN** Entonces se acepta el campo por longitud sin confundir bytes con caracteres

#### Scenario: V2 — 73 bytes
- **GIVEN** Dado cada campo de contraseña por separado
- **WHEN** Cuando se envía 73 ASCII o 36 ñ más a
- **THEN** Entonces responde 422 antes de llegar a bcrypt

#### Scenario: V3 — Vacío o NUL
- **GIVEN** Dado cada campo de contraseña
- **WHEN** Cuando se envía vacío o con NUL
- **THEN** Entonces responde 422, sin error 500

#### Scenario: V4 — Extras
- **GIVEN** Dado registro, login y cambio válidos
- **WHEN** Cuando se agrega un campo no declarado, incluido rol en registro
- **THEN** Entonces responde 422 sin ejecutar la operación

### Requirement: Nueva contraseña distinta
[Alumna] D7 — No especificado en la consigna: el contrato de cambio SHALL rechazar password_nueva igual a password_actual con 422 por comparación literal, sin bcrypt adicional ni escrituras.

#### Scenario: P3 — Igualdad con cambio pendiente
- **GIVEN** Dado un usuario autenticado con cambio obligatorio pendiente y snapshot
- **WHEN** Cuando envía actual y nueva idénticas
- **THEN** Entonces recibe 422, cero llamadas bcrypt, sin modificar hash/fecha/bandera, sin evento ni cookie renovada

#### Scenario: P3b — Igualdad sin obligación
- **GIVEN** Dado un usuario autenticado sin cambio pendiente
- **WHEN** Cuando envía actual y nueva idénticas
- **THEN** Entonces recibe el mismo rechazo contractual 422 sin bcrypt ni escrituras


