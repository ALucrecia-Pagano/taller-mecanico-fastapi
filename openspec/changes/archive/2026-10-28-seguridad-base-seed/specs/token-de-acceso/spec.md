# Spec Delta — token-de-acceso

## Purpose

Emite y valida el token de acceso: un JWT firmado con la clave y el algoritmo de la configuración, con `sub`, `iat` con fracción de segundo, `exp` y los roles vigentes al emitirlo. Todo token que no sirve se rechaza como un único error de dominio (Ejercicio 4, RN-07).

## ADDED Requirements

### Requirement: Contenido del token
El token SHALL llevar `sub` (el id del usuario como texto), `iat`, `exp` (`iat` más `JWT_EXPIRE_SECONDS`) y `roles` (los recibidos al emitir). Va firmado con `JWT_SECRET_KEY` y `JWT_ALGORITHM`. Los roles son informativos: la autorización no los lee. No lleva `iss`, `aud` ni `jti` («No especificado en la consigna»).

#### Scenario: T1 — Ida y vuelta
- **GIVEN** Dado un token emitido para el usuario 3 con los roles `RECEPCION`
- **WHEN** Cuando se valida
- **THEN** Entonces devuelve el usuario 3 como número, los roles `RECEPCION` y el mismo `iat` de la emisión

#### Scenario: T3 — Vencimiento desde la configuración
- **GIVEN** Dadas dos configuraciones, con `JWT_EXPIRE_SECONDS` 1800 y 60
- **WHEN** Cuando se emite un token con cada una
- **THEN** Entonces en cada token `exp` menos la parte entera de `iat` es igual a su duración

### Requirement: `iat` sin truncar a segundos
El token SHALL emitirse con la hora completa en `iat`, incluida la fracción de segundo, y la validación SHALL devolverla sin truncar (RN-07, DD-08).

#### Scenario: T2 — La fracción sobrevive (OB-09)
- **GIVEN** Dado un token emitido a una hora con fracción de segundo `.123456`
- **WHEN** Cuando se valida
- **THEN** Entonces el `iat` devuelto es exactamente esa hora en segundos con fracción
- **AND** su parte decimal no es cero

### Requirement: Token vencido rechazado
Un token cuyo `exp` ya pasó SHALL rechazarse como token inválido, sin tolerancia.

#### Scenario: T4 — Vencido
- **GIVEN** Dado un token emitido dos horas atrás con la duración por defecto
- **WHEN** Cuando se valida
- **THEN** Entonces se rechaza como token inválido

### Requirement: Firma y algoritmo verificados
La validación SHALL aceptar sólo tokens firmados con la clave de la configuración y con el algoritmo de la configuración. El algoritmo que declara el propio token no se tiene en cuenta: un token sin firma, con otro algoritmo, firmado con otra clave o alterado SHALL rechazarse como token inválido.

#### Scenario: T5 — Otra clave o contenido alterado
- **GIVEN** Dados un token firmado con otra clave y un token válido con el contenido modificado
- **WHEN** Cuando se validan
- **THEN** Entonces los dos se rechazan como token inválido

#### Scenario: T6 — Sin firma u otro algoritmo
- **GIVEN** Dados un token con algoritmo `none` y uno firmado con `HS512` y la misma clave
- **WHEN** Cuando se validan
- **THEN** Entonces los dos se rechazan como token inválido

### Requirement: Claims obligatorios y bien formados
La validación SHALL exigir `sub`, `iat` y `exp`, un `sub` que represente un id entero y unos `roles` que sean una lista. Lo que no cumpla, y lo que ni siquiera sea un token, SHALL rechazarse como el mismo error de dominio de token inválido, sin dejar escapar el error de la biblioteca.

#### Scenario: T7 — Claim faltante o mal formado
- **GIVEN** Dados tokens firmados correctamente, uno sin `sub`, uno sin `iat`, uno sin `exp`, uno con `sub` igual a `abc` y uno con `roles` que no es una lista
- **WHEN** Cuando se valida cada uno
- **THEN** Entonces cada uno se rechaza como token inválido

#### Scenario: T8 — No es un token
- **GIVEN** Dado el texto `no-es-un-token`
- **WHEN** Cuando se valida
- **THEN** Entonces se rechaza como token inválido
