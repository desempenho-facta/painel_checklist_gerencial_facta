import pandas as pd
import streamlit as st

from core import config as C
from core import dados
from core import regras as R
from core import ui

ctx = st.session_state["ctx"]
d = dados.carregar()
h = ctx.hier()
pre = h[h["status"] == "Preencheu"]

ui.faixa("Loja em caso grave: o preenchimento do mês tem pelo menos um destes sinais: "
         f"<b>{', '.join(C.SINAIS_GRAVES)}</b>. O tempo conta os preenchimentos seguidos com o sinal; "
         "mês sem preenchimento não zera a contagem.", pin="Regra")

if pre.empty:
    st.info("Nenhum preenchimento neste mês para esta visão.")
    st.stop()

g = R.casos_graves(d["validos"], ctx.comp)
g = g[g["COD_LOJAS"].isin(set(pre["COD_LOJAS"]))]
g = g.merge(pre[["COD_LOJAS", "LOJA", "coordenador_mes", "score", "supervisao_especial"]], on="COD_LOJAS")

n3 = int((g["preenchimentos_seguidos"] >= 3).sum())
ui.cards([
    dict(numero=len(g), rotulo="Lojas em caso grave", sub=ui.pct(len(g) / len(pre), 0) + " das que preencheram",
         cor=ui.VERMELHO_CLARO if len(g) else ui.VERDE_CLARO),
    dict(numero=n3, rotulo="Há 3 preenchimentos ou mais", sub="casos que não estão saindo",
         cor=ui.VERMELHO_CLARO if n3 else ui.VERDE_CLARO),
    dict(numero=int((g["qtd_sinais"] >= 3).sum()), rotulo="Com 3 sinais ou mais", sub="situação mais pesada", cor=C.COR_AMBAR),
    dict(numero=int((g["preenchimentos_seguidos"] == 1).sum()), rotulo="Entraram neste mês",
         sub="primeiro preenchimento com sinal", cor=C.COR_AMBAR),
], minimo=180)

st.markdown("**Quantas lojas carregam cada sinal**")
contagem = {s: int(g["sinais"].map(lambda l, s=s: s in l).sum()) for s in C.SINAIS_GRAVES}
hover = [f"<b>{s}: {n} lojas</b><br>" + ui.lista_hover(sorted(g.loc[g["sinais"].map(lambda l, s=s: s in l), "LOJA"]))
         for s, n in contagem.items()]
ui.grafico(ui.barras_h(list(contagem.values()), list(contagem), [C.COR_VERMELHO] * len(contagem),
                       altura=60 + 42 * len(contagem), hover=hover))

st.markdown("**Lojas em caso grave** (as que estão há mais tempo primeiro)")
filtro = st.multiselect("Sinal", list(C.SINAIS_GRAVES), placeholder="Todos os sinais")
if filtro:
    g = g[g["sinais"].map(lambda l: any(s in l for s in filtro))]


def descreve(por_sinal: dict) -> str:
    return " · ".join(f"{s} ({n} {'seguido' if n == 1 else 'seguidos'})" for s, n in por_sinal.items())


tab = pd.DataFrame({
    "Loja": g["LOJA"],
    "Coordenador": g["coordenador_mes"].str.title(),
    "Em caso grave há": g["preenchimentos_seguidos"].map(lambda n: f"{n} {'preenchimento' if n == 1 else 'preenchimentos'}"),
    "Desde": g["desde"].map(lambda m: R.rotulo_mes(m)[:3] + "/" + str(m.year)[2:]),
    "Sinais": g["qtd_sinais"].astype(str),
    "Quais sinais e há quanto tempo": g["por_sinal"].map(descreve),
    "Score": g["score"].map(ui.num),
    "Supervisão especial": g["supervisao_especial"].map({True: "Sim", False: ""}),
    "_t": g["preenchimentos_seguidos"], "_s": g["qtd_sinais"],
}).sort_values(["_t", "_s"], ascending=False).drop(columns=["_t", "_s"])

st.dataframe(ui.estilo_tabela(tab, {"Supervisão especial": {"Sim": C.COR_LARANJA}}), hide_index=True,
             use_container_width=True, height=min(38 * (len(tab) + 1), 720),
             column_config={"Loja": st.column_config.TextColumn(width=280),
                            "Coordenador": st.column_config.TextColumn(width=240),
                            "Em caso grave há": st.column_config.TextColumn(
                 help="Preenchimentos seguidos com pelo menos um sinal grave, mesmo que o sinal tenha mudado no caminho."),
                 "Quais sinais e há quanto tempo": st.column_config.TextColumn(width=380,
                 help="Sinais do preenchimento do mês e há quantos preenchimentos seguidos cada um aparece.")})
st.caption("Abra o Diagnóstico da loja para ver as respostas que levaram a cada sinal.")
