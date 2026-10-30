# Design

## Context

CH-09 ya concentra la lectura detallada y la composición del UoW de órdenes. CH-08 expone
`RepuestoRepository.ajustar_stock`, que actualiza stock y agrega el movimiento en la misma
sesión. CH-10 debe sumar sólo las transiciones y no duplicar modelos, serialización ni
lógica de stock.

## Goals / Non-Goals

**Goals:**

- Mantener autorización por roles vigentes y pertenencia al vehículo.
- Hacer cada transición una operación de un solo UoW.
- Usar una actualización condicional de estado como guardia de carrera.
- Reutilizar el ajuste de stock incluyendo repuestos dados de baja.
- Agendar el aviso únicamente después de la salida exitosa del UoW.

**Non-Goals:**

- Migraciones, cambios de catálogo, seed o nuevos endpoints de historial.
- Bloqueo general de concurrencia entre órdenes distintas que consumen el mismo repuesto.
- Cola durable, reintentos o persistencia del aviso.

## Decisions

1. **Guardia de transición antes de las escrituras dependientes.** El servicio valida existencia
   y autorización, abre el UoW y ejecuta `UPDATE ... WHERE id AND estado esperado`. Si el
   resultado es cero, lanza conflicto antes de stock/historial. Esto evita que dos
   terminaciones de la misma orden descuenten dos veces.
2. **Autorización específica por operación.** `iniciar` usa MECANICO; `terminar` verifica
   mecánico asignado + MECANICO vigente o ADMIN vigente; `cancelar` resuelve rol/propiedad
   en servicio porque no lleva `requiere_rol`.
3. **Stock por la única operación existente.** `terminar` llama el método de CH-08 con
   `incluir_baja=True`, cantidad negativa, motivo y orden. El punto único conserva la
   comprobación atómica y el movimiento append-only.
4. **Respuesta y aviso separados del commit.** El detalle se construye dentro del UoW con
   relaciones precargadas; el router agenda `BackgroundTasks` sólo tras el retorno exitoso
   del servicio. El aviso registra ids, no datos personales.
5. **Errores propios.** Las transiciones inválidas, la falta de stock y el permiso específico
   usan mensajes fijados en la exploración; nunca se expone texto de PostgreSQL.

## Risks / Trade-offs

- [Risk] El UPDATE condicional y el consumo de stock no bloquean carreras entre órdenes
  distintas. → Mitigación: queda explícitamente fuera de alcance según la consigna.
- [Risk] Una tarea se pierde al reiniciar el proceso o falla sin reintento. → Mitigación:
  documentar la limitación y mantener el aviso fuera de la transacción.
- [Risk] El detalle puede necesitar refresco explícito tras el UPDATE. → Mitigación:
  recargar con las precargas existentes antes de serializar.
