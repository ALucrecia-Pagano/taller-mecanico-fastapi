"""Paginación de los listados (spec paginacion, P1-P7)."""

from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from app.core.errores import PaginaInexistente
from app.core.paginacion import (
    Pagina,
    ParametrosDePagina,
    armar_pagina,
    calcular_ventana,
    parametros_de_pagina,
)
from tablas_de_prueba import ArticuloDePrueba, UoWDePrueba


def test_p1_ventana_de_cada_pagina():
    primera = calcular_ventana(5, page=1, size=2)
    tercera = calcular_ventana(5, page=3, size=2)

    assert (primera.offset, primera.limit, primera.pages) == (0, 2, 3)
    assert (tercera.offset, tercera.limit, tercera.pages) == (4, 2, 3)


def test_p2_mas_alla_de_la_ultima():
    with pytest.raises(PaginaInexistente) as error:
        calcular_ventana(4, page=3, size=2)

    assert error.value.mensaje == "La página 3 no existe: hay 2"


def test_p3_cero_resultados_es_una_pagina_vacia():
    ventana = calcular_ventana(0, page=1, size=20)

    assert (ventana.offset, ventana.pages) == (0, 1)
    with pytest.raises(PaginaInexistente) as error:
        calcular_ventana(0, page=2, size=20)
    assert error.value.mensaje == "La página 2 no existe: hay 1"


def test_p4_bordes_del_redondeo():
    assert calcular_ventana(100, page=1, size=100).pages == 1
    assert calcular_ventana(101, page=1, size=100).pages == 2


def app_de_prueba() -> FastAPI:
    app = FastAPI()

    @app.get("/lista")
    async def lista(pagina: Annotated[ParametrosDePagina, Depends(parametros_de_pagina)]) -> dict[str, int]:
        return {"page": pagina.page, "size": pagina.size}

    return app


@pytest.fixture
async def cliente_de_prueba():
    transporte = ASGITransport(app=app_de_prueba())
    async with AsyncClient(transport=transporte, base_url="http://test") as cliente:
        yield cliente


async def test_p5_defaults_y_limites(cliente_de_prueba):
    sin_parametros = await cliente_de_prueba.get("/lista")
    tope = await cliente_de_prueba.get("/lista", params={"size": 100})

    assert sin_parametros.json() == {"page": 1, "size": 20}
    assert tope.status_code == 200


class ItemDePrueba(BaseModel):
    id: int
    descripcion: str


def test_p6_forma_del_envoltorio():
    items = [ItemDePrueba(id=3, descripcion="Bujía"), ItemDePrueba(id=4, descripcion="Aceite")]
    ventana = calcular_ventana(5, page=2, size=2)

    pagina = armar_pagina(items, total=5, page=2, size=2, ventana=ventana)
    cuerpo = Pagina[ItemDePrueba].model_validate(pagina).model_dump(mode="json")

    assert cuerpo == {
        "items": [{"id": 3, "descripcion": "Bujía"}, {"id": 4, "descripcion": "Aceite"}],
        "total": 5,
        "page": 2,
        "size": 2,
        "pages": 3,
    }


async def pagina_de_articulos(fabrica, minimo: int, page: int, size: int):
    """El recorrido de un servicio: count -> validar -> listar -> envoltorio (design D5)."""
    async with fabrica() as sesion:
        uow = UoWDePrueba(sesion)
        async with uow:
            total = await uow.articulos.contar_con_cantidad_mayor_a(minimo)
            ventana = calcular_ventana(total, page, size)
            items = await uow.articulos.listar_con_cantidad_mayor_a(minimo, ventana.offset, ventana.limit)
        return armar_pagina(items, total, page, size, ventana)


async def test_p7_total_con_los_mismos_filtros(tablas_limpias):
    async with tablas_limpias() as sesion:
        async with UoWDePrueba(sesion) as uow:
            for numero, cantidad in enumerate((1, 10, 3, 20, 7), start=1):
                await uow.articulos.add(ArticuloDePrueba(nombre=f"Artículo {numero}", cantidad=cantidad))

    primera = await pagina_de_articulos(tablas_limpias, minimo=5, page=1, size=2)
    segunda = await pagina_de_articulos(tablas_limpias, minimo=5, page=2, size=2)

    assert (primera.total, primera.pages) == (3, 2)
    assert [a.id for a in primera.items] == [2, 4]
    assert [a.id for a in segunda.items] == [5]
    with pytest.raises(PaginaInexistente, match="La página 3 no existe: hay 2"):
        await pagina_de_articulos(tablas_limpias, minimo=5, page=3, size=2)


@pytest.mark.parametrize("parametros", [{"size": 500}, {"size": 0}, {"page": 0}, {"page": "abc"}])
async def test_p5_valores_invalidos(cliente_de_prueba, parametros):
    respuesta = await cliente_de_prueba.get("/lista", params=parametros)

    assert respuesta.status_code == 422
