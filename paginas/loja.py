import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import config as C
from core import dados
from core import regras as R
from core import ui
from core.perguntas import PERGUNTAS_TEXTO

ctx = st.session_state["ctx"]
d = dados.carregar()
val = d["validos"]
h = ctx.hier()

ui.topo("Diagnóstico da loja", f"{ctx.rotulo_visao} · {R.rotulo_mes(ctx.comp)}")

opcoes = h.sort_values("LOJA")[["COD_LOJAS", "LOJA"]].drop_duplicates()
if opcoes.empty:
    st.info("Nenhuma loja nesta visão.")
    st.stop()
rotulos = dict(zip(opcoes["COD_LOJAS"], opcoes["LOJA"]))
cod = st.selectbox("Loja", list(rotulos), format_func=rotulos.get, key="loja_sel")

hist = val[val["COD_LOJAS"] == cod].sort_values("timestamp")
ate_mes = hist[hist["competencia"] <= ctx.comp]
if ate_mes.empty:
    st.warning("Esta loja não tem preenchimento até o mês selecionado.")
    st.stop()

p = ate_mes.iloc[-1]
if p["competencia"] != ctx.comp:
    ui.destaque(f"<b>A loja não preencheu em {R.rotulo_mes(ctx.comp)}.</b> Abaixo, o último preenchimento antes disso, "
                f"de {p['timestamp']:%d/%m/%Y}.")
else:
    ui.faixa(f"Último preenchimento do mês: <b>{p['timestamp']:%d/%m/%Y às %H:%M}</b> · coordenador "
             f"{html.escape(p['COORDENADOR'].title())} · supervisor {html.escape(p['SUPERVISOR'].title())}", pin="Preenchimento")
if p["supervisao_especial"]:
    ui.destaque(f"<b>Supervisão especial ({html.escape(p['tipo_especial'])}).</b> As respostas estão como foram gravadas, "
                "mas esta loja não entra no score nem na cobertura do coordenador neste mês.")

grave = R.casos_graves(val[val["COD_LOJAS"] == cod], p["competencia"])
if len(grave):
    gr = grave.iloc[0]
    desde = R.rotulo_mes(gr["desde"])
    partes = ", ".join(f"{html.escape(s)} há {n} {'preenchimento' if n == 1 else 'preenchimentos seguidos'}"
                       for s, n in gr["por_sinal"].items())
    ui.destaque(f"<b>Caso grave há {gr['preenchimentos_seguidos']} "
                f"{'preenchimento' if gr['preenchimentos_seguidos'] == 1 else 'preenchimentos seguidos'} (desde {desde}).</b> "
                f"{partes}.")

c = st.columns(6)
with c[0]:
    ui.card(ui.num(p["score"]), "Score", "de 0 a 100", cor=ui.cor_score(p["score"]), ajuda=C.AJUDA["score"])
with c[1]:
    ui.card(p["maturidade"], "Maturidade", cor=ui.CORES_MATURIDADE[p["maturidade"]].replace(C.COR_VERDE, "#4CAF50"),
            ajuda=C.AJUDA["maturidade"])
with c[2]:
    ui.card(p["risco"], "Nível de risco", f"{p['falhas_criticas']} de 3 perguntas críticas com Não",
            cor="#E5484D" if p["falhas_criticas"] >= 2 else C.COR_AMBAR if p["falhas_criticas"] else "#4CAF50",
            ajuda=C.AJUDA["risco"])
with c[3]:
    ui.card(p["ciclo"], "Ciclo", cor="#ffffff", ajuda=C.AJUDA["ciclo"])
with c[4]:
    ui.card(p["quadrante"], "Quadrante do treino", cor="#ffffff", ajuda=C.AJUDA["quadrante"])
with c[5]:
    ui.card("Com chamados" if p["estrutura"] == "Com chamados abertos" else "Sem chamados", "Estrutura (Q36)",
            cor="#4CAF50" if p["estrutura"] == "Com chamados abertos" else "#E5484D", ajuda=C.AJUDA["estrutura"])

st.write("")
esq, dir_ = st.columns([1.5, 1])

with esq:
    st.markdown("**Respostas do preenchimento**")
    partes = []
    for bloco, b in C.BLOCOS.items():
        ganho = b["peso"] * p[f"pct_{bloco}"]
        partes.append(f'<div class="fx-bloco">{bloco} · {ui.num(ganho, 1)} de {b["peso"]} pontos</div>')
        for q in b["perguntas"]:
            r = p[q]
            cls = "fx-sim" if r == "Sim" else "fx-nao" if r == "Não" else "fx-vazio"
            pts = C.PONTO_POR_SIM[q] if r == "Sim" else 0
            partes.append(
                f'<div class="fx-resp"><div class="q">{q}</div><div class="t">{html.escape(PERGUNTAS_TEXTO[q])}</div>'
                f'<div class="r {cls}">{html.escape(r or "vazio")}</div><div class="p">+{ui.num(pts, 2)}</div></div>')
    st.markdown("".join(partes), unsafe_allow_html=True)

with dir_:
    st.markdown("**Aproveitamento por bloco**")
    blocos = list(C.BLOCOS)
    vals = [p[f"pct_{b}"] for b in blocos]
    fig = go.Figure(go.Bar(x=vals, y=blocos, orientation="h",
                           marker_color=[C.COR_AZUL if v >= C.LIMIAR_BLOCO else C.COR_VERMELHO for v in vals],
                           text=[ui.pct(v, 0) for v in vals], textposition="outside"))
    fig.add_vline(x=C.LIMIAR_BLOCO, line_dash="dot", line_color="#888")
    fig.update_layout(**ui.LAYOUT_GRAFICO, height=330, xaxis=dict(range=[0, 1.15], tickformat=".0%"),
                      yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Linha pontilhada: 60%, a partir de onde o bloco é considerado bom.")

    st.markdown("**Evolução do score**")
    serie = hist.groupby("competencia")["score"].last()
    fig2 = go.Figure(go.Scatter(x=[R.rotulo_mes(m)[:3] + "/" + str(m.year)[2:] for m in serie.index], y=serie.values,
                                mode="lines+markers+text", text=[ui.num(v, 1) for v in serie.values],
                                textposition="top center", line=dict(color=C.COR_LARANJA)))
    fig2.update_layout(**ui.LAYOUT_GRAFICO, height=260, yaxis=dict(range=[0, 110]))
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("**Histórico da loja**")
tab = R.historico_loja(val, cod)
st.dataframe(pd.DataFrame({
    "Mês": tab["competencia"].map(R.rotulo_mes),
    "Preenchido em": tab["timestamp"].dt.strftime("%d/%m/%Y"),
    "Coordenador": tab["COORDENADOR"].str.title(),
    "Supervisor": tab["SUPERVISOR"].str.title(),
    "Score": tab["score"].map(lambda v: ui.num(v)),
    "Maturidade": tab["maturidade"],
    "Risco": tab["risco"],
    "Estrutura": tab["estrutura"],
    "Supervisão especial": tab["supervisao_especial"].map({True: "Sim", False: ""}),
}).iloc[::-1], hide_index=True, use_container_width=True)
