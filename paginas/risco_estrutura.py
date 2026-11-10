import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import atuacoes as A
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
st.caption("Nível de risco: quantas falhas a loja teve em Q31 (inadimplência), Q24 (pendências) e Q32 (portabilidade). "
           "Falha é Não, Nunca ou Às vezes.")
cont = pre["risco"].value_counts().reindex(list(ui.CORES_RISCO)).fillna(0).astype(int)
ui.cards([dict(numero=int(cont[n]), rotulo=n, sub=f"{ui.pct(cont[n] / len(pre), 0)} das lojas",
               cor=ui.VERDE_CLARO if n == "Sem risco" else cor, ajuda=C.AJUDA["risco"])
          for n, cor in ui.CORES_RISCO.items()], minimo=160)

risco = pre[pre["falhas_criticas"] > 0].copy()
for q, tema in C.PERGUNTAS_RISCO.items():
    risco[tema.capitalize()] = risco["COD_LOJAS"].map(val_mes[q]).fillna("")
risco = risco.sort_values("falhas_criticas", ascending=False)
st.markdown("**Lojas com pelo menos uma falha crítica** (comece pelas de risco crítico)")
if risco.empty:
    st.success("Nenhuma loja com falha crítica neste mês.")
else:
    tab = risco[["LOJA", "coordenador_mes", "risco"] + [t.capitalize() for t in C.PERGUNTAS_RISCO.values()]]
    tab = tab.rename(columns={"LOJA": "Loja", "coordenador_mes": "Coordenador", "risco": "Risco"})
    tab["Coordenador"] = tab["Coordenador"].str.title()
    st.dataframe(ui.estilo_tabela(tab, {"Risco": ui.CORES_RISCO,
                                        **{t.capitalize(): {r: C.COR_VERMELHO for r in C.RESPOSTAS_NAO}
                                           for t in C.PERGUNTAS_RISCO.values()}}),
                 hide_index=True, use_container_width=True,
                 column_config={"Loja": st.column_config.TextColumn(width=280), "Coordenador": st.column_config.TextColumn(width=240)})

st.divider()
st.markdown("#### Situação estrutural (Q36)")
ui.destaque("<b>Demanda sem chamado é não conformidade:</b> há problema estrutural na loja e o chamado ainda não foi "
            "aberto. Sem pendências e com chamado aberto são situações regulares.")
CORES_ESTRUTURA = {C.ESTRUTURA_SEM_PENDENCIAS: C.COR_VERDE, C.ESTRUTURA_COM_CHAMADO: C.COR_AZUL,
                   C.ESTRUTURA_SEM_CHAMADO: C.COR_VERMELHO}
cont_e = pre["estrutura"].value_counts().reindex(C.ORDEM_ESTRUTURA).fillna(0).astype(int)
sem = pre[pre["estrutura"] == C.ESTRUTURA_SEM_CHAMADO]
ui.cards([
    dict(numero=int(cont_e[C.ESTRUTURA_SEM_PENDENCIAS]), rotulo="Sem pendências",
         sub=f"{ui.pct(cont_e[C.ESTRUTURA_SEM_PENDENCIAS] / len(pre), 0)} das lojas", cor=ui.VERDE_CLARO,
         ajuda=C.AJUDA["estrutura"]),
    dict(numero=int(cont_e[C.ESTRUTURA_COM_CHAMADO]), rotulo="Com chamado aberto",
         sub=f"{ui.pct(cont_e[C.ESTRUTURA_COM_CHAMADO] / len(pre), 0)} das lojas", cor=C.COR_AZUL,
         ajuda=C.AJUDA["estrutura"]),
    dict(numero=len(sem), rotulo="Demanda sem chamado",
         sub=f"{ui.pct(len(sem) / len(pre), 0)} das lojas · não conformidade",
         cor=ui.VERMELHO_CLARO if len(sem) else ui.VERDE_CLARO, ajuda=C.AJUDA["estrutura"]),
], minimo=200)

