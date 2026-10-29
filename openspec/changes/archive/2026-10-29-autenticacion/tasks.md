# Tasks

Sólo ejecutar tras pedido explícito de apply y aprobación CRÍTICA. Cada `[PERMISO]` exige confirmar antes de esa corrida; el agente sólo opera `<POSTGRES_DB>_test`. Amanda opera desarrollo. Ninguna tarea se ejecutó durante propose. Entrada definitiva: `docs/evidencias/explore-CH-05.md`.

En cada bloque vertical, repetir RED → GREEN → TRIANGULAR → REFACTOR por comportamiento (no escribir todos los tests primero). No pasar a producción sin RED ejecutado ni al siguiente comportamiento sin GREEN; mínimo dos casos distintos por comportamiento y todos los escenarios antes del refactor. Guardar encabezados/resultados con `tee -a` en `docs/evidencias/CH-05-tdd-rojo.txt` y `CH-05-tdd-verde.txt`; conservar fallos propios y explicar correcciones. Todo refactor requiere otra ejecución verde y permiso si toca base. Si el safety net falla, frenar como fallo preexistente. No commits/push ni instalaciones.

## 1. Checkpoint y safety net

- [x] 1.1 Obtener aprobación explícita del design CRÍTICO y alcance de apply; verificar que quedan fuera autorización/grupo protegido y que sólo se autorizó `_test`, registrando la aprobación en la conversación.
- [x] 1.2 Cargar fastapi, fastapi-patterns, tdd y python-testing-patterns y reglas de persistencia aplicables; verificar overrides de AGENTS y mapa de escenarios del design, sin instalar skills/paquetes.
- [x] 1.3 [PERMISO] Ejecutar baseline de suites existentes para archivos a modificar (rutas, errores, hash, token, lifespan y UoW; suite completa si la integración lo requiere) sobre `_test`, comprobar guarda y capturar N passing; frenar si falla, sin corregirlo silenciosamente.

## 2. Contratos de autenticación y D7

- [x] 2.1 RED: escribir caso V1 contra schemas públicos inexistentes en `test/pytest/test_auth_schemas.py`; [PERMISO] ejecutar hasta fallo esperado si el arnés de sesión toca base, guardar RED y verificar que falla por la conducta ausente.
- [x] 2.2 GREEN: crear schemas mínimos en usuarios con extra=forbid y Contrasena; [PERMISO] ejecutar el caso si toca base y guardar GREEN; verificar aceptación de 72 bytes.
- [x] 2.3 TRIANGULAR: agregar V2–V4 por campo (password registro/login, password_actual/nueva) con ASCII/UTF-8 72/73, vacío/NUL y extras; por cada nuevo fallo escribir mínimo código y [PERMISO] ejecutar RED/GREEN si el arnés toca base, verificando 422 y no llamadas a bcrypt.
- [x] 2.4 RED/GREEN/TRIANGULAR: agregar P3/P3b para igualdad con/sin cambio pendiente; implementar validador cruzado mínimo después de RED; [PERMISO] ejecutar cada ciclo si toca base, comprobar 422 y cero bcrypt, sin cambios/evento/cookie en la integración posterior.
- [x] 2.5 REFACTOR de schemas sin cambio de conducta; [PERMISO] ejecutar después de cada paso si toca base y verificar todos V/P3 verdes. Documentar en schemas que igualdad/vacío/NUL son No especificado en la consigna, [Alumna] D7 donde corresponde.

## 3. Registro atómico

- [x] 3.1 RED: escribir R1 por API en `test_auth_registro.py` y snapshot de cuatro tablas desde otra sesión; [PERMISO] ejecutar en `_test` y guardar fallo por endpoint ausente.
- [x] 3.2 GREEN: crear mínimo de repositorios/UoW/service/router de usuarios y ClienteRepository sólo add, hash antes del bloque y cuatro escrituras; registrar router en grupo abierto en el orden de CH-01; [PERMISO] ejecutar R1, verificar 201 y cuatro filas, sin hash expuesto.
- [x] 3.3 TRIANGULAR: R2 email duplicado, R3 documento vinculado y R4 ficha sin usuario, una conducta por ciclo; mapear uq_usuario_email y uq_cliente_documento tras RED; [PERMISO] ejecutar cada RED/GREEN, verificar mensajes exactos 409, ausencia de filas sueltas y ficha previa intacta.
- [x] 3.4 TRIANGULAR: R5 fallo después de escritura parcial con base real; [PERMISO] ejecutar RED/GREEN y verificar rollback de las cuatro tablas desde otra sesión, sin exigir continuidad de ids; comprobar que no hay consulta previa de unicidad.
- [x] 3.5 REFACTOR de registro; [PERMISO] ejecutar después de cada paso y conservar R1–R5 verdes. Crear `test/c02_registro.http` con 201/409 esperados, documento de ficha sin usuario y consultas de comprobación descritas; actualizar README sobre registro, atomicidad y ejecución de C-02; verificar archivos por lectura.
- [x] 3.6 [PERMISO] Demostrar C-02 ejecutando seed antes del archivo y consultas de filas; Amanda lo corre en desarrollo, el agente sólo en `_test` expresamente autorizado. Verificar 201/409 y cuatro tablas intactas tras rechazos, guardar resultado sin secretos.

