# Proposal

## Why

CH-05 autentica sesiones, pero aún no protege operaciones por roles ni por cambio obligatorio. CH-06 completa el Ejercicio 5 para administrar personal, vigencias e historial de seguridad sin confiar permisos al JWT.

## What Changes

- Crear requiere_rol y el control único de cambio obligatorio en rutas_protegidas; preservar /auth y salud.
- Agregar POST /usuarios; GET/POST /usuarios/{id}/roles; DELETE /usuarios/{id}/roles/{rol}; GET /eventos.
- Alta, asignación y revocación atómicas con eventos DA-13; roles administrativos limitados a ADMIN/RECEPCION/MECANICO [Alumna D1=B].
- Reasignar vencidos conservando historial; 404 sin asignación abierta [Alumna D2=A].
- Proteger RN-05 con candado asesor transaccional y revalidación fresca [Alumna D3=A]; conservar excepción por expiración de DA-15/SU-11.
- Contratos/respuestas/mensajes D4=A, TDD real PostgreSQL y demostraciones C-07 a C-09. C-06 completo queda en CH-09.

## Capabilities

### New Capabilities

- `autorizacion`: roles efectivos desde base, grupo protegido y control obligatorio.
- `administracion-de-usuarios`: alta de personal, vigencias, historial y autoprotección concurrente.
- `eventos-de-seguridad`: auditoría atómica y listado administrativo paginado.

### Modified Capabilities

- `errores-de-dominio`: traducción explícita de errores de autorización a 403.

## Impact

Modificar main.py, app/core/dependencies.py, errores.py y rutas.py; ampliar capas existentes del módulo usuarios sin modificar esquemas de tablas ni agregar migraciones/dependencias. Agregar pytest bajo test/pytest y los tres .http propios. Gobernanza CRÍTICA aprobada por Amanda en el alcance documentado en docs/evidencias/explore-CH-06.md; no commits/push, instalaciones ni lectura/modificación de .env.

