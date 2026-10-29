# Spec Delta — solo-agregado

## ADDED Requirements

### Requirement: Demostración sobre los datos iniciales
`test/solo_agregado.sql` SHALL funcionar sobre la base recién cargada por `python seed.py`. La verificación inicial pasa y las siete sentencias fallan como se espera, sin filas agregadas a mano.

#### Scenario: S14 — C-14 sobre el seed
- **GIVEN** Dada la base de prueba recién cargada por el seed
- **WHEN** Cuando se ejecutan la verificación inicial y, una por una, las siete sentencias de `test/solo_agregado.sql`
- **THEN** Entonces la verificación no corta
- **AND** las seis primeras se rechazan con SQLSTATE `23001` y la séptima con SQLSTATE `23503` por `fk_orden_trabajo_estado_estado_orden`

### Requirement: Evidencia de C-14
La entrega SHALL incluir la evidencia de `psql` de C-14, tomada sobre la base de la aplicación después de `python seed.py`: una captura (`docs/evidencias/capturas/C-14-solo-agregado.png`) y la misma salida en texto UTF-8 (`docs/evidencias/C-14-psql.txt`). El texto es decisión de la alumna. La toma la alumna.

#### Scenario: E1 — Salida en texto completa y legible
- **GIVEN** Dado `docs/evidencias/C-14-psql.txt`, generado con `psql -f test/solo_agregado.sql` sobre `taller_mecanico` recién cargada
- **WHEN** Cuando se inspecciona
- **THEN** Entonces es texto UTF-8, con los acentos legibles
- **AND** tiene 7 líneas `ERROR` y 6 con «sólo agregado»
- **AND** existe la captura `docs/evidencias/capturas/C-14-solo-agregado.png`
