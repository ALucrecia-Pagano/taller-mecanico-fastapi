# registro-de-clientes Specification

## Purpose

Permite el auto-registro de clientes con identidad, ficha y auditoría atómicas, rechazando duplicados sin apropiarse de datos existentes.

## Requirements

### Requirement: Registro atómico
POST /auth/registro SHALL crear usuario activo sin cambio pendiente, rol CLIENTE con otorgada_por nulo, ficha vinculada y evento con actor=email y acción «Registro de cliente <email>» en una sola transacción; responde 201.

#### Scenario: R1 — Alta completa
- **GIVEN** Dado un registro válido con email y documento nuevos
- **WHEN** Cuando se registra
- **THEN** Entonces otra sesión ve exactamente un usuario, una asignación CLIENTE, una ficha y un evento vinculados; el hash no es la contraseña y no se expone en la respuesta

#### Scenario: R5 — Falla tras escrituras parciales
- **GIVEN** Dado un estado previo conocido
- **WHEN** Cuando la operación falla después de algunas escrituras
- **THEN** Entonces ninguna de las cuatro filas nuevas queda y las previas permanecen iguales; no se exige restaurar secuencias

### Requirement: Unicidad sin apropiación
El registro SHALL dejar la unicidad a la base sin consulta previa y traducir conflictos a 409 con mensajes propios. Textos exactos confirmados: No especificado en la consigna.

#### Scenario: R2 — Email repetido
- **GIVEN** Dado un usuario existente
- **WHEN** Cuando se registra el mismo email con documento nuevo
- **THEN** Entonces responde 409 con detail «El correo ya está registrado», sin filas sueltas ni texto interno

#### Scenario: R3 — Documento con usuario
- **GIVEN** Dado una ficha vinculada existente
- **WHEN** Cuando se registra un email nuevo con ese documento
- **THEN** Entonces responde 409 con detail «El documento ya está registrado» y conserva las filas previas

#### Scenario: R4 — Documento sin usuario
- **GIVEN** Dado una ficha de cliente sin usuario
- **WHEN** Cuando se registra con su documento
- **THEN** Entonces responde 409 con detail «El documento ya está registrado», no vincula la ficha ni deja usuario, rol o evento


