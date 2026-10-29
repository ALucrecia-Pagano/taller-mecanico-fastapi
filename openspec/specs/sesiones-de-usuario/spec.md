# sesiones-de-usuario Specification

## Purpose

Permite iniciar y cerrar sesiones por cookie, consultar la identidad autenticada y cambiar la contraseña invalidando sesiones anteriores con precisión completa.

## Requirements

### Requirement: Login uniforme
POST /auth/login SHALL verificar credenciales tras el límite, responder 200 para activo válido y el mismo 401 para inexistente, clave mala o inactivo. Mensaje «Correo o contraseña incorrectos»: No especificado en la consigna.

#### Scenario: L1 — Activo válido
- **GIVEN** Dado un usuario activo con contraseña correcta
- **WHEN** Cuando inicia sesión
- **THEN** Entonces responde 200 con mensaje «Sesión iniciada», debe_cambiar_password y expira_en_segundos, y emite cookie sin token en JSON

#### Scenario: L2 — Clave mala
- **GIVEN** Dado un usuario activo
- **WHEN** Cuando inicia sesión con clave incorrecta
- **THEN** Entonces responde 401 con detail «Correo o contraseña incorrectos», registra fallo y no emite cookie

#### Scenario: L3 — Inexistente [Alumna]
- **GIVEN** Dado un email inexistente y el hash ficticio de arranque
- **WHEN** Cuando inicia sesión
- **THEN** Entonces se realiza exactamente una verificación contra ese hash, siempre se responde el mismo cuerpo 401 que L2 y se registra fallo; se comprueba con espía sin medir tiempos

#### Scenario: L4 — Inactivo con clave correcta [Alumna]
- **GIVEN** Dado un usuario inactivo
- **WHEN** Cuando envía contraseña correcta
- **THEN** Entonces verifica su hash real, registra exito=false y responde el mismo 401 sin cookie

#### Scenario: L5 — Inactivo con clave incorrecta [Alumna]
- **GIVEN** Dado un usuario inactivo
- **WHEN** Cuando envía contraseña incorrecta
- **THEN** Entonces verifica su hash real, registra exito=false y responde el mismo 401 sin cookie

#### Scenario: L6 — Roles informativos
- **GIVEN** Dado un usuario con roles vigentes, vencidos y revocados
- **WHEN** Cuando inicia sesión correctamente
- **THEN** Entonces el JWT firmado lleva sub, iat fraccionario, exp y sólo roles vigentes al emitir, ordenados e informativos

### Requirement: Cookie y cierre de sesión
El sistema SHALL transportar el JWT sólo en access_token HttpOnly, SameSite=Lax, Max-Age igual a duración y Secure configurable. Path=/ sin Domain: No especificado en la consigna. Logout público SHALL responder 200 y borrar esa cookie.

#### Scenario: K1 — Atributos y secreto
- **GIVEN** Dado un login exitoso
- **WHEN** Cuando se inspecciona respuesta
- **THEN** Entonces Set-Cookie tiene HttpOnly, SameSite=Lax, Max-Age=JWT_EXPIRE_SECONDS, Path=/ y no Domain; el cuerpo no contiene token ni hash

#### Scenario: K2 — Secure configurable
- **GIVEN** Dado configuraciones COOKIE_SECURE verdadera y falsa
- **WHEN** Cuando se inicia sesión en cada una
- **THEN** Entonces Secure está presente sólo en la primera

#### Scenario: K3 — Header no autentica
- **GIVEN** Dado una petición a /auth/yo sin cookie, con o sin Bearer válido
- **WHEN** Cuando se consulta
- **THEN** Entonces responde 401 con detail «Sesión no válida o vencida»

#### Scenario: K4 — Logout idempotente
- **GIVEN** Dado un cliente con cookie y otro sin cookie
- **WHEN** Cuando cada uno llama POST /auth/logout
- **THEN** Entonces ambos reciben 200 y eliminación de access_token con mismo alcance; no se agrega revocación de JWT en servidor

#### Scenario: K5 — Cookie y header
- **GIVEN** Dado una cookie válida y un header Authorization adicional
- **WHEN** Cuando se consulta /auth/yo
- **THEN** Entonces se autentica sólo por cookie y responde 200

### Requirement: Autenticación por cookie
La autenticación SHALL validar sólo cookie, token y usuario existente/activo. [Alumna] D6: todo rechazo de esta autenticación responde 401 con detail «Sesión no válida o vencida» (No especificado en la consigna). Las credenciales de login conservan su mensaje distinto.

#### Scenario: A1 — Cookie ausente
- **GIVEN** Dado una petición sin cookie
- **WHEN** Cuando se autentica
- **THEN** Entonces recibe el 401 neutro

