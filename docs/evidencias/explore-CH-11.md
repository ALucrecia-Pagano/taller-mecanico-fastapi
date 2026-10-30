# Explore CH-11 — `cierre-entrega`

Fecha: **2026-10-30**. **Trabajado con Codex**, usando `source-command-opsx-explore`.

## Alcance y estado

Exploración documental y estática. Este trabajo sólo autoriza los archivos nuevos
`docs/evidencias/explore-CH-11.md` y `docs/evidencias/auditoria-consigna.md`.
No se ejecutaron pytest, Alembic, seed, peticiones HTTP ni consultas a ninguna base;
no se modificaron README, roadmap, código, tests, `.http`, dependencias ni specs.
No se abrió `.env`, no se instalaron paquetes y no se creó el change CH-11.

`openspec list --json` resolvió la raíz local del proyecto y mostró
`ordenes-ciclo-aviso` en curso, con 0/11 tareas en el momento de la consulta.
`openspec status --change cierre-entrega --json` informó que el change no existe.
Es una fotografía del estado, no una afirmación sobre el progreso posterior del otro agente.
Todo lo relativo a iniciar, terminar, cancelar, aviso y C-11/C-12/C-13 queda
**⏳ pendiente CH-10**, aun si aparecen archivos durante esta exploración.

## Fuentes

- `docs/consigna/consigna-taller-mecanico.md`: ejercicios pp. 10–15, casos pp. 20–21,
  credenciales ficticias del seed p. 18 y evaluación/formato de entrega p. 22.
  Se usa la transcripción solicitada; ante una discrepancia manda el PDF original.
- `CHANGES.md`, ficha **CH-11 `cierre-entrega`** y tablas Caso → Change / RN → Change.
- `knowledge-base/12_criterios_de_evaluacion.md`, `08_arquitectura_propuesta.md`
  (Entrega), `09_decisiones_y_supuestos.md` (DA-07/26/30, DD-A4).
- `README.md`, `requirements.txt`, `requirements-dev.txt`, `.gitignore`,
  nombres y estado vacío de los dos secretos de `env.example` (sin mostrar valores),
  `migrations/versions/` y tests de configuración, repositorio, migraciones, seed y detalle.
- Specs durables `migraciones`, `datos-iniciales` y las capacidades usadas por la auditoría.
- `docs/evidencias/C-14-psql.txt`, `capturas/C-14-solo-agregado.png`,
  `C-15-consultas.txt`, `verify-CH-03.md`, `verify-CH-09.md` y auditoría adjunta.

## Qué exige el cierre

CH-11 es transversal y depende de CH-10. No incorpora una regla de negocio nueva.
Su alcance es **documentación y verificación**, governance BAJO según el roadmap;
una corrección de código que surja de la auditoría requiere su test y autorización
de ese alcance. Esta exploración no autoriza ninguna corrección ni corrida posterior.