## 4. Intentos y límite

- [x] 4.1 RED: escribir I8 e I7 en `test_intentos_acceso.py` para persistencia propia e independencia de rollback; [PERMISO] ejecutar primer RED en `_test`, verificando fallo por operación inexistente.
- [x] 4.2 GREEN/TRIANGULAR: componer operación de registro con session_factory e IntentosUoW suministrados por dependencias, nunca construidos en service; [PERMISO] ejecutar cada ciclo y verificar éxito/fallo confirmados aunque revierte petición. Agregar comentario DD-05 con costo de filas persistidas.
- [x] 4.3 RED/GREEN: I1 con cinco fallos y sexto bloqueo; crear conteo ligado en una consulta y error de límite después del RED; [PERMISO] ejecutar cada ciclo, verificar sin bcrypt ni sexta fila.
- [x] 4.4 TRIANGULAR: I2–I6, reloj/datos controlados sin sleeps ni medir tiempos: ceil restante, salida de ventana, éxito reinicia sin borrar, separación correo/IP y X-Forwarded-For ignorado; [PERMISO] ejecutar cada RED/GREEN, verificar una consulta de conteo y bloqueo hasta quedar menos de cinco fallos.
- [x] 4.5 RED/GREEN/TRIANGULAR: E429/E429b en `test_rutas.py`, límite en handler y dependencia; extender traducción con 429 y Retry-After sólo tras RED; [PERMISO] ejecutar cada ciclo y regresión T6/T7 si el arnés toca base, verificar mensaje interno Token inválido intacto y mapa completo.
- [x] 4.6 REFACTOR de consulta/operación/errores; [PERMISO] ejecutar tras cada paso y verificar I1–I8/E429 verdes. Documentar en README límite, reinicio sin borrado y Retry-After redondeado; verificar comentario de sesión propia y ausencia de creación UoW en service.

## 5. Login y cookie

- [x] 5.1 RED: L1 en `test_auth_login.py`; [PERMISO] ejecutar en `_test`, guardar fallo por login inexistente.
- [x] 5.2 GREEN: implementar mínimo login ordenado límite → usuario/verificación → intento propio → emisión, reutilizando recursos app.state; [PERMISO] ejecutar L1 y verificar cuerpo/cookie sin JWT en JSON.
- [x] 5.3 TRIANGULAR: L2/L3 con espía exactamente una verificar_password usando hash_ficticio para inexistente y mismo 401; [PERMISO] ejecutar cada RED/GREEN, verificar que rama inexistente nunca autentica y que no se miden tiempos.
- [x] 5.4 TRIANGULAR: L4/L5 inactivo clave correcta/incorrecta y L6 roles vigentes excluyendo revocados/vencidos; [PERMISO] ejecutar cada RED/GREEN, verificar exito=false para inactivo, roles informativos y sin cookie en fallos.
- [x] 5.5 RED/GREEN/TRIANGULAR: K1/K2/K4 en `test_auth_cookie.py`, emisión con todos los atributos y logout público con/sin cookie; [PERMISO] ejecutar cada ciclo, verificar Secure configurable, Path=/ sin Domain y borrado con mismo alcance.
- [x] 5.6 REFACTOR login/cookie; [PERMISO] ejecutar después de cada paso y verificar L/K verdes. Crear `test/c03_c04_login.http` con casos 200/401, cuerpo sin token, atributos y observación manual de tiempos C-04 (sin umbrales pytest); actualizar README login/logout/cookies; verificar lectura.
- [x] 5.7 Crear `test/c05_limite_intentos.http` con seis intentos, Retry-After, cinco filas y observación manual del rechazo rápido; verificar resultados esperados escritos y seed previo por archivo. [PERMISO] Ejecutar la demostración C-05 con seed previo y consultas DB (Amanda en desarrollo; agente sólo `_test` autorizado), verificar resultados sin medir tiempos en pytest.

## 6. Usuario actual y perfil

