# autorizacion Specification

## Purpose

Define permisos desde los roles actuales de la base y el bloqueo transversal por cambio obligatorio sin impedir autenticación o salud.

## Requirements

### Requirement: Permisos efectivos por petición
El sistema SHALL autorizar con roles vigentes de base en cada petición, no con roles del token. Una asignación vigente tiene revocada_en nula y vence_en nulo o estrictamente futuro; cualquiera de los roles requeridos sirve, sin privilegio ADMIN implícito.

#### Scenario: AU1 — Rol actual permitido
- **GIVEN** Dado ADMIN vigente con cookie válida
- **WHEN** Cuando consulta cada endpoint administrativo
- **THEN** Entonces obtiene su respuesta exitosa sin usar roles_token para decidir

#### Scenario: AU2 — Revocación con sesión abierta
- **GIVEN** Dado cookie emitida con ADMIN y rol luego revocado
- **WHEN** Cuando reutiliza la misma cookie en /eventos y /auth/yo
- **THEN** Entonces /eventos da 403; /auth/yo da 200 mostrando roles_vigentes sin ADMIN y roles_token con ADMIN

#### Scenario: AU3 — Alta de rol tras login
- **GIVEN** Dado cookie emitida sin ADMIN y asignación ADMIN nueva vigente
- **WHEN** Cuando consulta /eventos sin volver a iniciar sesión
- **THEN** Entonces accede 200

#### Scenario: AU4 — Vencimiento y borde
- **GIVEN** Dado asignación con vence_en pasado o exactamente ahora
- **WHEN** Cuando solicita ruta que exige ese rol
- **THEN** Entonces recibe 403, igual que rol revocado

#### Scenario: AU5 — Roles alternativos y sin bypass
- **GIVEN** Dado ruta de prueba exige RECEPCION o MECANICO y actores con uno de ellos o sólo ADMIN
- **WHEN** Cuando intenta cada acceso
- **THEN** Entonces RECEPCION y MECANICO acceden, ADMIN solo recibe 403

### Requirement: Distinción de autenticación y permiso
Toda ruta administrativa SHALL responder 401 D6 sin sesión válida y 403 sin ADMIN vigente. El 403 por rol SHALL usar detail «No tiene permisos para realizar esta operación» [Alumna D4, No especificado en la consigna].

#### Scenario: AU6 — Sin sesión antes del permiso
- **GIVEN** Dado cada ruta administrativa y ausencia de cookie o ******
- **WHEN** Cuando envía una solicitud válida
- **THEN** Entonces recibe 401 con detail Sesión no válida o vencida sin escritura

#### Scenario: AU7 — Sesión sin ADMIN
- **GIVEN** Dado cliente o mecánico autenticado sin cambio pendiente
- **WHEN** Cuando solicita cada ruta administrativa
- **THEN** Entonces recibe 403 con detail No tiene permisos para realizar esta operación antes de ejecutar negocio

### Requirement: Bloqueo por cambio obligatorio
Toda ruta protegida SHALL rechazar con 403 detail «Debe cambiar la contraseña para continuar» mientras la bandera esté pendiente. Salud y /auth SHALL quedar fuera del control, conservando autenticación propia de /yo y /cambiar-password.

#### Scenario: AU8 — Control transversal único
- **GIVEN** Dado usuario autenticado con cambio pendiente
- **WHEN** Cuando solicita las cinco rutas CH-06 y ruta protegida sólo autenticada de prueba
- **THEN** Entonces todas rechazan 403 sin escrituras por cambio obligatorio

#### Scenario: AU9 — Excepciones abiertas
- **GIVEN** Dado usuario con cambio pendiente
- **WHEN** Cuando consulta salud y /auth/yo y cambia su contraseña correctamente
- **THEN** Entonces salud conserva 200/503; /yo y cambio son accesibles y dan 200

#### Scenario: AU10 — Igualdad no desactiva obligación
- **GIVEN** Dado usuario con cambio pendiente
- **WHEN** Cuando envía claves actual y nueva iguales
- **THEN** Entonces recibe 422; bandera y hash siguen y protegido sigue 403 sin evento

#### Scenario: AU11 — Cookie renovada desbloquea
- **GIVEN** Dado personal ADMIN con cambio pendiente
- **WHEN** Cuando cambia contraseña y prueba cookie nueva y anterior sin esperar
- **THEN** Entonces la nueva accede /eventos 200 y la anterior da 401 aun dentro del mismo segundo

#### Scenario: AU12 — C09 no inventa privilegios
- **GIVEN** Dado nuevo@example.com MECANICO con cambio pendiente
- **WHEN** Cuando cambia contraseña y usa nueva cookie en /auth/yo y /eventos
- **THEN** Entonces /yo da 200 y /eventos sigue 403 por falta ADMIN; cookie anterior da 401
