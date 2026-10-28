import pandas as pd
import streamlit as st

from core import config as C
from core import dados
from core import regras as R
from core import ui

ctx = st.session_state["ctx"]
d = dados.carregar()
lojas = d["lojas"]
aus = R.ausencias(lojas, ctx.hoje.date())

ui.topo("Controle de férias", f"Situação em {ctx.hoje:%d/%m/%Y}")

if ctx.nivel == "regional":
    aus = aus[aus["regional"] == ctx.nome]
    lojas = lojas[lojas["REGIONAL"] == ctx.nome]
elif ctx.nivel == "coordenador":
    aus = aus[(aus["nome"] == ctx.nome) | ((aus["papel"] == "Regional") & aus["nome"].isin(lojas.loc[lojas["COORDENADOR"] == ctx.nome, "REGIONAL"]))]
    lojas = lojas[lojas["COORDENADOR"] == ctx.nome]

coord = aus[aus["papel"] == "Coordenador"]
reg = aus[aus["papel"] == "Regional"]
fora = lambda df: df[df["situacao_hoje"] != "Ativo"]
lojas = lojas.assign(ausencia=R.ausencia_por_loja(lojas, R.ausencias(d["lojas"], ctx.hoje.date())))

c = st.columns(5)
with c[0]:
    ui.card(len(fora(coord)), "Coordenadores ausentes hoje", cor=C.COR_AMBAR if len(fora(coord)) else "#4CAF50")
with c[1]:
    ui.card(int((coord["situacao_hoje"] == "Vaga aberta").sum()), "Vagas abertas", cor="#E5484D")
with c[2]:
    ui.card(len(fora(reg)), "Regionais ausentes hoje", cor=C.COR_AMBAR if len(fora(reg)) else "#4CAF50")
with c[3]:
    ui.card(int((lojas["ausencia"] != "Cobertura normal").sum()), "Lojas sem coordenador ou regional hoje", cor=C.COR_AMBAR)
with c[4]:
    ui.card(int((lojas["ausencia"] == "Coord + Regional ausentes").sum()), "Lojas sem os dois", cor="#E5484D")

CORES_SIT = {"Férias": C.COR_AMBAR, "Afastamento": "#E07020", "Maternidade": C.COR_AZUL,
             "Vaga aberta": C.COR_VERMELHO}


def tabela(df: pd.DataFrame):
    t = pd.DataFrame({
        "Nome": df["nome"].str.title(), "Lojas": df["lojas"], "Situação hoje": df["situacao_hoje"],
        "Retorno previsto": pd.to_datetime(df["retorno_previsto"]).dt.strftime("%d/%m/%Y").fillna(""),
        "Próxima ausência": pd.to_datetime(df["proxima_ausencia"]).dt.strftime("%d/%m/%Y").fillna(""),
        "Tipo": df["tipo_proxima"].fillna(""),
        "_dias": df["dias_ate_proxima"],
    }).sort_values(["Situação hoje", "_dias"], key=lambda s: s.map({"Ativo": 9}).fillna(0) if s.name == "Situação hoje" else s)
    t["Em quantos dias"] = t.pop("_dias").map(lambda v: "" if pd.isna(v) else str(int(v)))
    st.dataframe(ui.estilo_tabela(t, {"Situação hoje": CORES_SIT}), hide_index=True, use_container_width=True)


st.write("")
st.markdown("**Coordenadores**")
tabela(coord)
st.markdown("**Regionais**")
tabela(reg)
st.caption("Situação hoje pelas datas de início e retorno da aba de lojas. Status DEMITIDO aparece como vaga aberta.")
