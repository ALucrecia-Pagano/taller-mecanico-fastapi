# configuracion Specification

## Purpose

Define cómo la aplicación lee su configuración desde el entorno o un archivo `.env`, qué secretos son obligatorios y cómo se protegen, y qué valores se rechazan, para que la aplicación nunca arranque con un secreto faltante, vacío o expuesto.

## Requirements

### Requirement: Configuración desde el entorno con valores por defecto
El sistema SHALL leer su configuración desde las variables de entorno o desde un archivo `.env` no versionado, con los nombres y los valores por defecto de DA-07. Las variables del entorno tienen prioridad sobre el `.env`. La configuración se resuelve una sola vez por proceso y se reutiliza; se puede volver a leer de forma explícita.

#### Scenario: S1 — Carga con todas las variables y defaults aplicados
- **GIVEN** Dado un entorno con `POSTGRES_PASSWORD` y una `JWT_SECRET_KEY` válida, y sin `JWT_ALGORITHM` ni `DB_POOL_SIZE`
- **WHEN** Cuando se carga la configuración
- **THEN** Entonces la carga es exitosa, `JWT_ALGORITHM` vale `HS256` y `DB_POOL_SIZE` vale `5`

#### Scenario: S8 — Una sola lectura por proceso, relectura explícita
- **GIVEN** Dado que la configuración ya se resolvió una vez
- **WHEN** Cuando se la pide de nuevo
- **THEN** Entonces se obtiene la misma instancia
- **AND** después de invalidar la lectura en caché, un cambio en el entorno se refleja en la nueva instancia

### Requirement: Secretos obligatorios
`POSTGRES_PASSWORD` y `JWT_SECRET_KEY` MUST NOT tener valor por defecto, y un valor vacío cuenta como faltante. Si alguno falta o está vacío, la configuración falla y la aplicación no arranca. `JWT_SECRET_KEY` MUST tener al menos 32 caracteres (decisión de la alumna: RFC 7518 pide para HS256 una clave de al menos 256 bits; **No especificado en la consigna**).

#### Scenario: S2 — Falta la contraseña de la base
- **GIVEN** Dado un entorno sin `POSTGRES_PASSWORD`
- **WHEN** Cuando se carga la configuración
- **THEN** Entonces la carga falla con un error de validación que nombra la variable

#### Scenario: S2 — Falta la clave de firma
- **GIVEN** Dado un entorno sin `JWT_SECRET_KEY`
- **WHEN** Cuando se carga la configuración
- **THEN** Entonces la carga falla con un error de validación que nombra la variable

#### Scenario: S3 — Contraseña de la base vacía
- **GIVEN** Dado `POSTGRES_PASSWORD=""` (como queda al copiar `env.example` sin completarlo)
- **WHEN** Cuando se carga la configuración
- **THEN** Entonces la carga falla

#### Scenario: S3 — Largo mínimo de la clave de firma
- **GIVEN** Dada una `JWT_SECRET_KEY` de 31 caracteres
- **WHEN** Cuando se carga la configuración
- **THEN** Entonces la carga falla
- **AND** con una clave de 32 caracteres la carga es exitosa

### Requirement: Dirección de la base calculada con driver asincrónico
La dirección de la base SHALL calcularse a partir de `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST` y `POSTGRES_PORT`, con el driver `postgresql+asyncpg`. Los caracteres especiales de la contraseña se escapan, de modo que la dirección resultante siempre es válida.

#### Scenario: S4 — Driver y contraseña con caracteres especiales
- **GIVEN** Dada una `POSTGRES_PASSWORD` que contiene `@`, `/`, `%` y `:`
- **WHEN** Cuando se calcula la dirección de la base
- **THEN** Entonces la dirección usa el driver `postgresql+asyncpg`
- **AND** al interpretarla de vuelta, la contraseña, el host, el puerto y la base son los originales

### Requirement: Los secretos no se exponen
La representación textual de la configuración MUST NOT contener la contraseña de la base, la clave de firma ni la dirección de la base (que incluye la contraseña).

#### Scenario: S5 — Representación sin secretos
- **GIVEN** Dada una configuración cargada con una contraseña y una clave conocidas
- **WHEN** Cuando se obtiene su representación textual
- **THEN** Entonces ni la contraseña, ni la clave, ni la dirección de la base aparecen en el texto

### Requirement: Valores inválidos rechazados
La configuración SHALL rechazar las claves desconocidas en el `.env` y los valores numéricos fuera de rango: `DB_POOL_SIZE`, `JWT_EXPIRE_SECONDS` y `BCRYPT_MAX_CONCURRENCY` mayores que 0, y `BCRYPT_COST` entre 4 y 31 (rango que acepta bcrypt). **No especificado en la consigna**: es validación de configuración.

#### Scenario: S6 — Clave desconocida en el `.env`
- **GIVEN** Dado un `.env` con una clave que no es de la configuración (p. ej. `JWT_SECRET=...` por error de tipeo)
- **WHEN** Cuando se carga la configuración
- **THEN** Entonces la carga falla

#### Scenario: S7 — Pool en cero
- **GIVEN** Dado `DB_POOL_SIZE=0`
- **WHEN** Cuando se carga la configuración
- **THEN** Entonces la carga falla

#### Scenario: S7 — Bordes del costo de bcrypt
- **GIVEN** Dado `BCRYPT_COST` igual a 3 o a 32
- **WHEN** Cuando se carga la configuración
- **THEN** Entonces la carga falla
- **AND** con 4 y con 31 la carga es exitosa

### Requirement: Plantilla del entorno y secretos fuera del repositorio
El repositorio SHALL incluir un `env.example` que declare exactamente las variables de la configuración, con `POSTGRES_PASSWORD` y `JWT_SECRET_KEY` vacías y el comando fijo para generar la clave (`python -c "import secrets; print(secrets.token_urlsafe(64))"`). El archivo `.env` MUST estar ignorado por git.

#### Scenario: E1 — `env.example` sincronizado con la configuración
- **GIVEN** Dados el `env.example` del repositorio y las variables que declara la configuración
- **WHEN** Cuando se comparan
- **THEN** Entonces declaran el mismo conjunto de variables
- **AND** `POSTGRES_PASSWORD` y `JWT_SECRET_KEY` están vacías

#### Scenario: E2 — `.env` ignorado
- **GIVEN** Dado el `.gitignore` del repositorio
- **WHEN** Cuando se revisan sus entradas
- **THEN** Entonces `.env` está ignorado
