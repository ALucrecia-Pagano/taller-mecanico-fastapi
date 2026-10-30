# Taller Mecánico — API REST

Trabajo práctico integrador de Programación III (prof. Giuliano). Es una API REST asincrónica para un taller mecánico, construida con FastAPI, SQLModel, SQLAlchemy asincrónico (asyncpg), PostgreSQL y Alembic.

La consigna está en `docs/consigna/consigna-taller-mecanico.pdf`. El plan de implementación completo, con los 11 changes, sus dependencias y su alcance, está en [CHANGES.md](CHANGES.md).

## Estado

El proyecto se construye change por change. Este README se actualiza en cada uno, para que el repositorio se pueda levantar en cualquier punto del camino.

**Implementado:**

| Change | Qué incluye |
|---|---|
| CH-01 `proyecto-config-salud` | Configuración desde el entorno (sin secretos por defecto); motor y fábrica de sesiones creados en el lifespan; `GET /health/live` y `GET /health/ready`; Alembic con la plantilla asincrónica (todavía sin migraciones); suite de pruebas contra la base de prueba |
| CH-02 `core-repositorios-uow` | Repositorios genéricos (`BaseRepository`, `SoftDeleteRepository`) que nunca confirman; Unit of Work que confirma o revierte al salir; paginación `{items, total, page, size, pages}`; traducción de los choques con la base a 409 con mensaje propio y de los errores de dominio a HTTP en cada router. Sin endpoints nuevos ni pasos nuevos de puesta en marcha |
| CH-03 `modelos-migraciones` | Las 13 tablas del dominio con sus restricciones (CHECK, UNIQUE, tres índices únicos parciales, estados por clave foránea al catálogo, un índice por clave foránea) y nombres de restricción fijos; navegación entre entidades sin carga implícita; dos migraciones: `0001` autogenerada y `0002` escrita a mano, con el disparador que rechaza UPDATE y DELETE en las tres tablas de sólo agregado; `test/solo_agregado.sql` (C-14). Paso nuevo de puesta en marcha: `alembic upgrade head` |
| CH-04 `seguridad-base-seed` | Contraseñas con bcrypt fuera del bucle y bajo un semáforo, costo desde la configuración y límite de 72 bytes; token JWT con `sub`, `iat` con fracción de segundo, `exp` y roles; hash ficticio del login calculado una vez en el lifespan; token inválido → 401; `seed.py` con los datos iniciales del PDF; evidencia de C-14. Sin endpoints nuevos. Paso nuevo de puesta en marcha: `python seed.py` |

CH-05 `autenticacion` también está implementado: registro atómico, login uniforme con límite
de intentos, cookie HttpOnly, perfil y cambio de contraseña con invalidación inmediata de sesiones.

CH-07 `clientes-vehiculos` está implementado: alta y consulta de clientes, alta y baja lógica
de vehículos, normalización de documentos y patentes, conflictos de duplicados traducidos a
409, restricción de baja por órdenes abiertas y consulta de `/mis-vehiculos`. Todas las rutas
están dentro de `rutas_protegidas`; las operaciones de recepción requieren `RECEPCION` o
`ADMIN`, mientras que `/mis-vehiculos` sólo requiere una sesión autenticada.

Endpoints de CH-07:

| Método | Ruta | Respuesta principal |
|---|---|---|
| `POST` | `/clientes` | 201 |
| `GET` | `/clientes/{id}` | 200 |
| `POST` | `/clientes/{id}/vehiculos` | 201 |
| `DELETE` | `/vehiculos/{id}` | 204 |
| `GET` | `/mis-vehiculos` | 200 |

Los ejemplos C-01 y C-19 están en `test/c01_parametro_invalido.http` y
`test/c19_baja_vehiculo.http`. Usan `{{$processEnv TALLER_PASSWORD_PRUEBA}}` y no contienen
contraseñas. Para validar CH-07 sobre la base de prueba:

```powershell
.venv\Scripts\python.exe -m pytest -v test\pytest\test_clientes.py
```

**En curso y planificado** (detalle en [CHANGES.md](CHANGES.md)):

| Change | Qué incluye |
|---|---|
| CH-06 `autorizacion-usuarios-roles` | En implementación: roles vigentes en base, grupo protegido, personal, historial de roles y eventos; contratos aprobados abajo |
| CH-08 a CH-10 | Repuestos, stock y órdenes de trabajo |
| CH-11 | Verificación final y evidencias |

## Requisitos

- Python 3.12 o superior (el proyecto se desarrolla con 3.13).
- PostgreSQL 16 o superior (el proyecto se desarrolla con 17), con `psql` disponible en la terminal.

## Puesta en marcha desde cero

Los comandos se corren desde la raíz del proyecto. Cuando cambian según la terminal, se indican las tres variantes.

### 1. Entorno virtual

Git Bash:

```bash
python -m venv .venv
source .venv/Scripts/activate
```

PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Dependencias

```bash
pip install -r requirements.txt
```

### 3. Archivo `.env`

Copiá la plantilla. El `.env` no se versiona.

Git Bash y Linux:

```bash
cp env.example .env
```

PowerShell:

```powershell
Copy-Item env.example .env
```

Después completá en el `.env` las dos variables que vienen vacías:

- `POSTGRES_PASSWORD`: la contraseña de tu usuario de PostgreSQL.
- `JWT_SECRET_KEY`: la clave de firma de los tokens. Se genera **una sola vez** con este comando (es el mismo en las tres terminales), se pega en el `.env` y queda fija:

  ```
  python -c "import secrets; print(secrets.token_urlsafe(64))"
  ```

Si alguna de las dos falta o está vacía, la aplicación no arranca. La clave tiene que tener al menos 32 caracteres.

El resto de las variables ya tiene su valor por defecto en la plantilla. No agregues al `.env` variables que no estén en `env.example`: la configuración rechaza las desconocidas, para que un error de tipeo no pase en silencio.

### 4. Bases de datos

Se crean dos bases: la de la aplicación y la de las pruebas, que se llama igual con el sufijo `_test`.

```bash
psql -U postgres -c "CREATE DATABASE taller_mecanico;"
psql -U postgres -c "CREATE DATABASE taller_mecanico_test;"
```

### 5. Migraciones

Crea el esquema en la base de la aplicación (la que indica `POSTGRES_DB` en el `.env`):

```bash
alembic upgrade head
```

`alembic current` tiene que mostrar `0002 (head)`. Las tablas quedan vacías, incluido el catálogo de estados: los datos iniciales llegan con `python seed.py` (paso siguiente). La base de prueba no se migra a mano: la migra la suite al arrancar.

Para volver a la base vacía: `alembic downgrade base`.

### 6. Datos iniciales

Deja la base de la aplicación en el estado inicial conocido que usan los casos de prueba:

```bash
python seed.py
```

- **Primero muestra a qué base va** (nombre, host y puerto), y después **vacía todas las tablas** y carga los datos iniciales de la consigna: el catálogo de estados, 7 usuarios, 2 clientes, 3 vehículos, 4 repuestos con su stock inicial, las órdenes 1 y 2, y el historial de precios y de seguridad. Los ids coinciden con los ejemplos de la consigna.
- **No pide confirmación.** Si algo falla, la base queda como estaba, porque todo ocurre en una sola transacción.
- **Se puede correr las veces que haga falta**, y se corre **antes de cada archivo `.http`**, porque las pruebas cambian los datos.
- Sin esquema, corta con «Corré `alembic upgrade head` primero».
- Las contraseñas de los usuarios del seed son ficticias y están sólo en `seed.py`.

### 7. Levantar el servidor

```bash
uvicorn main:app --reload
```

