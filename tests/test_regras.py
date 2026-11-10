"""Testes das regras de negócio. Rodar com: python -m pytest -q"""

import pandas as pd
import pytest

from core import config as C
from core import regras as R


def resposta(ts, cod, coord="COORD A", reg="REG 1", sup="FULANO DE TAL", sim=None, nao_em=(), loja=None):
    """Monta um preenchimento. sim=None: tudo Sim, exceto as perguntas em nao_em."""
    linha = {"timestamp": ts, "REGIONAL": reg, "COORDENADOR": coord, "LOJA": loja or f"{cod} - LOJA {cod}",
             "SUPERVISOR": sup, "COD_LOJAS": cod}
    for q in C.PERGUNTAS:
        linha[q] = "Não" if q in nao_em else "Sim"
    if sim is not None:
        for q in C.PERGUNTAS:
            linha[q] = "Sim" if q in sim else "Não"
    return linha


def loja(cod, coord="COORD A", reg="REG 1", cadastro="01/01/2025", email_c="a@facta.com.br", email_r="r1@facta.com.br"):
    base = {"REGIONAL": reg, "COORDENADOR": coord, "LOJA": f"{cod} - LOJA {cod}", "COD_LOJAS": cod,
            "EMAIL_REGIONAL": email_r, "EMAIL_COORDENADOR": email_c, "STATUS_COORDENADOR": "ATIVO",
            "STATUS_REGIONAL": "ATIVO", "DATA_CADASTRO_LOJA": cadastro}
    for n in ("COORD", "REG"):
        for t in ("FERIAS", "AFAST", "MATERN"):
            base[f"{t}_INI_{n}"] = ""
            base[f"{t}_RET_{n}"] = ""
    return base


def preparar(resps, lojas):
    r = R.preparar_respostas(pd.DataFrame(resps))
    return r, R.validos(r), R.preparar_lojas(pd.DataFrame(lojas))


# --------------------------------------------------------------------------- score
def test_pesos_somam_100():
    assert sum(b["peso"] for b in C.BLOCOS.values()) == 100
    assert len(C.PERGUNTAS) == 36
    assert sum(C.PONTO_POR_SIM.values()) == pytest.approx(100)


def test_score_tudo_sim_e_tudo_nao():
    r, _, _ = preparar([resposta("2026-08-05 10:00:00", "1"), resposta("2026-08-05 11:00:00", "2", sim=[])], [loja("1"), loja("2")])
    assert r.loc[0, "score"] == pytest.approx(100)
    assert r.loc[1, "score"] == pytest.approx(0)


def test_score_exemplo_dominio():
    # Sim em tudo, menos nas 7 de Domínio de Método: perde os 22 pontos do bloco
    r, _, _ = preparar([resposta("2026-08-05 10:00:00", "1", nao_em=C.BLOCOS["Domínio de Método"]["perguntas"])], [loja("1")])
    assert r.loc[0, "score"] == pytest.approx(78)


def test_seguro_nao_entra_no_score():
    linha = resposta("2026-08-05 10:00:00", "1")
    linha.update({"Q37": "Não", "Q38": "Não", "Q39": "Não", "Q40": "Não"})
    r, _, _ = preparar([linha], [loja("1")])
    assert r.loc[0, "score"] == pytest.approx(100)


@pytest.mark.parametrize("nao, esperado", [
    ([], "Madura"),
    (C.BLOCOS["Treinar"]["perguntas"] + C.BLOCOS["Domínio de Método"]["perguntas"], "Em desenvolvimento"),   # 60
    (C.PERGUNTAS[:30], "Reativa"),
])
def test_maturidade(nao, esperado):
    r, _, _ = preparar([resposta("2026-08-05 10:00:00", "1", nao_em=nao)], [loja("1")])
    assert r.loc[0, "maturidade"] == esperado


def test_maturidade_limite_70_e_40():
    # Score exatamente 70 tem que ser "Em desenvolvimento" (limite fechado)
    nao_30 = C.BLOCOS["Treinar"]["perguntas"] + C.BLOCOS["Avaliar"]["perguntas"]          # perde 18 + 12 = 30
    r, _, _ = preparar([resposta("2026-08-05 10:00:00", "1", nao_em=nao_30)], [loja("1")])
    assert r.loc[0, "score"] == pytest.approx(70)
    assert r.loc[0, "maturidade"] == "Em desenvolvimento"


