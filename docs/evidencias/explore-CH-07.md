# Explore de CH-07 — clientes-vehiculos

Fecha: 2026-10-30. Trabajado con **Copilot**, mediante `source-command-opsx-explore`.
Decisiones del explore aprobadas por Amanda. Sin código de producción, tests ni commits.

## Fuentes y contraste

- `docs/consigna/consigna-taller-mecanico.md`: Ejercicios 3 y 6, RN-01, RN-16, RN-17, endpoints de clientes/vehículos y C-01/C-19.
- `CHANGES.md`: CH-07, dependencias CH-02/CH-06, governance BAJO y archivos `.http` requeridos.
- `knowledge-base/03_actores_y_roles.md`, `04_modelo_de_datos.md`, `05_reglas_de_negocio.md`, `07_flujos_principales.md`, `09_decisiones_y_supuestos.md`.
- `AGENTS.md`, `openspec/` y `docs/evidencias/explore-CH-01.md` a `explore-CH-06.md`.
- Baseline actual: [`app/modules/clientes/models.py`](../../app/modules/clientes/models.py) ya declara `uq_vehiculo_patente_vigente`, `lazy="raise"` y las relaciones; [`repository.py`](../../app/modules/clientes/repository.py) sólo cubre el `add` mínimo del auto-registro; [`main.py`](../../main.py) aún debe incluir el router nuevo dentro de `rutas_protegidas`.

No apareció una contradicción de símbolos entre la extracción y la KB; ante una diferencia, manda el PDF.

## Decisiones

