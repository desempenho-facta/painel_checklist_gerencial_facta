import streamlit as st

from core import config as C
from core import dados
from core import regras as R
from core import ui
from core.perguntas import PERGUNTAS_TEXTO

ctx = st.session_state["ctx"]
d = dados.carregar()
h = ctx.hier()
val_mes = d["validos"][d["validos"]["competencia"] == ctx.comp]

ui.topo("Pontos de atenção", f"{ctx.rotulo_visao} · {R.rotulo_mes(ctx.comp)}")

por_bloco, por_perg = R.percentual_nao(val_mes, h["COD_LOJAS"])
_, perg_rede = R.percentual_nao(val_mes, ctx.hier_total()["COD_LOJAS"])
if por_bloco["respondidas"].sum() == 0:
    st.info("Nenhum preenchimento que conte neste mês para esta visão.")
    st.stop()

a, b = st.columns([1, 1.3])
with a:
    st.markdown("**% de Não por bloco**")
    pb = por_bloco.sort_values("pct_nao", ascending=False)
    st.plotly_chart(ui.barras_h(pb["pct_nao"], pb["bloco"], C.COR_AZUL, [ui.pct(v) for v in pb["pct_nao"]],
                                altura=330, eixo_pct=True), use_container_width=True)
    st.caption("Do pior para o melhor. Só as perguntas de 1 a 36 e só as lojas que contam no mês.")

with b:
    st.markdown("**As 10 perguntas com mais Não**")
    top = por_perg.sort_values(["pct_nao", "nao"], ascending=False).head(10).copy()
    top["rede"] = top["pergunta"].map(perg_rede.set_index("pergunta")["pct_nao"])
    linhas = []
    for _, r in top.iterrows():
        linhas.append(f'<div class="fx-resp"><div class="q">{r["pergunta"]}</div>'
                      f'<div class="t">{PERGUNTAS_TEXTO[r["pergunta"]]}<br><span style="color:#888;font-size:12px">'
                      f'{r["bloco"]} · {r["nao"]} de {r["respondidas"]} lojas'
                      + (f' · rede {ui.pct(r["rede"])}' if ctx.nivel != "rede" else "") + '</span></div>'
                      f'<div class="r fx-nao">{ui.pct(r["pct_nao"], 0)}</div></div>')
    st.markdown("".join(linhas), unsafe_allow_html=True)