### 8. Probar la salud

Con el servidor levantado, desde otra terminal:

Git Bash y Linux:

```bash
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

PowerShell:

```powershell
Invoke-RestMethod http://localhost:8000/health/live
Invoke-RestMethod http://localhost:8000/health/ready
```

También se pueden ejecutar las peticiones de `test/health.http` desde el editor (por ejemplo, con la extensión REST Client de VS Code).

Respuestas esperadas:

| Sonda | Base disponible | Base caída o sin respuesta en 3 s |
|---|---|---|
| `GET /health/live` | 200 `{"estado": "vivo"}` | 200 `{"estado": "vivo"}` |
| `GET /health/ready` | 200 `{"estado": "listo"}` | 503 `{"detail": "La base de datos no responde"}` |

La aplicación arranca aunque la base esté caída: el proceso puede estar vivo y no estar listo.

## Pruebas

### Registro de clientes (CH-05)

`POST /auth/registro` recibe `{email,nombre,password,documento,telefono}` y crea usuario,
asignación CLIENTE, ficha y evento en una sola transacción. Devuelve 201; email o documento
repetido devuelve 409 con mensaje propio y no deja filas sueltas, incluso para una ficha sin usuario.
Los campos extra se rechazan; las contraseñas aceptan hasta 72 bytes UTF-8.
`test/c02_registro.http` demuestra C-02 después del seed. La suite también ejecuta sus peticiones
sobre ASGI con la base `_test` sembrada y verifica las cuatro tablas desde otra sesión.

El login limita a cinco fallos del mismo correo e IP en 60 segundos. Un éxito reinicia el conteo
sin borrar el historial. El rechazo 429 no verifica bcrypt ni agrega otro intento y entrega
`Retry-After` redondeado hacia arriba. Los intentos verificados se confirman en sesión propia,
incluso si la petición falla; la IP se toma de la conexión, no de `X-Forwarded-For`.

`POST /auth/login` recibe `{email,password}`. La respuesta 200 sólo trae mensaje,
`debe_cambiar_password` y `expira_en_segundos`; el JWT firmado viaja en `access_token`
HttpOnly, SameSite=Lax, Path=/, sin Domain, con Max-Age igual a su duración y Secure desde
COOKIE_SECURE. Sólo se lee la cookie; Authorization no autentica. `POST /auth/logout`
es público, devuelve 200 y borra la cookie incluso sin sesión; no revoca copias del JWT en servidor.
Demostraciones: `test/c03_c04_login.http` y `test/c05_limite_intentos.http`, cada uno después
de seed. Para REST Client, configurar `TALLER_PASSWORD_PRUEBA` en el proceso del editor con
la clave ficticia de `seed.py` (sin copiarla al repositorio); C-04/C-05 observan tiempos manualmente.

`GET /auth/yo` requiere cookie y devuelve exactamente `id,email,nombre,debe_cambiar_password,
roles_vigentes,roles_token`. Los roles vigentes se consultan en la base; los del JWT son informativos.
Una cookie ausente/inválida/vencida, usuario inexistente/inactivo o sesión anterior al cambio de clave
responde 401 `Sesión no válida o vencida`. Las rutas `/auth` quedan en el grupo abierto y autentican
individualmente cuando corresponde. El control del cambio obligatorio y la autorización por rol
pertenecen a CH-06; no se aplican aquí para impedir consultar el perfil o cambiar la clave.

`POST /auth/cambiar-password` recibe `{password_actual,password_nueva}` y requiere la cookie.
La actual incorrecta devuelve 401. **[Alumna]** La nueva igual a la actual se rechaza con 422
en el contrato, sin bcrypt adicional: no permite apagar el cambio obligatorio sin cambiar la clave
(No especificado en la consigna). Hash/fecha/bandera y evento se guardan juntos; sólo tras confirmar
se renueva la cookie. La anterior deja de valer incluso dentro del mismo segundo. C-09 completo
(bloqueo del grupo protegido) se completa en CH-06.

### Autorización, personal y roles (CH-06)

Los permisos se consultan en `asignacion_rol` en cada petición: una asignación está vigente si
no fue revocada y no venció. Los roles del JWT son informativos. Sin sesión válida se recibe
401; con sesión pero sin rol permitido, 403. El grupo protegido controla una sola vez el
cambio obligatorio: mientras esté pendiente devuelve 403, pero salud y las rutas `/auth`
siguen disponibles. `/auth/yo` y `/auth/cambiar-password` piden autenticación propia.

Las siguientes rutas requieren ADMIN vigente y contraseña sin cambio pendiente:

| Método y ruta | Entrada / respuesta |
|---|---|
| `POST /usuarios` | `{email,nombre,password_provisoria,rol}` → 201 con `{id,email,nombre,activo,debe_cambiar_password}` |
| `GET /usuarios/{id}/roles` | 200 con lista de todo el historial, incluidas filas vencidas/revocadas |
| `POST /usuarios/{id}/roles` | `{rol,vence_en?}` → 201 con la asignación |
| `DELETE /usuarios/{id}/roles/{rol}` | 200 con la asignación revocada, conservando la fila |
| `GET /eventos?page=1&size=20` | 200 con `{items,total,page,size,pages}` |

Las entradas de alta y asignación sólo admiten ADMIN, RECEPCION o MECANICO;
CLIENTE se obtiene por auto-registro (**[Alumna] D1=B**, extensión acordada de DA-17,
No especificado en la consigna para la asignación administrativa). Los extras se rechazan.
La contraseña provisoria usa el límite de 72 bytes UTF-8 y no acepta vacío/NUL.
El alta deja usuario activo con cambio obligatorio, asignación inicial y un evento en la
misma transacción. No devuelve contraseña, hash ni token.

`vence_en` puede omitirse o ser null; si se envía una fecha debe tener zona horaria y estar
en el futuro, si no da 422. Una asignación vigente duplicada da 409. Reasignar una vencida
cierra la fila anterior y abre otra conservando su autoría histórica.
La asignación devuelta incluye `id,usuario_id,rol,desde,vence_en,revocada_en,otorgada_por,vigente`.
El historial se ordena por `desde,id` ascendente; usuario existente sin roles devuelve `[]`.
Usuario inexistente da 404; sin asignación abierta también da 404 (**[Alumna] D2=A**).

Nadie se revoca su propio ADMIN (409), ni una revocación deja cero ADMIN vigentes (409).
Las mutaciones ADMIN se coordinan con un candado transaccional común y releen el rol del
actor después de esperar (**[Alumna] D3=A**, No especificado en la consigna).
En una revocación cruzada, una confirma y la otra pierde permiso (403).
Se conserva DA-15/SU-11: el vencimiento por tiempo puede dejar cero administradores;
no se agrega una tarea automática.

Los eventos usan el email del actor y los textos DA-13: `Alta de personal <email>`,
`Asignación de rol <ROL> a <email>` y `Revocación de rol <ROL> a <email>`.
Cada operación deja un evento en su misma transacción; los rechazos no agregan eventos.
`SISTEMA` queda para el seed. El listado devuelve `id,cuando,actor,accion`, ordenado por
`cuando,id` descendente; `size` permite 1..100, una página inexistente da 422 y sin datos
hay una página vacía. Formatos y orden explícitos: **[Alumna] D4=A**, No especificado
en la consigna.

Para las demostraciones, Amanda ejecuta `python seed.py` **antes de cada archivo** y corre
sus peticiones en orden desde REST Client. Definir `TALLER_PASSWORD_PRUEBA` en el proceso
del editor con la contraseña ficticia que vive sólo en `seed.py`; no copiarla al repositorio.
Los archivos usan respuestas nombradas y `# @no-cookie-jar` para enviar cookies explícitas
sin mezclar sesiones:

