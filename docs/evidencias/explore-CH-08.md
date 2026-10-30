# Explore CH-08 — repuestos-stock-precios

Fecha: 2026-10-30. Trabajado con **Copilot**, mediante `source-command-opsx-explore`.
Modo autónomo de exploración: sin código, sin tests ejecutados y sin commits.

## Fuentes contrastadas

- Fuente de verdad: `docs/consigna/consigna-taller-mecanico.md` y, ante dudas de símbolos, el PDF original.
- `CHANGES.md`, `AGENTS.md`.
- KB: `03_actores_y_roles.md`, `04_modelo_de_datos.md`, `05_reglas_de_negocio.md`,
  `06_funcionalidades.md`, `07_flujos_principales.md`, `09_decisiones_y_supuestos.md`,
  `11_casos_de_prueba.md`.
- OpenSpec vigente: `modelo-de-datos`, `repositorios`, `paginacion`, `solo-agregado`,
  `datos-iniciales`, `errores-de-dominio`, `unidad-de-trabajo` y `autorizacion`.
- Evidencias previas: `explore-CH-01.md` a `explore-CH-07.md`.

OpenSpec confirmó raíz local válida, sin changes activos y sin una spec específica de
repuestos. CH-08 depende de CH-02 y CH-06; CH-09 depende de este change.

## Decisiones

