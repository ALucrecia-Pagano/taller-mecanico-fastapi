# Explore CH-10 — `ordenes-ciclo-aviso`

Fecha: 2026-10-30. Trabajado con **Copilot**, en modo autónomo mediante
`source-command-opsx-explore`.

Alcance: decisiones para el propose de CH-10. No se ejecutaron pytest, Alembic,
`seed.py`, la API ni consultas a la base. No se creó el change en
`openspec/changes/` ni se modificó ningún archivo fuera de esta evidencia.
Las decisiones propias están marcadas **[Agente]**.

## Fuentes contrastadas

- `docs/consigna/consigna-taller-mecanico.md` (tabla de endpoints, RN-11/RN-13/RN-14,
  Ejercicios 6 y 8, C-11/C-12/C-13); ante discrepancias, manda el PDF.
- `CHANGES.md`, `AGENTS.md` y `knowledge-base/05_reglas_de_negocio.md`.
- `knowledge-base/06_funcionalidades.md`, `07_flujos_principales.md`,
  `09_decisiones_y_supuestos.md` (DA-09, DA-21, DA-22, DD-13, SU-10) y
  `11_casos_de_prueba.md`.
- Specs `repuestos-stock-precios`, `modelo-de-datos`, `unidad-de-trabajo`,
  `solo-agregado`, `autorizacion` y `errores-de-dominio`.
- Contexto de `openspec/changes/ordenes-alta-consulta/` (CH-09 en curso) y
  evidencias `explore-CH-01.md` a `explore-CH-09.md`.

## Decisiones

