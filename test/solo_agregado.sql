-- C-14: sólo agregado (RN-15) y estado por clave foránea al catálogo (RN-19).
--
-- Correr DESPUÉS de `python seed.py`, sobre la base de la aplicación:
--     psql -d taller_mecanico -f test/solo_agregado.sql
-- La captura de esta salida es la evidencia de C-14 y se hace en CH-04, después del seed.
--
-- El disparador es de fila: un UPDATE o DELETE que no encuentra filas no da error y no probaría
-- nada. Por eso el archivo primero verifica que hay filas, y cada sentencia apunta a una fila
-- existente (la de menor id) en lugar de un id fijo.

-- Si falta alguna fila, psql se detiene acá y no ejecuta ninguna de las siete sentencias.
-- Esperado sin seed: ERROR:  Corré python seed.py primero
\set ON_ERROR_STOP on
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM historial_estado_orden)
       OR NOT EXISTS (SELECT 1 FROM movimiento_stock)
       OR NOT EXISTS (SELECT 1 FROM historial_precio_repuesto)
       OR NOT EXISTS (SELECT 1 FROM vehiculo) THEN
        RAISE EXCEPTION 'Corré python seed.py primero';
    END IF;
END
$$;
-- A partir de acá cada sentencia falla por separado: psql sigue para mostrar los siete errores.
\set ON_ERROR_STOP off

-- 1. Esperado: ERROR:  La tabla historial_estado_orden es de sólo agregado: no se permite UPDATE
UPDATE historial_estado_orden SET cuando = cuando
 WHERE id = (SELECT min(id) FROM historial_estado_orden);

-- 2. Esperado: ERROR:  La tabla historial_estado_orden es de sólo agregado: no se permite DELETE
DELETE FROM historial_estado_orden
 WHERE id = (SELECT min(id) FROM historial_estado_orden);

-- 3. Esperado: ERROR:  La tabla movimiento_stock es de sólo agregado: no se permite UPDATE
UPDATE movimiento_stock SET cantidad = 99
 WHERE id = (SELECT min(id) FROM movimiento_stock);

-- 4. Esperado: ERROR:  La tabla movimiento_stock es de sólo agregado: no se permite DELETE
DELETE FROM movimiento_stock
 WHERE id = (SELECT min(id) FROM movimiento_stock);

-- 5. Esperado: ERROR:  La tabla historial_precio_repuesto es de sólo agregado: no se permite UPDATE
UPDATE historial_precio_repuesto SET precio_nuevo = 1
 WHERE id = (SELECT min(id) FROM historial_precio_repuesto);

-- 6. Esperado: ERROR:  La tabla historial_precio_repuesto es de sólo agregado: no se permite DELETE
DELETE FROM historial_precio_repuesto
 WHERE id = (SELECT min(id) FROM historial_precio_repuesto);

-- 7. Una orden con un estado que no está en el catálogo: la rechaza la clave foránea, no un CHECK.
-- Esperado: ERROR:  inserción o actualización en la tabla «orden_trabajo» viola la llave foránea
--           «fk_orden_trabajo_estado_estado_orden»
-- (el texto depende del idioma del servidor, lc_messages; el nombre de la restricción, no)
INSERT INTO orden_trabajo (vehiculo_id, estado, falla, total)
VALUES ((SELECT min(id) FROM vehiculo), 'INEXISTENTE', 'Prueba de C-14', 0);
