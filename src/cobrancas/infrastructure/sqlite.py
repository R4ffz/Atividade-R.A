"""Repositórios persistidos em SQLite.

Toda a tradução entre linhas da tabela e entidades do domínio fica aqui;
nenhuma outra camada conhece SQL.
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import date
from decimal import Decimal

from ..domain.entidades import Cobranca, Contrato, StatusCobranca
from ..domain.repositorios import CobrancaRepositorio, ContratoRepositorio
from ..domain.valores import Competencia, Dinheiro, Documento

ESQUEMA = """
CREATE TABLE IF NOT EXISTS contratos (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_nome     TEXT    NOT NULL,
    cliente_documento TEXT   NOT NULL,
    descricao        TEXT    NOT NULL,
    valor_mensal     TEXT    NOT NULL,
    dia_vencimento   INTEGER NOT NULL,
    data_inicio      TEXT    NOT NULL,
    data_fim         TEXT    NOT NULL,
    percentual_multa TEXT    NOT NULL,
    juros_mensal     TEXT    NOT NULL
);
CREATE TABLE IF NOT EXISTS cobrancas (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    contrato_id      INTEGER NOT NULL REFERENCES contratos(id),
    competencia      TEXT    NOT NULL,
    data_vencimento  TEXT    NOT NULL,
    valor_original   TEXT    NOT NULL,
    percentual_multa TEXT    NOT NULL,
    juros_mensal     TEXT    NOT NULL,
    status           TEXT    NOT NULL,
    data_pagamento   TEXT,
    valor_pago       TEXT,
    UNIQUE (contrato_id, competencia)
);
"""


class BancoSQLite:
    def __init__(self, caminho: str = ":memory:") -> None:
        self.conexao = sqlite3.connect(caminho, check_same_thread=False)
        self.conexao.row_factory = sqlite3.Row
        self.conexao.execute("PRAGMA foreign_keys = ON")
        self.trava = threading.Lock()
        with self.trava, self.conexao:
            self.conexao.executescript(ESQUEMA)


def _data(texto: str | None) -> date | None:
    return date.fromisoformat(texto) if texto else None


class ContratoRepositorioSQLite(ContratoRepositorio):
    def __init__(self, banco: BancoSQLite) -> None:
        self._banco = banco

    @staticmethod
    def _para_entidade(linha: sqlite3.Row) -> Contrato:
        return Contrato(
            id=linha["id"],
            cliente_nome=linha["cliente_nome"],
            cliente_documento=Documento(linha["cliente_documento"]),
            descricao=linha["descricao"],
            valor_mensal=Dinheiro(Decimal(linha["valor_mensal"])),
            dia_vencimento=linha["dia_vencimento"],
            data_inicio=date.fromisoformat(linha["data_inicio"]),
            data_fim=date.fromisoformat(linha["data_fim"]),
            percentual_multa=Decimal(linha["percentual_multa"]),
            juros_mensal=Decimal(linha["juros_mensal"]),
        )

    def salvar(self, contrato: Contrato) -> Contrato:
        valores = (
            contrato.cliente_nome,
            contrato.cliente_documento.numero,
            contrato.descricao,
            str(contrato.valor_mensal.valor),
            contrato.dia_vencimento,
            contrato.data_inicio.isoformat(),
            contrato.data_fim.isoformat(),
            str(contrato.percentual_multa),
            str(contrato.juros_mensal),
        )
        with self._banco.trava, self._banco.conexao as con:
            if contrato.id is None:
                cursor = con.execute(
                    """INSERT INTO contratos (cliente_nome, cliente_documento, descricao,
                       valor_mensal, dia_vencimento, data_inicio, data_fim,
                       percentual_multa, juros_mensal) VALUES (?,?,?,?,?,?,?,?,?)""",
                    valores,
                )
                contrato.id = cursor.lastrowid
            else:
                con.execute(
                    """UPDATE contratos SET cliente_nome=?, cliente_documento=?, descricao=?,
                       valor_mensal=?, dia_vencimento=?, data_inicio=?, data_fim=?,
                       percentual_multa=?, juros_mensal=? WHERE id=?""",
                    (*valores, contrato.id),
                )
        return contrato

    def buscar_por_id(self, contrato_id: int) -> Contrato | None:
        with self._banco.trava:
            linha = self._banco.conexao.execute(
                "SELECT * FROM contratos WHERE id = ?", (contrato_id,)
            ).fetchone()
        return self._para_entidade(linha) if linha else None

    def listar(self) -> list[Contrato]:
        with self._banco.trava:
            linhas = self._banco.conexao.execute(
                "SELECT * FROM contratos ORDER BY id"
            ).fetchall()
        return [self._para_entidade(l) for l in linhas]


class CobrancaRepositorioSQLite(CobrancaRepositorio):
    def __init__(self, banco: BancoSQLite) -> None:
        self._banco = banco

    @staticmethod
    def _para_entidade(linha: sqlite3.Row) -> Cobranca:
        return Cobranca(
            id=linha["id"],
            contrato_id=linha["contrato_id"],
            competencia=Competencia.parse(linha["competencia"]),
            data_vencimento=date.fromisoformat(linha["data_vencimento"]),
            valor_original=Dinheiro(Decimal(linha["valor_original"])),
            percentual_multa=Decimal(linha["percentual_multa"]),
            juros_mensal=Decimal(linha["juros_mensal"]),
            status=StatusCobranca(linha["status"]),
            data_pagamento=_data(linha["data_pagamento"]),
            valor_pago=Dinheiro(Decimal(linha["valor_pago"])) if linha["valor_pago"] else None,
        )

    def salvar(self, cobranca: Cobranca) -> Cobranca:
        valores = (
            cobranca.contrato_id,
            str(cobranca.competencia),
            cobranca.data_vencimento.isoformat(),
            str(cobranca.valor_original.valor),
            str(cobranca.percentual_multa),
            str(cobranca.juros_mensal),
            cobranca.status.value,
            cobranca.data_pagamento.isoformat() if cobranca.data_pagamento else None,
            str(cobranca.valor_pago.valor) if cobranca.valor_pago else None,
        )
        with self._banco.trava, self._banco.conexao as con:
            if cobranca.id is None:
                cursor = con.execute(
                    """INSERT INTO cobrancas (contrato_id, competencia, data_vencimento,
                       valor_original, percentual_multa, juros_mensal, status,
                       data_pagamento, valor_pago) VALUES (?,?,?,?,?,?,?,?,?)""",
                    valores,
                )
                cobranca.id = cursor.lastrowid
            else:
                con.execute(
                    """UPDATE cobrancas SET contrato_id=?, competencia=?, data_vencimento=?,
                       valor_original=?, percentual_multa=?, juros_mensal=?, status=?,
                       data_pagamento=?, valor_pago=? WHERE id=?""",
                    (*valores, cobranca.id),
                )
        return cobranca

    def buscar_por_id(self, cobranca_id: int) -> Cobranca | None:
        with self._banco.trava:
            linha = self._banco.conexao.execute(
                "SELECT * FROM cobrancas WHERE id = ?", (cobranca_id,)
            ).fetchone()
        return self._para_entidade(linha) if linha else None

    def buscar_por_competencia(
        self, contrato_id: int, competencia: Competencia
    ) -> Cobranca | None:
        with self._banco.trava:
            linha = self._banco.conexao.execute(
                "SELECT * FROM cobrancas WHERE contrato_id = ? AND competencia = ?",
                (contrato_id, str(competencia)),
            ).fetchone()
        return self._para_entidade(linha) if linha else None

    def listar_por_contrato(self, contrato_id: int) -> list[Cobranca]:
        with self._banco.trava:
            linhas = self._banco.conexao.execute(
                "SELECT * FROM cobrancas WHERE contrato_id = ? ORDER BY competencia",
                (contrato_id,),
            ).fetchall()
        return [self._para_entidade(l) for l in linhas]