# --------------------------------------------------------------------------- leituras
def test_risco_conta_q31_q24_q32():
    r, _, _ = preparar([resposta("2026-08-05 10:00:00", "1", nao_em=["Q31", "Q24", "Q32"]),
                        resposta("2026-08-05 10:00:00", "2", nao_em=["Q31"])], [loja("1"), loja("2")])
    assert list(r["risco"]) == ["Risco crítico", "Atenção"]


def test_estrutura_q36():
    r, _, _ = preparar([resposta("2026-08-05 10:00:00", "1"), resposta("2026-08-05 10:00:00", "2", nao_em=["Q36"])],
                       [loja("1"), loja("2")])
    assert list(r["estrutura"]) == [C.ESTRUTURA_COM_CHAMADO, C.ESTRUTURA_SEM_CHAMADO]     # meses antigos: Sim e Não


def test_ciclo_e_quadrante():
    treinar = C.BLOCOS["Treinar"]["perguntas"]
    ver_acomp = C.BLOCOS["Verificar"]["perguntas"] + C.BLOCOS["Acompanhar"]["perguntas"]
    r, _, _ = preparar([
        resposta("2026-08-05 10:00:00", "1"),
        resposta("2026-08-05 10:00:00", "2", nao_em=ver_acomp),
        resposta("2026-08-05 10:00:00", "3", nao_em=treinar),
        resposta("2026-08-05 10:00:00", "4", nao_em=treinar + ver_acomp),
    ], [loja(c) for c in "1234"])
    assert list(r["ciclo"]) == ["Ciclo fechado", "Esforço sem acompanhamento", "Exige sem preparar", "Ciclo frágil"]
    assert list(r["quadrante"]) == ["Treina e domina", "Treina e domina", "Talento natural", "Talento natural"]


# --------------------------------------------------------------------------- preenchimento válido
def test_vale_o_ultimo_preenchimento_do_mes():
    r, v, _ = preparar([resposta("2026-08-05 10:00:00", "1", sim=[]), resposta("2026-08-20 10:00:00", "1")], [loja("1")])
    assert len(v) == 1 and v.iloc[0]["score"] == pytest.approx(100)


def test_mesmo_horario_fica_o_gravado_por_ultimo():
    r, v, _ = preparar([resposta("2026-08-05 10:00:00", "1", sim=[]), resposta("2026-08-05 10:00:00", "1")], [loja("1")])
    assert v.iloc[0]["score"] == pytest.approx(100)


def test_meses_diferentes_valem_separados():
    _, v, _ = preparar([resposta("2026-07-05 10:00:00", "1"), resposta("2026-08-05 10:00:00", "1")], [loja("1")])
    assert len(v) == 2


# --------------------------------------------------------------------------- supervisão especial
@pytest.mark.parametrize("sup", ["LOJA SEM SUPERVISOR", "SUPERVISOR EM LICENÇA", "Supervisor de Férias", "supervisor  em licenca"])
def test_supervisao_especial_reconhecida(sup):
    r, _, _ = preparar([resposta("2026-08-05 10:00:00", "1", sup=sup)], [loja("1")])
    assert bool(r.loc[0, "supervisao_especial"])


def test_supervisao_especial_sai_do_score_e_da_cobertura():
    _, v, l = preparar([
        resposta("2026-08-05 10:00:00", "1"),                                   # 100
        resposta("2026-08-05 10:00:00", "2", sim=[], sup="SUPERVISOR DE FÉRIAS"),   # 0, não conta
    ], [loja("1"), loja("2"), loja("3")])
    h = R.hierarquia_do_mes(v, l, pd.Timestamp("2026-08-01"))
    i = R.indicadores(h)
    assert i["carteira"] == 3 and i["carteira_calculo"] == 2
    assert i["preenchidas"] == 2 and i["preenchidas_calculo"] == 1
    assert i["cobertura"] == pytest.approx(0.5)
    assert i["score"] == pytest.approx(100)
    assert i["supervisao_especial"] == 1
    # As respostas da loja continuam como gravadas
    assert h.set_index("COD_LOJAS").loc["2", "score"] == pytest.approx(0)


