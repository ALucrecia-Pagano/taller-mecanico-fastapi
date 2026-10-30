# Spec Delta

## Purpose

Permite registrar y consultar órdenes de trabajo preservando sus precios, su historial y la privacidad de las órdenes propias, con consultas cuyo costo no crece por cada ítem.

## ADDED Requirements

### Requirement: Contrato del alta
POST /ordenes SHALL aceptar sólo vehiculo_id, falla e items con repuesto_id y cantidad entera positiva. SHALL exigir al menos un ítem y rechazar repetidos y extras con 422 (RN-10, DA-19). No SHALL aceptar precio, total, estado, fecha ni mecánico.

#### Scenario: E03 — Entradas inválidas
- **GIVEN** Dado personal autorizado y datos de alta
- **WHEN** Cuando envía items vacíos, cantidad cero/negativa/fraccionaria, un campo requerido ausente o un repuesto repetido
- **THEN** Entonces responde 422 sin nuevas órdenes, ítems ni historial

#### Scenario: E04 — Campos controlados por servidor
- **GIVEN** Dado un alta válida
- **WHEN** Cuando agrega precio, total, estado, fecha, mecánico o cualquier extra, también dentro de un ítem
- **THEN** Entonces responde 422 sin escrituras

### Requirement: Alta atómica pendiente
El sistema SHALL crear PENDIENTE sin mecánico, copiar cada precio vigente, calcular total Decimal y agregar ítems e historial null→PENDIENTE con actor autenticado en una única transacción. SHALL responder 201 con el detalle sólo si confirma. Crear no SHALL reservar ni descontar stock.

#### Scenario: E01 — C-10 ejemplo literal
- **GIVEN** Dado el seed limpio y RECEPCION id 3
- **WHEN** Cuando crea vehículo 2 con repuesto 2 cantidad 1 y repuesto 4 cantidad 3
- **THEN** Entonces crea orden 3 PENDIENTE, total "68000.00", patente AC456EF, cliente Laura Cliente, mecánico null y una línea inicial con actor 3
- **AND** precios "32000.00" y "12000.00", subtotales "32000.00" y "36000.00", fechas con zona

#### Scenario: E02 — Altas de administrador
- **GIVEN** Dado ADMIN y vehículo ajeno vigente
- **WHEN** Cuando crea una orden de un ítem y otra de cuatro repuestos distintos
- **THEN** Entonces ambas responden 201 con precios copiados, sin exigir pertenencia

#### Scenario: E09 — Cantidad mayor al stock
- **GIVEN** Dado repuesto con stock menor a la cantidad, incluso cero
- **WHEN** Cuando crea una orden válida con él
- **THEN** Entonces responde 201 sin alterar stock ni movimientos

#### Scenario: E10 — Fallo después de escribir o al confirmar
- **GIVEN** Dada una operación que ya envió orden e ítems a la base
- **WHEN** Cuando falla el historial o una restricción al confirmar
- **THEN** Entonces revierte todas las escrituras, otra sesión no ve filas nuevas y el error de integridad se traduce a 409 propio sin texto SQL

### Requirement: Referencias disponibles
El alta SHALL rechazar vehículo o repuesto inexistente/dado de baja con 409 (tabla POST: 201/409/422, sin 404), y catálogo vacío con 409. [Agente] No especificado en la consigna: catálogo parcial sin PENDIENTE también SHALL dar 409, sin reparación automática.

#### Scenario: E05 — Referencia inexistente
- **GIVEN** Dada alta con dos ítems
- **WHEN** Cuando uno de los repuestos o el vehículo no existe
- **THEN** Entonces responde 409 sin orden, ítems, historial ni cambios de stock

#### Scenario: E06 — Referencia de baja
- **GIVEN** Dado vehículo o repuesto dado de baja
- **WHEN** Cuando intenta usar su id en un alta, aunque su patente/código haya sido reutilizado
- **THEN** Entonces responde 409 y no crea nada

#### Scenario: E07 — Catálogo vacío o parcial
- **GIVEN** Dado catálogo vacío o con filas pero sin PENDIENTE
- **WHEN** Cuando intenta crear una orden
- **THEN** Entonces responde 409 con mensaje propio sin crear ni reparar filas

### Requirement: Dinero exacto e histórico
Precios, subtotales y total SHALL serializarse como strings decimales de dos posiciones y conservarse tras cambios de precio. [Agente] No especificado en la consigna: total mayor a NUMERIC(12,2), 9999999999.99, SHALL dar 409 antes de persistir, sin truncar ni agregar límites arbitrarios.

#### Scenario: E08 — Centavos y límite almacenable
- **GIVEN** Dados precios de centavos y cantidades múltiples
- **WHEN** Cuando calcula total ordinario, total exacto 9999999999.99 y uno superior
- **THEN** Entonces conserva exactitud; acepta máximo y rechaza exceso 409 sin escrituras

#### Scenario: E11 — Precio congelado
- **GIVEN** Dada una orden creada y un precio de repuesto luego modificado por la operación válida
- **WHEN** Cuando consulta la orden y crea otra
- **THEN** Entonces la anterior conserva precio/subtotal/total y la nueva usa el precio actualizado

### Requirement: Autenticación y roles actuales
Las cinco rutas SHALL pertenecer al grupo protegido: sin cookie 401 y con cambio pendiente 403. POST SHALL exigir RECEPCION o ADMIN; GET general ADMIN/RECEPCION/MECANICO. Roles SHALL consultarse en base en cada petición.

