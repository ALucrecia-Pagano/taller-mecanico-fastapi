"""disparador solo agregado

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-28 16:51:47.495785

Escrita a mano: la comparación automática no ve funciones ni disparadores (DD-10).

Rechaza todo UPDATE y DELETE sobre historial_estado_orden, movimiento_stock e
historial_precio_repuesto, venga de donde venga (RN-15, Ejercicio 7).
- Es de fila (BEFORE ... FOR EACH ROW), para que el TRUNCATE de seed.py pase (DA-31).
  Costo: un UPDATE o DELETE que no alcanza filas no da error.
- ERRCODE restrict_violation (23001, clase 23): la aplicación lo recibe como IntegrityError y la
  traducción de CH-02 lo convierte en un 409 propio, nunca en un 500 con texto de la base (RN-18).

Leída antes de aplicarla: 2026-10-28, por Amanda Pagano. Revisado:
- down_revision 0001.
- La función rechazar_cambio_solo_agregado() con ERRCODE restrict_violation y su mensaje.
- Los tres disparadores BEFORE UPDATE OR DELETE FOR EACH ROW sobre historial_estado_orden,
  movimiento_stock e historial_precio_repuesto, armados en un for sobre la tupla fija TABLAS.
- El downgrade borra los disparadores y después la función.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# El único dato interpolado en el SQL es el nombre de tabla de esta tupla.
TABLAS = ("historial_estado_orden", "movimiento_stock", "historial_precio_repuesto")


def upgrade() -> None:
    """Una función y un disparador por tabla."""
    op.execute(
        """
        CREATE FUNCTION rechazar_cambio_solo_agregado() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'La tabla % es de sólo agregado: no se permite %', TG_TABLE_NAME, TG_OP
                USING ERRCODE = 'restrict_violation';
        END;
        $$
        """
    )
    for tabla in TABLAS:
        op.execute(
            f"""
            CREATE TRIGGER tg_{tabla}_solo_agregado
            BEFORE UPDATE OR DELETE ON {tabla}
            FOR EACH ROW EXECUTE FUNCTION rechazar_cambio_solo_agregado()
            """
        )


def downgrade() -> None:
    """Sin IF EXISTS: si falta un disparador, el esquema no es el que esta migración cree."""
    for tabla in TABLAS:
        op.execute(f"DROP TRIGGER tg_{tabla}_solo_agregado ON {tabla}")
    op.execute("DROP FUNCTION rechazar_cambio_solo_agregado()")