#### Scenario: A2 — Token inválido
- **GIVEN** Dado cookies con texto inválido, firma alterada, vencimiento pasado, claims inválidos u otro algoritmo
- **WHEN** Cuando se autentica cada una
- **THEN** Entonces todas reciben el mismo 401 neutro sin detalle de biblioteca

#### Scenario: A3 — Usuario inexistente
- **GIVEN** Dado un JWT válido para un id no guardado
- **WHEN** Cuando se autentica
- **THEN** Entonces recibe el 401 neutro

#### Scenario: A4 — Usuario inactivo
- **GIVEN** Dado un JWT válido para usuario ahora inactivo
- **WHEN** Cuando se autentica
- **THEN** Entonces recibe el 401 neutro

### Requirement: Invalidación con precisión completa
El sistema SHALL rechazar una sesión si iat es estrictamente menor que la fecha completa del último cambio; igualdad o posterior SHALL seguir válidas. Sin fecha de cambio no aplica esta restricción.

#### Scenario: A5 — Antes del cambio
- **GIVEN** Dado un token con iat anterior a password_cambiada_en
- **WHEN** Cuando se consulta /auth/yo
- **THEN** Entonces responde el 401 neutro

#### Scenario: A6 — Igualdad
- **GIVEN** Dado un token cuyo iat coincide exactamente con password_cambiada_en.timestamp()
- **WHEN** Cuando se consulta /auth/yo
- **THEN** Entonces responde 200

#### Scenario: A7 — Posterior
- **GIVEN** Dado un token posterior al cambio o un usuario sin fecha de cambio
- **WHEN** Cuando se consulta /auth/yo
- **THEN** Entonces responde 200

#### Scenario: A8 — Mismo segundo
- **GIVEN** Dado un token anterior y uno nuevo emitidos dentro del segundo del cambio
- **WHEN** Cuando se prueba cada uno sin esperar
- **THEN** Entonces el anterior recibe 401 y el nuevo 200, conservando la fracción

### Requirement: Cambio atómico de contraseña
POST /auth/cambiar-password SHALL requerir autenticación propia en grupo abierto, verificar actual y guardar hash nuevo, fecha completa, bandera falsa y evento «Cambio de contraseña» con actor=email en una transacción. Sólo tras confirmar SHALL emitir cookie nueva con roles vigentes e iat no anterior al cambio.

#### Scenario: P1 — Cambio correcto
- **GIVEN** Dado un usuario autenticado con contraseña actual correcta y nueva distinta
- **WHEN** Cuando cambia contraseña
- **THEN** Entonces responde 200; hash, fecha y bandera cambian juntos, otra sesión ve el evento y sólo la nueva contraseña verifica

#### Scenario: P2 — Actual incorrecta
- **GIVEN** Dado un usuario autenticado y snapshot previo
- **WHEN** Cuando envía actual incorrecta y nueva distinta
- **THEN** Entonces recibe 401, sin modificar hash/fecha/bandera/eventos ni renovar cookie

#### Scenario: P4 — Fallo transaccional
- **GIVEN** Dado un cambio con escrituras en curso
- **WHEN** Cuando falla antes de confirmar
- **THEN** Entonces se revierte hash/fecha/bandera y evento y no se emite cookie nueva

#### Scenario: P5 — Renovación inmediata
- **GIVEN** Dado un usuario que cambia contraseña dentro del mismo segundo del login
- **WHEN** Cuando usa cookie nueva y anterior
- **THEN** Entonces la nueva obtiene 200 y la anterior 401 sin sleeps

### Requirement: Perfil autenticado
GET /auth/yo SHALL devolver exactamente id, email, nombre, debe_cambiar_password, roles_vigentes y roles_token; roles actuales desde la base y los otros del JWT, ordenados. /yo y cambio SHALL funcionar con cambio pendiente y sin control de roles.

#### Scenario: Y1 — Forma DA-16
- **GIVEN** Dado un usuario autenticado
- **WHEN** Cuando consulta /auth/yo
- **THEN** Entonces recibe los seis campos DA-16, sin hash ni token completo

#### Scenario: Y2 — Roles divergentes
- **GIVEN** Dado una cookie emitida antes de revocación o vencimiento de un rol
- **WHEN** Cuando consulta /auth/yo tras modificar los datos de vigencia
- **THEN** Entonces roles_vigentes refleja la base y roles_token conserva los emitidos; no se autorizan permisos con éstos

#### Scenario: Y3 — Cambio pendiente
- **GIVEN** Dado un usuario autenticado con debe_cambiar_password=true
- **WHEN** Cuando consulta /yo y luego cambia su contraseña por una distinta
- **THEN** Entonces ambas operaciones están disponibles, sin el bloqueo reservado al grupo protegido de CH-06


