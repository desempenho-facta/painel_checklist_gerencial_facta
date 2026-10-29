"""
Estado compartilhado entre as telas: mês selecionado e visão (rede, regional ou coordenador).

Cada app tem um perfil:
    monitoria    visão da rede, com troca livre entre rede, regional e coordenador;
    regional     só a visão de regional;
    coordenador  só a visão de coordenador.

Enquanto o login com a conta Microsoft não existe, a pessoa escolhe o nome nos
filtros do cabeçalho (acesso amplo, decisão de 27/10/2026). Quando o login entrar,
basta ligar TRAVAR_POR_EMAIL nos secrets: o nome passa a vir do e-mail de quem
abriu o app, pela aba de lojas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd
import streamlit as st

from . import config as C
from . import dados, regras

PERFIS = {
    "monitoria": {"titulo": "Monitoria & Desempenho", "niveis": ["Rede", "Regional", "Coordenador"]},
    "regional": {"titulo": "Regionais", "niveis": ["Regional"]},
    "coordenador": {"titulo": "Coordenadores", "niveis": ["Coordenador"]},
}


@st.cache_data(ttl=600, show_spinner=False)
def hierarquia(comp_iso: str) -> pd.DataFrame:
    d = dados.carregar()
    return regras.hierarquia_do_mes(d["validos"], d["lojas"], pd.Timestamp(comp_iso))


@st.cache_data(ttl=600, show_spinner=False)
def rankings(comp_iso: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    d = dados.carregar()
    h = hierarquia(comp_iso)
    return regras.ranking(h, "coordenador", d["lojas"]), regras.ranking(h, "regional", d["lojas"])


@dataclass
class Contexto:
    comp: pd.Timestamp
    nivel: str            # 'rede', 'regional' ou 'coordenador'
    nome: str | None
    hoje: datetime
    perfil: str = "monitoria"

    @property
    def comp_iso(self) -> str:
        return self.comp.strftime("%Y-%m-%d")

    @property
    def rotulo_visao(self) -> str:
        if self.nivel == "rede":
            return "Rede própria"
        return f"{'Regional' if self.nivel == 'regional' else 'Coordenador'}: {self.nome.title()}"

    @property
    def eh_mes_corrente(self) -> bool:
        return regras.inicio_do_mes(self.hoje) == self.comp

    def hier_total(self) -> pd.DataFrame:
        return hierarquia(self.comp_iso)

    def hier(self) -> pd.DataFrame:
        return regras.filtrar_visao(self.hier_total(), self.nivel, self.nome)


def email_do_visitante() -> str | None:
    """E-mail de quem abriu o app, quando o login estiver ligado. Sem login, None."""
    try:
        u = st.user
        if getattr(u, "is_logged_in", False) or u.get("email"):
            return (u.get("email") or "").strip().lower() or None
    except Exception:
        return None
    return None


def _nome_pelo_email(lojas: pd.DataFrame, nivel: str, email: str | None) -> str | None:
    if not email:
        return None
    col_nome, col_email = ("REGIONAL", "EMAIL_REGIONAL") if nivel == "regional" else ("COORDENADOR", "EMAIL_COORDENADOR")
    achou = lojas.loc[lojas[col_email] == email, col_nome]
    return achou.iloc[0] if len(achou) else None


def _travar_por_email() -> bool:
    try:
        return bool(st.secrets.get("TRAVAR_POR_EMAIL", False))
    except Exception:
        return False


def filtros(perfil: str = "monitoria") -> Contexto:
    """Filtros no cabeçalho de todas as telas: período, visão (só Monitoria) e nome."""
    d = dados.carregar()
    cfg = PERFIS[perfil]
    hoje = datetime.now(C.FUSO)
    meses = sorted(d["validos"]["competencia"].unique(), reverse=True)
    atual = regras.inicio_do_mes(hoje)
    if atual not in meses:
        meses = [atual] + meses
    meses = [pd.Timestamp(m) for m in meses]

    # Atalho por link: ?visao=coordenador&nome=NOME%20DO%20COORDENADOR&mes=2026-08
    qp = st.query_params
    if "ctx_iniciado" not in st.session_state:
        st.session_state["ctx_iniciado"] = True
        if qp.get("mes"):
            alvo = pd.Timestamp(qp["mes"] + "-01")
            if alvo in meses:
                st.session_state["ctx_comp"] = alvo
        if qp.get("visao") and qp["visao"].title() in cfg["niveis"]:
            st.session_state["ctx_nivel"] = qp["visao"].title()
            if qp.get("nome"):
                st.session_state["ctx_reg" if qp["visao"] == "regional" else "ctx_coord"] = qp["nome"].upper()

    varias_visoes = len(cfg["niveis"]) > 1
    larguras = [1.1, 1.5, 2.2, 1.2] if varias_visoes else [1.1, 2.6, 1.2]
    cols = st.container(key="fx_filtros").columns(larguras, vertical_alignment="bottom")
    with cols[0]:
        comp = st.selectbox("Período", meses, format_func=regras.rotulo_mes, key="ctx_comp")
    if varias_visoes:
        with cols[1]:
            if st.session_state.get("ctx_nivel") not in cfg["niveis"]:
                st.session_state["ctx_nivel"] = cfg["niveis"][0]
            nivel_rot = st.segmented_control("Visão", cfg["niveis"], key="ctx_nivel", selection_mode="single") \
                or cfg["niveis"][0]
        col_nome = cols[2]
    else:
        nivel_rot = cfg["niveis"][0]
        col_nome = cols[1]
    nivel = nivel_rot.lower()

    nome = None
    h = hierarquia(pd.Timestamp(comp).strftime("%Y-%m-%d"))
    with col_nome:
        if nivel in ("regional", "coordenador"):
            col = "regional_mes" if nivel == "regional" else "coordenador_mes"
            chave = "ctx_reg" if nivel == "regional" else "ctx_coord"
            nomes = sorted(h[col].unique())
            if _travar_por_email():
                nome = _nome_pelo_email(d["lojas"], nivel, email_do_visitante())
                if nome is None:
                    st.error("Seu e-mail não está na aba de lojas como "
                             f"{'regional' if nivel == 'regional' else 'coordenador'}. Fale com a Monitoria.")
                    st.stop()
                st.text_input(nivel_rot, nome.title(), disabled=True)
            else:
                nome = st.selectbox(nivel_rot, nomes, key=chave, format_func=str.title)
        else:
            st.text_input("Recorte", "Rede própria inteira", disabled=True)
    with cols[-1]:
        if st.button("Recarregar dados", use_container_width=True,
                     help=f"Dados: {d['origem']}. Atualizado em {d['carregado_em']:%d/%m/%Y às %H:%M}. "
                          "Os dados se renovam sozinhos a cada 10 minutos."):
            st.cache_data.clear()
            st.rerun()

    return Contexto(comp=pd.Timestamp(comp), nivel=nivel, nome=nome, hoje=hoje, perfil=perfil)


# Compatibilidade com o nome antigo
barra_lateral = filtros
