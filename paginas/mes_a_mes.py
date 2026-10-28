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

meses = sorted(m for m in val["competencia"].unique() if m <= ctx.comp)
linhas = []
for m in meses:
    h_tot = hierarquia(pd.Timestamp(m).strftime("%Y-%m-%d"))
    h = R.filtrar_visao(h_tot, ctx.nivel, ctx.nome)
    i, r = R.indicadores(h), R.indicadores(h_tot)
    linhas.append({"mes": pd.Timestamp(m), "carteira": i["carteira_calculo"], "preenchidas": i["preenchidas_calculo"],
                   "cobertura": i["cobertura"], "score": i["score"], "score_rede": r["score"]})
ev = pd.DataFrame(linhas)
ev["rot"] = ev["mes"].map(lambda m: R.rotulo_mes(m)[:3] + "/" + str(m.year)[2:])
vazio = ev["score"].isna()

if vazio.any():
    ui.destaque("<b>Meses sem preenchimento:</b> " + ", ".join(R.rotulo_mes(m) for m in ev.loc[vazio, "mes"])
                + ". Neles não há score, e a cobertura aparece como 0%.")

a, b = st.columns(2, gap="large")
with a:
    st.markdown("**Score médio**" + (" contra a rede" if ctx.nivel != "rede" else ""))
    fig = go.Figure()
    if ctx.nivel != "rede":
        fig.add_trace(go.Scatter(x=ev["rot"], y=ev["score_rede"], mode="lines", name="Rede",
                                 line=dict(color="#9a9a9a", dash="dot"), hovertemplate="%{x}<br>Rede: %{y:.1f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=ev["rot"], y=ev["score"], mode="lines+markers+text", name="Visão", connectgaps=False,
                             text=[ui.num(v, 1) if pd.notna(v) else "" for v in ev["score"]], textposition="top center",
                             line=dict(color=C.COR_LARANJA, width=3), hovertemplate="%{x}<br>Score: %{y:.1f}<extra></extra>"))
    if vazio.any():
        fig.add_trace(go.Scatter(x=ev.loc[vazio, "rot"], y=[4] * int(vazio.sum()), mode="markers+text", name="Sem preenchimento",
                                 marker=dict(symbol="x", size=11, color=ui.VERMELHO_CLARO), text=["sem preenchimento"] * int(vazio.sum()),
                                 textposition="top center", textfont=dict(color=ui.VERMELHO_CLARO, size=11),
                                 hovertemplate="%{x}: nenhuma loja preencheu<extra></extra>"))
    fig.update_layout(**ui.LAYOUT_GRAFICO, height=320, yaxis=dict(range=[0, 108], gridcolor="#3a3838"))
    ui.grafico(fig)
with b:
    st.markdown("**Cobertura**")
    cores = [ui.VERMELHO_CLARO if v else ui.cor_cobertura(c) for c, v in zip(ev["cobertura"], vazio)]
    textos = ["" if v else ui.pct(c, 0) for c, v in zip(ev["cobertura"], vazio)]
    fig = go.Figure(go.Bar(x=ev["rot"], y=ev["cobertura"].fillna(0), marker_color=cores, text=textos, textposition="outside",
                           customdata=list(zip(ev["preenchidas"], ev["carteira"])),
                           hovertemplate="%{x}<br>%{customdata[0]} de %{customdata[1]} lojas<extra></extra>"))
    for rot in ev.loc[vazio, "rot"]:
        fig.add_annotation(x=rot, y=0.03, text="sem<br>preenchimento", showarrow=False, yanchor="bottom",
                           font=dict(color=ui.VERMELHO_CLARO, size=11))
    fig.update_layout(**ui.LAYOUT_GRAFICO, height=320, yaxis=dict(range=[0, 1.18], tickformat=".0%", gridcolor="#3a3838"))
    ui.grafico(fig)
st.caption("Cobertura e score sem as lojas com supervisão especial de cada mês.")

st.markdown("**Lojas mês a mês** (score do último preenchimento de cada mês)")
h_sel = ctx.hier()
cods = h_sel["COD_LOJAS"]
mat = (val[val["COD_LOJAS"].isin(set(cods)) & (val["competencia"] <= ctx.comp)]
       .pivot_table(index="COD_LOJAS", columns="competencia", values="score", aggfunc="last"))
mat = mat.reindex(index=cods.values, columns=[pd.Timestamp(m) for m in meses])
mat.index = h_sel.set_index("COD_LOJAS").loc[mat.index, "LOJA"].values
mat.columns = [R.rotulo_mes(c)[:3] + "/" + str(c.year)[2:] for c in mat.columns]
mat = mat.sort_index()


def cor(v):
    if pd.isna(v):
        return "background-color:#3a3434; color:#b58a8a; font-style:italic"
    return f"background-color:{ui.cor_score(v)}; color:#fff; font-weight:600"


mat_txt = mat.map(lambda v: "sem dado" if pd.isna(v) else ui.num(v, 1))
st.dataframe(mat_txt.style.apply(lambda _: mat.map(cor), axis=None), use_container_width=True,
             height=min(38 * (len(mat) + 1), 720), column_config={"_index": st.column_config.TextColumn("Loja", width=300)})
st.caption("Verde: madura (acima de 70). Âmbar: em desenvolvimento. Vermelho: reativa (até 40). "
           "\"sem dado\": a loja não preencheu naquele mês.")
