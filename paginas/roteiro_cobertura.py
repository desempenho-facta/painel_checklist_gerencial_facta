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

ui.faixa(f"Meta de visitas por loja no mês: <b>{RT.META_VISITAS_PERTO}</b> nas lojas de fácil acesso e "
         f"<b>{RT.META_VISITAS_LONGE}</b> nas distantes (mais de {RT.DISTANCIA_LOJA_DISTANTE_KM} km da base do coordenador). "
         "Conta os dias de visita e de base na loja no roteiro vigente, incluindo os já planejados para o resto do mês. "
         "Priorize as lojas que estão há mais tempo sem visita.", pin="Regra")

cb = RT.cobertura(h, rot, d["respostas"], ctx.comp, ctx.hoje)
cb = cb.merge(h[["COD_LOJAS", "LOJA", "regional_mes", "score", "risco", "maturidade", "status"]], on="COD_LOJAS", how="left")
com_rot = set(rot.loc[rot["vigente"] & (rot["competencia"] == ctx.comp), "COORDENADOR"])
cb["tem_roteiro"] = cb["coordenador_mes"].isin(com_rot)
base = cb[cb["tem_roteiro"]]
fora = cb[~cb["tem_roteiro"]]

if base.empty:
    st.info("Nenhum coordenador desta visão mandou roteiro neste mês.")
    st.stop()

n = len(base)
atingiu = int((base["situacao_meta"] == "Meta atingida").sum())
sem = int((base["situacao_meta"] == "Sem visita no mês").sum())
mais30 = int((base["dias_sem_visita"].isna() | (base["dias_sem_visita"] > 30)).sum())
alerta = base[(base["risco"].isin(["Risco crítico", "Risco alto"]) | (base["maturidade"] == "Reativa"))
              & (base["visitas_mes"] == 0)]

ui.cards([
    dict(numero=ui.pct(atingiu / n, 0), rotulo="Lojas com a meta de visitas", sub=f"{atingiu} de {n} lojas",
         cor=ui.cor_cobertura(atingiu / n)),
    dict(numero=sem, rotulo="Lojas sem visita no mês", sub=ui.pct(sem / n, 0) + " da carteira",
         cor=ui.VERMELHO_CLARO if sem else ui.VERDE_CLARO),
    dict(numero=mais30, rotulo="Há mais de 30 dias sem visita", sub="ou nunca visitadas desde julho",
         cor=ui.VERMELHO_CLARO if mais30 else ui.VERDE_CLARO),
    dict(numero=len(alerta), rotulo="Lojas em risco sem visita", sub="risco alto, crítico ou reativa",
         cor=ui.VERMELHO_CLARO if len(alerta) else ui.VERDE_CLARO,
         ajuda="Lojas com risco alto ou crítico, ou maturidade reativa no checklist do mês, sem dia de visita no roteiro."),
], minimo=190)
if len(fora):
    st.caption(f"Os números acima consideram as {n} lojas dos coordenadores que mandaram roteiro neste mês. "
               f"Outras {len(fora)} lojas são de coordenadores sem roteiro no mês e aparecem só na tabela.")

c1, c2 = st.columns(2)
with c1:
    ui.secao("Há quanto tempo a loja não recebe visita")
    faixa = base["dias_sem_visita"].map(RT.faixa_sem_visita)
    cont = [int((faixa == f).sum()) for f in RT.ORDEM_SEM_VISITA]
    cores = [ui.VERDE_CLARO, C.COR_AMBAR, "#E07020", ui.VERMELHO_CLARO, "#8B1A1A"]
    hover = [f"<b>{f}: {c} lojas</b><br>" + ui.lista_hover(sorted(base.loc[faixa == f, "LOJA"])) for f, c in
             zip(RT.ORDEM_SEM_VISITA, cont)]
    ui.grafico(ui.barras_h(cont, RT.ORDEM_SEM_VISITA, cores, altura=70 + 44 * 5, hover=hover))
with c2:
    ui.secao("Meta de visitas no mês")
    cont = [int((base["situacao_meta"] == s).sum()) for s in RT.ORDEM_META]
    hover = [f"<b>{s}: {c} lojas</b><br>" + ui.lista_hover(sorted(base.loc[base["situacao_meta"] == s, "LOJA"]))
             for s, c in zip(RT.ORDEM_META, cont)]
    ui.grafico(ui.barras_h(cont, RT.ORDEM_META, [ui.VERDE_CLARO, C.COR_AMBAR, ui.VERMELHO_CLARO], altura=70 + 44 * 3,
                           hover=hover))
    acesso = base["acesso"].value_counts()
    st.caption(" · ".join(f"{a}: {int(acesso.get(a, 0))} lojas" for a in
                          ["Fácil acesso", "Distante", "Sem localização", "Sem base no roteiro"] if acesso.get(a, 0)))

