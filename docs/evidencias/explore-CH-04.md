# Explore de CH-04 `seguridad-base-seed`

Resumen del explore (`/opsx:explore`) del cuarto change, hecho el 2026-10-28 con la alumna, una decisión por vez, antes del propose. Governance **CRÍTICO**: no se escribió código.

Fuentes: `CHANGES.md` (CH-04, Desvío 2, OB-03, OB-04, OB-09), `knowledge-base/04_modelo_de_datos.md` (§Entidades, §Seed data inicial, §Detalle del seed), `08_arquitectura_propuesta.md` (§Seguridad, §Variables de entorno), `09_decisiones_y_supuestos.md` (DA-01 a DA-08, DA-13, DA-16, DA-31, DD-01, DD-02, DD-06, DD-08), `AGENTS.md`, las specs de `openspec/specs/`, las notas para CH-04 de `explore-CH-01.md` (3e, 7b, nota 6), `explore-CH-03.md` (nota 9) y `verify-CH-03.md` (R4), y la consigna (Ej. 1 lifespan, Ej. 4, Datos iniciales, Requisitos no funcionales, C-14, Formato de entrega).

Estado del entorno al explorar: Python 3.13.6, FastAPI 0.162.0, SQLModel 0.0.48, asyncpg 0.32.0, pytest 9.1.1, pytest-asyncio 1.4.0 (bucle de sesión en `pytest.ini`), psql 17.11. **`bcrypt` y `PyJWT` no están instalados**: se instalan en el apply, con permiso.

En la columna «Decisión», **[Alumna]** marca lo que decidió la alumna sobre algo que la consigna no especifica; lo que no lleva marca sale de la consigna, de la KB o de una DA/DD ya aceptada.

## Qué nace en CH-04

- `app/core/security.py`: funciones de mecanismo, sin base ni HTTP (`hashear_password`, `verificar_password`, `emitir_token`, `decodificar_token`), el tipo `Contrasena` y el modelo `DatosToken`.
- `app/core/errores.py`: suma la excepción de dominio `TokenInvalido` (su traducción a 401 llega en CH-05).
- `main.py`: el lifespan suma `app.state.semaforo_bcrypt` y `app.state.hash_ficticio`.
- `seed.py` en la raíz.
- `requirements.txt`: `bcrypt>=4.0,<6` y `PyJWT>=2.10,<3`.
- Tests en `test/pytest/`: `test_contrasena.py`, `test_hash.py`, `test_token.py`, `test_seed.py`; se extienden `test_ciclo_de_vida.py` y el test de ciclo de migraciones (19a de CH-03).
- Evidencia de C-14: `docs/evidencias/capturas/C-14-solo-agregado.png` y `docs/evidencias/C-14-psql.txt` (las hace la alumna).

**No** nacen (quedan para CH-05): la cookie `access_token` (poner y borrar), `get_usuario_actual` y la comparación de `iat` con `password_cambiada_en` (RN-07), la consulta de roles vigentes, los schemas de `/auth`, el servicio de login (límite → verificación → token) y la traducción de `TokenInvalido` a 401.

## Decisiones

