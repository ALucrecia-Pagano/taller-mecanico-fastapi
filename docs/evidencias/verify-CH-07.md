# Verificación manual

**Fecha:** 2026-10-30  
**Verificó:** Amanda Pagano  
**Trabajado con:** Copilot

## Comandos

Antes de cada archivo se ejecutó `python seed.py` contra `taller_mecanico`.
Luego se ejecutaron las peticiones desde REST Client:

- `test/c01_parametro_invalido.http`
- `test/c19_baja_vehiculo.http`

La contraseña se escribió únicamente en el editor mediante la variable
`{{$processEnv TALLER_PASSWORD_PRUEBA}}`; no se guardó en el repositorio.

## Resultados

| Archivo | Resultados reales, en orden | Resultado |
|---|---|---|
| `test/c01_parametro_invalido.http` | Login `200`; `GET /clientes/no-entero` `422` | Coincide con lo esperado |
| `test/c19_baja_vehiculo.http` | Login `200`; `DELETE /vehiculos/2` `204`; alta de patente reutilizada `201`; patente equivalente `409` | Coincide con lo esperado |

Se corrigieron ambos archivos `.http` para usar `{{password_seed}}`, separado del
cuerpo de cada petición, leyendo `{{$processEnv TALLER_PASSWORD_PRUEBA}}`, y para
dejar las respuestas esperadas como comentarios.


# Informe de implementación

## Códigos esperados de los archivos HTTP

| Archivo | Petición, en orden | Código esperado |
|---|---|---:|
| `test/c01_parametro_invalido.http` | `GET /clientes/no-entero` | 422 |
| `test/c19_baja_vehiculo.http` | `DELETE /vehiculos/2` | 204 |
| `test/c19_baja_vehiculo.http` | `POST /clientes/2/vehiculos` | 201 |
| `test/c19_baja_vehiculo.http` | `POST /clientes/1/vehiculos` con patente equivalente | 409 |

## Escenario → test

| Escenario | Test |
|---|---|
| Alta válida de cliente | `test_alta_cliente_normaliza_documento_y_rechaza_repetido` |
| Documento con espacios de borde | `test_alta_cliente_normaliza_documento_y_rechaza_repetido` |
| Documento duplicado | `test_alta_cliente_normaliza_documento_y_rechaza_repetido` |
| Alta de cliente con contrato inválido | `test_contratos_y_parametro_invalido_422` |
| Alta de cliente sin sesión | `test_clientes_rutas_recepcion_sin_sesion_401` |
| Alta de cliente sin rol | `test_clientes_rutas_recepcion_sin_rol_403` |
| Consulta de cliente con vigentes y exclusión de baja | `test_cliente_y_vehiculos_seed_y_mis_vehiculos` |
| Consulta de cliente inexistente | `test_consultas_de_cliente_inexistente_y_baja_de_vehiculo_inexistente_404` |
| Parámetro de cliente inválido | `test_contratos_y_parametro_invalido_422` |
| Consulta de cliente sin permiso | `test_clientes_rutas_recepcion_sin_rol_403` |
| Alta válida de vehículo | `test_alta_vehiculo_normaliza_patente_y_rechaza_equivalente` |
| Cliente inexistente al agregar vehículo | `test_alta_vehiculo_cliente_inexistente_y_anio_invalido_404_422` |
| Patente equivalente normalizada | `test_alta_vehiculo_normaliza_patente_y_rechaza_equivalente` |
| Patente reutilizable tras baja | `test_alta_vehiculo_reutiliza_patente_dada_de_baja` |
| Año o campos inválidos | `test_alta_vehiculo_cliente_inexistente_y_anio_invalido_404_422`, `test_contratos_y_parametro_invalido_422` |
| Alta de vehículo sin permiso | `test_clientes_rutas_recepcion_sin_rol_403` |
| Baja permitida | `test_baja_vehiculo_abierto_409_y_final_204` |
| Baja con orden PENDIENTE o EN_REPARACION | `test_baja_vehiculo_abierto_409_y_final_204` |
| Baja con orden TERMINADA | `test_baja_permitida_con_cada_estado_final[TERMINADA]` |
| Baja con orden CANCELADA | `test_baja_permitida_con_cada_estado_final[CANCELADA]` |
| Vehículo inexistente o ya dado de baja | `test_consultas_de_cliente_inexistente_y_baja_de_vehiculo_inexistente_404`, `test_baja_vehiculo_abierto_409_y_final_204` |
| Baja de vehículo sin permiso | `test_clientes_rutas_recepcion_sin_rol_403` |
| `/mis-vehiculos` con ficha | `test_cliente_y_vehiculos_seed_y_mis_vehiculos` |
| `/mis-vehiculos` sin ficha | `test_mis_vehiculos_usuario_sin_ficha_lista_vacia` |
| `/mis-vehiculos` con cambio obligatorio | `test_cambio_obligatorio_bloquea_todas_las_rutas_de_clientes` |
| `/mis-vehiculos` sin sesión | `test_clientes_rutas_recepcion_sin_sesion_401` |
| Detalle sin N+1 | `test_detalle_cliente_usa_carga_anticipada_sin_n_mas_uno` |
| Relaciones no cargadas | **SIN TEST** |
| Contraseñas HTTP fuera del repositorio | `test_archivos_http_ch07_contienen_password_de_entorno` |

## Desvíos

Desvío de cobertura: el escenario de defensa ante una entidad devuelta sin la relación
precargada queda marcado como **SIN TEST**; la implementación evita lazy loading mediante
`lazy="raise"` y usa `selectinload`, pero no se agregó un test artificial que fabrique esa
entidad incompleta. El resto de los escenarios tiene cobertura explícita.

## Archivos

- `app/modules/clientes/models.py`
- `app/modules/clientes/repository.py`
- `app/modules/clientes/schemas.py`
- `app/modules/clientes/service.py`
- `app/modules/clientes/unit_of_work.py`
- `app/modules/clientes/router.py`
- `main.py`
- `test/pytest/test_clientes.py`
- `test/c01_parametro_invalido.http`
- `test/c19_baja_vehiculo.http`
- `README.md`
- `docs/evidencias/CH-07-tdd-rojo.txt`
- `docs/evidencias/CH-07-tdd-verde.txt`
- `docs/evidencias/pytest-CH-07.txt`
