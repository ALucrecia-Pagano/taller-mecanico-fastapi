# Proposal

## Why

El taller ya administra clientes, vehículos y repuestos, pero aún no puede registrar ni consultar órdenes desde la API. CH-09 incorpora el alta transaccional y las consultas exigidas por RN-10, RN-16, RN-17 y RN-19, respetando los precios históricos y evitando N+1.

## What Changes

- Cinco rutas en `rutas_protegidas`: POST/GET `/ordenes`, GET `/ordenes/{id}`, `/mis-ordenes` y `/estados-orden`, con roles de la tabla de la consigna.
- Alta PENDIENTE, ítems con precios copiados y primera línea de historial en un UoW; Decimal, sin modificar stock.
- Consultas paginadas y detalle histórico precargado; propiedad por usuario de la ficha y roles vigentes de base.
- C-06/C-10/C-15/C-17, tests TDD, SQL real de C-15, README e informe sin marcar verificación manual.
- Se aplican las decisiones aprobadas del explore; las decisiones propias conservan `[Agente]` y «No especificado en la consigna».

## Capabilities

### New Capabilities
- `ordenes-de-trabajo`: alta atómica, consultas generales/propias, detalle histórico y catálogo de estados de sólo lectura.

### Modified Capabilities

Ninguna. Se reutilizan sin alterar los contratos existentes de autorización, repositorios, paginación y UoW.

## Impact

Se completan schemas, repository, unit_of_work, service y router de `app/modules/ordenes/`; se registra el router en `main.py`. Se reutilizan repositorios CH-07/08 sobre una sesión. No hay migraciones, instalaciones ni cambios de seed. Transiciones, descuento de stock y aviso quedan en CH-10. Referencias inexistentes y bajas dan 409: POST sólo declara 201/409/422 en la tabla de la consigna. Gobernanza MEDIO; ejecución integral autorizada por la alumna, exclusivamente sobre `taller_mecanico_test`.
