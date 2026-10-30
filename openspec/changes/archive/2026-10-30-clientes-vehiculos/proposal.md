# Proposal

## Why

El proyecto ya tiene las tablas `cliente` y `vehiculo` y el repositorio mínimo que necesita el auto-registro, pero todavía no expone la operación diaria de recepción sobre clientes y vehículos. CH-07 completa ese módulo con borrado lógico, reutilización segura de patentes y consultas propias sin N+1, manteniendo las garantías de autorización e integridad de la consigna.

## What Changes

- Agregar únicamente los endpoints de la tabla de la consigna:
  - `POST /clientes`.
  - `GET /clientes/{id}` con vehículos vigentes.
  - `POST /clientes/{id}/vehiculos`.
  - `DELETE /vehiculos/{id}`.
  - `GET /mis-vehiculos`.
- Proteger las cuatro operaciones de recepción con `RECEPCION` o `ADMIN`; proteger `/mis-vehiculos` sólo con autenticación, pero incluirlo en `rutas_protegidas`.
- Completar schemas, repositorio, Unit of Work, service y router del módulo `clientes`.
- Normalizar patentes a mayúsculas sin espacios y documentos quitando espacios de los bordes antes de guardar. **[Alumna] — No especificado en la consigna.**
- Traducir duplicados y órdenes abiertas a 409 con mensajes propios:
  - `Ya existe un cliente con ese documento`.
  - `Ya existe un vehículo vigente con esa patente`.
  - `El vehículo tiene órdenes abiertas`.
- Aplicar baja lógica con `SoftDeleteRepository`; un vehículo ya dado de baja responde 404. **[Alumna]**, decisión 3d de CH-02.
- Bloquear la baja si existe una orden con estado no final (`es_final = false`) y ordenar vehículos por `id`.
- No agregar `GET /clientes`, vinculación de cliente existente con usuario ni cambios a la especificación de paginación.

## Capabilities

### New Capabilities

- `clientes-vehiculos`: Alta y consulta de clientes, alta y baja lógica de vehículos y consulta de vehículos propios con autorización, unicidad vigente y reglas de órdenes abiertas.

### Modified Capabilities

Ninguna. La autorización, la traducción de errores, los repositorios base y la paginación existentes se reutilizan sin cambiar sus requisitos generales.

## Impact

- Código: `app/modules/clientes/{schemas,repository,unit_of_work,service,router}.py` y registro del router en `main.py`.
- API: cinco rutas protegidas nuevas, con los códigos de la consigna y contratos separados de los modelos.
- Persistencia: uso de la restricción existente `uq_vehiculo_patente_vigente`; no se agrega una migración.
- Pruebas: tests PostgreSQL reales en `test/pytest/`, con cobertura de 401/403/404/409/422, normalización, baja, reutilización y ausencia de N+1.
- Evidencia: `.http` para C-01 y C-19, registros TDD, README y verificación manual.
