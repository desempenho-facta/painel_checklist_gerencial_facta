import pandas as pd
import streamlit as st

from core import config as C
from core import dados
from core import regras as R
from core import ui

ctx = st.session_state["ctx"]
d = dados.carregar()
h = ctx.hier()
pre = h[h["status"] == "Preencheu"]

ui.topo("Casos graves", f"{ctx.rotulo_visao} · {R.rotulo_mes(ctx.comp)}")
ui.faixa("Loja em caso grave: o preenchimento do mês tem pelo menos um destes sinais: "
         f"<b>{', '.join(C.SINAIS_GRAVES)}</b>. O tempo conta os preenchimentos seguidos com o sinal; "
         "mês sem preenchimento não zera a contagem.", pin="Regra")

if pre.empty:
    st.info("Nenhum preenchimento neste mês para esta visão.")
    st.stop()

g = R.casos_graves(d["validos"], ctx.comp)
g = g[g["COD_LOJAS"].isin(set(pre["COD_LOJAS"]))]
g = g.merge(pre[["COD_LOJAS", "LOJA", "coordenador_mes", "score", "supervisao_especial"]], on="COD_LOJAS")

c = st.columns(4)
with c[0]:
    ui.card(len(g), "Lojas em caso grave", ui.pct(len(g) / len(pre), 0) + " das que preencheram", cor=C.COR_VERMELHO)
with c[1]:
    n3 = int((g["preenchimentos_seguidos"] >= 3).sum())
    ui.card(n3, "Há 3 preenchimentos ou mais", "casos que não estão saindo", cor=C.COR_VERMELHO if n3 else "#4CAF50")
with c[2]:
    ui.card(int((g["qtd_sinais"] >= 3).sum()), "Com 3 sinais ou mais", "situação mais pesada", cor=C.COR_AMBAR)
with c[3]:
    novos = int((g["preenchimentos_seguidos"] == 1).sum())
    ui.card(novos, "Entraram neste mês", "primeiro preenchimento com sinal", cor=C.COR_AMBAR)

st.write("")
st.markdown("**Quantas lojas carregam cada sinal**")
contagem = {s: int(g["sinais"].map(lambda l, s=s: s in l).sum()) for s in C.SINAIS_GRAVES}
st.plotly_chart(ui.barras_h(list(contagem.values()), list(contagem), [C.COR_VERMELHO] * len(contagem),
                            altura=60 + 38 * len(contagem)), use_container_width=True)

st.markdown("**Lojas em caso grave** (as que estão há mais tempo primeiro)")
filtro = st.multiselect("Sinal", list(C.SINAIS_GRAVES), placeholder="Todos os sinais")
if filtro:
    g = g[g["sinais"].map(lambda l: any(s in l for s in filtro))]


def descreve(por_sinal: dict) -> str:
    return " · ".join(f"{s} ({n} {'seguido' if n == 1 else 'seguidos'})" for s, n in por_sinal.items())


tab = pd.DataFrame({
    "Loja": g["LOJA"],
    "Coordenador": g["coordenador_mes"].str.title(),
    "Em caso grave há": g["preenchimentos_seguidos"].map(lambda n: f"{n} {'preenchimento' if n == 1 else 'preenchimentos'}"),
    "Desde": g["desde"].map(lambda m: R.rotulo_mes(m)[:3] + "/" + str(m.year)[2:]),
    "Sinais": g["qtd_sinais"].astype(str),
    "Quais sinais e há quanto tempo": g["por_sinal"].map(descreve),
    "Score": g["score"].map(ui.num),
    "Supervisão especial": g["supervisao_especial"].map({True: "Sim", False: ""}),
    "_t": g["preenchimentos_seguidos"], "_s": g["qtd_sinais"],
}).sort_values(["_t", "_s"], ascending=False).drop(columns=["_t", "_s"])

st.dataframe(ui.estilo_tabela(tab, {"Supervisão especial": {"Sim": C.COR_LARANJA}}), hide_index=True,
             use_container_width=True, height=min(38 * (len(tab) + 1), 720),
             column_config={"Em caso grave há": st.column_config.TextColumn(
                 help="Preenchimentos seguidos com pelo menos um sinal grave, mesmo que o sinal tenha mudado no caminho."),
                 "Quais sinais e há quanto tempo": st.column_config.TextColumn(
                 help="Sinais do preenchimento do mês e há quantos preenchimentos seguidos cada um aparece.")})
st.caption("Abra o Diagnóstico da loja para ver as respostas que levaram a cada sinal.")
