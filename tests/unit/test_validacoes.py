"""Testes unitários de validação: objetos de valor e entidades."""

from datetime import date
from decimal import Decimal

import pytest

from cobrancas.domain.entidades import Cobranca, Contrato, StatusCobranca
from cobrancas.domain.excecoes import ConflitoError, RegraDeNegocioError, ValidacaoError
from cobrancas.domain.valores import Competencia, Dinheiro, Documento

from ..conftest import CNPJ_VALIDO, CPF_VALIDO


def criar_contrato(**alteracoes) -> Contrato:
    dados = dict(
        id=1,
        cliente_nome="Maria da Silva",
        cliente_documento=Documento(CPF_VALIDO),
        descricao="Manutenção predial",
        valor_mensal=Dinheiro("1000"),
        dia_vencimento=10,
        data_inicio=date(2026, 1, 1),
        data_fim=date(2026, 12, 31),
    )
    dados.update(alteracoes)
    return Contrato(**dados)


# ---------- Dinheiro ----------

def test_dinheiro_arredonda_em_centavos():
    assert Dinheiro("10.005").valor == Decimal("10.01")
    assert Dinheiro("10.004").valor == Decimal("10.00")


def test_dinheiro_evita_imprecisao_de_float():
    assert Dinheiro(0.1).valor + Dinheiro(0.2).valor == Decimal("0.30")


def test_dinheiro_rejeita_valor_nao_numerico():
    with pytest.raises(ValidacaoError):
        Dinheiro("dez reais")


# ---------- Documento ----------

def test_cpf_valido_e_normalizado():
    doc = Documento(CPF_VALIDO)
    assert doc.numero == "52998224725"
    assert doc.tipo == "CPF"
    assert str(doc) == CPF_VALIDO


def test_cnpj_valido_e_normalizado():
    doc = Documento(CNPJ_VALIDO)
    assert doc.numero == "11222333000181"
    assert doc.tipo == "CNPJ"
    assert str(doc) == CNPJ_VALIDO


@pytest.mark.parametrize(
    "numero",
    ["529.982.247-24", "111.111.111-11", "123", "11.222.333/0001-82", "", "abc"],
)
def test_documentos_invalidos_sao_rejeitados(numero):
    with pytest.raises(ValidacaoError):
        Documento(numero)


# ---------- Competência ----------

def test_competencia_parse():
    comp = Competencia.parse("2026-02")
    assert (comp.ano, comp.mes) == (2026, 2)
    assert comp.ultimo_dia == date(2026, 2, 28)
    assert str(comp) == "2026-02"


@pytest.mark.parametrize("texto", ["2026-13", "2026-00", "26-01", "2026/01", "abc"])
def test_competencia_invalida(texto):
    with pytest.raises(ValidacaoError):
        Competencia.parse(texto)


# ---------- Contrato ----------

def test_contrato_valido_usa_taxas_padrao():
    contrato = criar_contrato()
    assert contrato.percentual_multa == Decimal("2")
    assert contrato.juros_mensal == Decimal("1")


@pytest.mark.parametrize(
    "alteracao, mensagem",
    [
        ({"cliente_nome": "  "}, "Nome"),
        ({"descricao": ""}, "Descrição"),
        ({"valor_mensal": Dinheiro("0")}, "Valor mensal"),
        ({"valor_mensal": Dinheiro("-10")}, "Valor mensal"),
        ({"dia_vencimento": 0}, "Dia de vencimento"),
        ({"dia_vencimento": 29}, "Dia de vencimento"),
        ({"data_fim": date(2025, 12, 31)}, "Data de fim"),
        ({"data_fim": date(2026, 1, 1)}, "Data de fim"),
        ({"percentual_multa": Decimal("10")}, "Multa"),
        ({"juros_mensal": Decimal("5")}, "Juros"),
    ],
)
def test_contrato_invalido(alteracao, mensagem):
    with pytest.raises(ValidacaoError, match=mensagem):
        criar_contrato(**alteracao)


def test_emitir_cobranca_usa_dia_de_vencimento_e_copia_taxas():
    contrato = criar_contrato(percentual_multa=Decimal("1.5"), juros_mensal=Decimal("0.8"))
    cobranca = contrato.emitir_cobranca(Competencia(2026, 3))
    assert cobranca.data_vencimento == date(2026, 3, 10)
    assert cobranca.valor_original == Dinheiro("1000")
    assert cobranca.percentual_multa == Decimal("1.5")
    assert cobranca.juros_mensal == Decimal("0.8")
    assert cobranca.status is StatusCobranca.ABERTA


@pytest.mark.parametrize("competencia", [Competencia(2025, 12), Competencia(2027, 1)])
def test_nao_emite_cobranca_fora_da_vigencia(competencia):
    with pytest.raises(RegraDeNegocioError, match="fora da vigência"):
        criar_contrato().emitir_cobranca(competencia)


def test_nao_emite_cobranca_de_contrato_nao_cadastrado():
    with pytest.raises(RegraDeNegocioError):
        criar_contrato(id=None).emitir_cobranca(Competencia(2026, 5))


# ---------- Cobrança ----------

def criar_cobranca() -> Cobranca:
    return criar_contrato().emitir_cobranca(Competencia(2026, 11))  # vence 10/11


def test_registrar_pagamento_em_atraso_guarda_valor_pago():
    cobranca = criar_cobranca()
    demonstrativo = cobranca.registrar_pagamento(date(2026, 12, 10))
    assert cobranca.paga
    assert cobranca.data_pagamento == date(2026, 12, 10)
    assert cobranca.valor_pago == demonstrativo.total == Dinheiro("1030.00")


def test_cobranca_paga_nao_acumula_novos_encargos():
    cobranca = criar_cobranca()
    cobranca.registrar_pagamento(date(2026, 11, 10))
    depois = cobranca.calcular(date(2027, 6, 1))
    assert depois.total == Dinheiro("1000.00")
    assert depois.data_referencia == date(2026, 11, 10)


def test_cobranca_nao_pode_ser_paga_duas_vezes():
    cobranca = criar_cobranca()
    cobranca.registrar_pagamento(date(2026, 11, 10))
    with pytest.raises(ConflitoError):
        cobranca.registrar_pagamento(date(2026, 11, 11))
