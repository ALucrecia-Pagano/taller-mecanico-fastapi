# Design — CH-04 `seguridad-base-seed`

## Context

**CH-01 dejó:**
- `main.py`, con un lifespan que crea `engine` y `session_factory` en `app.state` y hace `dispose()` en el `finally`. Hoy el `try` envuelve sólo el `yield`.
- `Settings`, ya con `jwt_secret_key` (`SecretStr`, mínimo 32), `jwt_algorithm`, `jwt_expire_seconds`, `bcrypt_cost` (4..31) y `bcrypt_max_concurrency`. `env.example` ya las lista.
- Un arnés con un lifespan por test (`LifespanManager`) y un solo bucle por sesión (`pytest.ini`).

**CH-02 dejó:**
- `ErrorDeDominio` y sus subclases en `app/core/errores.py`.
- `RutaQueTraduceErrores`, que busca el código HTTP recorriendo el MRO del error.

**CH-03 dejó:**
- Los 13 modelos, `CodigoEstado` y `Rol`.
- El disparador de fila `BEFORE UPDATE OR DELETE`.
- `test/solo_agregado.sql`.
- Las fixtures `esquema_al_dia`, `conexion_revertida` y `alembic_de_prueba` (subproceso contra `_test`).
- `test_m2`: el ciclo `downgrade base → upgrade head`, que es el 19a del explore.

**Todavía no hay** `security.py` ni `seed.py`, y `bcrypt` y `PyJWT` no están instalados.

Motivación y alcance: ver `proposal.md`. Requisitos y escenarios: ver `specs/`. Las decisiones salen del explore ([docs/evidencias/explore-CH-04.md](../../../docs/evidencias/explore-CH-04.md)); el número entre paréntesis remite a su tabla.

## Goals / Non-Goals

**Goals:**
- Que `security.py` sea mecanismo puro (sin base, sin HTTP, sin estado global) y que CH-05 lo componga sin reabrir decisiones.
- Que ninguna llamada a bcrypt toque el bucle de eventos, ni siquiera en el arranque o en el seed.
- Que el seed sea repetible, atómico e incapaz de dejar la base a medias.
- Que la suite siga siendo rápida (`BCRYPT_COST=4`) y que el seed no ensucie la base `_test` para los tests de CH-03.

**Non-Goals:**
- Rehashear al hacer login cuando cambia `BCRYPT_COST` (3).
- Rotación de clave o tokens revocables (`jti`), y validación de `iss`/`aud` (4c).
- Desfasajes de hora inventados en el seed (5d-ter).

## Decisions

### D1. Archivos

```
app/core/security.py           Contrasena, hashear_password, verificar_password,
                               DatosToken, emitir_token, decodificar_token
app/core/errores.py      (mod) TokenInvalido(ErrorDeDominio)
app/core/rutas.py        (mod) TokenInvalido -> 401 en CODIGO_HTTP (D9)
test/pytest/test_rutas.py (mod) T6 y T7 de errores-de-dominio (D9)
main.py                  (mod) lifespan: semaforo_bcrypt y hash_ficticio dentro del try
seed.py                        CONTRASENA_DEL_SEED, calcular_hashes, cargar_datos_iniciales, sembrar, main
requirements.txt         (mod) bcrypt>=4.0,<6 ; PyJWT>=2.10,<3
test/pytest/conftest.py  (mod) BCRYPT_COST=4 en entorno_de_prueba; fixture base_sembrada
test/pytest/test_contrasena.py   C1-C4 (sin base)
test/pytest/test_hash.py         H1-H7 (sin base)
test/pytest/test_token.py        T1-T8 (sin base)
test/pytest/test_ciclo_de_vida.py (mod) F1-F5
test/pytest/test_seed.py         S1-S14, S16
test/pytest/test_migraciones.py  (mod) S15 dentro de test_m2
README.md                (mod) python seed.py y C-14 en Git Bash
```

### D2. Hash con bcrypt (2a, 2b, 2c)

```python
async def hashear_password(password: str, *, costo: int, semaforo: asyncio.Semaphore) -> str
async def verificar_password(password: str, hash_: str, *, semaforo: asyncio.Semaphore) -> bool
```