def test_caso_manual_de_supervisao_especial(monkeypatch):
    monkeypatch.setattr(C, "SUPERVISAO_ESPECIAL_CASOS", {("1", "2026-08-05")})
    r, _, _ = preparar([resposta("2026-08-05 10:00:00", "1", sup="FULANO AUSENTE")], [loja("1")])
    assert bool(r.loc[0, "supervisao_especial"])


# --------------------------------------------------------------------------- carteira, status, coordenador do mês
def test_carteira_do_mes_e_loja_nova():
    _, v, l = preparar([resposta("2026-06-05 10:00:00", "1")],
                       [loja("1"), loja("2", cadastro="15/07/2026"), loja("3", cadastro="10/09/2026"), loja("4")])
    h = R.hierarquia_do_mes(v, l, pd.Timestamp("2026-08-01")).set_index("COD_LOJAS")
    assert "3" not in h.index                         # cadastrada depois do mês
    assert h.loc["1", "status"] == "Não preencheu"   # já preencheu antes
    assert h.loc["2", "status"] == "Loja nova"       # cadastrada há menos de 3 meses
    assert h.loc["4", "status"] == "Nunca preencheu"


def test_coordenador_do_mes():
    _, v, l = preparar([
        resposta("2026-06-05 10:00:00", "1", coord="ANTIGO"),
        resposta("2026-07-05 10:00:00", "1", coord="ANTIGO"),
        resposta("2026-08-05 10:00:00", "2", coord="ANTIGO"),
    ], [loja("1", coord="NOVO"), loja("2", coord="NOVO"), loja("3", coord="NOVO")])
    h = R.hierarquia_do_mes(v, l, pd.Timestamp("2026-08-01")).set_index("COD_LOJAS")
    assert h.loc["2", "coordenador_mes"] == "ANTIGO" and h.loc["2", "origem_coordenador"] == "preenchimento do mês"
    assert h.loc["1", "coordenador_mes"] == "ANTIGO" and h.loc["1", "origem_coordenador"] == "preenchimento anterior"
    assert h.loc["3", "coordenador_mes"] == "NOVO" and h.loc["3", "origem_coordenador"] == "cadastro atual"


def test_alias_de_coordenador(monkeypatch):
    monkeypatch.setattr(C, "ALIAS_COORDENADOR", {"PAULA LIMA": "PAULA DA SILVA LIMA"})
    r, _, _ = preparar([resposta("2026-05-05 10:00:00", "1", coord="Paula  Lima")], [loja("1")])
    assert r.loc[0, "COORDENADOR"] == "PAULA DA SILVA LIMA"


# --------------------------------------------------------------------------- ranking
def _cenario_ranking():
    resps = [resposta("2026-08-05 10:00:00", c, coord="PEQUENA") for c in ("p1", "p2")]                 # 2 de 2
    resps += [resposta("2026-08-05 10:00:00", f"g{i}", coord="GRANDE") for i in range(25)]             # 25 de 27
    lojas = [loja(c, coord="PEQUENA") for c in ("p1", "p2")] + [loja(f"g{i}", coord="GRANDE") for i in range(27)]
    return preparar(resps, lojas)


def test_cobertura_ajustada_k3():
    _, v, l = _cenario_ranking()
    h = R.hierarquia_do_mes(v, l, pd.Timestamp("2026-08-01"))
    rk = R.ranking(h, "coordenador", l).set_index("nome")
    media = 27 / 29
    assert rk.loc["PEQUENA", "cobertura"] == pytest.approx(1.0)
    assert rk.loc["PEQUENA", "cobertura_ajustada"] == pytest.approx((2 + 3 * media) / (2 + 3))
    assert rk.loc["GRANDE", "cobertura_ajustada"] == pytest.approx((25 + 3 * media) / (27 + 3))