| # | Pregunta | Decisión | Por qué | Alternativa descartada |
|---|---|---|---|---|
| 1 | ¿Cuál es la superficie exacta? | **[Agente]** Sólo `POST /ordenes/{id}/iniciar`, `POST /ordenes/{id}/terminar` y `POST /ordenes/{id}/cancelar`. Se reutilizan schemas/serialización del detalle de CH-09 y se responde 200 con la orden actualizada. | Es exactamente la tabla de la consigna y el scope de CH-10. | Agregar PATCH/DELETE, endpoints de transición genéricos o CRUD del historial. |
| 2 | ¿Qué autorización declara cada ruta? | **[Agente]** `iniciar` lleva `requiere_rol(MECANICO)`; `terminar` no depende de un único rol porque admite MECANICO asignado o ADMIN; `cancelar` no lleva `requiere_rol` y decide el servicio entre RECEPCION, ADMIN o dueño. Todas están en `rutas_protegidas`, con `async def` y `RutaQueTraduceErrores`. | La consigna exige esos actores; la ruta de cancelar explícitamente no lleva `requiere_rol`. Roles siempre vigentes en la base. | Permitir que el JWT decida el rol, exigir rol global para cancelar o crear una ruta para cada rol. |
| 3 | ¿Cómo se ordenan 401, 403, 404 y 409? | **[Agente]** La dependencia protegida resuelve 401/cambio obligatorio. Tras localizar la orden, una falta de permiso responde 403 antes de comprobar el estado; id inexistente responde 404. Sólo con permiso se valida la transición y se responde 409 si es inválida. | La consigna fija 403 antes que 409 para terminar/cancelar y distingue 404. | Filtrar por estado antes de autorización, ocultar una orden existente como 404 o convertir toda referencia inválida en 409. |
| 4 | ¿Qué transición realiza `iniciar`? | **[Agente]** Sólo `PENDIENTE → EN_REPARACION`; en el mismo UoW asigna `mecanico_id = actor`, cambia el estado y agrega una línea de historial con `desde_estado`, `hasta_estado` y `usuario_id` del actor. | RN-11: el mecánico que inicia queda asignado; toda transición se audita. | Aceptar iniciar desde cualquier estado, conservar `mecanico_id` previo o confirmar por escrituras separadas. |
| 5 | ¿Qué permiso tiene el mecánico al terminar? | **[Agente]** Debe coincidir con `orden.mecanico_id` y tener `MECANICO` vigente en la base; alternativamente basta `ADMIN` vigente. Un MECANICO no asignado, rol vencido/revocado o usuario sin esos roles recibe 403. | DA-22 y RN-04: la relación y la vigencia se comprueban en cada petición. | Autorizar a cualquier MECANICO, confiar sólo en `mecanico_id` o aceptar el rol informado por el token. |
| 6 | ¿Cómo termina y descuenta stock? | **[Agente]** Sólo `EN_REPARACION → TERMINADA`. En un único UoW, por cada ítem se llama al punto único atómico de stock de CH-08 con salida negativa, motivo `"Orden terminada"`, `orden_id` y actor; luego se cambia estado y se agrega un historial. | RN-13/RN-14, DD-13 y DA-09; evita duplicar la lógica de stock y preserva append-only. | Editar `repuesto.stock` directamente, hacer un UoW por ítem o registrar un movimiento sin actualizar stock. |
| 7 | ¿Qué sucede con stock insuficiente? | **[Agente]** El punto único aborta la operación y el servicio traduce el fallo a conflicto de dominio 409 con mensaje propio. El rollback cubre estado, `mecanico_id` si correspondiera, stock, movimientos e historial; no queda ninguna escritura de la terminación. | Es el requisito explícito de RN-13 y C-11; SU-10 exige 409. | Descontar los ítems anteriores y fallar en el siguiente, devolver 422 o continuar con stock negativo. |
| 8 | ¿Se pueden terminar órdenes con repuestos dados de baja? | **[Agente]** Sí, si el ítem ya pertenece a la orden: cada repuesto se lee mediante `get_by_id_including_deleted`; su baja no impide descontarlo ni crear el movimiento. | DA-21 separa órdenes existentes de altas nuevas; el filtro de borrado lógico no puede ocultar el insumo histórico. | Rechazar la terminación por baja o reutilizar la lectura pública que filtra bajas. |
| 9 | ¿Qué hace `cancelar`? | **[Agente]** Sólo `PENDIENTE → CANCELADA`; autorizado RECEPCION/ADMIN vigente o dueño de la ficha del vehículo. En un único UoW cambia estado y agrega historial, sin tocar stock, movimientos ni ítems. | RN-12, C-13 y la regla de que cancelar no descuenta inventario. | Permitir cancelar EN_REPARACION/TERMINADA, exigir CLIENTE o descontar/liberar stock. |
| 10 | ¿Cómo se identifica al dueño? | **[Agente]** Por `vehiculo.cliente.usuario_id`, como en CH-09; no por patente, email o nombre. La autorización se evalúa antes del estado y también exige usuario autenticado. | SU-09 y DA-24 mantienen una única relación de pertenencia. | Comparar datos mutables o permitir a cualquier CLIENTE cancelar cualquier orden. |
| 11 | ¿Cómo se ordena y devuelve el historial? | **[Agente]** El detalle de respuesta carga el historial con precarga declarada y lo ordena por `(cuando, id)` ascendente, incluyendo la línea recién agregada. No se agregan endpoints de historial. | La fecha puede coincidir; CH-04 fijó el desempate por id y el requisito prohíbe N+1. | Ordenar sólo por `cuando`, depender de lazy loading o devolver sólo el nuevo evento. |
| 12 | ¿Cuándo se agenda el aviso? | **[Agente]** `terminar` recibe `BackgroundTasks` en el router y agenda el aviso sólo después de que el servicio/UoW confirmó. La tarea simula `await asyncio.sleep(0.5)` y escribe en el log; una falla de la tarea no cambia el 200 ni revierte la transacción. | Ejercicio 8, RN operativa y C-12; no hay Redis ni reintentos. | Agendar antes del commit, ejecutar el aviso dentro del UoW o hacer que su error vuelva 500. |
| 13 | ¿Qué transición es válida según el catálogo? | **[Agente]** El servicio valida códigos del catálogo (`PENDIENTE`, `EN_REPARACION`, `TERMINADA`, `CANCELADA`); cualquier otra combinación responde 409. No se inventan estados ni se edita `estado_orden`. | RN-11/RN-19 y catálogo de CH-09. | Usar un enum local como fuente exclusiva o aceptar estados no sembrados. |

## Resoluciones aprobadas para el propose

- **[Alumna] Concurrencia**: `iniciar`, `terminar` y `cancelar` cambian el estado al
  principio del UoW mediante `UPDATE ... WHERE id = :id AND estado = :estado_esperado`.
  Si no se actualiza ninguna fila, se revierte y responde 409 sin tocar stock ni
  historial. Se agrega un test con dos terminaciones concurrentes: una responde 200,
  la otra 409 y el stock se descuenta una sola vez. Es una decisión marcada
  «No especificado en la consigna».
- **[Alumna] Cancelar**: sólo se permite desde `PENDIENTE`; se respeta la consigna y
  RN-11 porque no define otra transición válida.
- **[Alumna] Mensajes propios**: `"La orden no está en un estado que permita esta
  operación"`, `"Stock insuficiente para el repuesto <código>"` y `"Solo el mecánico
  asignado o un administrador pueden terminar la orden"`.