| # | Pregunta | Decisión | Por qué | Alternativa descartada |
|---|---|---|---|---|
| 1 | ¿Qué endpoints entran? | **[Agente]** Sólo `GET /repuestos`, `GET /repuestos/{id}`, `POST /repuestos`, `PATCH /repuestos/{id}`, `DELETE /repuestos/{id}`, `POST /repuestos/{id}/reponer`, `GET /repuestos/{id}/movimientos` y `GET /repuestos/{id}/precios`. | Es exactamente la tabla de la consigna y el scope de CH-08. | Agregar endpoints de ajuste manual, movimientos o precios; no están pedidos. |
| 2 | ¿Qué autorización usan? | **[Agente]** Todas viven dentro de `rutas_protegidas`; listados y detalle llevan `requiere_rol(ADMIN, RECEPCION, MECANICO)`; las escrituras y ambos historiales llevan `requiere_rol(ADMIN)`. Sin sesión: 401; con sesión sin rol: 403; cambio obligatorio conserva el 403 heredado. | RN-04, C-06, C-18 y la matriz RBAC. No hay ADMIN implícito. | Permitir que ADMIN saltee la dependencia o autorizar a recepción la escritura/historial. |
| 3 | ¿Contrato de alta y stock inicial? | **[Agente]** `POST /repuestos` recibe código, descripción, precio y `stock_inicial`; `stock_inicial` es entero `>= 0`; `stock_inicial < 0` da 422. | DA-27, `CHECK stock >= 0` y C-16. | Rechazar cero o permitir negativos para compensar inventario. |
| 4 | ¿Movimiento de alta? | **[Agente]** Si `stock_inicial > 0`, agrega exactamente un movimiento positivo con motivo `"Stock inicial"` en el mismo UoW; si es cero, no agrega movimiento. | DA-27 y `CHECK cantidad <> 0`; mantiene `stock = suma de movimientos` para altas positivas. | Crear un movimiento de cantidad cero o escribir el stock fuera del punto único. |
| 5 | ¿Punto único de stock? | **[Agente]** Un método de servicio/UoW ajusta `repuesto.stock` y agrega `movimiento_stock` en la misma transacción; alta y reposición lo usan y CH-10 lo reutiliza para salidas. | RN-14, RN-13 y el alcance explícito de CH-08. Repositorios sólo hacen `flush()`. | Que cada endpoint actualice stock por su cuenta, o que CH-10 duplique la lógica. |
| 6 | ¿Reposición? | **[Agente]** `POST /repuestos/{id}/reponer` recibe exactamente `{"cantidad": int}` con `cantidad > 0`; suma stock y agrega movimiento positivo con motivo `"Reposición"`; responde 200 con el repuesto actualizado. | DA-09 y DA-10; el endpoint no tiene otro código de validación indicado que 422. | Aceptar cero, permitir negativos o aceptar motivo enviado por el cliente. |
| 7 | ¿Edición y precio? | **[Agente]** PATCH acepta sólo `descripcion` y `precio`, con `exclude_unset`; `stock` y extras dan 422. Precio usa `NUMERIC`/`Decimal`. Si cambia, agrega historial con anterior/nuevo y actor en el mismo UoW; si no cambia, no agrega fila. | RN-20, DA-16/19, C-16/C-18 y reglas de dinero. | Permitir editar stock, enviar total calculado por cliente o crear historial por PATCH sólo de descripción. |
| 8 | ¿Precio igual al actual? | **[Agente]** Se rechaza con 422, sin modificar ni crear historial. | El contrato de PATCH sólo declara 200, 404 y 422; la tabla exige `precio_nuevo <> precio_anterior`; 422 es el error de contrato/regla recomendado. | 409: no corresponde a conflicto de recurso en los códigos declarados; aceptar como no-op ocultaría la regla RN-20. |
| 9 | ¿Rollback del precio? | **[Agente]** El cambio de precio y su historial se confirman juntos; cualquier error revierte ambos y se traduce a error de dominio, nunca 500 ni texto de base. | RN-20, RN-02/RN-13 como patrón de atomicidad y reglas duras de errores. | Actualizar primero y registrar historial después de confirmar. |
| 10 | ¿Baja lógica? | **[Agente]** `RepuestoRepository` hereda `SoftDeleteRepository`; DELETE escribe `borrado_en`, responde 204; inexistente o ya dado de baja, 404. Se permite aunque existan órdenes abiertas; el código vigente queda libre para reuso. | DA-21, RN-16, `uq_repuesto_codigo_vigente` y el patrón de repositorios. | Baja física, 409 por orden abierta o DELETE idempotente 204. |
| 11 | ¿Código repetido? | **[Agente]** El índice parcial `uq_repuesto_codigo_vigente` manda: duplicado vigente → excepción de dominio → 409; un código de baja puede registrarse otra vez. | Consigna, RN-01 y C-19 como precedente de índice parcial. | Consulta previa como garantía de unicidad o índice único sin filtro de baja. |
| 12 | ¿Historiales y formato? | **[Agente]** `MovimientoStockRepository` y `HistorialPrecioRepository` son sólo de lectura/agregado especializado, sin CRUD público; ambos GET devuelven lista simple, sin `{items,total,...}`, ordenada por `id` ascendente. | DA-28 y la consigna sólo declaran 200/404; movimientos e historial son appendOnly. | Paginación o endpoints de UPDATE/DELETE del historial. |
| 13 | ¿Lectura de movimientos de una baja? | **[Agente]** El GET de historial primero verifica que el repuesto exista como recurso visible; una baja responde 404. La lógica futura de terminar orden usa una lectura explícita incluyendo bajas, separada del endpoint público. | Soft delete oculta bajas; DA-21 exige incluirlas sólo para terminar órdenes existentes. | Exponer bajas en GET público o reutilizar sin declarar `get_by_id_including_deleted`. |
| 14 | ¿Búsqueda y paginación? | **[Agente]** `q` filtra descripción con parámetros ligados, sin concatenar SQL; excluye bajas. `page>=1`, `1<=size<=100`, default 20; `total` usa el mismo filtro; página inexistente 422. | Ej. 3, C-16, spec `paginacion` y reglas de seguridad SQL. | Buscar por código sin pedirlo, interpolar `q` o devolver total global. |
| 15 | ¿Contratos de respuesta y errores? | **[Agente]** Schemas separados, extras prohibidos en entrada, dinero serializado como string Decimal y fechas con zona; 404 para id no visible, 409 para conflicto de código, 422 para contrato/regla. Mensajes propios se fijan en propose sólo donde la consigna no los da. | AGENTS.md y convenciones ya confirmadas en CH-05/CH-07. | Exponer modelos de tabla, floats, `IntegrityError`/SQL o 500. |
| 16 | ¿`.http` de C-16 y C-18? | **[Agente]** Crear `test/c16_busqueda_paginacion.http` y `test/c18_historial_precios.http` en CH-08. Cada archivo se corre tras `python seed.py`, empieza con su login propio, define `@password_seed = {{$processEnv TALLER_PASSWORD_PRUEBA}}` y usa `"{{password_seed}}"`; respuestas esperadas sólo con `#`, línea en blanco entre cuerpo y siguiente `###`. | Requisito explícito del explore y formato ya usado por los casos previos. | Contraseña literal, `{{$processEnv ...}}` directo en el login, compartir cookie entre archivos o usar `###` para respuestas. |
| 17 | ¿Qué prueba C-16? | **[Agente]** Búsqueda `' OR '1'='1` → lista vacía/total 0; `q=freno&size=1` → total 1/pages 1; page 2 → 422; size 500 → 422; PATCH parcial conserva lo no enviado; PATCH con stock → 422. | Es el caso C-16 textual y cubre filtro ligado, paginación, extras forbid y RN-14. | Probar sólo 200 del listado sin verificar el filtro y el total. |
| 18 | ¿Qué prueba C-18? | **[Agente]** Login ADMIN y recepción; PATCH de precio verifica una línea con anterior/nuevo; PATCH sólo descripción no agrega otra; recepción recibe 403 en escritura y `/precios`; también se comprueba 401 sin sesión. | C-18 y la regla transversal de rutas protegidas. | Verificar sólo la respuesta del PATCH sin consultar el historial ni el rollback lógico. |
| 19 | ¿Concurrencia de stock? | **[Agente]** No se agrega garantía nueva: la concurrencia general de terminaciones queda fuera de alcance, como ya dice Flujo 8; cada operación individual sí es atómica. | Evita ampliar CH-08 y respeta el límite documentado. | Introducir locks o diseñar reservas de stock no pedidos. |

