"""Exceções de negócio, independentes de protocolo (HTTP, CLI, etc.)."""


class ErroDeDominio(Exception):
    """Base para todos os erros de negócio."""


class ValidacaoError(ErroDeDominio):
    """Dados de entrada que violam uma regra de validação."""


class RegraDeNegocioError(ErroDeDominio):
    """Operação válida sintaticamente, mas proibida pelas regras de negócio."""


class ConflitoError(ErroDeDominio):
    """Operação conflita com o estado atual (ex.: duplicidade, já paga)."""


class NaoEncontradoError(ErroDeDominio):
    """Recurso solicitado não existe."""
