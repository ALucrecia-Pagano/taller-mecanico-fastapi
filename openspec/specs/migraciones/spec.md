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
