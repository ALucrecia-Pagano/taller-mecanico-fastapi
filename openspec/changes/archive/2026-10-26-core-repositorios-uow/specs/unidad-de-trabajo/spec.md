# Spec Delta — unidad-de-trabajo

## Purpose

Garantiza que cada operación de negocio sea una sola transacción: se confirma al terminar bien, se revierte ante cualquier error y nunca cierra la sesión que recibió, porque no la creó (Ejercicio 6, requisito no funcional «Transacciones»).

## ADDED Requirements

### Requirement: Confirma al salir del bloque
El Unit of Work SHALL confirmar la transacción cuando el bloque que lo abre termina sin excepción. Abrir bloques consecutivos sobre el mismo Unit of Work SHALL estar permitido, y cada uno confirma lo suyo.

#### Scenario: U1 — Bloque exitoso
- **GIVEN** Dado un Unit of Work sobre una sesión
- **WHEN** Cuando dentro del bloque se da de alta un artículo y el bloque termina sin excepción
- **THEN** Entonces otra sesión ve el artículo

#### Scenario: U7 — Bloques consecutivos
- **GIVEN** Dado un Unit of Work cuyo primer bloque ya confirmó un alta
- **WHEN** Cuando se abre un segundo bloque sobre el mismo Unit of Work, se da de alta otro artículo y termina sin excepción
- **THEN** Entonces otra sesión ve los dos artículos

### Requirement: Revierte ante cualquier excepción
El Unit of Work SHALL revertir la transacción cuando el bloque termina con **cualquier** excepción (de la base, de dominio o de otro tipo), y la excepción SHALL seguir su curso. Si no es un `IntegrityError`, sale sin cambios. Revertir ante cualquier excepción es decisión de la alumna.

#### Scenario: U2 — Error de la base
- **GIVEN** Dado un bloque que da de alta un artículo y después provoca un error de la base
- **WHEN** Cuando el bloque termina con ese error
- **THEN** Entonces el artículo no queda en la base

#### Scenario: U3 — Excepción de dominio después de escribir
- **GIVEN** Dado un bloque que da de alta un artículo (con `flush`) y después lanza una excepción de dominio, como haría un servicio
- **WHEN** Cuando el bloque termina con esa excepción
- **THEN** Entonces el artículo no queda en la base
- **AND** la excepción de dominio llega a quien abrió el bloque

#### Scenario: U4 — Excepción cualquiera
- **GIVEN** Dado un bloque que da de alta un artículo y después lanza un `ValueError`
- **WHEN** Cuando el bloque termina con esa excepción
- **THEN** Entonces el artículo no queda en la base
- **AND** el mismo `ValueError`, sin cambios, llega a quien abrió el bloque

### Requirement: No cierra la sesión
Al terminar un bloque, confirmando o revirtiendo, el Unit of Work SHALL dejar la sesión abierta y usable: la sesión es de quien la creó.

#### Scenario: U5 — Sesión usable después del bloque
- **GIVEN** Dados dos bloques sobre la misma sesión, uno que confirma y otro que revierte por una excepción
- **WHEN** Cuando termina cada bloque
- **THEN** Entonces en los dos casos la sesión sigue abierta y ejecuta `SELECT 1`

### Requirement: Sin bloques anidados
Abrir un Unit of Work que ya tiene un bloque abierto SHALL fallar con un error, y el bloque externo SHALL revertirse. **No especificado en la consigna.**

#### Scenario: U6 — Bloque dentro de otro
- **GIVEN** Dado un bloque abierto que ya dio de alta un artículo
- **WHEN** Cuando adentro se abre otro bloque sobre el mismo Unit of Work
- **THEN** Entonces la apertura interna falla con un error
- **AND** el artículo del bloque externo no queda en la base

### Requirement: Fallo al confirmar
Si la confirmación misma falla por una restricción de la base, el Unit of Work SHALL revertir, lanzar el error de dominio de conflicto correspondiente y dejar la sesión usable.

#### Scenario: U8 — La restricción salta en la confirmación
- **GIVEN** Dado un artículo guardado y un bloque que agrega otro con el mismo nombre, sin enviarlo a la base antes de terminar
- **WHEN** Cuando el bloque termina y la confirmación choca con el UNIQUE
- **THEN** Entonces se lanza un error de conflicto con mensaje propio
- **AND** el duplicado no queda en la base y la sesión ejecuta `SELECT 1`

### Requirement: Varios repositorios en una transacción
Un Unit of Work de módulo SHALL componer todos sus repositorios sobre la misma sesión, de modo que sus escrituras se confirmen o se reviertan juntas.

#### Scenario: U9 — Escrituras en dos tablas
- **GIVEN** Dado un Unit of Work de prueba con un repositorio de `prueba_articulo` y otro de `prueba_baja`
- **WHEN** Cuando un bloque escribe en las dos tablas y termina bien, y otro bloque escribe en las dos y termina con una excepción
- **THEN** Entonces las dos filas del primer bloque quedan en la base y ninguna del segundo

### Requirement: Transacción propia independiente
Un Unit of Work abierto sobre una sesión propia, creada aparte de la de la petición, SHALL confirmar sus escrituras aunque la transacción de la petición se revierta (patrón de DD-05).

#### Scenario: U10 — La sesión propia sobrevive al rollback de la petición
- **GIVEN** Dadas una sesión de la «petición» y una sesión propia, cada una con su Unit of Work
- **WHEN** Cuando la propia confirma un alta y la de la petición revierte la suya
- **THEN** Entonces la fila de la sesión propia queda en la base y la de la petición no
