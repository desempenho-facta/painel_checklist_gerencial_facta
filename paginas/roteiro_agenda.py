import html

import pandas as pd
import streamlit as st

from core import config as C
from core import dados
from core import roteiro as RT
from core import ui

ctx = st.session_state["ctx"]
d = dados.carregar()
h = ctx.hier()
rot = d["roteiro"]
val = d["validos"]
coords = sorted(h["coordenador_mes"].dropna().unique())
rot_v = rot[rot["COORDENADOR"].isin(coords) & rot["vigente"]]

st.markdown(f"""
<style>
.fx-semana {{ display:grid; gap:10px; grid-template-columns:repeat(auto-fit, minmax(190px, 1fr)); margin:6px 0 14px 0; }}
.fx-dia {{ background:{C.COR_CARD}; border:1px solid {C.COR_BORDA}; border-radius:12px; padding:12px 14px; }}
.fx-dia .cab {{ display:flex; justify-content:space-between; align-items:center; gap:8px; }}
.fx-dia .nome {{ font-weight:700; color:#f0f0f0; font-size:14px; }}
.fx-dia .data {{ color:#9a9a9a; font-size:12px; }}
.fx-dia .tipo {{ display:inline-block; color:#fff; font-size:11px; font-weight:800; letter-spacing:.6px; padding:2px 8px;
                border-radius:4px; margin:8px 0 6px 0; text-transform:uppercase; }}
.fx-dia .loja {{ color:#e8e8e8; font-size:13.5px; font-weight:600; margin-bottom:6px; }}
.fx-dia .mot {{ display:inline-block; background:#2A2828; border:1px solid #4a4545; color:#d6d6d6; font-size:11px;
               border-radius:10px; padding:1px 8px; margin:0 4px 4px 0; }}
.fx-dia .txt {{ color:#bdbdbd; font-size:12.5px; margin-top:6px; white-space:pre-wrap; }}
.fx-dia .txt b {{ color:#9a9a9a; font-weight:600; }}
.fx-dia .chk {{ color:#4CAF50; font-size:12px; font-weight:700; margin-top:6px; }}
</style>""", unsafe_allow_html=True)

if rot_v.empty:
    st.info("Nenhum roteiro enviado pelos coordenadores desta visão.")
    st.stop()

c1, c2 = st.columns([1.4, 1], vertical_alignment="bottom")
with c1:
    if ctx.nivel == "coordenador":
        coord = ctx.nome
        st.text_input("Coordenador", coord.title(), disabled=True)
    else:
        com_rot = sorted(rot_v["COORDENADOR"].unique())
        coord = st.selectbox("Coordenador", com_rot, format_func=str.title, key="agenda_coord")
semanas = sorted(rot_v.loc[rot_v["COORDENADOR"] == coord, "semana"].unique(), reverse=True)
if not semanas:
    st.info("Este coordenador ainda não mandou roteiro.")
    st.stop()
hoje = pd.Timestamp(ctx.hoje).tz_localize(None).normalize()
segunda_atual = hoje - pd.Timedelta(days=hoje.weekday())
no_mes = [s for s in semanas if pd.Timestamp(s).to_period("M") == ctx.comp.to_period("M")]
padrao = next((s for s in semanas if s <= segunda_atual and s in no_mes), no_mes[0] if no_mes else semanas[0])
with c2:
    semana = st.selectbox("Semana", semanas, index=semanas.index(padrao), format_func=RT.rotulo_semana,
                          key=f"agenda_semana_{coord}")

dias = rot_v[(rot_v["COORDENADOR"] == coord) & (rot_v["semana"] == semana)].sort_values("data")
todas = rot[(rot["COORDENADOR"] == coord) & (rot["semana"] == semana)]
versoes = todas["ts"].nunique()
envio = todas["ts"].min()
info = f"Enviado em {envio:%d/%m/%Y às %H:%M} ({RT.antecedencia(envio, pd.Timestamp(semana)).lower()})"
if versoes > 1:
    info += f" · reeditado {versoes - 1} {'vez' if versoes == 2 else 'vezes'}, última em {dias['ts'].max():%d/%m às %H:%M}"
st.caption(info)
just = dias["JUSTIFICATIVA"].replace("", pd.NA).dropna()
if versoes > 1 and len(just):
    ui.destaque(f"<b>Motivo da reedição:</b> {html.escape(just.iloc[0].capitalize())}")

chk_dia = set(zip(val["COD_LOJAS"], val["timestamp"].dt.normalize()))
cartoes = []
for _, r in dias.iterrows():
    tipo = r["TIPO"]
    cor = RT.COR_TIPO.get(tipo, C.COR_CINZA)
    partes = [f'<div class="cab"><span class="nome">{RT.DIAS[r["data"].weekday()] if r["data"].weekday() < 5 else ""}</span>'
              f'<span class="data">{r["data"]:%d/%m}</span></div>',
              f'<span class="tipo" style="background:{cor}">{html.escape(RT.NOME_TIPO.get(tipo, tipo.title()))}</span>']
    if r["LOJA"]:
        partes.append(f'<div class="loja">{html.escape(r["LOJA"])}</div>')
    for m in RT.motivos(r["MOTIVOS"]):
        partes.append(f'<span class="mot">{html.escape(m.capitalize())}</span>')
    if r["OBJETIVO"]:
        partes.append(f'<div class="txt"><b>Objetivo:</b> {html.escape(r["OBJETIVO"].capitalize())}</div>')
    if r["OBS"]:
        partes.append(f'<div class="txt"><b>Obs.:</b> {html.escape(r["OBS"].capitalize())}</div>')
    if tipo in RT.TIPOS_PRESENCA and (r["COD_LOJA"], r["data"]) in chk_dia:
        partes.append('<div class="chk">Checklist enviado neste dia</div>')
    cartoes.append(f'<div class="fx-dia">{"".join(partes)}</div>')
st.markdown(f'<div class="fx-semana">{"".join(cartoes)}</div>', unsafe_allow_html=True)

# Resumo do coordenador no mês
mes = rot_v[(rot_v["COORDENADOR"] == coord) & (rot_v["competencia"] == ctx.comp)]
if len(mes):
    vis = RT.presencas(mes)
    ui.cards([
        dict(numero=int((mes["TIPO"] == "VISITA").sum()), rotulo="Dias de visita no mês", sub="no roteiro vigente",
             cor=ui.VERDE_CLARO),
        dict(numero=int((mes["TIPO"] == "BASE").sum()), rotulo="Dias na base", sub="no roteiro vigente", cor=C.COR_AZUL),
        dict(numero=vis["COD_LOJA"].nunique(), rotulo="Lojas diferentes no mês", 
             sub=f"de {int((h['coordenador_mes'] == coord).sum())} na carteira", cor="#ffffff"),
    ], minimo=180)
