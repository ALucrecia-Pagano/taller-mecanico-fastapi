# Spec Delta

## ADDED Requirements

### Requirement: Autorización denegada a HTTP
Un error de autorización SHALL traducirse a 403 con {detail:mensaje} incluso desde dependencias. Falta de rol SHALL usar «No tiene permisos para realizar esta operación» y cambio pendiente «Debe cambiar la contraseña para continuar» [Alumna D4, No especificado en la consigna]. SHALL conservarse traducciones previas.

#### Scenario: E403a — Falta de rol
- **GIVEN** Dado dependencia que rechaza permiso
- **WHEN** Cuando resuelve la solicitud
- **THEN** Entonces responde 403 con detail No tiene permisos para realizar esta operación

#### Scenario: E403b — Cambio pendiente
- **GIVEN** Dado dependencia que rechaza cambio obligatorio
- **WHEN** Cuando resuelve la solicitud
- **THEN** Entonces responde 403 con detail Debe cambiar la contraseña para continuar

#### Scenario: E403c — Regresión de errores
- **GIVEN** Dado aplicación con nuevas rutas y errores
- **WHEN** Cuando recorre subclases y prueba códigos anteriores
- **THEN** Entonces cada error resuelve código; 401 D6, 404,409,422 y429/Retry-After conservan comportamiento, sin handler global

