import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import config as C
from core import ui

ctx = st.session_state["ctx"]
h = ctx.hier()
pre = h[(h["status"] == "Preencheu") & h["conta"]]

if pre.empty:
    st.info("Nenhum preenchimento que conte neste mês para esta visão.")
    st.stop()

QUADRANTES = {"Treina e domina": C.COR_VERDE, "Talento natural": C.COR_AZUL,
              "Treino ineficaz": C.COR_AMBAR, "Crítico": C.COR_VERMELHO}
EXPLICA_Q = {"Treina e domina": "treina (Treinar 60% ou mais) e a equipe domina o método",
             "Talento natural": "a equipe domina o método, mas a loja treina pouco",
             "Treino ineficaz": "treina, mas o treino ainda não virou domínio do método",
             "Crítico": "treina pouco e a equipe não domina o método"}
CICLOS = {"Ciclo fechado": C.COR_VERDE, "Esforço sem acompanhamento": C.COR_AMBAR,
          "Exige sem preparar": "#E07020", "Ciclo frágil": C.COR_VERMELHO}
EXPLICA_C = {"Ciclo fechado": "Treinar, Verificar e Acompanhar com 60% ou mais",
             "Esforço sem acompanhamento": "treina, mas não verifica nem acompanha",
             "Exige sem preparar": "verifica ou acompanha sem treinar",
             "Ciclo frágil": "Treinar, Verificar e Acompanhar abaixo de 60%"}

ui.faixa(f"<b>{len(pre)} lojas</b> que preencheram e contam no mês. Dois olhares: em que ponto do ciclo de gestão a loja "
         "está, e se o treino está virando domínio do método.", pin="Leitura")

a, b = st.columns(2, gap="large")
with a:
    st.markdown("**Onde cada loja está no ciclo de gestão**", help=C.AJUDA["ciclo"])
    cc = pre["ciclo"].value_counts().reindex(list(CICLOS)).fillna(0).astype(int)
    hover = [f"<b>{c}: {cc[c]} lojas</b><br><i>{EXPLICA_C[c]}</i><br><br>"
             + ui.lista_hover(sorted(pre.loc[pre["ciclo"] == c, "LOJA"]), limite=12) for c in CICLOS]
    fig = go.Figure(go.Pie(labels=list(CICLOS), values=cc.values, hole=0.58, sort=False, direction="clockwise",
                           marker=dict(colors=list(CICLOS.values()), line=dict(color=C.COR_FUNDO, width=2)),
                           textinfo="value", customdata=hover, hovertemplate="%{customdata}<extra></extra>"))
    fig.update_layout(**{**ui.LAYOUT_GRAFICO, "showlegend": True}, height=360,
                      legend=dict(orientation="h", y=-0.12, x=0.5, xanchor="center"),
                      annotations=[dict(text=f"<b>{ui.pct(cc['Ciclo fechado'] / len(pre), 0)}</b><br>ciclo fechado",
                                        showarrow=False, font=dict(size=15, color="#eee"))])
    ui.grafico(fig)
with b:
    st.markdown("**O treino está virando domínio?**", help=C.AJUDA["quadrante"])
    q = pre["quadrante"].value_counts().reindex(list(QUADRANTES)).fillna(0).astype(int)
    hover = [f"<b>{n}: {q[n]} lojas</b><br><i>{EXPLICA_Q[n]}</i><br><br>"
             + ui.lista_hover(sorted(pre.loc[pre["quadrante"] == n, "LOJA"]), limite=12) for n in QUADRANTES]
    ui.grafico(ui.barras_h(q.values, list(QUADRANTES), list(QUADRANTES.values()),
                           [f"{v} · {ui.pct(v / len(pre), 0)}" for v in q.values], altura=360, hover=hover))

st.markdown("**Lojas por quadrante do treino**")
sel = st.segmented_control("Quadrante", list(QUADRANTES), default="Treino ineficaz", label_visibility="collapsed")
lista = pre[pre["quadrante"] == sel] if sel else pre
if sel:
    st.caption(f"{sel}: {EXPLICA_Q[sel]}. {len(lista)} lojas.")
st.dataframe(pd.DataFrame({
    "Loja": lista["LOJA"], "Coordenador": lista["coordenador_mes"].str.title(),
    "Treinar": lista["pct_Treinar"], "Domínio de Método": lista["pct_Domínio de Método"],
    "Verificar": lista["pct_Verificar"], "Acompanhar": lista["pct_Acompanhar"],
    "Ciclo": lista["ciclo"], "Score": lista["score"].round(2),
}).sort_values("Score").assign(Score=lambda t: t["Score"].map(ui.num)), hide_index=True, use_container_width=True,
    column_config={"Loja": st.column_config.TextColumn(width=280), "Coordenador": st.column_config.TextColumn(width=240),
                   "Ciclo": st.column_config.TextColumn(width=210),
                   **{c: st.column_config.ProgressColumn(c, format="percent", min_value=0, max_value=1, width=140)
                      for c in ("Treinar", "Domínio de Método", "Verificar", "Acompanhar")}})
