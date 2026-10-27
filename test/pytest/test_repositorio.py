"""Repositorios genéricos (spec repositorios, R1-R11 y B1-B5), sobre las tablas prueba_*."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlmodel import select

from app.core.repository import BaseRepository, SoftDeleteRepository
from tablas_de_prueba import ArticuloDePrueba, BajaDePrueba, RepositorioDeArticulos


async def buscar_en_otra_sesion(fabrica, articulo_id: int) -> ArticuloDePrueba | None:
    async with fabrica() as otra:
        resultado = await otra.exec(select(ArticuloDePrueba).where(ArticuloDePrueba.id == articulo_id))
        return resultado.first()


async def test_r1_el_alta_deja_el_id_y_los_defaults_de_la_base_cargados(tablas_limpias):
    async with tablas_limpias() as sesion:
        repo = BaseRepository(sesion, ArticuloDePrueba)

        articulo = await repo.add(ArticuloDePrueba(nombre="Filtro"))

        assert articulo.id == 1
        # En async, leer una columna expirada dispararía IO implícito y fallaría (MissingGreenlet).
        assert isinstance(articulo.creado_en, datetime)
        assert articulo.creado_en.tzinfo is not None


async def test_r2_el_alta_no_se_confirma_sola(tablas_limpias):
    async with tablas_limpias() as sesion:
        articulo = await BaseRepository(sesion, ArticuloDePrueba).add(ArticuloDePrueba(nombre="Filtro"))

        assert await buscar_en_otra_sesion(tablas_limpias, articulo.id) is None

        await sesion.commit()  # en la aplicación lo hace el Unit of Work

    assert await buscar_en_otra_sesion(tablas_limpias, articulo.id) is not None


async def cargar_articulos(fabrica, *nombres: str, cantidad: int = 0) -> None:
    async with fabrica() as sesion:
        repo = BaseRepository(sesion, ArticuloDePrueba)
        for nombre in nombres:
            await repo.add(ArticuloDePrueba(nombre=nombre, cantidad=cantidad))
        await sesion.commit()


CINCO = ("Filtro", "Pastillas", "Bujía", "Aceite", "Correa")


async def test_r3_lectura_por_id_existente_e_inexistente(tablas_limpias):
    await cargar_articulos(tablas_limpias, "Filtro")

    async with tablas_limpias() as sesion:
        repo = BaseRepository(sesion, ArticuloDePrueba)
        encontrado = await repo.get_by_id(1)
        inexistente = await repo.get_by_id(999)

    assert encontrado.nombre == "Filtro"
    assert inexistente is None


async def test_r4_ventana_en_orden_y_ventana_fuera_de_rango(tablas_limpias):
    await cargar_articulos(tablas_limpias, *CINCO)

    async with tablas_limpias() as sesion:
        repo = BaseRepository(sesion, ArticuloDePrueba)
        ventana = await repo.get_all(offset=2, limit=2)
        fuera = await repo.get_all(offset=10, limit=2)

    assert [a.id for a in ventana] == [3, 4]
    assert fuera == []


async def test_r5_conteo_con_filas_y_sin_filas(tablas_limpias):
    async with tablas_limpias() as sesion:
        assert await BaseRepository(sesion, ArticuloDePrueba).count() == 0

    await cargar_articulos(tablas_limpias, *CINCO)

    async with tablas_limpias() as sesion:
        assert await BaseRepository(sesion, ArticuloDePrueba).count() == 5


async def test_r6_modifica_solo_lo_enviado(tablas_limpias):
    await cargar_articulos(tablas_limpias, "Filtro", cantidad=3)

    async with tablas_limpias() as sesion:
        repo = BaseRepository(sesion, ArticuloDePrueba)
        articulo = await repo.update(await repo.get_by_id(1), {"cantidad": 7})

        assert (articulo.nombre, articulo.cantidad) == ("Filtro", 7)
        assert (await buscar_en_otra_sesion(tablas_limpias, 1)).cantidad == 3  # flush, no commit
        await sesion.commit()

    assert (await buscar_en_otra_sesion(tablas_limpias, 1)).cantidad == 7


async def test_r7_clave_desconocida_rechazada(tablas_limpias):
    await cargar_articulos(tablas_limpias, "Filtro", cantidad=3)

    async with tablas_limpias() as sesion:
        repo = BaseRepository(sesion, ArticuloDePrueba)
        articulo = await repo.get_by_id(1)

        # Una clave válida junto a una desconocida: no se aplica ninguna.
        with pytest.raises(ValueError, match="precio"):
            await repo.update(articulo, {"cantidad": 9, "precio": 100})

        assert articulo.cantidad == 3
        assert not hasattr(articulo, "precio")


async def test_r8_el_id_no_se_modifica(tablas_limpias):
    await cargar_articulos(tablas_limpias, "Filtro")

    async with tablas_limpias() as sesion:
        repo = BaseRepository(sesion, ArticuloDePrueba)
        articulo = await repo.get_by_id(1)

        with pytest.raises(ValueError, match="'id'"):
            await repo.update(articulo, {"id": 99})

        assert articulo.id == 1


async def cargar_cantidades(fabrica, *cantidades: int) -> None:
    async with fabrica() as sesion:
        repo = BaseRepository(sesion, ArticuloDePrueba)
        for numero, cantidad in enumerate(cantidades, start=1):
            await repo.add(ArticuloDePrueba(nombre=f"Artículo {numero}", cantidad=cantidad))
        await sesion.commit()


@pytest.mark.parametrize(("minimo", "ids_esperados"), [(5, [2, 4, 5]), (15, [4])])
async def test_r10_total_e_items_con_el_mismo_filtro(tablas_limpias, minimo, ids_esperados):
    await cargar_cantidades(tablas_limpias, 1, 10, 3, 20, 7)

    async with tablas_limpias() as sesion:
        repo = RepositorioDeArticulos(sesion)
        total = await repo.contar_con_cantidad_mayor_a(minimo)
        items = await repo.listar_con_cantidad_mayor_a(minimo, offset=0, limit=100)

    assert [a.id for a in items] == ids_esperados
    assert total == len(ids_esperados)


async def test_r9_baja_fisica(tablas_limpias):
    await cargar_articulos(tablas_limpias, "Filtro")

    async with tablas_limpias() as sesion:
        repo = BaseRepository(sesion, ArticuloDePrueba)
        await repo.delete(await repo.get_by_id(1))

        assert await repo.get_by_id(1) is None  # dentro de la misma transacción
        await sesion.commit()

    assert await buscar_en_otra_sesion(tablas_limpias, 1) is None


# --- Borrado lógico (B1-B5) ---


async def cargar_bajas(fabrica, *nombres: str) -> None:
    async with fabrica() as sesion:
        repo = SoftDeleteRepository(sesion, BajaDePrueba)
        for nombre in nombres:
            await repo.add(BajaDePrueba(nombre=nombre))
        await sesion.commit()


async def test_b1_la_fila_dada_de_baja_deja_de_verse(tablas_limpias):
    await cargar_bajas(tablas_limpias, "AB123CD", "AC456EF")

    async with tablas_limpias() as sesion:
        repo = SoftDeleteRepository(sesion, BajaDePrueba)
        vehiculo = await repo.get_by_id(1)
        await repo.soft_delete(vehiculo)
        await sesion.commit()

    assert vehiculo.borrado_en.utcoffset() == timedelta(0)
    async with tablas_limpias() as sesion:
        repo = SoftDeleteRepository(sesion, BajaDePrueba)
        assert await repo.get_by_id(1) is None
        assert [b.id for b in await repo.get_all(offset=0, limit=10)] == [2]
        assert await repo.count() == 1


async def test_b2_recuperar_una_fila_dada_de_baja(tablas_limpias):
    await cargar_bajas(tablas_limpias, "AB123CD")
    async with tablas_limpias() as sesion:
        repo = SoftDeleteRepository(sesion, BajaDePrueba)
        await repo.soft_delete(await repo.get_by_id(1))
        await sesion.commit()

    async with tablas_limpias() as sesion:
        recuperado = await SoftDeleteRepository(sesion, BajaDePrueba).get_by_id_including_deleted(1)

    assert recuperado.nombre == "AB123CD"
    assert recuperado.borrado_en is not None


async def test_b3_una_segunda_baja_conserva_la_fecha_original(tablas_limpias):
    original = datetime(2026, 1, 15, 10, 30, tzinfo=timezone.utc)
    await cargar_bajas(tablas_limpias, "AB123CD")
    async with tablas_limpias() as sesion:
        repo = SoftDeleteRepository(sesion, BajaDePrueba)
        await repo.update(await repo.get_by_id(1), {"borrado_en": original})
        await sesion.commit()

    async with tablas_limpias() as sesion:
        repo = SoftDeleteRepository(sesion, BajaDePrueba)
        vehiculo = await repo.get_by_id_including_deleted(1)
        await repo.soft_delete(vehiculo)
        await sesion.commit()

    assert vehiculo.borrado_en == original


class RepositorioDeVehiculosDePrueba(SoftDeleteRepository[BajaDePrueba]):
    def __init__(self, session) -> None:
        super().__init__(session, BajaDePrueba)

    async def listar_por_prefijo(self, prefijo: str) -> list[BajaDePrueba]:
        # Sin filtro de baja propio: lo hereda de _consulta().
        stmt = self._consulta().where(BajaDePrueba.nombre.startswith(prefijo))
        return await self._listar(stmt, offset=0, limit=100)


async def test_b5_los_metodos_con_nombre_heredan_el_filtro(tablas_limpias):
    await cargar_bajas(tablas_limpias, "AB123CD", "AB999ZZ")
    async with tablas_limpias() as sesion:
        repo = RepositorioDeVehiculosDePrueba(sesion)
        await repo.soft_delete(await repo.get_by_id(1))
        await sesion.commit()

    async with tablas_limpias() as sesion:
        vigentes = await RepositorioDeVehiculosDePrueba(sesion).listar_por_prefijo("AB")

    assert [v.nombre for v in vigentes] == ["AB999ZZ"]


RAIZ = Path(__file__).resolve().parents[2]


def test_r11_ningun_repositorio_confirma():
    archivos = [RAIZ / "app" / "core" / "repository.py", *sorted(RAIZ.glob("app/modules/*/repository.py"))]

    con_commit = [a.name for a in archivos if ".commit(" in a.read_text(encoding="utf-8")]

    assert archivos[0].is_file()  # no pasa en vacío: el repositorio del core existe y se revisa
    assert con_commit == []


def test_b4_modelo_sin_borrado_en():
    with pytest.raises(TypeError, match="borrado_en"):
        SoftDeleteRepository(None, ArticuloDePrueba)