| Entregable | Exigencia de la consigna / CHANGES | Situación observada | Trabajo de CH-11 |
|---|---|---|---|
| Repositorio entregable | Código completo, `requirements.txt`, `env.example`, `alembic.ini`, `migrations/`, `test/`; no subir `.env` (p. 22). | Los componentes existen; `.gitignore` incluye `.env`. Esto no certifica el historial ni el contenido final que se enviará. | Comprobar el conjunto realmente entregado, rutas, archivos ignorados/versionados y ausencia de credenciales reales sin exponerlas. |
| README final | Entorno virtual, dependencias, `.env` y generación de clave fija, migraciones, seed, servidor (p. 22); roadmap agrega creación de bases y ejecución de `.http`/pytest. | Los pasos ya existen; la narración mezcla estados de changes anteriores y mantiene referencias pendientes que ya cambiaron. | Unificar el estado final, eliminar contradicciones y conservar instrucciones ejecutables desde cero y por terminal. |
| Requirements | Dependencias declaradas y stack mínimo de la consigna; pruebas separadas por DA-26. | `requirements.txt` declara FastAPI, SQLModel, SQLAlchemy async, asyncpg, Alembic, pydantic-settings, bcrypt y PyJWT con pisos/topes; dev incluye aplicación y pytest/httpx/lifespan. | Confirmar instalación limpia de ambos archivos y coherencia con imports. No agregar paquetes por conveniencia. |
| Arranque desde cero | Proyecto que levanta y esquema creado por `alembic upgrade head` en base vacía: condiciones excluyentes. | Hay instrucciones y tests reales de migración; no se ejecutó un arranque limpio del estado final en este explore. | Registrar entorno/comandos/salidas de un recorrido final autorizado, sin sustituirlo por lectura de código. |
| C-14 vigente | Captura de `psql`: seis rechazos de UPDATE/DELETE y uno por FK (p. 22). | Existen texto y PNG de CH-04; el texto contiene exactamente esos siete rechazos. | Contrastar con migraciones/modelos finales; conservar la captura si sigue vigente o renovarla si cambia el esquema o falta trazabilidad. |
| C-15 vigente | Captura o fragmento de consola con SQL del detalle de 2 y 4 ítems (p. 22). | Existe SQL real automático por ASGI: 5 SELECT HTTP por ambos detalles, 3 de dominio y 2 de autenticación/roles. Su origen es un evento del motor, no una captura de consola con SQL_ECHO. | Conservar esta evidencia útil; verificar su aceptación formal o complementarla con consola sobre la versión final y con ámbitos comparables. No se afirma que falte toda evidencia. |
| Auditoría | Verificar ejercicios, RN, casos, estructura, contratos, restricciones y prácticas prohibidas; no crea requisitos nuevos. | `auditoria-consigna.md` contiene la revisión estática y los riesgos; CH-10 queda pendiente. | Revalidar el documento al finalizar CH-10, resolver hallazgos con evidencia y distinguir pendiente, corregido y no reproducido. |
| Casos y suite finales | Roadmap: corrida completa de pytest y de los 19 casos desde esquema vacío + seed; respuestas esperadas en comentarios. | La última evidencia completa revisada es CH-09: 645 passed; es histórica y anterior al cierre CH-10. | Preparar una matriz final de los 19 casos, restaurar seed por archivo/grupo y registrar resultados sin presentar ejecuciones históricas como nuevas. |

## Evaluación y condiciones excluyentes

Los pesos de la p. 22 suman 100 %. El cierre debe aportar trazabilidad, no cambiar esos pesos.

| Criterio / ejercicio | Peso | Qué revisar al cerrar |
|---|---|---|
| Proyecto, configuración y ciclo de vida / 1 | 8 % | Estructura; Settings sin secretos por defecto; motor/fábrica en lifespan; get_session; salud. |
| Modelos, relaciones y migraciones / 2 | 14 % | Restricciones e índices parciales; catálogo por FK; navegación; dos migraciones, una manual; upgrade y downgrade. |
| Contratos y CRUD / 3 | 10 % | Schemas separados, extras prohibidos, códigos, PATCH parcial y paginación; entrada inválida nunca en 500. |
| Autenticación / 4 | 16 % | Bcrypt fuera del bucle y bajo semáforo; orden del login; límite; hash ficticio; cookie HttpOnly. |
| Autorización / 5 | 14 % | 401/403, roles actuales de la base, autoprotección, dos grupos de rutas, iat y lo propio. |
| Repositorios y UoW / 6 | 20 % | Dos jerarquías; clase del modelo; flush sin commit; precarga; creación/apertura/confirmación/cierre; operaciones múltiples. Transiciones: ⏳ pendiente CH-10. |
| Integridad / 7 | 10 % | Tres disparadores appendOnly, precio histórico transaccional e intento de acceso en sesión propia; evidencia C-14. |
| Lecturas sin N+1 y asincronía / 8 | 8 % | Cantidad fija de consultas y ausencia de bloqueos; evidencia C-15. Aviso: ⏳ pendiente CH-10. |

Las **tres condiciones excluyentes textuales** son: proyecto que no levanta,
esquema que no se crea con `alembic upgrade head` sobre base vacía y credenciales reales
en el repositorio. Las dos primeras no quedan certificadas por esta revisión estática;
la tercera requiere inspección del conjunto entregado y, si corresponde, su historia,
sin publicar secretos. Que `.env` esté ignorado no prueba por sí solo que nunca se versionó.

## Puesta en marcha desde cero: recorrido a documentar y verificar después

