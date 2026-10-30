# Tasks

## 1. Contratos y guardias de transición

- [x] 1.1 Agregar excepciones/mensajes y métodos de repositorio para actualización condicional de estado; escribir primero el test rojo y luego el verde, registrando ambos con `tee -a` en las evidencias TDD.
- [x] 1.2 Implementar `iniciar` con autorización MECANICO, asignación e historial; verificar 200, 404, 409 y respuesta de detalle mediante test rojo/verde.
- [x] 1.3 Implementar `cancelar` con autorización por rol vigente o dueño, sólo desde PENDIENTE y sin stock; verificar C-13 y sus errores mediante test rojo/verde.

## 2. Terminación y stock

- [x] 2.1 Implementar `terminar` para mecánico asignado/ADMIN, usando el punto único de stock de CH-08 con `incluir_baja=True`; verificar movimiento negativo, historial, respuesta y C-12 con rojo/verde.
- [x] 2.2 Cubrir stock insuficiente, rollback total y mensaje con código del repuesto; verificar C-11 y el snapshot de estado/stock/movimientos/historial con rojo/verde.
- [x] 2.3 Cubrir dos terminaciones concurrentes con UPDATE condicional; verificar una respuesta 200, otra 409 y un solo descuento con rojo/verde.

## 3. Aviso y superficie HTTP

- [x] 3.1 Registrar `BackgroundTasks` sólo después del commit, con `orden_id` y `cliente_id`, tolerando falla sin alterar 200; verificar el orden respuesta/log y la limitación de reinicio con rojo/verde.
- [x] 3.2 Registrar las tres rutas en el router protegido con códigos y dependencias correctas; crear los `.http` de C-11, C-12 y C-13 con respuestas esperadas comentadas.

## 4. Documentación y verificación

- [x] 4.1 Actualizar README con las transiciones, roles, atomicidad, aviso simulado y limitaciones; verificar que los comandos documentados coincidan con el proyecto.
- [x] 4.2 Ejecutar `pytest -v` sólo contra `taller_mecanico_test`, guardar salida en `docs/evidencias/pytest-CH-10.txt`, limpiar esa base y registrar cualquier corrida fallida sin borrarla.
- [x] 4.3 Crear `docs/evidencias/verify-CH-10.md` con tabla escenario→test para todos los escenarios, lista de escenarios sin test y sección manual vacía con códigos HTTP esperados; validar OpenSpec con `openspec validate --strict`.
