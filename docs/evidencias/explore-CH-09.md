# Explore CH-09 — `ordenes-alta-consulta`

Fecha: 2026-10-30. **Trabajado con Codex**, usando `source-command-opsx-explore`.
Alcance autorizado: exploración documental y escritura de este archivo exclusivamente.
No se ejecutaron pytest, Alembic, `seed.py`, peticiones a la API ni consultas a la base.
No se modificaron código, KB, specs, tareas de CH-08 ni configuración.

Las resoluciones propias se identifican como **[Agente]**; no son nuevas DA de la alumna.
El pedido permite resolver las decisiones de esta exploración, pero no autoriza implementar.

## Fuentes y estado comprobado

- `AGENTS.md`, leído primero; `CHANGES.md`, ficha CH-09 y dependencias CH-07/CH-08.
- `docs/consigna/consigna-taller-mecanico.md`: tablas pp. 5–6, RN-10/RN-16/RN-17/RN-19, ejercicios 3/6/8, tabla de endpoints pp. 16–17, ejemplo pp. 17–18, C-06/C-10/C-15/C-17 y entrega p. 22. Se usa la transcripción pedida; el PDF sigue siendo la autoridad ante discrepancias.
- `knowledge-base/04_modelo_de_datos.md`, `06_funcionalidades.md` (US-024/045/050/051/052/070), `07_flujos_principales.md` (alta y consultas), `09_decisiones_y_supuestos.md` y `11_casos_de_prueba.md`; reglas y contratos contrastados con la consigna.
- Specs durables pertinentes: `modelo-de-datos`, `repositorios`, `unidad-de-trabajo`, `paginacion`, `autorizacion`, `errores-de-dominio`, `clientes-vehiculos`.
- Artefactos de CH-08: `openspec/changes/repuestos-stock-precios/{proposal,design,tasks}.md` y `specs/repuestos-stock-precios/spec.md`. Son contexto de integración en curso, no prueba de funcionamiento.
- Notas de `docs/evidencias/explore-CH-0*.md`: CH-02 exige dependencia UoW async en el router y mapa de restricciones; CH-03 fija `CodigoEstado`, dinero, `lazy="raise"` y fechas de la base; CH-04 exige historial por `(cuando, id)` porque dos filas pueden compartir `now()`; CH-07 conserva consultas históricas y CH-08 distingue lectura pública de repuestos y lectura interna incluyendo bajas.
- OpenSpec CLI existente consultado en modo lectura con su ruta absoluta. `status --change ordenes-alta-consulta --json` informa **change inexistente**; no se creó. CH-08 tiene planificación completa (`proposal/specs/design/tasks: done`); esto **no significa implementación terminada**. La consulta `list` realizada en esta exploración compartida lo registra `in-progress`, 0/28 tareas. El usuario informa que otro agente está implementándolo: no se infiere cierre por archivos de evidencia o campos `isComplete` de planificación.
- Gobernanza CH-09: **MEDIO**, por alta de varias filas y comprobación de pertenencia. Esta entrega sólo captura decisiones; el apply requerirá autorización y coordinación con quien implementa CH-08.

## Superficie exacta de CH-09

### Confirmación previa al propose (2026-10-30)

La alumna aprobó las decisiones de este explore y autorizó propose → apply → informe sin checkpoints rutinarios. Se volvió a verificar la tabla de endpoints de la consigna (p. 16, transcripción `docs/consigna/consigna-taller-mecanico.md`): **POST /ordenes declara 201, 409, 422; no incluye 404**. Por lo tanto se conserva la decisión 6: vehículo o repuesto inexistente **409**, y dado de baja **409**. El 404 queda para el recurso de ruta del GET de detalle. CH-08 figura ahora completo (28/28 tareas) en OpenSpec; su implementación se integra sin modificar su alcance.

