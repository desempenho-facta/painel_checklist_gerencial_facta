"""
Parâmetros de negócio do Painel do Checklist Gerencial.

Tudo que é regra fixa fica aqui, num lugar só. A fonte de verdade é o
BASE_REGRAS_PAINEL_CHECKLIST.md; se uma regra mudar lá, muda aqui.
"""

from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Sao_Paulo")

# ---------------------------------------------------------------------------
# Blocos, perguntas e pesos do score (só Q1 a Q36 entram no score)
# ---------------------------------------------------------------------------
BLOCOS = {
    "Avaliar":           {"perguntas": ["Q1", "Q2", "Q3"], "peso": 12},
    "Treinar":           {"perguntas": ["Q4", "Q5", "Q6", "Q7", "Q8"], "peso": 18},
    "Domínio de Método": {"perguntas": [f"Q{i}" for i in range(9, 16)], "peso": 22},
    "Incentivar":        {"perguntas": ["Q16", "Q17", "Q18"], "peso": 8},
    "Verificar":         {"perguntas": ["Q19", "Q20", "Q21"], "peso": 12},
    "Acompanhar":        {"perguntas": ["Q22", "Q23", "Q24", "Q25"], "peso": 13},
    "Operação":          {"perguntas": [f"Q{i}" for i in range(26, 37)], "peso": 15},
}
PERGUNTAS = [q for b in BLOCOS.values() for q in b["perguntas"]]          # Q1..Q36
BLOCO_DA_PERGUNTA = {q: nome for nome, b in BLOCOS.items() for q in b["perguntas"]}
PONTO_POR_SIM = {q: BLOCOS[b]["peso"] / len(BLOCOS[b]["perguntas"]) for q, b in BLOCO_DA_PERGUNTA.items()}

# Perguntas de leituras específicas
PERGUNTAS_RISCO = {"Q31": "inadimplência (1ª parcela débito)", "Q24": "pendências de contrato", "Q32": "saldos de portabilidade"}
PERGUNTA_ESTRUTURA = "Q36"
PERGUNTA_ASSIDUIDADE = "Q35"

# ---------------------------------------------------------------------------
# Faixas e limiares
# ---------------------------------------------------------------------------
LIMIAR_BLOCO = 0.6                 # bloco "bom" a partir de 60%
MATURIDADE_REATIVA_ATE = 40        # score <= 40
MATURIDADE_DESENV_ATE = 70         # 40 < score <= 70; acima disso, Madura
MESES_LOJA_NOVA = 3                # loja nova: cadastrada há menos de 3 meses
K_COBERTURA = 3                    # força do ajuste da cobertura para carteiras pequenas

NIVEIS_RISCO = {0: "Sem risco", 1: "Atenção", 2: "Risco alto", 3: "Risco crítico"}

# ---------------------------------------------------------------------------
# Supervisão especial: a loja sai do score e da cobertura naquele mês
# ---------------------------------------------------------------------------
# Comparação feita sem acento, em maiúsculas e com espaços normalizados.
SUPERVISAO_ESPECIAL = {
    "LOJA SEM SUPERVISOR",
    "SUPERVISOR EM LICENCA",
    "SUPERVISOR DE FERIAS",
}

# Também conta como supervisão especial quando o próprio coordenador aparece como
# supervisor: precisa bater o primeiro nome e pelo menos um sobrenome (regra de
# regras.supervisor_e_coordenador). Só o primeiro nome não basta.
#
# Casos antigos, digitados à mão, que também contam como supervisão especial.
# Formato: (COD_LOJAS, "AAAA-MM-DD" do preenchimento).
# Pendente de validação do Wesley:
#   ("600064", "2026-07-15")  Suzano: "MARCUS HENRIQUE AUSENTE"
SUPERVISAO_ESPECIAL_CASOS: set[tuple[str, str]] = set()

