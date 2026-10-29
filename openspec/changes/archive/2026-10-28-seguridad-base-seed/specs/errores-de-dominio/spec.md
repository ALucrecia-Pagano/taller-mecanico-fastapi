# Spec Delta — errores-de-dominio

## MODIFIED Requirements

### Requirement: Error de dominio a HTTP
Toda ruta de la API SHALL traducir los errores de dominio, se lancen en el handler o en una de sus dependencias: no encontrado → 404, conflicto → 409, página inexistente → 422, token inválido → 401. En los cuatro casos el cuerpo es `{"detail": "<mensaje>"}`.

#### Scenario: T1 — Los tres códigos
- **GIVEN** Dada una aplicación de prueba con rutas que lanzan no encontrado, conflicto y página inexistente
- **WHEN** Cuando se llama a cada ruta
- **THEN** Entonces las respuestas son 404, 409 y 422, cada una con `{"detail": "<mensaje del error>"}`

#### Scenario: T2 — Error lanzado desde una dependencia
- **GIVEN** Dada una ruta de prueba cuya dependencia lanza un conflicto
- **WHEN** Cuando se llama a la ruta
- **THEN** Entonces la respuesta es 409 con `{"detail": "<mensaje del error>"}`

#### Scenario: T6 — Token inválido
- **GIVEN** Dada una ruta de prueba cuya dependencia lanza token inválido
- **WHEN** Cuando se llama a la ruta
- **THEN** Entonces la respuesta es 401 con `{"detail": "Token inválido"}`

## ADDED Requirements

### Requirement: Todo error de dominio tiene código HTTP
Cada subclase de error de dominio de la aplicación, directa o indirecta, SHALL tener un código HTTP en el mapa de traducción, propio o heredado de una clase de su jerarquía. Así ningún error de dominio nuevo puede terminar en 500 por falta de mapeo (decisión de la alumna).

#### Scenario: T7 — Recorrido de las subclases
- **GIVEN** Dada la aplicación real importada, con todos sus módulos
- **WHEN** Cuando se recorren todas las subclases de error de dominio, directas e indirectas
- **THEN** Entonces cada una resuelve un código HTTP
- **AND** el conjunto recorrido no está vacío e incluye token inválido
