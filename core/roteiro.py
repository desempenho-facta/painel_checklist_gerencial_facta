"""
Regras do Roteiro de Visitas (aba Roteiro do formulário).

Funções puras sobre DataFrames, sem Streamlit, para poder testar cada regra.

Cada envio do roteiro grava 5 linhas (segunda a sexta) com o mesmo TIMESTAMP_REGISTRO.
Quando o coordenador reedita a semana, um novo bloco de 5 linhas é gravado; vale o mais recente.

Decisões de 05/11/2026:
- o roteiro não é obrigatório, mas é indicado; o painel mostra a adesão sem tratar como pendência;
- meta de visitas por loja: 2 por mês nas lojas de fácil acesso e 1 por mês nas distantes;
- loja distante: mais de 200 km da base do coordenador. A base é a loja que ele mais marca como BASE
  no roteiro e a posição de cada loja vem da localização gravada nos checklists;
- sempre priorizar as lojas que estão há mais tempo sem visita;
- dia de BASE numa loja conta como presença nela (meta de visitas e cruzamento com o checklist).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from .regras import normaliza_nome

TIPOS = ["VISITA", "BASE", "FERIADO", "FOLGA"]
COR_TIPO = {"VISITA": C.COR_VERDE, "BASE": C.COR_AZUL, "FERIADO": "#7A7A7A", "FOLGA": "#555555"}
NOME_TIPO = {"VISITA": "Visita", "BASE": "Base", "FERIADO": "Feriado", "FOLGA": "Folga"}
# Dia de BASE também é presença na loja marcada (decisão de 05/11/2026): conta na meta de visitas
# e no cruzamento com o checklist.
TIPOS_PRESENCA = ("VISITA", "BASE")
DIAS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]

DISTANCIA_LOJA_DISTANTE_KM = 200
META_VISITAS_PERTO = 2
META_VISITAS_LONGE = 1
PRECISAO_MAX_M = 1000          # só usa localizações de checklist com precisão de até 1 km
LONGE_DA_LOJA_KM = 5           # checklist feito a mais de 5 km do ponto habitual da loja

COLUNAS = ["TIMESTAMP_REGISTRO", "REGIONAL", "COORDENADOR", "SEMANA_INICIO", "DATA_VISITA", "TIPO", "LOJA",
           "COD_LOJA", "OBJETIVO", "OBS", "STATUS", "JUSTIFICATIVA", "MOTIVOS"]


# ---------------------------------------------------------------------------
# Preparação
# ---------------------------------------------------------------------------
def preparar_roteiro(rot: pd.DataFrame) -> pd.DataFrame:
    """Normaliza a aba Roteiro e marca a versão vigente de cada semana."""
    if rot is None or rot.empty:
        vazio = pd.DataFrame(columns=COLUNAS + ["ts", "semana", "data", "vigente", "versoes", "primeiro_envio", "competencia"])
        return vazio.astype({"ts": "datetime64[ns]", "semana": "datetime64[ns]", "data": "datetime64[ns]",
                             "primeiro_envio": "datetime64[ns]", "competencia": "datetime64[ns]", "vigente": bool})
    df = rot.copy()
    for col in COLUNAS:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str).str.strip()
    for col in ("REGIONAL", "COORDENADOR", "LOJA"):
        df[col] = normaliza_nome(df[col])
    df["COORDENADOR"] = df["COORDENADOR"].replace(C.ALIAS_COORDENADOR)
    df["TIPO"] = df["TIPO"].str.upper()
    df["MOTIVOS"] = df["MOTIVOS"].str.upper()
    df["ts"] = pd.to_datetime(df["TIMESTAMP_REGISTRO"], errors="coerce")
    df["semana"] = pd.to_datetime(df["SEMANA_INICIO"], errors="coerce")
    df["data"] = pd.to_datetime(df["DATA_VISITA"], errors="coerce")
    df = df[df["ts"].notna() & df["semana"].notna() & df["data"].notna()].copy()

    chave = ["COORDENADOR", "SEMANA_INICIO"]
    ultimo = df.groupby(chave)["ts"].transform("max")
    df["vigente"] = df["ts"] == ultimo
    df["versoes"] = df.groupby(chave)["ts"].transform("nunique")
    df["primeiro_envio"] = df.groupby(chave)["ts"].transform("min")
    df["competencia"] = df["data"].dt.to_period("M").dt.to_timestamp()
    return df.reset_index(drop=True)


def vigentes(rot: pd.DataFrame) -> pd.DataFrame:
    return rot[rot["vigente"]].drop_duplicates(["COORDENADOR", "DATA_VISITA"], keep="last")


def presencas(v: pd.DataFrame) -> pd.DataFrame:
    """Dias em que o coordenador está numa loja: VISITA ou BASE, com a loja informada."""
    return v[v["TIPO"].isin(TIPOS_PRESENCA) & (v["COD_LOJA"] != "")]


def motivos(txt: str) -> list[str]:
    return [p.strip() for p in str(txt or "").split("|") if p.strip()]


# ---------------------------------------------------------------------------
# Semanas do mês e adesão
# ---------------------------------------------------------------------------
def semanas_do_mes(comp: pd.Timestamp, hoje) -> list[pd.Timestamp]:
    """Segundas-feiras das semanas que começam no mês, até a semana atual (a do mês corrente conta)."""
    comp = pd.Timestamp(comp)
    fim = comp + pd.offsets.MonthEnd(0)
    hoje = pd.Timestamp(hoje).tz_localize(None).normalize() if pd.Timestamp(hoje).tzinfo else pd.Timestamp(hoje).normalize()
    limite = min(fim, hoje - pd.Timedelta(days=hoje.weekday()) + pd.Timedelta(days=6))
    segundas = pd.date_range(comp, fim, freq="W-MON")
    return [s for s in segundas if s <= limite]


def antecedencia(primeiro_envio: pd.Timestamp, segunda: pd.Timestamp) -> str:
    if primeiro_envio < segunda:
        return "Antes da semana"
    if primeiro_envio < segunda + pd.Timedelta(days=1):
        return "Na segunda-feira"
    if primeiro_envio < segunda + pd.Timedelta(days=5):
        return "Durante a semana"
    return "Depois da semana"


ORDEM_ANTECEDENCIA = ["Antes da semana", "Na segunda-feira", "Durante a semana", "Depois da semana"]


def envios_semana(rot: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por coordenador e semana: quando mandou, quantas versões e a justificativa da última."""
    v = rot[rot["vigente"]]
    if v.empty:
        return pd.DataFrame(columns=["COORDENADOR", "REGIONAL", "semana", "primeiro_envio", "versoes",
                                     "antecedencia", "justificativa"])
    g = v.sort_values("ts").groupby(["COORDENADOR", "semana"], as_index=False).agg(
        REGIONAL=("REGIONAL", "last"), primeiro_envio=("primeiro_envio", "first"),
        versoes=("versoes", "first"), justificativa=("JUSTIFICATIVA", "last"))
    g["antecedencia"] = [antecedencia(p, s) for p, s in zip(g["primeiro_envio"], g["semana"])]
    return g


