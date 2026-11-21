"""Controladores HTTP. Não contêm SQL nem cálculos: apenas delegam aos casos de uso."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from ..application.casos_de_uso import (
    CadastrarContrato,
    CalcularCobranca,
    ConsultarContrato,
    EmitirCobranca,
    ListarCobrancasDoContrato,
    ListarContratos,
    RegistrarPagamento,
)
from ..application.dtos import NovoContratoDTO
from ..domain.excecoes import (
    ConflitoError,
    ErroDeDominio,
    NaoEncontradoError,
)
from .schemas import (
    CobrancaEntrada,
    CobrancaSaida,
    ContratoEntrada,
    ContratoSaida,
    DemonstrativoSaida,
    Erro,
    PagamentoEntrada,
)


@dataclass(frozen=True)
class CasosDeUso:
    cadastrar_contrato: CadastrarContrato
    consultar_contrato: ConsultarContrato
    listar_contratos: ListarContratos
    emitir_cobranca: EmitirCobranca
    listar_cobrancas: ListarCobrancasDoContrato
    calcular_cobranca: CalcularCobranca
    registrar_pagamento: RegistrarPagamento


_STATUS_POR_ERRO: list[tuple[type[ErroDeDominio], int]] = [
    (NaoEncontradoError, status.HTTP_404_NOT_FOUND),
    (ConflitoError, status.HTTP_409_CONFLICT),
]

_RESPOSTAS_ERRO = {
    404: {"model": Erro},
    409: {"model": Erro},
    422: {"description": "Dados inválidos ou regra de negócio violada"},
}


def criar_app(casos: CasosDeUso) -> FastAPI:
    app = FastAPI(
        title="API de Contratos e Cobranças",
        description="Protótipo em arquitetura em camadas: cadastro de contratos, "
        "emissão de cobranças e cálculo de multa e juros por atraso.",
        version="1.0.0",
    )

    @app.exception_handler(ErroDeDominio)
    async def tratar_erro_de_dominio(_: Request, erro: ErroDeDominio) -> JSONResponse:
        codigo = next(
            (c for tipo, c in _STATUS_POR_ERRO if isinstance(erro, tipo)),
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
        return JSONResponse(status_code=codigo, content={"detalhe": str(erro)})

    @app.post(
        "/contratos",
        response_model=ContratoSaida,
        status_code=status.HTTP_201_CREATED,
        responses=_RESPOSTAS_ERRO,
        tags=["Contratos"],
    )
    def cadastrar_contrato(entrada: ContratoEntrada) -> ContratoSaida:
        dto = casos.cadastrar_contrato.executar(NovoContratoDTO(**entrada.model_dump()))
        return ContratoSaida(**asdict(dto))

    @app.get("/contratos", response_model=list[ContratoSaida], tags=["Contratos"])
    def listar_contratos() -> list[ContratoSaida]:
        return [ContratoSaida(**asdict(d)) for d in casos.listar_contratos.executar()]

    @app.get(
        "/contratos/{contrato_id}",
        response_model=ContratoSaida,
        responses=_RESPOSTAS_ERRO,
        tags=["Contratos"],
    )
    def consultar_contrato(contrato_id: int) -> ContratoSaida:
        return ContratoSaida(**asdict(casos.consultar_contrato.executar(contrato_id)))

    @app.post(
        "/contratos/{contrato_id}/cobrancas",
        response_model=CobrancaSaida,
        status_code=status.HTTP_201_CREATED,
        responses=_RESPOSTAS_ERRO,
        tags=["Cobranças"],
    )
    def emitir_cobranca(contrato_id: int, entrada: CobrancaEntrada) -> CobrancaSaida:
        dto = casos.emitir_cobranca.executar(contrato_id, entrada.competencia)
        return CobrancaSaida(**asdict(dto))

    @app.get(
        "/contratos/{contrato_id}/cobrancas",
        response_model=list[CobrancaSaida],
        responses=_RESPOSTAS_ERRO,
        tags=["Cobranças"],
    )
    def listar_cobrancas(contrato_id: int) -> list[CobrancaSaida]:
        return [
            CobrancaSaida(**asdict(d))
            for d in casos.listar_cobrancas.executar(contrato_id)
        ]

    @app.get(
        "/cobrancas/{cobranca_id}/calculo",
        response_model=DemonstrativoSaida,
        responses=_RESPOSTAS_ERRO,
        tags=["Cobranças"],
    )
    def calcular_cobranca(
        cobranca_id: int, data_referencia: date | None = None
    ) -> DemonstrativoSaida:
        dto = casos.calcular_cobranca.executar(cobranca_id, data_referencia)
        return DemonstrativoSaida(**asdict(dto))

    @app.post(
        "/cobrancas/{cobranca_id}/pagamento",
        response_model=DemonstrativoSaida,
        responses=_RESPOSTAS_ERRO,
        tags=["Cobranças"],
    )
    def registrar_pagamento(
        cobranca_id: int, entrada: PagamentoEntrada | None = None
    ) -> DemonstrativoSaida:
        data = entrada.data_pagamento if entrada else None
        dto = casos.registrar_pagamento.executar(cobranca_id, data)
        return DemonstrativoSaida(**asdict(dto))

    return app
