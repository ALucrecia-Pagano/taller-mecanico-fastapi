# Tasks

## 1. Planificación y auditoría

- [x] 1.1 Leer la auditoría y actualizar CH-10 con iniciar, terminar, cancelar, aviso y C-11/C-12/C-13, vinculando cada afirmación a archivos y tests.
- [x] 1.2 Revisar C-14 y C-15 contra migraciones, modelos, repositorios y tests actuales; registrar cualquier riesgo sin inventar resultados.
- [x] 1.3 Buscar credenciales reales y prácticas prohibidas sin abrir `.env`, dejando documentada la contraseña ficticia del seed como excepción esperada.

## 2. Documentación de entrega

- [x] 2.1 Completar README con requisitos, entorno, `.env`, generación de JWT, bases, migraciones, seed, servidor, pytest, REST Client e índice de evidencias.
- [x] 2.2 Preparar `verify-CH-11.md` con informe de implementación, matriz de cobertura, riesgos y sección de verificación manual vacía.

## 3. Verificación final

- [x] 3.1 Proteger la evidencia C-15 frente a sobrescritura y ejecutar `pytest -v` sólo contra `taller_mecanico_test`, registrando la salida en `docs/evidencias/pytest-CH-11.txt`.
- [x] 3.2 Validar que el README y las evidencias no exponen secretos reales y que los comandos documentados son coherentes con el repositorio.
- [x] 3.3 Revisar el informe final, mostrar riesgos ordenados por gravedad, total de tests y `git status --short`, sin archivar el change.