Todas estas rutas se montarán en **`rutas_protegidas`**, con `route_class=RutaQueTraduceErrores`, handlers `async def`, cookie como mecanismo existente de sesión y control heredado de cambio obligatorio. Sin sesión → 401; cambio pendiente → 403. Donde se exige rol, su ausencia → 403 (DA-00/SU-04); roles vigentes consultados en la base, nunca autorizados por el JWT.

| Método y ruta | Quién, según la tabla de la consigna | Códigos de la tabla |
|---|---|---|
| `POST /ordenes` | RECEPCION, ADMIN | 201, 409, 422 |
| `GET /ordenes` (`estado`, `page`, `size`) | ADMIN, RECEPCION, MECANICO | 200, 422 |
| `GET /ordenes/{id}` | El personal, o el dueño del vehículo | 200, 403, 404 |
| `GET /estados-orden` | Autenticado | 200 |
| `GET /mis-ordenes` (`page`, `size`) | Autenticado | 200, 422 |

`iniciar`, `terminar` y `cancelar` son los otros endpoints de órdenes de la consigna, pero pertenecen a **CH-10**. CH-09 no agrega PATCH/DELETE de órdenes, CRUD del historial ni escritura del catálogo. La mención `/estados` en explore-CH-03 es una abreviatura errónea: manda **`/estados-orden`** de la consigna.

## Decisiones

