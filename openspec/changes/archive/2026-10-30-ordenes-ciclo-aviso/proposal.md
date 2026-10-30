# Proposal

## Why

El taller ya puede crear y consultar órdenes, pero todavía no puede ejecutar su ciclo de
trabajo. CH-10 agrega las transiciones autorizadas, el descuento transaccional del stock y
el aviso simulado posterior a la confirmación, evitando terminaciones duplicadas y datos a
medias.

## What Changes

- Agregar `POST /ordenes/{id}/iniciar`, `/terminar` y `/cancelar`, con los roles y códigos
  de la consigna.
- Aplicar transiciones condicionales: `PENDIENTE → EN_REPARACION`, `EN_REPARACION →
  TERMINADA` y `PENDIENTE → CANCELADA`; las demás responden 409.
- Reutilizar el punto único de stock de CH-08 para salidas negativas y movimientos
  `"Orden terminada"` en el mismo UoW.
- Hacer terminar atómico ante stock insuficiente y seguro ante dos terminaciones
  concurrentes sobre la misma orden.
- Agendar con `BackgroundTasks` el aviso simulado sólo después del commit; registrar
  `orden_id` y `cliente_id`, sin reintentos ni persistencia tras reinicio.
- Agregar pruebas TDD, `.http` para C-11/C-12/C-13, evidencias y documentación.

## Capabilities

### New Capabilities

- `ordenes-ciclo-aviso`: transiciones de órdenes, autorización, consumo atómico de stock y
  aviso posterior a la confirmación.

### Modified Capabilities

Ninguna. CH-10 agrega una capacidad complementaria a `ordenes-alta-consulta` y reutiliza
`repuestos-stock-precios` sin cambiar su contrato.

## Impact

Se amplían `app/modules/ordenes/` y el registro de rutas, reutilizando modelos, detalle,
UoW y repositorios de CH-09 y el ajuste atómico de `repuestos`. Se agregan tests en
`test/pytest/`, archivos `.http` y evidencias en `docs/evidencias/`. No hay migraciones,
cambios de seed ni dependencias nuevas.
