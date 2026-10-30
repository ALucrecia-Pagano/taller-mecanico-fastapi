# Tasks

## 1. Contratos y arneses de pruebas

- [x] 1.1 Crear schemas separados para cliente y vehículo con `extra="forbid"`, rangos de `anio`, recorte de documento y normalización de patente; verificar con tests de 201, 409 y 422.
- [x] 1.2 Agregar fixtures y helpers de PostgreSQL para actores `ADMIN`, `RECEPCION`, `MECANICO`, `CLIENTE`, sesión válida y órdenes con estados finales/no finales; verificar que la suite sólo use `taller_mecanico_test`.
- [x] 1.3 Escribir tests rojos del contrato HTTP y autorización para las cinco rutas, incluyendo 401, 403, 404, duplicados, campos extra y parámetro de ruta inválido; registrar la corrida en `docs/evidencias/CH-07-tdd-rojo.txt`.

## 2. Repositorios y Unit of Work

- [x] 2.1 Extender `ClienteRepository` con alta, lectura por id con vehículos vigentes ordenados por id y búsqueda de ficha por usuario; verificar que las bajas se excluyan.
- [x] 2.2 Implementar `VehiculoRepository` sobre `SoftDeleteRepository`, incluyendo consulta de vehículos propios y baja lógica; verificar que DELETE repetido y vehículo ya dado de baja produzcan 404.
- [x] 2.3 Implementar la consulta de órdenes abiertas mediante join al catálogo `estado_orden` y `es_final = false`; verificar 409 para PENDIENTE/EN_REPARACION y 204 para estados finales.
- [x] 2.4 Componer `ClientesUnitOfWork` con la sesión compartida y el mapa de conflictos de documento/patente; verificar rollback y mensajes sin texto de PostgreSQL.

## 3. Servicios y routers

- [x] 3.1 Implementar el service para alta de clientes, alta de vehículos y consulta de cliente aplicando normalizaciones y reglas de dominio; verificar los escenarios de la spec en tests de servicio/integración.
- [x] 3.2 Implementar el service de `/mis-vehiculos` con resultado vacío sin ficha y vehículos vigentes ordenados; verificar que no exija rol `CLIENTE`.
- [x] 3.3 Crear `router.py` con todos los handlers `async def`, `route_class=RutaQueTraduceErrores`, dependencias correctas y códigos de respuesta; verificar 401/403/404/409/422/204.
- [x] 3.4 Incluir el router exclusivamente en `rutas_protegidas` y verificar que el cambio obligatorio bloquee también `/mis-vehiculos`.

## 4. Verde, triangulación y refactor

- [x] 4.1 Ejecutar los tests rojos convertidos a verde y registrar cada grupo con `tee -a` en `docs/evidencias/CH-07-tdd-verde.txt`, conservando los fallos previos.
- [x] 4.2 Triangular duplicados, normalización, baja lógica, reutilización de patente, orden por id y usuario sin ficha con PostgreSQL real; verificar que no quede ninguna fila incorrecta tras errores.
- [x] 4.3 Medir consultas de `GET /clientes/{id}` y `/mis-vehiculos`; verificar carga anticipada y ausencia de N+1, y refactorizar sólo si los tests permanecen verdes.
- [x] 4.4 Agregar `test/c01_parametro_invalido.http` y `test/c19_baja_vehiculo.http` usando `{{$processEnv TALLER_PASSWORD_PRUEBA}}`; verificar en orden los códigos esperados 422, 200/204/201/409.
- [x] 4.5 Actualizar `README.md` con endpoints, autenticación, seed/test database y comandos de verificación; verificar que no revele secretos.

## 5. Integración final

- [x] 5.1 Ejecutar la suite completa con `pytest -v` contra `taller_mecanico_test`, guardar la salida final en `docs/evidencias/pytest-CH-07.txt` y confirmar cero fallos.
- [x] 5.2 Verificar que `taller_mecanico_test` quede sin datos cargados al terminar y que no se haya tocado `taller_mecanico`.
- [x] 5.3 Escribir `docs/evidencias/verify-CH-07.md` con “Verificación manual” vacía, códigos esperados de C-01/C-19, tabla escenario → test, desvíos y archivos.
