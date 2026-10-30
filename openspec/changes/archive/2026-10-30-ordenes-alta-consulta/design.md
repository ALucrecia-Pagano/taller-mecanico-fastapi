# Design

## Context

Ver proposal y explore-CH-09. CH-07/08 aportan repositorios con baja lógica, un UoW que traduce IntegrityError y una sesión por petición. Los cuatro modelos de órdenes y sus constraints ya existen, con lazy="raise". La tabla POST sólo lista 201/409/422; se verificó nuevamente antes de planificar. CH-08 tiene 28/28 tareas completas.

## Goals / Non-Goals

**Goals:** Alta transaccional, DTOs separados, cinco operaciones protegidas, consultas históricas y evidencia reproducible. Cubrir E01–E22 con seam HTTP para contratos/permisos y seam servicio/repository con PostgreSQL real para atomicidad/costo SQL que HTTP solo no demuestra.

**Non-Goals:** Transiciones CH-10, reservas, locking nuevo, migraciones, instalar paquetes, editar seed o .env, modificar datos de desarrollo y archivar. Tests y fallos controlados sólo sobre taller_mecanico_test, con limpieza final.

## Decisions

1. EntradaOrden/EntradaItem con extra forbid, validator repetidos y lista mínima1; enteros Pydantic habituales, falla sin normalización ni máximos nuevos [Agente, No especificado en la consigna]. Alternativa: aceptar campos calculados o sumar duplicados, descartada RN-10/DA-19.
2. Resumen con id/estado/patente/total/creada_en/mecanico_id/falla/cliente; detalle agrega items e historial según ejemplo. Decimal con serializador de dos decimales. Orden estable de ítems/id y historial/(cuando,id) [Agente, No especificado en la consigna].
3. OrdenesUnitOfWork compone órdenes, ítems (sólo add), historial (sólo add), catálogo sólo lectura (sin BaseRepository), VehiculoRepository y RepuestoRepository existentes, y lectura de roles de UsuarioRepository, todos misma sesión. Dependencia async construye UoW, servicio abre un bloque. Catálogo/vehículo/repuestos se verifican antes de alta; referencias faltantes o bajas409.
4. OrdenTrabajoRepository declara joinedload(vehiculo→cliente), selectinload(items) con joinedload(repuesto), selectinload(historial). Tres SELECT de dominio para detalle existente [Agente, No especificado en la consigna]; sin filtrar bajas históricas. Resumen carga sólo relaciones escalares. Count y filas comparten filtro por estado/usuario, sin colecciones ni duplicaciones.
5. Alta copia precios Decimal, calcula suma y rechaza >9999999999.99 con409 [Agente, No especificado en la consigna]; no stock. DTO dentro UoW con relaciones explícitas, respuesta tras confirmación. Lectura de ids en lote desde repositorio de órdenes usando la sesión y filtro de baja, sin modificar CH-08 [Agente, No especificado en la consigna].
6. GET detalle resuelve existencia antes de permiso, roles actuales o cliente.usuario_id; mis-ordenes sólo propietario, aunque tenga rol personal. Históricos visibles aun con bajas [Agente para interpretación histórica, No especificado en la consigna]. Sin CLIENTE obligatorio.
7. Mensajes propios aprobados en explore; constraints conocidas del alta se mapean a «No se pudo crear la orden». Para una constraint desconocida se conserva el genérico transversal «La operación choca con datos existentes» de la spec errores-de-dominio: precisión del fallback propuesto, sin cambiar core ni debilitar RN-18. Catálogo parcial sin PENDIENTE409 y GET vacío[] [Agente, No especificado en la consigna].
8. Mantener semántica de concurrencia existente: precios leídos dentro de la transacción; no bloquear bajas/precios cruzados [Agente, No especificado en la consigna]. No se promete snapshot global ni aislamiento adicional.
9. TDD por tarea vertical: test mínimo ausente→RED ejecutado→código mínimo→GREEN ejecutado→triangulación y refactor. Baseline completo previo. Logs append con encabezados y comandos; no borrar corridas. HTTP .http con password desde proceso y logins propios. C15 captura SQL real en prueba de sesiones independientes, sin parámetros sensibles; identifica consultas de auth y dominio. Carpeta DA-30; nombre C-15-consultas.txt [Agente, No especificado en la consigna].

## Risks / Trade-offs

- Identity map puede ocultar N+1 → sesiones HTTP nuevas por detalle y evento SQL acotado; contar y guardar sentencias reales, no tiempos.
- Fallo luego del flush o commit → pruebas PostgreSQL reales con actor FK inválido inmediato/diferido y segunda sesión que comprueba ausencia; ninguna BD mockeada.
- Cantidad grande del tipo entero → total máximo validado antes de persistir; cantidad fuera de INTEGER (máximo2147483647) se rechaza422 por contrato. IDs fuera de INTEGER se resuelven como inexistentes antes del bind (alta409/detalle404), preservando los códigos de la consigna [Agente, No especificado en la consigna]. No se captura DataError genéricamente.
- Fixtures sembradas y suite histórica → guarda _test y cleanup del arnés más consulta final de todas tablas de dominio; sin datos residuales.

## Migration Plan

No cambia esquema. Despliegue habitual de código; revertir los archivos CH-09 revierte rutas. La reversión no modifica órdenes históricas. No se ejecuta ninguna operación de git.
