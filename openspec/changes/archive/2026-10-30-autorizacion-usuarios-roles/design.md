# Design

## Context

Ver proposal.md para la motivación. CH-05 ya aporta ContextoAutenticado, get_usuario_actual, UsuarioRepository.roles_vigentes, AuthService, UsuariosUnitOfWork y un router /auth. main.py registra sólo rutas_abiertas. El índice uq_asignacion_rol_abierta controla filas no revocadas aunque estén vencidas; no cambia el esquema.

Fuentes contractuales: docs/evidencias/explore-CH-06.md (12 decisiones confirmadas), DA-08/13/15/16/17/18/22/25, SU-11 y specs actuales. D1=B y D3=A son decisiones nuevas [Alumna], No especificado en la consigna. El permiso expreso de Amanda cubre captura, propose y apply con TDD; no autoriza commits/push, instalaciones ni .env.

## Goals / Non-Goals

**Goals:** dependencias reutilizables con errores precisos, permisos actuales, mutaciones auditadas atómicas y seguridad de revocación ADMIN ante solicitudes cruzadas.

**Non-Goals:** migraciones, tablas/columnas nuevas, tareas por expiración, JWT blacklist, módulos de clientes/repuestos/órdenes, bypass implícito ADMIN y C-06 completo. Conservar CH-05 D6/D7.

## Decisions

### 1. Composición de rutas y autorización

Mantener router /auth abierto. Exportar otros routers desde usuarios/router.py para /usuarios y /eventos, con route_class=RutaQueTraduceErrores. main.py arma ambos grupos completos antes de app.include_router. rutas_protegidas declara Dependencies del control obligatorio exactamente una vez; requiere_rol(*roles) depende de UsuarioActualDep y consulta roles vigentes en repositorio por petición. La caché de dependencias sólo comparte contexto dentro de esa petición, nunca permisos entre solicitudes.

No se monta autorización ADMIN global al grupo, pues módulos futuros tienen otros permisos o sólo identidad. Se aplica requiere_rol(ADMIN) a cinco rutas CH-06. Lo propio seguirá sin require CLIENTE. ADMIN tampoco autoriza iniciar órdenes que exigen MECANICO.

Alternativas: checks por handler duplican control; grupo global bloquearía /auth; lectura de JWT viola RN-04.

### 2. Errores y schemas

Agregar error de dominio de permiso mapeado a 403, traducido por RutaQueTraduceErrores incluso desde dependencias. Preservar 401 D6 y demás códigos. Entradas Pydantic extra=forbid; reusable tipo de rol de personal (ADMIN, RECEPCION, MECANICO) para ambas entradas; el enum Rol de tabla conserva CLIENTE para auto-registro/historial y DELETE puede usar enum general.

Contrasena se reutiliza para password_provisoria: límite 72 bytes, vacío/NUL rechazados; sin validaciones de complejidad nuevas. vence_en datetime consciente de zona; omitido/null válido, presente estrictamente futuro => si no 422. Comparar contra reloj actual de aplicación con precisión, no quitar zona ni truncar.

Respuestas exactas:
- Alta: id,email,nombre,activo,debe_cambiar_password.
- Asignación POST/DELETE y GET historial: id,usuario_id,rol,desde,vence_en,revocada_en,otorgada_por,vigente.
- GET historial lista simple, orden desde asc,id asc; usuario existente vacío => [].
- Eventos: items con id,cuando,actor,accion; envoltorio core.
Nunca serializar tablas completas ni hashes/password/token. Mensajes: tabla del explore; Usuario no encontrado para id ausente como elección menor de redacción.

Alternativas: response_model tabla filtra mal secretos; datetime ingenuo ambiguo; CLIENTE administrativo contradice D1=B.

### 3. Servicios, repositorios y atomicidad

Ampliar UsuariosUnitOfWork y repositorios existentes con lecturas explícitas y métodos semánticos para asignaciones/eventos. El router/dependencia construye UoW; servicio recibe y abre; repositorios sólo flush. No cargar Usuario.roles perezosamente: seleccionar asignaciones o proyecciones directamente y precargar sólo relaciones efectivamente usadas.

Alta calcula hash antes del UoW, luego usuario, asignación inicial otorgada_por actor y un evento. Email duplicado lo garantiza uq_usuario_email sin preconsulta de unicidad y se traduce mensaje existente.

Asignación: verificar usuario 404; encontrar fila abierta. Si vigente, 409 propio; si vencida, escribir revocada_en y flush ANTES de insertar para liberar índice parcial, conservando otorgada_por vieja. Insertar nueva y evento Asignación. El índice sigue última garantía contra asignación duplicada simultánea y se mapea a El usuario ya tiene ese rol vigente.

Revocar: usuario ausente404; fila abierta ausente404 D2; vencida abierta sí cerrable200. Escribir fecha y evento sin borrar ni cambiar autoría. Fallo de cualquier escritura/evento o commit revierte todo. Sólo intento_acceso mantiene sesión independiente CH-05.

Alternativas: transacciones por fila dejan datos sueltos; actualizar rol previo destruye historia; insertar antes de cerrar viola índice.

### 4. RN-05 y candado [Alumna D3=A]

