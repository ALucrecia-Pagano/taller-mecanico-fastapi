# Spec Delta

## Purpose

Permite entregar el proyecto con instrucciones reproducibles, trazabilidad frente
a la consigna y evidencias finales verificables sin ocultar riesgos pendientes.

## ADDED Requirements

### Requirement: Documentación reproducible
El proyecto SHALL documentar los requisitos, la instalación desde cero, la creación de bases, las migraciones, el seed, el arranque y las pruebas.

#### Scenario: Puesta en marcha documentada
- **WHEN** una persona sigue el README desde un checkout limpio
- **THEN** encuentra los comandos para crear `.venv`, instalar dependencias, configurar `.env`, crear las bases, ejecutar `alembic upgrade head`, `python seed.py` y `uvicorn main:app`

#### Scenario: Pruebas documentadas
- **WHEN** la persona necesita verificar la entrega
- **THEN** encuentra cómo ejecutar pytest contra la base `_test` y cada archivo `.http` después de ejecutar el seed

### Requirement: Auditoría trazable
La entrega SHALL relacionar requisitos, casos y reglas de negocio con archivos, tests o evidencias existentes, distinguiendo cobertura confirmada de riesgos pendientes.

#### Scenario: CH-10 integrado
- **WHEN** se revisa la auditoría después de CH-10
- **THEN** iniciar, terminar, cancelar, aviso y C-11/C-12/C-13 figuran con su estado real, archivo y test sin marcadores obsoletos de pendiente

#### Scenario: Riesgo no resuelto
- **WHEN** una comprobación final no puede certificarse o queda parcialmente cubierta
- **THEN** la auditoría lo conserva como riesgo explícito y lo ordena por gravedad sin inventar evidencia

### Requirement: Evidencias finales
La entrega SHALL conservar evidencias vigentes de las restricciones de sólo agregado y de la cantidad fija de consultas del detalle.

#### Scenario: Evidencia C-14
- **WHEN** se compara la evidencia C-14 con el esquema final
- **THEN** siguen identificables los seis rechazos de UPDATE/DELETE y el rechazo de la FK del catálogo

#### Scenario: Evidencia C-15
- **WHEN** se compara la evidencia C-15 con el detalle de órdenes de 2 y 4 ítems
- **THEN** se observa la misma cantidad de consultas de dominio y ausencia de consultas por ítem

### Requirement: Suite final registrada
La entrega SHALL registrar la corrida completa de pytest contra la base de pruebas y dejar la verificación manual separada.

#### Scenario: Corrida completa
- **WHEN** se ejecuta la suite final autorizada
- **THEN** el resultado completo queda en `docs/evidencias/pytest-CH-11.txt` y no se presenta una evidencia histórica como corrida nueva

#### Scenario: Verificación manual pendiente
- **WHEN** se entrega el informe CH-11 antes de la prueba manual desde cero
- **THEN** la sección "Verificación manual" permanece vacía y lista para completar
