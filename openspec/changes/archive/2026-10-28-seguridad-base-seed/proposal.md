# Proposal — CH-04 `seguridad-base-seed`

## Why

El login (CH-05) y todos los casos de prueba necesitan dos cosas que todavía no existen.

- **Las piezas de seguridad**: bcrypt fuera del bucle y bajo un semáforo, el límite de 72 bytes, el hash ficticio del lifespan y el JWT con un `iat` que no se trunca.
- **Una base en un estado inicial conocido.** Los `.http` y C-02 a C-14 dependen de `python seed.py`, y sin el catálogo de estados no se puede crear ninguna orden.

Este change carga la parte base del Ejercicio 4 (16 %, compartido con CH-05), el `seed.py` de la puesta en marcha y la evidencia de `psql` de C-14 que CH-03 le pasó (R4). Governance **CRÍTICO**.

Las decisiones se tomaron en el explore, con la alumna, una por vez: [docs/evidencias/explore-CH-04.md](../../../docs/evidencias/explore-CH-04.md). Son definitivas. El número entre paréntesis remite a su tabla.

## What Changes

- **`app/core/security.py`**, con funciones de mecanismo, sin base ni HTTP (1):
  - `hashear_password(password, *, costo, semaforo)` y `verificar_password(password, hash_, *, semaforo)`: `asyncio.to_thread` bajo el semáforo recibido. El costo sale de `BCRYPT_COST`. `hashear_password` lanza su propio `ValueError` con más de 72 bytes (2a a 2c).
  - El tipo `Contrasena`: como máximo 72 bytes UTF-8 (no caracteres), `min_length=1` y sin `\x00`. Los dos últimos son «No especificado en la consigna» (2c).
  - `emitir_token(usuario_id, roles, *, settings, ahora=None)` con `sub` (`str`), `iat` (`float`, con la fracción de segundo), `exp` y `roles`, firmado con `JWT_ALGORITHM` (4a a 4c, 4e).
  - `decodificar_token(token, *, settings)`: lista fija de algoritmos y `sub`, `iat` y `exp` obligatorios. Devuelve `DatosToken(usuario_id, iat, roles)` o lanza `TokenInvalido` (4d).
- **`app/core/errores.py`**: suma la excepción de dominio `TokenInvalido` (4d).
- **`app/core/rutas.py`**: `TokenInvalido` → **401** en el mapa de traducción. Un test recorre todas las subclases de `ErrorDeDominio` y verifica que cada una tiene su código, para que ningún error de dominio nuevo termine en 500 (pedido de la alumna después del propose).
- **`main.py`**: el lifespan crea `app.state.semaforo_bcrypt` (de `BCRYPT_MAX_CONCURRENCY`) y calcula **una vez** `app.state.hash_ficticio`, con una entrada aleatoria descartada y el costo de `Settings` (2a, 3; Desvío 2 de `CHANGES.md`).
- **`seed.py`** en la raíz:
  - calcula los 7 hashes de `Taller2026!` antes de abrir la transacción;
  - en **una sola transacción**, vacía las 13 tablas de la metadata con `TRUNCATE … RESTART IDENTITY CASCADE` (sin tocar `alembic_version`) y carga DA-01 a DA-06 en el orden de `CHANGES.md`, con el catálogo desde `CodigoEstado`;
  - sin flag: el comando es `python seed.py`;
  - imprime la base, el host y el puerto antes de vaciar;
  - sin esquema, corta con «Corré `alembic upgrade head` primero» (5a a 5e).
- **`requirements.txt`**: `bcrypt>=4.0,<6` y `PyJWT>=2.10,<3` (2d, 4e).
- **Suite pytest test-first** (7):
  - `test_contrasena.py` (C1-C4), `test_hash.py` (H1-H7), `test_token.py` (T1-T8) y `test_seed.py` (S1-S14);
  - `test_ciclo_de_vida.py` suma F1-F5;
  - el test de ciclo de CH-03 (`test_m2`, el 19a del explore) suma el caso «sin esquema»;
  - `entorno_de_prueba` fija `BCRYPT_COST=4`;
  - la fixture del seed deja `_test` vacía.
- **Evidencia de C-14**, a cargo de la alumna, en Git Bash: `docs/evidencias/capturas/C-14-solo-agregado.png` y `docs/evidencias/C-14-psql.txt` (obligatorio) (6a a 6c).
- **`README.md`**: el paso `python seed.py` y los pasos de C-14.

