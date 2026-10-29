# Explore CH-05 — autenticacion

Fecha: 2026-10-29. CH-05 se trabajó con **Codex** mediante `source-command-opsx-explore`. Governance **CRÍTICO**. Sólo exploración y documentación; sin código, commits ni creación de change. Decisiones confirmadas por Amanda en la conversación; permiso explícito para este resumen y Engram.

## Fuentes y contraste

La consigna se leyó desde la conversión a `.md`: `docs/consigna/consigna-taller-mecanico.md` (22 páginas). Ante cualquier duda manda el PDF original; la extracción puede romper símbolos y tablas.

- Consigna: RN-02 y RN-07 (p. 7), RN-08/RN-09 (p. 8), Ejercicio 4 (p. 12), autenticación y grupos de rutas (p. 13), sesión propia de intentos (p. 14), endpoints `/auth/*` (p. 15), C-02 a C-05 (p. 20).
- `CHANGES.md`: CH-05, CH-06, desvíos 1 y 3; `AGENTS.md`.
- KB: `03_actores_y_roles.md`, `05_reglas_de_negocio.md`, `07_flujos_principales.md`, `08_arquitectura_propuesta.md`, `09_decisiones_y_supuestos.md` (DD-04/05/06/08, DA-11 a DA-16), `11_casos_de_prueba.md`.
- Specs vigentes: contrasenas, token-de-acceso, errores-de-dominio y unidad-de-trabajo; notas de los explore/design de CH-01 a CH-04.
- Estado consultado con OpenSpec 1.14.0: sin changes activos; CH-01 a CH-04 completos. CH-05 aún no fue creado.

El contraste no encontró incompatibilidades en los contratos acordados. Precisiones: no medir tiempos en pytest no elimina las observaciones temporales que exigen C-04 y C-05 en la demostración `.http`; los espías verifican el mecanismo, no prueban igualdad de tiempos. DA-11/PA-11 fija los segundos restantes, pero no escribe explícitamente el redondeo: hacia arriba es la precisión confirmada aquí. No surgió una duda numérica o de símbolos que bloquee CH-05; esto no certifica toda la conversión del PDF.

## Decisiones confirmadas

