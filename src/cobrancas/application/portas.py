"""Portas de saída da aplicação que não pertencem ao domínio."""

from __future__ import annotations

from datetime import date
from typing import Protocol


class Relogio(Protocol):
    """Fornece a data atual. Abstraído para permitir testes determinísticos."""

    def hoje(self) -> date: ...