| Archivo | Resultado esperado |
|---|---|
| `test/c07_roles_vigencia.http` | Dos sesiones: admin1 revoca ADMIN de admin2; la cookie original de admin2 da 403, `/auth/yo` muestra roles distintos y el historial conserva la fila; fechas pasada/sin zona dan 422 |
| `test/c08_autoproteccion.http` | Autorrevo ADMIN da 409 y conserva asignación/permisos |
| `test/c09_cambio_obligatorio.http` | Nuevo del seed bloqueado 403; repetir clave da 422; cambio correcto produce cookie nueva válida y anterior 401 sin esperar |
| `test/c16_busqueda_paginacion.http` | Búsqueda segura y paginada de repuestos, PATCH parcial y PATCH de stock rechazado |
| `test/c18_historial_precios.http` | Historial de precio, PATCH descriptivo sin nueva línea y 403 para RECEPCION |

El usuario `nuevo@example.com` del seed es MECANICO: después de cambiar la contraseña
su cookie nueva vale en `/auth/yo`, pero `/eventos` sigue dando 403 por falta ADMIN.
La suite comprueba además con un ADMIN provisional el acceso 200 al grupo protegido tras
el cambio. **C-06 completo** (orden propia 200/ajena 403 y `c06_401_403_propio.http`)
pertenece a **CH-09**; CH-06 prueba la base del 401 frente al 403.