grupo = {"rede": ("regional_mes", "regional"), "regional": ("coordenador_mes", "coordenador")}.get(ctx.nivel)
if grupo:
    col, nome_g = grupo
    st.markdown(f"**Situação estrutural por {nome_g}**")
    g = pre.groupby(col)["estrutura"].value_counts().unstack(fill_value=0)
    g = g.reindex(columns=C.ORDEM_ESTRUTURA, fill_value=0).sort_values(C.ESTRUTURA_SEM_CHAMADO, ascending=True)
    nomes = [n.title() for n in g.index]
    fig = go.Figure([go.Bar(y=nomes, x=g[e], name=e, orientation="h", marker_color=CORES_ESTRUTURA[e],
                            hovertemplate="%{y}<br>" + e + ": %{x}<extra></extra>") for e in C.ORDEM_ESTRUTURA])
    fig.update_layout(**{**ui.LAYOUT_GRAFICO, "showlegend": True}, barmode="stack", height=max(260, 34 * len(g) + 80),
                      legend=dict(orientation="h", y=-0.15, traceorder="normal"), xaxis=dict(gridcolor="#3a3838"))
    ui.grafico(fig)

# ---------------------------------------------------------------------------
# Atuação da monitoria (aba Atuacoes_Chamados). Só o app da monitoria grava; os outros só leem.
# ---------------------------------------------------------------------------
pode_atuar = ctx.perfil == "monitoria"
atuacao = A.atuais()


def _colunas_atuacao(chaves: pd.Series) -> pd.DataFrame:
    reg = atuacao.reindex(chaves)
    return pd.DataFrame({"Atuado": reg["atuado"].fillna("").eq("Sim").values,
                         "Status": reg["status"].replace("", None).values,
                         "Observação": reg["observacao"].fillna("").values,
                         "Última atuação": (reg["responsavel"].fillna("") + reg["registrado_em"].fillna("").map(
                             lambda v: f" em {pd.Timestamp(v):%d/%m %H:%M}" if v else "")).str.strip().values})


def tabela_com_atuacao(tab: pd.DataFrame, chaves: pd.Series, extras: pd.DataFrame, chave_form: str,
                       cores: dict, larguras: dict):
    """Mostra a tabela com as colunas de atuação. Na monitoria, elas são editáveis e gravam na planilha."""
    atu = _colunas_atuacao(chaves)
    tab = tab.reset_index(drop=True)
    # Atuado e Status logo depois da loja, para ficarem à vista; observação e histórico no fim
    tab = pd.concat([tab[["Loja"]], atu[["Atuado", "Status"]], tab.drop(columns="Loja"),
                     atu[["Observação", "Última atuação"]]], axis=1)
    conf = {k: st.column_config.TextColumn(width=v) for k, v in larguras.items()}
    conf["Loja"] = st.column_config.TextColumn(width=larguras.get("Loja", 240), pinned=True)
    altura = min(36 * (len(tab) + 1) + 4, 560)
    if not pode_atuar:
        st.dataframe(ui.estilo_tabela(tab.assign(Atuado=tab["Atuado"].map({True: "Sim", False: ""}),
                                                 Status=tab["Status"].fillna("")), cores),
                     hide_index=True, use_container_width=True, height=altura, column_config=conf)
        return
    editaveis = ["Atuado", "Status", "Observação"]
    conf.update({
        "Atuado": st.column_config.CheckboxColumn("Atuado", width=70, help="Marque quando a monitoria atuar no item."),
        "Status": st.column_config.SelectboxColumn("Status", options=C.STATUS_ATUACAO, width=120),
        "Observação": st.column_config.TextColumn("Observação", width=260, max_chars=300),
    })
    with st.form(chave_form, border=False):
        editado = st.data_editor(ui.estilo_tabela(tab, cores), hide_index=True, use_container_width=True,
                                 height=altura, column_config=conf, key=f"{chave_form}_editor",
                                 disabled=[c for c in tab.columns if c not in editaveis])
        c1, c2 = st.columns([2, 1], vertical_alignment="bottom")
        resp = c1.text_input("Seu nome (fica registrado na atuação)", key=f"{chave_form}_resp",
                             value=st.session_state.get("atuacao_responsavel", ""))
        enviar = c2.form_submit_button("Salvar atuações", type="primary", use_container_width=True)
    if enviar:
        norm = lambda df: df[editaveis].astype(object).where(df[editaveis].notna(), "").astype(str)
        mudou = (norm(editado) != norm(tab)).any(axis=1)
        if not mudou.any():
            st.info("Nenhuma alteração para salvar.")
            return
        if not resp.strip():
            st.error("Informe seu nome para registrar a atuação.")
            return
        st.session_state["atuacao_responsavel"] = resp.strip()
        registros = []
        for i in editado.index[mudou]:
            r = editado.loc[i]
            status = r["Status"] if isinstance(r["Status"], str) else ""
            atuado = bool(r["Atuado"]) or bool(status)
            registros.append({"chave": chaves.iloc[i], **extras.iloc[i].to_dict(),
                              "atuado": "Sim" if atuado else "Não",
                              "status": (status or "Em tratativa") if atuado else "",
                              "observacao": (r["Observação"] if isinstance(r["Observação"], str) else "")
                              .replace("\n", " ").strip(),
                              "responsavel": resp.strip().upper()})
        try:
            A.salvar(registros)
        except Exception as e:
            st.error(f"Não foi possível gravar na planilha. Tente de novo.\n\n{e}")
            return
        st.toast(f"{len(registros)} {'atuação registrada' if len(registros) == 1 else 'atuações registradas'}.",
                 icon=":material/check_circle:")
        st.rerun()