def adesao(rot: pd.DataFrame, coordenadores: list[str], comp: pd.Timestamp, hoje) -> pd.DataFrame:
    """Uma linha por coordenador da visão: semanas do mês com roteiro e como foram enviadas."""
    semanas = semanas_do_mes(comp, hoje)
    env = envios_semana(rot)
    env = env[env["semana"].isin(semanas)]
    linhas = []
    for c in coordenadores:
        e = env[env["COORDENADOR"] == c]
        linhas.append({
            "COORDENADOR": c,
            "semanas_mes": len(semanas),
            "semanas_com_roteiro": len(e),
            "antes_da_semana": int((e["antecedencia"] == "Antes da semana").sum()),
            "reeditadas": int((e["versoes"] > 1).sum()),
            "ultimo_envio": rot.loc[rot["COORDENADOR"] == c, "ts"].max() if len(rot) else pd.NaT,
        })
    df = pd.DataFrame(linhas)
    if df.empty:
        return df
    df["adesao"] = np.where(df["semanas_mes"] > 0, df["semanas_com_roteiro"] / df["semanas_mes"].clip(lower=1), np.nan)
    return df


def uso_do_tempo(rot_mes: pd.DataFrame) -> pd.DataFrame:
    """Dias de cada tipo por coordenador no mês (versão vigente)."""
    v = vigentes(rot_mes)
    if v.empty:
        return pd.DataFrame(columns=["COORDENADOR"] + TIPOS)
    t = pd.crosstab(v["COORDENADOR"], v["TIPO"]).reindex(columns=TIPOS, fill_value=0)
    return t.reset_index()


