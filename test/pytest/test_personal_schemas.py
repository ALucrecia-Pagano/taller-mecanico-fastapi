"""PE4-7 y RO2: contratos administrativos estrictos, sin I/O."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.modules.usuarios.schemas import AltaPersonal, AsignarRol


ALTA = {"email": "personal@example.com", "nombre": "Personal", "password_provisoria": "Provisoria99!", "rol": "MECANICO"}


@pytest.mark.parametrize("rol", ["CLIENTE", "JEFE"])
@pytest.mark.parametrize("modelo,datos", [(AltaPersonal, ALTA), (AsignarRol, {"rol": "MECANICO"})])
def test_pe4_roles_no_personal_422(modelo, datos, rol):
    with pytest.raises(ValidationError):
        modelo.model_validate({**datos, "rol": rol})


@pytest.mark.parametrize("modelo,datos", [(AltaPersonal, ALTA), (AsignarRol, {"rol": "MECANICO"})])
@pytest.mark.parametrize("extra", ["activo", "otorgada_por"])
def test_pe5_extras_rechazados(modelo, datos, extra):
    with pytest.raises(ValidationError):
        modelo.model_validate({**datos, extra: 1})


@pytest.mark.parametrize("password", ["a"*72, "ñ"*36])
def test_pe6_72_bytes_aceptados(password):
    assert AltaPersonal.model_validate({**ALTA, "password_provisoria": password}).password_provisoria == password


@pytest.mark.parametrize("password", ["a"*73, "ñ"*36+"a", "", "clave\x00"])
def test_pe6_pe7_password_invalida(password):
    with pytest.raises(ValidationError):
        AltaPersonal.model_validate({**ALTA, "password_provisoria": password})


@pytest.mark.parametrize("delta,zona", [(0, True), (-1, True), (10, False)])
def test_ro2_fecha_invalida(delta, zona, monkeypatch):
    import app.modules.usuarios.schemas as schemas
    ahora = datetime.now(UTC)
    class Reloj(datetime):
        @classmethod
        def now(cls, tz=None):
            return ahora
    monkeypatch.setattr(schemas, "datetime", Reloj)
    fecha = ahora+timedelta(seconds=delta)
    with pytest.raises(ValidationError):
        AsignarRol(rol="ADMIN", vence_en=fecha if zona else fecha.replace(tzinfo=None))


@pytest.mark.parametrize("datos", [{"rol": "MECANICO"}, {"rol": "ADMIN", "vence_en": None},
                                     {"rol": "RECEPCION", "vence_en": "2099-01-01T12:00:00-03:00"}])
def test_ro1_schema_futuro_omitido_null(datos):
    assert AsignarRol.model_validate(datos).rol == datos["rol"]
