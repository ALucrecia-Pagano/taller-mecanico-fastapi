# administracion-de-usuarios Specification

## Purpose

Administra altas de personal, asignaciones vigentes e historial conservado, con autoprotección de administradores y mutaciones atómicas auditadas.

## Requirements

### Requirement: Alta atómica de personal
POST /usuarios SHALL aceptar {email,nombre,password_provisoria,rol}, crear usuario activo con cambio pendiente, asignación sin vencimiento otorgada_por=actor y un evento en una transacción; responder 201 con {id,email,nombre,activo,debe_cambiar_password}, sin contraseña/hash. [Alumna D4: respuesta No especificado en la consigna].

#### Scenario: PE1 — Tres roles de personal
- **GIVEN** Dado ADMIN autorizado y alta para cada rol ADMIN,RECEPCION,MECANICO
- **WHEN** Cuando crea personal
- **THEN** Entonces cada alta da 201, activo=true, debe_cambiar_password=true, autoría correcta y exactamente un evento Alta de personal <email>

#### Scenario: PE2 — Correo repetido
- **GIVEN** Dado correo existente y snapshot de filas
- **WHEN** Cuando intenta alta repetida
- **THEN** Entonces recibe 409 El correo ya está registrado sin usuario, asignación ni evento nuevos

#### Scenario: PE3 — Atomicidad de alta
- **GIVEN** Dado alta con escrituras parciales
- **WHEN** Cuando falla antes de confirmar incluso al guardar evento
- **THEN** Entonces ninguna de las tres filas queda; otra sesión conserva estado previo

### Requirement: Contratos administrativos estrictos
Las entradas SHALL rechazar extras y CLIENTE u otro rol fuera ADMIN/RECEPCION/MECANICO con 422 tanto en alta como asignación [Alumna D1=B, No especificado en la consigna para asignación]. password_provisoria SHALL usar el contrato de contraseña vigente.

#### Scenario: PE4 — CLIENTE y desconocido
- **GIVEN** Dado alta o asignación autenticada
- **WHEN** Cuando envía CLIENTE o JEFE
- **THEN** Entonces recibe 422 sin ninguna escritura

#### Scenario: PE5 — Campos extras
- **GIVEN** Dado entrada de alta o asignación válida
- **WHEN** Cuando agrega activo,otorgada_por u otro campo no declarado
- **THEN** Entonces recibe 422 sin ejecutar operación

#### Scenario: PE6 — Longitud de contraseña
- **GIVEN** Dado alta con 72 o 73 bytes ASCII o UTF-8
- **WHEN** Cuando valida password_provisoria
- **THEN** Entonces 72 se acepta y 73 da 422 antes de bcrypt

#### Scenario: PE7 — Vacío y NUL
- **GIVEN** Dado alta válida salvo contraseña
- **WHEN** Cuando envía cadena vacía o con NUL
- **THEN** Entonces recibe 422 sin bcrypt ni escrituras

### Requirement: Asignación y vigencia
POST /usuarios/{id}/roles SHALL aceptar rol de personal y vence_en opcional/null; fecha presente SHALL tener zona y ser estrictamente futura o responder 422. Usuario inexistente SHALL dar 404. Una asignación exitosa SHALL responder 201 y registrar autoría/evento atómicamente.

#### Scenario: RO1 — Vencimiento opcional
- **GIVEN** Dado usuario existente
- **WHEN** Cuando asigna rol con fecha futura zonificada, campo omitido o null
- **THEN** Entonces recibe 201 con vigencia true y fecha del mismo instante o null

#### Scenario: RO2 — Vencimientos inválidos
- **GIVEN** Dado usuario existente
- **WHEN** Cuando envía fecha sin zona, pasada o igual al instante actual
- **THEN** Entonces recibe 422 sin nueva asignación ni evento

#### Scenario: RO3 — Usuario inexistente
- **GIVEN** Dado id no registrado
- **WHEN** Cuando consulta historial, asigna o revoca rol
- **THEN** Entonces cada operación da 404 Usuario no encontrado sin escrituras

#### Scenario: RO4 — Duplicado vigente
- **GIVEN** Dado asignación abierta vigente
- **WHEN** Cuando asigna mismo rol
- **THEN** Entonces recibe 409 El usuario ya tiene ese rol vigente sin segundo evento

#### Scenario: RO5 — Reasignación vencida
- **GIVEN** Dado fila abierta vencida del mismo rol
- **WHEN** Cuando asigna rol nuevamente
- **THEN** Entonces recibe 201; anterior queda con revocada_en y su otorgada_por original; nueva tiene otro id y actor otorgante, con un solo evento Asignación

#### Scenario: RO6 — Nueva tras revocación
- **GIVEN** Dado fila previa revocada
- **WHEN** Cuando asigna mismo rol
- **THEN** Entonces recibe 201 y conserva fila antigua intacta

#### Scenario: RO7 — Rollback reasignación
- **GIVEN** Dado fila abierta vencida y snapshot
- **WHEN** Cuando falla después del cierre o inserción y antes del commit
- **THEN** Entonces fila vieja queda abierta como antes y no quedan nueva fila ni evento

### Requirement: Revocación conservando historial
DELETE /usuarios/{id}/roles/{rol} SHALL responder 200 con la asignación cerrada, escribir revocada_en y evento en una transacción sin borrar ni cambiar otorgada_por. Ausencia de fila abierta SHALL dar 404 «No hay una asignación abierta de ese rol» [Alumna D2=A, No especificado en la consigna].

