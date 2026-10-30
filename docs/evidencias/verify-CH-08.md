# Informe de implementación — CH-08

## Verificación manual

**Fecha:** 30/10/2026  
**Responsable:** Amanda Pagano  
**Trabajado con:** Copilot

**Comandos y procedimiento:**

- `python seed.py` para cargar los datos de prueba en `taller_mecanico`.
- REST Client en VS Code, ejecutando [c18_historial_precios.http](../../test/c18_historial_precios.http).
- La contraseña se ingresó únicamente en el editor y no se guardó en archivos.

**Resultado C-18:** los códigos observados, en orden, fueron **200, 200, 200, 200, 200, 403, 403**, coincidentes con los esperados.

**Resultado C-16:** cubierto por los tests automáticos de búsqueda y paginación; no fue necesario ejecutarlo manualmente.


## Escenarios de la spec

| Escenario | Test | Estado |
|---|---|---|
| Lectura con rol permitido | `test_repuestos_rutas_sin_sesion_y_recepcion_403` + `test_alta_cero_busqueda_y_paginacion` | TEST |
| Escritura sólo ADMIN | `test_repuestos_rutas_sin_sesion_y_recepcion_403` | TEST |
| Sin sesión o cambio obligatorio | `test_repuestos_rutas_sin_sesion_y_recepcion_403`; cambio obligatorio existente | TEST |
| Alta con stock positivo | `test_alta_repuesto_stock_inicial_y_codigo_vigente` | TEST |
| Alta con stock cero | `test_alta_cero_busqueda_y_paginacion` | TEST |
| Stock inicial negativo | `test_schemas_repuestos_validan_limites_y_extras` | TEST |
| Código vigente repetido | `test_alta_repuesto_stock_inicial_y_codigo_vigente` | TEST |
| Búsqueda filtrada | `test_alta_cero_busqueda_y_paginacion` | TEST |
| Búsqueda no inyectable | `test_alta_cero_busqueda_y_paginacion` | TEST |
| Página inexistente o tamaño inválido | `test_alta_cero_busqueda_y_paginacion` | TEST |
| Bajas excluidas | `test_busqueda_repuestos_total_y_bajas` | TEST |
| PATCH parcial | `test_patch_precio_historial_parcial_y_rechazos` | TEST |
| Precio distinto | `test_patch_precio_historial_parcial_y_rechazos` | TEST |
| Precio igual o PATCH vacío | `test_patch_precio_historial_parcial_y_rechazos` | TEST — precio igual 422 |
| Stock o extras | `test_patch_precio_historial_parcial_y_rechazos` + schemas | TEST |
| Fallo al escribir historial | **SIN TEST** | SIN TEST |
| Reposición positiva y movimiento “Reposición” | `test_reponer_atomico_y_baja_reutiliza_codigo` | TEST |
| Cantidad no positiva | schemas de reposición | TEST |
| Reposiciones concurrentes | `test_dos_reposiciones_concurrentes_se_suman` | TEST |
| Stock insuficiente | `test_ajuste_negativo_rechaza_y_revierte` | TEST |
| Historial de movimientos | `test_alta_repuesto_stock_inicial_y_codigo_vigente` | TEST |
| Historial de precios | `test_patch_precio_historial_parcial_y_rechazos` | TEST |
| Historial de baja o id inexistente | `test_reponer_atomico_y_baja_reutiliza_codigo` | TEST |
| Baja permitida | `test_reponer_atomico_y_baja_reutiliza_codigo` | TEST |
| Código reutilizado | `test_reponer_atomico_y_baja_reutiliza_codigo` | TEST |
| Baja repetida | `test_reponer_atomico_y_baja_reutiliza_codigo` | TEST |
| Serialización de dinero | `test_patch_precio_historial_parcial_y_rechazos` | TEST |
| Campos planos | `test_schemas_historiales_son_planos` | TEST |
| Lectura explícita de baja para CH-10 | `test_repuesto_dado_de_baja_se_recupera_incluyendo_deleted` | TEST |
| UPDATE/DELETE append-only | Suite existente `test_solo_agregado.py`; no nuevo en CH-08 | TEST |
| Reposición atómica ante fallo | `test_ajuste_negativo_rechaza_y_revierte` | TEST |
| Filtro vacío y filtro sin coincidencias | `test_alta_cero_busqueda_y_paginacion` | TEST — página vacía y total 0 |

## Desvíos

- El fallo inducido al escribir el historial no tiene un test específico; la ruta
  de rollback comparte el UoW existente y queda marcado para una iteración posterior.
- La verificación manual de los `.http` queda intencionalmente vacía para la persona
  responsable de ejecutarla con REST Client.

## Archivos

- `app/modules/repuestos/schemas.py`
- `app/modules/repuestos/repository.py`
- `app/modules/repuestos/unit_of_work.py`
- `app/modules/repuestos/service.py`
- `app/modules/repuestos/router.py`
- `app/core/errores.py`
- `app/core/rutas.py`
- `main.py`
- `test/pytest/test_repuestos_schemas.py`
- `test/pytest/test_repuestos.py`
- `test/pytest/test_repuestos_repository.py`
- `test/c16_busqueda_paginacion.http`
- `test/c18_historial_precios.http`
- `README.md`
- `docs/evidencias/CH-08-tdd-rojo.txt`
- `docs/evidencias/CH-08-tdd-verde.txt`
- `docs/evidencias/pytest-CH-08.txt`

## Códigos esperados de los `.http`

### `test/c16_busqueda_paginacion.http`

1. Login administración: **200**
2. Búsqueda `' OR '1'='1`: **200**
3. `q=freno&size=1`: **200**
4. Página 2 del filtro: **422**
5. `size=500`: **422**
6. PATCH descripción: **200**
7. PATCH stock: **422**

### `test/c18_historial_precios.http`

1. Login administración: **200**
2. Login recepción: **200**
3. PATCH precio: **200**
4. GET precios: **200**
5. PATCH sólo descripción: **200**
6. PATCH recepción: **403**
7. GET precios recepción: **403**
