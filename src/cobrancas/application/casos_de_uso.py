"""Casos de uso da aplicação.

Cada caso de uso recebe suas dependências (repositórios, relógio) por
injeção no construtor e expõe um único método ``executar``.
"""

from __future__ import annotations

from datetime import date

from ..domain.entidades import Cobranca, Contrato
from ..domain.excecoes import ConflitoError, NaoEncontradoError, RegraDeNegocioError
from ..domain.repositorios import CobrancaRepositorio, ContratoRepositorio
from ..domain.valores import Competencia, Dinheiro, Documento
from .dtos import CobrancaDTO, ContratoDTO, DemonstrativoDTO, NovoContratoDTO
from .portas import Relogio


def _obter_contrato(repositorio: ContratoRepositorio, contrato_id: int) -> Contrato:
    contrato = repositorio.buscar_por_id(contrato_id)
    if contrato is None:
        raise NaoEncontradoError(f"Contrato {contrato_id} não encontrado")
    return contrato


def _obter_cobranca(repositorio: CobrancaRepositorio, cobranca_id: int) -> Cobranca:
    cobranca = repositorio.buscar_por_id(cobranca_id)
    if cobranca is None:
        raise NaoEncontradoError(f"Cobrança {cobranca_id} não encontrada")
    return cobranca


class CadastrarContrato:
    def __init__(self, contratos: ContratoRepositorio) -> None:
        self._contratos = contratos

    def executar(self, dados: NovoContratoDTO) -> ContratoDTO:
        contrato = Contrato(
            cliente_nome=dados.cliente_nome,
            cliente_documento=Documento(dados.cliente_documento),
            descricao=dados.descricao,
            valor_mensal=Dinheiro(dados.valor_mensal),
            dia_vencimento=dados.dia_vencimento,
            data_inicio=dados.data_inicio,
            data_fim=dados.data_fim,
            percentual_multa=dados.percentual_multa,
            juros_mensal=dados.juros_mensal,
        )
        return ContratoDTO.de_entidade(self._contratos.salvar(contrato))


class ConsultarContrato:
    def __init__(self, contratos: ContratoRepositorio) -> None:
        self._contratos = contratos

    def executar(self, contrato_id: int) -> ContratoDTO:
        return ContratoDTO.de_entidade(_obter_contrato(self._contratos, contrato_id))


class ListarContratos:
    def __init__(self, contratos: ContratoRepositorio) -> None:
        self._contratos = contratos

    def executar(self) -> list[ContratoDTO]:
        return [ContratoDTO.de_entidade(c) for c in self._contratos.listar()]


class EmitirCobranca:
    def __init__(
        self, contratos: ContratoRepositorio, cobrancas: CobrancaRepositorio
    ) -> None:
        self._contratos = contratos
        self._cobrancas = cobrancas

    def executar(self, contrato_id: int, competencia: str) -> CobrancaDTO:
        contrato = _obter_contrato(self._contratos, contrato_id)
        comp = Competencia.parse(competencia)
        if self._cobrancas.buscar_por_competencia(contrato_id, comp) is not None:
            raise ConflitoError(
                f"Já existe cobrança para o contrato {contrato_id} na competência {comp}"
            )
        cobranca = contrato.emitir_cobranca(comp)
        return CobrancaDTO.de_entidade(self._cobrancas.salvar(cobranca))


class ListarCobrancasDoContrato:
    def __init__(
        self, contratos: ContratoRepositorio, cobrancas: CobrancaRepositorio
    ) -> None:
        self._contratos = contratos
        self._cobrancas = cobrancas

    def executar(self, contrato_id: int) -> list[CobrancaDTO]:
        _obter_contrato(self._contratos, contrato_id)
        return [
            CobrancaDTO.de_entidade(c)
            for c in self._cobrancas.listar_por_contrato(contrato_id)
        ]


class CalcularCobranca:
    """Calcula o valor atualizado (com multa e juros) de uma cobrança."""

    def __init__(self, cobrancas: CobrancaRepositorio, relogio: Relogio) -> None:
        self._cobrancas = cobrancas
        self._relogio = relogio

    def executar(
        self, cobranca_id: int, data_referencia: date | None = None
    ) -> DemonstrativoDTO:
        cobranca = _obter_cobranca(self._cobrancas, cobranca_id)
        referencia = data_referencia or self._relogio.hoje()
        return DemonstrativoDTO.de_calculo(cobranca, cobranca.calcular(referencia))


class RegistrarPagamento:
    def __init__(self, cobrancas: CobrancaRepositorio, relogio: Relogio) -> None:
        self._cobrancas = cobrancas
        self._relogio = relogio

    def executar(
        self, cobranca_id: int, data_pagamento: date | None = None
    ) -> DemonstrativoDTO:
        cobranca = _obter_cobranca(self._cobrancas, cobranca_id)
        hoje = self._relogio.hoje()
        data = data_pagamento or hoje
        if data > hoje:
            raise RegraDeNegocioError("Data de pagamento não pode estar no futuro")
        demonstrativo = cobranca.registrar_pagamento(data)
        self._cobrancas.salvar(cobranca)
        return DemonstrativoDTO.de_calculo(cobranca, demonstrativo)