| # | Pregunta | Decisión | Por qué | Alternativa descartada |
|---|---|---|---|---|
| 1 | ¿Qué endpoints y permisos entran? | **[Agente]** Sólo los endpoints de la tabla de la consigna: `POST /clientes` y `GET /clientes/{id}` para `RECEPCION`/`ADMIN`; `POST /clientes/{id}/vehiculos` y `DELETE /vehiculos/{id}` para los mismos roles; `/mis-vehiculos` sólo autenticado y también dentro de `rutas_protegidas`. No se agrega `GET /clientes`. | Coincide con la tabla de la consigna, RN-17 y las notas de CH-06; `/mis-vehiculos` queda sujeto al cambio obligatorio. | Agregar un listado no pedido o exigir rol `CLIENTE` en `/mis-vehiculos`. |
| 2 | ¿Cómo se distinguen 401 y 403? | **[Agente]** Dejar que `rutas_protegidas` resuelva el control de contraseña pendiente y usar `requiere_rol` en las cuatro rutas de recepción; `/mis-vehiculos` usa sólo `get_usuario_actual`. | Mantiene 401 sin sesión, 403 sin rol y el bloqueo transversal de CH-06, sin duplicar dependencias. | Controlar autenticación/roles dentro de cada handler o aceptar roles del JWT. |
| 3 | ¿Cómo se modela la unicidad de patente? | **[Agente]** Escribir y dejar que la base aplique `uq_vehiculo_patente_vigente`; traducir el conflicto mediante el mapa de errores del UoW de clientes a 409 con mensaje propio. | RN-01/DD-03/DD-04 evitan carreras y permiten reutilizar una patente dada de baja. | Consulta previa de disponibilidad o UNIQUE global. |
| 4 | ¿Cómo se consulta `GET /clientes/{id}`? | **[Agente]** `ClienteRepository` devuelve el cliente con vehículos vigentes precargados en el método específico (`selectinload`/equivalente declarado); el servicio no dispara consultas adicionales. | DA-23 y Ej. 8 exigen ocultar bajas y evitar N+1; `lazy="raise"` hace visible cualquier incumplimiento. | Cargar vehículos en el router, usar lazy loading o hacer una consulta por vehículo. |
| 5 | ¿Cómo se comporta `/mis-vehiculos` sin ficha? | **[Agente]** Buscar la ficha por `usuario_id`; si no existe, responder 200 con lista vacía. Si existe, devolver sólo vehículos vigentes, precargados. | DA-14 y RN-17 definen “lo propio” como autenticación, no como rol ni como existencia de ficha. | 404 por falta de ficha o 403 por no tener rol CLIENTE. |
| 6 | ¿Cómo se da de baja un vehículo? | **[Agente]** Usar `VehiculoRepository(SoftDeleteRepository)` y marcar `borrado_en`; devolver 204. Antes, consultar por join al catálogo de estados si hay órdenes con `es_final = false`; si las hay, 409. | RN-16 exige conservar datos, excluir bajas y bloquear PENDIENTE/EN_REPARACION sin acoplar CRUD de órdenes al módulo clientes. | DELETE físico, permitir siempre la baja o depender de una lista fija de estados en Python. |
| 7 | ¿Qué ocurre si el vehículo no existe o ya está dado de baja? | **[Agente]** DELETE responde 404; alta de vehículo con cliente inexistente responde 404; no reutilizar un vehículo dado de baja como si siguiera vigente. | Los códigos están fijados por la tabla de endpoints y el recurso de la ruta; evita modificar datos históricos. | Convertir todos los casos en 409 o revelar texto de la base. |
| 8 | ¿Cómo se implementan los listados? | **[Agente]** No se agrega `GET /clientes` porque no figura en la tabla. Cualquier listado que sí exista en CH-07 usa exactamente `openspec/specs/paginacion` (CH-02): `page`/`size`, envoltorio estándar, total con el mismo filtro y página inexistente 422. | Mantiene el alcance textual de la consigna y la especificación de paginación ya aprobada. | Agregar `GET /clientes`, cambiar el envoltorio o usar `limit`/`offset`. |
| 9 | ¿Qué contratos y mensajes se fijan? | **[Agente]** Schemas separados, entrada `extra="forbid"`, `anio` 1950..2100 y respuestas sin campos internos. Mensajes 409: `Ya existe un cliente con ese documento`, `Ya existe un vehículo vigente con esa patente` y `El vehículo tiene órdenes abiertas`, sin texto SQL. | Ej. 3, RN-01, RN-16 y RN-18; los textos exactos no están en la consigna y quedan fijados como decisión aprobada. | Reutilizar modelos de tabla como DTO o propagar `IntegrityError`. |
| 11 | ¿Cómo se normalizan los identificadores? | **[Alumna]** La patente de entrada se normaliza a mayúsculas y sin espacios antes de guardar; el documento sólo pierde espacios en los bordes. Se prueban ambas reglas. | Evita que `ac456ef` o `AC 456 EF` salteen la unicidad vigente; conserva el documento interno sin modificarlo más allá de los bordes. Es **No especificado en la consigna**. | Dejar el texto sin normalizar o aplicar normalización agresiva al documento. |
| 12 | ¿Qué ocurre con DELETE y el orden de respuesta? | **[Alumna]** DELETE de un vehículo ya dado de baja responde 404, como la decisión 3d de CH-02; los vehículos se ordenan por `id`. Vincular un cliente existente con un usuario queda fuera de alcance. | Hace explícita la semántica ya decidida y evita agregar una operación no pedida. | DELETE idempotente 204, orden no determinista o endpoint de vinculación. |
| 10 | ¿Qué evidencia HTTP y contraseña se prepara? | **[Agente]** Crear en el propose `test/c01_parametro_invalido.http` y `test/c19_baja_vehiculo.http`; la contraseña se referencia con `{{$processEnv TALLER_PASSWORD_PRUEBA}}`, igual que CH-06, sin hardcodearla. | C-01/C-19 son los casos propios y el seed debe seguir siendo configurable. | Poner `Taller2026!` en los `.http` o mezclar casos en un archivo sin estado claro. |

## Escenarios

### Feliz

