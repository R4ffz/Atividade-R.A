"""Testes de integração: HTTP -> casos de uso -> domínio -> SQLite (em memória)."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from cobrancas.infrastructure.relogio import RelogioFixo
from cobrancas.main import criar_aplicacao

CONTRATO = {
    "cliente_nome": "Empresa Exemplo Ltda",
    "cliente_documento": "11.222.333/0001-81",
    "descricao": "Suporte técnico mensal",
    "valor_mensal": "1500.00",
    "dia_vencimento": 10,
    "data_inicio": "2026-01-01",
    "data_fim": "2026-12-31",
}


@pytest.fixture
def cliente():
    app = criar_aplicacao(":memory:", RelogioFixo(date(2026, 11, 25)))
    return TestClient(app)


def test_fluxo_completo(cliente):
    r = cliente.post("/contratos", json=CONTRATO)
    assert r.status_code == 201, r.text
    contrato = r.json()
    assert contrato["tipo_documento"] == "CNPJ"

    r = cliente.post(f"/contratos/{contrato['id']}/cobrancas", json={"competencia": "2026-11"})
    assert r.status_code == 201, r.text
    cobranca = r.json()
    assert cobranca["data_vencimento"] == "2026-11-10"

    r = cliente.get(f"/cobrancas/{cobranca['id']}/calculo", params={"data_referencia": "2026-12-25"})
    assert r.status_code == 200
    calculo = r.json()
    assert calculo["dias_atraso"] == 45
    assert calculo["multa"] == "30.00"
    assert calculo["juros"] == "22.50"
    assert calculo["total"] == "1552.50"

    r = cliente.post(f"/cobrancas/{cobranca['id']}/pagamento", json={"data_pagamento": "2026-11-20"})
    assert r.status_code == 200
    assert r.json()["status"] == "PAGA"
    assert r.json()["total"] == "1535.00"

    r = cliente.get(f"/contratos/{contrato['id']}/cobrancas")
    assert r.json()[0]["valor_pago"] == "1535.00"


def test_documento_invalido_retorna_422(cliente):
    r = cliente.post("/contratos", json={**CONTRATO, "cliente_documento": "123"})
    assert r.status_code == 422
    assert "Documento inválido" in r.json()["detalhe"]


def test_formato_invalido_retorna_422(cliente):
    r = cliente.post("/contratos", json={**CONTRATO, "data_inicio": "ontem"})
    assert r.status_code == 422


def test_contrato_inexistente_retorna_404(cliente):
    assert cliente.get("/contratos/999").status_code == 404
    assert cliente.get("/cobrancas/999/calculo").status_code == 404


def test_cobranca_duplicada_retorna_409(cliente):
    contrato_id = cliente.post("/contratos", json=CONTRATO).json()["id"]
    url = f"/contratos/{contrato_id}/cobrancas"
    assert cliente.post(url, json={"competencia": "2026-05"}).status_code == 201
    r = cliente.post(url, json={"competencia": "2026-05"})
    assert r.status_code == 409


def test_pagamento_sem_corpo_usa_data_de_hoje(cliente):
    contrato_id = cliente.post("/contratos", json=CONTRATO).json()["id"]
    cobranca_id = cliente.post(
        f"/contratos/{contrato_id}/cobrancas", json={"competencia": "2026-11"}
    ).json()["id"]
    r = cliente.post(f"/cobrancas/{cobranca_id}/pagamento")
    assert r.status_code == 200
    assert r.json()["data_referencia"] == "2026-11-25"
    assert cliente.post(f"/cobrancas/{cobranca_id}/pagamento").status_code == 409