| # | Pregunta | Decisión | Por qué | Alternativa descartada |
|---|---|---|---|---|
| 1 | ¿Qué implementar después de explorar? | Los cinco endpoints anteriores, schemas, repositorios, UoW y servicio del módulo existente `ordenes`; sin migraciones ni cambios al seed. | Ficha CH-09; modelos y restricciones ya corresponden a CH-03. | Adelantar las transiciones/aviso de CH-10 o crear endpoints auxiliares. |
| 2 | ¿Quién ve el detalle y lo propio? | Personal = ADMIN/RECEPCION/MECANICO vigente (SU-05); también cualquier autenticado cuyo id coincida con `orden.vehiculo.cliente.usuario_id` (SU-09). `/mis-ordenes` filtra por esa relación, sin exigir CLIENTE ni ampliar por ser personal. | RN-04/RN-17, DA-14 y DA-24. El dueño se identifica por FK, no por email, nombre o patente reutilizada. | Exigir CLIENTE o devolver todas al personal también en `/mis-ordenes`. |
| 3 | ¿Cómo resolver 403 y 404 del detalle? | Buscar orden por id con precarga; inexistente → 404; existente sin pertenencia ni rol de personal → 403. **[Agente]** Mensajes: `Orden no encontrada` y el 403 existente `No tiene permisos para realizar esta operación`. | Tabla del endpoint y C-06 distinguen orden ajena de inexistente. | Filtrar primero por dueño y convertir toda orden ajena en 404; agregar `requiere_rol` de personal al detalle. |
| 4 | ¿Qué recibe el alta? | Sólo `{vehiculo_id, falla, items:[{repuesto_id,cantidad}]}`; entradas y subentradas con `extra="forbid"`; al menos un ítem y cantidad entera positiva. Repetidos → 422 en DTO (DA-19). Precio, total, estado, fecha y mecánico no son campos de entrada. **[Agente]** Mantener el tratamiento habitual de enteros de Pydantic usado en cambios previos; no imponer nuevas longitudes máximas ni normalizar `falla`. | RN-10, ejemplo y convenciones previas. La unicidad de la base es respaldo, no sustituto del contrato. | Sumar cantidades repetidas; aceptar campos calculados; escribir antes de validar. |
| 5 | ¿Cuál es la secuencia transaccional? | Router obtiene el UoW con dependencia async; servicio abre **un solo** `async with uow`. Comprueba catálogo, vehículo y repuestos; copia precios y calcula total; agrega orden PENDIENTE con `mecanico_id=null`, ítems y primera línea `null → PENDIENTE`, `usuario_id=actor`; confirma al salir. **[Agente]** Construir el DTO de detalle dentro del bloque con datos explícitamente cargados; devolver 201 sólo después de la confirmación. | RN-10/RN-19, Flujo 6, patrón UoW y fechas por defecto ya acordadas. Un fallo de ítems, historial o commit revierte todo. | Commits por tabla; UoW creado por el servicio; serializar relaciones perezosas después del commit. |
| 6 | ¿Qué pasa con catálogo o referencias inválidas? | Catálogo vacío → 409; vehículo o repuesto inexistente/dado de baja → 409, nunca 404 en el alta (SU-07/SU-08, DA-21 y RN-16). **[Agente]** Si hay filas pero falta PENDIENTE, también 409 de catálogo no disponible; no repararlo desde la API. | La ruta crea una orden: sus referencias son conflictos del cuerpo, no recursos de ruta. DA-23 habla de listados; la prohibición de usar vehículos de baja viene de RN-16. | Crear catálogo al vuelo; usar repuesto dado de baja; responder 404 por referencia del alta. |
| 7 | ¿Cómo manejar importes y stock? | Copiar `repuesto.precio` a `item_orden.precio_unitario` una vez; total = suma de cantidad × precio copiado con Decimal; `NUMERIC(10,2)` y `NUMERIC(12,2)`; subtotal calculado en salida, dinero string de dos decimales. Crear no reserva stock, no exige disponibilidad y no descuenta stock: se permite cantidad mayor al stock. | RN-10/RN-13/RN-14, ejemplo `68000.00` y seed de orden 2 con cuatro bujías y stock dos. | Recalcular precios históricos con el precio actual; float; descuento o movimiento al crear. |
| 8 | ¿Qué hacer si total excede NUMERIC(12,2)? | **[Agente]** Validar total calculado ≤ `9999999999.99` antes de escribir; si excede → 409 `El total de la orden excede el importe permitido`, sin filas. No agregar límite arbitrario de ítems/cantidad. | Es el límite del tipo existente; ninguna entrada inválida puede terminar en 500. Es conflicto del resultado con lo almacenable; no es una nueva restricción de stock. | Dejar que un desbordamiento del driver llegue como 500; cambiar columnas o truncar/ajustar importes. |
| 9 | ¿Cuál es el detalle público? | Reutilizar el formato del ejemplo para POST y GET: `{id,estado,patente,total,creada_en,mecanico_id,falla,cliente,items,historial}`; `cliente` es nombre, no objeto. Ítems: `{repuesto_id,codigo,descripcion,cantidad,precio_unitario,subtotal}`. Historial: `{desde_estado,hasta_estado,usuario_id,cuando}`; sin usuario anidado ni hash. **[Agente]** Ítems por id ascendente; historial por `(cuando,id)` ascendente, usando ids para ordenar sin agregarlos al JSON. | Ejemplo textual; nota CH-04 evita ambigüedad cuando coinciden fechas. | Exponer el grafo ORM completo; sustituir `usuario_id` por un objeto; ordenar sólo por `cuando`. |
| 10 | ¿Cómo evitar N+1 y conservar bajas históricas? | **[Agente]** Método de detalle en `OrdenTrabajoRepository`: `joinedload` de vehículo→cliente, `selectinload` de ítems con `joinedload` del repuesto, y `selectinload` de historial; objetivo **3 SELECT de dominio** por detalle existente con 2 o 4 ítems. Sin filtro de baja en estas relaciones históricas. Mantener `lazy="raise"`. | C-15 exige cantidad fija, no un número concreto; DA-21 exige mostrar el repuesto de baja y RN-16 conservar datos. Las órdenes no tienen baja lógica. | Leer cada repuesto con un get dentro del bucle; JOIN simultáneo de dos colecciones con producto cartesiano; filtro global que borre relaciones históricas. |
| 11 | ¿Cómo listar órdenes? | Paginación común `{items,total,page,size,pages}`; estado opcional tipado `CodigoEstado`, valor desconocido (también vacío explícito) → 422; count y filas usan idéntico filtro. MECANICO ve todas, no sólo las asignadas (DA-24). **[Agente]** Orden por id ascendente; cada resumen contiene `{id,estado,patente,total,creada_en,mecanico_id,falla,cliente}` sin ítems/historial, con vehículo→cliente precargados. | DA-24, contrato enum de CH-03 y specs de paginación/repositorios. La consigna no fija el contenido de cada fila del listado. | Usar estado como texto sin enum; joins a colecciones que dupliquen conteo; incluir detalle completo por cada fila. |
| 12 | ¿Cómo funciona `/mis-ordenes` sin ficha? | Mismo resumen/paginación del listado, con filtro obligatorio por usuario propietario; sin ficha → página 1: `{items:[],total:0,page:1,size:<solicitado>,pages:1}` (DA-14). Página 2 en ese conjunto → 422, igual a cualquier listado vacío. Incluye órdenes históricas aunque el vehículo esté dado de baja. | RN-17 limita dueño, no estados ni vigencia del vehículo. DA-23 excluye vehículos de sus listados, no órdenes históricas. | Devolver 404 sin ficha; exigir rol CLIENTE; ocultar órdenes finalizadas o de vehículos dados de baja. |
| 13 | ¿Cómo exponer el catálogo? | Repositorio propio sólo lectura, **sin heredar BaseRepository**; GET devuelve lista simple de `{codigo,descripcion,posicion,es_final}` por posición. Con seed: PENDIENTE, EN_REPARACION, TERMINADA, CANCELADA; las dos últimas finales. **[Agente]** Catálogo vacío en GET → 200 `[]`; el 409 corresponde al POST de órdenes. | RN-19, DD-02/DD-A2, US-024 y C-17. GET lee filas, no rellena desde el enum. | CRUD público, repositorio con `add/update/delete`, paginar catálogo o inventar estados si faltan. |
| 14 | ¿Qué reutilizar de CH-08? | Componer su repositorio de repuestos con la misma sesión del UoW de órdenes; para alta sólo vigentes. **[Agente]** Resolver ids solicitados en una consulta parametrizada en lote si el contrato final lo permite; no copiar su servicio ni su punto de stock. Revisar API real al terminar CH-08 antes del apply. | CH-08 aún cambia; CH-09 sólo necesita lectura de precios/disponibilidad lógica. Punto único de stock será requerido en CH-10. | Editar CH-08 durante este explore; depender de nombres internos todavía no verificados; invocar stock para alta. |
| 15 | ¿Qué errores propios fijar? | **[Agente]** 409: `El catálogo de estados no está disponible`, `Vehículo inexistente o dado de baja`, `Repuesto inexistente o dado de baja`, y el mensaje de total de la decisión 8. Error de integridad no previsto: 409 con mensaje propio genérico `No se pudo crear la orden`; conservar traducción central y mapa de restricciones del UoW. | RN-18: sin SQL, constraint o texto de PostgreSQL en respuestas. | Mensajes del driver; 400 por conflictos; handler global nuevo en main.py. |
| 16 | ¿Hace falta bloquear precio o baja concurrente? | **[Agente]** No ampliar este change con locking o garantías de snapshot global: copiar precios leídos dentro del UoW y validar bajas en esa operación. Documentar que una baja/cambio de precio simultáneo no tiene semántica adicional definida. | La consigna no exige aislar concurrencia de alta contra catálogo/bajas/precios; CH-08 tiene su propio ajuste atómico de stock. | Incorporar bloqueos cruzados o nuevos niveles de aislamiento sin requisito ni escenario de aceptación. |

