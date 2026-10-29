"""
Componentes visuais no padrão Facta (fundo grafite, faixa azul marinho, logo azul e destaque laranja),
o mesmo dos painéis antigos do Power BI. Tudo é responsivo: os cartões quebram em linhas no celular.
"""

from __future__ import annotations

import base64
import html
from functools import lru_cache
from pathlib import Path

import pandas as pd
import streamlit as st

from . import config as C

PASTA_ASSETS = Path(__file__).resolve().parent.parent / "assets"


@lru_cache(maxsize=4)
def _b64(nome: str) -> str:
    return base64.b64encode((PASTA_ASSETS / nome).read_bytes()).decode()


def caminho_icone() -> str:
    return str(PASTA_ASSETS / "facta_icone.png")


CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:ital,wght@0,400;0,500;0,700;0,900;1,700;1,900&display=swap');
html, body, .stMarkdown, .stMarkdown *, button p, input, textarea, label p {{ font-family: 'Roboto', sans-serif; }}
[data-testid="stIconMaterial"], .material-symbols-rounded {{ font-family: 'Material Symbols Rounded' !important; }}
.block-container {{ padding-top: 4.2rem; padding-bottom: 2.5rem; max-width: 1440px; }}

/* Cabeçalho */
.fx-topo {{ background:{C.COR_NAVY}; border-radius:12px; padding:12px 22px; margin-bottom:12px; position:relative;
           display:flex; align-items:center; justify-content:space-between; min-height:64px; gap:12px; }}
