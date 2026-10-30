# Informe de implementación — CH-10 `ordenes-ciclo-aviso`

Fecha: 2026-10-30. Trabajado con Copilot.

## Alcance verificado

Se implementaron las tres rutas de la consigna:

- `POST /ordenes/{id}/iniciar`
- `POST /ordenes/{id}/terminar`
- `POST /ordenes/{id}/cancelar`

Las transiciones usan UPDATE condicional por id y estado esperado. La terminación reutiliza
el punto único de stock de CH-08, que ejecuta `UPDATE ... SET stock = stock + :cantidad
... RETURNING` con la condición atómica de stock suficiente, sin leer el stock previamente
en Python. Registra salidas negativas y revierte íntegramente ante stock insuficiente. El aviso se agenda después del commit con `BackgroundTasks` y registra
`orden_id` y `cliente_id`; no tiene reintentos ni persistencia ante reinicio.

## Informe de implementación

| Escenario | Test / evidencia | Resultado |
|---|---|---|
| Iniciar PENDIENTE asigna mecánico, cambia a EN_REPARACION e historial | `test_iniciar_asigna_mecanico_y_agrega_historial` | PASA |
| Iniciar orden inexistente → 404 | `test_orden_inexistente_en_transicion_da_404[/ordenes/999999/iniciar-4]` | PASA |
| Iniciar desde estado no permitido → 409 y mensaje propio | `test_iniciar_orden_no_pendiente_da_409` | PASA |
| Dueño cancela PENDIENTE → 200, historial y sin stock | `test_c13_dueno_cancela_orden_pendiente` | PASA |
| Cancelación no autorizada → 403 antes del estado | `test_c13_orden_ajena_da_403` | PASA |
| Cancelar EN_REPARACION/TERMINADA/CANCELADA → 409 | `test_c13_orden_terminada_no_se_cancela`; resto sin test | PARCIAL |
| Cancelar inexistente → 404 | `test_orden_inexistente_en_transicion_da_404[/ordenes/999999/cancelar-6]` | PASA |
| Mecánico asignado o ADMIN termina con stock → 200 | `test_c12_reponer_terminar_y_avisar` | PASA |
| Terminación no autorizada y mensaje propio | `test_terminar_mecanico_no_asignado_da_403` | PASA |
| Terminación inexistente → 404 | `test_orden_inexistente_en_transicion_da_404[/ordenes/999999/terminar-1]` | PASA |
| Terminar desde estado no permitido → 409 | `test_c13_orden_terminada_no_se_cancela` cubre cancelar; terminar repetido sin test | SIN TEST específico |
| Stock insuficiente → 409 con código y rollback total | `test_c11_terminar_sin_stock_revierte_todo` | PASA |
| Movimiento negativo por ítem, motivo y orden_id | `test_c12_reponer_terminar_y_avisar` | PASA |
| Repuesto dado de baja en orden existente se descuenta | `test_repuesto_dado_de_baja_se_descuenta_al_terminar` | PASA |
| Cancelar no agrega movimientos | `test_c13_dueno_cancela_orden_pendiente` | PASA |
| Dos terminaciones concurrentes: una 200, otra 409 | `test_dos_terminaciones_concurrentes_solo_descuentan_una` | PASA |
| Carrera de iniciar/cancelar con actualización condicional | SIN TEST específico | SIN TEST |
| Aviso posterior con orden_id y cliente_id | `test_c12_reponer_terminar_y_avisar`, log capturado | PASA |
| Falla del aviso no afecta la respuesta | `test_falla_del_aviso_no_afecta_terminacion` | PASA |
| Detalle 200 con historial ordenado por (cuando, id) | `test_c12_reponer_terminar_y_avisar` verifica el último historial; orden total sin test específico | PARCIAL |
| Sin sesión en las tres rutas → 401 | `test_transiciones_requieren_sesion` | PASA |
| Rutas protegidas, route class y superficie exacta | `test_superficie_cinco_operaciones_sin_crud_extra` actualizado | PASA |

### Totales de pruebas

- Tests nuevos agregados en esta ampliación: **6 funciones** (**7 casos** por la
  parametrización de las tres operaciones inexistentes).
- Tests de ciclo CH-10 ejecutados en la última corrida: **16 passed**.
- Suite completa ejecutada con `pytest -v`: **661 passed** en `docs/evidencias/pytest-CH-10.txt`.
- Corridas TDD: el rojo conserva fallos en `docs/evidencias/CH-10-tdd-rojo.txt`; los verdes
  se acumulan en `docs/evidencias/CH-10-tdd-verde.txt`.
- Validación OpenSpec: `openspec validate ordenes-ciclo-aviso --strict` → **válido**.
- La fixture de pruebas apunta a `<POSTGRES_DB>_test` y limpia sus datos al terminar.

## Escenarios SIN TEST

Quedan explícitamente sin test específico: las variantes de cancelación desde
EN_REPARACION/CANCELADA; terminar repetido con una segunda solicitud secuencial; carreras
de iniciar/cancelar; y orden total del historial por `(cuando, id)`. C-11/C-12/C-13,
las tres operaciones inexistentes, el repuesto dado de baja, la falla controlada del aviso
y las carreras de terminación (misma orden y órdenes distintas) están cubiertos.

## Verificación manual

Fecha: 30/10/2026. Ejecutó Amanda Pagano con la API reiniciada después de la
corrección del punto único, contra `taller_mecanico`, usando `python seed.py` y
REST Client. La contraseña se mantuvo únicamente en el editor y no se guardó.
Trabajado con Copilot.

Comandos y procedimiento:

1. `python seed.py`
2. Reiniciar la API.
3. Abrir `test/c11_c12_terminar_orden.http` en REST Client y ejecutar sus
   solicitudes, con la variable de contraseña provista sólo desde el editor.
4. Verificar los resultados de C-11 y C-12.

Resultados observados:

- C-11/C-12: `200, 409, 200, 200, 200`, coincidente con lo esperado.
- C-13: cubierto por los tests automáticos de CH-10.

Desvíos y correcciones:

- El ajuste de cobertura detectó que el punto único de stock de CH-08 no era
  completamente atómico: el servicio verificaba el stock antes de descontarlo.
  Se corrigió trasladando la condición de suficiencia dentro del `UPDATE`
  atómico, con `RETURNING`, sin lectura previa del stock en Python.
- No hubo desvíos en los códigos observados durante la verificación manual.

| Archivo | Códigos HTTP esperados, en orden |
|---|---|
| `test/c11_c12_terminar_orden.http` | 200, 409, 200, 200, 200 |
| `test/c13_cancelar.http` | 200, 200, 403, 200, 201, 200, 409, 200, 200, 200, 409 |