### Suite automática

La suite automática vive en `test/pytest/` y corre **sólo** contra la base `<POSTGRES_DB>_test` (por ejemplo, `taller_mecanico_test`). Si la configuración apunta a una base cuyo nombre no termina en `_test`, la prueba no corre. Necesita el `.env` completo y la base de prueba creada (paso 4).

```bash
pip install -r requirements-dev.txt
pytest -v
```

`POSTGRES_DB` en el `.env` tiene que ser la base de la aplicación, no la de prueba: la suite deriva sola el nombre `_test`, y aborta con un mensaje si el `.env` ya apunta a una base de prueba.

### Caso C-14 (sólo agregado)

`test/solo_agregado.sql` muestra en `psql` los seis rechazos del disparador y el de la clave foránea. Se corre **después** de `python seed.py`, sobre la base de la aplicación. Sin los datos iniciales, el archivo se detiene al principio con «Corré python seed.py primero».

Pasos en Git Bash, desde la raíz del repositorio. El `tee` deja en pantalla, para la captura, la misma salida que guarda en el archivo:

```bash
source .venv/Scripts/activate
alembic upgrade head                      # si la base no está en head
python seed.py
export PGCLIENTENCODING=UTF8
psql -U postgres -d taller_mecanico -f test/solo_agregado.sql 2>&1 | tee docs/evidencias/C-14-psql.txt
#   -> captura de esa ventana: docs/evidencias/capturas/C-14-solo-agregado.png
file docs/evidencias/C-14-psql.txt                     # esperado: UTF-8 text
grep -c "ERROR" docs/evidencias/C-14-psql.txt          # esperado: 7
grep -c "sólo agregado" docs/evidencias/C-14-psql.txt  # esperado: 6
python seed.py                            # repone la secuencia que consumió la sentencia 7
```

- **El `python seed.py` final es necesario.** La séptima sentencia falla por la clave foránea, pero consume un número de la secuencia de `orden_trabajo`. Sin volver a correr el seed, la próxima orden creada por la API no tendría el id que esperan los ejemplos.
- **No usar `winpty psql`:** con `winpty`, la consola usa la página de códigos 850 (los acentos salen rotos) y el `tee` deja de funcionar. En Git Bash, `psql` ya escribe UTF-8.

La evidencia queda en `docs/evidencias/C-14-psql.txt` (texto) y en `docs/evidencias/capturas/C-14-solo-agregado.png` (captura).
