import pandas as pd
import streamlit as st

from core import config as C
from core import dados
from core import regras as R
from core import ui

ctx = st.session_state["ctx"]
d = dados.carregar()
h = ctx.hier()
pre = h[(h["status"] == "Preencheu") & h["conta"]]
val_mes = d["validos"][d["validos"]["competencia"] == ctx.comp].set_index("COD_LOJAS")

ui.topo("Risco e estrutura", f"{ctx.rotulo_visao} · {R.rotulo_mes(ctx.comp)}")
if pre.empty:
    st.info("Nenhum preenchimento que conte neste mês para esta visão.")
    st.stop()

st.markdown("#### Onde o dinheiro está escapando")
st.caption("Nível de risco: quantos Não a loja deu em Q31 (inadimplência), Q24 (pendências) e Q32 (portabilidade).")
cont = pre["risco"].value_counts().reindex(list(ui.CORES_RISCO)).fillna(0).astype(int)
c = st.columns(4)
for col, (nivel, cor) in zip(c, ui.CORES_RISCO.items()):
    with col:
        ui.card(cont[nivel], nivel, ui.pct(cont[nivel] / len(pre), 0) + " das lojas",
                cor="#4CAF50" if nivel == "Sem risco" else cor, ajuda=C.AJUDA["risco"])

risco = pre[pre["falhas_criticas"] > 0].copy()
for q, tema in C.PERGUNTAS_RISCO.items():
    risco[tema.capitalize()] = risco["COD_LOJAS"].map(val_mes[q]).map({"Não": "Não", "Sim": "Sim"})
risco = risco.sort_values("falhas_criticas", ascending=False)
st.write("")
st.markdown("**Lojas com pelo menos uma falha crítica** (comece pelas de risco crítico)")
tab = risco[["LOJA", "coordenador_mes", "risco"] + [t.capitalize() for t in C.PERGUNTAS_RISCO.values()]]
tab = tab.rename(columns={"LOJA": "Loja", "coordenador_mes": "Coordenador", "risco": "Risco"})
tab["Coordenador"] = tab["Coordenador"].str.title()
st.dataframe(ui.estilo_tabela(tab, {"Risco": ui.CORES_RISCO,
                                    **{t.capitalize(): {"Não": C.COR_VERMELHO} for t in C.PERGUNTAS_RISCO.values()}}),
             hide_index=True, use_container_width=True)

st.divider()
st.markdown("#### Situação estrutural (Q36)")
ui.destaque("<b>A leitura é invertida.</b> Com chamados abertos é bom: o problema de estrutura foi registrado. "
            "Sem chamados abertos é alerta, porque provavelmente existe problema que não foi reportado.")
sem = pre[pre["estrutura"] == "Sem chamados abertos"]
a, b = st.columns(2)
with a:
    ui.card(int((pre["estrutura"] == "Com chamados abertos").sum()), "Com chamados abertos", cor="#4CAF50",
            ajuda=C.AJUDA["estrutura"])
with b:
    ui.card(len(sem), "Sem chamados abertos", "alerta", cor="#E5484D" if len(sem) else "#4CAF50", ajuda=C.AJUDA["estrutura"])
if len(sem):
    st.dataframe(pd.DataFrame({"Loja": sem["LOJA"], "Coordenador": sem["coordenador_mes"].str.title(),
                               "Supervisor": sem["SUPERVISOR"].str.title(),
                               "Preenchido em": pd.to_datetime(sem["timestamp"]).dt.strftime("%d/%m/%Y")}),
                 hide_index=True, use_container_width=True)
