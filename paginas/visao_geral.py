import streamlit as st

from core import config as C
from core import regras as R
from core import ui
from core.contexto import rankings

ctx = st.session_state["ctx"]
h_total = ctx.hier_total()
h = ctx.hier()
ind = R.indicadores(h)
rede = R.indicadores(h_total)

rk_coord, rk_reg = rankings(ctx.comp_iso)
texto = f"<b>{R.aviso_mes(rk_coord, ctx.comp, ctx.hoje.date())}</b>"
if ctx.eh_mes_corrente:
    texto += f" · {R.texto_prazo(ctx.hoje.date())}"
ui.faixa(texto, pin=R.rotulo_mes(ctx.comp))

comp_rede = R.comparacao_rede(ind["score"], rede["score"]) if ctx.nivel != "rede" else ""
ui.cards([
    dict(numero=ind["preenchidas"], rotulo="Lojas preenchidas", sub=f"de {ind['carteira']} na carteira do mês",
         cor=ui.VERDE_CLARO, ajuda=C.AJUDA["carteira"]),
    dict(numero=ui.pct(ind["cobertura"]), rotulo="Cobertura",
         sub=f"{ind['preenchidas_calculo']} de {ind['carteira_calculo']} que contam",
         cor=ui.cor_cobertura(ind["cobertura"]), ajuda=C.AJUDA["cobertura"]),
    dict(numero=ind["pendentes"], rotulo="Lojas pendentes", sub=f"{ind['lojas_novas']} lojas novas",
         cor=ui.VERMELHO_CLARO if ind["pendentes"] else ui.VERDE_CLARO, ajuda=C.AJUDA["status"]),
    dict(numero=ui.num(ind["score"]), rotulo="Score médio",
         sub=f"rede em {ui.num(rede['score'])} · {comp_rede}" if comp_rede else "média das lojas que contam",
         cor=ui.cor_score(ind["score"]), ajuda=C.AJUDA["score"]),
    dict(numero=ui.pct(ind["pct_maduras"]), rotulo="Lojas maduras", sub=f"{ind['reativas']} reativas",
         cor=ui.VERDE_CLARO, ajuda=C.AJUDA["maturidade"]),
    dict(numero=ind["risco_critico"], rotulo="Risco crítico", sub=f"{ind['sem_chamados']} sem chamados abertos",
         cor=ui.VERMELHO_CLARO if ind["risco_critico"] else ui.VERDE_CLARO, ajuda=C.AJUDA["risco"]),
], minimo=160)

# Posição no ranking (visão de coordenador ou regional)
if ctx.nivel in ("coordenador", "regional"):
    rk = rk_coord if ctx.nivel == "coordenador" else rk_reg
    linha = rk[rk["nome"] == ctx.nome]
    if len(linha):
        lr = linha.iloc[0]
        ord_ = "º" if ctx.nivel == "coordenador" else "ª"
        ui.cards([
            dict(numero=f"{lr['pos_cobertura']}{ord_} de {len(rk)}", rotulo="Posição em cobertura",
                 sub=f"cobertura ajustada {ui.pct(lr['cobertura_ajustada'])}", ajuda=C.AJUDA["cobertura_ajustada"]),
            dict(numero=f"{lr['pos_score']}{ord_} de {len(rk)}", rotulo="Posição em score",
                 sub=f"score {ui.num(lr['score'])}", ajuda=C.AJUDA["score"]),
        ], minimo=260)
    else:
        st.info("Sem posição no ranking neste mês.")

# Supervisão especial em destaque
esp = h[h["supervisao_especial"]]
if len(esp):
    texto = (f"<b>{len(esp)} {'loja' if len(esp) == 1 else 'lojas'} com supervisão especial neste mês, "
             f"fora do score e da cobertura.</b> As respostas foram mantidas como gravadas.")
    if len(esp) <= 12:
        nomes = ", ".join(f"{l.split(' - ')[1].replace('LOJA ', '').title() if ' - ' in l else l} ({s})"
                          for l, s in zip(esp["LOJA"], esp["tipo_especial"]))
        texto += " " + nomes
    else:
        por_tipo = esp["tipo_especial"].value_counts()
        texto += " " + "; ".join(f"{t}: {n}" for t, n in por_tipo.items()) + ". A lista está na tela Lojas."
    ui.destaque(texto)

g1, g2 = st.columns(2)
with g1:
    st.markdown("**Situação das lojas no mês**", help=C.AJUDA["status"])
    ordem = list(ui.CORES_STATUS)
    cont = h["status"].value_counts().reindex(ordem).fillna(0).astype(int)
    hover = [f"<b>{s}: {cont[s]} lojas</b><br>" + ui.lista_hover(sorted(h.loc[h["status"] == s, "LOJA"])) for s in ordem]
    ui.grafico(ui.barras_h(cont.values, ordem, [ui.CORES_STATUS[s] for s in ordem], altura=280, hover=hover))
    st.caption("Passe o mouse nas barras para ver as lojas.")
with g2:
    st.markdown("**Maturidade das lojas que preencheram**", help=C.AJUDA["maturidade"])
    pre = h[(h["status"] == "Preencheu") & h["conta"]]
    ordem = list(ui.CORES_MATURIDADE)
    cont = pre["maturidade"].value_counts().reindex(ordem).fillna(0).astype(int)
    hover = [f"<b>{m}: {cont[m]} lojas</b><br><i>{C.DEFINICAO_MATURIDADE[m]}</i><br><br>"
             + ui.lista_hover(sorted(pre.loc[pre["maturidade"] == m, "LOJA"]), limite=12) for m in ordem]
    ui.grafico(ui.barras_h(cont.values, ordem, list(ui.CORES_MATURIDADE.values()), altura=280, hover=hover))
    st.caption("Passe o mouse nas barras para ver o que cada nível significa e quais lojas estão nele.")
