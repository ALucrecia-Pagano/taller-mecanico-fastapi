# Design

## Context

CH-01 a CH-10 ya aportan la aplicación, la suite, los archivos `.http` y
evidencias parciales. CH-11 debe consolidar documentación y verificación sin
alterar el contrato de la API. La auditoría existente es un borrador anterior a
CH-10 y debe actualizarse con evidencia concreta.

## Goals / Non-Goals

**Goals:**

- Hacer reproducible el arranque desde cero y la ejecución de pruebas.
- Auditar el código y las evidencias contra la consigna, sin exponer secretos.
- Registrar una corrida completa de pytest sólo contra `taller_mecanico_test`.
- Mantener separada la verificación manual que realizará la responsable.

**Non-Goals:**

- No agregar endpoints, reglas de negocio, dependencias ni migraciones.
- No modificar `.env`, bases de datos productivas ni evidencias de changes
  anteriores.
- No ejecutar ni registrar comandos que requieran credenciales reales.

## Decisions

- **README como guía operativa única:** se consolidan allí los comandos de
  preparación, migración, seed, servidor, pytest y REST Client.
- **Auditoría basada en referencias:** cada afirmación se vincula a archivos,
  símbolos, tests o evidencias; lo no verificable queda como riesgo.
- **Evidencia C-15 protegida:** antes de la suite se inspecciona el test que
  escribe `C-15-consultas.txt`; si la corrida pudiera sobrescribir la evidencia
  histórica, se usa un respaldo en el scratchpad y se restaura después.
- **Búsqueda de secretos sin abrir `.env`:** se inspeccionan nombres y valores
  versionados mediante búsquedas acotadas, tratando la contraseña ficticia del
  seed como excepción esperada.
- **Sin correcciones de código por defecto:** un hallazgo de implementación se
  informa como riesgo; sólo se corrige si la auditoría demuestra un defecto
  directamente exigido y existe autorización compatible.

## Risks / Trade-offs

- [Riesgo] La suite puede depender de PostgreSQL y del entorno local → se
  registra el comando y su salida, sin afirmar una instalación limpia no
  ejecutada.
- [Riesgo] La evidencia C-15 puede ser reemplazada por un test → se respalda o
  redirige únicamente durante la corrida, conservando el archivo histórico.
- [Riesgo] La auditoría estática no certifica el arranque manual → se deja la
  sección manual vacía y se identifican las condiciones excluyentes.
