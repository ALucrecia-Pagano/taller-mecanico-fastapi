# Explore CH-06 — autorizacion-usuarios-roles

Fecha: 2026-10-29. Trabajado con **Codex**, mediante source-command-opsx-explore. Governance CRÍTICO. Amanda confirmó todas las recomendaciones y D1=B, D2=A, D3=A, D4=A; autorizó guardar esta exploración y Engram, crear el propose y continuar con apply sin nuevos checkpoints dentro de este alcance. Sin commits ni push.

## Fuentes

Consigna convertida docs/consigna/consigna-taller-mecanico.md: Ejercicio 5, RN-03 a RN-07, endpoints de usuarios/eventos, C-06 a C-09; CHANGES.md CH-06; KB 03, 05, 07, 08, 09 (DA-08,13,15,16,17,18,22,25 y SU-11); AGENTS.md; specs vigentes y docs/evidencias/explore-CH-05.md. No surgió duda de símbolos en estos contratos; ante duda manda el PDF.

## Decisiones confirmadas

| # | Pregunta | Decisión | Por qué |
|---|---|---|---|
| 1 | ¿Alcance? | CH-06 crea requiere_rol, control obligatorio, rutas_protegidas y cinco endpoints de personal/roles/eventos. Reutiliza get_usuario_actual de CH-05. | Mantener dependencias del roadmap. |
| 2 | ¿Roles para autorizar? | Base por petición: revocada_en NULL y vence_en NULL o mayor que ahora. Cualquier rol pedido sirve; ADMIN no es bypass universal. 401 D6 sin sesión y 403 sin rol. | RN-04 e IN-02; JWT sólo informativo. |
| 3 | ¿Cambio obligatorio? | Control una sola vez en rutas_protegidas; salud y /auth fuera. /yo y cambiar-password autentican individualmente. Mantener D7 y precisión iat. | RN-06, C-09 y decisiones CH-05. |
| 4 | ¿Alta de personal? | Cuerpo email,nombre,password_provisoria,rol; Contrasena, extras forbid; rol ADMIN/RECEPCION/MECANICO. Hash previo; un UoW usuario activo con cambio pendiente + asignación otorgada_por actor + un evento Alta de personal. | DA-16/17, sin filas sueltas ni contraseña en respuesta. |
| 5 | ¿Asignar/reasignar? | vence_en opcional/null, con zona y futuro; inválida 422. Duplicado vigente 409. Vencida abierta se cierra antes de insertar nueva, conserva otorgada_por vieja; nueva autoría actor. **[Alumna] D1=B: CLIENTE también rechazado 422 al asignar roles administrativamente.** | DA-18 e índice parcial; CLIENTE sólo auto-registro. Extensión explícita de DA-17, No especificado en la consigna. |
| 6 | ¿Revocar e historial? | DELETE 200 marca revocada_en sin borrar ni cambiar otorgada_por. GET lista simple de todo historial con vigente, orden desde,id ascendente; usuario existente sin roles devuelve []. **[Alumna] D2=A: ninguna asignación abierta (nunca asignada o ya revocada) da 404; vencida abierta se puede cerrar 200.** | DA-25 y semántica de asignación abierta. Ausencia/orden: No especificado en la consigna. |
| 7 | ¿RN-05? | Autorrevo ADMIN 409 y revocar dejando cero vigentes 409. Vencidos/revocados no cuentan. Conservar DA-15/SU-11: paso del tiempo puede dejar cero, no se introduce tarea ni prohibición de vencimientos. | Respeta alcance previamente confirmado. |
| 8 | ¿Dos admins revocándose? | **[Alumna] D3=A:** candado asesor transaccional común para mutaciones ADMIN, relectura fresca después de esperar del actor, objetivo y vigencia. Primero 200, segundo pierde ADMIN y da 403 sin evento; nunca dos éxitos dejando cero. | No especificado en la consigna; concurrencia general no evaluada, esta garantía fue solicitada expresamente. |
| 9 | ¿Eventos? | Actor email de quien opera; textos DA-13 exactos; SISTEMA sólo seed. Un evento por operación exitosa, dentro mismo UoW; cierre técnico de reasignación no duplica evento. No auditar errores, lecturas, login/logout. Eventos orden cuando,id descendente, paginación core. | Historial atómico y sin duplicar CH-05. Orden: No especificado en la consigna. |
| 10 | ¿Respuestas y mensajes? | **[Alumna] D4=A:** alta {id,email,nombre,activo,debe_cambiar_password}; asignar/revocar devuelve asignación {id,usuario_id,rol,desde,vence_en,revocada_en,otorgada_por,vigente}; eventos {id,cuando,actor,accion}. Mensajes exactos en sección siguiente. | No especificado en la consigna; contratos explícitos sin hashes/contraseñas. |
| 11 | ¿Pruebas? | TDD estricto, safety net, dos casos por comportamiento y escenarios feliz/error/borde; PostgreSQL _test real. Carrera con conexiones independientes y coordinación sin sleeps; evidencias RED/GREEN. | Pruebas de permisos y atomicidad observables, sin mocks de base. |
| 12 | ¿HTTP y módulos futuros? | CH-06 posee c07_roles_vigencia.http, c08_autoproteccion.http y c09_cambio_obligatorio.http. C-06 completo/c06_401_403_propio.http pertenece a CH-09. En C09 nuevo MECANICO muestra nueva cookie válida en /auth/yo; no se promete acceso a /eventos ADMIN. | CHANGES y permisos reales. |

