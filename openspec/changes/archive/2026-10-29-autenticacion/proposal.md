# Proposal

## Why

CH-01 a CH-04 ya aportan infraestructura, persistencia y mecanismos de seguridad, pero todavía no se puede registrar ni autenticar un usuario desde la API. CH-05 conecta esos mecanismos mediante `/auth/*`, respetando RN-02 y RN-07 a RN-09 y dejando la autorización para CH-06.

## What Changes

- Registro atómico de usuario, rol CLIENTE, ficha y evento; duplicados → 409 sin filas sueltas.
- Login uniforme con hash real/ficticio, conteo por correo/IP, intentos confirmados en sesión propia y cookie HttpOnly; logout público.
- `get_usuario_actual` por cookie con invalidación por cambio de contraseña y `/auth/yo` con roles actuales y del token.
- Cambio de contraseña atómico, cookie nueva y rechazo contractual de contraseña repetida.
- TDD sin medir tiempos, tres archivos `.http`, README y evidencia final pytest. Decisiones definitivas: `docs/evidencias/explore-CH-05.md`, trabajado con Codex; consigna leída desde su conversión `.md` (manda el PDF).

## Capabilities

### New Capabilities

- `registro-de-clientes`: auto-registro transaccional y conflictos.
- `sesiones-de-usuario`: login, cookie, autenticación, logout, perfil y cambio de contraseña.
- `intentos-de-acceso`: límite, IP y persistencia independiente de verificaciones.

### Modified Capabilities

- `errores-de-dominio`: agregar traducción de límite a 429 con Retry-After sin cambiar T6 ni el mecanismo puro de TokenInvalido.
- `contrasenas`: agregar contrato cruzado que rechaza password_nueva igual a password_actual y aplicación de Contrasena en `/auth`.

## Impact

Capas nuevas en `app/modules/usuarios/`, repositorio mínimo en `app/modules/clientes/repository.py`, `app/core/dependencies.py`, extensiones de errores/rutas y registro del router en `main.py`. Tests en `test/pytest/`; `.http` C-02 a C-05 y README. Sin migraciones ni dependencias nuevas; pypdf sigue sólo como herramienta local. CH-06 conserva requiere_rol, cambio obligatorio, grupo protegido y administración de usuarios/roles/eventos. Governance CRÍTICO: esta propuesta no autoriza código ni corridas sobre bases; Amanda hace los commits.
