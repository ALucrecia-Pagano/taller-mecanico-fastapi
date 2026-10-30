# Design

## Context

El módulo `clientes` ya declara los modelos `Cliente` y `Vehiculo`, la relación con
`OrdenTrabajo`, el índice parcial `uq_vehiculo_patente_vigente` y relaciones con
`lazy="raise"`. El repositorio actual sólo ofrece el `add` requerido por el
auto-registro. La aplicación ya dispone de `rutas_protegidas`, `requiere_rol`,
`SoftDeleteRepository`, traducción de errores de dominio y Unit of Work base.

## Goals / Non-Goals

**Goals:**

- Completar las capas del módulo sin mover responsabilidades entre Router, Service,
  Unit of Work y Repository.
- Mantener autorización por roles vigentes de base y el bloqueo transversal de
  cambio obligatorio.
- Garantizar baja lógica, unicidad parcial, normalización acordada y lecturas sin N+1.
- Reutilizar las restricciones y capacidades core existentes, sin migración nueva.

**Non-Goals:**

- No agregar `GET /clientes`, vinculación posterior cliente-usuario ni endpoints de
  administración de órdenes.
- No modificar la especificación general de paginación.
- No implementar concurrencia avanzada fuera de las garantías ya exigidas por la base.

## Decisions

### Capas y composición

`router.py` recibirá dependencias de sesión, contexto autenticado y roles; construirá
el `ClientesUnitOfWork` mediante la dependencia existente y lo pasará al servicio.
El servicio abrirá `async with uow` y los repositorios sólo harán `flush()`. El router
nuevo declarará `route_class=RutaQueTraduceErrores` y se incluirá en
`rutas_protegidas`.

### Repositorios y precarga

`ClienteRepository` ampliará el repositorio mínimo con métodos específicos para:
cliente por id con `vehiculos` vigentes, ficha por `usuario_id`, y vehículos propios
vigentes. La consulta declarará `selectinload` o la estrategia equivalente y ordenará
por `Vehiculo.id`. `VehiculoRepository` heredará de `SoftDeleteRepository` para que
las búsquedas normales excluyan bajas y `soft_delete` sea la única operación de baja.

### Regla de órdenes abiertas

La baja consultará la existencia de órdenes del vehículo enlazadas al catálogo
`estado_orden` y filtradas por `es_final = false`. La consulta se resolverá desde el
módulo clientes, sin importar CRUD ni servicios del módulo `ordenes`; el catálogo
será de sólo lectura. Si existe una fila, se lanzará el conflicto propio antes de
marcar `borrado_en`.

### Normalización y conflictos

El schema de entrada de cliente quitará sólo espacios de los bordes del documento.
El schema de entrada de vehículo eliminará todos los espacios de la patente y la
convertirá a mayúsculas antes de construir el modelo. La base sigue siendo la
autoridad para la unicidad; el mapa de conflictos distinguirá el documento
duplicado, la patente vigente duplicada y la regla de órdenes abiertas. No se
propagará texto de PostgreSQL.

### `/mis-vehiculos` y ruta protegida

La ruta usará sólo autenticación, no `requiere_rol`, pero se montará en
`rutas_protegidas` para que el cambio obligatorio produzca 403. La ausencia de una
ficha se tratará como resultado vacío; no se consultarán vehículos sin un cliente
vinculado.

## Risks / Trade-offs

- **[Risk]** La normalización de patente puede cambiar el valor que el usuario
  envió. → Se valida en el schema y se cubren variantes con espacios y minúsculas.
- **[Risk]** Una relación no precargada puede causar `lazy="raise"` o N+1. →
  Las consultas relacionales se concentran en métodos de repositorio y se prueban
  con contador de consultas.
- **[Risk]** Un vehículo puede tener órdenes históricas y abiertas simultáneamente.
  → La baja usa `es_final` del catálogo, no una lista fija ni el mero conteo de
  órdenes.
- **[Risk]** Un conflicto de base puede no coincidir con el nombre esperado. →
  Se conserva el mapa de restricciones y se registra el detalle sólo en servidor,
  devolviendo siempre el mensaje propio.

## Migration Plan

No hay migración de esquema. Se agregan las capas de aplicación, se registra el
router y se ejecutan los tests contra `taller_mecanico_test`. El rollback consiste
en retirar el router y las capas del change; no se toca la base de producción ni
se ejecuta `create_all`.
