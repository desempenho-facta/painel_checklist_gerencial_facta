import pandas as pd
import streamlit as st

from core import config as C
from core import ui

ctx = st.session_state["ctx"]
h = ctx.hier().copy()

f1, f2, f3, f4 = st.columns([1, 1, 1, 0.8], vertical_alignment="bottom")
status = f1.multiselect("Situação", list(ui.CORES_STATUS), placeholder="Todas", help=C.AJUDA["status"])
matur = f2.multiselect("Maturidade", list(ui.CORES_MATURIDADE), placeholder="Todas", help=C.AJUDA["maturidade"])
risco = f3.multiselect("Nível de risco", list(ui.CORES_RISCO), placeholder="Todos", help=C.AJUDA["risco"])
so_esp = f4.toggle("Só supervisão especial", help=C.AJUDA["supervisao_especial"])

if status:
    h = h[h["status"].isin(status)]
if matur:
    h = h[h["maturidade"].isin(matur)]
if risco:
    h = h[h["risco"].isin(risco)]
if so_esp:
    h = h[h["supervisao_especial"]]

tab = pd.DataFrame({
    "Loja": h["LOJA"],
    "Coordenador": h["coordenador_mes"].str.title(),
    "Supervisor": h["SUPERVISOR"].fillna("").str.title(),
    "Situação": h["status"],
    "Supervisão especial": h["supervisao_especial"].map({True: "Sim", False: ""}),
    "Score": h["score"].round(2),
    "Maturidade": h["maturidade"].fillna(""),
    "Ciclo": h["ciclo"].fillna(""),
    "Quadrante do treino": h["quadrante"].fillna(""),
    "Risco": h["risco"].fillna(""),
    "Estrutura (Q36)": h["estrutura"].fillna(""),
    "Preenchido em": pd.to_datetime(h["timestamp"]).dt.strftime("%d/%m/%Y %H:%M").fillna(""),
})
ordem = {"Não preencheu": 0, "Nunca preencheu": 1, "Loja nova": 2, "Preencheu": 3}
tab = tab.assign(_o=tab["Situação"].map(ordem)).sort_values(["_o", "Score"], ascending=[True, False]).drop(columns="_o")

st.caption(f"{len(tab)} lojas. Passe o cursor no nome das colunas para ver o que cada nomenclatura significa. "
           "No celular, arraste a tabela para o lado.")
tab_txt = tab.assign(Score=tab["Score"].map(lambda v: "" if pd.isna(v) else ui.num(v)))
estilo = ui.estilo_tabela(tab_txt, {
    "Situação": ui.CORES_STATUS, "Maturidade": ui.CORES_MATURIDADE, "Risco": ui.CORES_RISCO,
    "Supervisão especial": {"Sim": C.COR_LARANJA},
    "Estrutura (Q36)": {"Com chamados abertos": C.COR_VERDE, "Sem chamados abertos": C.COR_VERMELHO},
})
st.dataframe(
    estilo, hide_index=True, use_container_width=True, height=min(38 * (len(tab) + 1), 720),
    column_config={
        "Loja": st.column_config.TextColumn(width=300, pinned=True),
        "Coordenador": st.column_config.TextColumn(width=260, help="Coordenador da loja naquele mês."),
        "Supervisor": st.column_config.TextColumn(width=240),
        "Situação": st.column_config.TextColumn(width=130, help=C.AJUDA["status"]),
        "Supervisão especial": st.column_config.TextColumn(width=150, help=C.AJUDA["supervisao_especial"]),
        "Score": st.column_config.TextColumn(width=80, help=C.AJUDA["score"]),
        "Maturidade": st.column_config.TextColumn(width=160, help=C.AJUDA["maturidade"]),
        "Ciclo": st.column_config.TextColumn(width=220, help=C.AJUDA["ciclo"]),
        "Quadrante do treino": st.column_config.TextColumn(width=160, help=C.AJUDA["quadrante"]),
        "Risco": st.column_config.TextColumn(width=120, help=C.AJUDA["risco"]),
        "Estrutura (Q36)": st.column_config.TextColumn(width=190, help=C.AJUDA["estrutura"]),
        "Preenchido em": st.column_config.TextColumn(width=140),
    },
)