def test_desempate_cruzado():
    # Mesma cobertura; desempata pelo score
    _, v, l = preparar([
        resposta("2026-08-05 10:00:00", "a1", coord="A"),
        resposta("2026-08-05 10:00:00", "b1", coord="B", nao_em=["Q1"]),
    ], [loja("a1", coord="A"), loja("b1", coord="B")])
    h = R.hierarquia_do_mes(v, l, pd.Timestamp("2026-08-01"))
    rk = R.ranking(h, "coordenador", l).set_index("nome")
    assert rk.loc["A", "pos_cobertura"] == 1 and rk.loc["B", "pos_cobertura"] == 2
    assert rk.loc["A", "pos_score"] == 1 and rk.loc["B", "pos_score"] == 2


def test_ranking_regional_usa_regional_do_mes():
    _, v, l = preparar([resposta("2026-08-05 10:00:00", "1", reg="REG ANTIGA")], [loja("1", reg="REG 2")])
    h = R.hierarquia_do_mes(v, l, pd.Timestamp("2026-08-01"))
    assert list(R.ranking(h, "regional", l)["nome"]) == ["REG ANTIGA"]


def test_coordenador_anterior_sem_preenchimento_no_mes_vai_para_o_atual():
    # A loja 1 não preencheu em setembro. O coordenador anterior (SAIU) não preencheu nada em setembro.
    resps = [resposta("2026-08-05 10:00:00", "1", coord="SAIU"), resposta("2026-09-05 10:00:00", "2", coord="NOVO")]
    _, v, l = preparar(resps, [loja("1", coord="NOVO"), loja("2", coord="NOVO")])
    h = R.hierarquia_do_mes(v, l, pd.Timestamp("2026-09-01")).set_index("COD_LOJAS")
    assert h.loc["1", "coordenador_mes"] == "NOVO" and h.loc["1", "origem_coordenador"] == "cadastro atual"


def test_regional_do_mes_segue_a_mesma_regra():
    resps = [resposta("2026-08-05 10:00:00", "1", reg="REG ANTIGA"), resposta("2026-09-05 10:00:00", "2", reg="REG ANTIGA")]
    _, v, l = preparar(resps, [loja("1", reg="REG 2"), loja("2", reg="REG 2")])
    h = R.hierarquia_do_mes(v, l, pd.Timestamp("2026-09-01")).set_index("COD_LOJAS")
    assert h.loc["1", "regional_mes"] == "REG ANTIGA" and h.loc["1", "origem_regional"] == "preenchimento anterior"
    h10 = R.hierarquia_do_mes(v, l, pd.Timestamp("2026-10-01")).set_index("COD_LOJAS")
    assert h10.loc["1", "regional_mes"] == "REG 2"


# --------------------------------------------------------------------------- coordenador como supervisor
@pytest.mark.parametrize("sup, coord, esperado", [
    ("CARLA BASTOS DA SILVA", "CARLA BASTOS DA SILVA", True),
    ("CARLA SILVA", "CARLA BASTOS DA SILVA", True),
    ("BRUNA", "BRUNA BARBOSA", False),                       # só o primeiro nome não basta
    ("ANA CAROLINA MOURA", "ANA PAULA REIS", False),
    ("TANIA RAMOS", "TANIA RAMOS DA SILVA DIAS", True),
    ("MARIA DA SILVA", "MARIA DE SOUZA", False),             # partícula não conta como sobrenome
])
def test_supervisor_e_coordenador(sup, coord, esperado):
    assert R.supervisor_e_coordenador(sup, coord) is esperado


def test_coordenador_como_supervisor_sai_do_score():
    r = R.preparar_respostas(pd.DataFrame([resposta("2026-09-16 10:00:00", "1", coord="TANIA RAMOS DA SILVA DIAS",
                                                    sup="Tania Ramos da Silva Dias")]))
    assert bool(r.loc[0, "supervisao_especial"]) and r.loc[0, "tipo_especial"] == "Coordenador como supervisor"


