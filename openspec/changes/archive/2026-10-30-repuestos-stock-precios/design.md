# Design

## Context

La aplicación ya dispone de modelos SQLModel para `repuesto`, `movimiento_stock` e
`historial_precio_repuesto`, repositorios genéricos asincrónicos sin `commit()`,
`SoftDeleteRepository`, UoW y traducción de errores de dominio. El módulo `repuestos`
todavía sólo contiene modelos. Las restricciones existentes incluyen código único
entre vigentes, stock no negativo, cantidad de movimiento distinta de cero y
historial de precio con precio nuevo diferente.

## Goals / Non-Goals

**Goals:**

- Completar el módulo por capas Router → Service → UoW → Repository.
- Mantener autorización y cambio obligatorio mediante las dependencias ya existentes.
- Hacer atómicos los cambios de stock y precio.
- Exponer DTOs planos y listas de historial compatibles con la consigna.
- Dejar una operación de stock reutilizable por CH-10.

**Non-Goals:**

- No crear endpoints de movimientos o precios distintos de los GET declarados.
- No cambiar el esquema de tablas ni agregar límites máximos de stock.
- No resolver locking general para terminación simultánea de órdenes; la consigna lo
  deja fuera de alcance.
- No implementar órdenes ni cambiar `seed.py` en este change.

## Decisions

### Punto único de stock y concurrencia

El servicio usará una sentencia parametrizada que incremente o decremente
atómicamente el stock:

```sql
UPDATE repuesto
SET stock = stock + :cantidad
WHERE id = :id
  AND borrado_en IS NULL
RETURNING stock
```

El resultado se leerá sin consultar previamente el stock en Python. El movimiento se
agregará en la misma sesión y el UoW confirmará ambas escrituras. Si el `CHECK
ck_repuesto_stock_no_negativo` falla, el UoW hará rollback y la ruta traducirá el
conflicto a 409. Para CH-10 se ofrecerá la misma operación con lectura explícita de
repuestos dados de baja cuando corresponda a una orden existente; el endpoint público
no expone bajas.

Se descarta leer-modificar-escribir en Python porque pierde actualizaciones concurrentes.
No se agrega un lock pesimista adicional porque la sentencia atómica cubre el ajuste
requerido y el alcance de concurrencia de órdenes está fuera de CH-08.

### Separación de repositorios y servicios

`RepuestoRepository` heredará `SoftDeleteRepository` y tendrá búsqueda por descripción
con `ILIKE`, total con el mismo statement y orden por id. Los repositorios de movimiento
y precio sólo ofrecerán lecturas ordenadas por `(cuando, id)` y altas internas mediante
el servicio; no habrá CRUD público destructivo.

El servicio será dueño de las reglas de motivo, signo, stock inicial, precio distinto,
mensajes de dominio y composición de operaciones. El UoW compondrá todos los
repositorios sobre la misma `AsyncSession`; ningún repositorio hará `commit()`.

### Transacciones y errores

Alta positiva + movimiento inicial, reposición + movimiento y precio + historial se
ejecutarán dentro de un único UoW. Los errores de unicidad, CHECK o historial se
convertirán a excepciones de dominio antes de alcanzar la respuesta; no se expondrán
detalles de PostgreSQL.

### Contratos y autorización

Los schemas Pydantic serán independientes de los modelos de tabla y usarán
`extra="forbid"` en entradas. El PATCH usará `exclude_unset`, rechaza cuerpo vacío y
no incluye stock. Los precios serán Decimal/NUMERIC y sus serializaciones serán strings.
Cada router declarará `route_class=RutaQueTraduceErrores`; las rutas se incluirán dentro
de `rutas_protegidas` con dependencias exactas por rol.

### Pruebas y HTTP

Las pruebas de base correrán contra PostgreSQL `_test`, sin mocks de la base. Se
probarán atomicidad, rollback, filtros, paginación, permisos, baja lógica,
serialización, concurrencia de reposiciones y rechazo de stock negativo. C-16 y C-18
tendrán archivos `.http` independientes: cada uno ejecuta su propio login tras
`python seed.py`, define `@password_seed = {{$processEnv TALLER_PASSWORD_PRUEBA}}`,
usa `"{{password_seed}}"`, deja una línea en blanco antes de cada `###` y expresa
respuestas esperadas con comentarios `#`.

## Risks / Trade-offs

- [Risk] El CHECK puede fallar después del UPDATE atómico → [Mitigation] traducir
  `IntegrityError` a 409 y verificar rollback completo en pytest.
- [Risk] Un método público podría cargar bajas accidentalmente → [Mitigation] centralizar
  el filtro en `SoftDeleteRepository` y probar GET de baja con 404.
- [Risk] Un historial parcialmente serializado podría exponer relaciones → [Mitigation]
  usar schemas planos y verificar que sólo salga `usuario_id`.
- [Risk] La sentencia de stock y el movimiento pueden divergir si el UoW se confirma
  fuera de la composición → [Mitigation] una única unidad de trabajo y pruebas de
  fallo inducido.

## Migration Plan

No se requiere migración de esquema: las tablas y restricciones necesarias ya existen.
La implementación se valida contra una base `_test` migrada. El rollback operativo es
revertir el change completo antes de aplicar CH-09; no se ejecutan migraciones nuevas.