| # | Pregunta | Decisión | Por qué |
|---|---|---|---|
| 1 | ¿Qué nace en CH-04 y qué queda para CH-05? | `security.py` con funciones puras de mecanismo: hashear, verificar, emitir y decodificar, sin base ni HTTP. `emitir_token` **recibe** los roles; no los consulta. La cookie y la comparación de `iat` con `password_cambiada_en` quedan en CH-05. El hash ficticio nace en el lifespan en CH-04 y se usa en el login de CH-05. | Es el reparto del PDF entre `security.py` («hash con bcrypt fuera del bucle, y emisión y verificación del token») y `dependencies.py` («usuario actual, roles vigentes…»). Nace sólo lo que se implementa y prueba; todo se prueba con pytest sin endpoints. Alternativa descartada: adelantar la cookie a CH-04 (se probaría sobre un `Response` suelto; el transporte es del login). |
| 2a | ¿Dónde vive el semáforo de bcrypt? | Se crea en el lifespan con `BCRYPT_MAX_CONCURRENCY` y se guarda en `app.state.semaforo_bcrypt`. Las funciones lo reciben como parámetro junto con el costo: `hashear_password(password, *, costo, semaforo)` y `verificar_password(password, hash_, *, semaforo)`, con `async with semaforo: await asyncio.to_thread(...)`. `seed.py` crea el suyo. Sin estado global en `security.py`. | Nada se construye al importar (Ej. 1, EA-08). El tamaño sale de `Settings`: un semáforo global leería la configuración al importar y los tests que cambian el entorno quedarían con el valor viejo. Alternativa descartada: clase `Hasheador` (se aleja de «funciones puras»). |
| 2b | ¿Cómo se aplica el costo? | `bcrypt.gensalt(rounds=costo)`, con `costo = settings.bcrypt_cost` (4..31 ya validado en `Settings`). La verificación lee el costo del hash guardado. | El PDF pide «un costo declarado en la configuración y no fijo en el código». Subir `BCRYPT_COST` no invalida los hashes viejos. |
| 2c | ¿Cómo se aplica el límite de 72 bytes? | Tipo reutilizable `Contrasena = Annotated[str, ...]` en `security.py`: `len(v.encode("utf-8")) <= 72`. **[Alumna]** También `min_length=1` y rechazo de `\x00` (422), los dos «No especificado en la consigna». Defensa en profundidad: `hashear_password` lanza su propio `ValueError` con más de 72 bytes. | El PDF: «son bytes y no caracteres», y sin el límite «una contraseña larga daría un 500 en lugar de un 422». bcrypt 4 trunca en silencio y bcrypt 5 lanza la excepción: el `ValueError` propio iguala las dos. El `\x00` probablemente lo rechaza bcrypt y daría 500 («ninguna entrada inválida en 500»). **Verificar en el apply** cómo se comporta bcrypt con `\x00` en la versión instalada y anotarlo. |
| 2d | Rango de bcrypt en requirements | `bcrypt>=4.0,<6`. | Patrón de CH-01 7a: piso del PDF, tope en la siguiente versión mayor. Hoy se instalaría la 5.x. |
| 3 | Hash ficticio del lifespan | `app.state.hash_ficticio = await hashear_password(secrets.token_urlsafe(32), costo=settings.bcrypt_cost, semaforo=app.state.semaforo_bcrypt)`, una vez por arranque. La entrada aleatoria se descarta. En CH-05, la rama «correo inexistente» verifica contra él y siempre responde 401, sin mirar el resultado. | RN-09, anti-enumeración: mismo tiempo y mismo cuerpo con o sin correo. El costo es el de `Settings`, igual que el de los usuarios. Ninguna contraseña literal en el código. Pasa por `to_thread` y el semáforo («bcrypt siempre fuera del bucle»). Alternativas descartadas: un hash literal precalculado (costo fijo, algo con forma de credencial en el repo) y calcularlo de forma perezosa en el primer login (el PDF lo pone en el lifespan). **Límite que va al design**: si sube `BCRYPT_COST`, los hashes viejos tardan menos que el ficticio; se acepta y rehashear al hacer login queda fuera del alcance. |
| 4a | `iat` con fracción de segundo (OB-09) | `"iat": ahora.timestamp()` como `float`. **Nunca** como `datetime`, que PyJWT pasa por `timegm` y trunca a segundos. | El PDF: «EL IAT NO SE TRUNCA A SEGUNDOS». `json.dumps` conserva el `float` exacto. **Verificar en el apply**, con la versión instalada de PyJWT, que la validación no modifica el claim (test T2). |
| 4b | `exp` | `ahora + timedelta(seconds=JWT_EXPIRE_SECONDS)` como `datetime` (PyJWT lo pasa a entero). Leeway 0. | Truncar `exp` acorta la vida del token menos de 1 s; RFC 7519 lo admite. |
| 4c | Claims | Sólo `sub` (`str(usuario_id)`), `iat`, `exp` y `roles` (los vigentes al emitir, recibidos por parámetro, ordenados). `roles` es informativo (`roles_token` de `/auth/yo`, DA-16); la autorización nunca lo lee. Sin `iss`, `aud` ni `jti` («No especificado en la consigna»). | El PDF: «un JWT firmado con sub, iat, exp y los roles vigentes al emitirlo». DD-01 y RN-04: los roles se deciden en la base en cada petición. |
| 4d | Validación y resultado | `jwt.decode(token, clave, algorithms=[settings.jwt_algorithm], options={"require": ["sub", "iat", "exp"]})`. Devuelve un modelo Pydantic congelado, `DatosToken(usuario_id: int, iat: float, roles: list[str])`, en `security.py`. Cualquier `jwt.InvalidTokenError`, un `sub` que no es entero o `roles` que no es lista se convierten en la excepción de dominio `TokenInvalido` (en `app/core/errores.py`; su 401 llega en CH-05). | La lista fija de algoritmos ignora el `alg` de la cabecera (bloquea `none` y la confusión de algoritmos). CH-05 no manipula un `dict` crudo, y la excepción sube por la dependencia y la traduce la ruta, como el resto de los errores de dominio (CH-02). Alternativa descartada: devolver `None` (pierde el motivo y obliga a un `if` en cada llamador). |
| 4e | Tiempo inyectable y rango de PyJWT | `emitir_token(usuario_id, roles, *, settings, ahora=None)`. `PyJWT>=2.10,<3`. | «Vencido» se prueba emitiendo con `ahora` 2 h atrás, sin `sleep`. El piso sube de 2.8 a 2.10 porque desde esa versión `sub` se valida como string y el diseño cuenta con eso; sigue cumpliendo el mínimo del PDF. |
| 5a | Estructura y transacción de `seed.py` | `async def cargar_datos_iniciales(sesion, hashes)` más `main()` con `asyncio.run`. Los 7 hashes se calculan **antes** de abrir la transacción, concurrentes bajo el semáforo propio. Todo va en **una sola transacción**, con los modelos SQLModel directamente (`add` y `flush` por grupo) y sin servicios. | DD-06: el hash antes de la transacción. Todo o nada: si algo falla, también se revierte el `TRUNCATE`. Los servicios de los módulos todavía no existen. |
| 5b | `TRUNCATE` | Una sola sentencia `TRUNCATE … RESTART IDENTITY CASCADE` con las tablas tomadas de `SQLModel.metadata.sorted_tables`, nunca «todas las del esquema». | DA-31. No toca `alembic_version`, y en `_test` tampoco las `prueba_*` de CH-02 (no tienen FK al dominio). |
| 5c | Ids | No se fijan ids explícitos: `RESTART IDENTITY` más el orden de alta, con `flush` por grupo. Un test verifica cada id contra su clave natural. | Con `id=1` explícito la secuencia no avanza y el primer alta de la API chocaría. Los ids deben coincidir con el PDF (SU-06). |
| 5d | Datos | DA-01 a DA-06 tal cual, en el orden: catálogo (desde `CodigoEstado`) → usuarios 1..7 → asignaciones (`otorgada_por = NULL`) → clientes → vehículos → repuestos (+ «Stock inicial» y el historial de precio del filtro) → órdenes 1 y 2 (+ ítems e historiales) → evento `SISTEMA` / «Carga de los datos iniciales». **[Alumna]** Descripciones del catálogo: «Pendiente», «En reparación», «Terminada» y «Cancelada» («No especificado en la consigna»). El `total` se calcula sumando los ítems. 7 hashes distintos de `Taller2026!` (uno por usuario). | El PDF dice «cada uno con su descripción» sin dar los textos. Calcular el total evita escribir el número dos veces; el test lo compara con los literales. |
| 5d-bis | Stock directo en el seed | El seed escribe `repuesto.stock` junto con su movimiento «Stock inicial» sin pasar por el punto único de stock (que nace en CH-08). Es una excepción acotada a la puesta en marcha, como DA-31. Test: `stock == sum(movimientos)` por repuesto. La orden 2 no descuenta nada. | El punto único no existe todavía; el test garantiza la consistencia. El stock se mueve recién al terminar la orden (C-11). |
| 5d-ter | Horas del seed | Todos los `cuando` y `creada_en` quedan en `now()` (inicio de la transacción), sin desfasajes inventados. | Las dos filas de historial de la orden 2 tienen el mismo `cuando`; ver la nota para CH-09. |
| 5e | Protección contra correrlo por error | **[Alumna]** Sin flag ni confirmación: el comando es `python seed.py`, como fija el PDF. Tres protecciones: imprime base, host y puerto (sin contraseña) antes de vaciar; usa una sola transacción; y sin esquema corta con «Corré `alembic upgrade head` primero». | El PDF: «antes de cada archivo se corre `python seed.py`». Alternativa descartada: `python seed.py --si` (cambia el comando del PDF y del README). |
| 5f | Cómo se prueba contra `_test` | Los tests llaman a `cargar_datos_iniciales` detrás de `verificar_base_de_prueba`. Un test corre `python seed.py` por subproceso con `POSTGRES_DB=<db>_test` y `BCRYPT_COST=4`. La fixture `base_sembrada` **deja la base `_test` vacía al terminar** (el mismo `TRUNCATE`). | Hallazgo: `test_m3_el_catalogo_queda_vacio` y `test_x2_con_tablas_vacias_corta_antes_de_las_siete` asumen tablas del dominio vacías, y `_una_fila_por_tabla` (D5, X1) inserta catálogo propio que chocaría por PK con el del seed. |
| 6a | Captura de C-14 | **[Alumna]** Los pasos 1 a 6 los hace la alumna sobre `taller_mecanico`; el agente sólo toca `_test`. Es un checkpoint del apply: la task se marca cuando existen la captura y el `.txt`. **[Alumna]** El `.txt` es obligatorio: `docs/evidencias/C-14-psql.txt`, junto a `docs/evidencias/capturas/C-14-solo-agregado.png`. | DA-30 y R4 de CH-03. El PDF pide «una captura de psql»; el `.txt` permite que CH-11 verifique el contenido sin abrir la imagen. Alternativa descartada: que el agente corra psql contra `taller_mecanico` (rompe la frontera de que el agente sólo toca `_test`). |
| 6b | Secuencia consumida por la sentencia 7 | Después de la captura se vuelve a correr `python seed.py`. | El `INSERT` de la sentencia 7 falla por la FK, pero consume el `nextval` de `orden_trabajo`: sin re-seed, la próxima orden de la API sería la 4. |
| 6c | Shell y UTF-8 | **[Alumna]** Los pasos se escriben para **Git Bash** (sección «Pasos de C-14»). Verificado en el explore contra `taller_mecanico_test` (sólo lectura): en Git Bash, `client_encoding` ya es UTF8, `sólo` sale como `c3 b3` en el archivo y los mensajes traducidos del servidor (`lc_messages = Spanish_Argentina.1252`) salen bien. `PGCLIENTENCODING=UTF8` se deja explícito. **No usar `winpty`**: ahí vuelve la página de códigos 850 y se rompe el `tee`. | mintty no es una consola de Windows. Hay `pgpass.conf`, así que psql no pide contraseña. |
| 6d | Test de C-14 sobre el seed | Test nuevo S14: seed en `_test` → bloque de verificación (pasa) → las siete sentencias, cada una con su error esperado. | Es el motivo por el que la captura pasó a CH-04 (R4 de CH-03): X1 usa filas propias del test, y este prueba el script con los datos del seed. |
| 7a | Costo de bcrypt en los tests | `entorno_de_prueba` hace `setenv("BCRYPT_COST", "4")` (alcanza al lifespan y al seed); los unit tests pasan `costo=4`; el subproceso del seed recibe `BCRYPT_COST=4`. | Nota 6 de CH-01: con un lifespan por test, el hash ficticio sumaría unos 250 ms por test. |
| 7b | Escenarios | Los de la sección «Escenarios de prueba». | Feliz, error y borde por pieza, con triangulación. |
| 7c | Caso «sin esquema» del seed | Va **dentro del test de ciclo de CH-03 (19a)**: estando en `base`, corre `python seed.py` por subproceso y verifica `returncode ≠ 0` y el mensaje. La suite de CH-03 tiene que seguir en verde después del cambio. | Ese test ya pasa por `downgrade base`. Crear una base vacía aparte sería otra acción con efectos y otra base que mantener. |

