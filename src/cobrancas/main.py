"""Raiz de composição: único ponto que conhece todas as camadas e as conecta.

Execução:  uvicorn cobrancas.main:criar_aplicacao --factory --app-dir src
"""

from __future__ import annotations

import os

from fastapi import FastAPI

from .application.casos_de_uso import (
    CadastrarContrato,
    CalcularCobranca,
    ConsultarContrato,
    EmitirCobranca,
    ListarCobrancasDoContrato,
    ListarContratos,
    RegistrarPagamento,
)
from .application.portas import Relogio
from .domain.repositorios import CobrancaRepositorio, ContratoRepositorio
from .infrastructure.relogio import RelogioSistema
from .infrastructure.sqlite import (
    BancoSQLite,
    CobrancaRepositorioSQLite,
    ContratoRepositorioSQLite,
)
from .presentation.api import CasosDeUso, criar_app


def montar_casos_de_uso(
    contratos: ContratoRepositorio, cobrancas: CobrancaRepositorio, relogio: Relogio
) -> CasosDeUso:
    return CasosDeUso(
        cadastrar_contrato=CadastrarContrato(contratos),
        consultar_contrato=ConsultarContrato(contratos),
        listar_contratos=ListarContratos(contratos),
        emitir_cobranca=EmitirCobranca(contratos, cobrancas),
        listar_cobrancas=ListarCobrancasDoContrato(contratos, cobrancas),
        calcular_cobranca=CalcularCobranca(cobrancas, relogio),
        registrar_pagamento=RegistrarPagamento(cobrancas, relogio),
    )


def criar_aplicacao(
    caminho_banco: str | None = None, relogio: Relogio | None = None
) -> FastAPI:
    banco = BancoSQLite(caminho_banco or os.getenv("COBRANCAS_DB", "cobrancas.db"))
    casos = montar_casos_de_uso(
        ContratoRepositorioSQLite(banco),
        CobrancaRepositorioSQLite(banco),
        relogio or RelogioSistema(),
    )
    return criar_app(casos)

