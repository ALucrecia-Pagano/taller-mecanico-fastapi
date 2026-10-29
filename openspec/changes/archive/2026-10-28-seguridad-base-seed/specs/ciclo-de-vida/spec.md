# Spec Delta — ciclo-de-vida

## ADDED Requirements

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
