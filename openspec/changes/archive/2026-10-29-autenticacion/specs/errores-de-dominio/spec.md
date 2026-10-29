# Spec Delta

## ADDED Requirements

### Requirement: Límite de acceso a HTTP
Un error de dominio por límite de acceso SHALL traducirse en el router a 429 con cuerpo detail propio y Retry-After entero en segundos. No SHALL exponerse texto interno ni cambiar la traducción vigente de otros errores.

#### Scenario: E429 — Límite traducido
- **GIVEN** Dado una ruta o dependencia que lanza límite con dos segundos restantes
- **WHEN** Cuando se atiende la petición
- **THEN** Entonces responde 429 con Retry-After: 2 y detail propio

#### Scenario: E429b — Regresión
- **GIVEN** Dado una dependencia que lanza TokenInvalido con mensaje «Token inválido» y las rutas nuevas importadas
- **WHEN** Cuando se ejecutan T6 y T7 existentes
- **THEN** Entonces T6 conserva su 401 y mensaje original, y todos los errores de dominio nuevos tienen código HTTP; D6 se normaliza sólo en autenticación


