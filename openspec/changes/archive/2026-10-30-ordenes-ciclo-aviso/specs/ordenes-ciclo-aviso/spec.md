# Spec Delta

## Purpose

Permite ejecutar de forma autorizada y transaccional el ciclo de una orden de trabajo,
incluyendo el consumo de repuestos y el aviso simulado posterior a una terminación exitosa.

## ADDED Requirements

### Requirement: Iniciar una orden
El sistema SHALL permitir que un MECANICO vigente inicie una orden PENDIENTE y la asigne a sí mismo.

#### Scenario: Inicio autorizado
- **WHEN** un MECANICO vigente inicia una orden PENDIENTE
- **THEN** responde 200 con el detalle, cambia a EN_REPARACION, asigna mecanico_id al actor y agrega historial.

#### Scenario: Inicio inexistente
- **WHEN** se inicia una orden cuyo id no existe
- **THEN** responde 404 sin escribir historial.

#### Scenario: Inicio desde estado no permitido
- **WHEN** se intenta iniciar una orden que no está PENDIENTE
- **THEN** responde 409 con "La orden no está en un estado que permita esta operación".

### Requirement: Cancelar una orden
El sistema SHALL permitir cancelar únicamente órdenes PENDIENTE a RECEPCION, ADMIN o al dueño del vehículo.

#### Scenario: Dueño cancela
- **WHEN** el dueño autenticado cancela su orden PENDIENTE
- **THEN** responde 200 con el detalle, cambia a CANCELADA, agrega historial y no modifica stock.

#### Scenario: Cancelación no autorizada
- **WHEN** un usuario autenticado sin rol permitido ni relación de dueño intenta cancelar
- **THEN** responde 403 antes de validar el estado.

#### Scenario: Cancelación inválida
- **WHEN** una orden EN_REPARACION, TERMINADA o CANCELADA se intenta cancelar con permiso
- **THEN** responde 409 con "La orden no está en un estado que permita esta operación".

#### Scenario: Cancelación inexistente
- **WHEN** se cancela una orden cuyo id no existe
- **THEN** responde 404.

### Requirement: Terminar una orden
El sistema SHALL permitir terminar una orden EN_REPARACION al mecánico asignado con rol MECANICO vigente o a un ADMIN vigente.

#### Scenario: Terminación autorizada
- **WHEN** el mecánico asignado o un ADMIN vigente termina una orden EN_REPARACION con stock suficiente
- **THEN** responde 200 con el detalle, cambia a TERMINADA, descuenta cada ítem y agrega historial.

#### Scenario: Terminación no autorizada
- **WHEN** un usuario que no es el mecánico asignado con MECANICO vigente ni ADMIN vigente intenta terminar
- **THEN** responde 403 con "Solo el mecánico asignado o un administrador pueden terminar la orden".

#### Scenario: Terminación inexistente
- **WHEN** se termina una orden cuyo id no existe
- **THEN** responde 404.

#### Scenario: Terminación desde estado no permitido
- **WHEN** un actor autorizado intenta terminar una orden que no está EN_REPARACION
- **THEN** responde 409 con "La orden no está en un estado que permita esta operación".

### Requirement: Descuento atómico de stock
La terminación SHALL descontar cada repuesto mediante el punto único de stock y registrar un movimiento negativo por ítem con motivo "Orden terminada" y orden_id.

#### Scenario: Stock insuficiente revierte todo
- **WHEN** un ítem requiere más stock que el disponible
- **THEN** responde 409 con "Stock insuficiente para el repuesto <código>" y revierte estado, stock, movimientos e historial.

#### Scenario: Repuesto dado de baja en orden existente
- **WHEN** un repuesto usado por una orden existente fue dado de baja antes de terminar
- **THEN** la terminación autorizada lo lee incluyendo bajas y descuenta su stock normalmente.

#### Scenario: Cancelar no consume stock
- **WHEN** se cancela una orden PENDIENTE con ítems
- **THEN** no se agregan movimientos ni se altera stock.

### Requirement: Transiciones condicionales
Las tres operaciones SHALL cambiar el estado con una condición de id y estado esperado dentro de su UoW.

#### Scenario: Carrera de terminaciones
- **WHEN** dos terminaciones concurrentes intentan cambiar la misma orden EN_REPARACION
- **THEN** una responde 200 y la otra 409, con un único descuento de stock, movimiento e historial de terminación.

#### Scenario: Carrera de otras transiciones
- **WHEN** dos operaciones compiten por una transición de la misma orden
- **THEN** la actualización que no afecta ninguna fila responde 409 y no agrega stock ni historial.

### Requirement: Aviso posterior
El sistema SHALL agendar un aviso simulado sólo después de confirmar una terminación exitosa.

#### Scenario: Aviso confirmado
- **WHEN** terminar confirma la transacción
- **THEN** se agenda una tarea que espera 0.5 segundos y registra orden_id y cliente_id después de la respuesta.

#### Scenario: Falla del aviso
- **WHEN** la tarea del aviso falla después del commit
- **THEN** la respuesta 200 y las escrituras confirmadas permanecen sin reintento ni persistencia.

### Requirement: Historial y respuesta
Las respuestas 200 de las transiciones SHALL devolver el detalle de orden de CH-09 con historial ordenado por (cuando, id).

#### Scenario: Detalle posterior a transición
- **WHEN** una transición termina correctamente
- **THEN** la respuesta incluye ítems, repuestos, cliente, estado actual y todas las líneas de historial ordenadas por fecha e id.