.fx-topo img {{ height:34px; }}
.fx-titulo {{ position:absolute; left:50%; transform:translateX(-50%); font-size:22px; font-weight:900;
             font-style:italic; color:#fff; letter-spacing:.6px; text-transform:uppercase; white-space:nowrap; }}
.fx-sub {{ font-size:13px; color:#cfd8e3; text-align:right; max-width:34%; }}

/* Cartões em grade: altura igual na linha, quebram no celular */
.fx-grade {{ display:grid; gap:12px; margin:4px 0 14px 0;
            grid-template-columns: repeat(auto-fit, minmax(var(--min, 170px), 1fr)); }}
.fx-card {{ background:{C.COR_CARD}; border:1px solid {C.COR_BORDA}; border-radius:12px; padding:14px 16px;
           display:flex; flex-direction:column; justify-content:flex-start; min-height:112px; }}
.fx-card .num {{ font-size:30px; font-weight:700; line-height:1.1; }}
.fx-card .num.medio {{ font-size:22px; }}
.fx-card .rot {{ font-size:13.5px; color:#d6d6d6; margin-top:6px; font-weight:500; }}
.fx-card .sub {{ font-size:12px; color:#9a9a9a; margin-top:3px; min-height:15px; }}

.fx-faixa {{ background:{C.COR_CARD}; border:1px solid {C.COR_BORDA}; border-radius:10px; padding:10px 16px;
            margin:6px 0 12px 0; font-size:14px; color:#ddd; }}
.fx-pin {{ background:{C.COR_LARANJA}; color:#fff; font-size:11px; font-weight:800; letter-spacing:1px;
          padding:3px 9px; border-radius:4px; margin-right:10px; text-transform:uppercase; }}
.fx-destaque {{ background:#3A2318; border-left:4px solid {C.COR_LARANJA}; border-radius:8px; padding:10px 14px;
               color:#E6D9D0; font-size:13.5px; margin:6px 0 12px 0; }}
.fx-destaque b {{ color:#FF8A3D; }}
.fx-secao {{ font-size:15px; font-weight:700; color:#f0f0f0; margin:10px 0 2px 0; }}
.fx-secao span {{ color:#9a9a9a; font-weight:400; font-size:13px; }}

/* Respostas do diagnóstico */
.fx-resp {{ display:flex; gap:10px; align-items:flex-start; padding:7px 10px; border-bottom:1px solid #3a3838; font-size:13.5px; }}
.fx-resp .q {{ color:#9a9a9a; min-width:38px; font-weight:700; }}
.fx-resp .t {{ flex:1; color:#e8e8e8; }}
.fx-resp .r {{ min-width:64px; text-align:center; font-weight:700; border-radius:4px; padding:2px 0; color:#fff; }}
.fx-resp .p {{ min-width:54px; text-align:right; color:#9a9a9a; font-size:12px; }}
.fx-sim {{ background:{C.COR_VERDE}; }} .fx-nao {{ background:{C.COR_VERMELHO}; }} .fx-vazio {{ background:#555; }}
.fx-bloco {{ margin-top:12px; font-weight:800; color:{C.COR_LARANJA}; letter-spacing:.5px; font-size:13px; text-transform:uppercase; }}

/* Filtros do cabeçalho */
.fx-filtros-info {{ font-size:12px; color:#9a9a9a; padding-top:30px; }}
.st-key-fx_filtros [data-testid="stHorizontalBlock"] {{ flex-wrap:wrap; row-gap:.6rem; }}
.st-key-fx_filtros [data-testid="stColumn"] {{ flex:1 1 220px !important; min-width:220px !important; }}
.st-key-fx_filtros [data-testid="stColumn"]:nth-child(2):nth-last-child(3) {{ flex-basis:300px !important; min-width:300px !important; }}

/* Componente invisível que fecha o menu no celular */
[data-testid="stElementContainer"]:has(iframe[srcdoc*="fx-fecha-menu"]) {{ display:none; }}

/* Menu do topo */
[data-testid="stTopNavLinkContainer"] a span, [data-testid="stNavSectionHeader"] {{ font-weight:500; }}

@media (max-width: 760px) {{
  .block-container {{ padding-left: .8rem; padding-right: .8rem; padding-top: 3.6rem; }}
  .fx-topo {{ flex-direction:column; align-items:flex-start; padding:12px 14px; }}
  .fx-titulo {{ position:static; transform:none; font-size:18px; white-space:normal; }}
  .fx-sub {{ text-align:left; max-width:100%; }}
  .fx-card .num {{ font-size:24px; }}
  .fx-grade {{ --min: 140px; }}
}}
</style>
"""


def aplicar_estilo():
    st.markdown(CSS, unsafe_allow_html=True)


def topo(titulo: str, sub: str = ""):
    """Cabeçalho com a logo da Facta, o título centralizado e a visão à direita."""
    st.markdown(
        f'<div class="fx-topo"><img src="data:image/png;base64,{_b64("facta_logo.png")}" alt="Facta">'
        f'<div class="fx-titulo">{html.escape(titulo)}</div><div class="fx-sub">{html.escape(sub)}</div></div>',
        unsafe_allow_html=True)


def _card_html(numero, rotulo: str, sub: str = "", cor: str = "#ffffff", ajuda: str | None = None) -> str:
    titulo = f' title="{html.escape(ajuda)}"' if ajuda else ""
    classe = "num medio" if isinstance(numero, str) and len(numero) > 9 else "num"
    return (f'<div class="fx-card"{titulo}><div class="{classe}" style="color:{cor}">{html.escape(str(numero))}</div>'
            f'<div class="rot">{html.escape(rotulo)}{" ⓘ" if ajuda else ""}</div>'
            f'<div class="sub">{html.escape(sub) if sub else "&nbsp;"}</div></div>')


def cards(itens: list[dict], minimo: int = 170):
    """Uma linha de cartões do mesmo tamanho. Cada item: numero, rotulo, sub, cor, ajuda."""
    corpo = "".join(_card_html(**i) for i in itens)
    st.markdown(f'<div class="fx-grade" style="--min:{minimo}px">{corpo}</div>', unsafe_allow_html=True)


def card(numero, rotulo: str, sub: str = "", cor: str = "#ffffff", ajuda: str | None = None):
    cards([dict(numero=numero, rotulo=rotulo, sub=sub, cor=cor, ajuda=ajuda)])


def faixa(texto_html: str, pin: str | None = None):
    p = f'<span class="fx-pin">{html.escape(pin)}</span>' if pin else ""
    st.markdown(f'<div class="fx-faixa">{p}{texto_html}</div>', unsafe_allow_html=True)


def destaque(texto_html: str):
    st.markdown(f'<div class="fx-destaque">{texto_html}</div>', unsafe_allow_html=True)


def secao(titulo: str, detalhe: str = ""):
    d = f" <span>{html.escape(detalhe)}</span>" if detalhe else ""
    st.markdown(f'<div class="fx-secao">{html.escape(titulo)}{d}</div>', unsafe_allow_html=True)


def pct(x, casas: int = 1) -> str:
    return "sem dado" if x is None or pd.isna(x) else f"{x * 100:.{casas}f}%".replace(".", ",")


def num(x, casas: int = 2) -> str:
    return "sem dado" if x is None or pd.isna(x) else f"{x:.{casas}f}".replace(".", ",")


VERDE_CLARO = "#4CAF50"
VERMELHO_CLARO = "#E5484D"


def cor_cobertura(x) -> str:
    if pd.isna(x):
        return C.COR_CINZA
    return VERDE_CLARO if x >= 0.9 else C.COR_AMBAR if x >= 0.7 else VERMELHO_CLARO


def cor_score(x) -> str:
    if pd.isna(x):
        return C.COR_CINZA
    return VERDE_CLARO if x > C.MATURIDADE_DESENV_ATE else C.COR_AMBAR if x > C.MATURIDADE_REATIVA_ATE else VERMELHO_CLARO


CORES_STATUS = {"Preencheu": C.COR_VERDE, "Não preencheu": C.COR_VERMELHO, "Loja nova": C.COR_AZUL, "Nunca preencheu": "#666"}
CORES_RISCO = {"Sem risco": C.COR_VERDE, "Atenção": C.COR_AMBAR, "Risco alto": "#E07020", "Risco crítico": C.COR_VERMELHO}
CORES_MATURIDADE = {"Madura": C.COR_VERDE, "Em desenvolvimento": C.COR_AMBAR, "Reativa": C.COR_VERMELHO}


def estilo_tabela(df: pd.DataFrame, colunas_cor: dict[str, dict[str, str]]):
    """Pinta o fundo das células de texto conforme o dicionário de cores de cada coluna."""
    def pinta(col):
        mapa = colunas_cor.get(col.name)
        if not mapa:
            return [""] * len(col)
        return [f"background-color:{mapa[v]}; color:#fff; font-weight:600" if v in mapa else "" for v in col]
    return df.style.apply(pinta, axis=0).format(na_rep="")


LAYOUT_GRAFICO = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#dddddd", size=13, family="Roboto, Arial, sans-serif"),
    margin=dict(l=10, r=20, t=20, b=10), showlegend=False,
    hoverlabel=dict(bgcolor="#1f1e1e", bordercolor="#555", font=dict(color="#f2f2f2", size=12, family="Roboto, Arial, sans-serif"), align="left"),
)

CONFIG_GRAFICO = {"displayModeBar": False, "responsive": True, "scrollZoom": False, "doubleClick": False,
                  "showAxisDragHandles": False}


def grafico(fig):
    """Mostra um gráfico Plotly fixo (sem zoom, sem arrastar e sem barra de ferramentas), mantendo os tooltips."""
    fig.update_layout(dragmode=False)
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    st.plotly_chart(fig, use_container_width=True, config=CONFIG_GRAFICO)


def lista_hover(nomes, limite: int = 18) -> str:
    """Lista de lojas para o tooltip: até `limite` nomes e um resumo do resto."""
    nomes = [str(n) for n in nomes]
    if not nomes:
        return "nenhuma loja"
    corpo = "<br>".join(html.escape(n) for n in nomes[:limite])
    if len(nomes) > limite:
        corpo += f"<br><i>e mais {len(nomes) - limite} lojas</i>"
    return corpo


def barras_h(valores, rotulos, cores, textos=None, altura=260, eixo_pct=False, hover=None):
    """Barras horizontais com espaço para o rótulo no fim da barra. hover: texto HTML por barra."""
    import plotly.graph_objects as go
    valores = list(valores)
    maximo = max([v for v in valores if pd.notna(v)] or [1])
    fig = go.Figure(go.Bar(
        x=valores, y=list(rotulos), orientation="h", marker_color=cores,
        text=textos if textos is not None else [int(v) for v in valores], textposition="outside", cliponaxis=False,
        customdata=hover if hover is not None else None,
        hovertemplate="%{customdata}<extra></extra>" if hover is not None else "%{y}: %{text}<extra></extra>"))
    eixo = dict(range=[0, maximo * 1.22 if maximo else 1], gridcolor="#3a3838")
    if eixo_pct:
        eixo["tickformat"] = ".0%"
    fig.update_layout(**LAYOUT_GRAFICO, height=altura, xaxis=eixo, yaxis=dict(autorange="reversed"))
    return fig