**[Agente]** El propose debe separar preparación, ejecución y evidencia, indicando el
responsable y la base antes de cualquier paso con efectos. Los pasos siguientes son
un plan; **no se ejecutaron** ni conceden permiso para tocar una base:

1. Anotar sistema, Python/PostgreSQL y revisión del código; crear un entorno virtual nuevo.
2. Instalar `requirements.txt`; para pytest, `requirements-dev.txt`. No exigir un lockfile:
   la consigna no lo pide. Registrar versiones efectivas cuando se autorice la prueba limpia.
3. Copiar `env.example` a `.env` local y completar secretos fuera del repositorio.
   Generar la clave una sola vez mediante `python -c "import secrets; print(secrets.token_urlsafe(64))"`.
   Nunca guardar su salida en evidencias. No generar otra clave en cada arranque.
4. Crear las bases de aplicación y prueba con nombres inequívocos. Amanda ejecuta los
   pasos sobre desarrollo; cualquier ejecución del agente requerirá alcance explícito
   y seguirá limitada a la base `_test` según las reglas del proyecto.
5. Verificar, en una base autorizada vacía, `alembic upgrade head`,
   `alembic downgrade base` y `alembic upgrade head`; registrar head y resultado.
   Los tests existentes `test_m1_*`, `test_m2_*` y `test_m4_*` ya definen parte de esa comprobación.
6. Ejecutar `python seed.py` sobre el esquema migrado, comprobar datos de ejemplo e ids.
   El seed vacía datos: el README ya lo informa y no debe perder esa advertencia concreta.
7. Arrancar `uvicorn main:app --reload`; comprobar salud, documentación y rutas según permisos.
8. Preparar REST Client con contraseña sólo en el editor/proceso, cookies nombradas y
   `# @no-cookie-jar`; ejecutar los grupos C-01–C-19 con seed previo por archivo cuando corresponda.
   C-14 usa SQL, no necesita un `.http` ficticio; C-03/C-04 y C-11/C-12 pueden compartir archivo.
9. Capturar C-14 y consola SQL de C-15 con datos iniciales conocidos, registrar revisión y fecha.
   Tras C-14, reponer el seed para restaurar la secuencia consumida por el INSERT rechazado.
10. Ejecutar una sola suite completa de cierre cuando haya autorización; conservar salida,
    comprobar que sólo usó `_test` y dejarla sin datos. Cualquier fallo no entendido se informa.

## Evidencias: presencia, alcance y vigencia

| Caso | Evidencia actual | Comprobación estática | Riesgo / siguiente paso |
|---|---|---|---|
| C-14 | `C-14-psql.txt` y `capturas/C-14-solo-agregado.png`, ambos presentes; fecha de archivo 2026-10-28. | Texto: 6 rechazos por `rechazar_cambio_solo_agregado()` y FK `fk_orden_trabajo_estado_estado_orden`. Hay dos migraciones 0001/0002; `test_seed.py::test_s14_c14_sobre_el_seed` prueba las siete sentencias reales. | Presencia no equivale a vigencia final. Contrastar con schema final y revalidar que la captura corresponde; renovar sólo si hace falta. |
| C-15 | `C-15-consultas.txt`, presente; fecha de archivo 2026-10-30. | SQL real capturado por `before_cursor_execute` durante GET ASGI; mismo actor, sesiones nuevas, JSON dentro de medición, sin parámetros/resultados/cookies. `test_ordenes_detalle.py::test_c15_sql_real_dos_y_cuatro_items_consultas_fijas` genera el archivo. | La p. 22 pide consola: verificar aceptación formal o complementar ese formato y comprobar que CH-10 no cambia el costo ni las cargas del detalle. No se invalida la medición real existente ni se afirma una medición final hoy. |

## Pedidos para el propose

1. Crear `cierre-entrega` por CLI sólo cuando se solicite; volver a consultar estado y
   dependencia CH-10. No confundir planificación disponible con implementación cerrada.
2. Proposal sin endpoints ni reglas nuevas: README final, auditoría y paquete de entrega,
   requirements, puesta en marcha limpia, suite/casos y vigencia formal de C-14/C-15.
3. Especificar criterios de aceptación separados para las tres condiciones excluyentes,
   los 8 ejercicios, 20 RN, 19 casos, estructura y esquema; enlazar `auditoria-consigna.md`.
