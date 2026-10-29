"""
Montagem dos três apps do painel. Cada app é publicado separado, com a própria
lista de acesso, para que coordenadores e regionais não vejam as telas da
Monitoria nem a visão de outros perfis.

    app_monitoria.py    visão da rede, todas as telas
    app_regional.py     visão de regional
    app_coordenador.py  visão de coordenador

O menu das telas fica no topo e os filtros logo abaixo do cabeçalho, para
funcionar bem também no celular.
"""

import streamlit as st
import streamlit.components.v1 as components

from . import regras as R
from . import ui
from .contexto import PERFIS, filtros


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


_FECHA_MENU_CELULAR = """
<script>
// fx-fecha-menu: no celular o menu das telas vira uma aba lateral. Depois de trocar de tela, ela fecha sozinha.
const doc = window.parent.document;
if (window.parent.innerWidth < 768) {
  const aberto = doc.querySelector('[data-testid="stSidebar"][data-collapsed="false"]');
  const botao = aberto && aberto.querySelector('[data-testid="stBaseButton-headerNoPadding"]');
  if (aberto && botao) botao.click();
}
</script>
"""


def _fechar_menu_no_celular(pagina: str):
    # A página entra no HTML para o componente ser recriado a cada troca de tela.
    components.html(_FECHA_MENU_CELULAR + f"<!-- {pagina} -->", height=0)


def rodar(perfil: str):
    st.set_page_config(page_title=f"Checklist Gerencial · {PERFIS[perfil]['titulo']}", page_icon=ui.caminho_icone(),
                       layout="wide", initial_sidebar_state="collapsed")
    ui.aplicar_estilo()
    st.logo(ui.caminho_icone(), size="large")
    pg = st.navigation(paginas_do_perfil(perfil), position="top")
    cabecalho = st.container()
    ctx = filtros(perfil)
    st.session_state["ctx"] = ctx
    with cabecalho:
        ui.topo(pg.title, f"{ctx.rotulo_visao} · {R.rotulo_mes(ctx.comp)}")
    _fechar_menu_no_celular(pg.title)
    pg.run()
