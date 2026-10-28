import pandas as pd
import streamlit as st

from core import config as C
from core import regras as R
from core import ui

ctx = st.session_state["ctx"]
h = ctx.hier()
pre = h[(h["status"] == "Preencheu") & h["conta"]]

ui.topo("O treino está funcionando?", f"{ctx.rotulo_visao} · {R.rotulo_mes(ctx.comp)}")
if pre.empty:
    st.info("Nenhum preenchimento que conte neste mês para esta visão.")
    st.stop()

QUADRANTES = {"Treina e domina": C.COR_VERDE, "Talento natural": C.COR_AZUL,
              "Treino ineficaz": C.COR_AMBAR, "Crítico": C.COR_VERMELHO}
CICLOS = {"Ciclo fechado": C.COR_VERDE, "Esforço sem acompanhamento": C.COR_AMBAR,
          "Exige sem preparar": "#E07020", "Ciclo frágil": C.COR_VERMELHO}

a, b = st.columns(2)
with a:
    st.markdown("**Treino x domínio de método**", help=C.AJUDA["quadrante"])
    q = pre["quadrante"].value_counts().reindex(list(QUADRANTES)).fillna(0).astype(int)
    c1, c2 = st.columns(2)
    for i, (nome, cor) in enumerate(QUADRANTES.items()):
        with (c1 if i % 2 == 0 else c2):
            ui.card(q[nome], nome, ui.pct(q[nome] / len(pre), 0) + " das lojas", cor=cor)
            st.write("")
with b:
    st.markdown("**Ciclo treinar, verificar e acompanhar**", help=C.AJUDA["ciclo"])
    cc = pre["ciclo"].value_counts().reindex(list(CICLOS)).fillna(0).astype(int)
    st.plotly_chart(ui.barras_h(cc.values, cc.index, list(CICLOS.values()), altura=280), use_container_width=True)

st.markdown("**Lojas por quadrante**")
sel = st.segmented_control("Quadrante", list(QUADRANTES), default="Treino ineficaz", label_visibility="collapsed")
lista = pre[pre["quadrante"] == sel] if sel else pre
st.dataframe(pd.DataFrame({
    "Loja": lista["LOJA"], "Coordenador": lista["coordenador_mes"].str.title(),
    "Treinar": lista["pct_Treinar"], "Domínio de Método": lista["pct_Domínio de Método"],
    "Verificar": lista["pct_Verificar"], "Acompanhar": lista["pct_Acompanhar"],
    "Ciclo": lista["ciclo"], "Score": lista["score"].round(2),
}).sort_values("Score").assign(Score=lambda t: t["Score"].map(ui.num)), hide_index=True, use_container_width=True,
    column_config={c: st.column_config.ProgressColumn(c, format="percent", min_value=0, max_value=1)
                   for c in ("Treinar", "Domínio de Método", "Verificar", "Acompanhar")})
