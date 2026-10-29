# ciclo-de-vida Specification

## Purpose

Define cuándo se crean y se liberan los recursos de base de datos de la aplicación (en el arranque y en el apagado, nunca al importar un módulo) y cómo cada petición obtiene su propia sesión.

## Requirements

### Requirement: Recursos creados en el arranque
Al arrancar, la aplicación SHALL resolver la configuración y crear el motor asincrónico (con el tamaño de pool y el excedente de la configuración) y la fábrica de sesiones (sin expirar los objetos al confirmar), y guardarlos en el estado de la aplicación. Ningún recurso de base de datos se crea al importar un módulo. Si la configuración es inválida, el arranque falla.

#### Scenario: L1 — Estado poblado por el arranque
- **GIVEN** Dada la aplicación con la configuración de prueba
- **WHEN** Cuando completa el arranque
- **THEN** Entonces su estado tiene el motor, con el tamaño de pool de la configuración, y la fábrica de sesiones, configurada para no expirar los objetos al confirmar

#### Scenario: L3 — Arranque con la base caída
- **GIVEN** Dada una configuración que apunta a un puerto donde no hay ninguna base
- **WHEN** Cuando la aplicación arranca
- **THEN** Entonces el arranque termina sin errores (no se conecta a la base al arrancar)

#### Scenario: L4 — Arranque sin la clave de firma
- **GIVEN** Dado un entorno sin `JWT_SECRET_KEY`
- **WHEN** Cuando la aplicación arranca
- **THEN** Entonces el arranque falla y el error se propaga

### Requirement: Recursos liberados al apagar
Al apagarse, la aplicación SHALL cerrar el motor y liberar todas las conexiones de su pool, también cuando el arranque falla después de haber creado el motor.

#### Scenario: L2 — El apagado libera el pool
- **GIVEN** Dada la aplicación arrancada y su motor
- **WHEN** Cuando la aplicación se apaga
- **THEN** Entonces el motor fue cerrado: su pool de conexiones fue reemplazado por uno nuevo, sin conexiones

### Requirement: Una sesión por petición
Cada petición que necesite la base SHALL recibir su propia sesión, obtenida de la fábrica guardada en el estado de la aplicación. La sesión se cierra al terminar la petición y devuelve su conexión al pool. La sesión no confirma cambios por su cuenta.

#### Scenario: G1 — Sesiones distintas por petición
- **GIVEN** Dada la aplicación arrancada contra la base de prueba
- **WHEN** Cuando dos peticiones piden una sesión y cada una ejecuta `SELECT 1`
- **THEN** Entonces cada una recibe una sesión distinta, creada por la fábrica del estado de la aplicación
- **AND** las dos consultas devuelven 1

#### Scenario: G2 — La sesión se cierra al terminar
- **GIVEN** Dada una petición que usó su sesión contra la base de prueba
- **WHEN** Cuando la petición termina
- **THEN** Entonces la sesión quedó cerrada y el pool no tiene conexiones prestadas

### Requirement: Semáforo de bcrypt creado en el arranque
Al arrancar, la aplicación SHALL crear el semáforo que limita las llamadas a bcrypt, del tamaño de `BCRYPT_MAX_CONCURRENCY`, y guardarlo en su estado. No se crea al importar un módulo.

#### Scenario: F5 — Tamaño desde la configuración
- **GIVEN** Dada la aplicación arrancada con `BCRYPT_MAX_CONCURRENCY=1`
- **WHEN** Cuando se lanzan a la vez dos verificaciones de contraseña con el semáforo de su estado
- **THEN** Entonces el máximo de llamadas a bcrypt activas al mismo tiempo es 1

### Requirement: Hash ficticio del login calculado una vez en el arranque
Al arrancar, la aplicación SHALL calcular una sola vez un hash ficticio para el login de un correo inexistente (RN-09) y guardarlo en su estado. Se calcula con el costo de `BCRYPT_COST`, pasando por el semáforo y fuera del bucle, sobre una entrada aleatoria que se descarta: ninguna contraseña conocida verifica contra él.

#### Scenario: F1 — Hash presente con el costo configurado
- **GIVEN** Dada la configuración de prueba con `BCRYPT_COST=4`
- **WHEN** Cuando la aplicación completa el arranque
- **THEN** Entonces su estado tiene un hash ficticio que empieza con `$2b$04$`

#### Scenario: F2 — Una sola vez
- **GIVEN** Dado un registro de los cálculos de hash
- **WHEN** Cuando la aplicación arranca y atiende varias peticiones
- **THEN** Entonces se calculó exactamente un hash

#### Scenario: F3 — Ninguna contraseña conocida verifica
- **GIVEN** Dada la aplicación arrancada
- **WHEN** Cuando se verifica `Taller2026!` contra el hash ficticio
- **THEN** Entonces la verificación da falso

#### Scenario: F4 — El costo no está fijo
- **GIVEN** Dada la configuración de prueba con `BCRYPT_COST=5`
- **WHEN** Cuando la aplicación completa el arranque
- **THEN** Entonces el hash ficticio empieza con `$2b$05$`
