# Design

## Context

Ver `proposal.md` para la motivación. Entrada definitiva: `docs/evidencias/explore-CH-05.md` (Codex; consigna leída desde conversión `.md`, el PDF manda). CH-01–04 están completos; el código observado tiene sólo models en usuarios/clientes, `rutas_abiertas` en main y mecanismos puros Contrasena/DatosToken/hash/JWT de CH-04. El arnés ofrece lifespan real, cliente httpx, base_sembrada y guarda `_test`. No se ejecutaron tests al proponer.

## Goals / Non-Goals

**Goals:** componer seguridad existente con transacciones y contratos HTTP verificables; conservar separación entre autenticación y autorización, y todos los escenarios R/L/I/K/A/P/Y/V del explore.

**Non-Goals:** requiere_rol, control de cambio obligatorio, grupo protegido, administración de usuarios/roles/eventos (CH-06), ampliar clientes más allá de add (CH-07), migraciones, rehash de cuentas al login, revocación de JWT al logout, dependencias nuevas y tests temporales.

## Decisions

### D1. Capas y dependencias

Crear `schemas.py`, `repository.py`, `unit_of_work.py`, `service.py`, `router.py` de usuarios y repositorio mínimo de clientes; `dependencies.py` en core. Router `/auth`, route_class=RutaQueTraduceErrores, handlers async, dependencias Annotated y responses separadas de modelos. `main.py` incluye auth en rutas_abiertas antes de copiar el grupo a app (regla CH-01). Alternativa de crear el grupo protegido ahora descartada por alcance CH-06.

El router/dependencias construye UoW y servicios; el servicio sólo abre bloques y nunca crea UoW ni hace commit. UoW de usuarios compone usuarios, roles, clientes y eventos sobre la misma sesión. Repos usan flush, consultas ligadas y precarga declarada; sin leer relaciones lazy. Cambios sin migración. Se usan los compact rules fastapi/fastapi-patterns/tdd/python-testing del registro con los overrides de AGENTS (rutas raíz/core, async, 409, refactor por ciclo y DB real).

### D2. Contratos y valores no especificados

Registro: `{email,nombre,password,documento,telefono}`; login: `{email,password}`; cambio: `{password_actual,password_nueva}`. Entradas con extra=forbid y TODOS los campos de contraseña con Contrasena existente. No imponer normalización de email/documento ni complejidad adicional no acordada. Schemas de respuesta nunca filtran hash/token.

**[Alumna] D7 — No especificado en la consigna:** validación cruzada Pydantic rechaza igualdad literal password_nueva==password_actual con 422, antes del servicio, sin bcrypt extra. Alternativa de permitir igualdad descartada porque apagaría debe_cambiar_password sin cambiar clave. La autenticación de la cookie no ejecuta bcrypt.

Los cuerpos 200 de login y /yo son los fijados por consigna/DA-16. Detalles no fijados de respuesta de registro, logout y cambio se mantienen mínimos (mensaje propio y sin secretos); texto puntual de esos mensajes no es criterio nuevo de aceptación. No agregar campos públicos sin revisión.

### D3. Registro y restricciones

Hash antes del bloque del UoW. Crear usuario activo sin obligación pendiente, asignación CLIENTE con otorgada_por=NULL, ficha y evento (actor=email, acción `Registro de cliente <email>`) en un único bloque. Sin comprobación previa de unicidad; se dejan actuar los UNIQUE, también ante carreras. `uq_usuario_email` → `El correo ya está registrado`; `uq_cliente_documento` → `El documento ya está registrado`. Textos exactos: **No especificado en la consigna**, confirmados. `uq_cliente_usuario_id` conserva fallback propio si aparece inesperadamente; nunca SQL interno. Un documento de ficha sin usuario se rechaza igual, sin vincularla.

Alternativa de consultas previas descartada por DD-04. R1–R5 comprueban las cuatro tablas y datos previos desde otra sesión; rollback tras escrituras parciales sin exigir que las secuencias vuelvan atrás (sus huecos son normales).

