"""Componentes visuais no padrão Facta (fundo escuro, faixa navy, destaque laranja)."""

from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from . import config as C

CSS = f"""
<style>
.block-container {{ padding-top: 3.2rem; padding-bottom: 2rem; max-width: 1400px; }}
.fx-topo {{ background:{C.COR_NAVY}; border-radius:10px; padding:14px 22px; margin-bottom:14px;
           display:flex; align-items:center; justify-content:space-between; }}
.fx-logo {{ font-size:26px; font-weight:800; color:#fff; letter-spacing:-1px; }}
.fx-logo span {{ display:inline-block; background:#0A84FF; color:{C.COR_NAVY}; border-radius:5px;
                padding:0 7px; margin-right:6px; font-style:italic; }}
.fx-titulo {{ font-size:22px; font-weight:800; font-style:italic; color:#fff; letter-spacing:.5px; text-transform:uppercase; }}
.fx-sub {{ font-size:13px; color:#cfd8e3; text-align:right; }}
.fx-card {{ background:#2B2B2B; border-radius:10px; padding:12px 16px; height:100%; }}
.fx-card .num {{ font-size:30px; font-weight:700; line-height:1.1; }}
.fx-card .rot {{ font-size:13px; color:#c9c9c9; margin-top:4px; }}
.fx-card .sub {{ font-size:12px; color:#8f8f8f; margin-top:2px; }}
.fx-faixa {{ background:#2B2B2B; border-radius:10px; padding:10px 16px; margin:8px 0 12px 0; font-size:14px; color:#ddd; }}
.fx-pin {{ background:{C.COR_LARANJA}; color:{C.COR_NAVY}; font-size:11px; font-weight:800; letter-spacing:1px;
          padding:3px 9px; border-radius:4px; margin-right:10px; }}
.fx-destaque {{ background:#3A2318; border-left:4px solid {C.COR_LARANJA}; border-radius:6px; padding:10px 14px;
               color:#E6D9D0; font-size:13.5px; margin:6px 0 12px 0; }}
.fx-destaque b {{ color:#FF8A3D; }}
.fx-resp {{ display:flex; gap:10px; align-items:flex-start; padding:7px 10px; border-bottom:1px solid #2f2f2f; font-size:13.5px; }}
.fx-resp .q {{ color:#9a9a9a; min-width:38px; font-weight:700; }}
.fx-resp .t {{ flex:1; color:#e8e8e8; }}
.fx-resp .r {{ min-width:64px; text-align:center; font-weight:700; border-radius:4px; padding:2px 0; color:#fff; }}
.fx-resp .p {{ min-width:54px; text-align:right; color:#9a9a9a; font-size:12px; }}
.fx-sim {{ background:{C.COR_VERDE}; }} .fx-nao {{ background:{C.COR_VERMELHO}; }} .fx-vazio {{ background:#555; }}
.fx-bloco {{ margin-top:12px; font-weight:800; color:{C.COR_LARANJA}; letter-spacing:.5px; font-size:13px; text-transform:uppercase; }}
.fx-tag {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:12px; font-weight:700; margin-right:6px; }}
</style>
"""


def aplicar_estilo():
    st.markdown(CSS, unsafe_allow_html=True)


def topo(titulo: str, sub: str = ""):
    st.markdown(
        f'<div class="fx-topo"><div class="fx-logo"><span>F</span>facta</div>'
        f'<div class="fx-titulo">{html.escape(titulo)}</div><div class="fx-sub">{html.escape(sub)}</div></div>',
        unsafe_allow_html=True)


def card(numero, rotulo: str, sub: str = "", cor: str = "#ffffff", ajuda: str | None = None):
    titulo = f' title="{html.escape(ajuda)}"' if ajuda else ""
    tam = "font-size:19px;" if isinstance(numero, str) and len(numero) > 9 else ""
    st.markdown(
        f'<div class="fx-card"{titulo}><div class="num" style="color:{cor};{tam}">{numero}</div>'
        f'<div class="rot">{html.escape(rotulo)}{" ⓘ" if ajuda else ""}</div>'
        f'<div class="sub">{html.escape(sub)}</div></div>',
        unsafe_allow_html=True)


def faixa(texto_html: str, pin: str | None = None):
    p = f'<span class="fx-pin">{html.escape(pin)}</span>' if pin else ""
    st.markdown(f'<div class="fx-faixa">{p}{texto_html}</div>', unsafe_allow_html=True)


def destaque(texto_html: str):
    st.markdown(f'<div class="fx-destaque">{texto_html}</div>', unsafe_allow_html=True)


def pct(x, casas: int = 1) -> str:
    return "sem dado" if x is None or pd.isna(x) else f"{x * 100:.{casas}f}%".replace(".", ",")


def num(x, casas: int = 2) -> str:
    return "sem dado" if x is None or pd.isna(x) else f"{x:.{casas}f}".replace(".", ",")


def cor_cobertura(x) -> str:
    if pd.isna(x):
        return C.COR_CINZA
    return "#4CAF50" if x >= 0.9 else C.COR_AMBAR if x >= 0.7 else "#E5484D"


def cor_score(x) -> str:
    if pd.isna(x):
        return C.COR_CINZA
    return "#4CAF50" if x > C.MATURIDADE_DESENV_ATE else C.COR_AMBAR if x > C.MATURIDADE_REATIVA_ATE else "#E5484D"


CORES_STATUS = {"Preencheu": C.COR_VERDE, "Não preencheu": C.COR_VERMELHO, "Loja nova": C.COR_AZUL, "Nunca preencheu": "#555"}
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
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#dddddd", size=13),
    margin=dict(l=10, r=20, t=30, b=10), showlegend=False,
)


def barras_h(valores, rotulos, cores, textos=None, altura=260, eixo_pct=False):
    """Barras horizontais com espaço para o rótulo no fim da barra."""
    import plotly.graph_objects as go
    valores = list(valores)
    maximo = max([v for v in valores if pd.notna(v)] or [1])
    fig = go.Figure(go.Bar(x=valores, y=list(rotulos), orientation="h", marker_color=cores,
                           text=textos if textos is not None else [int(v) for v in valores], textposition="outside",
                           cliponaxis=False))
    eixo = dict(range=[0, maximo * 1.22 if maximo else 1])
    if eixo_pct:
        eixo["tickformat"] = ".0%"
    fig.update_layout(**LAYOUT_GRAFICO, height=altura, xaxis=eixo, yaxis=dict(autorange="reversed"))
    return fig
