"""Objetos de transferência de dados entre apresentação e aplicação."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from ..domain.entidades import Cobranca, Contrato
from ..domain.regras import Demonstrativo


@dataclass(frozen=True)
class NovoContratoDTO:
    cliente_nome: str
    cliente_documento: str
    descricao: str
    valor_mensal: Decimal
    dia_vencimento: int
    data_inicio: date
    data_fim: date
    percentual_multa: Decimal = Decimal("2")
    juros_mensal: Decimal = Decimal("1")


@dataclass(frozen=True)
class ContratoDTO:
    id: int
    cliente_nome: str
    cliente_documento: str
    tipo_documento: str
    descricao: str
    valor_mensal: Decimal
    dia_vencimento: int
    data_inicio: date
    data_fim: date
    percentual_multa: Decimal
    juros_mensal: Decimal

    @classmethod
    def de_entidade(cls, contrato: Contrato) -> ContratoDTO:
        assert contrato.id is not None
        return cls(
            id=contrato.id,
            cliente_nome=contrato.cliente_nome,
            cliente_documento=str(contrato.cliente_documento),
            tipo_documento=contrato.cliente_documento.tipo,
            descricao=contrato.descricao,
            valor_mensal=contrato.valor_mensal.valor,
            dia_vencimento=contrato.dia_vencimento,
            data_inicio=contrato.data_inicio,
            data_fim=contrato.data_fim,
            percentual_multa=contrato.percentual_multa,
            juros_mensal=contrato.juros_mensal,
        )


@dataclass(frozen=True)
class CobrancaDTO:
    id: int
    contrato_id: int
    competencia: str
    data_vencimento: date
    valor_original: Decimal
    percentual_multa: Decimal
    juros_mensal: Decimal
    status: str
    data_pagamento: date | None
    valor_pago: Decimal | None

    @classmethod
    def de_entidade(cls, cobranca: Cobranca) -> CobrancaDTO:
        assert cobranca.id is not None
        return cls(
            id=cobranca.id,
            contrato_id=cobranca.contrato_id,
            competencia=str(cobranca.competencia),
            data_vencimento=cobranca.data_vencimento,
            valor_original=cobranca.valor_original.valor,
            percentual_multa=cobranca.percentual_multa,
            juros_mensal=cobranca.juros_mensal,
            status=cobranca.status.value,
            data_pagamento=cobranca.data_pagamento,
            valor_pago=cobranca.valor_pago.valor if cobranca.valor_pago else None,
        )


@dataclass(frozen=True)
class DemonstrativoDTO:
    cobranca_id: int
    status: str
    valor_original: Decimal
    data_vencimento: date
    vencimento_efetivo: date
    data_referencia: date
    dias_atraso: int
    multa: Decimal
    juros: Decimal
    total: Decimal

    @classmethod
    def de_calculo(cls, cobranca: Cobranca, d: Demonstrativo) -> DemonstrativoDTO:
        assert cobranca.id is not None
        return cls(
            cobranca_id=cobranca.id,
            status=cobranca.status.value,
            valor_original=d.valor_original.valor,
            data_vencimento=d.data_vencimento,
            vencimento_efetivo=d.vencimento_efetivo,
            data_referencia=d.data_referencia,
            dias_atraso=d.dias_atraso,
            multa=d.multa.valor,
            juros=d.juros.valor,
            total=d.total.valor,
        )