vm = d["validos"][(d["validos"]["competencia"] == ctx.comp) & d["validos"]["COD_LOJAS"].isin(set(pre["COD_LOJAS"]))]

# Demandas sem chamado (não conformidade)
st.markdown("**Demandas sem chamado** (não conformidade: o chamado ainda não foi aberto)")
dsc = R.demandas_sem_chamado(vm)
if dsc.empty:
    st.success("Nenhuma loja desta visão informou demanda sem chamado neste mês.")
else:
    coord = pre.set_index("COD_LOJAS")["coordenador_mes"]
    dsc = dsc.sort_values(["LOJA", "item"]).reset_index(drop=True)
    tab = pd.DataFrame({
        "Loja": dsc["LOJA"], "Coordenador": dsc["COD_LOJAS"].map(coord).fillna("").str.title(),
        "Preenchido em": dsc["timestamp"].dt.strftime("%d/%m/%Y"),
        "Motivo": dsc["motivo"].str.capitalize().replace("", "Não informado (checklist antigo)"),
        "Descrição": dsc["detalhe"].str.capitalize(),
        "Coerência": dsc["coerencia"] + dsc["cita"].map(lambda c: f" ({c})" if c else ""),
    })
    chaves = pd.Series([A.chave_demanda(c, t, i) for c, t, i in zip(dsc["COD_LOJAS"], dsc["timestamp"], dsc["item"])])
    extras = pd.DataFrame({"cod_loja": dsc["COD_LOJAS"], "loja": dsc["LOJA"], "tipo": "Demanda sem chamado",
                           "chamado": "", "motivo": dsc["motivo"]})
    cores_c = {k: v for k, v in C.CORES_COERENCIA.items()}
    tabela_com_atuacao(tab, chaves, extras, "form_demandas",
                       {"Coerência": {t: c for t in tab["Coerência"].unique() for k, c in cores_c.items()
                                      if t.startswith(k)}},
                       {"Loja": 240, "Coordenador": 180, "Motivo": 200, "Descrição": 300, "Coerência": 170})

# ---------------------------------------------------------------------------
# Chamados informados na Q36 (motivo, número, abertura, prazo do SLA e coerência do detalhe)
# ---------------------------------------------------------------------------
st.divider()
st.markdown("#### Chamados de estrutura informados", help=C.AJUDA["sla"])
ch = R.chamados_q36(vm)
if ch.empty:
    st.info("Nenhum chamado informado neste mês para esta visão. O detalhamento da Q36 (motivo, número e data de "
            "abertura) vale para os preenchimentos feitos a partir de novembro de 2026.")
