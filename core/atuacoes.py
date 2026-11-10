"""
Atuação da monitoria nos chamados e nas demandas sem chamado da Q36.

Cada registro vira uma linha na aba Atuacoes_Chamados (histórico completo); a situação
atual de um chamado é o registro mais recente da chave dele. Só o app da monitoria grava.

Chaves:
    CH|<cod_loja>|<nº do chamado>               o mesmo chamado informado em meses seguintes mantém a atuação
    SC|<cod_loja>|<data e hora do checklist>|<n> cada demanda sem chamado de um preenchimento

Produção: Google Sheets pela conta de serviço, com permissão de escrita (a conta precisa ser
editora da planilha). Desenvolvimento: Atuacoes_Chamados.csv na pasta de CHECKLIST_DADOS_DIR.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

from . import config as C


def chave_chamado(cod_loja: str, chamado: str) -> str:
    return f"CH|{cod_loja}|{chamado}"


def chave_demanda(cod_loja: str, timestamp: pd.Timestamp, item: int) -> str:
    return f"SC|{cod_loja}|{pd.Timestamp(timestamp):%Y%m%d%H%M%S}|{item}"


def _pasta_csv() -> Path | None:
    pasta = os.environ.get("CHECKLIST_DADOS_DIR")
    return Path(pasta) if pasta else None


def _aba():
    import gspread
    from google.oauth2.service_account import Credentials

    cred = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]),
                                                 scopes=["https://www.googleapis.com/auth/spreadsheets"])
    planilha = gspread.authorize(cred).open_by_key(st.secrets["SHEET_ID"])
    try:
        return planilha.worksheet(C.ABA_ATUACOES)
    except gspread.WorksheetNotFound:
        aba = planilha.add_worksheet(title=C.ABA_ATUACOES, rows=1000, cols=len(C.COLUNAS_ATUACOES))
        aba.append_row(C.COLUNAS_ATUACOES)
        return aba


@st.cache_data(ttl=120, show_spinner=False)
def _ler_tudo() -> pd.DataFrame:
    pasta = _pasta_csv()
    if pasta:
        arq = pasta / f"{C.ABA_ATUACOES}.csv"
        if not arq.exists():
            return pd.DataFrame(columns=C.COLUNAS_ATUACOES)
        return pd.read_csv(arq, dtype=str, keep_default_na=False)
    valores = _aba().get_all_values()
    if not valores:
        return pd.DataFrame(columns=C.COLUNAS_ATUACOES)
    return pd.DataFrame(valores[1:], columns=valores[0])


def atuais() -> pd.DataFrame:
    """Registro mais recente de cada chave, indexado pela chave. Vazio se a aba não existe ou falhou."""
    try:
        df = _ler_tudo()
    except Exception:
        return pd.DataFrame(columns=C.COLUNAS_ATUACOES).set_index("chave")
    for col in C.COLUNAS_ATUACOES:
        if col not in df.columns:
            df[col] = ""
    df = df[df["chave"].astype(str).str.strip() != ""]
    return df.sort_values("registrado_em").drop_duplicates("chave", keep="last").set_index("chave")


def salvar(registros: list[dict]) -> None:
    """Acrescenta os registros (dicionários com as colunas de C.COLUNAS_ATUACOES) e limpa o cache."""
    if not registros:
        return
    agora = pd.Timestamp.now(tz=C.FUSO).strftime("%Y-%m-%d %H:%M:%S")
    linhas = [[agora if c == "registrado_em" else str(r.get(c, "")) for c in C.COLUNAS_ATUACOES] for r in registros]
    pasta = _pasta_csv()
    if pasta:
        arq = pasta / f"{C.ABA_ATUACOES}.csv"
        novo = pd.DataFrame(linhas, columns=C.COLUNAS_ATUACOES)
        if arq.exists():
            novo = pd.concat([pd.read_csv(arq, dtype=str, keep_default_na=False), novo], ignore_index=True)
        novo.to_csv(arq, index=False)
    else:
        _aba().append_rows(linhas, value_input_option="RAW")
    _ler_tudo.clear()