### D4. Login y roles

Orden: límite → usuario → una verificación real/ficticia → registrar resultado propio → 401 o token/cookie. Usar app.state.hash_ficticio y app.state.semaforo_bcrypt mediante dependencias, nunca generar el ficticio por petición. Correo inexistente siempre falla aunque el verificador ficticio devolviera verdadero. Error común `Correo o contraseña incorrectos` (**No especificado en la consigna**). **[Alumna] ajuste 3:** usuario inactivo verifica hash real y registra fallo aun con clave correcta. Alternativa de rechazo temprano descartada para no distinguir cuentas.

Roles se consultan vigentes (revocada_en NULL y vence_en NULL o futuro) al emitir JWT, ordenados; son informativos. Se reutiliza emitir_token de CH-04. El token sólo se publica tras confirmar las operaciones necesarias. Si registrar un intento falla, no se declara sesión exitosa.

### D5. Límite y sesión propia

Una consulta ligada devuelve conteo y fecha necesaria para desbloqueo, filtrando correo/IP, últimos 60 s y posteriores al último éxito del par; subconsulta del último éxito en la misma sentencia. Para n>=5 fallos, el desbloqueo es cuando quedan menos de 5: usar el quinto más reciente (no siempre el más viejo si hubo más de cinco). Ventana con borde de salida a 60 s; tests con reloj/datos controlados, sin sleeps. Retry-After=ceil(segundos positivos restantes). DA-11 fija segundos restantes; el redondeo es precisión confirmada por Amanda, no cita textual del PDF.

DD-05: dependencia construye una operación/gestor para registrar intentos; esa operación abre `session_factory()` propia y un IntentosUoW suministrado por composición. El servicio solicita registrar el resultado, no construye el UoW. Confirmar éxito/fallo antes de devolver; escribir comentario sobre filas que sobreviven rollback y el costo transaccional. No compartir sesión con petición. IP=request.client.host; no confiar en X-Forwarded-For. Éxito conserva filas y reinicia conteo. 429 no inserta ni verifica.

Alternativa de borrar filas o registrar 429 descartada por RN-08/DA-11. El índice existente (email,ip,cuando) respalda el filtro; no se planea nuevo esquema. El patrón contar-luego-anotar no promete serialización de logins concurrentes (C-05 exige secuencia), no introducir locks ni una política nueva en este change.

### D6. Cookie, autenticación y mensajes

Cookie access_token, HttpOnly, SameSite=Lax, Max-Age=config, Secure=COOKIE_SECURE; Path=/ sin Domain (**No especificado en la consigna**, confirmado). Centralizar emisión/eliminación con mismo alcance; logout público idempotente no revoca JWT copiados. Alternativa Bearer/JSON descartada por consigna. Cookie válida prevalece porque Authorization se ignora, no se rechaza por estar presente.

get_usuario_actual lee cookie, decodifica y busca usuario; rechaza inexistente/inactivo y compara float iat con password_cambiada_en.timestamp(), estrictamente menor. No usar fromtimestamp ni segundos enteros. Contexto Pydantic interno con usuario y DatosToken (sin serializar modelo de tabla directamente).

**[Alumna] D6 — No especificado en la consigna:** normalizar todos los rechazos de esta dependencia a `Sesión no válida o vencida`. Atrapar TokenInvalido del mecanismo puro y relanzar error con ese mensaje; NO cambiar security.py ni el escenario T6 de errores-de-dominio, que sigue probando `Token inválido` cuando una dependencia lo lanza directamente. Login mantiene D3. Actual incorrecta en cambio usa error 401 propio de credenciales, sin exponer detalles; no confundir con rechazo de sesión.

Agregar error de dominio de límite con segundos restantes y soporte de headers en la clase de ruta para Retry-After, con mapa 429; conservar comportamiento de los demás errores. Alternativa de HTTPException en service o handler global descartada por capas. Test T7 debe seguir viendo todas las subclases importadas.

### D7. Cambio y perfil

