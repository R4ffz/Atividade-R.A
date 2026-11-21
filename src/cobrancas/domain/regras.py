"""Regras financeiras: multa e juros de mora por atraso.

Regras implementadas:
* Multa moratória: percentual fixo sobre o valor original, aplicado uma única
  vez quando há atraso (limite de 2%, conforme art. 52, §1º, do CDC).
* Juros de mora: juros simples pro rata die, com mês comercial de 30 dias
  (limite de 1% ao mês).
* Vencimento em sábado ou domingo é prorrogado para o próximo dia útil; se o
  pagamento ocorrer depois da data prorrogada, os dias de atraso contam a
  partir do vencimento original.
* Cada parcela (multa e juros) é arredondada em centavos (half-up).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from .excecoes import ValidacaoError
from .valores import Dinheiro, para_decimal

LIMITE_MULTA_PERCENTUAL = Decimal("2")
LIMITE_JUROS_MENSAL_PERCENTUAL = Decimal("1")
DIAS_MES_COMERCIAL = 30


def validar_taxas(percentual_multa: Decimal, juros_mensal: Decimal) -> None:
    if not Decimal("0") <= percentual_multa <= LIMITE_MULTA_PERCENTUAL:
        raise ValidacaoError(
            f"Multa deve estar entre 0% e {LIMITE_MULTA_PERCENTUAL}%: {percentual_multa}%"
        )
    if not Decimal("0") <= juros_mensal <= LIMITE_JUROS_MENSAL_PERCENTUAL:
        raise ValidacaoError(
            f"Juros devem estar entre 0% e {LIMITE_JUROS_MENSAL_PERCENTUAL}% ao mês: {juros_mensal}%"
        )


def proximo_dia_util(data: date) -> date:
    """Retorna a própria data se for dia útil, ou a próxima segunda-feira."""
    while data.weekday() >= 5:  # 5 = sábado, 6 = domingo
        data += timedelta(days=1)
    return data


@dataclass(frozen=True)
class Demonstrativo:
    """Resultado do cálculo de uma cobrança em uma data de referência."""

    valor_original: Dinheiro
    data_vencimento: date
    vencimento_efetivo: date
    data_referencia: date
    dias_atraso: int
    multa: Dinheiro
    juros: Dinheiro
    total: Dinheiro

    @property
    def em_atraso(self) -> bool:
        return self.dias_atraso > 0


class CalculadoraEncargos:
    """Calcula multa e juros por atraso de forma determinística."""

    def __init__(self, percentual_multa: object, juros_mensal: object) -> None:
        self.percentual_multa = para_decimal(percentual_multa)
        self.juros_mensal = para_decimal(juros_mensal)
        validar_taxas(self.percentual_multa, self.juros_mensal)

    def dias_de_atraso(self, data_vencimento: date, data_referencia: date) -> int:
        if data_referencia <= proximo_dia_util(data_vencimento):
            return 0
        return (data_referencia - data_vencimento).days

    def calcular(
        self, valor_original: Dinheiro, data_vencimento: date, data_referencia: date
    ) -> Demonstrativo:
        if not valor_original.e_positivo():
            raise ValidacaoError("Valor original da cobrança deve ser positivo")

        dias = self.dias_de_atraso(data_vencimento, data_referencia)
        if dias == 0:
            multa = juros = Dinheiro.zero()
        else:
            base = valor_original.valor
            multa = Dinheiro(base * self.percentual_multa / 100)
            juros = Dinheiro(
                base * self.juros_mensal * dias / (100 * DIAS_MES_COMERCIAL)
            )

        return Demonstrativo(
            valor_original=valor_original,
            data_vencimento=data_vencimento,
            vencimento_efetivo=proximo_dia_util(data_vencimento),
            data_referencia=data_referencia,
            dias_atraso=dias,
            multa=multa,
            juros=juros,
            total=valor_original + multa + juros,
        )
