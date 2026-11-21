"""Testes unitários das regras de cálculo de multa e juros (domínio puro)."""

from datetime import date
from decimal import Decimal

import pytest

from cobrancas.domain.excecoes import ValidacaoError
from cobrancas.domain.regras import CalculadoraEncargos, proximo_dia_util
from cobrancas.domain.valores import Dinheiro

VENCIMENTO = date(2026, 11, 10)  # terça-feira


@pytest.fixture
def calculadora():
    return CalculadoraEncargos(percentual_multa="2", juros_mensal="1")


def test_pagamento_antes_do_vencimento_nao_gera_encargos(calculadora):
    d = calculadora.calcular(Dinheiro("1000"), VENCIMENTO, date(2026, 11, 5))
    assert d.dias_atraso == 0
    assert d.multa == Dinheiro.zero()
    assert d.juros == Dinheiro.zero()
    assert d.total == Dinheiro("1000.00")
    assert not d.em_atraso


def test_pagamento_no_dia_do_vencimento_nao_gera_encargos(calculadora):
    d = calculadora.calcular(Dinheiro("1000"), VENCIMENTO, VENCIMENTO)
    assert d.total == Dinheiro("1000.00")


def test_um_dia_de_atraso_aplica_multa_integral_e_juros_pro_rata(calculadora):
    d = calculadora.calcular(Dinheiro("1000"), VENCIMENTO, date(2026, 11, 11))
    assert d.dias_atraso == 1
    assert d.multa.valor == Decimal("20.00")  # 2% de 1000
    assert d.juros.valor == Decimal("0.33")  # 1% a.m. / 30 dias
    assert d.total.valor == Decimal("1020.33")
    assert d.em_atraso


def test_trinta_dias_de_atraso_equivale_a_um_mes_de_juros(calculadora):
    d = calculadora.calcular(Dinheiro("1000"), VENCIMENTO, date(2026, 12, 10))
    assert d.dias_atraso == 30
    assert d.juros.valor == Decimal("10.00")
    assert d.total.valor == Decimal("1030.00")


def test_juros_simples_nao_capitalizam(calculadora):
    # 90 dias = 3 meses * 1% = 3% (juros simples), e não 3,0301% (compostos)
    d = calculadora.calcular(Dinheiro("1000"), VENCIMENTO, date(2027, 2, 8))
    assert d.dias_atraso == 90
    assert d.juros.valor == Decimal("30.00")


def test_multa_e_aplicada_uma_unica_vez(calculadora):
    curto = calculadora.calcular(Dinheiro("1500"), VENCIMENTO, date(2026, 11, 12))
    longo = calculadora.calcular(Dinheiro("1500"), VENCIMENTO, date(2027, 3, 1))
    assert curto.multa == longo.multa == Dinheiro("30.00")


def test_calculo_com_45_dias_de_atraso(calculadora):
    d = calculadora.calcular(Dinheiro("1500"), VENCIMENTO, date(2026, 12, 25))
    assert d.dias_atraso == 45
    assert d.multa.valor == Decimal("30.00")
    assert d.juros.valor == Decimal("22.50")  # 1500 * 1% * 45/30
    assert d.total.valor == Decimal("1552.50")


def test_arredondamento_half_up_em_centavos(calculadora):
    d = calculadora.calcular(Dinheiro("333.33"), VENCIMENTO, date(2026, 11, 17))
    assert d.dias_atraso == 7
    assert d.multa.valor == Decimal("6.67")  # 6,6666 -> 6,67
    assert d.juros.valor == Decimal("0.78")  # 0,77777 -> 0,78
    assert d.total.valor == Decimal("340.78")


def test_vencimento_no_sabado_pode_ser_pago_na_segunda_sem_encargos(calculadora):
    sabado = date(2026, 11, 21)
    segunda = date(2026, 11, 23)
    d = calculadora.calcular(Dinheiro("1000"), sabado, segunda)
    assert d.vencimento_efetivo == segunda
    assert d.dias_atraso == 0
    assert d.total.valor == Decimal("1000.00")


def test_pagamento_apos_prorrogacao_conta_atraso_desde_vencimento_original(calculadora):
    sabado = date(2026, 11, 21)
    terca = date(2026, 11, 24)
    d = calculadora.calcular(Dinheiro("1000"), sabado, terca)
    assert d.dias_atraso == 3
    assert d.juros.valor == Decimal("1.00")
    assert d.total.valor == Decimal("1021.00")


def test_taxas_zeradas_nao_geram_encargos():
    calc = CalculadoraEncargos(percentual_multa=0, juros_mensal=0)
    d = calc.calcular(Dinheiro("1000"), VENCIMENTO, date(2027, 1, 1))
    assert d.dias_atraso > 0
    assert d.total.valor == Decimal("1000.00")


def test_taxas_personalizadas_sao_respeitadas():
    calc = CalculadoraEncargos(percentual_multa="1.5", juros_mensal="0.5")
    d = calc.calcular(Dinheiro("2000"), VENCIMENTO, date(2026, 12, 10))
    assert d.multa.valor == Decimal("30.00")
    assert d.juros.valor == Decimal("10.00")


@pytest.mark.parametrize(
    "multa, juros",
    [("2.01", "1"), ("-1", "1"), ("2", "1.5"), ("2", "-0.1"), ("abc", "1")],
)
def test_taxas_fora_dos_limites_sao_rejeitadas(multa, juros):
    with pytest.raises(ValidacaoError):
        CalculadoraEncargos(percentual_multa=multa, juros_mensal=juros)


def test_valor_original_deve_ser_positivo(calculadora):
    with pytest.raises(ValidacaoError):
        calculadora.calcular(Dinheiro("0"), VENCIMENTO, VENCIMENTO)


@pytest.mark.parametrize(
    "data, esperado",
    [
        (date(2026, 11, 20), date(2026, 11, 20)),  # sexta
        (date(2026, 11, 21), date(2026, 11, 23)),  # sábado
        (date(2026, 11, 22), date(2026, 11, 23)),  # domingo
    ],
)
def test_proximo_dia_util(data, esperado):
    assert proximo_dia_util(data) == esperado
