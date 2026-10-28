import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import config as C
from core import dados
from core import regras as R
from core import relatorio
from core import ui
from core.perguntas import PERGUNTAS_TEXTO

ctx = st.session_state["ctx"]
d = dados.carregar()
val = d["validos"]
h = ctx.hier()

opcoes = h.sort_values("LOJA")[["COD_LOJAS", "LOJA"]].drop_duplicates()
if opcoes.empty:
    st.info("Nenhuma loja nesta visão.")
    st.stop()
rotulos = dict(zip(opcoes["COD_LOJAS"], opcoes["LOJA"]))
a, b = st.columns([3, 1], vertical_alignment="bottom")
with a:
    cod = st.selectbox("Loja", list(rotulos), format_func=rotulos.get, key="loja_sel")

hist = val[val["COD_LOJAS"] == cod].sort_values("timestamp")
ate_mes = hist[hist["competencia"] <= ctx.comp]
if ate_mes.empty:
    st.warning("Esta loja não tem preenchimento até o mês selecionado.")
    st.stop()
p = ate_mes.iloc[-1]

# Média da rede por bloco no mês do preenchimento (só lojas que contam)
rede_mes = val[(val["competencia"] == p["competencia"]) & ~val["supervisao_especial"]]
rede_blocos = {bl: rede_mes[f"pct_{bl}"].mean() for bl in C.BLOCOS} if len(rede_mes) else None
grave_df = R.casos_graves(hist, p["competencia"])
grave = grave_df.iloc[0] if len(grave_df) else None

with b:
    pdf = relatorio.gerar_pdf(rotulos[cod], p, R.historico_loja(ate_mes, cod), grave, rede_blocos, ctx.rotulo_visao)
    st.download_button("Baixar relatório (PDF)", pdf, file_name=f"diagnostico_{cod}_{p['competencia']:%Y_%m}.pdf",
                       mime="application/pdf", use_container_width=True, type="primary",
                       help="Relatório da loja com situação do mês, pontos de melhoria, histórico e respostas.")

if p["competencia"] != ctx.comp:
    ui.destaque(f"<b>A loja não preencheu em {R.rotulo_mes(ctx.comp)}.</b> Abaixo, o último preenchimento antes disso, "
                f"de {p['timestamp']:%d/%m/%Y}.")
else:
    ui.faixa(f"Último preenchimento do mês: <b>{p['timestamp']:%d/%m/%Y às %H:%M}</b> · coordenador "
             f"{html.escape(p['COORDENADOR'].title())} · supervisor {html.escape(p['SUPERVISOR'].title())}",
             pin="Preenchimento")
if p["supervisao_especial"]:
    ui.destaque(f"<b>Supervisão especial ({html.escape(p['tipo_especial'])}).</b> As respostas estão como foram gravadas, "
                "mas esta loja não entra no score nem na cobertura do coordenador neste mês.")
if grave is not None:
    partes = ", ".join(f"{html.escape(s)} há {n} {'preenchimento' if n == 1 else 'preenchimentos seguidos'}"
                       for s, n in grave["por_sinal"].items())
    ui.destaque(f"<b>Caso grave há {grave['preenchimentos_seguidos']} "
                f"{'preenchimento' if grave['preenchimentos_seguidos'] == 1 else 'preenchimentos seguidos'} "
                f"(desde {R.rotulo_mes(grave['desde'])}).</b> {partes}.")

esq, dir_ = st.columns([1.35, 1], gap="large")
with esq:
    st.markdown("**Desempenho da loja por bloco**", help="Percentual de Sim em cada bloco. A linha pontilhada é a média "
                                                         "da rede no mesmo mês.")
    blocos = list(C.BLOCOS)
    vals = [p[f"pct_{bl}"] * 100 for bl in blocos]
    pontos = [f"{C.BLOCOS[bl]['peso'] * p[f'pct_{bl}']:.1f} de {C.BLOCOS[bl]['peso']} pontos".replace(".", ",") for bl in blocos]
    fig = go.Figure()
    if rede_blocos:
        rv = [rede_blocos[bl] * 100 for bl in blocos]
        fig.add_trace(go.Scatterpolar(r=rv + rv[:1], theta=blocos + blocos[:1], name="Média da rede", mode="lines",
                                      line=dict(color="#bdbdbd", dash="dot", width=2),
                                      hovertemplate="%{theta}<br>Rede: %{r:.0f}%<extra></extra>"))
    fig.add_trace(go.Scatterpolar(r=vals + vals[:1], theta=blocos + blocos[:1], name="Loja", fill="toself",
                                  line=dict(color=C.COR_AZUL_FACTA, width=3), fillcolor="rgba(0,128,245,0.25)",
                                  customdata=pontos + pontos[:1], mode="lines+markers",
                                  hovertemplate="<b>%{theta}</b><br>Loja: %{r:.0f}%<br>%{customdata}<extra></extra>"))
    fig.update_layout(**{**ui.LAYOUT_GRAFICO, "showlegend": True, "margin": dict(l=75, r=75, t=30, b=20)}, height=430,
                      legend=dict(orientation="h", y=-0.08, x=0.5, xanchor="center"),
                      polar=dict(bgcolor="rgba(0,0,0,0)",
                                 radialaxis=dict(range=[0, 100], ticksuffix="%", gridcolor="#4a4646", showticklabels=False, tickvals=[20, 40, 60, 80, 100]),
                                 angularaxis=dict(gridcolor="#4a4646", tickfont=dict(size=12), rotation=90, direction="clockwise")))
    ui.grafico(fig)

