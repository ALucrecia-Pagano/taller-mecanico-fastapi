# repuestos-stock-precios Specification

## Purpose
Provee la gestión autenticada de repuestos del taller, manteniendo stock, movimientos
append-only e historial de precios consistentes y utilizables por las órdenes.

## Requirements

### Requirement: Endpoints y roles de repuestos
El sistema SHALL exponer sólo los ocho endpoints de repuestos de la consigna con los roles indicados y dentro de rutas protegidas.

#### Scenario: Lectura con rol permitido
- **WHEN** ADMIN, RECEPCION o MECANICO consulta el listado o detalle de repuestos
- **THEN** recibe 200 y los datos visibles del recurso

#### Scenario: Escritura sólo ADMIN
- **WHEN** RECEPCION intenta alta, PATCH, baja, reposición o consultar movimientos/precios
- **THEN** recibe 403

#### Scenario: Sin sesión o cambio obligatorio
- **WHEN** una petición llega sin sesión, con Authorization Bearer o con cambio de contraseña pendiente
- **THEN** recibe 401 en el primer caso y 403 en el segundo

### Requirement: Alta de repuesto y stock inicial
`POST /repuestos` SHALL aceptar código, descripción, precio y `stock_inicial` entero no negativo, crear el recurso y registrar stock inicial positivo atómicamente.

#### Scenario: Alta con stock positivo
- **WHEN** ADMIN crea un código vigente con precio positivo y `stock_inicial > 0`
- **THEN** recibe 201, el stock coincide con la cantidad y existe un movimiento positivo `"Stock inicial"`

#### Scenario: Alta con stock cero
- **WHEN** ADMIN crea un repuesto con `stock_inicial = 0`
- **THEN** recibe 201 y no existe movimiento de cantidad cero

#### Scenario: Stock inicial negativo
- **WHEN** el cuerpo contiene `stock_inicial < 0`
- **THEN** recibe 422 y no se crea el repuesto

#### Scenario: Código vigente repetido
- **WHEN** el código ya pertenece a un repuesto vigente
- **THEN** recibe 409 con `"Ya existe un repuesto vigente con ese código"` y no deja filas sueltas

### Requirement: Listado y búsqueda paginada
`GET /repuestos` SHALL excluir bajas, ordenar por id, aceptar `q` con `ILIKE` y devolver total calculado con el mismo filtro.

#### Scenario: Búsqueda filtrada
- **WHEN** se consulta `q=freno&size=1`
- **THEN** el total es 1, pages es 1 y el resultado contiene el repuesto coincidente

#### Scenario: Búsqueda no inyectable
- **WHEN** se consulta `q=' OR '1'='1`
- **THEN** recibe una lista vacía con total 0

#### Scenario: Página inexistente o tamaño inválido
- **WHEN** se pide `page=2` para un filtro de una página o `size=500`
- **THEN** recibe 422

#### Scenario: Bajas excluidas
- **WHEN** un repuesto tiene `borrado_en`
- **THEN** no aparece en listado, búsqueda ni detalle público

### Requirement: Modificación parcial y precio
`PATCH /repuestos/{id}` SHALL aceptar sólo descripción y precio, aplicar únicamente campos enviados y registrar historial cuando el precio cambia.

#### Scenario: PATCH parcial
- **WHEN** ADMIN envía sólo una descripción válida
- **THEN** cambia la descripción y conserva precio y stock

#### Scenario: Precio distinto
- **WHEN** ADMIN envía un precio positivo distinto del actual
- **THEN** cambia el precio y agrega una línea con precio anterior, nuevo y usuario_id

#### Scenario: Precio igual o PATCH vacío
- **WHEN** el precio nuevo coincide con el actual o no se envía ningún campo modificable
- **THEN** recibe 422, conserva el repuesto y no agrega historial

#### Scenario: Stock o extras
- **WHEN** el cuerpo intenta modificar stock o contiene un campo no declarado
- **THEN** recibe 422

#### Scenario: Fallo al escribir historial
- **WHEN** falla la escritura del historial después de un cambio de precio
- **THEN** todo el UoW se revierte y recibe 409 genérico

### Requirement: Punto único y reposición atómica de stock
El sistema SHALL actualizar stock y registrar el movimiento en la misma operación; el ajuste concurrente SHALL ser atómico y no leer stock previamente en Python.

#### Scenario: Reposición positiva
- **WHEN** ADMIN repone `{"cantidad": 3}`
- **THEN** recibe 200, el stock aumenta en 3 y queda un movimiento positivo `"Reposición"`

#### Scenario: Cantidad no positiva
- **WHEN** la reposición contiene cero, un negativo o un cuerpo inválido
- **THEN** recibe 422 sin cambios

#### Scenario: Reposiciones concurrentes
- **WHEN** dos reposiciones concurrentes actualizan el mismo repuesto
- **THEN** ambas cantidades se suman exactamente una vez y existen ambos movimientos

#### Scenario: Stock insuficiente
- **WHEN** un ajuste negativo dejaría stock menor que cero
- **THEN** el CHECK rechaza la operación, recibe 409 y no queda movimiento ni cambio parcial

### Requirement: Historiales append-only
Los movimientos y precios SHALL exponerse como listas simples de campos planos, sin relaciones anidadas, ordenadas por `(cuando, id)` y sin permitir UPDATE o DELETE.

#### Scenario: Historial de movimientos
- **WHEN** ADMIN consulta `/repuestos/{id}/movimientos` de un repuesto vigente
- **THEN** recibe una lista simple ordenada por `(cuando, id)` con `usuario_id`, motivo, cantidad y orden_id

#### Scenario: Historial de precios
- **WHEN** ADMIN consulta `/repuestos/{id}/precios` de un repuesto vigente
- **THEN** recibe una lista simple ordenada por `(cuando, id)` con `usuario_id`, precio_anterior y precio_nuevo

#### Scenario: Historial de baja o id inexistente
- **WHEN** se consulta historial de un repuesto inexistente o dado de baja
- **THEN** recibe 404 con `"Repuesto no encontrado"`

### Requirement: Baja lógica y reutilización del código
`DELETE /repuestos/{id}` SHALL realizar baja lógica sin impedir la terminación de órdenes existentes y el código SHALL quedar disponible entre vigentes.

#### Scenario: Baja permitida
- **WHEN** ADMIN da de baja un repuesto existente aunque tenga órdenes abiertas
- **THEN** recibe 204, deja los datos conservados y lo excluye de lecturas públicas

#### Scenario: Código reutilizado
- **WHEN** después de la baja se crea otro repuesto con el mismo código
- **THEN** recibe 201; otro repuesto vigente con ese código recibe 409

#### Scenario: Baja repetida
- **WHEN** se intenta dar de baja un repuesto ya dado de baja
- **THEN** recibe 404

### Requirement: Contratos monetarios y respuestas
Los contratos SHALL usar Decimal para dinero, serializarlo como string, incluir fechas con zona y devolver sólo campos del modelo, sin relaciones anidadas.

#### Scenario: Serialización de dinero
- **WHEN** se obtiene o modifica un repuesto o historial con precio decimal
- **THEN** el JSON representa el precio como string con dos decimales

#### Scenario: Campos planos
- **WHEN** se consulta un movimiento o historial
- **THEN** la respuesta contiene usuario_id y no un objeto usuario anidado
