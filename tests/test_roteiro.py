import pandas as pd
import pytest

from core import regras as R
from core import roteiro as RT


def _semana(coord, segunda, ts, tipos, lojas, motivos=None, status="Original", just=""):
    seg = pd.Timestamp(segunda)
    linhas = []
    for i, (t, l) in enumerate(zip(tipos, lojas)):
        linhas.append({"TIMESTAMP_REGISTRO": ts, "REGIONAL": "REG A", "COORDENADOR": coord,
                       "SEMANA_INICIO": f"{seg:%Y-%m-%d}", "DATA_VISITA": f"{seg + pd.Timedelta(days=i):%Y-%m-%d}",
                       "TIPO": t, "LOJA": f"{l} - LOJA {l}" if l else "", "COD_LOJA": l, "OBJETIVO": "", "OBS": "",
                       "STATUS": status, "JUSTIFICATIVA": just, "MOTIVOS": (motivos or [""] * 5)[i]})
    return linhas


def _rot():
    linhas = []
    # Ana: semana de 05/10 enviada na sexta antes; depois reeditada na terça
    linhas += _semana("ANA", "2026-10-05", "2026-10-02 10:00:00", ["VISITA", "VISITA", "BASE", "VISITA", "FERIADO"],
                      ["1", "2", "9", "1", ""], motivos=["CHECKLIST MENSAL", "", "", "", ""])
    linhas += _semana("ANA", "2026-10-05", "2026-10-06 09:00:00", ["VISITA", "VISITA", "BASE", "VISITA", "FERIADO"],
                      ["1", "3", "9", "1", ""], motivos=["CHECKLIST MENSAL", "", "", "", ""], status="Reeditado",
                      just="TROCA DE LOJA")
    # Ana: semana de 12/10 enviada na quarta da própria semana
    linhas += _semana("ANA", "2026-10-12", "2026-10-14 08:00:00", ["BASE"] * 5, ["9"] * 5)
    return RT.preparar_roteiro(pd.DataFrame(linhas))


def test_versao_vigente_e_reedicao():
    rot = _rot()
    v = RT.vigentes(rot)
    s1 = v[v["SEMANA_INICIO"] == "2026-10-05"]
    assert len(s1) == 5 and set(s1["COD_LOJA"]) == {"1", "3", "9", ""}      # vale a reedição (loja 3, não 2)
    env = RT.envios_semana(rot).set_index("semana")
    assert env.loc[pd.Timestamp("2026-10-05"), "versoes"] == 2
    assert env.loc[pd.Timestamp("2026-10-05"), "antecedencia"] == "Antes da semana"   # conta o primeiro envio
    assert env.loc[pd.Timestamp("2026-10-12"), "antecedencia"] == "Durante a semana"


def test_semanas_do_mes_e_adesao():
    sem = RT.semanas_do_mes(pd.Timestamp("2026-10-01"), pd.Timestamp("2026-11-05"))
    assert [f"{s:%d}" for s in sem] == ["05", "12", "19", "26"]
    # mês corrente: só até a semana atual
    assert len(RT.semanas_do_mes(pd.Timestamp("2026-11-01"), pd.Timestamp("2026-11-05"))) == 1
    ad = RT.adesao(_rot(), ["ANA", "BRUNO"], pd.Timestamp("2026-10-01"), pd.Timestamp("2026-11-05")).set_index("COORDENADOR")
    assert ad.loc["ANA", "semanas_com_roteiro"] == 2 and ad.loc["ANA", "reeditadas"] == 1
    assert ad.loc["BRUNO", "semanas_com_roteiro"] == 0 and pd.isna(ad.loc["BRUNO", "ultimo_envio"])


def test_distancia_e_meta():
    # Base na loja 9 (Porto Alegre). Loja 1 a ~20 km, loja 3 a ~ 380 km (Florianópolis-ish), loja 2 sem ponto
    resp = pd.DataFrame({"COD_LOJAS": ["9", "9", "1", "1", "3", "3", "4"],
                         "LATITUDE": ["-30.03", "-30.03", "-29.95", "-29.95", "-27.59", "-27.59", "-2980863953"],
                         "LONGITUDE": ["-51.23", "-51.23", "-51.10", "-51.10", "-48.55", "-48.55", "-51.2"],
                         "PRECISÃO": ["20", "30", "50", "40", "15", "15", "10"]})
    cart = pd.DataFrame({"COD_LOJAS": ["1", "2", "3", "9", "4"], "coordenador_mes": ["ANA"] * 5})
    m = RT.distancia_e_meta(cart, _rot(), resp).set_index("COD_LOJAS")
    assert m.loc["9", "distancia_km"] == 0 and m.loc["9", "acesso"] == "Fácil acesso"
    assert m.loc["1", "distancia_km"] == pytest.approx(15.6, abs=2) and m.loc["1", "meta_visitas"] == 2
    assert m.loc["3", "acesso"] == "Distante" and m.loc["3", "meta_visitas"] == 1
    assert m.loc["2", "acesso"] == "Sem localização" and m.loc["2", "meta_visitas"] == 2
    assert m.loc["4", "acesso"] == "Sem localização"          # latitude sem ponto decimal é descartada