- **Hash**: `async with semaforo: await asyncio.to_thread(bcrypt.hashpw, datos, bcrypt.gensalt(rounds=costo))`, con `datos = password.encode("utf-8")`. El hash se guarda como `str` (ASCII).
- **Verificación**: `checkpw`, por el mismo camino. Toma el costo del propio hash.
- **Límite de 72 bytes**: `hashear_password` lanza `ValueError("La contraseña supera 72 bytes")` **antes** de tocar bcrypt.
- **Por qué funciones con el semáforo por parámetro**: es la decisión 2a.
  - Descartado un semáforo global: leería `Settings` al importar.
  - Descartada una clase `Hasheador`: se aleja de «funciones puras».
- **Tests (H6, H7)**: un envoltorio con `monkeypatch` sobre `app.core.security.bcrypt.hashpw`/`checkpw` registra el hilo y cuenta las llamadas activas con un `threading.Lock`.
  - H7 usa un costo que dura lo suficiente (unos 10 ms con costo 4 alcanzan para solaparse; si no, el envoltorio suma un `time.sleep` corto **dentro del hilo**, que no bloquea el bucle) y verifica pico `== 2`.

### D3. El tipo `Contrasena` (2c)

```python
Contrasena = Annotated[str, Field(min_length=1), AfterValidator(_validar_contrasena)]
```

- `_validar_contrasena` rechaza un `\x00` y más de 72 bytes UTF-8, con mensajes propios.
- Vive en `security.py` porque el límite es de bcrypt. Lo importan los schemas de CH-05 y CH-06.
- C1-C4 lo prueban con `TypeAdapter(Contrasena)`: la `ValidationError` es lo que un schema convierte en 422.
- `min_length=1` y el rechazo de `\x00` llevan en el código el comentario «No especificado en la consigna».
- **Por qué se rechaza `\x00`**: bcrypt 5 lo acepta como un byte más (V1). Se rechaza porque un carácter nulo no tiene uso legítimo en una contraseña y suele traer problemas en otros sistemas (cadenas de C, campos de texto, herramientas que cortan en el NUL). No es por un error de bcrypt.

### D4. Lifespan (2a, 3)

```python
settings = get_settings()
engine = crear_motor(settings)
app.state.engine = engine
try:
    app.state.session_factory = crear_fabrica_de_sesiones(engine)
    app.state.semaforo_bcrypt = asyncio.Semaphore(settings.bcrypt_max_concurrency)
    app.state.hash_ficticio = await hashear_password(
        secrets.token_urlsafe(32), costo=settings.bcrypt_cost, semaforo=app.state.semaforo_bcrypt
    )  # entrada aleatoria descartada: nadie conoce el texto plano
    yield
finally:
    await engine.dispose()
```

- **El `try` se amplía para incluir el hash ficticio.** Así el requisito vigente de `ciclo-de-vida` («liberar el pool también cuando el arranque falla después de haber creado el motor») se sigue cumpliendo si falla bcrypt.
- **F2** espía `main.hashear_password`, el nombre importado en `main`, no el de `security`.
- **F5** usa `app.state.semaforo_bcrypt` con el mismo envoltorio de D2.

### D5. Token (4a a 4e)

```python
class DatosToken(BaseModel, frozen=True):
    usuario_id: int
    iat: float
    roles: list[str]

def emitir_token(usuario_id: int, roles: Iterable[str], *, settings: Settings, ahora: datetime | None = None) -> str
def decodificar_token(token: str, *, settings: Settings) -> DatosToken     # o raise TokenInvalido
```

**Emisión:**
- `ahora = ahora or datetime.now(UTC)`.
- Claims: `sub = str(usuario_id)`, `iat = ahora.timestamp()` (**`float`**: si se pasa un `datetime`, PyJWT lo trunca con `timegm`), `exp = ahora + timedelta(seconds=settings.jwt_expire_seconds)` y `roles = sorted(roles)`.
- Se firma con `settings.jwt_secret_key.get_secret_value()` y `settings.jwt_algorithm`.

**Validación:**
- `jwt.decode(token, clave, algorithms=[settings.jwt_algorithm], options={"require": ["sub", "iat", "exp"]})`, con leeway 0.
- Después, `DatosToken(usuario_id=int(sub), iat=claims["iat"], roles=claims["roles"])`: un `sub` no numérico o unos `roles` que no son lista dan `ValueError` o `ValidationError`.
- `jwt.InvalidTokenError`, `ValueError`, `ValidationError` y `KeyError` se convierten en `TokenInvalido("Token inválido")` con `raise … from None`, para no exponer el detalle de la biblioteca.

