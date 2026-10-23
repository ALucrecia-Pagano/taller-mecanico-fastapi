# Casos de Prueba

El proyecto incluye archivos `.http` en `test/` que demuestran los casos siguientes, **cada uno con la respuesta esperada en un comentario**, y un `test/solo_agregado.sql` para el caso C-14. **Antes de cada archivo se corre `python seed.py`.** (Consigna, pp. 20-21.)

## Casos de prueba mínimos

| Caso | Qué se demuestra | Resultado esperado | Reglas / épica |
|---|---|---|---|
| **C-01** | Un parámetro de ruta que no es entero, con la sesión iniciada | 422, sin ejecutar el handler | Ej. 3 |
| **C-02** | Registro; correo y documento repetidos | 201; 409 con mensaje propio, y el registro rechazado no deja ninguna fila suelta | RN-01, RN-02 |
| **C-03** | La cookie del login | `Set-Cookie` con `HttpOnly`, `SameSite=Lax` y `Max-Age`; el cuerpo sin token; sin cookie o con `Authorization: Bearer`, 401 | Ej. 4 |
| **C-04** | Correo existente con contraseña mala, y correo inexistente | 401 con el mismo cuerpo y un tiempo parecido | RN-09 |
| **C-05** | Seis intentos fallidos seguidos | El sexto, 429 con `Retry-After` y en pocos milisegundos; los cinco fallos están en `intento_acceso` | RN-08 |
| **C-06** | 401 contra 403, y lo propio | Sin rol, 403; el cliente ve su orden (200) y no la ajena (403) | RN-04, RN-17 |
| **C-07** | Revocar un rol con la sesión abierta; vencimientos inválidos | La misma cookie, 403 en la petición siguiente; `/auth/yo` muestra la diferencia; la fila revocada sigue. Un vencimiento en el pasado o sin zona horaria, 422 | RN-04, Ej. 5 |
| **C-08** | Autoprotección | El administrador no se revoca su ADMIN: 409 | RN-05 |
| **C-09** | Cambio obligatorio | Bloqueado (403) salvo `/auth`; después del cambio, la cookie nueva vale y la anterior da 401, sin esperar entre el login y el cambio | RN-06, RN-07 |
| **C-10** | Alta de una orden con dos ítems | 201 con los precios copiados, el total y el historial; con un repuesto inexistente, 409 y la orden no queda creada | RN-10 |
| **C-11** | Terminar la orden 2, que pide más bujías que las que hay | 409; el estado, el stock, los movimientos y el historial quedan exactamente como estaban | RN-13 |
| **C-12** | Reponer y terminar la orden 2 | 200; baja el stock, aparecen los movimientos y la línea de historial; el aviso sale en el registro después de la respuesta | RN-13, RN-14, Ej. 8 |
| **C-13** | Cancelar | El dueño cancela su orden pendiente (200); una orden ajena da 403; una terminada, 409 | RN-11, RN-12 |
| **C-14** | `UPDATE` y `DELETE` sobre las tres tablas de sólo agregado en `psql`; una orden con un estado que no está en el catálogo | Los seis, rechazados por el disparador; el último, por la clave foránea | RN-15, RN-19 |
| **C-15** | Detalle de una orden con 2 y con 4 ítems | La misma cantidad de consultas en la consola | Ej. 8 |
| **C-16** | Búsqueda con `' OR '1'='1`; paginación con filtro; PATCH parcial; PATCH del stock | Lista vacía con total 0; con `q=freno&size=1`, total 1 y pages 1, y `page=2` da 422; `size=500`, 422; sólo cambia lo enviado; 422 | Ej. 3, RN-14 |
| **C-17** | Catálogo de estados; filtrar órdenes por un estado que el contrato no declara | Los cuatro por posición, con TERMINADA y CANCELADA finales; sin sesión, 401; 422 | RN-19 |
| **C-18** | Cambiar el precio de un repuesto y después sólo su descripción | Una línea nueva en `/repuestos/{id}/precios` con el precio anterior y el nuevo; el segundo PATCH no agrega ninguna; la recepción recibe 403 | RN-20 |
| **C-19** | Dar de baja un vehículo sin órdenes y registrarlo con la misma patente para otro cliente | 204 y 201: el índice único parcial sólo cuenta los vigentes; una segunda patente vigente igual, 409 | RN-01, RN-16 |

