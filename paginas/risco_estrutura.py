import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import config as C
from core import dados
from core import ui

ctx = st.session_state["ctx"]
d = dados.carregar()
h = ctx.hier()
pre = h[(h["status"] == "Preencheu") & h["conta"]]
val_mes = d["validos"][d["validos"]["competencia"] == ctx.comp].set_index("COD_LOJAS")

if pre.empty:
    st.info("Nenhum preenchimento que conte neste mês para esta visão.")
    st.stop()

st.markdown("#### Onde o dinheiro está escapando")
st.caption("Nível de risco: quantos Não a loja deu em Q31 (inadimplência), Q24 (pendências) e Q32 (portabilidade).")
cont = pre["risco"].value_counts().reindex(list(ui.CORES_RISCO)).fillna(0).astype(int)
ui.cards([dict(numero=int(cont[n]), rotulo=n, sub=f"{ui.pct(cont[n] / len(pre), 0)} das lojas",
               cor=ui.VERDE_CLARO if n == "Sem risco" else cor, ajuda=C.AJUDA["risco"])
          for n, cor in ui.CORES_RISCO.items()], minimo=160)

risco = pre[pre["falhas_criticas"] > 0].copy()
for q, tema in C.PERGUNTAS_RISCO.items():
    risco[tema.capitalize()] = risco["COD_LOJAS"].map(val_mes[q]).map({"Não": "Não", "Sim": "Sim"})
risco = risco.sort_values("falhas_criticas", ascending=False)
st.markdown("**Lojas com pelo menos uma falha crítica** (comece pelas de risco crítico)")
if risco.empty:
    st.success("Nenhuma loja com falha crítica neste mês.")
else:
    tab = risco[["LOJA", "coordenador_mes", "risco"] + [t.capitalize() for t in C.PERGUNTAS_RISCO.values()]]
    tab = tab.rename(columns={"LOJA": "Loja", "coordenador_mes": "Coordenador", "risco": "Risco"})
    tab["Coordenador"] = tab["Coordenador"].str.title()
    st.dataframe(ui.estilo_tabela(tab, {"Risco": ui.CORES_RISCO,
                                        **{t.capitalize(): {"Não": C.COR_VERMELHO} for t in C.PERGUNTAS_RISCO.values()}}),
                 hide_index=True, use_container_width=True,
                 column_config={"Loja": st.column_config.TextColumn(width=280), "Coordenador": st.column_config.TextColumn(width=240)})

st.divider()
st.markdown("#### Situação estrutural (Q36)")
ui.destaque("<b>A leitura é invertida.</b> Com chamados abertos é bom: o problema de estrutura foi registrado. "
            "Sem chamados abertos é alerta, porque provavelmente existe problema que não foi reportado.")
com = int((pre["estrutura"] == "Com chamados abertos").sum())
sem = pre[pre["estrutura"] == "Sem chamados abertos"]
ui.cards([
    dict(numero=com, rotulo="Com chamados abertos", sub=f"{ui.pct(com / len(pre), 0)} das lojas · situação esperada",
         cor=ui.VERDE_CLARO, ajuda=C.AJUDA["estrutura"]),
    dict(numero=len(sem), rotulo="Sem chamados abertos", sub=f"{ui.pct(len(sem) / len(pre), 0)} das lojas · alerta",
         cor=ui.VERMELHO_CLARO if len(sem) else ui.VERDE_CLARO, ajuda=C.AJUDA["estrutura"]),
], minimo=240)

grupo = {"rede": ("regional_mes", "regional"), "regional": ("coordenador_mes", "coordenador")}.get(ctx.nivel)
a, b = st.columns([1.1, 1], gap="large") if grupo else (st.container(), None)
if grupo:
    col, nome_g = grupo
    with a:
        st.markdown(f"**Distribuição dos chamados por {nome_g}**")
        g = pre.groupby(col)["estrutura"].value_counts().unstack(fill_value=0)
        g = g.reindex(columns=["Com chamados abertos", "Sem chamados abertos"], fill_value=0)
        g = g.sort_values("Sem chamados abertos", ascending=True)
        nomes = [n.title() for n in g.index]
        fig = go.Figure([
            go.Bar(y=nomes, x=g["Com chamados abertos"], name="Com chamados", orientation="h", marker_color=C.COR_VERDE,
                   hovertemplate="%{y}<br>Com chamados: %{x}<extra></extra>"),
            go.Bar(y=nomes, x=g["Sem chamados abertos"], name="Sem chamados", orientation="h", marker_color=C.COR_VERMELHO,
                   hovertemplate="%{y}<br>Sem chamados: %{x}<extra></extra>"),
        ])
        fig.update_layout(**{**ui.LAYOUT_GRAFICO, "showlegend": True}, barmode="stack", height=max(260, 34 * len(g) + 80),
                          legend=dict(orientation="h", y=-0.15), xaxis=dict(gridcolor="#3a3838"))
        ui.grafico(fig)
alvo = b if grupo else a
with alvo:
    st.markdown("**Lojas sem chamados abertos**")
    if len(sem):
        st.dataframe(pd.DataFrame({"Loja": sem["LOJA"], "Coordenador": sem["coordenador_mes"].str.title(),
                                   "Supervisor": sem["SUPERVISOR"].str.title(),
                                   "Preenchido em": pd.to_datetime(sem["timestamp"]).dt.strftime("%d/%m/%Y")}),
                     hide_index=True, use_container_width=True,
                     column_config={"Loja": st.column_config.TextColumn(width=250)})
    else:
        st.success("Todas as lojas desta visão estão com os chamados de estrutura abertos.")