## Escenarios para el propose

### Feliz

- ADMIN crea un repuesto con stock inicial positivo: alta, movimiento `"Stock inicial"` y stock coherentes.
- ADMIN crea con stock inicial cero: alta válida sin movimiento.
- ADMIN repone una cantidad positiva: stock aumenta y queda `"Reposición"`.
- ADMIN cambia descripción y/o precio válido: sólo cambia lo enviado; precio distinto crea un historial.
- ADMIN lista, busca y consulta historiales; el personal lista y consulta detalle de repuestos.
- ADMIN da de baja y luego puede reutilizarse el código vigente en otra alta.

### Error

- Anónimo en cualquier ruta protegida → 401, incluido `Authorization: Bearer`.
- RECEPCION en alta, PATCH, baja, reposición o historiales → 403 (C-18).
- Código vigente duplicado → 409 sin filas sueltas.
- Repuesto inexistente o dado de baja en una ruta por id → 404.
- `stock_inicial < 0`, reposición no positiva, precio inválido, extras o `stock` en PATCH → 422.
- Precio igual al actual → 422 sin cambio ni historial.
- Filtro y paginación inválidos, inyección textual o página fuera de rango → 422 o lista vacía según el caso.

### Borde

- `stock_inicial = 0` no viola `movimiento_stock.cantidad <> 0`.
- `size=1`, `size=100`, cero resultados y `page=2` de un filtro con una sola página.
- Código reutilizado después de baja; una segunda baja no se expone como vigente.
- Precio que baja sigue siendo positivo y debe crear historial; dinero permanece Decimal.
- Un repuesto dado de baja conserva datos para órdenes existentes, aunque no aparezca en lecturas públicas.
- Error al escribir historial revierte también el precio dentro del mismo UoW.

## Pedidos para el propose

1. Crear el change `repuestos-stock-precios` con proposal, design, specs y tasks según el estado de CH-08; no implementar desde explore.
2. Separar el punto único de stock para que CH-10 pueda invocarlo sin duplicar reglas.
3. Mantener `RepuestoRepository(SoftDeleteRepository)` y declarar métodos filtrados con total coherente y parámetros ligados.
4. Modelar historial de precio y movimiento como appendOnly; ningún CRUD de modificación/baja para esas tablas.
5. Declarar explícitamente en specs los ocho endpoints permitidos y sus roles exactos, incluyendo 401/403 heredados.
6. Definir schemas de entrada con `extra="forbid"`, `stock_inicial >= 0`, reposición `cantidad > 0`, precio Decimal y PATCH con `exclude_unset`.
7. Capturar atomicidad: alta + stock inicial, reposición + movimiento y precio + historial; rollback verificable.
8. Cubrir C-16 y C-18 con pytest contra PostgreSQL `_test` y los dos `.http` con el formato indicado.
9. Resolver mensajes propios sólo si el propose necesita fijarlos; no inventar endpoints ni códigos adicionales.

## No especificado en la consigna

Estas resoluciones fueron aprobadas para el propose; las que no surgen de la consigna quedan
marcadas como **[Alumna]**, **No especificado en la consigna**:

- **[Alumna]** Precio igual al actual → 422, porque la tabla del endpoint PATCH declara 200, 404 y 422.
- Mensajes propios: `"Ya existe un repuesto vigente con ese código"`,
  `"El precio nuevo debe ser distinto del actual"` y `"Repuesto no encontrado"`.
- **[Alumna]** Orden del listado: `id ASC`; movimientos e historial de precios:
  `(cuando, id) ASC`.
- **[Alumna]** JSON con los campos del modelo, sin relaciones anidadas; se expone
  `usuario_id`, no el usuario.
- **[Alumna]** PATCH vacío `{}` → 422.
- **[Alumna]** `q` usa `ILIKE`, sin distinguir mayúsculas; los acentos se comparan tal como
  están almacenados.
- **[Alumna]** Si falla la escritura del historial, rollback de todo el UoW y 409 genérico.
- **[Alumna]** Enteros con el comportamiento por defecto de Pydantic, como en changes previos.
- **[Alumna]** Los historiales de un repuesto dado de baja responden 404.
- **[Alumna]** No hay límite máximo de stock.
- **[Alumna]** Concurrencia: el punto único ejecuta
  `UPDATE repuesto SET stock = stock + :cantidad WHERE id = :id RETURNING stock`
  y agrega el movimiento en el mismo UoW, sin leer stock antes en Python. Si el resultado
  viola `ck_repuesto_stock_no_negativo`, se traduce a 409. CH-10 reutiliza este punto.
  Se probarán dos reposiciones concurrentes que suman correctamente y una salida que
  dejaría stock negativo que responde 409.
