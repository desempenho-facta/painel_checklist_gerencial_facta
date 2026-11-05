import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import config as C
from core import dados
from core import roteiro as RT
from core import ui

ctx = st.session_state["ctx"]
d = dados.carregar()
h = ctx.hier()
rot = d["roteiro"]
coords = sorted(h["coordenador_mes"].dropna().unique())
rot_v = rot[rot["COORDENADOR"].isin(coords)]

ui.faixa("O roteiro não é obrigatório, mas é indicado para todos os coordenadores. Vale a versão mais recente "
         "de cada semana. <b>Antes da semana</b> é o roteiro enviado até domingo.", pin="Regra")

semanas = RT.semanas_do_mes(ctx.comp, ctx.hoje)
if not semanas:
    st.info("Ainda não há semanas deste mês para acompanhar.")
    st.stop()

ad = RT.adesao(rot_v, coords, ctx.comp, ctx.hoje)
env = RT.envios_semana(rot_v)
env = env[env["semana"].isin(semanas)]
com = int((ad["semanas_com_roteiro"] > 0).sum())
possiveis = int(ad["semanas_mes"].sum())
feitas = int(ad["semanas_com_roteiro"].sum())
antes = int((env["antecedencia"] == "Antes da semana").sum())
reed = int((env["versoes"] > 1).sum())

ui.cards([
    dict(numero=f"{com} de {len(coords)}", rotulo="Coordenadores com roteiro", sub="mandaram ao menos uma semana no mês",
         cor=ui.cor_cobertura(com / len(coords) if coords else None)),
    dict(numero=ui.pct(feitas / possiveis if possiveis else None, 0), rotulo="Semanas com roteiro",
         sub=f"{feitas} de {possiveis} semanas possíveis", cor=ui.cor_cobertura(feitas / possiveis if possiveis else None),
         ajuda="Semanas que começam no mês, até a semana atual, multiplicadas pelos coordenadores da visão."),
    dict(numero=ui.pct(antes / feitas if feitas else None, 0), rotulo="Enviados antes da semana",
         sub=f"{antes} de {feitas} roteiros", cor=ui.cor_cobertura(antes / feitas if feitas else None)),
    dict(numero=reed, rotulo="Semanas reeditadas", sub=ui.pct(reed / feitas if feitas else None, 0) + " dos roteiros",
         cor=C.COR_AMBAR if reed else ui.VERDE_CLARO),
], minimo=190)

c1, c2 = st.columns(2)
with c1:
    ui.secao("Coordenadores com roteiro por semana", f"de {len(coords)} na visão")
    por_sem = [int((env["semana"] == s).sum()) for s in semanas]
    nomes_sem = [sorted(env.loc[env["semana"] == s, "COORDENADOR"].str.title()) for s in semanas]
    faltam = [sorted(set(coords) - set(env.loc[env["semana"] == s, "COORDENADOR"])) for s in semanas]
    hover = [f"<b>Semana de {RT.rotulo_semana(s)}</b><br>Sem roteiro ({len(f)}):<br>" + ui.lista_hover([x.title() for x in f])
             for s, f in zip(semanas, faltam)]
    ui.grafico(ui.barras_h(por_sem, [RT.rotulo_semana(s) for s in semanas], [C.COR_AZUL] * len(semanas),
                           altura=70 + 46 * len(semanas), hover=hover))
with c2:
    ui.secao("Quando o roteiro foi enviado", "primeiro envio de cada semana")
    cont = [int((env["antecedencia"] == a).sum()) for a in RT.ORDEM_ANTECEDENCIA]
    cores = [ui.VERDE_CLARO, C.COR_AMBAR, "#E07020", ui.VERMELHO_CLARO]
    hover = []
    for a, n in zip(RT.ORDEM_ANTECEDENCIA, cont):
        e = env[env["antecedencia"] == a]
        nomes = sorted(f"{c.title()} ({s:%d/%m})" for c, s in zip(e["COORDENADOR"], e["semana"]))
        hover.append(f"<b>{a}: {n}</b><br>" + ui.lista_hover(nomes))
    ui.grafico(ui.barras_h(cont, RT.ORDEM_ANTECEDENCIA, cores, altura=70 + 46 * 4, hover=hover))

# Uso do tempo
rot_mes = rot_v[rot_v["competencia"] == ctx.comp]
uso = RT.uso_do_tempo(rot_mes)
ui.secao("Como os dias foram planejados no mês", "dias de visita, base, feriado e folga por coordenador")
if uso.empty:
    st.caption("Nenhum roteiro neste mês.")
else:
    uso = uso.assign(_t=uso[RT.TIPOS].sum(axis=1)).sort_values("VISITA", ascending=True)
    fig = go.Figure()
    for t in RT.TIPOS:
        fig.add_bar(y=uso["COORDENADOR"].str.title(), x=uso[t], name=RT.NOME_TIPO[t], orientation="h",
                    marker_color=RT.COR_TIPO[t], hovertemplate=f"%{{y}}<br>{RT.NOME_TIPO[t]}: %{{x}} dias<extra></extra>")
    fig.update_layout(**{**ui.LAYOUT_GRAFICO, "showlegend": True}, barmode="stack", height=90 + 28 * len(uso),
                      legend=dict(orientation="h", y=1.02, x=0, yanchor="bottom", traceorder="normal"), xaxis=dict(gridcolor="#3a3838"))
    ui.grafico(fig)

# Tabela por coordenador
regional = h.groupby("coordenador_mes")["regional_mes"].agg(lambda s: s.value_counts().index[0])
dias = uso.set_index("COORDENADOR")[RT.TIPOS] if not uso.empty else pd.DataFrame(columns=RT.TIPOS)
tab = pd.DataFrame({
    "Coordenador": ad["COORDENADOR"].str.title(),
    "Regional": ad["COORDENADOR"].map(regional.to_dict()).fillna("").str.title(),
    "Semanas com roteiro": ad["semanas_com_roteiro"].astype(str) + " de " + ad["semanas_mes"].astype(str),
    "Antes da semana": ad["antes_da_semana"],
    "Reeditadas": ad["reeditadas"],
    "Dias de visita": ad["COORDENADOR"].map(dias["VISITA"].to_dict() if "VISITA" in dias else {}).fillna(0).astype(int),
    "Dias na base": ad["COORDENADOR"].map(dias["BASE"].to_dict() if "BASE" in dias else {}).fillna(0).astype(int),
    "Último envio": ad["ultimo_envio"].map(lambda x: "nunca enviou" if pd.isna(x) else f"{x:%d/%m/%Y}"),
    "_o": ad["adesao"],
}).sort_values(["_o", "Coordenador"]).drop(columns="_o")
ui.secao("Adesão por coordenador", "quem está sem roteiro aparece primeiro")
st.dataframe(tab, hide_index=True, use_container_width=True, height=min(38 * (len(tab) + 1), 720),
             column_config={"Coordenador": st.column_config.TextColumn(width=260, pinned=True),
                            "Regional": st.column_config.TextColumn(width=220),
                            "Dias na base": st.column_config.NumberColumn(
                                help="Dias marcados como BASE: trabalho na loja que serve de base do coordenador.")})
