"""Schemas HTTP (Pydantic). Validam o *formato*; regras de negócio ficam no domínio."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class ContratoEntrada(BaseModel):
    cliente_nome: str = Field(examples=["Maria da Silva"])
    cliente_documento: str = Field(examples=["529.982.247-25"])
    descricao: str = Field(examples=["Manutenção predial mensal"])
    valor_mensal: Decimal = Field(examples=["1500.00"])
    dia_vencimento: int = Field(examples=[10])
    data_inicio: date
    data_fim: date
    percentual_multa: Decimal = Field(default=Decimal("2"), examples=["2"])
    juros_mensal: Decimal = Field(default=Decimal("1"), examples=["1"])


class ContratoSaida(BaseModel):
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


class CobrancaEntrada(BaseModel):
    competencia: str = Field(examples=["2026-11"], description="Formato AAAA-MM")


class CobrancaSaida(BaseModel):
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


class PagamentoEntrada(BaseModel):
    data_pagamento: date | None = Field(
        default=None, description="Se omitida, usa a data de hoje"
    )


class DemonstrativoSaida(BaseModel):
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


class Erro(BaseModel):
    detalhe: str
