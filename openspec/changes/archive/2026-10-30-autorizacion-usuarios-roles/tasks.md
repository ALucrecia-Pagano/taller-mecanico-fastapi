# Tasks

Cada tarea de código sigue safety net → RED ejecutado → GREEN mínimo → triangulación de al menos dos casos por comportamiento → refactor con verde. Guardar comandos/salidas RED/GREEN y tabla de evidencia por tarea. Una tarea no se marca hasta cubrir todos sus escenarios. PostgreSQL real _test; sin mocks DB; sin .env, installs, commits/push.

## 1. Seguridad transversal

- [x] 1.1 Capturar safety net de archivos afectados (suite existente) y verificar baseline sin fallos; ante fallo preexistente detener/reportar sin arreglarlo. Registrar conteo y salida.
- [x] 1.2 TDD de error de autorización a HTTP: E403a-c y regresiones T6/T7 de errores; agregar error/mapa 403 con mensajes D4 y verificar ambos 403 y códigos previos en verde.
- [x] 1.3 TDD requiere_rol con base por petición: AU1-7; probar revocación/vencimiento/borde, asignación tras login, varios roles, sin bypass ADMIN y 401 antes403; verificar PostgreSQL real y mismo token en solicitudes sucesivas.
- [x] 1.4 TDD grupo protegido/control obligatorio único y composición: AU8-12, preservando D6/D7 y rutas abiertas; verificar cookie nueva/antigua sin sleeps y ADMIN provisional desbloqueado, sin inventar privilegios del MECANICO seed. Documentar integración futura en evidencia.

## 2. Personal

- [x] 2.1 TDD schemas administrativos PE4-7 y RO2: extra forbid, rol personal compartido D1=B y Contrasena; validar 72/73 bytes, vacío/NUL, CLIENTE, desconocido, fechas futuras zonificadas/pasadas/igual/sin zona, omitido/null; verificar 422 sin escritura/bcrypt.
- [x] 2.2 TDD alta vertical PE1-3: endpoint201 con respuesta D4, hash previo a UoW, usuario+rol+evento atómicos, duplicado409 propio; pruebas de tres roles, rollback y ausencia de secretos. Documentar contratos en evidencia junto al corte.

## 3. Roles e historial

- [x] 3.1 TDD asignación RO1-4 y RO6: usuario404, vigencia/otorgada_por/respuesta201, duplicado409 garantizado índice y evento atómico; verificar opciones de fecha válidas y entradas inválidas con mensajes propios.
- [x] 3.2 TDD reasignación RO5 y RO7: cierre viejo+flush antes de insertar, autoría histórica intacta y evento único; verificar éxito y rollback después del cierre/nueva fila/evento.
- [x] 3.3 TDD historial HI1-2: todas las asignaciones incluidas CLIENTE histórico, orden desde/id, campo vigente calculado y lista vacía; verificar forma exacta sin hash y borde vencido.
- [x] 3.4 TDD revocación RV1-4 y RO3: 200 con asignación cerrada, ausencia404 D2, usuario404, vencida abierta cerrable y rollback; conservar otorgada_por y fila antigua. Entregar c07_roles_vigencia.http con dos sesiones y no-cookie-jar, respuestas esperadas y notas de ejecución seed por Amanda.

## 4. Autoprotección

- [x] 4.1 TDD RN-05 AD1-4: autorevo409 aun con respaldo, revocar otro200, guardia de último ADMIN409 y excepción por vencimiento SU11; probar guardia pura usada por servicio para branch defensivo AD2 sin fabricar bypass HTTP ni mocks DB. Entregar c08_autoproteccion.http con resultado409 esperado.
- [x] 4.2 TDD coordinación CO1-4: advisory lock transaccional común para mutaciones ADMIN, incluida alta, y revalidación fresca de actor/objetivo/hora; carrera con dos conexiones independientes y sincronización sin sleeps, resultados200/403, un sobreviviente/un evento; rollback libera coordinación y actor obsoleto no escribe. Documentar D3 y clave estable en código/evidencia.

## 5. Auditoría y demostración de obligación

- [x] 5.1 TDD lectura eventos EV1-9: actor/textos/número exacto y atomicidad de todas mutaciones, compatibilidad CH05, ninguna fila en fallos/lecturas/login/logout, envoltorio y orden cuando/id descendente, vacío y límites size/page. Verificar endpoints reales y fila parcial invisible desde otra sesión.
- [x] 5.2 Entregar c09_cambio_obligatorio.http con nuevo@example.com, bandera403, /yo200, claves iguales422, cookie nueva válida y anterior401 sin espera; documentar README con los tres HTTP, seed previo y C06 diferido CH09. Verificar contenidos/contratos con tests HTTP adecuados sin ejecutar seed de desarrollo.

## 6. Integración y cierre de apply

- [x] 6.1 Ejecutar suite completa _test y openspec validate autorizacion-usuarios-roles --strict; verificar que las 52 fichas de escenarios están cubiertas con matriz ID→test/evidencia, traducción de todas rutas/errores y ningún cambio fuera de alcance. Guardar tabla TDD por tarea y resultados RED/GREEN/refactor; no archivar ni commitear.