## Mensajes aprobados [Alumna] D4 — No especificado en la consigna

- 403 sin rol: No tiene permisos para realizar esta operación
- 403 pendiente: Debe cambiar la contraseña para continuar
- 404 sin asignación abierta: No hay una asignación abierta de ese rol
- 409 duplicada: El usuario ya tiene ese rol vigente
- 409 autorrevocación: No puede revocarse su propio rol ADMIN
- 409 último ADMIN: No puede dejar el sistema sin administradores vigentes
- 409 correo: El correo ya está registrado (CH-05).
- 401 autenticación: Sesión no válida o vencida (D6, CH-05).
- Usuario inexistente: 404 con mensaje propio; redacción menor propuesta Usuario no encontrado.

## Pedidos para el propose

1. Usar CLI para crear autorizacion-usuarios-roles y obtener status/instructions, sin inventar estado.
2. Registrar capacidades de autorización, administración de personal/roles y eventos; extender errores de dominio con 403 sin reemplazar D6.
3. Capturar todas las decisiones confirmadas, especialmente D1=B, D2=A, D3=A y D4=A como [Alumna], No especificado en la consigna.
4. Diseñar candado común dentro UoW y revalidación fresca tras espera: evitar ORM identity map obsoleto y hora tomada antes del bloqueo.
5. Escenarios Dado/Cuando/Entonces con IDs y tasks TDD para feliz, error, borde, rollback y carrera; no archivos .env ni instalaciones.
6. No agregar endpoints de dominio, migraciones, cron ni bypass ADMIN. No commits/push; Amanda los hace.

## Notas CH-07 a CH-10

- CH-07: incluir routers en rutas_protegidas antes de incluir grupo en app; /mis-vehiculos sólo autenticación, sin exigir CLIENTE; sin ficha => lista vacía.
- CH-08: usar requiere_rol con permisos exactos, sin ADMIN implícito; conservar control obligatorio heredado.
- CH-09: completar C-06 con orden propia 200/ajena 403; /mis-ordenes sólo autenticación; detalle con permiso de personal o propiedad.
- CH-10: DA-22 exige mecánico asignado Y MECANICO vigente o ADMIN vigente para terminar; cancelar sin requiere_rol, permiso antes de estado. Reutilizar roles vigentes de base, nunca token.

## Estado

Exploración confirmada. Documentación/propose autorizados; sin código de producción ni tests ejecutados durante explore. Continuación autorizada por Amanda: propose y apply con TDD, sin checkpoints rutinarios adicionales.

