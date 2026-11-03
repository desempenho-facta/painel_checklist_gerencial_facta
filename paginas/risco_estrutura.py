import pandas as pd
import plotly.graph_objects as go
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

# ---------------------------------------------------------------------------
# Chamados informados na Q36 (motivo, número, abertura e prazo do SLA)
# ---------------------------------------------------------------------------
st.divider()
st.markdown("#### Chamados de estrutura informados", help=C.AJUDA["sla"])
vm = d["validos"][(d["validos"]["competencia"] == ctx.comp) & d["validos"]["COD_LOJAS"].isin(set(pre["COD_LOJAS"]))]
ch = R.chamados_q36(vm)
if ch.empty:
    st.info("Nenhum chamado informado neste mês para esta visão. O detalhamento da Q36 (motivo, número e data de "
            "abertura) vale para os preenchimentos feitos a partir de novembro de 2026.")
else:
    fora = ch[ch["situacao_sla"] == "Fora do prazo"]
    ui.cards([
        dict(numero=len(ch), rotulo="Chamados informados", sub=f"em {ch['COD_LOJAS'].nunique()} lojas"),
        dict(numero=len(fora), rotulo="Fora do prazo do SLA", sub=f"{ui.pct(len(fora) / len(ch), 0)} dos chamados",
             cor=ui.VERMELHO_CLARO if len(fora) else ui.VERDE_CLARO, ajuda=C.AJUDA["sla"]),
        dict(numero=int((ch["situacao_sla"] == "Dentro do prazo").sum()), rotulo="Dentro do prazo",
             sub="ainda no tempo do SLA", cor=ui.VERDE_CLARO),
        dict(numero=f"{int(ch['dias_aberto'].max())} dias" if ch["dias_aberto"].notna().any() else "sem dado",
             rotulo="Chamado mais antigo", sub="da abertura até o preenchimento", cor=C.COR_AMBAR),
    ], minimo=170)

    a, b = st.columns([1.1, 1], gap="large")
    with a:
        st.markdown("**Chamados por motivo**")
        ordem = ch["motivo"].value_counts().index.tolist()
        cores = {"Fora do prazo": C.COR_VERMELHO, "Dentro do prazo": C.COR_VERDE, "Sem prazo definido": "#7a7a7a"}  # ordem da legenda
        fig = go.Figure()
        for sit, cor in cores.items():
            parte = ch[ch["situacao_sla"] == sit]
            cont = parte["motivo"].value_counts().reindex(ordem).fillna(0).astype(int)
            hover = [f"<b>{m.capitalize()}</b><br>{sit}: {n}<br>Prazo: "
                     + (f"{C.SLA_FACILITIES.get(m)} dias" if C.SLA_FACILITIES.get(m) else "sem prazo fixo") + "<br><br>"
                     + ui.lista_hover(sorted(parte.loc[parte["motivo"] == m, "LOJA"].unique()), limite=10)
                     for m, n in cont.items()]
            fig.add_trace(go.Bar(y=[m.capitalize() for m in ordem], x=cont.values, name=sit, orientation="h",
                                 marker_color=cor, customdata=hover, hovertemplate="%{customdata}<extra></extra>"))
        fig.update_layout(**{**ui.LAYOUT_GRAFICO, "showlegend": True}, barmode="stack",
                          height=max(240, 36 * len(ordem) + 90), legend=dict(orientation="h", y=-0.18, traceorder="normal"),
                          yaxis=dict(autorange="reversed"), xaxis=dict(gridcolor="#3a3838"))
        ui.grafico(fig)
    with b:
        st.markdown("**O que mais aparece no detalhe**")
        obs = vm.drop_duplicates("COD_LOJAS")[C.COL_Q36_OBS]
        palavras = (obs.str.upper().map(R.sem_acento).str.replace(r"[^A-ZÀ-Ü ]", " ", regex=True).str.split().explode())
        palavras = palavras[(palavras.str.len() >= 4) & ~palavras.isin(C.PALAVRAS_IGNORADAS_Q36)]
        top = palavras.value_counts().head(10)
        if top.empty:
            st.caption("Sem detalhes escritos neste mês.")
        else:
            base_obs = vm.drop_duplicates("COD_LOJAS")
            hover = [f"<b>{w.capitalize()}: {n} lojas</b><br>"
                     + ui.lista_hover(sorted(base_obs.loc[base_obs[C.COL_Q36_OBS].str.upper().map(R.sem_acento).str.contains(rf"\b{w}\b", regex=True), "LOJA"]), limite=10)
                     for w, n in top.items()]
            ui.grafico(ui.barras_h(top.values, [w.capitalize() for w in top.index], C.COR_AZUL,
                                   altura=60 + 30 * len(top), hover=hover))
            st.caption("Palavras que mais se repetem nos detalhes da Q36, sem as palavras comuns (loja, para, está...). "
                       "Passe o mouse para ver as lojas.")

    st.markdown("**Lista de chamados** (os fora do prazo primeiro)")
    ordem_sit = {"Fora do prazo": 0, "Dentro do prazo": 1, "Sem prazo definido": 2}
    t = ch.assign(_o=ch["situacao_sla"].map(ordem_sit)).sort_values(["_o", "dias_aberto"], ascending=[True, False])
    tab = pd.DataFrame({
        "Loja": t["LOJA"], "Motivo": t["motivo"].str.capitalize(), "Chamado": t["chamado"],
        "Aberto em": t["abertura"].dt.strftime("%d/%m/%Y").fillna(""),
        "Dias em aberto": t["dias_aberto"].map(lambda v: "" if pd.isna(v) else str(int(v))),
        "Prazo (dias)": t["sla"].map(lambda v: "sem prazo" if pd.isna(v) else str(int(v))),
        "Situação": t["situacao_sla"], "Detalhe": t["detalhe"].str.capitalize(),
    })
    st.dataframe(ui.estilo_tabela(tab, {"Situação": {"Fora do prazo": C.COR_VERMELHO, "Dentro do prazo": C.COR_VERDE}}),
                 hide_index=True, use_container_width=True, height=min(38 * (len(tab) + 1), 560),
                 column_config={"Loja": st.column_config.TextColumn(width=240),
                                "Motivo": st.column_config.TextColumn(width=220),
                                "Detalhe": st.column_config.TextColumn(width=360)})