## Escenarios de prueba

### C: tipo `Contrasena` (`test_contrasena.py`)

- **C1** (feliz): `"Taller2026!"` es válida.
- **C2** (borde): 72 bytes ASCII aceptada; 73 rechazada (`ValidationError`, que en un schema da 422).
- **C3** (borde): 36 «ñ» (36 caracteres, 72 bytes) aceptada; 36 «ñ» + «a» (37 caracteres, 73 bytes) rechazada. Cuenta bytes, no caracteres.
- **C4** (error): `""` rechazada (`min_length=1`); `"abc\x00"` rechazada.

### H: hash (`test_hash.py`)

- **H1** (feliz): hash ≠ contraseña, empieza con `$2b$04$` y verifica `True`.
- **H2** (error): otra contraseña verifica `False`.
- **H3** (triangulación): dos hashes de la misma contraseña son distintos y los dos verifican.
- **H4** (borde): con `costo=5` empieza con `$2b$05$`; un hash de costo 4 verifica con cualquier configuración.
- **H5** (error): `hashear_password` con 73 bytes lanza nuestro `ValueError`. Se anota el comportamiento real de bcrypt con `\x00`.
- **H6** (fuera del bucle): un envoltorio sobre `bcrypt.hashpw`/`checkpw` registra el hilo; no es el del bucle.
- **H7** (semáforo): `Semaphore(2)` y 6 hashes concurrentes, pico de hilos activos **== 2**. Prueba el límite y que hay concurrencia.