def test_base_ignora_loja_fora_da_carteira():
    rot = _rot()
    cart = pd.DataFrame({"COD_LOJAS": ["1", "3"], "coordenador_mes": ["ANA", "ANA"]})
    assert RT.base_dos_coordenadores(rot, cart).empty        # a base (9) não é mais da carteira dela
    assert RT.base_dos_coordenadores(rot).loc["ANA"] == "9"


def test_cobertura_conta_visita_e_base():
    rot = _rot()
    cart = pd.DataFrame({"COD_LOJAS": ["1", "2", "3", "9", "5"], "coordenador_mes": ["ANA"] * 5})
    cb = RT.cobertura(cart, rot, pd.DataFrame(columns=["COD_LOJAS", "LATITUDE", "LONGITUDE", "PRECISÃO"]),
                      pd.Timestamp("2026-10-01"), pd.Timestamp("2026-10-20")).set_index("COD_LOJAS")
    assert cb.loc["1", "visitas_mes"] == 2 and cb.loc["1", "situacao_meta"] == "Meta atingida"
    assert cb.loc["2", "visitas_mes"] == 0                    # a loja 2 saiu na reedição
    assert cb.loc["3", "visitas_mes"] == 1 and cb.loc["3", "situacao_meta"] == "Abaixo da meta"
    assert cb.loc["9", "visitas_mes"] == 6 and cb.loc["9", "dias_base_mes"] == 6     # base conta como presença
    assert cb.loc["9", "ultima_visita"] == pd.Timestamp("2026-10-16") and cb.loc["9", "dias_sem_visita"] == 4
    assert pd.isna(cb.loc["5", "ultima_visita"]) and RT.faixa_sem_visita(cb.loc["5", "dias_sem_visita"]) == "Nunca visitada"
    assert cb.loc["1", "dias_sem_visita"] == 12               # última em 08/10


def test_planejado_realizado():
    rot = _rot()
    base = {"REGIONAL": "REG A", "COORDENADOR": "ANA", "SUPERVISOR": "X", **{q: "Sempre" for q in R.C.PERGUNTAS}}
    resp = R.preparar_respostas(pd.DataFrame([
        {**base, "timestamp": "2026-10-05 15:00:00", "LOJA": "1 - LOJA 1", "COD_LOJAS": "1"},   # no dia
        {**base, "timestamp": "2026-10-09 15:00:00", "LOJA": "3 - LOJA 3", "COD_LOJAS": "3"},   # loja no roteiro, outro dia
        {**base, "timestamp": "2026-10-13 15:00:00", "LOJA": "9 - LOJA 9", "COD_LOJAS": "9"},   # base no dia
        {**base, "timestamp": "2026-10-20 15:00:00", "LOJA": "5 - LOJA 5", "COD_LOJAS": "5"},   # sem roteiro na semana
        {**base, "timestamp": "2026-10-06 15:00:00", "LOJA": "7 - LOJA 7", "COD_LOJAS": "7"},   # roteiro sem essa loja
    ]))
    val = R.validos(resp)
    pr = RT.planejado_realizado(rot, val, resp, pd.Timestamp("2026-10-01"))
    sit = dict(zip(pr["COD_LOJAS"], RT.classificar_checklist(pr)))
    assert sit == {"1": RT.ORDEM_CHECKLIST[0], "3": RT.ORDEM_CHECKLIST[1], "9": RT.ORDEM_CHECKLIST[0],
                   "5": RT.ORDEM_CHECKLIST[3], "7": RT.ORDEM_CHECKLIST[2]}
    mot = RT.checklists_motivo(rot, val, pd.Timestamp("2026-10-01"), pd.Timestamp("2026-10-31"))
    assert len(mot) == 1 and bool(mot["feito_no_dia"].iloc[0])


def test_roteiro_vazio_nao_quebra():
    rot = RT.preparar_roteiro(pd.DataFrame())
    assert rot.empty
    cart = pd.DataFrame({"COD_LOJAS": ["1"], "coordenador_mes": ["ANA"]})
    cb = RT.cobertura(cart, rot, pd.DataFrame(), pd.Timestamp("2026-10-01"), pd.Timestamp("2026-10-20"))
    assert cb.loc[0, "situacao_meta"] == "Sem visita no mês"