## Escenarios para specs y TDD posterior

Son criterios propuestos para el **propose/apply**; **no fueron ejecutados** en este explore.
Aplicar safety net, RED, GREEN, triangulación y refactor con evidencia sólo cuando se autorice el apply, sobre `<POSTGRES_DB>_test`, sin mocks de la base.

| ID | Tipo | Dado / Cuando | Entonces |
|---|---|---|---|
| E01 | Feliz — C-10 | Seed limpio; recepción crea vehículo 2 con repuesto 2 × 1 y 4 × 3. | 201; PENDIENTE, id 3, mecánico null, total `68000.00`, precios `32000.00`/`12000.00`, subtotales correctos y una línea inicial con actor 3. |
| E02 | Feliz/borde | ADMIN crea una orden con un ítem de cantidad 1 y otra con cuatro repuestos distintos. | Ambas 201; precios exactos copiados; no se exige ser dueño del vehículo. |
| E03 | Error de contrato | `items=[]`, cantidad cero/negativa/no entera, campo obligatorio ausente o repuesto repetido. | 422; ninguna orden, ítem o historial nuevo. Repetidos se rechazan en DTO, no al chocar con UNIQUE. |
| E04 | Error de contrato | Precio o total inyectados arriba o en ítem, estado/fecha/mecánico u otro extra. | 422; no se aceptan ni ignoran campos controlados por servidor. |
| E05 | Error — C-10 | Uno de dos repuestos no existe; repetir con vehículo inexistente. | 409; sin orden, ítems ni historial nuevos y sin cambios de stock/movimientos. |
| E06 | Error de baja | Repuesto o vehículo de baja en un alta nueva. | 409; no reutiliza por código o patente otra entidad vigente; nada creado. |
| E07 | Error/borde de catálogo | Catálogo vacío; luego catálogo con filas pero sin PENDIENTE. | 409 con mensaje propio; no crea ni repara catálogo y no deja escritura parcial. |
| E08 | Borde monetario | Precios de centavos, múltiples cantidades; luego total exacto máximo y un total que lo supera. | Aritmética Decimal, strings de dos decimales; máximo representable aceptado si demás datos válidos; exceso 409 sin escrituras. |
| E09 | Borde de stock | Cantidad pedida superior al stock, incluso stock cero. | 201 sin reserva/descuento/movimientos; validación de stock queda para terminar (CH-10). |
| E10 | Rollback | Fallo después del flush de orden/ítems o al agregar historial/confirmar. | Transacción completamente revertida; error propio sin texto de base. Una segunda sesión verifica ausencia de filas, no continuidad de secuencias. |
| E11 | Precio histórico | Crear orden, cambiar precio de repuesto mediante operación válida de CH-08, consultar detalle. | Precio unitario, subtotal y total de la orden conservan lo copiado; otra orden usa el precio nuevo. |
| E12 | Autenticación — C-06 | Cada una de las cinco rutas sin cookie; Bearer sin cookie; sesión con cambio obligatorio pendiente. | 401, 401 y 403 respectivamente; la ruta usa los controles ya existentes. |
| E13 | Roles — C-06 | Cliente intenta POST/GET general; MECANICO intenta POST; ADMIN/RECEPCION crean; tres roles de personal listan. | 403 en los primeros tres; creación autorizada 201, listados autorizados 200. Revocado/vencido no autoriza usando roles del token. |
| E14 | Propiedad — C-06 | Laura consulta orden 1 y orden 2; personal consulta ambas; usuario sin ficha consulta detalle ajeno; id inexistente. | 200/403 para Laura; 200 ambas para personal; 403 sin ficha; 404 inexistente. |
| E15 | Lo propio | Laura llama `/mis-ordenes`; personal sin ficha también; autenticado con ficha pero sin rol CLIENTE. | Laura sólo sus órdenes; sin ficha envoltorio vacío; con ficha sólo las suyas sin exigir CLIENTE. |
| E16 | Paginación | `page=1&size=1`, última página, `size=100`, `page=0`, `size=0/500`, página inexistente y listado sin resultados. | Defaults/límites comunes, total coherente; inválidos 422; cero resultados una página vacía y página 2 da 422. |
| E17 | Filtro — C-17 | MECANICO consulta PENDIENTE/EN_REPARACION y sin estado, con órdenes asignadas a distintos mecánicos. | 200 con todas las coincidentes, sin filtro por asignado; count idéntico al filtro; `estado=XYZ` o vacío explícito 422. |
| E18 | Catálogo — C-17 | Autenticado consulta catálogo sembrado; sin sesión; catálogo vacío. | Cuatro filas por posición con TERMINADA/CANCELADA finales; 401 sin sesión; 200 `[]` vacío. No endpoints de escritura. |
| E19 | Consultas — C-15 | Dos detalles reales, uno de 2 ítems y otro de 4, en sesiones nuevas y con el mismo actor. | Igual número de consultas SQL; objetivo de dominio 3; acceso a relaciones y serialización no agregan SQL. No prometer un total HTTP sin medir consultas de autenticación. |
| E20 | Orden de historial | Orden 2 con las dos líneas del seed que comparten `cuando`. | `null→PENDIENTE` precede `PENDIENTE→EN_REPARACION`, desempate por id; las filas no se editan para lograrlo. |
| E21 | Conservación | Dar de baja repuesto de una orden existente; vehículo de orden finalizada dado de baja. | Detalle, listado y mis-ordenes conservan referencias históricas, precios y pertenencia; las altas con esos ids fallan 409. |
| E22 | Superficie y errores | Recorrer rutas y errores nuevos; parámetro id no entero con sesión. | Cinco rutas nuevas previstas, protegidas y con clase traductora; sin CRUD appendOnly/catálogo; id no entero 422; errores propios sin SQL ni nombres de constraint. |

