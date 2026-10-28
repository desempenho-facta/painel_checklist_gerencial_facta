import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import config as C
from core import dados
from core import regras as R
from core import ui
from core.contexto import hierarquia

ctx = st.session_state["ctx"]
d = dados.carregar()
val = d["validos"]

ui.topo("Mês a mês", ctx.rotulo_visao)

meses = sorted(m for m in val["competencia"].unique() if m <= ctx.comp)
linhas = []
for m in meses:
    h_tot = hierarquia(pd.Timestamp(m).strftime("%Y-%m-%d"))
    h = R.filtrar_visao(h_tot, ctx.nivel, ctx.nome)
    i, r = R.indicadores(h), R.indicadores(h_tot)
    linhas.append({"mes": pd.Timestamp(m), "carteira": i["carteira"], "preenchidas": i["preenchidas"],
                   "cobertura": i["cobertura"], "score": i["score"], "score_rede": r["score"],
                   "maduras": i["pct_maduras"], "risco_critico": i["risco_critico"]})
ev = pd.DataFrame(linhas)
ev["rot"] = ev["mes"].map(lambda m: R.rotulo_mes(m)[:3] + "/" + str(m.year)[2:])

a, b = st.columns(2)
with a:
    st.markdown("**Score médio**" + (" contra a rede" if ctx.nivel != "rede" else ""))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ev["rot"], y=ev["score"], mode="lines+markers+text", name="Visão",
                             text=[ui.num(v, 1) for v in ev["score"]], textposition="top center",
                             line=dict(color=C.COR_LARANJA, width=3)))
    if ctx.nivel != "rede":
        fig.add_trace(go.Scatter(x=ev["rot"], y=ev["score_rede"], mode="lines", name="Rede",
                                 line=dict(color="#888", dash="dot")))
    fig.update_layout(**ui.LAYOUT_GRAFICO, height=300, yaxis=dict(range=[0, 105]))
    st.plotly_chart(fig, use_container_width=True)
with b:
    st.markdown("**Cobertura**")
    fig = go.Figure(go.Bar(x=ev["rot"], y=ev["cobertura"], marker_color=[ui.cor_cobertura(v) for v in ev["cobertura"]],
                           text=[ui.pct(v, 0) for v in ev["cobertura"]], textposition="outside"))
    fig.update_layout(**ui.LAYOUT_GRAFICO, height=300, yaxis=dict(range=[0, 1.15], tickformat=".0%"))
    st.plotly_chart(fig, use_container_width=True)
st.caption("Cobertura e score sem as lojas com supervisão especial de cada mês.")

st.markdown("**Lojas mês a mês (score do último preenchimento de cada mês)**")
h_sel = ctx.hier()
cods = h_sel["COD_LOJAS"]
mat = (val[val["COD_LOJAS"].isin(set(cods)) & (val["competencia"] <= ctx.comp)]
       .pivot_table(index="COD_LOJAS", columns="competencia", values="score", aggfunc="last"))
mat = mat.reindex(cods.values)
mat.index = h_sel.set_index("COD_LOJAS").loc[mat.index, "LOJA"].values
mat.columns = [R.rotulo_mes(c)[:3] + "/" + str(c.year)[2:] for c in mat.columns]
mat = mat.sort_index()


def cor(v):
    if pd.isna(v):
        return "background-color:#2a2a2a; color:#666"
    c = ui.cor_score(v)
    return f"background-color:{c}; color:#fff; font-weight:600"


mat_txt = mat.map(lambda v: "" if pd.isna(v) else ui.num(v, 1))
st.dataframe(mat_txt.style.apply(lambda _: mat.map(cor), axis=None),
             use_container_width=True, height=min(38 * (len(mat) + 1), 720))
st.caption("Verde: madura (acima de 70). Âmbar: em desenvolvimento. Vermelho: reativa (até 40). Cinza: sem preenchimento no mês.")