# Concentração
top = base[base["visitas_mes"] > 0].sort_values("visitas_mes", ascending=False).head(10)
if len(top):
    ui.secao("Lojas com mais dias de presença no mês", "visita ou base; ajuda a ver concentração em poucas lojas")
    ui.grafico(ui.barras_h(top["visitas_mes"], top["LOJA"], [C.COR_AZUL] * len(top), altura=70 + 34 * len(top),
                           hover=[f"<b>{l}</b><br>{v} dias na loja · meta {m}" for l, v, m in
                                  zip(top["LOJA"], top["visitas_mes"], top["meta_visitas"])]))

# Prioridade
ui.secao("Prioridade de visita", "as lojas há mais tempo sem visita aparecem primeiro")
f1, f2, f3 = st.columns([1.2, 1, 0.9], vertical_alignment="bottom")
filtro_meta = f1.multiselect("Meta no mês", RT.ORDEM_META, placeholder="Todas")
filtro_acesso = f2.multiselect("Acesso", ["Fácil acesso", "Distante", "Sem localização", "Sem base no roteiro"],
                               placeholder="Todos")
incluir_fora = f3.toggle("Incluir lojas sem roteiro", value=False,
                         help="Mostra também as lojas de coordenadores que não mandaram roteiro no mês.")
t = cb if incluir_fora else base
if filtro_meta:
    t = t[t["situacao_meta"].isin(filtro_meta)]
if filtro_acesso:
    t = t[t["acesso"].isin(filtro_acesso)]

tab = pd.DataFrame({
    "Loja": t["LOJA"],
    "Coordenador": t["coordenador_mes"].str.title(),
    "Dias sem visita": t["dias_sem_visita"].map(lambda x: "nunca visitada" if pd.isna(x) else str(int(x))),
    "Última visita": t["ultima_visita"].map(RT.data_curta),
    "Próxima no roteiro": t["proxima_visita"].map(RT.data_curta),
    "Visitas no mês": t["visitas_mes"].astype(str) + " de " + t["meta_visitas"].astype(str)
                      + t["dias_base_mes"].map(lambda b: f" ({b} na base)" if b else ""),
    "Meta no mês": t["situacao_meta"],
    "Acesso": t["acesso"],
    "Distância da base": t["distancia_km"].map(lambda x: "" if pd.isna(x) else f"{x:.0f} km"),
    "Score": t["score"].map(lambda v: "" if pd.isna(v) else ui.num(v)),
    "Risco": t["risco"].fillna(""),
    "_o": t["dias_sem_visita"].fillna(10_000),
}).sort_values("_o", ascending=False).drop(columns="_o")

st.dataframe(ui.estilo_tabela(tab, {"Meta no mês": {"Meta atingida": C.COR_VERDE, "Abaixo da meta": C.COR_AMBAR,
                                                    "Sem visita no mês": C.COR_VERMELHO},
                                    "Risco": ui.CORES_RISCO}),
             hide_index=True, use_container_width=True, height=min(38 * (len(tab) + 1), 720),
             column_config={
                 "Loja": st.column_config.TextColumn(width=280, pinned=True),
                 "Coordenador": st.column_config.TextColumn(width=240),
                 "Dias sem visita": st.column_config.TextColumn(
                     help="Dias desde o último dia de visita ou base na loja até hoje. Conta o roteiro de qualquer coordenador."),
                 "Visitas no mês": st.column_config.TextColumn(
                     help="Dias na loja no roteiro do mês (visita ou base, feitos e planejados) e a meta da loja."),
                 "Acesso": st.column_config.TextColumn(
                     help=f"Distante: mais de {RT.DISTANCIA_LOJA_DISTANTE_KM} km em linha reta da base do coordenador. "
                          "A base é a loja que ele mais marca como BASE no roteiro e a posição da loja vem dos checklists. "
                          "Sem localização ou sem base, vale a meta de fácil acesso."),
             })
st.caption(f"{len(tab)} lojas. A distância é em linha reta e pode ser menor que a da estrada.")
