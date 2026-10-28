import html
import textwrap

import pandas as pd
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

por_bloco, por_perg = R.percentual_nao(val_mes, h["COD_LOJAS"])
_, perg_rede = R.percentual_nao(val_mes, ctx.hier_total()["COD_LOJAS"])
bloco_rede, _ = R.percentual_nao(val_mes, ctx.hier_total()["COD_LOJAS"])
if por_bloco["respondidas"].sum() == 0:
    st.info("Nenhum preenchimento que conte neste mês para esta visão.")
    st.stop()

n_lojas = int(por_perg["respondidas"].max())
ui.faixa(f"<b>{n_lojas} lojas</b> que contam no mês. Só as perguntas de 1 a 36, sem as lojas com supervisão especial."
         + (" Passe o mouse para comparar com a rede." if ctx.nivel != "rede" else ""), pin="Base")

ALTURA = 440
a, b = st.columns(2, gap="large")
with a:
    st.markdown("**Ranking de blocos por % de Não**")
    pb = por_bloco.sort_values("pct_nao", ascending=False).copy()
    pb["rede"] = pb["bloco"].map(bloco_rede.set_index("bloco")["pct_nao"])
    hover = [f"<b>{r.bloco}</b><br>{ui.pct(r.pct_nao)} de Não ({r.nao} de {r.respondidas} respostas)"
             + (f"<br>Rede: {ui.pct(r.rede)}" if ctx.nivel != "rede" else "") for r in pb.itertuples()]
    ui.grafico(ui.barras_h(pb["pct_nao"], pb["bloco"], C.COR_AZUL, [ui.pct(v) for v in pb["pct_nao"]],
                           altura=ALTURA, eixo_pct=True, hover=hover))
with b:
    st.markdown("**As 10 perguntas com mais Não**")
    top = por_perg.sort_values(["pct_nao", "nao"], ascending=False).head(10).copy()
    top["rede"] = top["pergunta"].map(perg_rede.set_index("pergunta")["pct_nao"])
    rotulos = [f"{q} · {textwrap.shorten(PERGUNTAS_TEXTO[q], 34, placeholder='...')}" for q in top["pergunta"]]
    hover = ["<b>" + q + "</b> · " + html.escape(bl) + "<br>" + "<br>".join(textwrap.wrap(html.escape(PERGUNTAS_TEXTO[q]), 60))
             + f"<br><br>{ui.pct(pn)} de Não ({n} de {resp} lojas)" + (f"<br>Rede: {ui.pct(rd)}" if ctx.nivel != "rede" else "")
             for q, bl, pn, n, resp, rd in zip(top["pergunta"], top["bloco"], top["pct_nao"], top["nao"], top["respondidas"], top["rede"])]
    ui.grafico(ui.barras_h(top["pct_nao"], rotulos, C.COR_VERMELHO, [ui.pct(v, 0) for v in top["pct_nao"]],
                           altura=ALTURA, eixo_pct=True, hover=hover))

st.markdown("**Todas as perguntas** (da que mais tem Não para a que menos tem)")
tab = por_perg.sort_values(["pct_nao", "nao"], ascending=False).copy()
tab["rede"] = tab["pergunta"].map(perg_rede.set_index("pergunta")["pct_nao"])
saida = pd.DataFrame({
    "Pergunta": tab["pergunta"], "Texto": tab["pergunta"].map(PERGUNTAS_TEXTO), "Bloco": tab["bloco"],
    "% de Não": tab["pct_nao"].map(lambda v: ui.pct(v, 1)), "Lojas com Não": tab["nao"].astype(str) + " de " + tab["respondidas"].astype(str),
})
if ctx.nivel != "rede":
    saida["Rede"] = tab["rede"].map(lambda v: ui.pct(v, 1))
st.dataframe(saida, hide_index=True, use_container_width=True, height=420,
             column_config={"Pergunta": st.column_config.TextColumn(width=80), "Texto": st.column_config.TextColumn(width=560),
                            "Bloco": st.column_config.TextColumn(width=160)})
