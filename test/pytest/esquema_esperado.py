"""El esquema que exige la consigna (pp. 5-6) y los nombres de restricción del design (D2).

Lo usan los tests de la metadata (sin base) y los de la base migrada: los dos comparan contra lo mismo.
"""

# La misma lista que importa migrations/env.py; test_modelos verifica que coinciden.
MODULOS_DE_MODELOS = (
    "app.modules.usuarios.models",
    "app.modules.clientes.models",
    "app.modules.repuestos.models",
    "app.modules.ordenes.models",
)

COLUMNAS = {
    "usuario": {"id", "email", "nombre", "password_hash", "activo", "debe_cambiar_password", "password_cambiada_en"},
    "asignacion_rol": {"id", "usuario_id", "rol", "desde", "vence_en", "revocada_en", "otorgada_por"},
    "intento_acceso": {"id", "cuando", "email", "ip", "exito"},
    "evento_seguridad": {"id", "cuando", "actor", "accion"},
    "cliente": {"id", "usuario_id", "nombre", "documento", "telefono"},
    "vehiculo": {"id", "cliente_id", "patente", "marca", "modelo", "anio", "borrado_en"},
    "repuesto": {"id", "codigo", "descripcion", "precio", "stock", "borrado_en"},
    "estado_orden": {"codigo", "descripcion", "posicion", "es_final"},
    "orden_trabajo": {"id", "vehiculo_id", "mecanico_id", "estado", "falla", "creada_en", "total"},
    "item_orden": {"id", "orden_id", "repuesto_id", "cantidad", "precio_unitario"},
    "historial_estado_orden": {"id", "orden_id", "desde_estado", "hasta_estado", "usuario_id", "cuando"},
    "movimiento_stock": {"id", "repuesto_id", "orden_id", "usuario_id", "cantidad", "motivo", "cuando"},
    "historial_precio_repuesto": {"id", "repuesto_id", "usuario_id", "precio_anterior", "precio_nuevo", "cuando"},
}

# Las marcadas «(nulo)» en la consigna; todas las demás son NOT NULL (DA-20).
NULABLES = {
    ("usuario", "password_cambiada_en"),
    ("asignacion_rol", "vence_en"),
    ("asignacion_rol", "revocada_en"),
    ("asignacion_rol", "otorgada_por"),
    ("cliente", "usuario_id"),
    ("vehiculo", "borrado_en"),
    ("repuesto", "borrado_en"),
    ("orden_trabajo", "mecanico_id"),
    ("historial_estado_orden", "desde_estado"),
    ("movimiento_stock", "orden_id"),
}

DINERO = {
    ("repuesto", "precio"): (10, 2),
    ("item_orden", "precio_unitario"): (10, 2),
    ("historial_precio_repuesto", "precio_anterior"): (10, 2),
    ("historial_precio_repuesto", "precio_nuevo"): (10, 2),
    ("orden_trabajo", "total"): (12, 2),
}

FECHAS = {
    ("usuario", "password_cambiada_en"),
    ("asignacion_rol", "desde"),
    ("asignacion_rol", "vence_en"),
    ("asignacion_rol", "revocada_en"),
    ("intento_acceso", "cuando"),
    ("evento_seguridad", "cuando"),
    ("vehiculo", "borrado_en"),
    ("repuesto", "borrado_en"),
    ("orden_trabajo", "creada_en"),
    ("historial_estado_orden", "cuando"),
    ("movimiento_stock", "cuando"),
    ("historial_precio_repuesto", "cuando"),
}

# Fechas que registran «cuándo pasó»: la base pone now() si la aplicación no la envía (7b).
FECHAS_CON_NOW = {
    ("asignacion_rol", "desde"),
    ("intento_acceso", "cuando"),
    ("evento_seguridad", "cuando"),
    ("orden_trabajo", "creada_en"),
    ("historial_estado_orden", "cuando"),
    ("movimiento_stock", "cuando"),
    ("historial_precio_repuesto", "cuando"),
}

PK = {f"pk_{tabla}" for tabla in COLUMNAS}

UNIQUE = {
    "uq_usuario_email": ("usuario", ("email",)),
    "uq_cliente_usuario_id": ("cliente", ("usuario_id",)),
    "uq_cliente_documento": ("cliente", ("documento",)),
    "uq_estado_orden_posicion": ("estado_orden", ("posicion",)),
    "uq_item_orden_orden_id_repuesto_id": ("item_orden", ("orden_id", "repuesto_id")),
}