## Evidencia pendiente de C-15

**[Agente]** En el apply autorizado, preparar en el mismo `.http` una orden de dos ítems y otra de cuatro con los cuatro repuestos del seed, sin modificar `seed.py`. Hacer los dos GET de detalle separadamente con el mismo actor y sesiones HTTP equivalentes. Guardar un fragmento legible de la consola con **las sentencias SQL reales de ambos GET**, delimitadores por petición y conteos; destino propuesto `docs/evidencias/C-15-consultas.txt` (DA-30 fija la carpeta, no el nombre).

Con `SQL_ECHO=true`, registrar la consola únicamente durante ambos GET, separando login y creación de datos de la medición. La prueba automática podrá usar contador de eventos del motor, acotado al detalle y con sesión nueva por caso para impedir que la caché de identidad o carga previa falseen el resultado. Mostrar tanto las tres consultas esperadas del dominio como las consultas de autenticación/roles si se mide la petición completa; comparar ámbitos iguales y no presentar sólo tiempos ni sólo un contador sin SQL.

La consigna exige misma cantidad con 2 y 4 ítems, no un número absoluto. El objetivo de tres SELECT es **[Agente]**, sujeto a medición. **No existe evidencia de ejecución de C-15 producida por esta exploración.** Los pasos de desarrollo/seed manual corresponden a la alumna; el agente sólo podrá usar `_test` con autorización posterior.

