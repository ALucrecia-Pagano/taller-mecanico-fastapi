# Proposal

## Why

El proyecto ya tiene los modelos base de repuestos, pero aún no expone su gestión ni
garantiza que stock, movimientos e historial de precios se operen como una unidad.
CH-08 completa los endpoints de repuestos requeridos por la consigna y deja un punto
único de stock reutilizable por CH-10.

## What Changes

- Agregar el módulo completo de `/repuestos` con los ocho endpoints de la consigna.
- Exigir autorización exacta: lectura para ADMIN/RECEPCION/MECANICO y escritura/historial sólo para ADMIN.
- Agregar contratos para alta, PATCH, reposición y respuestas Decimal sin exponer relaciones.
- Implementar búsqueda `ILIKE` paginada, total coherente y exclusión de bajas lógicas.
- Implementar el punto único de stock con `UPDATE ... SET stock = stock + :cantidad ... RETURNING stock`, movimiento append-only y atomicidad.
- Registrar `"Stock inicial"` sólo para altas con stock positivo y `"Reposición"` para reposiciones.
- Registrar historial de precio sólo cuando el precio cambia y revertir toda la operación ante errores.
- Implementar baja lógica y unicidad de código entre repuestos vigentes.
- Agregar pruebas pytest de C-16, C-18 y concurrencia, más los archivos `.http` con el formato acordado.

## Capabilities

### New Capabilities

- `repuestos-stock-precios`: gestión autenticada de repuestos, stock, movimientos, precios, baja lógica y sus contratos.

### Modified Capabilities

<!-- Las capacidades existentes se reutilizan sin cambiar sus requisitos; su aplicación
     a repuestos queda cubierta por la capacidad nueva y sus tests. -->

## Impact

- Código: `app/modules/repuestos/` completo, integración de router protegido y composición del UoW.
- Persistencia: uso de las tablas existentes `repuesto`, `movimiento_stock` e `historial_precio_repuesto`; no se agregan tablas ni endpoints fuera de la consigna.
- Tests: nuevos casos en `test/pytest/` sobre contratos, autorización, atomicidad, rollback, concurrencia y consultas; `test/c16_busqueda_paginacion.http` y `test/c18_historial_precios.http`.
- Integración futura: CH-10 reutilizará el punto único para descontar stock con motivo `"Orden terminada"` y `orden_id`.