Cambio autentica en grupo abierto, verifica actual y calcula hash nuevo antes del bloque; en un UoW actualiza hash/fecha completa/bandera y evento `Cambio de contraseña`. Emitir nueva cookie después de confirmar y con iat>=fecha del cambio. Preparar instante completo de cambio explícito (evitar now() de inicio transaccional que podría preceder a la sesión) y preservar fracción. Actual incorrecta o fallo no modifica datos ni emite cookie. /yo retorna exactamente DA-16, roles_vigentes frescos y roles_token del contexto, ordenados. Alternativa de exigir otro login descartada por RN-07.

### D8. Pruebas y trazabilidad

**[Alumna] ajuste 9:** ningún test mide tiempos. Espía del nombre usado por servicio verifica exactamente una llamada a verificar_password con app.state.hash_ficticio para inexistente; cero bcrypt en 429 e igualdad contractual. Reloj controlable por parámetro/monkeypatch, sin instalar freezegun ni mockear DB. C-04/C-05 conservan observación temporal manual en .http.

| Explore | Spec | Test propuesto |
|---|---|---|
| R1–R5 | registro-de-clientes | test_auth_registro.py |
| L1–L6 | sesiones-de-usuario | test_auth_login.py |
| I1–I8 | intentos-de-acceso | test_intentos_acceso.py |
| K1–K5 | sesiones-de-usuario | test_auth_cookie.py |
| A1–A8 | sesiones-de-usuario | test_auth_dependencias.py |
| P1–P5 | sesiones-de-usuario y contrasenas | test_auth_password.py |
| Y1–Y3 | sesiones-de-usuario | test_auth_yo.py |
| V1–V4 | contrasenas | test_auth_schemas.py |
| 429 y regresiones T6/T7 | errores-de-dominio | test_rutas.py |

Por cada comportamiento: safety net de archivos existentes, RED ejecutado, mínimo GREEN, segundo caso distinto y todos los escenarios, refactor con verde después de cada paso. Tests de integración API/httpx con base real `_test`, sin mocks DB; tablas/estado se consultan directamente para atomicidad e intentos. Guardar RED/GREEN con encabezados y tee -a sin borrar fallos propios; tabla de evidencia TDD al devolver apply. No escribir todos los tests antes de producción: trabajar verticalmente por comportamiento.

## Risks / Trade-offs

- [Hash ficticio/costo antiguo] → conservar trade-off CH-04: costos diferentes en hashes viejos pueden producir diferencias; sin rehash automático.
- [Conexión retenida por lectura previa a bcrypt] → SQLAlchemy puede autobegin al leer. Cerrar explícitamente el alcance de lectura antes del cálculo en registro/cambio y no confundir un bloque UoW aún no abierto con ausencia de transacción; obtener datos necesarios sin relaciones lazy y revalidar dentro del bloque de escritura cuando corresponda.
- [Sesión propia comparte referencias] → registrar email/IP/resultado escalares; no transportar entidades entre sesiones.
- [Tiempos no automatizados] → mecanismos comprobados por espías; observación C-04/C-05 en demostración manual, sin prometer igualdad temporal por pasar pytest.
- [Conversiones PDF] → ante un símbolo dudoso manda el original; la conversión no redefine RN.

## Migration Plan

No migraciones ni instalación nuevas. Tras permiso explícito de apply CRÍTICO, desarrollar y probar sólo sobre `<POSTGRES_DB>_test` con guarda; pedir [PERMISO] en cada corrida contra base. Amanda ejecuta seed/.http sobre desarrollo con su permiso, nunca el agente por defecto. Actualizar README (uso de cookies, endpoints, cambio, límite, tests y ejecución .http); pypdf no va en requirements.

La última tarea será guardar `pytest -v` en `docs/evidencias/pytest-CH-05.txt`. No marcar CH-05 completo ni archivar aquí; revisión y archive posteriores. Sin commit/push (Amanda). Rollback de implementación futura: retirar cambios de código bajo revisión, sin migraciones ni borrado de datos; esta planificación no ejecuta rollback.