### T: token (`test_token.py`)

- **T1** (feliz): round-trip; `usuario_id` (int), `roles` e `iat` vuelven iguales.
- **T2** (OB-09): `ahora = …:00.123456` y el `iat` decodificado es `== ahora.timestamp()`, con parte decimal ≠ 0.
- **T3** (triangulación): `exp - int(iat) == JWT_EXPIRE_SECONDS`, con 1800 y con 60.
- **T4** (error): emitido con `ahora` 2 h atrás da `TokenInvalido`.
- **T5** (error): otra clave da `TokenInvalido`; payload alterado da `TokenInvalido`.
- **T6** (error): `alg: none` y `HS512` con la misma clave dan `TokenInvalido`.
- **T7** (borde, parametrizado): sin `sub`, sin `iat` o sin `exp`, `sub = "abc"` y `roles` que no es lista dan `TokenInvalido`.
- **T8** (error): `"no-es-un-token"` da `TokenInvalido`.

### F: lifespan (`test_ciclo_de_vida.py`, se extiende)

- **F1**: tras el arranque, `app.state.hash_ficticio` existe y empieza con `$2b$04$`.
- **F2**: se calcula una sola vez; espiando `hashear_password`, un arranque más varias peticiones dan 1 llamada.
- **F3**: `verificar_password("Taller2026!", hash_ficticio)` da `False`.
- **F4** (triangulación): con `BCRYPT_COST=5` empieza con `$2b$05$`.
- **F5**: con `BCRYPT_MAX_CONCURRENCY=1`, dos verificaciones concurrentes con `app.state.semaforo_bcrypt` tienen pico 1 (por comportamiento, sin atributos privados).

