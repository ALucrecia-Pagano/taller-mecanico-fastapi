# Proposal

## Why

El proyecto ya implementa CH-01 a CH-10, pero la entrega todavía necesita una
verificación reproducible desde cero, documentación final y trazabilidad completa
contra la consigna. Este change cierra esas condiciones sin introducir reglas de
negocio nuevas.

## What Changes

- Consolidar el README con requisitos, instalación, migraciones, seed, servidor,
  pytest y ejecución de los 19 archivos `.http`.
- Completar la auditoría contra la consigna con el estado real de CH-10 y sus
  evidencias.
- Verificar la vigencia de las evidencias C-14 y C-15 frente al código final.
- Revisar el repositorio en busca de credenciales reales y prácticas prohibidas.
- Ejecutar y registrar la suite completa contra `taller_mecanico_test`.
- Entregar un informe CH-11 con cobertura, riesgos remanentes y verificación
  manual pendiente.

## Capabilities

### New Capabilities

- `cierre-entrega`: documentación reproducible y evidencia de verificación final
  de la API contra la consigna.

### Modified Capabilities

- Ninguna.

## Impact

- Documentación: `README.md`, `docs/evidencias/auditoria-consigna.md` y nuevas
  evidencias CH-11.
- Verificación: suite pytest completa y revisión de C-14/C-15.
- No se agregan endpoints, dependencias, migraciones ni cambios de esquema.
