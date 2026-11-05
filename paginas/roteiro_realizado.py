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
coords = sorted(h["coordenador_mes"].dropna().unique())
rot_v = rot[rot["COORDENADOR"].isin(coords)]
lojas_visao = set(h["COD_LOJAS"])

ui.faixa("Cruza cada checklist do mês com o roteiro de quem preencheu. <b>No dia da visita planejada</b>: o roteiro "
         "marcava visita ou base naquela loja no mesmo dia. A localização compara o ponto do checklist com o ponto habitual "
         f"da loja (mediana dos checklists dela); mais de {RT.LONGE_DA_LOJA_KM} km conta como longe da loja.", pin="Regra")

pr = RT.planejado_realizado(rot_v, d["validos"], d["respostas"], ctx.comp)
pr = pr[pr["COD_LOJAS"].isin(lojas_visao)]
if pr.empty:
    st.info("Nenhum checklist neste mês para esta visão.")
    st.stop()
pr["situacao"] = RT.classificar_checklist(pr)
n = len(pr)
no_dia = int((pr["situacao"] == RT.ORDEM_CHECKLIST[0]).sum())
com_rot = pr[pr["roteiro_na_semana"]]
mot = RT.checklists_motivo(rot_v, d["validos"], ctx.comp, ctx.hoje)
mot = mot[mot["COD_LOJA"].isin(lojas_visao)]
longe = int((pr["local"] == "Longe da loja").sum())

ui.cards([
    dict(numero=ui.pct(no_dia / n, 0), rotulo="Checklists no dia da visita", sub=f"{no_dia} de {n} checklists do mês",
         cor=ui.cor_cobertura(no_dia / n)),
    dict(numero=ui.pct((com_rot["situacao"] == RT.ORDEM_CHECKLIST[0]).mean() if len(com_rot) else None, 0),
         rotulo="Entre quem tinha roteiro", sub=f"{len(com_rot)} checklists com roteiro na semana",
         cor=ui.cor_cobertura((com_rot["situacao"] == RT.ORDEM_CHECKLIST[0]).mean() if len(com_rot) else None),
         ajuda="Só os checklists de coordenadores que tinham roteiro para aquela semana."),
    dict(numero=f"{int(mot['feito_no_dia'].sum())} de {len(mot)}", rotulo="Visitas para checklist cumpridas no dia",
         sub=f"{int(mot['feito_no_mes'].sum())} saíram em algum dia do mês",
         cor=ui.cor_cobertura(mot["feito_no_dia"].mean() if len(mot) else None),
         ajuda="Dias de visita ou base até hoje com o motivo CHECKLIST MENSAL no roteiro."),
    dict(numero=longe, rotulo="Feitos longe da loja", sub=f"a mais de {RT.LONGE_DA_LOJA_KM} km do ponto habitual",
         cor=ui.VERMELHO_CLARO if longe else ui.VERDE_CLARO),
], minimo=190)

c1, c2 = st.columns(2)
with c1:
    ui.secao("Checklists do mês em relação ao roteiro")
    cont = [int((pr["situacao"] == s).sum()) for s in RT.ORDEM_CHECKLIST]
    hover = [f"<b>{s}: {c}</b><br>" + ui.lista_hover(sorted(pr.loc[pr["situacao"] == s, "LOJA"])) for s, c in
             zip(RT.ORDEM_CHECKLIST, cont)]
    ui.grafico(ui.barras_h(cont, RT.ORDEM_CHECKLIST, [ui.VERDE_CLARO, C.COR_AMBAR, "#E07020", "#666"],
                           altura=70 + 44 * 4, hover=hover))
with c2:
    ui.secao("Onde o checklist foi preenchido")
    locais = ["Na loja", "Longe da loja", "Sem localização", "Sem referência"]
    cont = [int((pr["local"] == s).sum()) for s in locais]
    hover = [f"<b>{s}: {c}</b><br>" + ui.lista_hover(sorted(pr.loc[pr["local"] == s, "LOJA"])) for s, c in zip(locais, cont)]
    ui.grafico(ui.barras_h(cont, locais, [ui.VERDE_CLARO, ui.VERMELHO_CLARO, "#666", "#555"], altura=70 + 44 * 4,
                           hover=hover))
    st.caption("Sem localização: o coordenador não capturou a localização. Sem referência: a loja tem um único "
               "checklist com localização, então ainda não há ponto habitual para comparar.")

# Por coordenador
ui.secao("Por coordenador")
g = pr.groupby("COORDENADOR").agg(
    checklists=("COD_LOJAS", "size"),
    no_dia=("situacao", lambda s: int((s == RT.ORDEM_CHECKLIST[0]).sum())),
    outro_dia=("situacao", lambda s: int((s == RT.ORDEM_CHECKLIST[1]).sum())),
    fora=("situacao", lambda s: int((s == RT.ORDEM_CHECKLIST[2]).sum())),
    sem_rot=("situacao", lambda s: int((s == RT.ORDEM_CHECKLIST[3]).sum())),
    longe=("local", lambda s: int((s == "Longe da loja").sum())),
).reset_index()
tab = pd.DataFrame({
    "Coordenador": g["COORDENADOR"].str.title(),
    "Checklists": g["checklists"],
    "No dia da visita": g["no_dia"],
    "Loja no roteiro, outro dia": g["outro_dia"],
    "Loja fora do roteiro": g["fora"],
    "Sem roteiro na semana": g["sem_rot"],
    "Longe da loja": g["longe"],
    "% no dia": (g["no_dia"] / g["checklists"]).map(lambda x: ui.pct(x, 0)),
    "_o": g["no_dia"] / g["checklists"],
}).sort_values("_o").drop(columns="_o")
st.dataframe(tab, hide_index=True, use_container_width=True, height=min(38 * (len(tab) + 1), 520),
             column_config={"Coordenador": st.column_config.TextColumn(width=260, pinned=True)})

# Detalhe
ui.secao("Checklists fora do dia planejado", "para conversar com o coordenador")
fora_dia = pr[pr["situacao"] != RT.ORDEM_CHECKLIST[0]].copy()
vis = RT.vigentes(rot_v)
vis = RT.presencas(vis)
vis = vis[vis["competencia"] == ctx.comp]
datas = {loja: ", ".join(f"{x:%d/%m}" for x in sorted(g.unique())) for loja, g in vis.groupby("COD_LOJA")["data"]}
det = pd.DataFrame({
    "Loja": fora_dia["LOJA"],
    "Coordenador": fora_dia["COORDENADOR"].str.title(),
    "Checklist em": fora_dia["timestamp"].dt.strftime("%d/%m/%Y %H:%M"),
    "Situação": fora_dia["situacao"],
    "Dias na loja no roteiro": fora_dia["COD_LOJAS"].map(datas).fillna(""),
    "Local": fora_dia["local"],
    "Distância da loja": fora_dia["distancia_km"].map(lambda x: "" if pd.isna(x) else f"{x:.1f} km".replace(".", ",")),
}).sort_values(["Coordenador", "Checklist em"])
st.dataframe(ui.estilo_tabela(det, {"Local": {"Longe da loja": C.COR_VERMELHO, "Na loja": C.COR_VERDE}}),
             hide_index=True, use_container_width=True, height=min(38 * (len(det) + 1), 620),
             column_config={"Loja": st.column_config.TextColumn(width=280, pinned=True),
                            "Coordenador": st.column_config.TextColumn(width=240),
                            "Situação": st.column_config.TextColumn(width=230)})