# --------------------------------------------------------------------------- casos graves
def test_casos_graves_conta_preenchimentos_seguidos():
    criticas = list(C.PERGUNTAS_RISCO)
    resps = [
        resposta("2026-06-05 10:00:00", "1"),                       # bom
        resposta("2026-07-05 10:00:00", "1", nao_em=criticas),      # risco crítico
        resposta("2026-09-05 10:00:00", "1", nao_em=criticas),      # agosto sem preenchimento não zera
        resposta("2026-09-05 10:00:00", "2"),                       # loja sem sinal
    ]
    _, v, _ = preparar(resps, [loja("1"), loja("2")])
    g = R.casos_graves(v, pd.Timestamp("2026-09-01")).set_index("COD_LOJAS")
    assert list(g.index) == ["1"]
    assert "Risco crítico" in g.loc["1", "sinais"]
    assert g.loc["1", "por_sinal"]["Risco crítico"] == 2
    assert g.loc["1", "desde"] == pd.Timestamp("2026-07-01")


def test_reativa_e_sinal_grave():
    _, v, _ = preparar([resposta("2026-09-05 10:00:00", "1", sim=[])], [loja("1")])
    g = R.casos_graves(v, pd.Timestamp("2026-09-01"))
    assert {"Reativa", "Risco crítico", "Quadrante crítico", "Ciclo frágil"} <= set(g.loc[0, "sinais"])


# --------------------------------------------------------------------------- % Não
def test_percentual_nao_so_q1_a_q36_e_sem_especial():
    linha = resposta("2026-08-05 10:00:00", "1", nao_em=["Q1"])
    linha.update({"Q37": "Não"})
    _, v, l = preparar([linha, resposta("2026-08-05 10:00:00", "2", sim=[], sup="LOJA SEM SUPERVISOR")], [loja("1"), loja("2")])
    blocos, perguntas = R.percentual_nao(v, pd.Series(["1", "2"]))
    assert set(perguntas["pergunta"]) == set(C.PERGUNTAS)
    assert perguntas.set_index("pergunta").loc["Q1", "pct_nao"] == pytest.approx(1.0)
    assert blocos.set_index("bloco").loc["Avaliar", "pct_nao"] == pytest.approx(1 / 3)


# --------------------------------------------------------------------------- ausências
def test_ausencias():
    lj = [loja("1", coord="C1"), loja("2", coord="C2"), loja("3", coord="C3")]
    lj[0].update({"FERIAS_INI_COORD": "20/10/2026", "FERIAS_RET_COORD": "03/11/2026"})
    lj[1].update({"STATUS_COORDENADOR": "DEMITIDO"})
    lj[2].update({"FERIAS_INI_COORD": "10/11/2026", "FERIAS_RET_COORD": "20/11/2026"})
    a = R.ausencias(R.preparar_lojas(pd.DataFrame(lj)), pd.Timestamp("2026-10-27").date())
    a = a[a.papel == "Coordenador"].set_index("nome")
    assert a.loc["C1", "situacao_hoje"] == "Férias"
    assert a.loc["C2", "situacao_hoje"] == "Vaga aberta"
    assert a.loc["C3", "situacao_hoje"] == "Ativo" and a.loc["C3", "dias_ate_proxima"] == 14


# ---------------------------------------------------------------------------
# Chamados da Q36 e prazo do SLA
# ---------------------------------------------------------------------------
def test_chamados_q36_prazo_do_sla():
    base = {"timestamp": "2026-11-10 10:00:00", "REGIONAL": "R", "COORDENADOR": "C", "LOJA": "1 - LOJA A - RS",
            "SUPERVISOR": "PAULA LIMA", "COD_LOJAS": "1"}
    linha = {**base, **{q: "Sim" for q in C.PERGUNTAS},
             C.COL_Q36_MOTIVOS: "SERVIÇO DE INFORMÁTICA | MANUTENÇÃO HIDRÁULICA | SERVIÇOS DE REFORMA",
             C.COL_Q36_CHAMADOS: "1001 | 1002 | 1003",
             C.COL_Q36_ABERTURA: "2026-11-01 | 2026-11-05 | 2026-10-01",
             C.COL_Q36_OBS: "TESTE"}
    antiga = {**base, "timestamp": "2026-10-10 10:00:00", **{q: "Sim" for q in C.PERGUNTAS}}
    val = R.validos(R.preparar_respostas(pd.DataFrame([linha, antiga])))
    ch = R.chamados_q36(val)
    assert list(ch["chamado"]) == ["1001", "1002", "1003"]
    assert list(ch["dias_aberto"]) == [9, 5, 40]
    assert list(ch["situacao_sla"]) == ["Fora do prazo", "Dentro do prazo", "Sem prazo definido"]
    assert (ch["detalhe"] == "TESTE").all()