- [x] 6.1 RED: A1 y K3 en `test_auth_dependencias.py`; [PERMISO] ejecutar primer fallo esperado en `_test`.
- [x] 6.2 GREEN: crear get_usuario_actual/contexto Pydantic en core/dependencies.py y autenticación propia en /auth/yo, sin requiere_rol/control de cambio; [PERMISO] ejecutar y verificar cookie ausente/Bearer solo 401 neutro D6.
- [x] 6.3 TRIANGULAR: A2–A4 (tokens inválidos/alterados/vencidos/claims y usuarios inexistentes/inactivos) y K5 cookie válida+header; [PERMISO] ejecutar cada RED/GREEN, verificar todos rechazos D6 y header ignorado sin alterar TokenInvalido puro/T6.
- [x] 6.4 TRIANGULAR: A5–A8 con instantes controlados, anterior/igual/posterior y mismo segundo; [PERMISO] ejecutar cada RED/GREEN y verificar comparación float estricta sin truncar ni sleeps.
- [x] 6.5 RED/GREEN/TRIANGULAR: Y1/Y2 y la parte de Y3 correspondiente a /yo en `test_auth_yo.py`, forma DA-16, divergencia por revocación/vencimiento y consulta con cambio pendiente; [PERMISO] ejecutar cada ciclo y verificar roles desde base y token separados, listas ordenadas sin secretos. Y3 completo con cambiar-password se verifica en 7.4, cuando exista ese endpoint.
- [x] 6.6 REFACTOR de dependencia/perfil; [PERMISO] ejecutar después de cada paso y verificar A/K/Y1/Y2 y la consulta /yo de Y3 verdes. Completar C-03 sin cookie/Bearer y README /yo, D6 y límites CH-06; verificar documentos por lectura.

## 7. Cambio de contraseña

- [x] 7.1 RED: P1 en `test_auth_password.py`, snapshot de hash/fecha/bandera/evento; [PERMISO] ejecutar fallo esperado en `_test`.
- [x] 7.2 GREEN: verificar actual y hashear antes del bloque, transacción de cambio+evento y emisión después del commit; [PERMISO] ejecutar P1 y verificar 200, evento actor=email y nueva contraseña efectiva.
- [x] 7.3 TRIANGULAR: P2 actual incorrecta y P4 fallo antes de confirmar; [PERMISO] ejecutar cada RED/GREEN y verificar estado intacto y ausencia de cookie nueva/evento en fallos.
- [x] 7.4 TRIANGULAR: integrar P3/P3b contractual con usuario con/sin obligación, P5 y A8 mismo segundo y Y3 acceso con obligación; [PERMISO] ejecutar cada ciclo y verificar cero bcrypt en igualdad, bandera pendiente conservada y renovación válida sólo tras confirmar.
- [x] 7.5 REFACTOR del cambio; [PERMISO] ejecutar después de cada paso y verificar P1–P5 verdes. Actualizar README con cambio, rechazo de igualdad [Alumna], invalidación inmediata, y completar ejemplos .http si necesarios, sin mover el C-09 completo fuera de CH-06; verificar documentos por lectura.

## 8. Integración, revisión y evidencia final

- [x] 8.1 [PERMISO] Ejecutar `c03_c04_login.http` después de seed y revisar C-03/C-04 de punta a punta: 200, cookie y cuerpo, 401 idénticos y observación manual de tiempos; Amanda opera desarrollo, agente sólo `_test` autorizado. Verificar que C-02 y C-05 ya tienen sus demostraciones y consultas de los grupos correspondientes.
- [x] 8.2 Auditar cobertura R/L/I/K/A/P/Y/V y E429 contra specs/explore, mapa de restricciones, orden include_router, ausencia de secretos/SQL concatenado/IO bloqueante, main/dependencies correctos y alcance CH-06 intacto; verificar sin nuevas dependencias/migraciones y pypdf fuera de requirements.
- [x] 8.3 Completar tabla TDD por tarea con test/layer/safety net/RED/GREEN/triangulación/refactor y referencias a evidencias; verificar que no se borraron corridas fallidas ni se afirma igualdad temporal a partir del espía. Dejar preparado el resumen de revisión sin marcar archive ni hacer commits.
- [x] 8.4 Validar artefactos con `C:/Users/hp/AppData/Roaming/npm/openspec.cmd validate autenticacion --strict` y verificar éxito; comprobar que README y tres `.http` están actualizados y que el siguiente paso sólo se recomienda tras revisión humana.
- [x] 8.5 [PERMISO] Como última tarea, ejecutar la suite completa `pytest -v` exclusivamente contra `<POSTGRES_DB>_test` y guardar su salida íntegra en `docs/evidencias/pytest-CH-05.txt` (Git Bash: `set -o pipefail` y `pytest -v 2>&1 | tee docs/evidencias/pytest-CH-05.txt`); verificar código de salida cero y todos los tests pasando, sin ocultar errores del pipe. No marcar completa ante fallo; registrar y corregir con TDD y permiso de cada nueva corrida, dejando esta evidencia final al cierre.
