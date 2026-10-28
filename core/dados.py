"""
Leitura dos dados do checklist.

Produção: Google Sheets pela conta de serviço (gspread), lendo as colunas
pelo nome do cabeçalho. Desenvolvimento: CSVs locais apontados pela
variável de ambiente CHECKLIST_DADOS_DIR (Respostas.csv e Lojas.csv).
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

from . import regras


def _ler_planilha() -> tuple[pd.DataFrame, pd.DataFrame]:
    import gspread
    from google.oauth2.service_account import Credentials

    escopos = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    cred = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=escopos)
    planilha = gspread.authorize(cred).open_by_key(st.secrets["SHEET_ID"])

    def aba(nome: str) -> pd.DataFrame:
        valores = planilha.worksheet(nome).get_all_values()
        cab, linhas = valores[0], valores[1:]
        return pd.DataFrame(linhas, columns=cab)

    # Aceita o mesmo bloco de secrets do app do formulário (SHEET_ID, gcp_service_account, NOME_ABA).
    aba_resp = st.secrets.get("ABA_RESPOSTAS") or st.secrets.get("NOME_ABA") or "Respostas"
    aba_lojas = st.secrets.get("ABA_LOJAS") or "Hierarquia"
    return aba(aba_resp), aba(aba_lojas)


def _ler_csv(pasta: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    ler = lambda n: pd.read_csv(pasta / n, dtype=str, keep_default_na=False)
    return ler("Respostas.csv"), ler("Lojas.csv")


def aplicar_secrets() -> None:
    """Lê dos secrets os ajustes que têm nomes reais e por isso não ficam no código público."""
    from . import config as C
    try:
        alias = st.secrets.get("ALIAS_COORDENADOR", {})
        casos = st.secrets.get("SUPERVISAO_ESPECIAL_CASOS", [])
    except Exception:          # sem secrets (testes ou arquivos locais)
        return
    C.ALIAS_COORDENADOR.update({str(k).upper(): str(v).upper() for k, v in dict(alias).items()})
    C.SUPERVISAO_ESPECIAL_CASOS.update((str(c), str(d)) for c, d in casos)


@st.cache_data(ttl=600, show_spinner="Carregando os preenchimentos...")
def carregar() -> dict:
    aplicar_secrets()
    pasta = os.environ.get("CHECKLIST_DADOS_DIR")
    if pasta:
        resp, lojas = _ler_csv(Path(pasta))
        origem = f"arquivos locais ({pasta})"
    else:
        resp, lojas = _ler_planilha()
        origem = "Google Sheets"
    respostas = regras.preparar_respostas(resp)
    lojas = regras.preparar_lojas(lojas)
    return {
        "respostas": respostas,
        "validos": regras.validos(respostas),
        "lojas": lojas,
        "origem": origem,
        "carregado_em": pd.Timestamp.now(tz="America/Sao_Paulo"),
    }