else:
    fora = ch[ch["situacao_sla"] == "Fora do prazo"]
    incoer = ch[ch["coerencia"].isin([C.CITA_OUTRO_MOTIVO, C.NAO_CITA_MOTIVO])]
    ui.cards([
        dict(numero=len(ch), rotulo="Chamados informados", sub=f"em {ch['COD_LOJAS'].nunique()} lojas"),
        dict(numero=len(fora), rotulo="Fora do prazo do SLA", sub=f"{ui.pct(len(fora) / len(ch), 0)} dos chamados",
             cor=ui.VERMELHO_CLARO if len(fora) else ui.VERDE_CLARO, ajuda=C.AJUDA["sla"]),
        dict(numero=len(incoer), rotulo="Detalhe a verificar", sub="não bate com o motivo do chamado",
             cor=C.COR_AMBAR if len(incoer) else ui.VERDE_CLARO, ajuda=C.AJUDA["coerencia"]),
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
        base_obs = ch.drop_duplicates(["COD_LOJAS", "detalhe"])
        palavras = (base_obs["detalhe"].str.upper().map(R.sem_acento).str.replace(r"[^A-ZÀ-Ü ]", " ", regex=True)
                    .str.split().map(lambda l: sorted(set(l)) if isinstance(l, list) else l).explode())
        palavras = palavras[(palavras.str.len() >= 4) & ~palavras.isin(C.PALAVRAS_IGNORADAS_Q36)]
        lojas_p = pd.DataFrame({"p": palavras, "LOJA": base_obs.loc[palavras.index, "LOJA"]}).drop_duplicates()
        top = lojas_p["p"].value_counts().head(10)
        if top.empty:
            st.caption("Sem detalhes escritos neste mês.")
        else:
            hover = [f"<b>{w.capitalize()}: {n} lojas</b><br>"
                     + ui.lista_hover(sorted(lojas_p.loc[lojas_p["p"] == w, "LOJA"]), limite=10) for w, n in top.items()]
            ui.grafico(ui.barras_h(top.values, [w.capitalize() for w in top.index], C.COR_AZUL,
                                   altura=60 + 30 * len(top), hover=hover))
            st.caption("Palavras que mais se repetem nos detalhes dos chamados, sem as palavras comuns "
                       "(loja, para, está...). Passe o mouse para ver as lojas.")

    st.markdown("**Lista de chamados** (os fora do prazo primeiro)", help=C.AJUDA["coerencia"])
    ordem_sit = {"Fora do prazo": 0, "Dentro do prazo": 1, "Sem prazo definido": 2}
    t = (ch.assign(_o=ch["situacao_sla"].map(ordem_sit))
         .sort_values(["_o", "dias_aberto"], ascending=[True, False]).reset_index(drop=True))
    tab = pd.DataFrame({
        "Loja": t["LOJA"], "Motivo": t["motivo"].str.capitalize(), "Chamado": t["chamado"],
        "Aberto em": t["abertura"].dt.strftime("%d/%m/%Y").fillna(""),
        "Dias em aberto": t["dias_aberto"].map(lambda v: "" if pd.isna(v) else str(int(v))),
        "Prazo (dias)": t["sla"].map(lambda v: "sem prazo" if pd.isna(v) else str(int(v))),
        "Situação": t["situacao_sla"],
        "Coerência": t["coerencia"] + t["cita"].map(lambda c: f" ({c})" if c else ""),
        "Detalhe": t["detalhe"].str.capitalize() + t["detalhe_unico"].map(lambda u: " [texto único do checklist]" if u else ""),
    })
    chaves = pd.Series([A.chave_chamado(c, n) for c, n in zip(t["COD_LOJAS"], t["chamado"])])
    extras = pd.DataFrame({"cod_loja": t["COD_LOJAS"], "loja": t["LOJA"], "tipo": "Chamado", "chamado": t["chamado"],
                           "motivo": t["motivo"]})
    cor_coer = {v: c for v in tab["Coerência"].unique() for k, c in C.CORES_COERENCIA.items() if v.startswith(k)}
    tabela_com_atuacao(tab, chaves, extras, "form_chamados",
                       {"Situação": {"Fora do prazo": C.COR_VERMELHO, "Dentro do prazo": C.COR_VERDE},
                        "Coerência": cor_coer},
                       {"Loja": 240, "Motivo": 210, "Coerência": 200, "Detalhe": 340})
    if pode_atuar:
        st.caption("Marque Atuado, escolha o status e salve. Cada gravação fica registrada na aba "
                   f"{C.ABA_ATUACOES} da planilha, com o nome de quem salvou e a hora.")