**Tests:**
- T4 emite con `ahora` 2 h atrás.
- T6 arma el token `none` con `jwt.encode(payload, None, algorithm="none")`.
- T7 firma payloads a mano con la clave correcta.

**Por qué `DatosToken` + excepción y no `None`**: decisión 4d.

### D6. Seed (5a a 5f)

```python
CONTRASENA_DEL_SEED = "Taller2026!"     # ficticia; vive sólo acá (DA-01). Los tests la importan.

async def calcular_hashes(settings) -> list[str]           # 7 hashes, gather bajo su propio semáforo
async def cargar_datos_iniciales(sesion, hashes) -> None   # TRUNCATE + altas, con flush; no confirma
async def sembrar(settings) -> None                        # motor propio, una transacción, dispose
def main() -> None                                         # imprime destino, asyncio.run(sembrar(...)),
                                                           # sin esquema -> sys.exit(mensaje)
if __name__ == "__main__": main()
```

- **Orden de `sembrar`**:
  1. `hashes = await calcular_hashes(settings)`, **antes** de abrir la transacción (DD-06).
  2. `async with fabrica() as sesion, sesion.begin(): await cargar_datos_iniciales(sesion, hashes)`.
  3. `await motor.dispose()` en un `finally`.
- **`TRUNCATE`**: `text("TRUNCATE " + ", ".join(t.name for t in SQLModel.metadata.sorted_tables) + " RESTART IDENTITY CASCADE")`. Los nombres salen de la metadata, no del usuario, así que no hay entrada externa concatenada. `alembic_version` no está en la metadata.
- **Altas**: con los modelos (`sesion.add_all([...])` y `await sesion.flush()` por grupo, en el orden de `CHANGES.md`), sin ids explícitos.
  - El catálogo se arma recorriendo `CodigoEstado`, con un diccionario de descripciones y posiciones indexado por el enum. Un estado nuevo sin entrada en el diccionario hace fallar al seed.
  - Totales: `sum(cantidad * precio_unitario)` en `Decimal`.
- **Destino**: `main()` imprime `Vaciando y cargando <db> en <host>:<port>` con los campos de `Settings`, nunca `database_url`.
- **Sin esquema** (V3): se captura el `ProgrammingError` cuyo SQLSTATE es `42P01` (`undefined_table`) y se termina con `sys.exit("Corré `alembic upgrade head` primero")`, que deja código 1. Cualquier otro error se propaga sin disfrazarse.
- **Stock directo** (R2 del proposal): `Repuesto(stock=…)` junto con `MovimientoStock(cantidad=stock, motivo="Stock inicial", usuario_id=1)`. El comentario lo declara como una excepción acotada a la puesta en marcha.
- **Alternativa descartada para los ids**: fijarlos a mano. La secuencia no avanza y la primera alta de la API choca (5c).

### D7. Arnés de pruebas (5f, 7a, 7c)

- **`entorno_de_prueba`** suma `monkeypatch.setenv("BCRYPT_COST", "4")`, que alcanza al lifespan de todos los tests. F4 lo sobrescribe con 5.
- **`base_sembrada`** (por test, sobre `esquema_al_dia`):
  - `verificar_base_de_prueba(settings_de_prueba)`, `sembrar(settings_de_prueba)` y `yield`;
  - en el teardown, el mismo `TRUNCATE` de D6, para que la base `_test` quede vacía. Si no, `test_m3`, `test_x2` y `_una_fila_por_tabla` (que usan D5 y X1) fallarían según el orden de ejecución.
- **`settings_de_prueba`** es de sesión y se resuelve antes de que `entorno_de_prueba` fije `BCRYPT_COST`. Por eso `base_sembrada` construye su propia `Settings` con `model_copy(update={"bcrypt_cost": 4})`, sin depender del orden de las fixtures.
- **S9 (foto)**: para cada tabla de la metadata, `SELECT` de todas las columnas que no son `timestamp with time zone` (según `information_schema.columns`), ordenadas por la PK.
- **S12**: `monkeypatch` reemplaza el último paso de carga (el evento de seguridad) por una función que lanza. El test compara la foto de antes y la de después.
- **S13**: `subprocess.run([sys.executable, "seed.py"], env={**os.environ, "POSTGRES_DB": base_de_prueba, "BCRYPT_COST": "4"})`, detrás de la guarda. Verifica que la contraseña de la base (`settings.postgres_password`) no aparece en la salida.
- **S14**: reusa `_bloques_del_archivo()` de `test_solo_agregado.py` (se importa y no se duplica), sobre `base_sembrada`, cada sentencia en su `SAVEPOINT`.
  - **La sentencia 7 consume el `nextval` de `orden_trabajo`**, y el teardown con `RESTART IDENTITY` lo repone.
