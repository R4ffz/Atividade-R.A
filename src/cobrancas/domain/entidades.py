"""Entidades do domínio: Contrato e Cobrança."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum

from .excecoes import ConflitoError, RegraDeNegocioError, ValidacaoError
from .regras import CalculadoraEncargos, Demonstrativo, validar_taxas
from .valores import Competencia, Dinheiro, Documento, para_decimal

DIA_VENCIMENTO_MAXIMO = 28  # garante que o dia exista em todos os meses


class StatusCobranca(str, Enum):
    ABERTA = "ABERTA"
    PAGA = "PAGA"


@dataclass
class Contrato:
    cliente_nome: str
    cliente_documento: Documento
    descricao: str
    valor_mensal: Dinheiro
    dia_vencimento: int
    data_inicio: date
    data_fim: date
    percentual_multa: Decimal = Decimal("2")
    juros_mensal: Decimal = Decimal("1")
    id: int | None = None

    def __post_init__(self) -> None:
        self.cliente_nome = (self.cliente_nome or "").strip()
        self.descricao = (self.descricao or "").strip()
        self.percentual_multa = para_decimal(self.percentual_multa)
        self.juros_mensal = para_decimal(self.juros_mensal)
        self._validar()

    def _validar(self) -> None:
        if len(self.cliente_nome) < 3:
            raise ValidacaoError("Nome do cliente deve ter ao menos 3 caracteres")
        if not self.descricao:
            raise ValidacaoError("Descrição do contrato é obrigatória")
        if not self.valor_mensal.e_positivo():
            raise ValidacaoError("Valor mensal deve ser maior que zero")
        if not 1 <= self.dia_vencimento <= DIA_VENCIMENTO_MAXIMO:
            raise ValidacaoError(
                f"Dia de vencimento deve estar entre 1 e {DIA_VENCIMENTO_MAXIMO}"
            )
        if self.data_fim <= self.data_inicio:
            raise ValidacaoError("Data de fim deve ser posterior à data de início")
        validar_taxas(self.percentual_multa, self.juros_mensal)

    def vigente_na_competencia(self, competencia: Competencia) -> bool:
        return (
            competencia.primeiro_dia <= self.data_fim
            and competencia.ultimo_dia >= self.data_inicio
        )

    def vencimento_da_competencia(self, competencia: Competencia) -> date:
        return date(competencia.ano, competencia.mes, self.dia_vencimento)

    def emitir_cobranca(self, competencia: Competencia) -> Cobranca:
        if self.id is None:
            raise RegraDeNegocioError("Contrato precisa estar cadastrado para emitir cobranças")
        if not self.vigente_na_competencia(competencia):
            raise RegraDeNegocioError(
                f"Competência {competencia} fora da vigência do contrato "
                f"({self.data_inicio.isoformat()} a {self.data_fim.isoformat()})"
            )
        # As taxas são copiadas para a cobrança: alterações futuras no
        # contrato não afetam cobranças já emitidas.
        return Cobranca(
            contrato_id=self.id,
            competencia=competencia,
            data_vencimento=self.vencimento_da_competencia(competencia),
            valor_original=self.valor_mensal,
            percentual_multa=self.percentual_multa,
            juros_mensal=self.juros_mensal,
        )


@dataclass
class Cobranca:
    contrato_id: int
    competencia: Competencia
    data_vencimento: date
    valor_original: Dinheiro
    percentual_multa: Decimal
    juros_mensal: Decimal
    status: StatusCobranca = StatusCobranca.ABERTA
    data_pagamento: date | None = None
    valor_pago: Dinheiro | None = None
    id: int | None = None
    _calculadora: CalculadoraEncargos = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        self._calculadora = CalculadoraEncargos(self.percentual_multa, self.juros_mensal)

    @property
    def paga(self) -> bool:
        return self.status is StatusCobranca.PAGA

    def calcular(self, data_referencia: date) -> Demonstrativo:
        """Valor devido na data informada. Se já paga, retorna o valor da quitação."""
        if self.paga and self.data_pagamento is not None:
            data_referencia = self.data_pagamento
        return self._calculadora.calcular(
            self.valor_original, self.data_vencimento, data_referencia
        )

    def registrar_pagamento(self, data_pagamento: date) -> Demonstrativo:
        if self.paga:
            raise ConflitoError("Cobrança já está paga")
        demonstrativo = self._calculadora.calcular(
            self.valor_original, self.data_vencimento, data_pagamento
        )
        self.status = StatusCobranca.PAGA
        self.data_pagamento = data_pagamento
        self.valor_pago = demonstrativo.total
        return demonstrativo
