# Tasks

## 1. Contratos y superficie protegida

- [x] 1.1 Escribir primero tests de schemas para alta, PATCH, reposiciÃ³n y respuestas: `extra="forbid"`, `stock_inicial >= 0`, `cantidad > 0`, PATCH vacÃ­o, Decimal y campos planos; verificar que fallen antes de implementar los schemas.
- [x] 1.2 Implementar `schemas.py` con contratos separados de los modelos y verificar los tests de schemas en `test/pytest/`.
- [x] 1.3 Escribir tests de rutas que recorran los ocho endpoints, comprueben `route_class=RutaQueTraduceErrores`, inclusiÃ³n en `rutas_protegidas`, 401 sin cookie, 401 con Bearer y 403 por rol; verificar que fallen antes de crear el router.
- [x] 1.4 Implementar `router.py` async con sÃ³lo los ocho endpoints y roles exactos; verificar tests de rutas y que no existan endpoints adicionales del mÃ³dulo.

## 2. Repositorios, UoW y lectura

- [x] 2.1 Escribir tests de `RepuestoRepository` para filtro `ILIKE`, parÃ¡metros ligados, exclusiÃ³n de bajas, orden por id y total con el mismo filtro; verificar primero el rojo.
- [x] 2.2 Implementar `RepuestoRepository(SoftDeleteRepository)` con bÃºsqueda paginada, `get_by_id_including_deleted` para el futuro de CH-10 y sin `commit()`; verificar tests de repositorio y las specs `repositorios`/`paginacion`.
- [x] 2.3 Escribir tests de lecturas de movimientos y precios: lista simple, campos planos, `usuario_id`, orden `(cuando, id)` y 404 para repuesto inexistente o dado de baja; verificar primero el rojo.
- [x] 2.4 Implementar repositorios de movimiento e historial y el `unit_of_work.py`; verificar que las lecturas tengan una Ãºnica sesiÃ³n y que no exista CRUD destructivo pÃºblico.

## 3. Punto Ãºnico de stock y alta

- [x] 3.1 Escribir tests de servicio para alta con stock positivo, cero y negativo; verificar movimiento `"Stock inicial"`, ausencia de movimiento cero y rollback ante duplicado vigente.
- [x] 3.2 Implementar el servicio de alta con el punto Ãºnico de stock y mensajes `"Ya existe un repuesto vigente con ese cÃ³digo"`; verificar tests de alta y traducciÃ³n 409.
- [x] 3.3 Escribir tests concurrentes de dos reposiciones que suman correctamente y de un ajuste negativo que viola `ck_repuesto_stock_no_negativo`; verificar rojo sin leer stock previamente en Python.
- [x] 3.4 Implementar el ajuste atÃ³mico parametrizado con `UPDATE repuesto SET stock = stock + :cantidad WHERE id = :id RETURNING stock`, agregar movimiento en el mismo UoW y traducir CHECK a 409; verificar concurrencia, rollback y suma exacta de movimientos.
- [x] 3.5 Integrar POST `/repuestos` y verificar con httpx que ADMIN recibe 201, RECEPCION 403 y los contratos invÃ¡lidos 422.

## 4. ReposiciÃ³n y baja lÃ³gica

- [x] 4.1 Escribir tests de reposiciÃ³n positiva, cero, negativa, cuerpo extra, repuesto inexistente y repuesto dado de baja; verificar rojo y que no haya cambios en errores.
- [x] 4.2 Implementar POST `/repuestos/{id}/reponer` con motivo `"ReposiciÃ³n"` y respuesta actualizada; verificar tests de servicio, router y autorizaciÃ³n.
- [x] 4.3 Escribir tests de baja lÃ³gica, ocultamiento, 404 en segunda baja, reutilizaciÃ³n de cÃ³digo y conservaciÃ³n para una futura orden abierta; verificar rojo.
- [x] 4.4 Implementar DELETE con `SoftDeleteRepository`, mensaje `"Repuesto no encontrado"` y conflicto de cÃ³digo vigente; verificar tests y la spec de repositorios.

## 5. Precio e historiales

- [x] 5.1 Escribir tests de PATCH parcial, cambio de precio, precio igual, PATCH vacÃ­o, stock/extras y fallo inducido al escribir historial; verificar que el precio e historial reviertan juntos.
- [x] 5.2 Implementar PATCH con `exclude_unset`, Decimal, mensaje `"El precio nuevo debe ser distinto del actual"` y 409 genÃ©rico ante fallo de historial; verificar rollback y ausencia de historial en descripciÃ³n sola.
- [x] 5.3 Escribir tests de GET `/movimientos` y `/precios`, incluyendo orden `(cuando, id)`, campos planos y rechazo de recepciÃ³n; verificar rojo.
- [x] 5.4 Implementar respuestas de historial sin relaciones anidadas y verificar que dinero sea string y fechas zonificadas.

## 6. Casos C-16 y C-18

- [x] 6.1 Escribir tests pytest de C-16: bÃºsqueda `' OR '1'='1`, `q=freno&size=1`, page inexistente, `size=500`, PATCH parcial y PATCH de stock; verificar todos contra PostgreSQL `_test`.
- [x] 6.2 Crear `test/c16_busqueda_paginacion.http`, ejecutable despuÃ©s de `python seed.py`, con `@password_seed = {{$processEnv TALLER_PASSWORD_PRUEBA}}`, login usando `"{{password_seed}}"`, lÃ­nea en blanco antes de cada `###` y respuestas esperadas sÃ³lo como comentarios `#`; verificar revisiÃ³n del formato.
- [x] 6.3 Escribir tests pytest de C-18: historial anterior/nuevo, PATCH posterior sÃ³lo de descripciÃ³n, 403 para RECEPCION y 401 sin sesiÃ³n; verificar contra PostgreSQL `_test`.
- [x] 6.4 Crear `test/c18_historial_precios.http` con el mismo login propio, variable y formato de respuestas; verificar que se pueda ejecutar tras `python seed.py` y demuestre C-18.

## 7. IntegraciÃ³n y verificaciÃ³n

- [x] 7.1 Ejecutar la suite focalizada de repuestos, autorizaciÃ³n, repositorios, paginaciÃ³n y solo-agregado; verificar que pase sin modificar pruebas previas.
- [x] 7.2 Ejecutar una verificaciÃ³n de consultas y tipos para confirmar que no hay N+1, floats de dinero, `commit()` en repositorios ni SQL concatenado; verificar con inspecciÃ³n automatizada y tests existentes.
- [x] 7.3 Ejecutar los dos `.http` con REST Client despuÃ©s de `python seed.py` y conservar sus respuestas esperadas como comentarios; verificar C-16 y C-18.