| # | Pregunta | Decisión | Por qué |
|---|---|---|---|
| 1 | ¿Qué nace acá y qué queda para CH-06? | CH-05 crea `get_usuario_actual` en `app/core/dependencies.py`, las capas necesarias de usuarios para `/auth/*` y el repositorio mínimo de clientes (sólo `add`). CH-06 conserva `requiere_rol`, control del cambio obligatorio, grupo protegido y administración de usuarios/roles/eventos. | Respeta CHANGES y sus desvíos; `/yo` y `/cambiar-password` necesitan autenticación propia ahora. |
| 2 | ¿Cómo registrar sin filas sueltas? | Contrato `{email, nombre, password, documento, telefono}`, `extra="forbid"`, `Contrasena`. Hash antes del bloque; un solo UoW crea usuario activo sin cambio pendiente, asignación CLIENTE (`otorgada_por=NULL`), ficha vinculada y evento (`actor=email`, `accion=Registro de cliente <email>`). | RN-02 y C-02: las cuatro escrituras se confirman juntas o ninguna. |
| 2a | ¿Cómo tratar duplicados? | Sin consulta previa: UNIQUE → IntegrityError → rollback del UoW → conflicto de dominio → 409 en el router. Mensajes: `El correo ya está registrado` y `El documento ya está registrado` (texto exacto: **No especificado en la consigna**, confirmado por la alumna). Documento de ficha sin usuario también se rechaza; no se apropia ni modifica la ficha. | DD-04, RN-01/RN-02; evita carreras y respeta C-02. |
| 3 | ¿Cómo verificar el login? | Tras el límite, una llamada a `verificar_password` con hash real si existe el usuario o `app.state.hash_ficticio` si no existe; semáforo de CH-04, bcrypt fuera del bucle. Correo inexistente, contraseña incorrecta o usuario inactivo → mismo 401: `Correo o contraseña incorrectos` (texto exacto: **No especificado en la consigna**). | RN-09: no revelar existencia de cuentas. La rama inexistente falla siempre, independientemente del resultado del hash ficticio. |
| 3a | ¿Qué ocurre con un usuario inactivo? | **[Alumna]** Verifica contra su hash real y registra `exito=false`, incluso con contraseña correcta. Nunca emite cookie. | La autenticación no fue exitosa; cuenta para el límite sin distinguir cuentas por respuesta. |
| 3b | ¿Qué roles lleva el token? | Vigentes consultados en la base al emitir; `sub`, `iat` fraccionario, `exp`, `roles`. Roles del JWT sólo informativos. | Ejercicio 4, RN-04 y spec token-de-acceso. |
| 4 | ¿Cómo aplicar el límite? | Una consulta cuenta fallos del mismo correo+IP en 60 s y posteriores al último éxito de ese par. Con 5 fallos → 429 antes de bcrypt, sin registrar ese rechazo. `Retry-After`: segundos hasta que el conteo deje de bloquear, redondeados hacia arriba. | RN-08, DA-11/PA-11, C-05. El redondeo evita anunciar un reintento prematuro. |
| 4a | ¿Dónde registrar los intentos y de dónde sale la IP? | Sesión/transacción propias confirmadas para cada verificación, incluso si la petición falla; el UoW se suministra por composición/dependencias, no se construye en el servicio. IP de `request.client.host`, nunca `X-Forwarded-For`. Un éxito reinicia el conteo, sin borrar fallos. | DD-05 y DA-12/PA-12. Comentar en código el costo: quedan filas aunque la petición revierta. |
| 5 | ¿Cómo transportar y eliminar la sesión? | Cookie `access_token`: HttpOnly, SameSite=Lax, Max-Age=JWT_EXPIRE_SECONDS, Secure desde COOKIE_SECURE; `Path=/`, sin Domain (estos dos detalles: **No especificado en la consigna**). Login 200 con `{mensaje: Sesión iniciada, debe_cambiar_password, expira_en_segundos}`, sin token. Logout público 200 borra la cookie con el mismo alcance y funciona sin sesión. | Ejercicio 4 y C-03; la cookie debe llegar a las futuras rutas del dominio. Logout no agrega revocación de JWT en servidor. |
| 5a | ¿Qué hacer con Authorization? | No se lee para autenticar. Bearer solo → 401. Si hay cookie válida, se autentica exclusivamente con ella aunque también haya header. | Transporte sólo por cookie; no se crea una regla adicional de rechazo por presencia del header. |
| 6 | ¿Qué valida get_usuario_actual? | Cookie, firma/claims/vencimiento, usuario existente y activo, y RN-07: `datos.iat < usuario.password_cambiada_en.timestamp()` cuando la fecha no es nula. Sin truncar ni convertir iat mediante fromtimestamp. Contexto Pydantic interno con usuario y DatosToken para reutilizar roles_token. | Nota de CH-04: fromtimestamp puede desplazar microsegundos; no mezclar autorización de CH-06. |
| 6a | ¿Qué mensaje devuelven estos rechazos? | **[Alumna] D6**: un solo 401 con `Sesión no válida o vencida` ante cookie ausente, token inválido/vencido, usuario inexistente/inactivo o sesión anterior al cambio. **No especificado en la consigna**. Unificar también el TokenInvalido recibido del decodificador en esta frontera. | Mensaje neutro que sirve incluso cuando no llegó una cookie. D3 sigue siendo el mensaje de credenciales incorrectas del login; no se reemplaza por D6. El mecanismo puro de CH-04 conserva su mensaje interno y el escenario T6 existente. |
| 7 | ¿Cómo cambiar la contraseña? | Grupo abierto con autenticación propia; ambas contraseñas usan Contrasena. Verifica la actual y calcula hash nuevo antes del bloque. Un UoW modifica hash, password_cambiada_en con precisión completa y debe_cambiar_password=false, más evento `Cambio de contraseña` (actor=email). Después de confirmar, emite cookie nueva con roles vigentes e iat no anterior al cambio. Actual incorrecta → 401 sin escrituras/evento; sin confirmación no hay cookie nueva. | RN-07 y flujo 4; la nueva sesión vale y todas las anteriores dejan de valer aun dentro del mismo segundo. |
| 7a | ¿Se permite repetir contraseña? | **[Alumna] D7 — No especificado en la consigna**: si `password_nueva == password_actual`, rechazar 422 en el contrato, comparando los valores sin bcrypt adicional. | No permitir apagar el cambio obligatorio sin cambiar la contraseña. Escenario: usuario con cambio pendiente envía dos contraseñas iguales → 422, ninguna llamada a bcrypt, sin cambios de hash/fecha/bandera, sin evento ni cookie renovada. |
| 8 | ¿Qué devuelve /auth/yo? | DA-16: `{id, email, nombre, debe_cambiar_password, roles_vigentes, roles_token}`; vigentes desde la base (no revocados, sin vencer); token desde el contexto validado. Listas ordenadas de forma reproducible, sin hashes. | Mostrar diferencias reales tras revocación/vencimiento sin usar roles_token para autorizar. |
| 9 | ¿Cómo probar sin tiempos inestables? | **[Alumna] Ajuste 9**: no medir tiempos en tests. Un espía verifica que el correo inexistente llama exactamente una vez a verificar_password con app.state.hash_ficticio; respuesta idéntica a contraseña mala. Otro espía acredita cero llamadas bcrypt en 429. | Evitar fallos aleatorios por carga/planificación. No sustituye la observación temporal de C-04/C-05 en la demostración manual. |

