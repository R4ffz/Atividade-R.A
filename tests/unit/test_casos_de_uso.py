"""Testes unitários dos casos de uso, com repositórios em memória e relógio fixo."""

from datetime import date
from decimal import Decimal

import pytest

from cobrancas.application.casos_de_uso import (
    CadastrarContrato,
    CalcularCobranca,
    ConsultarContrato,
    EmitirCobranca,
    ListarCobrancasDoContrato,
    RegistrarPagamento,
)
from cobrancas.domain.excecoes import (
    ConflitoError,
    NaoEncontradoError,
    RegraDeNegocioError,
    ValidacaoError,
)
from cobrancas.infrastructure.memoria import (
    CobrancaRepositorioMemoria,
    ContratoRepositorioMemoria,
)
from cobrancas.infrastructure.relogio import RelogioFixo

HOJE = date(2026, 11, 25)


@pytest.fixture
def ctx(novo_contrato_dto):
    contratos = ContratoRepositorioMemoria()
    cobrancas = CobrancaRepositorioMemoria()
    relogio = RelogioFixo(HOJE)

    class Ctx:
        cadastrar = CadastrarContrato(contratos)
        consultar = ConsultarContrato(contratos)
        emitir = EmitirCobranca(contratos, cobrancas)
        listar_cobrancas = ListarCobrancasDoContrato(contratos, cobrancas)
        calcular = CalcularCobranca(cobrancas, relogio)
        pagar = RegistrarPagamento(cobrancas, relogio)
        novo = staticmethod(novo_contrato_dto)

    return Ctx


def test_cadastrar_e_consultar_contrato(ctx):
    criado = ctx.cadastrar.executar(ctx.novo())
    assert criado.id == 1
    assert criado.cliente_documento == "529.982.247-25"
    assert ctx.consultar.executar(1) == criado


def test_cadastro_invalido_nao_persiste(ctx):
    with pytest.raises(ValidacaoError):
        ctx.cadastrar.executar(ctx.novo(cliente_documento="000.000.000-00"))
    with pytest.raises(NaoEncontradoError):
        ctx.consultar.executar(1)


def test_emitir_cobranca(ctx):
    contrato = ctx.cadastrar.executar(ctx.novo())
    cobranca = ctx.emitir.executar(contrato.id, "2026-11")
    assert cobranca.data_vencimento == date(2026, 11, 10)
    assert cobranca.valor_original == Decimal("1000.00")
    assert cobranca.status == "ABERTA"


def test_nao_emite_cobranca_duplicada_na_mesma_competencia(ctx):
    contrato = ctx.cadastrar.executar(ctx.novo())
    ctx.emitir.executar(contrato.id, "2026-11")
    with pytest.raises(ConflitoError):
        ctx.emitir.executar(contrato.id, "2026-11")


def test_nao_emite_cobranca_para_contrato_inexistente(ctx):
    with pytest.raises(NaoEncontradoError):
        ctx.emitir.executar(99, "2026-11")


def test_nao_emite_cobranca_fora_da_vigencia(ctx):
    contrato = ctx.cadastrar.executar(ctx.novo())
    with pytest.raises(RegraDeNegocioError):
        ctx.emitir.executar(contrato.id, "2027-01")


def test_listar_cobrancas_ordenadas_por_competencia(ctx):
    contrato = ctx.cadastrar.executar(ctx.novo())
    ctx.emitir.executar(contrato.id, "2026-03")
    ctx.emitir.executar(contrato.id, "2026-01")
    competencias = [c.competencia for c in ctx.listar_cobrancas.executar(contrato.id)]
    assert competencias == ["2026-01", "2026-03"]


def test_calcular_usa_data_de_hoje_quando_nao_informada(ctx):
    contrato = ctx.cadastrar.executar(ctx.novo())
    cobranca = ctx.emitir.executar(contrato.id, "2026-11")
    calculo = ctx.calcular.executar(cobranca.id)
    assert calculo.data_referencia == HOJE
    assert calculo.dias_atraso == 15
    assert calculo.multa == Decimal("20.00")
    assert calculo.juros == Decimal("5.00")
    assert calculo.total == Decimal("1025.00")


def test_calcular_em_data_especifica(ctx):
    contrato = ctx.cadastrar.executar(ctx.novo())
    cobranca = ctx.emitir.executar(contrato.id, "2026-11")
    assert ctx.calcular.executar(cobranca.id, date(2026, 11, 9)).total == Decimal("1000.00")


def test_registrar_pagamento_persiste_status(ctx):
    contrato = ctx.cadastrar.executar(ctx.novo())
    cobranca = ctx.emitir.executar(contrato.id, "2026-11")
    pago = ctx.pagar.executar(cobranca.id, date(2026, 11, 20))
    assert pago.status == "PAGA"
    assert pago.total == Decimal("1023.33")
    [salva] = ctx.listar_cobrancas.executar(contrato.id)
    assert salva.status == "PAGA"
    assert salva.valor_pago == Decimal("1023.33")


def test_pagamento_com_data_futura_e_rejeitado(ctx):
    contrato = ctx.cadastrar.executar(ctx.novo())
    cobranca = ctx.emitir.executar(contrato.id, "2026-11")
    with pytest.raises(RegraDeNegocioError):
        ctx.pagar.executar(cobranca.id, date(2026, 11, 26))


def test_pagamento_duplicado_e_rejeitado(ctx):
    contrato = ctx.cadastrar.executar(ctx.novo())
    cobranca = ctx.emitir.executar(contrato.id, "2026-11")
    ctx.pagar.executar(cobranca.id)
    with pytest.raises(ConflitoError):
        ctx.pagar.executar(cobranca.id)
