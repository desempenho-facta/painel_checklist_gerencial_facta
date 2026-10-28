"""
Montagem dos três apps do painel. Cada app é publicado separado, com a própria
lista de acesso, para que coordenadores e regionais não vejam as telas da
Monitoria nem a visão de outros perfis.

    app_monitoria.py    visão da rede, todas as telas
    app_regional.py     visão de regional
    app_coordenador.py  visão de coordenador
"""

import streamlit as st

from . import ui
from .contexto import PERFIS, barra_lateral


def _p(arquivo, titulo, icone, default=False):
    return st.Page(f"paginas/{arquivo}.py", title=titulo, icon=f":material/{icone}:", default=default)


def paginas_do_perfil(perfil: str) -> dict:
    painel = [
        _p("visao_geral", "Visão geral", "dashboard", default=True),
        _p("lojas", "Lojas", "storefront"),
        _p("loja", "Diagnóstico da loja", "fact_check"),
        _p("mes_a_mes", "Mês a mês", "timeline"),
    ]
    leituras = [
        _p("atencao", "Pontos de atenção", "warning"),
        _p("treino", "O treino está funcionando?", "school"),
        _p("risco_estrutura", "Risco e estrutura", "report"),
        _p("casos_graves", "Casos graves", "crisis_alert"),
    ]
    rede = [_p("ranking", "Ranking", "leaderboard")]
    if perfil in ("monitoria", "regional"):
        rede.append(_p("ferias", "Controle de férias", "event_busy"))
    return {"Painel": painel, "Leituras": leituras, "Rede": rede}


def rodar(perfil: str):
    st.set_page_config(page_title=f"Checklist Gerencial · {PERFIS[perfil]['titulo']}", page_icon="✅", layout="wide")
    ui.aplicar_estilo()
    pg = st.navigation(paginas_do_perfil(perfil))
    st.session_state["ctx"] = barra_lateral(perfil)
    pg.run()