def test_chamados_q36_sem_colunas_novas():
    base = {"timestamp": "2026-10-10 10:00:00", "REGIONAL": "R", "COORDENADOR": "C", "LOJA": "1 - LOJA A - RS",
            "SUPERVISOR": "PAULA LIMA", "COD_LOJAS": "1", **{q: "Sim" for q in C.PERGUNTAS}}
    val = R.validos(R.preparar_respostas(pd.DataFrame([base])))
    assert R.chamados_q36(val).empty


# ---------------------------------------------------------------------------
# Escala de frequência (Nunca, Às vezes, Quase sempre, Sempre)
# ---------------------------------------------------------------------------
def _linha_escala(nivel, **extra):
    base = {"timestamp": "2026-11-10 10:00:00", "REGIONAL": "R", "COORDENADOR": "C", "LOJA": "1 - LOJA A - RS",
            "SUPERVISOR": "PAULA LIMA", "COD_LOJAS": "1"}
    return {**base, **{q: nivel for q in C.PERGUNTAS if q != "Q36"}, "Q36": "Sim", **extra}


def test_escala_score_e_credito():
    df = R.preparar_respostas(pd.DataFrame([_linha_escala("Sempre"), {**_linha_escala("Nunca"), "COD_LOJAS": "2"},
                                            {**_linha_escala("Quase sempre"), "COD_LOJAS": "3"}]))
    s = df.set_index("COD_LOJAS")["score"]
    assert s["1"] == pytest.approx(100)
    # Nunca em tudo, só a Q36 com Sim: vale 1/11 do bloco Operação (15 pontos)
    assert s["2"] == pytest.approx(15 / 11)
    # Quase sempre vale 2/3 em Q1..Q35; Q36 Sim vale inteiro
    assert s["3"] == pytest.approx((100 - 15) * 2 / 3 + 15 * (10 * 2 / 3 + 1) / 11)


def test_escala_nao_conta_nunca_e_as_vezes():
    df = R.preparar_respostas(pd.DataFrame([_linha_escala("Às vezes"), {**_linha_escala("Quase sempre"), "COD_LOJAS": "2"}]))
    d = df.set_index("COD_LOJAS")
    assert d.loc["1", "falhas_criticas"] == 3 and d.loc["1", "risco"] == "Risco crítico"
    assert d.loc["1", "equipe_assidua"] == "Equipe não assídua"
    assert d.loc["2", "falhas_criticas"] == 0 and d.loc["2", "equipe_assidua"] == "Equipe assídua"
    _, por_perg = R.percentual_nao(df.assign(supervisao_especial=False), df["COD_LOJAS"])
    q1 = por_perg.set_index("pergunta").loc["Q1"]
    assert q1["nao"] == 1 and q1["respondidas"] == 2


def test_sim_nao_antigo_continua_igual():
    assert R.credito("Sim") == 1 and R.credito("Não") == 0
    assert R.e_nao("Não") and R.e_nao("Nunca") and R.e_nao("Às vezes") and not R.e_nao("Quase sempre")
    assert R.em_transicao("2026-11-01") and R.em_transicao("2026-12-01") and not R.em_transicao("2027-01-01")


# ---------------------------------------------------------------------------
# Q36 em três situações (desde 11/2026), detalhe por chamado e coerência
# ---------------------------------------------------------------------------
def _q36(cod, situacao, **cols):
    base = {"timestamp": "2026-11-10 10:00:00", "REGIONAL": "R", "COORDENADOR": "C", "LOJA": f"{cod} - LOJA {cod}",
            "SUPERVISOR": "PAULA LIMA", "COD_LOJAS": cod, **{q: "Sempre" for q in C.PERGUNTAS}}
    return {**base, "Q36": situacao, **cols}


