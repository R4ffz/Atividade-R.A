"""Objetos de valor do domínio: Dinheiro, Documento (CPF/CNPJ) e Competência."""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from .excecoes import ValidacaoError

CENTAVO = Decimal("0.01")


def para_decimal(valor: object) -> Decimal:
    """Converte para Decimal evitando imprecisões de float."""
    if isinstance(valor, Decimal):
        resultado = valor
    else:
        if isinstance(valor, float):
            valor = repr(valor)
        try:
            resultado = Decimal(str(valor))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidacaoError(f"Valor numérico inválido: {valor!r}") from None
    if not resultado.is_finite():
        raise ValidacaoError(f"Valor numérico inválido: {valor!r}")
    return resultado


@dataclass(frozen=True, order=True)
class Dinheiro:
    """Valor monetário em reais, sempre arredondado em centavos (half-up)."""

    valor: Decimal

    def __post_init__(self) -> None:
        normalizado = para_decimal(self.valor).quantize(CENTAVO, rounding=ROUND_HALF_UP)
        object.__setattr__(self, "valor", normalizado)

    @classmethod
    def zero(cls) -> Dinheiro:
        return cls(Decimal("0"))

    def __add__(self, outro: Dinheiro) -> Dinheiro:
        return Dinheiro(self.valor + outro.valor)

    def e_positivo(self) -> bool:
        return self.valor > 0

    def __str__(self) -> str:
        return f"R$ {self.valor:.2f}"


def _digito_verificador(numeros: str, pesos: list[int]) -> int:
    soma = sum(int(n) * p for n, p in zip(numeros, pesos))
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


def cpf_valido(cpf: str) -> bool:
    if len(cpf) != 11 or not cpf.isdigit() or cpf == cpf[0] * 11:
        return False
    d1 = _digito_verificador(cpf[:9], list(range(10, 1, -1)))
    d2 = _digito_verificador(cpf[:10], list(range(11, 1, -1)))
    return cpf[-2:] == f"{d1}{d2}"


def cnpj_valido(cnpj: str) -> bool:
    if len(cnpj) != 14 or not cnpj.isdigit() or cnpj == cnpj[0] * 14:
        return False
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6] + pesos1
    d1 = _digito_verificador(cnpj[:12], pesos1)
    d2 = _digito_verificador(cnpj[:13], pesos2)
    return cnpj[-2:] == f"{d1}{d2}"


@dataclass(frozen=True)
class Documento:
    """CPF ou CNPJ do cliente, armazenado apenas com dígitos."""

    numero: str

    def __post_init__(self) -> None:
        digitos = re.sub(r"\D", "", self.numero or "")
        if len(digitos) == 11 and cpf_valido(digitos):
            pass
        elif len(digitos) == 14 and cnpj_valido(digitos):
            pass
        else:
            raise ValidacaoError(f"Documento inválido (CPF/CNPJ): {self.numero!r}")
        object.__setattr__(self, "numero", digitos)

    @property
    def tipo(self) -> str:
        return "CPF" if len(self.numero) == 11 else "CNPJ"

    def __str__(self) -> str:
        n = self.numero
        if self.tipo == "CPF":
            return f"{n[:3]}.{n[3:6]}.{n[6:9]}-{n[9:]}"
        return f"{n[:2]}.{n[2:5]}.{n[5:8]}/{n[8:12]}-{n[12:]}"


@dataclass(frozen=True, order=True)
class Competencia:
    """Mês/ano de referência de uma cobrança (formato AAAA-MM)."""

    ano: int
    mes: int

    def __post_init__(self) -> None:
        if not 1 <= self.mes <= 12:
            raise ValidacaoError(f"Mês de competência inválido: {self.mes}")
        if not 2000 <= self.ano <= 2100:
            raise ValidacaoError(f"Ano de competência inválido: {self.ano}")

    @classmethod
    def parse(cls, texto: str) -> Competencia:
        correspondencia = re.fullmatch(r"(\d{4})-(\d{2})", (texto or "").strip())
        if not correspondencia:
            raise ValidacaoError(f"Competência deve estar no formato AAAA-MM: {texto!r}")
        return cls(int(correspondencia.group(1)), int(correspondencia.group(2)))

    @property
    def primeiro_dia(self) -> date:
        return date(self.ano, self.mes, 1)

    @property
    def ultimo_dia(self) -> date:
        return date(self.ano, self.mes, calendar.monthrange(self.ano, self.mes)[1])

    def __str__(self) -> str:
        return f"{self.ano:04d}-{self.mes:02d}"
