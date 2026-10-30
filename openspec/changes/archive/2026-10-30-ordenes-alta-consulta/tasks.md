# Tasks

Cada tarea sigue safety net → RED ejecutado → GREEN ejecutado → triangulación → refactor verde. Logs append en CH-09-tdd-rojo.txt y CH-09-tdd-verde.txt con comando/resultado; no se borran fallos. Seams: HTTP prueba contratos/permisos; servicio/repositorio con PostgreSQL real prueba atomicidad/precarga. Sólo taller_mecanico_test, cleanup final, sin mocks de base. Documentación y pruebas acompañan cada comportamiento.

## 1. Contratos

- [x] 1.1 Implementar DTOs entrada/salida con extras prohibidos, repetidos422 y Decimal dos posiciones; verificar tests de schemas E03/E04 y serialización, RED/GREEN y triangulación.

## 2. Catálogo protegido

- [x] 2.1 Implementar catálogo sólo lectura, composición UoW, dependencia/router protegido y documentación C17; verificar HTTP E18/E22 con catálogo sembrado/vacío y acceso, RED/GREEN.

## 3. Alta transaccional

- [x] 3.1 Implementar alta PENDIENTE, ítems e historial y detalle de respuesta sin mover stock; documentar C10; verificar E01/E02/E09 con PostgreSQL real, RED/GREEN.
- [x] 3.2 Validar referencias vigentes y catálogo antes de escribir; garantizar rollback e IntegrityError propio incluso al confirmar, conservar precios históricos; verificar E05/E06/E07/E10/E11, RED/GREEN.
- [x] 3.3 Validar dinero exacto y límites físicos sin desbordamientos de driver; verificar E08 y cantidades extremas, RED/GREEN y borde máximo.

## 4. Detalle autorizado y costo SQL

- [x] 4.1 Implementar GET detalle personal/dueño con roles de base, orden historial y bajas históricas; documentar C06/C15 y capturar SQL real 2/4 ítems en C-15-consultas.txt; verificar E14/E19/E20 y detalle E21, RED/GREEN.

## 5. Listados propios y generales

- [x] 5.1 Implementar listados paginados con estado enum y propiedad sin exigir CLIENTE; verificar E15/E16/E17 y listados E21, RED/GREEN; actualizar documentación.

## 6. Integración y entrega

- [x] 6.1 Completar controles transversales E12/E13/E22, archivos HTTP C06/C10/C15/C17 con formato acordado, README e informe completo escenario→test; verificar integración y formato mediante RED/GREEN, suite pytest -v guardada en pytest-CH-09.txt, openspec validate --strict y base de prueba sin datos al terminar.
