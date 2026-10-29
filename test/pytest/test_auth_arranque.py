"""El arranque no depende de imports previos de seed o de otros tests."""

import subprocess
import sys


def test_auth_arranque_registra_modelos_sin_importar_seed():
    resultado = subprocess.run(
        [sys.executable, "-c", "import main; from sqlalchemy.orm import configure_mappers; configure_mappers()"],
        capture_output=True, text=True, timeout=20,
    )
    assert resultado.returncode == 0, resultado.stderr