- **S15** (R3): `test_m2`, después de `downgrade base` y antes de volver a `head`, corre `python seed.py` por subproceso y verifica `returncode != 0` y el mensaje. El `finally` existente ya garantiza volver a `head`.
- **S16**: recorre los `.py` fuera de `.venv`, como M6, y verifica que `Taller2026!` aparece sólo en `seed.py`. Los tests usan `seed.CONTRASENA_DEL_SEED`.

### D8. Evidencia de C-14 (6a a 6c)

Es un checkpoint de la alumna, con los pasos en Git Bash de la tarea correspondiente.

- El agente nunca corre `psql` ni `seed.py` contra `taller_mecanico`.
- Se verificó en el explore (sólo lectura, contra `taller_mecanico_test`) que en Git Bash `psql` ya sale en UTF-8, también con los mensajes traducidos del servidor (`lc_messages = Spanish_Argentina.1252`). `PGCLIENTENCODING=UTF8` se deja explícito.
- No se usa `winpty`.
- Un único `tee` produce la pantalla de la captura y el `.txt`.

### D9. `TokenInvalido` → 401 y cobertura del mapa (agregado de la alumna después del propose)

- **`CODIGO_HTTP`** suma `TokenInvalido: status.HTTP_401_UNAUTHORIZED`. Es la única línea nueva de `rutas.py`; `codigo_http` y la clase de ruta no cambian.
- **T6**, en `test_rutas.py`: una ruta de prueba cuya dependencia lanza `TokenInvalido("Token inválido")` responde 401 con `{"detail": "Token inválido"}`. Va en la dependencia porque así lo va a usar `get_usuario_actual` en CH-05.
- **T7**: `import main` y después un recorrido recursivo de `ErrorDeDominio.__subclasses__()`. Para cada subclase, `codigo_http(clase("x"))` no lanza. El conjunto no está vacío y contiene `TokenInvalido`.
  - `ErrorDeDominio` en sí queda fuera del recorrido: es abstracta y nunca se lanza.
- **Alternativa descartada**: cambiar `codigo_http` para que devuelva 500 cuando no encuentra código. El fallo se vería recién en producción. Con T7, la falta de un mapeo es un test en rojo.

## Verificaciones del apply

- **V1**: comportamiento de la versión instalada de bcrypt con `\x00` (¿`ValueError` o trunca?) y con más de 72 bytes en `hashpw` y en `checkpw`. Anotarlo en este design y en el resumen del apply (pedido de la alumna, 2c).
  - **Resultado (bcrypt 5.0.0)**:
    - `hashpw(b"abc\x00")` devuelve un hash sin error, y `checkpw(b"abc\x00", hash de b"abc")` da `False`: el NUL es un byte más. La premisa del explore («bcrypt lo rechaza y daría un 500») no se cumple en esta versión. El rechazo de `\x00` en `Contrasena` se mantiene por decisión de la alumna, con el motivo actualizado en D3 y en la spec `contrasenas`: no tiene uso legítimo en una contraseña y suele traer problemas en otros sistemas. El comentario del código dice lo mismo.
    - Con 73 bytes, `hashpw` y `checkpw` lanzan `ValueError` («password cannot be longer than 72 bytes»). Con 72 bytes, `hashpw` funciona.
    - **Nota para CH-05**: `verificar_password` no tiene guarda propia de 72 bytes. Un llamador que no pase por `Contrasena` obtendría el `ValueError` de bcrypt (500). El login y el cambio de contraseña tienen que usar el tipo en todos los campos.
