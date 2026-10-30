# Spec Delta

## Purpose

Conserva eventos de seguridad con autor humano identificable y permite su lectura paginada sólo a administradores vigentes sin auditar operaciones fallidas.

## ADDED Requirements

### Requirement: Eventos exactos y atómicos
El sistema SHALL guardar actor=email de quien opera y accion DA-13 en la misma transacción exitosa: Alta de personal <email>, Asignación de rol <ROL> a <email>, Revocación de rol <ROL> a <email>. SISTEMA SHALL quedar sólo para seed; registro/cambio de contraseña conservan CH-05.

#### Scenario: EV1 — Autor y texto
- **GIVEN** Dado ADMIN distinto del destinatario
- **WHEN** Cuando crea personal, asigna y revoca roles
- **THEN** Entonces cada operación deja un evento con email actor y texto exacto del destinatario; alta no agrega evento Asignación adicional

#### Scenario: EV2 — Reasignación técnica
- **GIVEN** Dado rol abierto vencido
- **WHEN** Cuando reasigna
- **THEN** Entonces queda sólo Asignación de rol <ROL> a <email>, sin evento por cierre técnico

#### Scenario: EV3 — Fallo no auditado
- **GIVEN** Dado snapshot de eventos
- **WHEN** Cuando ocurre 401,403,404,409,422 o rollback de mutación
- **THEN** Entonces no se agrega ningún evento de esa operación

#### Scenario: EV4 — Compatibilidad CH05
- **GIVEN** Dado registro, cambio de contraseña y seed
- **WHEN** Cuando consulta eventos tras sus operaciones exitosas
- **THEN** Entonces conserva Registro de cliente <email>, Cambio de contraseña y Carga de los datos iniciales con su actor original, sin duplicados

#### Scenario: EV5 — Lecturas y sesiones
- **GIVEN** Dado eventos previos
- **WHEN** Cuando lee endpoints, inicia o cierra sesión
- **THEN** Entonces no agrega evento_seguridad; intento_acceso conserva comportamiento separado

### Requirement: Listado administrativo paginado
GET /eventos SHALL exigir ADMIN y devolver {items,total,page,size,pages}, con items {id,cuando,actor,accion}, fechas con zona, orden cuando,id descendente. page inicia 1, size 1..100 default20; página inexistente da 422 y vacío una página. Orden/campos [Alumna D4], No especificado en la consigna.

#### Scenario: EV6 — Páginas reproducibles
- **GIVEN** Dado más de veinte eventos incluyendo tiempos empatados
- **WHEN** Cuando consulta primera y segunda página
- **THEN** Entonces devuelve orden estable con id desempate, total correcto y sin hashes/contraseñas

#### Scenario: EV7 — Vacío
- **GIVEN** Dado sin eventos
- **WHEN** Cuando consulta page=1
- **THEN** Entonces recibe items=[],total=0,page=1,size=20,pages=1

#### Scenario: EV8 — Parámetros inválidos
- **GIVEN** Dado eventos conocidos
- **WHEN** Cuando pide page=0,size=0,size=101 o página posterior a última
- **THEN** Entonces recibe 422 con mensaje propio para página inexistente

#### Scenario: EV9 — Tamaños límite
- **GIVEN** Dado eventos conocidos
- **WHEN** Cuando consulta size=1 y size=100
- **THEN** Entonces ambos válidos conservan envoltorio y total correcto

