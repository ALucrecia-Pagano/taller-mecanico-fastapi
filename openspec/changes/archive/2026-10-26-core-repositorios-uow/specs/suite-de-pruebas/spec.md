# Spec Delta — suite-de-pruebas

## ADDED Requirements

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