### S: seed (`test_seed.py`; la fixture `base_sembrada` deja `_test` vacía al terminar)

- **S1**: cada id ↔ su clave natural (7 usuarios, 2 clientes, 3 vehículos, 4 repuestos, 2 órdenes).
- **S2**: totales `Decimal("56500.00")` y `Decimal("24000.00")`; ítems con su `precio_unitario`.
- **S3**: un «Stock inicial» por repuesto con `cantidad == stock` y `usuario_id 1`; `stock == sum(movimientos)`.
- **S4**: precio 8000 → 8500 por el usuario 1; 3 filas de historial de estado con los autores de DA-06.
- **S5**: catálogo == `CodigoEstado`: códigos, posiciones 1..4, `es_final` y las 4 descripciones.
- **S6**: asignaciones vigentes con `otorgada_por NULL`; sólo `nuevo@` con `debe_cambiar_password`; todos `activo`; `password_cambiada_en NULL`.
- **S7**: `"Taller2026!"` verifica contra los 7 hashes, y los 7 son distintos.
- **S8**: exactamente un evento `SISTEMA` / «Carga de los datos iniciales».
- **S9** (repetible): dos corridas dejan la misma foto de las 13 tablas (sin columnas de hora).
- **S10** (borde): sobre una base «sucia» (filas extra en las tablas de sólo agregado), el `TRUNCATE` las limpia sin chocar con el disparador.
- **S11** (borde): `alembic_version` intacta después del seed.
- **S12** (error): con una excepción inyectada después del `TRUNCATE`, la base queda como estaba.
- **S13** (entrada real): `python seed.py` por subproceso contra `_test`: `returncode 0`, imprime base, host y puerto, y la salida no contiene la contraseña.
- **S14** (C-14): seed, verificación (pasa) y las siete sentencias, cada una con su error esperado.
- **Sin esquema** (dentro del 19a de CH-03): estando en `base`, `python seed.py` da `returncode ≠ 0` y «Corré `alembic upgrade head` primero».

## Pasos de C-14 en Git Bash [Alumna]

