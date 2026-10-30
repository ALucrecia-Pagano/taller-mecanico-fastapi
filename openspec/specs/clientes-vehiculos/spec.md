# clientes-vehiculos Specification

## Purpose

Permite administrar clientes y vehículos del taller con autorización por rol, baja lógica,
reutilización segura de patentes y consultas propias que excluyen vehículos dados de baja.

## Requirements

### Requirement: Alta de cliente
El sistema SHALL aceptar `POST /clientes` sólo con `RECEPCION` o `ADMIN`, crear un cliente con `nombre`, `documento` y `telefono`, quitar espacios de los bordes del documento y responder 201 sin datos internos. El recorte del documento es **[Alumna] — No especificado en la consigna**.

#### Scenario: Alta válida
- **GIVEN** Dado un usuario autenticado con rol vigente `RECEPCION` o `ADMIN` y un documento nuevo
- **WHEN** Cuando envía `POST /clientes` con `nombre`, `documento` y `telefono`
- **THEN** Entonces responde 201 con el cliente creado y sin `password_hash` ni campos internos

#### Scenario: Documento con espacios de borde
- **GIVEN** Dado un usuario autorizado y un documento nuevo
- **WHEN** Cuando envía el documento con espacios sólo en sus bordes
- **THEN** Entonces responde 201 y persiste el documento sin esos espacios

#### Scenario: Documento duplicado
- **GIVEN** Dado un cliente existente con el documento enviado
- **WHEN** Cuando un usuario autorizado intenta crear otro cliente
- **THEN** Entonces responde 409 con detail `Ya existe un cliente con ese documento` y no crea otra ficha

#### Scenario: Contrato inválido
- **GIVEN** Dado un usuario autorizado
- **WHEN** Cuando envía un campo no declarado o datos que no cumplen el contrato
- **THEN** Entonces responde 422 sin ejecutar la operación de alta

#### Scenario: Sin sesión o rol
- **GIVEN** Dado un usuario anónimo, o un usuario autenticado sin `RECEPCION` ni `ADMIN`
- **WHEN** Cuando envía una solicitud válida a `POST /clientes`
- **THEN** Entonces responde 401 sin sesión o 403 sin rol, respectivamente

### Requirement: Consulta de cliente con vehículos vigentes
`GET /clientes/{id}` SHALL devolver el cliente y sus vehículos vigentes ordenados por `id`; los vehículos con `borrado_en` no SHALL aparecer.

#### Scenario: Cliente con vehículos
- **GIVEN** Dado un cliente existente con vehículos vigentes y dados de baja
- **WHEN** Cuando un usuario `RECEPCION` o `ADMIN` consulta `GET /clientes/{id}`
- **THEN** Entonces responde 200 con el cliente y sólo los vehículos vigentes en orden ascendente de `id`

#### Scenario: Cliente inexistente
- **GIVEN** Dado un usuario autorizado
- **WHEN** Cuando consulta un `id` de cliente inexistente
- **THEN** Entonces responde 404 con un mensaje propio

#### Scenario: Parámetro inválido
- **GIVEN** Dado un usuario con rol de recepción vigente
- **WHEN** Cuando consulta `GET /clientes/no-entero`
- **THEN** Entonces responde 422 sin ejecutar el handler

#### Scenario: Sin permiso
- **GIVEN** Dado un usuario autenticado sin `RECEPCION` ni `ADMIN`
- **WHEN** Cuando consulta un cliente existente
- **THEN** Entonces responde 403 sin leer ni modificar los datos del cliente

### Requirement: Alta de vehículo y normalización
`POST /clientes/{id}/vehiculos` SHALL aceptar sólo `patente`, `marca`, `modelo` y `anio`, validar `anio` entre 1950 y 2100 y normalizar la patente a mayúsculas sin espacios. La normalización es **[Alumna] — No especificado en la consigna**.

#### Scenario: Alta válida
- **GIVEN** Dado un cliente existente y un usuario `RECEPCION` o `ADMIN`
- **WHEN** Cuando envía una patente válida y un año entre 1950 y 2100
- **THEN** Entonces responde 201 con el vehículo vigente guardado y su patente normalizada

#### Scenario: Cliente inexistente
- **GIVEN** Dado un usuario autorizado
- **WHEN** Cuando agrega un vehículo a un cliente inexistente
- **THEN** Entonces responde 404 con un mensaje propio

#### Scenario: Patente equivalente normalizada
- **GIVEN** Dado un vehículo vigente con patente `AC456EF`
- **WHEN** Cuando intenta registrar `ac 456 ef` para otro cliente
- **THEN** Entonces responde 409 con detail `Ya existe un vehículo vigente con esa patente`