# ---------------------------------------------------------------------------
# Localização das lojas e distância da base
# ---------------------------------------------------------------------------
def _num(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(serie.fillna("").astype(str).str.replace(",", ".", regex=False), errors="coerce")


def coordenadas_checklist(resp: pd.DataFrame) -> pd.DataFrame:
    """Latitude e longitude de cada preenchimento, só quando são válidas no Brasil e precisas."""
    if resp is None or resp.empty or "LATITUDE" not in resp.columns:
        return pd.DataFrame(columns=["COD_LOJAS", "lat", "lon"])
    lat, lon = _num(resp["LATITUDE"]), _num(resp["LONGITUDE"])
    prec = _num(resp["PRECISÃO"]) if "PRECISÃO" in resp.columns else pd.Series(np.nan, index=resp.index)
    ok = lat.between(-34, 6) & lon.between(-74, -34) & (prec.isna() | (prec <= PRECISAO_MAX_M))
    return pd.DataFrame({"COD_LOJAS": resp["COD_LOJAS"].astype(str).str.strip(), "lat": lat, "lon": lon})[ok]


def posicao_lojas(resp: pd.DataFrame) -> pd.DataFrame:
    """Ponto habitual de cada loja: a mediana das localizações dos checklists dela."""
    c = coordenadas_checklist(resp)
    if c.empty:
        return pd.DataFrame(columns=["lat", "lon", "n_pontos"]).rename_axis("COD_LOJAS")
    return c.groupby("COD_LOJAS").agg(lat=("lat", "median"), lon=("lon", "median"), n_pontos=("lat", "size"))


def km(lat1, lon1, lat2, lon2):
    """Distância em linha reta (haversine), em km."""
    lat1, lon1, lat2, lon2 = (np.radians(np.asarray(x, dtype=float)) for x in (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(a))


def base_dos_coordenadores(rot: pd.DataFrame, carteira: pd.DataFrame | None = None, semanas: int = 12) -> pd.Series:
    """
    Loja que cada coordenador mais marca como BASE nas últimas N semanas (parâmetro semanas) com roteiro.
    Quando há carteira, só valem as lojas da carteira atual dele (quem mudou de carteira não
    fica com a base antiga). Sem BASE recente, usa todo o histórico com a mesma regra.
    """
    b = vigentes(rot)
    b = b[(b["TIPO"] == "BASE") & (b["COD_LOJA"] != "")]
    if b.empty:
        return pd.Series(dtype=object)
    if carteira is not None and len(carteira):
        da_carteira = set(zip(carteira["coordenador_mes"], carteira["COD_LOJAS"]))
        b = b[[(c, l) in da_carteira for c, l in zip(b["COORDENADOR"], b["COD_LOJA"])]]
    if b.empty:
        return pd.Series(dtype=object)
    corte = b.groupby("COORDENADOR")["semana"].transform("max") - pd.Timedelta(weeks=semanas)
    recente = b[b["semana"] > corte]
    return recente.groupby("COORDENADOR")["COD_LOJA"].agg(lambda s: s.value_counts().index[0])


def distancia_e_meta(carteira: pd.DataFrame, rot: pd.DataFrame, resp: pd.DataFrame) -> pd.DataFrame:
    """
    Para cada loja da carteira (colunas COD_LOJAS e coordenador_mes): base do coordenador,
    distância até a base e meta de visitas no mês. Sem base ou sem localização, a meta fica a de fácil acesso (2).
    """
    pos = posicao_lojas(resp)
    bases = base_dos_coordenadores(rot, carteira)
    df = carteira[["COD_LOJAS", "coordenador_mes"]].copy()
    df["base"] = df["coordenador_mes"].map(bases.to_dict())
    p_loja = pos.reindex(df["COD_LOJAS"])
    p_base = pos.reindex(df["base"].fillna(""))
    dist = km(p_loja["lat"].to_numpy(), p_loja["lon"].to_numpy(), p_base["lat"].to_numpy(), p_base["lon"].to_numpy())
    df["distancia_km"] = dist
    df.loc[df["COD_LOJAS"] == df["base"], "distancia_km"] = 0.0
    df["acesso"] = np.select([df["base"].isna(), df["distancia_km"].isna(), df["distancia_km"] > DISTANCIA_LOJA_DISTANTE_KM],
                             ["Sem base no roteiro", "Sem localização", "Distante"], default="Fácil acesso")
    df["meta_visitas"] = np.where(df["acesso"] == "Distante", META_VISITAS_LONGE, META_VISITAS_PERTO)
    return df


# ---------------------------------------------------------------------------
# Cobertura da carteira
# ---------------------------------------------------------------------------
def cobertura(carteira: pd.DataFrame, rot: pd.DataFrame, resp: pd.DataFrame, comp: pd.Timestamp, hoje) -> pd.DataFrame:
    """
    Uma linha por loja da carteira do mês com: dias na loja no mês (visita ou base, feitos e planejados), meta,
    última visita até hoje (de qualquer coordenador) e dias sem visita.
    """
    hoje = pd.Timestamp(hoje)
    hoje = (hoje.tz_localize(None) if hoje.tzinfo else hoje).normalize()
    v = vigentes(rot)
    vis = presencas(v)
    no_mes = vis[vis["competencia"] == pd.Timestamp(comp)]
    dias_mes = no_mes.groupby("COD_LOJA")["data"].nunique()
    dias_base = no_mes[no_mes["TIPO"] == "BASE"].groupby("COD_LOJA")["data"].nunique()
    feitas = no_mes[no_mes["data"] <= hoje].groupby("COD_LOJA")["data"].nunique()
    ate_hoje = vis[vis["data"] <= hoje]
    ultima = ate_hoje.groupby("COD_LOJA")["data"].max()
    proxima = vis[vis["data"] > hoje].groupby("COD_LOJA")["data"].min()

    df = distancia_e_meta(carteira, rot, resp)
    cod = df["COD_LOJAS"]
    df["visitas_mes"] = cod.map(dias_mes.to_dict()).fillna(0).astype(int)
    df["dias_base_mes"] = cod.map(dias_base.to_dict()).fillna(0).astype(int)
    df["visitas_feitas"] = cod.map(feitas.to_dict()).fillna(0).astype(int)
    df["ultima_visita"] = pd.to_datetime(cod.map(ultima.to_dict()))
    df["proxima_visita"] = pd.to_datetime(cod.map(proxima.to_dict()))
    df["dias_sem_visita"] = (hoje - df["ultima_visita"]).dt.days
    df["situacao_meta"] = np.select(
        [df["visitas_mes"] >= df["meta_visitas"], df["visitas_mes"] > 0],
        ["Meta atingida", "Abaixo da meta"], default="Sem visita no mês")
    return df


ORDEM_META = ["Meta atingida", "Abaixo da meta", "Sem visita no mês"]


def faixa_sem_visita(dias) -> str:
    if pd.isna(dias):
        return "Nunca visitada"
    if dias <= 15:
        return "Até 15 dias"
    if dias <= 30:
        return "16 a 30 dias"
    if dias <= 60:
        return "31 a 60 dias"
    return "Mais de 60 dias"


ORDEM_SEM_VISITA = ["Até 15 dias", "16 a 30 dias", "31 a 60 dias", "Mais de 60 dias", "Nunca visitada"]


# ---------------------------------------------------------------------------
# Planejado x realizado
# ---------------------------------------------------------------------------
def planejado_realizado(rot: pd.DataFrame, val: pd.DataFrame, respostas: pd.DataFrame, comp: pd.Timestamp) -> pd.DataFrame:
    """
    Uma linha por checklist do mês, cruzado com o roteiro do coordenador:
      - roteiro_na_semana: o coordenador tinha roteiro para a semana do checklist;
      - visita_no_dia: o roteiro marcava visita naquela loja no dia do checklist;
      - visita_no_mes: a loja estava no roteiro em algum dia do mês;
      - distancia_km: distância entre o ponto do checklist e o ponto habitual da loja.
    """
    comp = pd.Timestamp(comp)
    chk = val[val["competencia"] == comp].copy()
    if chk.empty:
        return chk.assign(roteiro_na_semana=False, visita_no_dia=False, visita_no_mes=False, distancia_km=np.nan,
                          local="Sem localização")
    v = vigentes(rot)
    vis = presencas(v)
    dia = chk["timestamp"].dt.normalize()
    segunda = dia - pd.to_timedelta(dia.dt.weekday, unit="D")
    semanas = set(zip(v["COORDENADOR"], v["semana"]))
    dias_vis = set(zip(vis["COD_LOJA"], vis["data"]))
    mes_vis = set(zip(vis["COD_LOJA"], vis["competencia"]))
    chk["roteiro_na_semana"] = [(c, s) in semanas for c, s in zip(chk["COORDENADOR"], segunda)]
    chk["visita_no_dia"] = [(l, d) in dias_vis for l, d in zip(chk["COD_LOJAS"], dia)]
    chk["visita_no_mes"] = [(l, comp) in mes_vis for l in chk["COD_LOJAS"]]

    pos = posicao_lojas(respostas)
    pts = coordenadas_checklist(chk)
    chk["lat"], chk["lon"] = pts["lat"].reindex(chk.index), pts["lon"].reindex(chk.index)
    ref = pos.reindex(chk["COD_LOJAS"])
    chk["distancia_km"] = km(chk["lat"].to_numpy(), chk["lon"].to_numpy(), ref["lat"].to_numpy(), ref["lon"].to_numpy())
    # Loja com um único ponto: a referência é o próprio checklist, então não dá para comparar
    unico = chk["COD_LOJAS"].map(pos["n_pontos"].to_dict()).fillna(0) < 2
    chk.loc[unico, "distancia_km"] = np.nan
    chk["local"] = np.select([chk["lat"].isna(), chk["distancia_km"].isna(), chk["distancia_km"] > LONGE_DA_LOJA_KM],
                             ["Sem localização", "Sem referência", "Longe da loja"], default="Na loja")
    return chk


def checklists_motivo(rot: pd.DataFrame, val: pd.DataFrame, comp: pd.Timestamp, hoje) -> pd.DataFrame:
    """Dias de visita do mês (até hoje) com o motivo CHECKLIST MENSAL e se o checklist saiu no dia ou no mês."""
    hoje = pd.Timestamp(hoje)
    hoje = (hoje.tz_localize(None) if hoje.tzinfo else hoje).normalize()
    v = vigentes(rot)
    m = v[v["TIPO"].isin(TIPOS_PRESENCA) & (v["COD_LOJA"] != "") & (v["competencia"] == pd.Timestamp(comp)) & (v["data"] <= hoje)
          & v["MOTIVOS"].str.contains("CHECKLIST", na=False)].copy()
    chk = val[val["competencia"] == pd.Timestamp(comp)]
    dias = set(zip(chk["COD_LOJAS"], chk["timestamp"].dt.normalize()))
    lojas = set(chk["COD_LOJAS"])
    m["feito_no_dia"] = [(l, d) in dias for l, d in zip(m["COD_LOJA"], m["data"])]
    m["feito_no_mes"] = m["COD_LOJA"].isin(lojas)
    return m


ORDEM_CHECKLIST = ["No dia da visita planejada", "Loja no roteiro, em outro dia", "Roteiro da semana sem essa loja",
                   "Sem roteiro na semana"]


def classificar_checklist(pr: pd.DataFrame) -> pd.Series:
    return pd.Series(np.select(
        [pr["visita_no_dia"], pr["visita_no_mes"], pr["roteiro_na_semana"]], ORDEM_CHECKLIST[:3],
        default=ORDEM_CHECKLIST[3]), index=pr.index)


def rotulo_semana(segunda) -> str:
    segunda = pd.Timestamp(segunda)
    return f"{segunda:%d/%m} a {segunda + pd.Timedelta(days=4):%d/%m}"


def data_curta(d) -> str:
    return "" if d is None or pd.isna(d) else pd.Timestamp(d).strftime("%d/%m/%Y")