4. Resolver primero los riesgos estáticos señalados por auditoría: rangos físicos en módulos
   anteriores y ubicación exclusiva de la contraseña ficticia. No llamarlos fallos reproducidos
   ni cambiarlos sin test rojo y autorización de la corrección.
5. Revisar la referencia literal a la contraseña ficticia en `openspec/specs/datos-iniciales/spec.md`
   (el test S16 sólo busca `.py`); conservar la regla sin repetir el valor fuera del seed.
   No tratarla como credencial real de producción ni publicar su texto en esta exploración.
6. Design con pasos y responsables para clean room y evidencias; distinguir ámbito automático
   ASGI, consola y verificación manual de Amanda. Registrar versión final/fecha/comandos.
7. Tasks verificables y acotadas: documentación no exige tests tautológicos; cualquier
   corrección de comportamiento sigue TDD estricto y las skills del dominio correspondiente.
   No proponer instalación de herramientas o dependencias no solicitadas.
8. README: reemplazar textos históricos contradictorios, consolidar endpoints/roles/errores y
   pasos de instalación, clave, bases, migración, seed, uvicorn, REST Client y pytest; enlazar evidencias.
9. Validar requisitos instalables en entorno nuevo usando archivos existentes, sin confundir
   un mínimo admitido con la versión concreta registrada en una evidencia anterior.
10. Diseñar recorrido final C-01–C-19 con respuestas esperadas, sesiones y seed previo por grupo;
    C-11/C-12/C-13 siguen **⏳ pendiente CH-10** y se incorporan sólo al cerrar esa dependencia.
11. Preparar evidencias C-14/C-15 vigentes, con el formato textual de p. 22; no borrar capturas
    históricas ni presentar la evidencia ASGI como una ejecución manual de consola.
12. Conservar todas las corridas fallidas y dejar un informe final de cobertura/hallazgos
    resueltos/pendientes; actualizar roadmap y archivar sólo con autorización de esas acciones.

## No especificado en la consigna

- **[Agente]** Nombres de los dos archivos de esta exploración, estructura de las matrices,
  severidades de riesgos y clasificación estática/ejecutada/reportada. El usuario los pidió.
- **[Agente]** Registrar revisión/entorno/fecha y separar evidencias automáticas, consola y
  manual es una práctica de trazabilidad propuesta; no cambia pesos ni agrega un caso C-20.
- La consigna no exige lockfile, Docker, CI, cobertura porcentual mínima, documentación de
  despliegue productivo ni nuevas herramientas de seguridad. No convertir su ausencia en defecto.
- La carpeta `docs/evidencias/` viene de **DA-30 [Alumna]**; la suite en `test/pytest/` y
  `requirements-dev.txt`, de **DA-26 [Alumna]**. No atribuir esos nombres al PDF.

## Riesgos y faltantes, sin contar CH-10

1. **Alta prioridad:** demostrar arranque y migración desde base vacía en el estado final;
   es una condición excluyente, hoy respaldada por evidencia histórica, no por nueva ejecución.
2. **Alta prioridad:** descartar credenciales reales en el conjunto entregado/historia sin
   exponerlas. `.env` ignorado y plantilla vacía son controles parciales, no certificación completa.
3. **Alta prioridad, hipótesis estática:** límites de tipos físicos en contratos de módulos
   anteriores podrían llevar valores extremos al driver y producir 500; reproducir con TDD autorizado.
4. **Media:** comprobar aceptación formal o complementar con consola la evidencia SQL real
   C-15; conservar/revalidar C-14. No falta toda la evidencia de esos casos.
5. **Media, defecto documental confirmado:** eliminar la repetición de la contraseña ficticia
   fuera de `seed.py` (consigna, líneas 756–757) y ampliar la comprobación de ubicación;
   no es hallazgo confirmado de un secreto real.
6. **Media:** README final coherente y recorrido completo de instalación/casos/suite tras CH-10.
7. **Baja:** mantener inventario final, enlaces de evidencias y trazabilidad de resultados;
   no dar por actual el total 645 de CH-09 cuando cierre una nueva versión.

La auditoría detallada y las referencias por requisito están en `auditoria-consigna.md`.
Esta entrega termina aquí: no implica propose, apply ni permiso de ejecución.