## Escenarios para el propose

Todos con TDD estricto, safety net antes de modificar, pytest en `test/pytest/`, PostgreSQL `_test` real, sin mocks de la base. Espías sólo para verificar las llamadas señaladas. Preservar evidencia RED/GREEN y corridas fallidas.

- **Registro R1-R5**: alta deja las cuatro filas vinculadas; email repetido; documento repetido con usuario; documento de ficha sin usuario; excepción después de escrituras parciales revierte todo. Comparar filas/estado desde otra sesión y preservar los datos existentes.
- **Login L1-L6**: activo con contraseña correcta; contraseña mala; correo inexistente con exactamente una verificación del ficticio; inactivo con clave correcta y con clave incorrecta, ambos registrados como fallo; token con sólo roles vigentes (excluir revocados/vencidos).
- **Límite I1-I8**: cinco fallos registrados y sexto 429 sin bcrypt ni nueva fila; Retry-After positivo y redondeado hacia arriba; salida de ventana sin dormir (reloj/datos controlados); éxito reinicia sin borrar; independencia por correo e IP; ignorar X-Forwarded-For; intento confirmado sobrevive rollback de petición; éxito también se registra. El conteo se resuelve con una consulta.
- **Cookie K1-K5**: atributos y cuerpo sin token; COOKIE_SECURE en ambos valores; ausencia de cookie y Bearer solo → 401; logout con/sin sesión elimina el mismo alcance; cookie válida con header adicional sigue la autenticación por cookie.
- **Autenticación A1-A8**: cookie ausente; token inválido/alterado/vencido; usuario inexistente; inactivo; iat anterior al cambio; igualdad exacta aceptada; posterior aceptado; anterior/nuevo dentro del mismo segundo. Mismo mensaje D6 en todos los rechazos de esta dependencia.
- **Cambio P1-P5**: actual correcta cambia hash/fecha/bandera y deja evento; actual incorrecta no modifica nada; claves iguales → 422 contractual sin bcrypt, incluyendo cambio obligatorio pendiente; fallo transaccional revierte datos/evento y no emite cookie; cookie nueva válida y anterior 401 en el mismo segundo, sin sleeps.
- **Yo Y1-Y3**: forma exacta de DA-16; diferencia entre roles vigentes y del token tras revocación/vencimiento mediante preparación de datos; accesible autenticado con cambio pendiente.
- **Validación V1-V4**: todos los campos de contraseña de registro/login/cambio usan Contrasena; 72 bytes ASCII/UTF-8 aceptados, 73 rechazados; vacío/NUL rechazados; extras rechazados. Comprobar password_actual y password_nueva por separado. No agregar políticas de complejidad no acordadas.
- **Archivos HTTP**: `test/c02_registro.http`, `test/c03_c04_login.http`, `test/c05_limite_intentos.http`, con resultados esperados en comentarios; `python seed.py` antes de cada archivo. C-02/C-05 se complementan consultando la base. C-04 observa tiempos parecidos y C-05 rechazo rápido sin convertirlos en umbrales de pytest. Amanda opera la base de desarrollo; el agente sólo `_test` con el permiso correspondiente.