Los hace la alumna, sobre la base de la aplicación, al llegar al checkpoint del apply. Un único `tee` deja la pantalla (para la captura) y el `.txt` idénticos.

```bash
source .venv/Scripts/activate
alembic upgrade head                      # si taller_mecanico no está en head
python seed.py
export PGCLIENTENCODING=UTF8
psql -U postgres -d taller_mecanico -f test/solo_agregado.sql 2>&1 | tee docs/evidencias/C-14-psql.txt
#   -> captura de esa ventana: docs/evidencias/capturas/C-14-solo-agregado.png
file docs/evidencias/C-14-psql.txt                     # esperado: UTF-8 text
grep -c "ERROR" docs/evidencias/C-14-psql.txt          # esperado: 7
grep -c "sólo agregado" docs/evidencias/C-14-psql.txt  # esperado: 6
python seed.py                            # repone la secuencia que consumió la sentencia 7
```

No usar `winpty psql`: vuelve la página de códigos 850 y rompe el `tee`.

## Pedidos para el propose

1. **Design**: la frontera con CH-05 (1); la firma de las cuatro funciones, el semáforo y el costo por parámetro (2a, 2b); el tipo `Contrasena` (2c); el hash ficticio y su límite ante un cambio de costo (3); la forma del token, `DatosToken` y `TokenInvalido` (4); la estructura de `seed.py` y su transacción (5a a 5f).
2. **Specs**: capacidades nuevas para la seguridad (hash y token) y el seed. Se modifican `ciclo-de-vida` (semáforo y hash ficticio en el lifespan), `errores-de-dominio` (`TokenInvalido`) y `migraciones` (el caso «sin esquema» del seed dentro del ciclo).
3. **Marcar «No especificado en la consigna»**: `min_length=1` y el rechazo de `\x00` (2c), la ausencia de `iss`/`aud`/`jti` (4c), las descripciones del catálogo (5d) y las tres protecciones de `seed.py` (5e).
4. **Excepciones acotadas a declarar**: el stock directo del seed (5d-bis), justificado como DA-31 y cubierto por S3.
5. **Acciones con efectos que el apply debe pedir antes de correr**: instalar `bcrypt` y `PyJWT` (`requirements.txt` actualizado) y las corridas de la suite contra `taller_mecanico_test`. Las evidencias TDD van en `CH-04-tdd-rojo.txt`, `CH-04-tdd-verde.txt` y `pytest-CH-04.txt`, sin borrar las corridas fallidas.
6. **Verificaciones del apply** (anotarlas en el design o en el verify): el comportamiento de bcrypt con `\x00` en la versión instalada (2c, H5) y que PyJWT no modifica un `iat` fraccionario (4a, T2).
7. **Checkpoint de la alumna**: la captura y el `.txt` de C-14 (6a a 6c). La task se marca cuando existen los dos archivos.
8. **Tasks que tocan lo de CH-03**: extender el test de ciclo 19a con el caso «sin esquema» (7c); la suite de CH-03 tiene que seguir en verde.
9. **Al cerrar el change** (archive): marcar CH-04 `[x]` en `CHANGES.md` y OB-09 como resuelta; README con el paso `python seed.py`.

## Notas para los changes siguientes

- **CH-05**:
  - La comparación de RN-07 se hace como `datos.iat < usuario.password_cambiada_en.timestamp()`, en el espacio de los `float`. Convertir `iat` a `datetime` con `fromtimestamp` puede correrse ±1 µs; `datetime.timestamp()` es monótono y no tiene ese error.
  - El login toma `app.state.semaforo_bcrypt` y `app.state.hash_ficticio` con una dependencia; en la rama «correo inexistente», verifica contra el ficticio y responde 401 siempre.
  - Traducción de `TokenInvalido` a 401 en `RutaQueTraduceErrores`; la cookie `access_token` (`HttpOnly`, `SameSite=Lax`, `Max-Age = JWT_EXPIRE_SECONDS`, `Secure` desde `COOKIE_SECURE`).
  - Los schemas usan `Contrasena` en todos los campos de contraseña (DA-16).
- **CH-09**: el historial de una orden se ordena por `(cuando, id)`. Las filas del seed (y las de una misma transacción) comparten el `cuando` de `now()`.
- **CH-11**: verifica que la captura y el `.txt` de C-14 siguen vigentes (7 `ERROR`, 6 «sólo agregado»).