- **[Alumna] Respuesta 200**: detalle de la orden con el mismo contrato del GET de CH-09.
- **[Alumna] Aviso**: el log incluye `orden_id` y `cliente_id`, nunca el email. No hay
  reintentos ni persistencia ante reinicio; queda documentado como limitación.

## Escenarios a pedir en el propose

### Feliz

- Mecánico vigente inicia una orden `PENDIENTE`: 200, asignación, `EN_REPARACION` e historial.
- ADMIN vigente termina una orden `EN_REPARACION`: 200, una salida negativa por ítem,
  `"Orden terminada"` con `orden_id`, stock actualizado, `TERMINADA` e historial.
- Tras reponer, el mecánico asignado termina: C-12 verifica todas las escrituras y el aviso
  en el log después del commit/respuesta.
- Dueño cancela su orden `PENDIENTE`: 200, `CANCELADA`, historial y stock intacto.

### Error

- C-11: stock insuficiente en cualquier ítem → 409 y estado, stock, movimientos e historial
  idénticos al estado previo.
- Mecánico no asignado, rol MECANICO no vigente, ADMIN no vigente, usuario ajeno o cliente
  sin permiso → 403 antes de 409 por estado.
- Orden inexistente → 404; transición no permitida → 409; sin sesión → 401.
- Falla del aviso en segundo plano: la operación confirmada conserva 200.

### Borde

- Repuesto dado de baja después de crear la orden: se termina y descuenta mediante
  `get_by_id_including_deleted`.
- Cada ítem genera exactamente un movimiento negativo; una orden no tiene ítems repetidos
  por contrato de CH-09.
- Historial con igual `cuando`: el orden por `(cuando, id)` es estable.
- Cancelar no modifica stock aunque la orden tenga ítems; terminar nunca acepta estado
  `PENDIENTE` ni `TERMINADA`.
- Dos terminaciones concurrentes sobre la misma orden: sólo una actualiza el estado,
  descuenta stock y agrega historial; la otra responde 409 sin escrituras propias.

## Pedidos para el propose

- Mantener la integración con los modelos, schemas, precargas y UoW de CH-09 sin crear una
  segunda representación de orden.
- Exponer en el servicio una operación reutilizable del punto único de stock de CH-08 que
  haga el ajuste atómico y el INSERT append-only juntos; no actualizar `stock` desde CH-10.
- Definir excepciones/mensajes propios para transición inválida y stock insuficiente, traducidos
  a 409 sin texto de PostgreSQL.
- Declarar el orden de autorización: dependencia protegida, existencia, permiso, estado,
  escrituras; usar roles vigentes de la base.
- Probar C-11/C-12/C-13 en `<POSTGRES_DB>_test`, más una prueba de fallo del BackgroundTasks;
  documentar el aviso sin Redis, reintentos ni garantía tras reinicio.
- Verificar que todas las escrituras de terminar (incluidos movimientos e historial) salen de
  un solo bloque `async with uow` y que el aviso se agenda sólo tras su salida exitosa.

## No especificado en la consigna

- El texto exacto de los mensajes de 403, 404 y 409, salvo que sean propios y no expongan la
  base; se propone reutilizar los mensajes de dominio existentes.
- El schema exacto de la respuesta 200 de las tres transiciones; se propone el detalle de orden
  ya establecido por CH-09.
- El nombre de la función/método interno del punto único de stock y si vive físicamente en
  `repuestos.service`, `repuestos.unit_of_work` o una abstracción compartida.
- El mecanismo exacto para detectar stock insuficiente (resultado de UPDATE, CHECK o excepción
  de dominio), siempre que sea atómico, traduzca a 409 y revierta todo.
- El nivel/logger y el texto exacto del aviso simulado; sólo se exige `sleep(0.5)`, log y
  ejecución posterior al commit/respuesta.
- La política de reintento, persistencia, cola externa y comportamiento ante reinicio del
  proceso: quedan fuera de alcance por la consigna.
- Si el aviso debe identificarse por `orden_id`, cliente o ambos en el log.
- El comportamiento frente a dos terminaciones concurrentes: la consigna declara fuera de
  alcance el bloqueo contra actualización perdida; la decisión aprobada de CH-10 lo
  resuelve mediante actualización condicional para las tres transiciones.
- La concurrencia de distintas órdenes que consumen el mismo repuesto no se especifica;
  no se amplía el alcance más allá de impedir dos transiciones de la misma orden.
- Si una transición repetida debe devolver un mensaje distinto por estado concreto; el código
  común exigido es 409.
