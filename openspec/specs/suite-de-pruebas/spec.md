# suite-de-pruebas Specification

## Purpose

Garantiza que la suite automática corra sólo contra la base de prueba `<POSTGRES_DB>_test` y nunca contra la base de la aplicación (DA-29).

## Requirements

### Requirement: Guarda de la base de prueba
Antes de cada prueba que toque la base, y antes de cada ejecución de migraciones desde la suite, la suite SHALL verificar que la configuración efectivamente resuelta (la misma que va a usar la aplicación, después de cualquier ajuste del entorno hecho por la prueba) apunta a una base cuyo nombre termina en `_test`. Si no es así, la prueba no corre (decisión de la alumna).

#### Scenario: T1 — Base de la aplicación rechazada
- **GIVEN** Dada una configuración con `POSTGRES_DB=taller_mecanico`
- **WHEN** Cuando se aplica la guarda
- **THEN** Entonces la guarda la rechaza y la prueba no corre

#### Scenario: T1 — Base de prueba aceptada
- **GIVEN** Dada una configuración con `POSTGRES_DB=taller_mecanico_test`
- **WHEN** Cuando se aplica la guarda
- **THEN** Entonces la guarda la acepta

### Requirement: Derivación de la base de prueba
La suite SHALL derivar la base de prueba como `<POSTGRES_DB>_test` a partir de la configuración de la aplicación. Si `POSTGRES_DB` ya termina en `_test`, la suite aborta con un mensaje claro en lugar de derivar `*_test_test`.

#### Scenario: T2 — El `.env` ya apunta a la base de prueba
- **GIVEN** Dado un `.env` con `POSTGRES_DB=taller_mecanico_test`
- **WHEN** Cuando arranca la suite
- **THEN** Entonces la corrida se aborta con un mensaje que indica que `POSTGRES_DB` debe ser la base de la aplicación

### Requirement: Tablas de prueba de la suite
La suite SHALL crear sus tablas de prueba (`prueba_articulo` y `prueba_baja`) en la base de prueba con sentencias DDL escritas a mano, nunca con `create_all`, y SHALL borrarlas al terminar. La creación SHALL ocurrir sólo después de aplicar la guarda de `_test` a la configuración efectivamente resuelta, y SHALL tolerar que las tablas ya existan por una corrida interrumpida. Decisión de la alumna.

#### Scenario: F1 — La guarda va antes que el DDL
- **GIVEN** Dada una configuración con `POSTGRES_DB` que no termina en `_test`, apuntada a un puerto en el que no escucha nadie
- **WHEN** Cuando se intenta crear las tablas de prueba
- **THEN** Entonces falla con el error de la guarda, no con un error de conexión, es decir, antes de intentar conectarse

#### Scenario: F2 — Tablas que quedaron de una corrida interrumpida
- **GIVEN** Dadas las tablas de prueba ya existentes en la base de prueba
- **WHEN** Cuando se las vuelve a crear
- **THEN** Entonces la creación termina sin error y las tablas quedan vacías
