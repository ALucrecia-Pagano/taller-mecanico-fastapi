"""Espía de bcrypt (design D2): registra en qué hilo corre cada llamada y cuántas corren a la vez.

Reemplaza hashpw y checkpw dentro de app.core.security; la pausa corre en el hilo de la
llamada (no bloquea el bucle) y hace que las llamadas admitidas por el semáforo se solapen.
"""

import threading
import time

import bcrypt


class EspiaBcrypt:
    def __init__(self, pausa: float) -> None:
        self.pausa = pausa
        self.hilos: list[int] = []
        self.activas = 0
        self.pico = 0
        self._lock = threading.Lock()

    def envolver(self, original):
        def espiada(*args, **kwargs):
            with self._lock:
                self.hilos.append(threading.get_ident())
                self.activas += 1
                self.pico = max(self.pico, self.activas)
            try:
                time.sleep(self.pausa)
                return original(*args, **kwargs)
            finally:
                with self._lock:
                    self.activas -= 1

        return espiada


def espiar_bcrypt(monkeypatch, pausa: float = 0.0) -> EspiaBcrypt:
    espia = EspiaBcrypt(pausa)
    monkeypatch.setattr("app.core.security.bcrypt.hashpw", espia.envolver(bcrypt.hashpw))
    monkeypatch.setattr("app.core.security.bcrypt.checkpw", espia.envolver(bcrypt.checkpw))
    return espia