- **V2**: que PyJWT no modifica un `iat` `float` al validarlo (T2, OB-09). Anotar la versión. Si lo modificara, frenar y consultar antes de buscar otra vía.
  - **Resultado (PyJWT 2.15.1)**:
    - `PyJWT._validate_iat` hace `iat = int(payload["iat"])` en una variable local, sólo para compararlo con la hora actual, y **no modifica el claim**. Un `iat` de `1793235710.824109` vuelve idéntico. T2 pasa sin trucos y OB-09 queda verificada.
    - Pasado como `datetime`, el mismo instante se codifica como `1793235710`, truncado: confirma la trampa que evita D5.
    - La comparación de PyJWT con la hora actual usa la parte entera. Por eso un `iat` con fracción, hasta 1 s en el futuro, no se rechaza.
- **V3**: con qué excepción y SQLSTATE llega la tabla inexistente a través de SQLAlchemy y asyncpg (se espera `ProgrammingError` con `42P01`).
  - **Resultado**: llega `sqlalchemy.exc.ProgrammingError`, cuyo `orig` es el `ProgrammingError` del adaptador asyncpg, con `sqlstate == "42P01"` y el mensaje del servidor «no existe la relación «estado_orden»». Salta en el `TRUNCATE`, después de calcular los hashes. `main()` captura sólo ese SQLSTATE (S15 en verde dentro de `test_m2`).
- **V4**: que `session.exec(text("TRUNCATE …"))` funciona con la versión instalada de SQLModel (en CH-02 ya se usó en `tablas_limpias`).
  - **Resultado (SQLModel 0.0.48)**: funciona dentro de la transacción del seed, y S9, S11 y S12 lo ejercitan (S12 prueba además que el `TRUNCATE` se revierte con el resto).
- **Observación del apply (falla previa de CH-03, corregida a pedido de la alumna, tarea 8.4)**:
  - `test_m4_modelos_y_base_sin_diferencias` fallaba si `test_migraciones.py` corría **solo**: el archivo no importaba ningún modelo y `SQLModel.metadata` quedaba vacía. En la suite completa pasaba, porque otros módulos importan los modelos antes.
  - Ahora `test_migraciones.py` importa los módulos de `esquema_esperado.MODULOS_DE_MODELOS` (la misma lista que `migrations/env.py`), y el archivo pasa solo (8 passed).

## Risks / Trade-offs

- **[Cambio de `BCRYPT_COST`]**: los usuarios con hash viejo tardan menos que el ficticio y se reabre una diferencia chica de tiempo (3). → Se acepta y se documenta; rehashear al hacer login queda fuera del alcance.
- **[Error de dominio sin código HTTP]**: `codigo_http` recorre el MRO con `next()`, y una subclase de `ErrorDeDominio` sin entrada en `CODIGO_HTTP` termina en 500. → D9: `TokenInvalido` se mapea a 401 en CH-04, y T7 hace fallar la suite ante cualquier subclase nueva sin código.
- **[T7 sólo ve las subclases importadas]**: `__subclasses__()` no encuentra una clase cuyo módulo nadie importó. → T7 importa `main`, que importa todos los routers y sus dependencias. Una excepción que la aplicación nunca importa tampoco puede lanzarse desde una ruta.
- **[El seed deja datos en `_test`]**: M3, X2, D5 y X1 asumen tablas vacías o insertan su propio catálogo. → El teardown de `base_sembrada` vacía la base; S12 y S13 también pasan por la fixture o por el mismo `TRUNCATE`.
- **[`now()` igual en todo el seed]**: dos filas del historial de la orden 2 comparten `cuando`. → CH-09 ordena por `(cuando, id)`.
- **[Stock escrito directo]**: rompe en apariencia «sólo por el punto único». → Se limita a `seed.py`, se declara en un comentario, y S3 lo garantiza.
- **[`TRUNCATE` sobre las tablas de sólo agregado]**: cualquiera con acceso a la base puede hacerlo. → Trade-off aceptado en DA-31; C-14 sólo pide rechazar `UPDATE` y `DELETE`.
- **[`fromtimestamp` corre ±1 µs]**: → CH-05 compara `iat < password_cambiada_en.timestamp()` en `float` (nota del explore).

## Migration Plan

No hay migraciones nuevas.

**Puesta en marcha:** `pip install -r requirements.txt`, que suma `bcrypt` y `PyJWT`, y después `alembic upgrade head` y `python seed.py`.

**Rollback:** revertir los archivos del change. `seed.py` no cambia el esquema, y volver a correr el seed repone el estado.