### Observaciones para armar los casos con el seed

- **C-11 / C-12**: la orden 2 está EN_REPARACION, asignada a `mecanico@example.com`, con 4 bujías y stock 2. C-12 primero repone (≥ 2) y después termina.
- **C-13**: «el dueño» = `cliente@example.com` (Laura) cancelando la orden 1 (PENDIENTE); «orden ajena» = la orden 2 (de Jorge); «una terminada» = la orden 2 después de C-12 (o una creada y terminada en el mismo archivo — se corre `seed.py` antes de cada archivo).
- **C-15**: hace falta una orden con 4 ítems; el seed tiene 4 repuestos, así que se puede crear en el mismo `.http`.
- **C-16**: con el seed, sólo «Pastillas de freno delanteras» contiene «freno» → `total 1`.
- **C-19**: el vehículo sin órdenes es el segundo de Laura (las órdenes 1 y 2 son del primero de Laura y del de Jorge); «otro cliente» = Jorge.

## Varias sesiones a la vez (REST Client)

Con la extensión «REST Client», cada login se nombra con `# @name` y los pedidos de esa sesión llevan `# @no-cookie-jar` y el encabezado `Cookie: {{loginAdmin.response.headers.Set-Cookie}}`. Así un mismo archivo puede tener la sesión del administrador y la de la recepción al mismo tiempo (lo que necesita C-07).

## Ejemplos de la consigna

### `POST /ordenes` — cuerpo
Viajan el id del vehículo y los datos de cada ítem; **no** viajan el precio, el total, el estado ni la fecha:

```json
{
  "vehiculo_id": 2,
  "falla": "Ruido al frenar",
  "items": [
    { "repuesto_id": 2, "cantidad": 1 },
    { "repuesto_id": 4, "cantidad": 3 }
  ]
}
```

### `POST /ordenes` — respuesta 201
Precio copiado de cada repuesto, total calculado y primera línea del historial:

```json
{
  "id": 3,
  "estado": "PENDIENTE",
  "patente": "AC456EF",
  "total": "68000.00",
  "creada_en": "2026-10-23T02:18:54.332849Z",
  "mecanico_id": null,
  "falla": "Ruido al frenar",
  "cliente": "Laura Cliente",
  "items": [
    { "repuesto_id": 2, "codigo": "FRE-010", "descripcion": "Pastillas de freno delanteras",
      "cantidad": 1, "precio_unitario": "32000.00", "subtotal": "32000.00" },
    { "repuesto_id": 4, "codigo": "ACE-530", "descripcion": "Aceite 5W30 por litro",
      "cantidad": 3, "precio_unitario": "12000.00", "subtotal": "36000.00" }
  ],
  "historial": [
    { "desde_estado": null, "hasta_estado": "PENDIENTE", "usuario_id": 3,
      "cuando": "2026-10-23T02:18:54.366899Z" }
  ]
}
```

### `POST /auth/login` — respuesta 200
El token no viene en el cuerpo: viaja en el encabezado `Set-Cookie`.

```json
{ "mensaje": "Sesión iniciada", "debe_cambiar_password": false, "expira_en_segundos": 1800 }
```

### `GET /repuestos?size=2` — respuesta 200
Con `page=3` respondería 422: «La página 3 no existe: hay 2».

```json
{
  "items": [
    { "id": 1, "codigo": "FIL-001", "descripcion": "Filtro de aceite", "precio": "8500.00", "stock": 10 },
    { "id": 2, "codigo": "FRE-010", "descripcion": "Pastillas de freno delanteras", "precio": "32000.00", "stock": 4 }
  ],
  "total": 4,
  "page": 1,
  "size": 2,
  "pages": 2
}
```
