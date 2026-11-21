from datetime import date
from decimal import Decimal

import pytest

from cobrancas.application.dtos import NovoContratoDTO

CPF_VALIDO = "529.982.247-25"
CNPJ_VALIDO = "11.222.333/0001-81"


@pytest.fixture
def novo_contrato_dto():
    def _criar(**alteracoes):
        dados = dict(
            cliente_nome="Maria da Silva",
            cliente_documento=CPF_VALIDO,
            descricao="Manutenção predial mensal",
            valor_mensal=Decimal("1000.00"),
            dia_vencimento=10,
            data_inicio=date(2026, 1, 1),
            data_fim=date(2026, 12, 31),
        )
        dados.update(alteracoes)
        return NovoContratoDTO(**dados)

    return _criar
