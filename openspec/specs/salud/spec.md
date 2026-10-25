# salud Specification

## Purpose

Expone dos sondas HTTP públicas que distinguen un proceso vivo de uno listo para atender: el proceso puede estar vivo y no estar listo, y reiniciarlo no arregla una base caída.

## Requirements

### Requirement: Sonda de vida
`GET /health/live` SHALL responder 200 sin tocar la base, sin requerir autenticación, con el cuerpo `{"estado": "vivo"}` (cuerpo **No especificado en la consigna**).

#### Scenario: H1 — Proceso vivo
- **GIVEN** Dada la aplicación arrancada
- **WHEN** Cuando se hace `GET /health/live`
- **THEN** Entonces la respuesta es 200 con `{"estado": "vivo"}`

#### Scenario: H2 — Vivo aunque la base esté caída
- **GIVEN** Dada la aplicación arrancada con una configuración que apunta a un puerto sin base
- **WHEN** Cuando se hace `GET /health/live`
- **THEN** Entonces la respuesta es 200 con `{"estado": "vivo"}`

### Requirement: Sonda de disponibilidad
`GET /health/ready` SHALL ejecutar `SELECT 1` con la sesión de la petición y responder 200 con `{"estado": "listo"}`. Si la base no está disponible (conexión rechazada, credenciales inválidas o sin respuesta en 3 segundos), responde 503 con `{"detail": "La base de datos no responde"}`, sin texto interno de la base ni del error. Cuerpos y plazo de 3 s: **No especificado en la consigna**.

#### Scenario: H3 — Base disponible
- **GIVEN** Dada la aplicación arrancada contra la base de prueba
- **WHEN** Cuando se hace `GET /health/ready`
- **THEN** Entonces la respuesta es 200 con `{"estado": "listo"}`

#### Scenario: H4 — Conexión rechazada
- **GIVEN** Dada la aplicación arrancada con una configuración que apunta a un puerto cerrado
- **WHEN** Cuando se hace `GET /health/ready`
- **THEN** Entonces la respuesta es 503 con `{"detail": "La base de datos no responde"}`
- **AND** el cuerpo no contiene texto del error original

#### Scenario: H5 — Credenciales inválidas
- **GIVEN** Dada la aplicación arrancada con una contraseña incorrecta para la base de prueba
- **WHEN** Cuando se hace `GET /health/ready`
- **THEN** Entonces la respuesta es 503 con `{"detail": "La base de datos no responde"}`

#### Scenario: H6 — Base que no contesta
- **GIVEN** Dado un servidor que acepta la conexión y nunca responde, y el plazo del chequeo reducido para la prueba
- **WHEN** Cuando se hace `GET /health/ready`
- **THEN** Entonces la respuesta es 503 con `{"detail": "La base de datos no responde"}`, una vez vencido el plazo

### Requirement: Sólo lectura por GET
Las dos sondas SHALL aceptar únicamente el método GET.

#### Scenario: H7 — Método no permitido
- **GIVEN** Dada la aplicación arrancada
- **WHEN** Cuando se hace `POST /health/ready`
- **THEN** Entonces la respuesta es 405

### Requirement: Humo manual
El repositorio SHALL incluir `test/health.http` con las dos sondas y la respuesta esperada en un comentario, para probarlas a mano con el servidor levantado. No corresponde a ningún caso C-NN de la consigna.

#### Scenario: Humo con el servidor levantado
- **GIVEN** Dado el servidor levantado con uvicorn contra la base de la aplicación
- **WHEN** Cuando se ejecutan las peticiones de `test/health.http`
- **THEN** Entonces las respuestas coinciden con las esperadas en los comentarios