CHECK = {
    "ck_asignacion_rol_rol": "asignacion_rol",
    "ck_vehiculo_anio": "vehiculo",
    "ck_repuesto_precio_positivo": "repuesto",
    "ck_repuesto_stock_no_negativo": "repuesto",
    "ck_orden_trabajo_total_no_negativo": "orden_trabajo",
    "ck_item_orden_cantidad_positiva": "item_orden",
    "ck_item_orden_precio_unitario_positivo": "item_orden",
    "ck_movimiento_stock_cantidad_distinta_de_cero": "movimiento_stock",
    "ck_historial_precio_repuesto_precio_nuevo_positivo": "historial_precio_repuesto",
    "ck_historial_precio_repuesto_precio_cambia": "historial_precio_repuesto",
}

# nombre -> (tabla, columna, tabla destino, columna destino)
FK = {
    "fk_asignacion_rol_usuario_id_usuario": ("asignacion_rol", "usuario_id", "usuario", "id"),
    "fk_asignacion_rol_otorgada_por_usuario": ("asignacion_rol", "otorgada_por", "usuario", "id"),
    "fk_cliente_usuario_id_usuario": ("cliente", "usuario_id", "usuario", "id"),
    "fk_vehiculo_cliente_id_cliente": ("vehiculo", "cliente_id", "cliente", "id"),
    "fk_orden_trabajo_vehiculo_id_vehiculo": ("orden_trabajo", "vehiculo_id", "vehiculo", "id"),
    "fk_orden_trabajo_mecanico_id_usuario": ("orden_trabajo", "mecanico_id", "usuario", "id"),
    "fk_orden_trabajo_estado_estado_orden": ("orden_trabajo", "estado", "estado_orden", "codigo"),
    "fk_item_orden_orden_id_orden_trabajo": ("item_orden", "orden_id", "orden_trabajo", "id"),
    "fk_item_orden_repuesto_id_repuesto": ("item_orden", "repuesto_id", "repuesto", "id"),
    "fk_historial_estado_orden_orden_id_orden_trabajo": ("historial_estado_orden", "orden_id", "orden_trabajo", "id"),
    "fk_historial_estado_orden_desde_estado_estado_orden": (
        "historial_estado_orden", "desde_estado", "estado_orden", "codigo"),
    "fk_historial_estado_orden_hasta_estado_estado_orden": (
        "historial_estado_orden", "hasta_estado", "estado_orden", "codigo"),
    "fk_historial_estado_orden_usuario_id_usuario": ("historial_estado_orden", "usuario_id", "usuario", "id"),
    "fk_movimiento_stock_repuesto_id_repuesto": ("movimiento_stock", "repuesto_id", "repuesto", "id"),
    "fk_movimiento_stock_orden_id_orden_trabajo": ("movimiento_stock", "orden_id", "orden_trabajo", "id"),
    "fk_movimiento_stock_usuario_id_usuario": ("movimiento_stock", "usuario_id", "usuario", "id"),
    "fk_historial_precio_repuesto_repuesto_id_repuesto": (
        "historial_precio_repuesto", "repuesto_id", "repuesto", "id"),
    "fk_historial_precio_repuesto_usuario_id_usuario": ("historial_precio_repuesto", "usuario_id", "usuario", "id"),
}

# Índices comunes (nombre -> tabla): uno por FK que no encabeza un UNIQUE (D4) y el de intento_acceso.
INDICES = {
    "ix_asignacion_rol_usuario_id": "asignacion_rol",
    "ix_asignacion_rol_otorgada_por": "asignacion_rol",
    "ix_vehiculo_cliente_id": "vehiculo",
    "ix_orden_trabajo_vehiculo_id": "orden_trabajo",
    "ix_orden_trabajo_mecanico_id": "orden_trabajo",
    "ix_orden_trabajo_estado": "orden_trabajo",
    "ix_item_orden_repuesto_id": "item_orden",
    "ix_historial_estado_orden_orden_id": "historial_estado_orden",
    "ix_historial_estado_orden_desde_estado": "historial_estado_orden",
    "ix_historial_estado_orden_hasta_estado": "historial_estado_orden",
    "ix_historial_estado_orden_usuario_id": "historial_estado_orden",
    "ix_movimiento_stock_repuesto_id": "movimiento_stock",
    "ix_movimiento_stock_orden_id": "movimiento_stock",
    "ix_movimiento_stock_usuario_id": "movimiento_stock",
    "ix_historial_precio_repuesto_repuesto_id": "historial_precio_repuesto",
    "ix_historial_precio_repuesto_usuario_id": "historial_precio_repuesto",
    "ix_intento_acceso_email_ip_cuando": "intento_acceso",
}

# Índices únicos parciales: nombre -> (tabla, columnas, condición)
PARCIALES = {
    "uq_asignacion_rol_abierta": ("asignacion_rol", ("usuario_id", "rol"), "revocada_en IS NULL"),
    "uq_vehiculo_patente_vigente": ("vehiculo", ("patente",), "borrado_en IS NULL"),
    "uq_repuesto_codigo_vigente": ("repuesto", ("codigo",), "borrado_en IS NULL"),
}
