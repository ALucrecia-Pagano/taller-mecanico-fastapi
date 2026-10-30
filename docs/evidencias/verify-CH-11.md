# Informe de implementación — CH-11 `cierre-entrega`

Fecha de corte: 30/10/2026. Trabajado con Copilot.

## Informe de implementación

| Escenario | Archivo / evidencia | Resultado |
|---|---|---|
| Instrucciones reproducibles desde cero | `README.md`, secciones Requisitos, Puesta en marcha desde cero y Ejecución de la suite | PASA documentalmente |
| CH-10 iniciar | `app/modules/ordenes/router.py`, `app/modules/ordenes/service.py`, `test/pytest/test_ordenes_ciclo.py::test_iniciar_asigna_mecanico_y_agrega_historial` | PASA |
| CH-10 terminar y rollback C-11 | `test/c11_c12_terminar_orden.http`, `test/pytest/test_ordenes_ciclo.py::test_c11_terminar_sin_stock_revierte_todo` | PASA |
| CH-10 terminar, stock, historial y aviso C-12 | `test/c11_c12_terminar_orden.http`, `test/pytest/test_ordenes_ciclo.py::test_c12_reponer_terminar_y_avisar` | PASA |
| CH-10 cancelar C-13 | `test/c13_cancelar.http`, tests `test_c13_dueno_cancela_orden_pendiente`, `test_c13_orden_ajena_da_403`, `test_c13_orden_terminada_no_se_cancela` | PASA |
| Repuesto dado de baja consumido al terminar | `test/pytest/test_ordenes_ciclo.py::test_repuesto_dado_de_baja_se_descuenta_al_terminar` | PASA |
| Aviso fallido sin revertir la operación | `test/pytest/test_ordenes_ciclo.py::test_falla_del_aviso_no_afecta_terminacion` | PASA |
| Concurrencia de terminaciones | `test/pytest/test_ordenes_ciclo.py::test_dos_terminaciones_concurrentes_solo_descuentan_una`, `test_ordenes_distintas_compiten_por_un_stock` | PASA |
| C-14, sólo agregado y FK | `docs/evidencias/C-14-psql.txt`, `docs/evidencias/capturas/C-14-solo-agregado.png` | Vigente: 7 errores, 6 de sólo agregado |
| C-15, consultas fijas | `docs/evidencias/C-15-consultas.txt`, `test/pytest/test_ordenes_detalle.py::test_c15_sql_real_dos_y_cuatro_items_consultas_fijas` | Vigente: 5 SELECT por petición, 3 de dominio |
| Búsqueda de credenciales reales | Revisión de archivos versionables sin abrir `.env`; literal ficticio del seed tratado como excepción | No se observaron credenciales reales |
| Suite completa | `docs/evidencias/pytest-CH-11.txt` | Se registra la corrida final |

### Totales

- Tests completos: **661 passed** en `docs/evidencias/pytest-CH-11.txt`.
- Tests de CH-10: 16 casos enfocados, incluidos los escenarios adicionales de
  baja lógica, falla del aviso, inexistencia y concurrencia entre órdenes.
- C-14: 7 rechazos esperados en la evidencia textual.
- C-15: misma cantidad de consultas para órdenes de 2 y 4 ítems, sin N+1.

## Riesgos restantes, ordenados por gravedad

1. **Alta — R1:** no hay cobertura específica de todos los desbordamientos
   físicos de `INTEGER`/`NUMERIC` en módulos anteriores; la auditoría lo marca
   como riesgo estático no reproducido.
2. **Alta — R2:** el arranque desde cero y la creación del esquema quedan para
   la verificación manual de la responsable; esta corrida no certifica el
   entorno nuevo.
3. **Media — R3:** C-15 es un fragmento textual real generado por el listener
   SQL y no una captura de consola `SQL_ECHO`; conserva la trazabilidad técnica,
   pero la aceptación formal del formato queda pendiente.
4. **Baja — R6:** no se fija un umbral cuantitativo para la semejanza temporal
   de C-04 ni para C-05; los tests verifican la lógica y el rechazo 429.

El hallazgo documental R4 de la auditoría fue corregido: las referencias al
literal ficticio se reemplazaron por la alusión a la contraseña definida en
`seed.py`; la búsqueda posterior no encontró el literal en `docs/` ni
`openspec/`.

## Verificación manual

Fecha: 30/10/2026. Ejecutó Amanda Pagano contra `taller_mecanico`, con la
contraseña mantenida únicamente en el editor de REST Client. Trabajado con
Copilot.

Comandos ejecutados:

```text
alembic downgrade base
alembic upgrade head
alembic current
python seed.py
uvicorn main:app
```

Resultados:

- `alembic current`: `0002 (head)`.
- `GET /health/live`: 200, `{"estado": "vivo"}`.
- `GET /health/ready`: 200, `{"estado": "listo"}`.
- C-06 con REST Client: `401, 200, 403, 200, 403, 200`.
- Los resultados coinciden con lo esperado.

La prueba resuelve R2: queda verificado el arranque desde cero, la creación del
esquema mediante Alembic, la carga del seed y la disponibilidad de la API. R1,
R3 y R6 permanecen como riesgos conocidos documentados.
