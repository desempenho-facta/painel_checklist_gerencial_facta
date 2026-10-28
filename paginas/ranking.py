import pandas as pd
import streamlit as st

from core import config as C
from core import regras as R
from core import ui
from core.contexto import rankings

ctx = st.session_state["ctx"]
rk_coord, rk_reg = rankings(ctx.comp_iso)

ui.topo("Ranking", R.rotulo_mes(ctx.comp))
ui.faixa(f"<b>{R.aviso_mes(rk_coord, ctx.comp, ctx.hoje.date())}</b> · lista completa, com o coordenador de cada loja "
         f"naquele mês. Lojas com supervisão especial ficam fora da conta.", pin=R.rotulo_mes(ctx.comp))


def _mostrar(t: pd.DataFrame, destaque_nome: str | None, formatos: dict):
    def linha(r):
        marca = destaque_nome is not None and r["Nome"] == destaque_nome
        return [f"background-color:{C.COR_LARANJA}40; font-weight:700" if marca else ""] * len(r)
    st.dataframe(t.style.apply(linha, axis=1).format(formatos, na_rep=""), hide_index=True,
                 use_container_width=True, height=min(36 * (len(t) + 1), 760))


def tabelas(rk: pd.DataFrame, destaque: str | None, rotulo: str):
    rk = rk.copy()
    rk["Nome"] = rk["nome"].str.title()
    alvo = destaque.title() if destaque else None
    rk["Preenchidas"] = rk["preenchidas"].astype(str) + " de " + rk["carteira"].astype(str)

    a, b = st.columns([1.15, 1])
    with a:
        st.markdown(f"**{rotulo} por cobertura**", help=C.AJUDA["cobertura_ajustada"])
        t = rk.sort_values("pos_cobertura")[["pos_cobertura", "Nome", "Preenchidas", "cobertura_ajustada", "cobertura"]]
        t.columns = ["Posição", "Nome", "Preenchidas", "Cobertura ajustada", "Cobertura real"]
        _mostrar(t, alvo, {"Cobertura ajustada": lambda v: ui.pct(v, 2), "Cobertura real": lambda v: ui.pct(v, 1)})
    with b:
        st.markdown(f"**{rotulo} por score**", help=C.AJUDA["score"])
        t = rk.sort_values("pos_score")[["pos_score", "Nome", "score"]]
        t.columns = ["Posição", "Nome", "Score"]
        _mostrar(t, alvo, {"Score": lambda v: ui.num(v, 2)})
    if alvo:
        st.caption("Linha em destaque: a visão escolhida na barra lateral.")


def aba_coordenadores():
    rk = rk_coord
    if ctx.nivel == "regional":
        if st.toggle("Só os coordenadores da minha área", value=False):
            rk = rk[rk["nome"].isin(set(ctx.hier()["coordenador_mes"]))]
            st.caption(f"Posição calculada entre os {len(rk_coord)} coordenadores da rede.")
    tabelas(rk, ctx.nome if ctx.nivel == "coordenador" else None, "Coordenadores")


if ctx.perfil == "coordenador":
    aba_coordenadores()
else:
    aba1, aba2 = st.tabs(["Coordenadores", "Regionais"])
    with aba1:
        aba_coordenadores()
    with aba2:
        tabelas(rk_reg, ctx.nome if ctx.nivel == "regional" else None, "Regionais")
