# Spec Delta

## ADDED Requirements

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


