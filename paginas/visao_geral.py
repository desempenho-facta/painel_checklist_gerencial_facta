import pandas as pd
import streamlit as st

from core import config as C
from core import regras as R
from core import ui
from core.contexto import rankings

ctx = st.session_state["ctx"]
h_total = ctx.hier_total()
h = ctx.hier()
ind = R.indicadores(h)
rede = R.indicadores(h_total)

ui.topo("Visão geral", f"{ctx.rotulo_visao} · {R.rotulo_mes(ctx.comp)}")

rk_coord, rk_reg = rankings(ctx.comp_iso)
aviso = R.aviso_mes(rk_coord, ctx.comp, ctx.hoje.date())
texto = f"<b>{aviso}</b>"
if ctx.eh_mes_corrente:
    texto += f" · {R.texto_prazo(ctx.hoje.date())}"
ui.faixa(texto, pin=R.rotulo_mes(ctx.comp))

c = st.columns(6)
with c[0]:
    ui.card(ind["preenchidas"], "Lojas preenchidas", f"de {ind['carteira']} na carteira do mês",
            cor="#4CAF50", ajuda=C.AJUDA["carteira"])
with c[1]:
    ui.card(ui.pct(ind["cobertura"]), "Cobertura", f"{ind['preenchidas_calculo']} de {ind['carteira_calculo']} que contam",
            cor=ui.cor_cobertura(ind["cobertura"]), ajuda=C.AJUDA["cobertura"])
with c[2]:
    ui.card(ind["pendentes"], "Lojas pendentes", f"{ind['lojas_novas']} lojas novas",
            cor="#E5484D" if ind["pendentes"] else "#4CAF50", ajuda=C.AJUDA["status"])
with c[3]:
    comp_rede = R.comparacao_rede(ind["score"], rede["score"]) if ctx.nivel != "rede" else ""
    ui.card(ui.num(ind["score"]), "Score médio",
            f"rede em {ui.num(rede['score'])} · {comp_rede}" if comp_rede else "média das lojas",
            cor=ui.cor_score(ind["score"]), ajuda=C.AJUDA["score"])
with c[4]:
    ui.card(ui.pct(ind["pct_maduras"]), "Lojas maduras", f"{ind['reativas']} reativas",
            cor="#4CAF50", ajuda=C.AJUDA["maturidade"])
with c[5]:
    ui.card(ind["risco_critico"], "Risco crítico", f"{ind['sem_chamados']} sem chamados abertos",
            cor="#E5484D" if ind["risco_critico"] else "#4CAF50", ajuda=C.AJUDA["risco"])

# Posição no ranking (visão de coordenador ou regional)
if ctx.nivel in ("coordenador", "regional"):
    rk = rk_coord if ctx.nivel == "coordenador" else rk_reg
    linha = rk[rk["nome"] == ctx.nome]
    st.write("")
    a, b = st.columns(2)
    if len(linha):
        lr = linha.iloc[0]
        artigo = "é o" if ctx.nivel == "coordenador" else "é a"
        ord_ = "º" if ctx.nivel == "coordenador" else "ª"
        with a:
            ui.card(f"{lr['pos_cobertura']}{ord_} de {len(rk)}", "Posição em cobertura",
                    f"cobertura ajustada {ui.pct(lr['cobertura_ajustada'])}", ajuda=C.AJUDA["cobertura_ajustada"])
        with b:
            ui.card(f"{lr['pos_score']}{ord_} de {len(rk)}", "Posição em score", f"score {ui.num(lr['score'])}")
    else:
        st.info("Sem posição no ranking neste mês.")

# Supervisão especial em destaque
esp = h[h["supervisao_especial"]]
if len(esp):
    st.write("")
    texto = (f"<b>{len(esp)} {'loja' if len(esp) == 1 else 'lojas'} com supervisão especial neste mês, "
             f"fora do score e da cobertura.</b> As respostas foram mantidas como gravadas.")
    if len(esp) <= 12:
        nomes = ", ".join(f"{l.split(' - ')[1].replace('LOJA ', '').title() if ' - ' in l else l} ({s.title()})"
                          for l, s in zip(esp["LOJA"], esp["tipo_especial"]))
        texto += " " + nomes
    else:
        por_tipo = esp["tipo_especial"].value_counts()
        texto += " " + ", ".join(f"{n} {t.lower()}" for t, n in por_tipo.items()) + ". A lista está na tela Lojas."
    ui.destaque(texto)

st.write("")
g1, g2 = st.columns(2)
with g1:
    st.markdown("**Situação das lojas no mês**", help=C.AJUDA["status"])
    cont = h["status"].value_counts().reindex(list(ui.CORES_STATUS)).fillna(0)
    st.plotly_chart(ui.barras_h(cont.values, cont.index, [ui.CORES_STATUS[s] for s in cont.index]), use_container_width=True)
with g2:
    st.markdown("**Maturidade das lojas que preencheram**", help=C.AJUDA["maturidade"])
    pre = h[(h["status"] == "Preencheu") & h["conta"]]
    cont = pre["maturidade"].value_counts().reindex(list(ui.CORES_MATURIDADE)).fillna(0)
    st.plotly_chart(ui.barras_h(cont.values, cont.index, list(ui.CORES_MATURIDADE.values())), use_container_width=True)