Usar pg_advisory_xact_lock con clave entera fija documentada en módulo usuarios (un namespace estable propio de RN-05; no derivado de hash Python ni id objetivo). SQL parametrizado; candado común para todas las operaciones que agregan/reasignan/revocan ADMIN, incluido alta de personal ADMIN. Se toma dentro del mismo UoW de operación, antes de lecturas decisorias/escrituras, y permanece hasta terminar esa transacción. No liberar manualmente ni usar lock de sesión.

Después de adquirirlo obtener tiempo fresco y consultar ADMIN vigente del actor desde base; si ya perdió rol, 403 estándar sin escrituras/evento. No confiar en token ni usuario/colección almacenados antes de espera. Consultas de columnas o populate_existing/refresh explícito previenen identity map obsoleto; aislamiento existente READ COMMITTED permite sentencias nuevas ver commit previo. Leer objetivo/fila abierta otra vez y contar ADMIN vigentes de asignacion_rol excluyendo la fila que se intenta cerrar. Contar asignaciones vigentes según definición DA, no agregar una nueva política por activo del usuario no discutida.

Autorrevo ADMIN =>409 aunque haya otros. Una revocación que dejaría cero =>409. El chequeo de último ADMIN se cubre por seam de servicio con caso preparado, porque una petición legítima ordinaria de otro ADMIN vigente ya constituye un respaldo; no fabricar bypass en API para alcanzar ese branch.

Carrera A->B y B->A: primero confirma200, segundo tras esperar relee su rol perdido y da403; queda uno y un evento. No aceptar 409 como resultado de esa carrera si el actor ya perdió permisos. Fecha de expiración puede cambiar durante espera: usar ahora posterior al candado. DA15/SU11 permiten cero ADMIN por vencimiento; no prometer protección por tiempo/cron.

Alternativas: candado por objetivo permite write skew; count sin bloqueo falla; SELECT FOR UPDATE conjunto exige protocolo más complejo; SERIALIZABLE añade retry no necesario.

### 5. Auditoría y paginación

Reusar eventos CH-05. Actor es email autenticado, no id ni destinatario. Cada operación agrega un texto DA13 dentro mismo UoW; alta tiene sólo Alta de personal y reasignación sólo Asignación. No logear fallos ni lectura/login/logout en evento_seguridad. No imponer nuevo trigger de sólo agregado para esta tabla.

GET /eventos usa paginación core, count y página con mismos filtros (sin filtros nuevos), cuando DESC,id DESC para reproducibilidad; vacío => una página; 422 página inexistente. Lecturas pueden usar bloque UoW consecutivo como patrón existente; no abrir bloques anidados.

Alternativa: auditoría postcommit pierde atomicidad; orden sólo por fecha empata.

### 6. Pruebas y demostraciones

Safety net antes de tocar archivos y detener ante fallo preexistente. Un corte vertical por comportamiento: RED ejecutado y guardado, GREEN mínimo, triangulación mínimo dos casos, refactor con verde; evidencias por task. Tests integrados httpx/PostgreSQL _test real en test/pytest, sin mocks DB. Pruebas de atomicidad observan resultados y pueden consultar con otra sesión por ausencia de endpoints de filas/eventos parciales; no reemplazar comportamiento público por tautologías.

AU1-12, PE1-7, RO1-7, RV1-4, HI1-2, AD1-4, CO1-4, EV1-9 y E403a-c enlazan contratos y tests. Preparar tiempo controlado sin sleeps para bordes; carrera coordina dos conexiones con barrera/eventos y confirma espera real, sin timings frágiles. Rollback libera candado y permite solicitud siguiente. Pruebas de composición verifican control único heredado y traducción de rutas/subclases.

HTTP: c07 con dos cookies nombradas explícitas y # @no-cookie-jar; admin1 revoca ADMIN de admin2, cookie2 antes/tras, /yo divergente e historial desde admin1, fechas inválidas. c08 autorrevo409. c09 nuevo@example.com pending MECANICO: protegido403, /yo200, mismo password422, cambio correcto, nueva /yo200 y anterior401 sin espera. Un test pytest con ADMIN provisional demuestra acceso protegido200 después de cambio; no otorgar ADMIN al seed nuevo para acomodar ejemplo. C06 completo se documenta para CH09 sin crear orden/ruta ficticia de producción.

## Risks / Trade-offs

- [Decisiones DA no actualizadas todavía en KB09] → evidencia explore y deltas las identifican explícitamente; D1 extiende DA17 sin cambiar enum de tabla.
- [Espera bajo candado] → ámbito sólo mutaciones ADMIN y hash fuera de bloque; no instalación ni nuevo esquema.
- [Actor autorizado antes de espera queda obsoleto] → releer columnas de base después del lock y tiempo fresco.
- [Expiración deja cero] → excepción SU11 explícita, no se oculta ni introduce nueva regla.
- [Nuevo MECANICO sigue403 en endpoint ADMIN tras cambio] → C09 usa /yo y test ADMIN prueba desbloqueo real.

## Migration Plan

Sin migración de datos ni esquema. Ejecutar safety net, implementar por cortes TDD y correr suite completa sobre _test; validar OpenSpec estricto. Despliegue local conserva Settings y lifespan; rollback de código no requiere downgrade. No correr seed en desarrollo desde agente ni modificar .env. README sólo añade uso de HTTP sin credenciales reales. Archivar y marcar CHANGES únicamente si Amanda lo solicita o autoriza, no como efecto del propose.