def test_q36_tres_situacoes_score_e_estrutura():
    val = R.validos(R.preparar_respostas(pd.DataFrame([
        _q36("1", C.Q36_SEM_PENDENCIAS), _q36("2", C.Q36_COM_CHAMADO), _q36("3", C.Q36_SEM_CHAMADO)])))
    assert list(val["estrutura"]) == [C.ESTRUTURA_SEM_PENDENCIAS, C.ESTRUTURA_COM_CHAMADO, C.ESTRUTURA_SEM_CHAMADO]
    assert list(val["pct_Estrutura"]) == [1.0, 1.0, 0.0]
    assert val["score"].iloc[0] == pytest.approx(100) and val["score"].iloc[1] == pytest.approx(100)
    assert val["score"].iloc[2] < 100
    assert R.e_nao(C.Q36_SEM_CHAMADO) and not R.e_nao(C.Q36_COM_CHAMADO)


def test_chamados_com_detalhe_por_chamado_e_coerencia():
    val = R.validos(R.preparar_respostas(pd.DataFrame([_q36(
        "1", C.Q36_COM_CHAMADO,
        Q36_MOTIVOS="MANUTENÇÃO BEBEDOURO / PURIFICADOR | MANUTENÇÃO HIDRÁULICA | OUTROS",
        Q36_CHAMADOS="10 | 11 | 12", Q36_ABERTURA="2026-11-01 | 2026-11-01 | 2026-11-01",
        Q36_DETALHES="MÓVEIS AGUARDANDO O MONTADOR | VAZAMENTO NA PIA DA COPA | PROBLEMA QUALQUER")])))
    ch = R.chamados_q36(val)
    assert list(ch["detalhe"]) == ["MÓVEIS AGUARDANDO O MONTADOR", "VAZAMENTO NA PIA DA COPA", "PROBLEMA QUALQUER"]
    assert list(ch["coerencia"]) == [C.CITA_OUTRO_MOTIVO, C.COERENTE, C.SEM_VERIFICACAO]
    assert ch["cita"].iloc[0] == "Manutenção móveis e utensílios"
    assert not ch["detalhe_unico"].any()


def test_coerencia_texto_unico_antigo_e_palavras_inteiras():
    val = R.validos(R.preparar_respostas(pd.DataFrame([_q36(
        "1", "Sim", Q36_MOTIVOS="MANUTENÇÃO DE PORTAS | EXTINTOR: NOVO", Q36_CHAMADOS="20 | 21",
        Q36_ABERTURA="2026-11-01 | 2026-11-01", Q36_OBS="SALDO DE PORTABILIDADE E RECARGA DO EXTINTOR")])))
    ch = R.chamados_q36(val)
    assert ch["detalhe_unico"].all()
    # "portabilidade" não conta como porta; os dois motivos de extintor dividem as palavras
    assert list(ch["coerencia"]) == [C.NAO_CITA_MOTIVO, C.COERENTE]
    assert R.coerencia("SERVIÇOS ELÉTRICOS", "") == (C.SEM_DETALHE, "")


def test_demandas_sem_chamado():
    val = R.validos(R.preparar_respostas(pd.DataFrame([
        _q36("1", C.Q36_SEM_CHAMADO, Q36_MOTIVOS="MANUTENÇÃO MÓVEIS E UTENSÍLIOS | SERVIÇOS ELÉTRICOS",
             Q36_DETALHES="CADEIRA QUEBRADA | LÂMPADA QUEIMADA"),
        {**_q36("2", "Não"), "timestamp": "2026-10-05 10:00:00"},
        _q36("3", C.Q36_COM_CHAMADO, Q36_MOTIVOS="OUTROS", Q36_CHAMADOS="9", Q36_ABERTURA="2026-11-01")])))
    dsc = R.demandas_sem_chamado(val)
    assert list(dsc["COD_LOJAS"]) == ["1", "1", "2"]
    assert list(dsc["motivo"]) == ["MANUTENÇÃO MÓVEIS E UTENSÍLIOS", "SERVIÇOS ELÉTRICOS", ""]
    assert list(dsc["coerencia"]) == [C.COERENTE, C.COERENTE, ""]
    assert R.chamados_q36(val)["chamado"].tolist() == ["9"]
