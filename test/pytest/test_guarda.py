"""Guarda de la base de prueba (spec suite-de-pruebas, T1 y T2)."""

from types import SimpleNamespace

import pytest

from guarda import derivar_base_de_prueba, verificar_base_de_prueba


def test_t1_rechaza_la_base_de_la_aplicacion():
    with pytest.raises(pytest.fail.Exception, match="taller_mecanico"):
        verificar_base_de_prueba(SimpleNamespace(postgres_db="taller_mecanico"))


def test_t1_acepta_la_base_de_prueba():
    verificar_base_de_prueba(SimpleNamespace(postgres_db="taller_mecanico_test"))


def test_deriva_la_base_de_prueba_desde_la_de_la_aplicacion():
    assert derivar_base_de_prueba("taller_mecanico") == "taller_mecanico_test"


def test_t2_aborta_si_el_env_ya_apunta_a_la_base_de_prueba():
    with pytest.raises(ValueError, match="POSTGRES_DB debe ser la base de la aplicación"):
        derivar_base_de_prueba("taller_mecanico_test")
