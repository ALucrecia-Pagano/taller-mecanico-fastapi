# intentos-de-acceso Specification

## Purpose

Limita verificaciones de credenciales por correo y dirección y conserva intentos auditables aun cuando la petición que los originó se revierta.

## Requirements

### Requirement: Límite por correo y dirección
El login SHALL contar en una consulta fallos del mismo correo/IP de los últimos 60 s posteriores al último éxito. Con cinco o más SHALL responder 429 antes de verificar, sin registrar ese rechazo; Retry-After indica segundos restantes redondeados hacia arriba (precisión [Alumna] de DA-11).

#### Scenario: I1 — Sexto intento
- **GIVEN** Dado cinco fallos consecutivos del par dentro de 60 s
- **WHEN** Cuando llega el sexto intento
- **THEN** Entonces responde 429 con Retry-After, cero llamadas bcrypt y exactamente cinco filas de fallo

#### Scenario: I2 — Segundos restantes
- **GIVEN** Dado cinco fallos y un desbloqueo a 1.2 s del ahora controlado
- **WHEN** Cuando se intenta login
- **THEN** Entonces Retry-After vale 2, es positivo y el conteo ejecuta una consulta

#### Scenario: I3 — Salida de ventana
- **GIVEN** Dado cinco fallos y tiempo controlado
- **WHEN** Cuando se alcanza el instante en que quedan menos de cinco en la ventana
- **THEN** Entonces se permite verificar sin dormir y el límite ya no devuelve 429

#### Scenario: I4 — Éxito reinicia
- **GIVEN** Dado cuatro fallos de un par y luego un éxito
- **WHEN** Cuando ocurre un nuevo fallo
- **THEN** Entonces el conteo es uno, el éxito existe y los fallos anteriores siguen guardados

#### Scenario: I5 — Pares independientes
- **GIVEN** Dado un par bloqueado
- **WHEN** Cuando se usa otro correo con la misma IP u otra IP con el mismo correo
- **THEN** Entonces ninguno hereda el bloqueo del par original

#### Scenario: I6 — IP real
- **GIVEN** Dado el par bloqueado y un X-Forwarded-For distinto
- **WHEN** Cuando llega intento desde el mismo client.host
- **THEN** Entonces sigue bloqueado y la cabecera no cambia la IP usada

### Requirement: Intento confirmado independientemente
Cada verificación de login SHALL registrar email, client.host, fecha y resultado en sesión y transacción propias confirmadas. El éxito reinicia el conteo sin borrar filas; un fallo posterior de la petición no SHALL borrar el intento.

#### Scenario: I7 — Sobrevive rollback
- **GIVEN** Dado una verificación registrada en sesión propia y escritura de petición aún no confirmada
- **WHEN** Cuando la petición falla y revierte
- **THEN** Entonces otra sesión ve el intento confirmado y no la escritura revertida

#### Scenario: I8 — Éxito persistido
- **GIVEN** Dado un login válido
- **WHEN** Cuando se completa
- **THEN** Entonces otra sesión ve una fila exito=true del par y el token sólo se entrega después de confirmar ese registro