- `RECEPCION` o `ADMIN` crea un cliente válido: 201, sin password ni campos internos.
- El mismo actor agrega un vehículo válido a un cliente existente: 201.
- `GET /clientes/{id}` devuelve cliente y sólo vehículos vigentes, con una carga declarada.
- Un cliente autenticado con ficha obtiene sus vehículos vigentes en `/mis-vehiculos`; sin ficha obtiene 200 con `[]`.
- Se da de baja un vehículo sin órdenes abiertas: 204; luego otra ficha puede registrar la misma patente: 201.

### Error

- Sin cookie: 401; con sesión sin `RECEPCION`/`ADMIN` (incluidos MECANICO y CLIENTE): 403.
- Cuerpo extra o `anio` fuera de 1950..2100: 422, sin ejecutar el servicio.
- Documento repetido o patente vigente repetida: 409 con mensaje propio y sin texto de PostgreSQL.
- Cliente inexistente al agregar vehículo o cliente inexistente al consultar: 404.
- Vehículo con una orden PENDIENTE o EN_REPARACION: baja 409 y permanece vigente.

### Borde

- Una patente baja puede reutilizarse; dos vehículos vigentes con la misma patente no.
- Órdenes TERMINADA o CANCELADA no impiden la baja.
- Vehículos dados de baja no aparecen en `GET /clientes/{id}` ni `/mis-vehiculos`.
- Página fuera de rango, `size=0` o `size=101`: 422 según `openspec/specs/paginacion`; cero resultados devuelve `items=[]`, `total=0`, `pages=1`.
- Un usuario autenticado sin ficha no debe provocar lazy loading, 404 ni 500.

## No especificado en la consigna

- La normalización de patente a mayúsculas/sin espacios y de documento quitando sólo bordes (decisión aprobada [Alumna]).
- Formato exacto de los DTO de cliente/vehículo, salvo los campos de entrada indicados.
- Los textos exactos de esos mensajes dejaron de estar abiertos: fueron fijados como `Ya existe un cliente con ese documento`, `Ya existe un vehículo vigente con esa patente` y `El vehículo tiene órdenes abiertas`.
- Si `GET /clientes` debe exponerse: resuelto, no se agrega porque no figura en la tabla.
- Orden de los vehículos: resuelto, por `id`.
- DELETE repetido: resuelto, 404 por decisión 3d de CH-02.
- Vinculación posterior de un cliente con usuario: fuera de alcance.
- Si las órdenes abiertas deben bloquearse con una consulta `EXISTS` o una carga de entidades; se recomienda `EXISTS` con join al catálogo.
- Redondeo/formato interno de `pages`: se aplica sin cambios la spec de paginación de CH-02.

## Pedidos para el propose

1. Crear el change `clientes-vehiculos` sólo después de confirmar el status OpenSpec y sus artefactos requeridos; no agregar `GET /clientes`.
2. Ampliar el repositorio mínimo de clientes con métodos nombrados por la lectura: cliente con vehículos vigentes, cliente por id, ficha por usuario y vehículos propios vigentes.
3. Implementar la baja en `SoftDeleteRepository` y la comprobación de órdenes abiertas con join a `estado_orden.es_final`, manteniendo el mapa de conflictos `uq_vehiculo_patente_vigente`.
4. Mantener todos los handlers `async def`, UoW construido por dependencia y abierto por el servicio, sin `commit()` en repositorios.
5. Añadir tests PostgreSQL reales en `test/pytest/` para 201/401/403/404/409/422, precarga sin N+1, baja y reutilización de patente; agregar los `.http` de C-01 y C-19.
6. Verificar que `main.py` incluye el router de clientes dentro de `rutas_protegidas` antes de incluir el grupo en la app.
7. Incorporar escenarios explícitos para normalización de patente/documento, DELETE repetido 404, orden por id y ausencia de vínculo cliente-usuario; marcar lo no textual como `[Alumna]` o `[Agente]`.
