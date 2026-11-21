"""Garante as regras de dependência entre as camadas.

* domain: não importa nenhuma outra camada nem frameworks (web/banco).
* application: importa apenas o domínio.
* presentation: não acessa a infraestrutura diretamente.
"""

import ast
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2] / "src" / "cobrancas"

PROIBIDOS = {
    "domain": {"fastapi", "pydantic", "starlette", "sqlite3", "sqlalchemy",
               "application", "infrastructure", "presentation", "main"},
    "application": {"fastapi", "pydantic", "starlette", "sqlite3", "sqlalchemy",
                    "infrastructure", "presentation", "main"},
    "presentation": {"sqlite3", "sqlalchemy", "infrastructure", "main"},
}


def modulos_importados(arquivo: Path) -> set[str]:
    nomes: set[str] = set()
    for no in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
        if isinstance(no, ast.Import):
            for alias in no.names:
                nomes.update(alias.name.split("."))
        elif isinstance(no, ast.ImportFrom) and no.module:
            nomes.update(no.module.split("."))
    return nomes


@pytest.mark.parametrize("camada", sorted(PROIBIDOS))
def test_camada_respeita_dependencias(camada):
    violacoes = {
        arquivo.name: sorted(modulos_importados(arquivo) & PROIBIDOS[camada])
        for arquivo in (RAIZ / camada).glob("*.py")
    }
    violacoes = {k: v for k, v in violacoes.items() if v}
    assert not violacoes, f"Camada '{camada}' com dependências proibidas: {violacoes}"