# ---------------------------------------------------------------------------
# Casos graves: sinais negativos do preenchimento. A loja está em caso grave
# quando o último preenchimento tem pelo menos um destes sinais. O tempo conta
# os preenchimentos seguidos com o sinal (mês sem preenchimento não zera).
# Formato: rótulo exibido -> (coluna, valor).
# ---------------------------------------------------------------------------
SINAIS_GRAVES = {
    "Risco crítico": ("risco", "Risco crítico"),
    "Reativa": ("maturidade", "Reativa"),
    "Quadrante crítico": ("quadrante", "Crítico"),
    "Treino ineficaz": ("quadrante", "Treino ineficaz"),
    "Ciclo frágil": ("ciclo", "Ciclo frágil"),
}

# ---------------------------------------------------------------------------
# Nomes de coordenador que aparecem escritos de outro jeito nas respostas
# antigas e são a mesma pessoa do cadastro atual (confirmado em 28/10/2026).
# ---------------------------------------------------------------------------
ALIAS_COORDENADOR = {
    "ANA PICOLLI": "ANA PAULA PICOLLI",
    "JIANINI MARIN": "JIANINI DA SILVA MARIN",
    "MICHELE SANTOS": "MICHELE MARTINS DOS SANTOS",
}

# ---------------------------------------------------------------------------
# Visual Facta
# ---------------------------------------------------------------------------
COR_NAVY = "#10466E"
COR_LARANJA = "#FF5B00"
COR_VERDE = "#2E7D32"
COR_VERMELHO = "#C62828"
COR_AMBAR = "#F0A030"
COR_AZUL = "#2E86C1"
COR_CINZA = "#7A7A7A"

# ---------------------------------------------------------------------------
# Explicações das nomenclaturas (aparecem ao passar o cursor)
# ---------------------------------------------------------------------------
AJUDA = {
    "score": "Pontuação de 0 a 100. Cada Sim soma o peso do bloco dividido pelo número de perguntas dele. "
             "Avaliar 12, Treinar 18, Domínio de Método 22, Incentivar 8, Verificar 12, Acompanhar 13, Operação 15.",
    "maturidade": "Reativa: score até 40. Em desenvolvimento: acima de 40 até 70. Madura: acima de 70.",
    "ciclo": "Ciclo fechado: Treinar, Verificar e Acompanhar com 60% ou mais. "
             "Esforço sem acompanhamento: treina, mas não verifica nem acompanha. "
             "Exige sem preparar: verifica ou acompanha sem treinar. Ciclo frágil: os três abaixo de 60%.",
    "quadrante": "Cruza Treinar com Domínio de Método (60% ou mais = bom). "
                 "Treina e domina, Treino ineficaz, Talento natural ou Crítico.",
    "risco": "Conta quantos Não a loja deu em Q31 (inadimplência), Q24 (pendências) e Q32 (portabilidade). "
             "0 Sem risco, 1 Atenção, 2 Risco alto, 3 Risco crítico.",
    "estrutura": "Q36. Com chamados abertos é bom: o problema de estrutura foi registrado. "
                 "Sem chamados abertos é alerta.",
    "cobertura": "Lojas que preencheram no mês dividido pela carteira do mês. "
                 "Lojas com supervisão especial ficam fora da conta.",
    "cobertura_ajustada": "Cobertura corrigida pelo tamanho da carteira (K = 3): carteiras pequenas são puxadas "
                          "para a média da rede, para 2 de 2 não valer mais que 25 de 27. Usada para ordenar o ranking.",
    "status": "Preencheu: tem preenchimento no mês. Não preencheu: já preencheu antes, mas não neste mês. "
              "Loja nova: cadastrada há menos de 3 meses e nunca preencheu. Nunca preencheu: as demais.",
    "supervisao_especial": "Preenchimento feito com Loja sem supervisor, Supervisor em licença ou Supervisor de férias. "
                           "As respostas ficam como foram gravadas, mas a loja sai do score e da cobertura no mês.",
    "carteira": "Lojas cadastradas até o último dia do mês selecionado.",
}