#### Scenario: E12 — C-06 sesión y cambio obligatorio
- **GIVEN** Dadas las cinco rutas y una petición válida
- **WHEN** Cuando falta cookie, sólo hay Bearer o el usuario tiene cambio pendiente
- **THEN** Entonces cada ruta responde 401, 401 y 403 respectivamente

#### Scenario: E13 — Permisos del personal
- **GIVEN** Dados cliente, mecánico, recepción y administrador
- **WHEN** Cuando cliente intenta POST/GET general, mecánico intenta POST, recepción/ADMIN crean y los tres roles de personal listan
- **THEN** Entonces los primeros tres accesos dan 403 y los permitidos 201/200
- **AND** un rol revocado o vencido no autoriza aunque esté en el token

### Requirement: Detalle y propiedad
GET /ordenes/{id} SHALL permitir personal vigente o dueño identificado por cliente.usuario_id, sin exigir CLIENTE. Inexistente SHALL dar 404 y ajena existente 403. SHALL devolver formato del ejemplo con ítems e historial, sin hashes. [Agente] No especificado en la consigna: ítems por id e historial por (cuando,id) ascendentes.

#### Scenario: E14 — C-06 propio ajeno inexistente
- **GIVEN** Dado seed y usuario Laura, personal y usuario sin ficha
- **WHEN** Cuando Laura consulta órdenes 1/2, personal ambas, usuario sin ficha una ajena e id inexistente
- **THEN** Entonces da 200/403, 200/200, 403 y 404 respectivamente

#### Scenario: E20 — Desempate del historial
- **GIVEN** Dada orden 2 con dos líneas de igual cuando
- **WHEN** Cuando consulta el detalle
- **THEN** Entonces null→PENDIENTE precede PENDIENTE→EN_REPARACION sin modificar filas ni exponer ids internos de historial

### Requirement: Consulta con costo fijo y bajas históricas
El detalle SHALL precargar vehículo, cliente, ítems, sus repuestos e historial sin carga perezosa ni N+1. SHALL conservar referencias históricas de baja. [Agente] No especificado en la consigna: objetivo tres SELECT de dominio; la evidencia SHALL registrar SQL real y comparar ámbitos iguales.

#### Scenario: E19 — C-15 dos y cuatro ítems
- **GIVEN** Dadas órdenes reales de dos y cuatro ítems y sesiones nuevas del mismo actor
- **WHEN** Cuando consulta y serializa ambos detalles
- **THEN** Entonces ejecuta igual cantidad de consultas, sin SQL por cada ítem ni durante serialización; guarda SQL real y conteos, distinguiendo autenticación del dominio

#### Scenario: E21 — Históricos tras baja
- **GIVEN** Dado repuesto de baja de orden existente y vehículo de baja de orden finalizada
- **WHEN** Cuando consulta detalle, listado y mis-ordenes
- **THEN** Entonces conserva referencias, precios y pertenencia; nuevas altas con esos ids dan 409

### Requirement: Listados paginados
GET /ordenes SHALL aceptar estado opcional del enum y paginación común. MECANICO SHALL ver todas las coincidentes (DA-24). /mis-ordenes SHALL filtrar por usuario propietario sin exigir CLIENTE; sin ficha devolver envoltorio vacío (DA-14). [Agente] No especificado en la consigna: resumen sin colecciones, ocho campos del explore, orden id ascendente.

#### Scenario: E15 — Propias con y sin ficha
- **GIVEN** Dados Laura, personal sin ficha y autenticado con ficha sin rol CLIENTE
- **WHEN** Cuando consultan mis-ordenes
- **THEN** Entonces devuelve sólo propias a Laura y al último, y envoltorio vacío al personal sin ficha

#### Scenario: E16 — Páginas y vacío
- **GIVEN** Dado listado de órdenes o propias
- **WHEN** Cuando pide defaults, size 1/100, última página, page 0, size 0/500, página inexistente y conjunto vacío
- **THEN** Entonces aplica envoltorio común y count coherente; inválidas 422; vacío page1 válido con pages1 y page2 da422

#### Scenario: E17 — C-17 filtro y mecánico
- **GIVEN** Dado MECANICO y órdenes con distintas asignaciones
- **WHEN** Cuando lista sin filtro o por PENDIENTE/EN_REPARACION, o estado XYZ/vacío explícito
- **THEN** Entonces ve todas las coincidentes sin filtrar asignación y count idéntico; valores inválidos dan422

### Requirement: Catálogo y superficie limitada
GET /estados-orden SHALL devolver lista simple de codigo, descripcion, posicion y es_final por posición a cualquier autenticado. No SHALL existir escritura pública de catálogo ni historial ni transiciones CH-10. [Agente] No especificado en la consigna: catálogo vacío SHALL devolver 200 con [].

#### Scenario: E18 — C-17 catálogo
- **GIVEN** Dado catálogo del seed o vacío
- **WHEN** Cuando lo consulta autenticado y sin sesión
- **THEN** Entonces autenticado obtiene cuatro filas ordenadas, TERMINADA/CANCELADA finales, o []; sin sesión da401

#### Scenario: E22 — Rutas y traducción
- **GIVEN** Dada app con CH-09
- **WHEN** Cuando recorre rutas, prueba escrituras no declaradas e id no entero autenticado
- **THEN** Entonces hay cinco operaciones previstas protegidas con traducción por router; no CRUD appendOnly/catálogo; id no entero422 y errores sin texto interno