## Pedidos para el propose

1. Crear el change `autenticacion` mediante CLI sólo cuando se solicite propose; consultar estado/instrucciones. No se creó durante este explore.
2. Mantener la frontera CH-05/CH-06 y describir la composición Router → Service → UoW → Repository; el servicio nunca construye UoW. Registro y cambio de contraseña con sus escrituras/evento en un solo bloque cada uno.
3. Describir el orden límite → usuario/hash real o ficticio → registro independiente → fallo o emisión de cookie; diseñar el conteo en una consulta y el vencimiento del bloqueo desde los fallos que siguen contando.
4. Hacer explícitas las dependencias de app.state (session_factory, semaforo_bcrypt, hash_ficticio), Settings y el contexto de autenticación Pydantic. No generar hashes ficticios por petición ni duplicar mecanismos de CH-04.
5. Documentar mapas de restricciones con los nombres estables de CH-03 y los mensajes de 2a; reutilizar la traducción del UoW y `route_class=RutaQueTraduceErrores`. Los errores nuevos, incluido 429/Retry-After, deben tener traducción probada; sin handler global en main.py.
6. Capturar D6/D7 y los ajustes 3/9 como **[Alumna]**; marcar **No especificado en la consigna** donde corresponda. Conservar D3 para el login y D6 para la dependencia de autenticación. Registrar la precisión del redondeo de DA-11 sin atribuirla textualmente al PDF.
7. En specs/tasks, cubrir los escenarios anteriores, sin tests temporales, y conservar la demostración manual temporal requerida por C-04/C-05. No agregar dependencias sin pedido; pypdf se instaló sólo como herramienta del .venv y no va en requirements.
8. Respetar el orden de include_router de CH-01: primero incluir /auth en rutas_abiertas, después incluir el grupo en app. `/yo` y `/cambiar-password` autentican individualmente; logout sigue público.
9. Revisión CRÍTICA antes de implementar: el permiso de este resumen no autoriza código, apply, instalaciones ni corridas con efectos. No commits/push: los hace Amanda.

## Notas para CH-06

- Reutilizar get_usuario_actual/contexto; mantener `/auth/*` y salud fuera del control de cambio obligatorio. Agregar grupo protegido con el control una sola vez y requiere_rol consultando roles vigentes en cada petición.
- Completar administración de usuarios/roles/eventos; el repositorio mínimo de clientes se amplía en CH-07, no en CH-06.
- C-09 completo pertenece a CH-06; CH-05 prueba la invalidación de cookie anterior y validez de la nueva dentro del mismo segundo.
- **[Alumna] D7** evita que una contraseña provisoria se reutilice para apagar debe_cambiar_password: conservar su validación contractual y escenario al probar el bloqueo obligatorio.
- C-07 debe mostrar roles_vigentes distintos de roles_token tras revocar, sin autorizar nunca con roles_token.
- Todos los campos nuevos de contraseña (incluida password_provisoria) usan Contrasena. Preservar D6 para los rechazos de autenticación; falta de rol/cambio pendiente es autorización → 403.

## Cierre

Decisiones 1 a 9 confirmadas con los ajustes de Amanda. Próximo paso recomendado: `/opsx:propose autenticacion`, cuando Amanda lo solicite. Sin código ni commits durante esta exploración.
