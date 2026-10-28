"""
Motor de regras do Painel do Checklist Gerencial.

Funções puras sobre DataFrames (sem Streamlit), para poder testar cada regra
isoladamente. Fonte de verdade: BASE_REGRAS_PAINEL_CHECKLIST.md.

Entradas esperadas
------------------
respostas: aba Respostas (uma linha por preenchimento), colunas por nome:
    timestamp, REGIONAL, COORDENADOR, LOJA, SUPERVISOR, Q1..Q36 (Q37..Q40 opcionais), COD_LOJAS
lojas: aba de lojas (uma linha por loja), colunas por nome:
    REGIONAL, COORDENADOR, LOJA, COD_LOJAS, EMAIL_REGIONAL, EMAIL_COORDENADOR,
    STATUS_COORDENADOR, STATUS_REGIONAL, FERIAS/AFAST/MATERN _INI/_RET _COORD/_REG,
    DATA_CADASTRO_LOJA
"""

from __future__ import annotations

import unicodedata
from datetime import date

import numpy as np
import pandas as pd

from . import config as C


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------
def sem_acento(txt: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", str(txt)) if unicodedata.category(c) != "Mn")


def normaliza_nome(serie: pd.Series) -> pd.Series:
    """Maiúsculas e espaços simples, mantendo acentos (como o formulário grava)."""
    return serie.fillna("").astype(str).str.upper().str.replace(r"\s+", " ", regex=True).str.strip()


def chave_texto(serie: pd.Series) -> pd.Series:
    """Versão para comparação: maiúsculas, sem acento, espaços simples."""
    return normaliza_nome(serie).map(sem_acento)


_PARTICULAS = {"DA", "DE", "DO", "DAS", "DOS", "E"}


def supervisor_e_coordenador(supervisor: str, coordenador: str) -> bool:
    """
    O próprio coordenador aparece como supervisor da loja.

    Precisa bater o primeiro nome e pelo menos um sobrenome. Só o primeiro nome
    não basta, porque o supervisor pode ter o mesmo nome do coordenador.
    """
    s = [t for t in sem_acento(supervisor or "").upper().split() if t not in _PARTICULAS]
    c = [t for t in sem_acento(coordenador or "").upper().split() if t not in _PARTICULAS]
    if len(s) < 2 or len(c) < 2 or s[0] != c[0]:
        return False
    return bool(set(s[1:]) & set(c[1:]))


def fim_do_mes(comp: pd.Timestamp) -> pd.Timestamp:
    return (pd.Timestamp(comp) + pd.offsets.MonthEnd(0)).normalize()


def inicio_do_mes(d) -> pd.Timestamp:
    d = pd.Timestamp(d)
    return pd.Timestamp(year=d.year, month=d.month, day=1)


def para_data(serie: pd.Series) -> pd.Series:
    """Datas da planilha no formato dd/mm/aaaa (ou vazias)."""
    s = serie.fillna("").astype(str).str.strip()
    return pd.to_datetime(s.where(s != "", None), dayfirst=True, errors="coerce")


# ---------------------------------------------------------------------------
# 1. Preparação das respostas
# ---------------------------------------------------------------------------
def preparar_respostas(respostas: pd.DataFrame) -> pd.DataFrame:
    """Normaliza a aba Respostas e calcula tudo que é por preenchimento."""
    df = respostas.copy()
    df["_ordem"] = np.arange(len(df))                      # ordem de gravação na planilha
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df[df["timestamp"].notna()].copy()

    df["COD_LOJAS"] = df["COD_LOJAS"].fillna("").astype(str).str.strip()
    for col in ("REGIONAL", "COORDENADOR", "LOJA"):
        df[col] = normaliza_nome(df[col])
    df["COORDENADOR"] = df["COORDENADOR"].replace(C.ALIAS_COORDENADOR)
    df["SUPERVISOR"] = normaliza_nome(df["SUPERVISOR"])

    df["competencia"] = df["timestamp"].dt.to_period("M").dt.to_timestamp()
    df["data"] = df["timestamp"].dt.strftime("%Y-%m-%d")

    for q in C.PERGUNTAS:
        if q not in df.columns:
            df[q] = ""
        df[q] = df[q].fillna("").astype(str).str.strip()

    sim = df[C.PERGUNTAS].eq("Sim")
    nao = df[C.PERGUNTAS].eq("Não")

    # Score: soma por bloco de peso x (Sim no bloco / perguntas do bloco)
    score = pd.Series(0.0, index=df.index)
    for nome, b in C.BLOCOS.items():
        pct = sim[b["perguntas"]].sum(axis=1) / len(b["perguntas"])
        df[f"pct_{nome}"] = pct
        score = score + b["peso"] * pct
    df["score"] = score.round(9)
    df["pct_Estrutura"] = sim[C.PERGUNTA_ESTRUTURA].astype(float)

    df["maturidade"] = np.select(
        [df["score"] <= C.MATURIDADE_REATIVA_ATE, df["score"] <= C.MATURIDADE_DESENV_ATE],
        ["Reativa", "Em desenvolvimento"], default="Madura")

    t = df["pct_Treinar"] >= C.LIMIAR_BLOCO
    v = df["pct_Verificar"] >= C.LIMIAR_BLOCO
    a = df["pct_Acompanhar"] >= C.LIMIAR_BLOCO
    df["ciclo"] = np.select(
        [t & v & a, t & ~(v & a), ~t & (v | a)],
        ["Ciclo fechado", "Esforço sem acompanhamento", "Exige sem preparar"], default="Ciclo frágil")

    d = df["pct_Domínio de Método"] >= C.LIMIAR_BLOCO
    df["quadrante"] = np.select(
        [t & d, t & ~d, ~t & d], ["Treina e domina", "Treino ineficaz", "Talento natural"], default="Crítico")

    df["falhas_criticas"] = nao[list(C.PERGUNTAS_RISCO)].sum(axis=1).astype(int)
    df["risco"] = df["falhas_criticas"].map(C.NIVEIS_RISCO)

    df["estrutura"] = np.where(df[C.PERGUNTA_ESTRUTURA].eq("Sim"), "Com chamados abertos", "Sem chamados abertos")
    df["avaliar_forca"] = np.where(df["pct_Avaliar"] >= C.LIMIAR_BLOCO, "Avalia bem", "Avalia pouco")
    df["incentivar_forca"] = np.where(df["pct_Incentivar"] >= C.LIMIAR_BLOCO, "Incentiva bem", "Incentiva pouco")
    df["equipe_assidua"] = np.where(df[C.PERGUNTA_ASSIDUIDADE].eq("Sim"), "Equipe assídua", "Equipe não assídua")

    chave_sup = df["SUPERVISOR"].map(sem_acento)
    padrao = chave_sup.isin(C.SUPERVISAO_ESPECIAL)
    coord_sup = pd.Series([supervisor_e_coordenador(s, c) for s, c in zip(df["SUPERVISOR"], df["COORDENADOR"])],
                          index=df.index, dtype=bool)
    casos = df.apply(lambda r: (r["COD_LOJAS"], r["data"]) in C.SUPERVISAO_ESPECIAL_CASOS, axis=1) \
        if C.SUPERVISAO_ESPECIAL_CASOS else pd.Series(False, index=df.index)
    df["supervisao_especial"] = padrao | coord_sup | casos
    df["tipo_especial"] = np.select(
        [padrao, coord_sup, casos], [df["SUPERVISOR"].str.title(), "Coordenador como supervisor", "Caso validado"],
        default="")

    # Preenchimento válido: o último da loja no mês (maior timestamp; empate, o gravado por último)
    df = df.sort_values(["COD_LOJAS", "competencia", "timestamp", "_ordem"])
    df["valido"] = ~df.duplicated(["COD_LOJAS", "competencia"], keep="last")
    return df.sort_values("_ordem").reset_index(drop=True)


def validos(resp: pd.DataFrame) -> pd.DataFrame:
    return resp[resp["valido"]].copy()


# ---------------------------------------------------------------------------
# 2. Preparação das lojas
# ---------------------------------------------------------------------------
_DATAS_AUSENCIA = [f"{t}_{p}_{n}" for n in ("COORD", "REG") for t in ("FERIAS", "AFAST", "MATERN") for p in ("INI", "RET")]


def preparar_lojas(lojas: pd.DataFrame) -> pd.DataFrame:
    df = lojas.copy()
    df["COD_LOJAS"] = df["COD_LOJAS"].fillna("").astype(str).str.strip()
    df = df[df["COD_LOJAS"] != ""].drop_duplicates("COD_LOJAS", keep="last")
    for col in ("REGIONAL", "COORDENADOR", "LOJA", "STATUS_COORDENADOR", "STATUS_REGIONAL"):
        if col in df.columns:
            df[col] = normaliza_nome(df[col])
    for col in ("EMAIL_REGIONAL", "EMAIL_COORDENADOR"):
        df[col] = df[col].fillna("").astype(str).str.strip().str.lower()
    df["data_cadastro"] = para_data(df["DATA_CADASTRO_LOJA"])
    for col in _DATAS_AUSENCIA:
        df[col] = para_data(df[col]) if col in df.columns else pd.NaT
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 3. Carteira e hierarquia do mês
# ---------------------------------------------------------------------------
def _responsavel_do_mes(cart: pd.DataFrame, no_mes: pd.DataFrame, antes: pd.DataFrame, col: str):
    """
    Coordenador (ou regional) de cada loja no mês.
      1. a loja preencheu no mês: o nome gravado no preenchimento;
      2. não preencheu: o nome do preenchimento mais recente antes do mês, desde que essa
         pessoa tenha preenchimento em alguma loja naquele mês (sinal de que segue na função);
      3. senão: o nome atual da aba de lojas.
    """
    cod = cart["COD_LOJAS"]
    nome = cod.map(no_mes[col])
    origem = pd.Series(np.where(nome.notna(), "preenchimento do mês", None), index=cart.index, dtype=object)
    ativos_no_mes = set(no_mes[col])
    anterior = cod.map(antes[col])
    usa_ant = nome.isna() & anterior.notna() & anterior.isin(ativos_no_mes)
    nome = nome.where(~usa_ant, anterior)
    origem[usa_ant] = "preenchimento anterior"
    usa_atual = nome.isna()
    nome = nome.where(~usa_atual, cart[col])
    origem[usa_atual] = "cadastro atual"
    return nome, origem


def hierarquia_do_mes(val: pd.DataFrame, lojas: pd.DataFrame, comp: pd.Timestamp) -> pd.DataFrame:
    """
    Uma linha por loja da carteira do mês, com o coordenador daquele mês.

    Carteira: lojas cadastradas até o fim do mês.
    Coordenador e regional do mês: regra de _responsavel_do_mes.
    """
    comp = pd.Timestamp(comp)
    cart = lojas[lojas["data_cadastro"].isna() | (lojas["data_cadastro"] <= fim_do_mes(comp))].copy()

    no_mes = val[val["competencia"] == comp].set_index("COD_LOJAS")
    antes = (val[val["competencia"] < comp].sort_values(["competencia", "timestamp", "_ordem"])
             .drop_duplicates("COD_LOJAS", keep="last").set_index("COD_LOJAS"))

    cod = cart["COD_LOJAS"]
    cart["coordenador_mes"], cart["origem_coordenador"] = _responsavel_do_mes(cart, no_mes, antes, "COORDENADOR")
    cart["regional_mes"], cart["origem_regional"] = _responsavel_do_mes(cart, no_mes, antes, "REGIONAL")
    cart["competencia"] = comp

    # Situação da loja no mês
    preencheu = cod.isin(no_mes.index)
    ja_preencheu = cod.isin(set(val["COD_LOJAS"]))
    limite_novo = fim_do_mes(comp - pd.DateOffset(months=C.MESES_LOJA_NOVA))
    loja_nova = cart["data_cadastro"].notna() & (cart["data_cadastro"] > limite_novo)
    cart["status"] = np.select([preencheu, ja_preencheu, loja_nova],
                               ["Preencheu", "Não preencheu", "Loja nova"], default="Nunca preencheu")

    campos = ["score", "maturidade", "ciclo", "quadrante", "risco", "falhas_criticas", "estrutura",
              "SUPERVISOR", "supervisao_especial", "tipo_especial", "timestamp"] + [f"pct_{b}" for b in C.BLOCOS]
    info = no_mes[[c for c in campos if c in no_mes.columns]].reset_index()
    cart = cart.merge(info, on="COD_LOJAS", how="left")
    cart["supervisao_especial"] = cart["supervisao_especial"].astype("boolean").fillna(False).astype(bool)
    cart["conta"] = ~cart["supervisao_especial"]          # entra no score e na cobertura
    return cart.reset_index(drop=True)


def filtrar_visao(hier: pd.DataFrame, nivel: str, nome: str | None) -> pd.DataFrame:
    """nivel: 'rede', 'regional' ou 'coordenador'."""
    if nivel == "regional" and nome:
        return hier[hier["regional_mes"] == nome]
    if nivel == "coordenador" and nome:
        return hier[hier["coordenador_mes"] == nome]
    return hier


# ---------------------------------------------------------------------------
# 4. Indicadores de um recorte (rede, regional ou coordenador) no mês
# ---------------------------------------------------------------------------
def indicadores(recorte: pd.DataFrame) -> dict:
    conta = recorte[recorte["conta"]]
    preench = conta[conta["status"] == "Preencheu"]
    carteira = len(recorte)
    carteira_calc = len(conta)
    n_pre = len(preench)
    return {
        "carteira": carteira,
        "carteira_calculo": carteira_calc,
        "preenchidas": int((recorte["status"] == "Preencheu").sum()),
        "preenchidas_calculo": n_pre,
        "pendentes": int((recorte["status"] != "Preencheu").sum()),
        "supervisao_especial": int(recorte["supervisao_especial"].sum()),
        "cobertura": (n_pre / carteira_calc) if carteira_calc else np.nan,
        "score": preench["score"].mean() if n_pre else np.nan,
        "pct_maduras": (preench["maturidade"].eq("Madura").mean()) if n_pre else np.nan,
        "reativas": int(preench["maturidade"].eq("Reativa").sum()),
        "risco_critico": int(preench["risco"].eq("Risco crítico").sum()),
        "sem_chamados": int(preench["estrutura"].eq("Sem chamados abertos").sum()),
        "lojas_novas": int(recorte["status"].eq("Loja nova").sum()),
    }


def comparacao_rede(valor: float, rede: float) -> str:
    if pd.isna(valor) or pd.isna(rede):
        return ""
    a, b = round(valor, 2), round(rede, 2)
    return "acima da rede" if a > b else "abaixo da rede" if a < b else "na média da rede"


# ---------------------------------------------------------------------------
# 5. % de Não por bloco e por pergunta (só Q1 a Q36, só lojas que contam)
# ---------------------------------------------------------------------------
def percentual_nao(val_mes: pd.DataFrame, cods: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = val_mes[val_mes["COD_LOJAS"].isin(set(cods)) & ~val_mes["supervisao_especial"]]
    linhas = []
    for q in C.PERGUNTAS:
        resp = base[q]
        respondidas = resp.isin(["Sim", "Não"]).sum()
        linhas.append({"pergunta": q, "bloco": C.BLOCO_DA_PERGUNTA[q],
                       "nao": int(resp.eq("Não").sum()), "respondidas": int(respondidas)})
    por_pergunta = pd.DataFrame(linhas)
    por_pergunta["pct_nao"] = por_pergunta["nao"] / por_pergunta["respondidas"].replace(0, np.nan)
    por_bloco = por_pergunta.groupby("bloco", sort=False)[["nao", "respondidas"]].sum().reset_index()
    por_bloco["pct_nao"] = por_bloco["nao"] / por_bloco["respondidas"].replace(0, np.nan)
    return por_bloco, por_pergunta


# ---------------------------------------------------------------------------
# 6. Ranking (coordenador ou regional) no mês
# ---------------------------------------------------------------------------
def ranking(hier: pd.DataFrame, nivel: str, lojas: pd.DataFrame) -> pd.DataFrame:
    """
    nivel 'coordenador' agrupa pelo coordenador do mês; 'regional', pela regional do mês.
    Lojas com supervisão especial ficam fora da carteira e das preenchidas.
    """
    chave = "coordenador_mes" if nivel == "coordenador" else "regional_mes"
    base = hier[hier["conta"]]
    g = base.groupby(chave)
    df = pd.DataFrame({
        "carteira": g.size(),
        "preenchidas": g["status"].apply(lambda s: int((s == "Preencheu").sum())),
        "score": base[base["status"] == "Preencheu"].groupby(chave)["score"].mean(),
    }).reset_index().rename(columns={chave: "nome"})
    df["preenchidas"] = df["preenchidas"].fillna(0).astype(int)
    df = df[df["carteira"] > 0].copy()

    media_rede = df["preenchidas"].sum() / df["carteira"].sum() if df["carteira"].sum() else 0.0
    df["cobertura"] = (df["preenchidas"] / df["carteira"]).clip(upper=1)
    df["cobertura_ajustada"] = (df["preenchidas"] + C.K_COBERTURA * media_rede) / (df["carteira"] + C.K_COBERTURA)

    s = df["score"].fillna(0)
    df["pos_cobertura"] = (df["cobertura_ajustada"] + s / 100000).rank(method="dense", ascending=False).astype(int)
    df["pos_score"] = (s + df["cobertura_ajustada"] / 100000).rank(method="dense", ascending=False).astype(int)

    col_email = "EMAIL_COORDENADOR" if nivel == "coordenador" else "EMAIL_REGIONAL"
    col_nome = "COORDENADOR" if nivel == "coordenador" else "REGIONAL"
    emails = lojas.drop_duplicates(col_nome).set_index(col_nome)[col_email]
    df["email"] = df["nome"].map(emails).fillna("")
    return df.reset_index(drop=True)


def aviso_mes(rank_coord: pd.DataFrame, comp: pd.Timestamp, hoje: date) -> str:
    if inicio_do_mes(hoje) == pd.Timestamp(comp):
        x = int((rank_coord["preenchidas"] > 0).sum())
        return f"Mês em andamento · {x} de {len(rank_coord)} coordenadores já preencheram"
    return "Mês fechado"


def texto_prazo(hoje: date) -> str:
    fim = fim_do_mes(pd.Timestamp(hoje)).date()
    dias = (fim - hoje).days
    mes = MESES_PT[hoje.month]
    return f"último dia para preencher {mes}" if dias == 0 else f"faltam {dias} dias para preencher {mes}"


MESES_PT = {1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril", 5: "maio", 6: "junho", 7: "julho",
            8: "agosto", 9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro"}


def rotulo_mes(comp) -> str:
    comp = pd.Timestamp(comp)
    return f"{MESES_PT[comp.month]} de {comp.year}"


# ---------------------------------------------------------------------------
# 7. Histórico de uma loja
# ---------------------------------------------------------------------------
def historico_loja(val: pd.DataFrame, cod: str) -> pd.DataFrame:
    h = val[val["COD_LOJAS"] == cod].sort_values("competencia")
    return h[["competencia", "timestamp", "COORDENADOR", "SUPERVISOR", "score", "maturidade", "ciclo",
              "quadrante", "risco", "estrutura", "supervisao_especial"] + [f"pct_{b}" for b in C.BLOCOS]]


# ---------------------------------------------------------------------------
# 8. Ausências de coordenadores e regionais
# ---------------------------------------------------------------------------
def _situacao(row: pd.Series, papel: str, hoje: pd.Timestamp) -> tuple[str, pd.Timestamp | None]:
    if row.get(f"STATUS_{'COORDENADOR' if papel == 'COORD' else 'REGIONAL'}", "") == "DEMITIDO":
        return "Vaga aberta", None
    for tipo, rotulo in (("MATERN", "Maternidade"), ("AFAST", "Afastamento"), ("FERIAS", "Férias")):
        ini, ret = row[f"{tipo}_INI_{papel}"], row[f"{tipo}_RET_{papel}"]
        # Mesma regra do Power BI: dentro do período = hoje >= início e hoje < retorno
        if pd.notna(ini) and pd.notna(ret) and ini <= hoje < ret:
            return rotulo, ret
    return "Ativo", None


def _proxima(row: pd.Series, papel: str, hoje: pd.Timestamp) -> tuple[pd.Timestamp | None, str | None]:
    futuras = [(row[f"{t}_INI_{papel}"], r) for t, r in (("FERIAS", "Férias"), ("AFAST", "Afastamento"), ("MATERN", "Maternidade"))
               if pd.notna(row[f"{t}_INI_{papel}"]) and row[f"{t}_INI_{papel}"] > hoje]
    if not futuras:
        return None, None
    return min(futuras, key=lambda x: x[0])


def ausencias(lojas: pd.DataFrame, hoje: date) -> pd.DataFrame:
    """Uma linha por pessoa (coordenador ou regional) com a situação de hoje e a próxima ausência."""
    hoje = pd.Timestamp(hoje)
    linhas = []
    for papel, col_nome, col_email in (("COORD", "COORDENADOR", "EMAIL_COORDENADOR"), ("REG", "REGIONAL", "EMAIL_REGIONAL")):
        for nome, grupo in lojas.groupby(col_nome):
            row = grupo.iloc[0]
            sit, ret = _situacao(row, papel, hoje)
            prox, tipo = _proxima(row, papel, hoje)
            linhas.append({
                "papel": "Coordenador" if papel == "COORD" else "Regional",
                "nome": nome, "email": row[col_email], "lojas": len(grupo),
                "regional": row["REGIONAL"],
                "situacao_hoje": sit, "retorno_previsto": ret,
                "proxima_ausencia": prox, "tipo_proxima": tipo,
                "dias_ate_proxima": (prox - hoje).days if prox is not None else None,
            })
    return pd.DataFrame(linhas)


def ausencia_por_loja(lojas: pd.DataFrame, aus: pd.DataFrame) -> pd.Series:
    sit_c = lojas["COORDENADOR"].map(aus[aus["papel"] == "Coordenador"].set_index("nome")["situacao_hoje"])
    sit_r = lojas["REGIONAL"].map(aus[aus["papel"] == "Regional"].set_index("nome")["situacao_hoje"])
    c, r = sit_c.ne("Ativo"), sit_r.ne("Ativo")
    return pd.Series(np.select([c & r, c, r], ["Coord + Regional ausentes", "Coordenador ausente", "Regional ausente"],
                               default="Cobertura normal"), index=lojas.index)


# ---------------------------------------------------------------------------
# Casos graves e há quanto tempo a loja está neles
# ---------------------------------------------------------------------------
def sinais_graves(df: pd.DataFrame) -> pd.DataFrame:
    """Uma coluna booleana por sinal grave (C.SINAIS_GRAVES), para cada preenchimento."""
    return pd.DataFrame({rot: df[col].eq(valor) for rot, (col, valor) in C.SINAIS_GRAVES.items()}, index=df.index)


def _sequencia_final(flags: pd.Series) -> int:
    """Quantos valores True seguidos existem no fim da série."""
    n = 0
    for v in reversed(flags.tolist()):
        if not v:
            break
        n += 1
    return n


def casos_graves(val: pd.DataFrame, comp: pd.Timestamp) -> pd.DataFrame:
    """
    Lojas cujo preenchimento do mês tem pelo menos um sinal grave.

    Para cada loja: sinais atuais, há quantos preenchimentos seguidos ela está em caso
    grave (qualquer sinal) e desde qual mês, e o mesmo por sinal. A contagem usa os
    preenchimentos válidos até o mês escolhido; mês sem preenchimento não zera nem conta.
    """
    comp = pd.Timestamp(comp)
    base = val[val["competencia"] <= comp].sort_values(["COD_LOJAS", "competencia"])
    do_mes = set(base.loc[base["competencia"] == comp, "COD_LOJAS"])
    base = base[base["COD_LOJAS"].isin(do_mes)]
    flags = sinais_graves(base)
    flags["_algum"] = flags.any(axis=1)
    flags["COD_LOJAS"] = base["COD_LOJAS"]
    flags["competencia"] = base["competencia"]

    linhas = []
    for cod, g in flags.groupby("COD_LOJAS", sort=False):
        atual = g.iloc[-1]
        if not atual["_algum"]:
            continue
        seq = _sequencia_final(g["_algum"])
        por_sinal = {rot: _sequencia_final(g[rot]) for rot in C.SINAIS_GRAVES if atual[rot]}
        linhas.append({
            "COD_LOJAS": cod,
            "sinais": list(por_sinal),
            "qtd_sinais": len(por_sinal),
            "preenchimentos_seguidos": seq,
            "desde": g["competencia"].iloc[-seq],
            "por_sinal": por_sinal,
        })
    cols = ["COD_LOJAS", "sinais", "qtd_sinais", "preenchimentos_seguidos", "desde", "por_sinal"]
    return pd.DataFrame(linhas, columns=cols)
