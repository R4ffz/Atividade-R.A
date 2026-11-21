from __future__ import annotations

from datetime import date


class RelogioSistema:
    def hoje(self) -> date:
        return date.today()


class RelogioFixo:
    """Relógio com data fixa, útil para testes e demonstrações."""

    def __init__(self, data: date) -> None:
        self.data = data

    def hoje(self) -> date:
        return self.data
