"""Datos ficticios y consultas de evidencia C-02/C-05, nunca una base alternativa."""

from sqlalchemy import text

REGISTRO = {"email": "alta@example.com", "nombre": "Alta Cliente", "password": "ClaveNueva99!",
            "documento": "40000001", "telefono": "2614000003"}


async def foto_auth(fabrica):
    async with fabrica() as sesion:
        return {tabla: (await sesion.exec(text(f"SELECT * FROM {tabla} ORDER BY id"))).all()
                for tabla in ("usuario", "asignacion_rol", "cliente", "evento_seguridad")}
