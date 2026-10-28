# migraciones Specification

## Purpose

Define cómo se configura la herramienta de migraciones: plantilla asincrónica, sin credenciales en el repositorio y con la conexión tomada de la configuración de la aplicación. El esquema se crea sólo con migraciones.

## Requirements

### Requirement: Configuración de migraciones sin credenciales
El archivo `alembic.ini` MUST NOT contener la dirección de la base ni ninguna credencial. Las migraciones SHALL tomar la dirección de la configuración de la aplicación, también cuando la contraseña tiene caracteres especiales como `%`.

#### Scenario: A1 — `alembic.ini` sin dirección de la base
- **GIVEN** Dado el `alembic.ini` del repositorio
- **WHEN** Cuando se buscan líneas `sqlalchemy.url`
- **THEN** Entonces no hay ninguna con valor

### Requirement: Migraciones operables contra la base configurada
La herramienta de migraciones SHALL poder conectarse, con la plantilla asincrónica, a la base que indica la configuración del entorno en que se la ejecuta.

#### Scenario: A2 — Humo contra la base de prueba
- **GIVEN** Dado un entorno con `POSTGRES_DB` apuntando a la base de prueba (verificada por la guarda)
- **WHEN** Cuando se ejecuta `alembic current`
- **THEN** Entonces el comando termina con código 0

### Requirement: Esquema creado sólo con migraciones
`alembic upgrade head` sobre una base vacía SHALL crear las 13 tablas del dominio y dejarla en la última versión. La aplicación MUST NOT crear tablas por otro camino: ningún archivo Python del proyecto usa `create_all`.

#### Scenario: M1 — Upgrade sobre base vacía
- **GIVEN** Dada la base de prueba sin tablas del dominio
- **WHEN** Cuando se ejecuta `alembic upgrade head`
- **THEN** Entonces existen las 13 tablas del dominio y la versión registrada es la de la segunda migración

#### Scenario: M6 — Ningún `create_all`
- **GIVEN** Dados todos los archivos `.py` del proyecto (fuera del entorno virtual)
- **WHEN** Cuando se buscan usos de `create_all`
- **THEN** Entonces no hay ninguno

### Requirement: Ciclo de ida y vuelta
`alembic downgrade base` SHALL deshacer todo lo que crean las migraciones: las 13 tablas, la función y los disparadores de sólo agregado. Un nuevo `alembic upgrade head` SHALL volver a crearlo todo (Ejercicio 2).

#### Scenario: M2 — Upgrade, downgrade base y upgrade otra vez
- **GIVEN** Dada la base de prueba en la última versión
- **WHEN** Cuando se ejecuta `alembic downgrade base` y luego `alembic upgrade head`
- **THEN** Entonces después del downgrade no queda ninguna de las 13 tablas ni la función del disparador
- **AND** las tablas de prueba de la suite, si existen, siguen
- **AND** después del segundo upgrade están otra vez las 13 tablas y la función

### Requirement: Catálogo vacío después de migrar
Las migraciones SHALL crear la tabla `estado_orden` vacía: sus filas son datos y las carga `seed.py`.

#### Scenario: M3 — Catálogo sin filas
- **GIVEN** Dada la base de prueba recién migrada a la última versión
- **WHEN** Cuando se cuentan las filas de `estado_orden`
- **THEN** Entonces hay 0

### Requirement: Dos migraciones leídas antes de aplicarse
La primera migración SHALL ser la generada por comparación automática, con todas las tablas. La segunda SHALL estar escrita a mano, con el disparador de sólo agregado. Cada una SHALL llevar un comentario que diga que se leyó antes de aplicarla. Ninguna MUST mencionar las tablas de prueba de la suite.

#### Scenario: M5 — Comentario de lectura y sin tablas de prueba
- **GIVEN** Dados los archivos de `migrations/versions/`
- **WHEN** Cuando se los lee
- **THEN** Entonces son exactamente dos, cada uno tiene el comentario «Leída antes de aplicarla», y ninguno contiene `prueba_`

### Requirement: Modelos y migraciones coinciden
La metadata que usa Alembic SHALL contener exactamente las 13 tablas del dominio. Comparada contra la base migrada, no SHALL haber diferencias: ningún cambio en un modelo queda sin migrar. Las tablas de prueba de la suite se ignoran en la comparación.

#### Scenario: M7 — La metadata tiene las 13 tablas
- **GIVEN** Dados los modelos que importa la configuración de Alembic
- **WHEN** Cuando se listan las tablas de la metadata
- **THEN** Entonces son exactamente las 13 del dominio, sin ninguna tabla de prueba

#### Scenario: M4 — Sin diferencias entre modelos y base
- **GIVEN** Dada la base de prueba en la última versión, con o sin tablas de prueba de la suite
- **WHEN** Cuando se compara la metadata de los modelos contra la base
- **THEN** Entonces, descartando sólo la eliminación de tablas `prueba_*`, la lista de diferencias está vacía
