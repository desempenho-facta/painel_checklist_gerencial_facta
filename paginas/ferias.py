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

ui.faixa(f"Situação de hoje, <b>{ctx.hoje:%d/%m/%Y}</b>, pelas datas de início e retorno da aba de lojas.", pin="Hoje")

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

n_vagas = int((coord["situacao_hoje"] == "Vaga aberta").sum())
n_sem = int((lojas["ausencia"] != "Cobertura normal").sum())
n_dois = int((lojas["ausencia"] == "Coord + Regional ausentes").sum())
ui.cards([
    dict(numero=len(fora(coord)), rotulo="Coordenadores ausentes", sub=f"de {len(coord)} coordenadores",
         cor=C.COR_AMBAR if len(fora(coord)) else ui.VERDE_CLARO),
    dict(numero=n_vagas, rotulo="Vagas abertas", sub="coordenador desligado",
         cor=ui.VERMELHO_CLARO if n_vagas else ui.VERDE_CLARO),
    dict(numero=len(fora(reg)), rotulo="Regionais ausentes", sub=f"de {len(reg)} regionais",
         cor=C.COR_AMBAR if len(fora(reg)) else ui.VERDE_CLARO),
    dict(numero=n_sem, rotulo="Lojas descobertas", sub="sem coordenador ou regional",
         cor=C.COR_AMBAR if n_sem else ui.VERDE_CLARO),
    dict(numero=n_dois, rotulo="Lojas sem os dois", sub="coordenador e regional fora",
         cor=ui.VERMELHO_CLARO if n_dois else ui.VERDE_CLARO),
], minimo=170)

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
    st.dataframe(ui.estilo_tabela(t, {"Situação hoje": CORES_SIT}), hide_index=True, use_container_width=True,
                 column_config={"Nome": st.column_config.TextColumn(width=280)})


st.write("")
st.markdown("**Coordenadores**")
tabela(coord)
st.markdown("**Regionais**")
tabela(reg)
st.caption("Status DEMITIDO na aba de lojas aparece como vaga aberta.")