with dir_:
    ui.cards([
        dict(numero=ui.num(p["score"]), rotulo="Score", sub="de 0 a 100", cor=ui.cor_score(p["score"]), ajuda=C.AJUDA["score"]),
        dict(numero=p["maturidade"], rotulo="Maturidade", sub=C.DEFINICAO_MATURIDADE[p["maturidade"]],
             cor=ui.CORES_MATURIDADE[p["maturidade"]].replace(C.COR_VERDE, ui.VERDE_CLARO), ajuda=C.AJUDA["maturidade"]),
        dict(numero=p["risco"], rotulo="Nível de risco", sub=f"{p['falhas_criticas']} de 3 perguntas críticas com Não",
             cor=ui.VERMELHO_CLARO if p["falhas_criticas"] >= 2 else C.COR_AMBAR if p["falhas_criticas"] else ui.VERDE_CLARO,
             ajuda=C.AJUDA["risco"]),
        dict(numero=p["ciclo"], rotulo="Ciclo de gestão", sub="treinar, verificar e acompanhar", ajuda=C.AJUDA["ciclo"]),
        dict(numero=p["quadrante"], rotulo="Quadrante do treino", sub="treinar x domínio de método", ajuda=C.AJUDA["quadrante"]),
        dict(numero="Com chamados" if p["estrutura"] == "Com chamados abertos" else "Sem chamados", rotulo="Estrutura (Q36)",
             sub="chamados de estrutura", cor=ui.VERDE_CLARO if p["estrutura"] == "Com chamados abertos" else ui.VERMELHO_CLARO,
             ajuda=C.AJUDA["estrutura"]),
    ], minimo=180)

# Pontos de melhoria: perguntas com Não, por bloco
naos = [(bl, q) for bl, b_ in C.BLOCOS.items() for q in b_["perguntas"] if p[q] == "Não"]
st.markdown(f"**Pontos de melhoria** ({len(naos)} {'pergunta' if len(naos) == 1 else 'perguntas'} com Não)")
if naos:
    partes = []
    for bl in C.BLOCOS:
        qs = [q for b2, q in naos if b2 == bl]
        if qs:
            perdeu = sum(C.PONTO_POR_SIM[q] for q in qs)
            partes.append(f'<div class="fx-bloco">{bl} · perdeu {ui.num(perdeu, 1)} de {C.BLOCOS[bl]["peso"]} pontos</div>')
            partes += [f'<div class="fx-resp"><div class="q">{q}</div><div class="t">{html.escape(PERGUNTAS_TEXTO[q])}</div>'
                       f'<div class="r fx-nao">Não</div></div>' for q in qs]
    st.markdown("".join(partes), unsafe_allow_html=True)
else:
    st.success("Nenhuma pergunta com Não neste preenchimento.")

with st.expander("Ver as 36 respostas do preenchimento"):
    partes = []
    for bloco, b_ in C.BLOCOS.items():
        ganho = b_["peso"] * p[f"pct_{bloco}"]
        partes.append(f'<div class="fx-bloco">{bloco} · {ui.num(ganho, 1)} de {b_["peso"]} pontos</div>')
        for q in b_["perguntas"]:
            r = p[q]
            cls = "fx-sim" if r == "Sim" else "fx-nao" if r == "Não" else "fx-vazio"
            pts = C.PONTO_POR_SIM[q] if r == "Sim" else 0
            partes.append(
                f'<div class="fx-resp"><div class="q">{q}</div><div class="t">{html.escape(PERGUNTAS_TEXTO[q])}</div>'
                f'<div class="r {cls}">{html.escape(r or "vazio")}</div><div class="p">+{ui.num(pts, 2)}</div></div>')
    st.markdown("".join(partes), unsafe_allow_html=True)

g1, g2 = st.columns([1, 1.3], gap="large")
with g1:
    st.markdown("**Evolução do score**")
    serie = hist.groupby("competencia")["score"].last()
    fig2 = go.Figure(go.Scatter(x=[R.rotulo_mes(m)[:3] + "/" + str(m.year)[2:] for m in serie.index], y=serie.values,
                                mode="lines+markers+text", text=[ui.num(v, 1) for v in serie.values],
                                textposition="top center", line=dict(color=C.COR_LARANJA, width=3),
                                hovertemplate="%{x}: %{y:.2f}<extra></extra>"))
    fig2.update_layout(**ui.LAYOUT_GRAFICO, height=280, yaxis=dict(range=[0, 110], gridcolor="#3a3838"))
    ui.grafico(fig2)
with g2:
    st.markdown("**Histórico da loja**")
    tab = R.historico_loja(val, cod)
    st.dataframe(pd.DataFrame({
        "Mês": tab["competencia"].map(R.rotulo_mes),
        "Preenchido em": tab["timestamp"].dt.strftime("%d/%m/%Y"),
        "Score": tab["score"].map(lambda v: ui.num(v)),
        "Maturidade": tab["maturidade"],
        "Risco": tab["risco"],
        "Coordenador": tab["COORDENADOR"].str.title(),
        "Supervisor": tab["SUPERVISOR"].str.title(),
        "Supervisão especial": tab["supervisao_especial"].map({True: "Sim", False: ""}),
    }).iloc[::-1], hide_index=True, use_container_width=True, height=min(36 * (len(tab) + 1) + 4, 320),
        column_config={"Mês": st.column_config.TextColumn(width=130), "Coordenador": st.column_config.TextColumn(width=220),
                       "Supervisor": st.column_config.TextColumn(width=220)})