## Pedidos para el propose

1. Crear por CLI el change exacto `ordenes-alta-consulta`, tras comprobar de nuevo estado y dependencias. Este explore **no lo crea**. CH-08 en curso permite planificar, pero su integración final se verifica antes de implementar; no marcarlo terminado.
2. Capturar las decisiones de esta tabla sin atribuir las **[Agente]** a la consigna o a la alumna; conservar lista de no especificado. No actualizar DA ni KB como parte de este pedido.
3. Proposal: cinco endpoints, reglas RN-10/RN-16/RN-17/RN-19 y aplicación RN-04/RN-18; CH-10 conserva transiciones, stock y aviso. Incluir DA-14/19/21/23/24, DD-02/DD-A2 y SU-05/07/08/09 con sus alcances exactos.
4. Design: DTOs de resumen/detalle, composición de UoW sobre sesión única, carga declarada, lectura histórica de bajas, enum `CodigoEstado`, orden `(cuando,id)`, errores, límite de total y ausencia de movimientos en alta. Verificar firmas reales de repositorios de CH-07/08, sin inventar API interna.
5. Specs: convertir E01–E22 en escenarios Dado/Cuando/Entonces por requisito, incluyendo rollback después de escribir, precio congelado, roles vigentes, vacío paginado, empate de historial y consulta histórica. Reutilizar specs existentes sin debilitarlas ni copiar reglas de CH-08 que no aplican a órdenes.
6. Tasks: safety net previo sobre archivos afectados; RED→GREEN→triangulación→refactor y tabla de evidencia TDD. Test de consultas con sesiones independientes; no contar filas ni duración como sustituto de consultas. Las corridas de tests/DB no están autorizadas por este explore.
7. Planificar `test/c06_401_403_propio.http`, `test/c10_alta_orden.http`, `test/c15_detalle_sin_n1.http`, `test/c17_catalogo_estados.http`. Cada uno con login propio, respuestas esperadas en comentarios y seed previo manual. Reutilizar convención de contraseña por variable de entorno de CH-08, sin copiar contraseña literal fuera del seed; separar cookies de distintos actores en C-06.
8. C-10 presupone seed limpio antes del archivo: `id=3` es evidencia de ese fixture, no requisito de continuidad de secuencias después de rollback. C-15 requiere archivo SQL de evidencia real además del `.http` y prueba de conteo.
9. Conservar estructura del PDF y clase traductora por router; ningún handler global, endpoint extra, instalación, migración o nuevo seed por conveniencia. Reanudar con autorización explícita; frenar al terminar este explore.