#### Scenario: RV1 — Revocación vigente
- **GIVEN** Dado asignación abierta de rol no ADMIN
- **WHEN** Cuando revoca autorizado
- **THEN** Entonces recibe 200, vigente=false; fila/id/otorgada_por se conservan y queda un evento

#### Scenario: RV2 — Ausencia abierta
- **GIVEN** Dado usuario existente sin rol o sólo con filas revocadas
- **WHEN** Cuando revoca ese rol
- **THEN** Entonces recibe 404 No hay una asignación abierta de ese rol sin evento

#### Scenario: RV3 — Cierre vencido
- **GIVEN** Dado asignación abierta vencida
- **WHEN** Cuando revoca
- **THEN** Entonces recibe 200 con revocada_en y un evento; no borra la fila

#### Scenario: RV4 — Rollback revocación
- **GIVEN** Dado asignación abierta
- **WHEN** Cuando falla antes de confirmar el evento
- **THEN** Entonces fila conserva revocada_en anterior y no queda evento

### Requirement: Historial completo y respuesta de asignación
GET /usuarios/{id}/roles SHALL devolver lista simple de todas las asignaciones ordenada por desde,id ascendente, con {id,usuario_id,rol,desde,vence_en,revocada_en,otorgada_por,vigente}. POST y DELETE roles SHALL devolver ese objeto. vigente SHALL calcularse con el instante de consulta. [Alumna D4, orden/formato No especificado en la consigna].

#### Scenario: HI1 — Historial mixto
- **GIVEN** Dado filas vigentes, vencidas y revocadas incluso CLIENTE histórico
- **WHEN** Cuando consulta historial
- **THEN** Entonces ve todas en orden, fechas con zona y vigente correcto sin hash ni contraseñas

#### Scenario: HI2 — Historial vacío y borde
- **GIVEN** Dado usuario existente sin asignaciones y otro con vence_en exactamente ahora
- **WHEN** Cuando consulta ambos
- **THEN** Entonces primero devuelve [] y segundo muestra vigente=false

### Requirement: Autoprotección ADMIN
Revocar ADMIN propio SHALL dar 409 «No puede revocarse su propio rol ADMIN»; dejar cero ADMIN vigentes SHALL dar 409 «No puede dejar el sistema sin administradores vigentes». El vencimiento temporal SHALL conservar la excepción DA-15/SU-11, sin prevenir cero por el paso del tiempo.

#### Scenario: AD1 — Autorrevo con respaldo
- **GIVEN** Dado dos administradores vigentes
- **WHEN** Cuando uno revoca su propio ADMIN
- **THEN** Entonces recibe 409 de autorrevocación sin fila modificada ni evento

#### Scenario: AD2 — Último administrador
- **GIVEN** Dado único ADMIN vigente y otros vencidos/revocados
- **WHEN** Cuando servicio evalúa revocación de ese último rol por actor distinto autorizado en el contexto del caso
- **THEN** Entonces rechaza 409 de último administrador sin escritura

#### Scenario: AD3 — Revocar otro con respaldo
- **GIVEN** Dado dos admins vigentes
- **WHEN** Cuando uno revoca al otro
- **THEN** Entonces recibe 200 y queda su ADMIN vigente

#### Scenario: AD4 — Expiración admitida
- **GIVEN** Dado últimas asignaciones ADMIN con vencimiento futuro
- **WHEN** Cuando transcurre su vencimiento
- **THEN** Entonces pueden quedar cero por tiempo; no hay evento de revocación automática ni tarea nueva

### Requirement: Autoprotección frente a operaciones concurrentes
Las mutaciones ADMIN SHALL serializar su decisión y revalidar el ADMIN vigente del actor después de esperar. Dos administradores que se revocan mutuamente SHALL producir un éxito y un 403 al actor ya sin rol, nunca dos éxitos dejando cero. [Alumna D3=A, No especificado en la consigna].

#### Scenario: CO1 — Revocaciones cruzadas
- **GIVEN** Dado dos sesiones y dos ADMIN vigentes
- **WHEN** Cuando cada uno intenta revocar al otro simultáneamente
- **THEN** Entonces exactamente una operación da 200, la otra 403; queda un ADMIN y un evento

#### Scenario: CO2 — Actor pierde permiso esperando
- **GIVEN** Dado actor pasó autenticación y espera una mutación ADMIN
- **WHEN** Cuando su ADMIN es revocado antes de continuar
- **THEN** Entonces operación pendiente relee base y da 403 sin mutación ni evento aun si token/objeto previo decía ADMIN

#### Scenario: CO3 — Alta y asignación bajo coordinación
- **GIVEN** Dado alta de ADMIN o asignación/reasignación ADMIN esperando y actor pierde permiso
- **WHEN** Cuando continúa operación tras la espera
- **THEN** Entonces revalida rol antes de escribir y rechaza 403 sin filas/evento

#### Scenario: CO4 — Rollback libera coordinación
- **GIVEN** Dado primera operación ADMIN falla y segunda está esperando
- **WHEN** Cuando primera revierte y segunda continúa
- **THEN** Entonces segunda puede completar con datos vigentes, sin bloqueo retenido ni evento parcial