### Refinamientos de alcance respecto de `CHANGES.md`

Como los Desvíos de `CHANGES.md`, no renombran, fusionan ni reordenan changes:

- **R1**: `TokenInvalido` nace en CH-04 **con** su traducción a 401. Por pedido de la alumna se adelanta de CH-05, junto con el test que exige un código HTTP para cada error de dominio (4d).
- **R2**: el seed escribe `repuesto.stock` directo, junto con su movimiento «Stock inicial», porque el punto único de stock nace en CH-08. Es una excepción acotada a la puesta en marcha, como DA-31, y la garantiza el test S3 (`stock == suma de movimientos`) (5d-bis).
- **R3**: el caso «sin esquema» del seed se prueba dentro del test de ciclo de CH-03, que se modifica; la suite de CH-03 tiene que seguir en verde (7c).
- **R4**: el piso de PyJWT sube de 2.8 (PDF) a **2.10**, la versión que valida `sub` como string. Sigue cumpliendo el mínimo de la consigna (4e).

### Queda afuera (y dónde va)

| Qué | Change |
|---|---|
| Cookie `access_token` (poner y borrar), schemas de `/auth`, servicio de login (límite → verificación → token), `get_usuario_actual`, comparación de `iat` con `password_cambiada_en` (RN-07), consulta de roles vigentes | CH-05 |
| Punto único de stock | CH-08 |
| Orden del historial por `(cuando, id)` | CH-09 |
| Revisión de que la evidencia de C-14 sigue vigente | CH-11 |

## Capabilities

### New Capabilities

- `contrasenas`: hash y verificación de contraseñas con bcrypt, fuera del bucle de eventos y con concurrencia limitada, costo configurable y el contrato de contraseña (72 bytes, no vacía, sin NUL).
- `token-de-acceso`: emisión y validación del JWT firmado, con `sub`, `iat` fraccionario, `exp` y roles, y el rechazo de todo token inválido como error de dominio.
- `datos-iniciales`: `seed.py` deja la base en el estado inicial conocido del PDF: vaciado repetible, ids fijos por orden de alta, una sola transacción y sus protecciones.

### Modified Capabilities

- `ciclo-de-vida`: el arranque suma el semáforo de bcrypt y el hash ficticio del login, calculado una vez con el costo de la configuración.
- `solo-agregado`: el script de C-14 se demuestra sobre los datos iniciales, con su evidencia de `psql`.
- `errores-de-dominio`: el token inválido se traduce a 401, y todo error de dominio tiene que tener un código HTTP.

## Impact

- **Archivos nuevos**:
  - `app/core/security.py` y `seed.py`;
  - `test/pytest/test_contrasena.py`, `test_hash.py`, `test_token.py` y `test_seed.py`;
  - `docs/evidencias/C-14-psql.txt` y `docs/evidencias/capturas/C-14-solo-agregado.png` (de la alumna);
  - evidencias TDD: `CH-04-tdd-rojo.txt`, `CH-04-tdd-verde.txt` y `pytest-CH-04.txt`.
- **Archivos modificados**:
  - `app/core/errores.py` (`TokenInvalido`), `app/core/rutas.py` (401) y `main.py` (lifespan);
  - `test/pytest/test_rutas.py` (T6 y T7 de `errores-de-dominio`);
  - `requirements.txt`;
  - `test/pytest/conftest.py` (`BCRYPT_COST=4` y fixture `base_sembrada`);
  - `test/pytest/test_ciclo_de_vida.py` (F1-F5) y `test/pytest/test_migraciones.py` (caso «sin esquema» en `test_m2`);
  - `README.md`;
  - `CHANGES.md` (CH-04 `[x]` y OB-09 resuelta, al archivar).
- **Dependencias nuevas**: `bcrypt` y `PyJWT`. Se instalan con permiso.
- **Base**:
  - `taller_mecanico_test`: la suite y el seed por subproceso, con permiso;
  - `taller_mecanico`: sólo la alumna (seed y psql de C-14).
- **API**: sin endpoints nuevos.
- **RN y casos**:
  - RN: base de RN-09 (hash ficticio) y de RN-07 (`iat` sin truncar); requisitos no funcionales de Asincronía y Credenciales.
  - DA/DD aplicados: DA-01 a DA-08, DA-13, DA-31, DD-01, DD-02, DD-06 y DD-08.
  - Habilita C-02 a C-14.
  - Evidencia propia: C-14.
