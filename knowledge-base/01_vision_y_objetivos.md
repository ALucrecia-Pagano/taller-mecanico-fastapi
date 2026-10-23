# Visión y Objetivos

> Fuente única: `docs/consigna/consigna-taller-mecanico.pdf` (TP integrador, Programación III, Unidades 1 a 6 «Del objeto a la transacción»). Lo que no figura en el PDF se marca **No especificado en la consigna** y se registra en [10_preguntas_abiertas.md](10_preguntas_abiertas.md).

## Propósito del sistema

Una API asincrónica para el trabajo diario de un taller mecánico: clientes, vehículos, órdenes de trabajo, stock de repuestos y acceso del personal.

Contexto (consigna, p. 2): la recepción da de alta a los clientes y a sus vehículos, y abre una orden de trabajo por cada ingreso, con la falla que describe el cliente y los repuestos que se van a usar. Un mecánico toma la orden, la repara y la da por terminada: en ese momento se descuenta del stock cada repuesto usado. El administrador mantiene el catálogo de repuestos, repone el stock y administra al personal y sus roles. Los clientes se registran solos en la web y consultan el estado de sus vehículos.

## Objetivos académicos (lo que el proyecto debe demostrar)

Textual de la consigna (p. 1):

1. Construir una API asincrónica en capas —Router → Service → UoW → Repository → Model— donde cada capa sabe lo suyo y nada más.
2. Traducir un modelo con asociación, composición, uno a uno y una tabla de catálogo a un esquema relacional versionado con Alembic, incluida una migración que hay que escribir a mano.
3. Autenticar con contraseñas guardadas con bcrypt y un token en una cookie `HttpOnly`, sin frenar el servidor y sin revelar qué cuentas existen.
4. Autorizar consultando los roles en la base en cada petición, con vigencia, y distinguir siempre entre 401 y 403.
5. Agrupar en una sola transacción las escrituras de una operación de negocio, de modo que un fallo en el medio no deje datos a medias.
6. Delegar en la base las garantías que la base puede dar: unicidad, claves foráneas, comprobaciones y el sólo agregado.

## Objetivos por actor

| Actor | Objetivo principal | Objetivos secundarios |
|---|---|---|
| Recepción (`RECEPCION`) | Dar de alta clientes y vehículos y abrir órdenes de trabajo | Cancelar órdenes; dar de baja vehículos; consultar repuestos y órdenes |
| Mecánico (`MECANICO`) | Tomar (iniciar) una orden y terminarla | Consultar repuestos y órdenes |
| Administrador (`ADMIN`) | Mantener el catálogo de repuestos y el stock; administrar personal y roles | Todo lo de recepción; terminar órdenes; ver eventos de seguridad, movimientos e historial de precios |
| Cliente (`CLIENTE`) | Registrarse solo y consultar el estado de sus vehículos y órdenes | Cancelar su propia orden pendiente |

## Alcance (lo que el sistema SÍ hace)

- Salud: `GET /health/live` y `GET /health/ready`.
- Autenticación con cookie `HttpOnly`: registro, login con límite de intentos, logout, `GET /auth/yo`, cambio de contraseña (incluido el obligatorio).
- Administración de personal y roles con vigencia (asignar con vencimiento opcional, revocar sin borrar).
- Clientes y vehículos (con borrado lógico del vehículo).
- Repuestos: catálogo con borrado lógico, búsqueda paginada, reposición de stock, movimientos e historial de precios.
- Órdenes de trabajo: alta con ítems, transiciones de estado, historial, terminación con descuento de stock y aviso simulado en segundo plano.
- Catálogo de estados de orden de sólo lectura.
- Lo propio del cliente: `/mis-vehiculos` y `/mis-ordenes`.
- Integridad delegada en la base: UNIQUE, índices únicos parciales, CHECK, claves foráneas y disparador de sólo agregado.

## Fuera de alcance

Textual de la consigna («Qué queda afuera», p. 2):

- **Concurrencia (capítulo 7)**: no se evalúa. La actualización perdida de stock entre dos terminaciones simultáneas se acepta; el bloqueo que la evita es tema de la próxima clase.
- **Colas de tareas con Redis (capítulo 8)**: el aviso al cliente se resuelve con `BackgroundTasks` en el mismo proceso; si el proceso se reinicia el aviso se pierde y no hay reintento. Se acepta porque el aviso es simulado.
- **Segundo mecanismo de sólo agregado** (rol de base sin permisos de modificación, sección 6.9): no se pide; el TP usa un solo rol de base.
- Frontend: No especificado en la consigna (la consigna sólo pide la API).

## Métricas de éxito

- El proyecto levanta, crea su esquema con `alembic upgrade head` sobre una base vacía y no contiene credenciales reales en el repositorio (si no, «no se corrige hasta que se subsane»).
- Los casos de prueba C-01 a C-19 dan el resultado esperado ([11_casos_de_prueba.md](11_casos_de_prueba.md)).
- Criterios y pesos de evaluación: [12_criterios_de_evaluacion.md](12_criterios_de_evaluacion.md).