#### Scenario: Patente reutilizable tras baja
- **GIVEN** Dado un vehículo dado de baja con patente `AC456EF`
- **WHEN** Cuando registra `ac 456 ef` para otro cliente
- **THEN** Entonces responde 201 y guarda la patente como `AC456EF`

#### Scenario: Año o campos inválidos
- **GIVEN** Dado un usuario autorizado
- **WHEN** Cuando envía `anio` menor que 1950, mayor que 2100 o un campo extra
- **THEN** Entonces responde 422 sin crear el vehículo

#### Scenario: Sin permiso
- **GIVEN** Dado un usuario autenticado sin `RECEPCION` ni `ADMIN`
- **WHEN** Cuando intenta agregar un vehículo
- **THEN** Entonces responde 403 sin crear filas

### Requirement: Baja lógica de vehículo
`DELETE /vehiculos/{id}` SHALL marcar `borrado_en` y responder 204 si el vehículo existe, está vigente y no tiene órdenes con `es_final = false`; SHALL responder 409 si tiene órdenes abiertas y 404 si no existe o ya fue dado de baja.

#### Scenario: Baja permitida
- **GIVEN** Dado un vehículo vigente sin órdenes abiertas y un usuario `RECEPCION` o `ADMIN`
- **WHEN** Cuando envía `DELETE /vehiculos/{id}`
- **THEN** Entonces responde 204, conserva la fila y deja de mostrar el vehículo en los listados

#### Scenario: Orden abierta
- **GIVEN** Dado un vehículo vigente con una orden cuyo estado tiene `es_final = false`
- **WHEN** Cuando un usuario autorizado intenta darlo de baja
- **THEN** Entonces responde 409 con detail `El vehículo tiene órdenes abiertas` y el vehículo permanece vigente

#### Scenario: Sólo órdenes finales
- **GIVEN** Dado un vehículo vigente cuyas órdenes están en estados finales
- **WHEN** Cuando un usuario autorizado intenta darlo de baja
- **THEN** Entonces responde 204

#### Scenario: Vehículo inexistente o ya dado de baja
- **GIVEN** Dado un identificador inexistente o de un vehículo con `borrado_en` no nulo
- **WHEN** Cuando se solicita DELETE
- **THEN** Entonces responde 404 sin modificar datos

#### Scenario: Sin permiso
- **GIVEN** Dado un usuario autenticado sin `RECEPCION` ni `ADMIN`
- **WHEN** Cuando intenta dar de baja un vehículo
- **THEN** Entonces responde 403 antes de ejecutar la baja

### Requirement: Consulta de vehículos propios
`GET /mis-vehiculos` SHALL requerir autenticación, devolver sólo los vehículos vigentes de la ficha vinculada al usuario y responder 200 con lista vacía si no existe ficha; la ruta SHALL permanecer dentro de `rutas_protegidas`.

#### Scenario: Usuario con ficha
- **GIVEN** Dado un usuario autenticado con una ficha que tiene dos vehículos vigentes y uno dado de baja
- **WHEN** Cuando consulta `GET /mis-vehiculos`
- **THEN** Entonces responde 200 con los dos vigentes ordenados por `id` y excluye el dado de baja

#### Scenario: Usuario sin ficha
- **GIVEN** Dado un usuario autenticado sin ficha de cliente
- **WHEN** Cuando consulta `GET /mis-vehiculos`
- **THEN** Entonces responde 200 con una lista vacía

#### Scenario: Cambio obligatorio pendiente
- **GIVEN** Dado un usuario autenticado cuya contraseña debe cambiarse
- **WHEN** Cuando consulta `GET /mis-vehiculos`
- **THEN** Entonces responde 403 con el mensaje vigente de cambio obligatorio

#### Scenario: Sin sesión
- **GIVEN** Dado un usuario sin cookie de sesión válida
- **WHEN** Cuando consulta `GET /mis-vehiculos`
- **THEN** Entonces responde 401

### Requirement: Lecturas sin consultas implícitas
Las respuestas que incluyen relaciones de cliente y vehículos SHALL obtener los vehículos vigentes con carga anticipada declarada y un número de consultas que no crezca con la cantidad de vehículos.

#### Scenario: Detalle sin N+1
- **GIVEN** Dado un cliente con varios vehículos vigentes
- **WHEN** Cuando se consulta su detalle o sus vehículos propios
- **THEN** Entonces la respuesta incluye todos los vehículos correctos sin lazy loading ni una consulta por vehículo

#### Scenario: Relaciones no cargadas
- **GIVEN** Dado un repositorio que devuelve una entidad sin la relación necesaria precargada
- **WHEN** Cuando el servicio intenta serializar una respuesta relacional
- **THEN** Entonces la implementación no depende de carga perezosa y la prueba detecta la ausencia de precarga
