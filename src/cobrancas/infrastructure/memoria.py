"""Repositórios em memória (usados em testes e protótipos)."""

from __future__ import annotations

import copy
import itertools

from ..domain.entidades import Cobranca, Contrato
from ..domain.repositorios import CobrancaRepositorio, ContratoRepositorio
from ..domain.valores import Competencia


class ContratoRepositorioMemoria(ContratoRepositorio):
    def __init__(self) -> None:
        self._dados: dict[int, Contrato] = {}
        self._ids = itertools.count(1)

    def salvar(self, contrato: Contrato) -> Contrato:
        if contrato.id is None:
            contrato.id = next(self._ids)
        self._dados[contrato.id] = copy.deepcopy(contrato)
        return copy.deepcopy(contrato)

    def buscar_por_id(self, contrato_id: int) -> Contrato | None:
        contrato = self._dados.get(contrato_id)
        return copy.deepcopy(contrato) if contrato else None

    def listar(self) -> list[Contrato]:
        return [copy.deepcopy(c) for c in self._dados.values()]


class CobrancaRepositorioMemoria(CobrancaRepositorio):
    def __init__(self) -> None:
        self._dados: dict[int, Cobranca] = {}
        self._ids = itertools.count(1)

    def salvar(self, cobranca: Cobranca) -> Cobranca:
        if cobranca.id is None:
            cobranca.id = next(self._ids)
        self._dados[cobranca.id] = copy.deepcopy(cobranca)
        return copy.deepcopy(cobranca)

    def buscar_por_id(self, cobranca_id: int) -> Cobranca | None:
        cobranca = self._dados.get(cobranca_id)
        return copy.deepcopy(cobranca) if cobranca else None

    def buscar_por_competencia(
        self, contrato_id: int, competencia: Competencia
    ) -> Cobranca | None:
        for c in self._dados.values():
            if c.contrato_id == contrato_id and c.competencia == competencia:
                return copy.deepcopy(c)
        return None

    def listar_por_contrato(self, contrato_id: int) -> list[Cobranca]:
        return [
            copy.deepcopy(c)
            for c in sorted(self._dados.values(), key=lambda c: c.competencia)
            if c.contrato_id == contrato_id
        ]