## No especificado en la consigna

Resoluciones heredadas, con origen preservado:

- **[Alumna] DA-14**: `/mis-ordenes` sin ficha devuelve envoltorio vacío; **DA-19**: repetidos 422; **DA-21**: baja de repuesto permitida aunque existan órdenes abiertas y lectura histórica de esos repuestos; **DA-24**: MECANICO ve todas. SU-05/07/08/09 completan interpretación de personal, referencias del alta y dueño.
- **[Alumna] DA-23** precisa ocultamiento en listados de vehículos; la prohibición de altas con vehículo de baja sí está en RN-16. No atribuir a DA-23 una nueva regla de órdenes.
- Notas ya acordadas CH-02/03/04: forma declarativa de traducción (`errores.py`/`rutas.py`), nombre `CodigoEstado`, `lazy="raise"`, fechas `now()` y desempate de historial por id; descripciones del catálogo elegidas por la alumna. **DA-30** fija `docs/evidencias/` para C-15.

Resoluciones propias de este explore, todas **[Agente]**:

- Mensajes 404/409 de decisiones 3/6/8/15; reutilización del 403 existente, sin exigir nuevos textos de validación Pydantic.
- Catálogo parcialmente cargado sin PENDIENTE → 409 al crear; GET de catálogo vacío → 200 `[]`.
- Resumen de listados con los ocho campos de decisión 11; orden de órdenes e ítems por id ascendente. El formato de detalle se toma del ejemplo, no es una invención de este explore.
- Validación del máximo NUMERIC(12,2) calculado antes de persistir, exceso → 409; sin límites arbitrarios adicionales de cantidad/ítems/longitud de falla.
- Estrategia concreta de precarga y objetivo de tres SELECT de dominio, construcción del DTO dentro del UoW y lectura en lote de repuestos cuando sea compatible con CH-08.
- Conservar órdenes históricas en listado/mis-ordenes aun con vehículo de baja; resolver id inexistente 404 antes de pertenencia, sin ocultar orden ajena como 404.
- Reutilizar tratamiento de enteros de cambios anteriores; no agregar normalización de `falla`, locking ni semántica adicional de concurrencia sobre precios/bajas.
- Nombre `docs/evidencias/C-15-consultas.txt` y delimitación de mediciones SQL; el destino y método se planifican, **no se ejecutaron**.

No se detectó una contradicción documental que impida planificar CH-09. Estas decisiones no equivalen a implementación ni a verificación de CH-08; cualquier requisito nuevo que aparezca en propose/apply se debe señalar y revisar antes de ampliar alcance.
