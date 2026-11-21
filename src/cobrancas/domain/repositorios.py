"""Portas (interfaces) de persistência definidas pelo domínio.

A infraestrutura implementa estas interfaces; o domínio e a aplicação
dependem apenas das abstrações (Princípio da Inversão de Dependência).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .entidades import Cobranca, Contrato
from .valores import Competencia


class ContratoRepositorio(ABC):
    @abstractmethod
    def salvar(self, contrato: Contrato) -> Contrato: ...

    @abstractmethod
    def buscar_por_id(self, contrato_id: int) -> Contrato | None: ...

    @abstractmethod
    def listar(self) -> list[Contrato]: ...


class CobrancaRepositorio(ABC):
    @abstractmethod
    def salvar(self, cobranca: Cobranca) -> Cobranca: ...

    @abstractmethod
    def buscar_por_id(self, cobranca_id: int) -> Cobranca | None: ...

    @abstractmethod
    def buscar_por_competencia(
        self, contrato_id: int, competencia: Competencia
    ) -> Cobranca | None: ...

    @abstractmethod
    def listar_por_contrato(self, contrato_id: int) -> list[Cobranca]: ...
