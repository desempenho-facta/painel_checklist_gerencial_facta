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
# Escala de frequência (desde novembro de 2026). Q1 a Q35 usam 4 níveis sem meio;
# a Q36 é o status da estrutura (ver abaixo). Preenchimentos antigos: Sim vale como Sempre e Não como Nunca.
# Cada nível vale uma parte do ponto da pergunta; Nunca e Às vezes contam como Não
# em % de Não, risco, assiduidade, casos graves e pontos de melhoria.
# ---------------------------------------------------------------------------
NIVEIS = ["Nunca", "Às vezes", "Quase sempre", "Sempre"]
# Q36 desde 11/2026: Sem pendências e Demanda com chamado valem o ponto cheio; Demanda sem chamado vale zero
# e conta como Não. Nos meses antigos, Sim equivale a com chamado e Não a sem chamado.
Q36_SEM_PENDENCIAS = "Sem pendências"
Q36_COM_CHAMADO = "Demanda com chamado"
Q36_SEM_CHAMADO = "Demanda sem chamado"
VALOR_RESPOSTA = {"Nunca": 0.0, "Às vezes": 1 / 3, "Quase sempre": 2 / 3, "Sempre": 1.0, "Sim": 1.0, "Não": 0.0,
                  Q36_SEM_PENDENCIAS: 1.0, Q36_COM_CHAMADO: 1.0, Q36_SEM_CHAMADO: 0.0}
RESPOSTAS_NAO = {"Nunca", "Às vezes", "Não", Q36_SEM_CHAMADO}

# Situação estrutural da loja (coluna "estrutura"), a partir da Q36
ESTRUTURA_SEM_PENDENCIAS = "Sem pendências"
ESTRUTURA_COM_CHAMADO = "Com chamado aberto"
ESTRUTURA_SEM_CHAMADO = "Demanda sem chamado"
ESTRUTURA_DA_RESPOSTA = {Q36_SEM_PENDENCIAS: ESTRUTURA_SEM_PENDENCIAS, Q36_COM_CHAMADO: ESTRUTURA_COM_CHAMADO,
                         "Sim": ESTRUTURA_COM_CHAMADO, Q36_SEM_CHAMADO: ESTRUTURA_SEM_CHAMADO, "Não": ESTRUTURA_SEM_CHAMADO}
ORDEM_ESTRUTURA = [ESTRUTURA_SEM_PENDENCIAS, ESTRUTURA_COM_CHAMADO, ESTRUTURA_SEM_CHAMADO]
ESCALA_DESDE = "2026-11-01"
COR_RESPOSTA = {"Sempre": "#2E7D32", "Sim": "#2E7D32", "Quase sempre": "#7CB342", "Às vezes": "#E07020",
                "Nunca": "#C62828", "Não": "#C62828", Q36_SEM_PENDENCIAS: "#2E7D32", Q36_COM_CHAMADO: "#2E7D32",
                Q36_SEM_CHAMADO: "#C62828"}
MESES_TRANSICAO = 2               # meses com aviso de transição nas faixas de maturidade

# Itens da Q36. Com chamado: motivo, número, data de abertura e detalhe de cada chamado.
# Sem chamado: motivo e descrição de cada demanda. Valores na mesma ordem, separados por " | ".
# Q36_OBS: detalhe único dos preenchimentos antigos (valia para todos os chamados do checklist).
COL_Q36_MOTIVOS = "Q36_MOTIVOS"
COL_Q36_CHAMADOS = "Q36_CHAMADOS"
COL_Q36_ABERTURA = "Q36_ABERTURA"
COL_Q36_DETALHES = "Q36_DETALHES"
COL_Q36_OBS = "Q36_OBS"
COLUNAS_Q36 = [COL_Q36_MOTIVOS, COL_Q36_CHAMADOS, COL_Q36_ABERTURA, COL_Q36_DETALHES, COL_Q36_OBS]

# Coerência entre o motivo e o detalhe: palavras de cada motivo, comparadas sem acento e pelo começo
# da palavra ("INFILTRA" pega infiltração e infiltrando). Palavras de até 3 letras, e as terminadas em $,
# valem só inteiras (PORTA$ não pega portabilidade).
# Motivo sem palavras (Outros) não é verificado.
PALAVRAS_MOTIVO = {
    "SERVIÇO DE INFORMÁTICA": "INFORMATICA COMPUTADOR NOTEBOOK TECLADO MOUSE MONITOR$ MONITORES$ IMPRESSORA INTERNET WIFI WI-FI "
                              "SISTEMA TELEFONE CPU PC TI NOBREAK ESTABILIZADOR ROTEADOR SCANNER HEADSET",
    "INFILTRAÇÃO PAREDES E TETO": "INFILTRA GOTEIRA MOFO UMIDADE UMIDO TETO FORRO PAREDE",
    "MANUTENÇÃO DE PORTAS": "PORTA$ PORTAS$ FECHADURA MACANETA DOBRADICA PORTAO TRANCA",
    "MANUTENÇÃO HIDRÁULICA": "HIDRAULIC VAZAMENTO VAZANDO TORNEIRA PIA VASO DESCARGA ENCANAMENTO CANO$ CANOS$ ESGOTO "
                             "ENTUPI BANHEIRO",
    "SERVIÇOS ELÉTRICOS": "ELETRIC LAMPADA LUZ ILUMINA TOMADA DISJUNTOR FIACAO FIO FIOS$ ENERGIA CIRCUITO INTERRUPTOR "
                          "REATOR "
                          "LUMINARIA",
    "MANUTENÇÃO DE JANELAS": "JANELA VIDRO PERSIANA CORTINA VITRINE",
    "ROUBO / FURTO / ARROMBAMENTO": "ROUBO ROUBAD FURTO FURTAD ARROMBA ASSALTO INVASAO INVADID",
    "MANUTENÇÃO AR-CONDICIONADO": "AR-CONDICIONADO AR CONDICIONADO CLIMATIZ SPLIT REFRIGERA",
    "MANUTENÇÃO BEBEDOURO / PURIFICADOR": "BEBEDOURO PURIFICADOR FILTRO GALAO",
    "MANUTENÇÃO MÓVEIS E UTENSÍLIOS": "MOVEL MOVEIS CADEIRA MESA$ MESAS$ ARMARIO GAVETA BALCAO ESTANTE SOFA POLTRONA PRATELEIRA "
                                      "MONTADOR MONTAGEM UTENSILIO LONGARINA",
    "EXTINTOR: RECARGA": "EXTINTOR RECARGA",
    "EXTINTOR: NOVO": "EXTINTOR RECARGA",
    "DEDETIZAÇÃO": "DEDETIZ BARATA RATO CUPIM INSETO PRAGA FORMIGA POMBO ESCORPI",
    "SERVIÇOS DE REFORMA": "REFORMA PINTURA PINTAR PISO OBRA REBOCO AZULEJO GESSO",
    "COMUNICAÇÃO VISUAL": "FACHADA LETREIRO PLACA ADESIVO BANNER LOGOMARCA TOTEM ENVELOPAMENTO",
    "OUTROS": "",
}
COERENTE = "Coerente"
CITA_OUTRO_MOTIVO = "Cita outro motivo"
NAO_CITA_MOTIVO = "Não cita o motivo"
SEM_DETALHE = "Sem detalhe"
SEM_VERIFICACAO = "Sem verificação"
CORES_COERENCIA = {CITA_OUTRO_MOTIVO: "#C62828", NAO_CITA_MOTIVO: "#E07020", SEM_DETALHE: "#E07020"}

# Atuação da monitoria nos chamados e demandas (aba própria na planilha, uma linha por registro;
# vale o registro mais recente de cada chave).
ABA_ATUACOES = "Atuacoes_Chamados"
COLUNAS_ATUACOES = ["registrado_em", "chave", "cod_loja", "loja", "tipo", "chamado", "motivo", "atuado", "status",
                    "observacao", "responsavel"]
STATUS_ATUACAO = ["Em tratativa", "Resolvido"]

# Motivos e prazo de atendimento (dias corridos) da tabela "Ordem de Atendimentos e SLA" do Facilities.
# None: sem prazo fixo (Reforma e Comunicação visual variam por UF; Outros não tem tabela).
SLA_FACILITIES = {
    "SERVIÇO DE INFORMÁTICA": 2,
    "INFILTRAÇÃO PAREDES E TETO": 30,
    "MANUTENÇÃO DE PORTAS": 10,
    "MANUTENÇÃO HIDRÁULICA": 10,
    "SERVIÇOS ELÉTRICOS": 20,
    "MANUTENÇÃO DE JANELAS": 10,
    "ROUBO / FURTO / ARROMBAMENTO": 5,
    "MANUTENÇÃO AR-CONDICIONADO": 15,
    "MANUTENÇÃO BEBEDOURO / PURIFICADOR": 15,
    "MANUTENÇÃO MÓVEIS E UTENSÍLIOS": 30,
    "EXTINTOR: RECARGA": 30,
    "EXTINTOR: NOVO": 30,
    "DEDETIZAÇÃO": 20,
    "SERVIÇOS DE REFORMA": None,
    "COMUNICAÇÃO VISUAL": None,
    "OUTROS": None,
}

# Palavras comuns que não entram na contagem do detalhe da Q36 (comparadas sem acento).
PALAVRAS_IGNORADAS_Q36 = set("""
LOJA LOJAS PARA COMO ESTA ESTAO ESTAVA FOIS FORAM SERA DESDE AINDA MUITO MUITA MAIS MENOS ESSE ESSA ESTE ESTA ISSO
AQUI ONDE QUANDO PORQUE PELO PELA PELOS PELAS NOSSO NOSSA DELE DELA SOBRE ENTRE APOS ANTES DEPOIS TODOS TODAS TODO
TODA CHAMADO CHAMADOS ABERTO ABERTOS ABERTA ABERTAS AGUARDANDO SOLUCAO PROXIMO PROXIMA LADO SALA PRECISA FAZER
TAMBEM NADA TUDO COMO SENDO TENDO TINHA TEMOS TERA
""".split())

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
# Casos antigos, digitados à mão, validados um a um. Formato: (COD_LOJAS, "AAAA-MM-DD").
# Ficam nos secrets (SUPERVISAO_ESPECIAL_CASOS = [["COD", "AAAA-MM-DD"], ...]),
# porque o repositório é público. Ver dados.aplicar_secrets.
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
# antigas e são a mesma pessoa do cadastro atual. Ficam nos secrets, na tabela
# [ALIAS_COORDENADOR] ("NOME ANTIGO" = "NOME DO CADASTRO"), porque o repositório
# é público. Ver dados.aplicar_secrets.
# ---------------------------------------------------------------------------
ALIAS_COORDENADOR: dict[str, str] = {}

# ---------------------------------------------------------------------------
# Visual Facta
# ---------------------------------------------------------------------------
COR_NAVY = "#154567"          # faixa do cabeçalho dos painéis antigos
COR_FUNDO = "#2A2828"         # fundo grafite dos painéis antigos
COR_CARD = "#353232"
COR_BORDA = "#433f3f"
COR_AZUL_FACTA = "#0080F5"
COR_LARANJA = "#FF5B00"
COR_VERDE = "#2E7D32"
COR_VERMELHO = "#C62828"
COR_AMBAR = "#F0A030"
COR_AZUL = "#2E86C1"
COR_CINZA = "#7A7A7A"

# ---------------------------------------------------------------------------
# Explicações das nomenclaturas (aparecem ao passar o cursor)
# ---------------------------------------------------------------------------
DEFINICAO_MATURIDADE = {
    "Madura": "Score acima de 70 pontos.",
    "Em desenvolvimento": "Score acima de 40 e até 70 pontos.",
    "Reativa": "Score até 40 pontos.",
}

AJUDA = {
    "score": "Pontuação de 0 a 100. Cada pergunta vale o peso do bloco dividido pelo número de perguntas dele; "
             "Sempre (ou Sim) soma o ponto inteiro, Quase sempre 2/3, Às vezes 1/3 e Nunca (ou Não) nada. "
             "Avaliar 12, Treinar 18, Domínio de Método 22, Incentivar 8, Verificar 12, Acompanhar 13, Operação 15.",
    "maturidade": "Reativa: score até 40. Em desenvolvimento: acima de 40 até 70. Madura: acima de 70.",
    "ciclo": "Ciclo fechado: Treinar, Verificar e Acompanhar com 60% ou mais. "
             "Esforço sem acompanhamento: treina, mas não verifica nem acompanha. "
             "Exige sem preparar: verifica ou acompanha sem treinar. Ciclo frágil: os três abaixo de 60%.",
    "quadrante": "Cruza Treinar com Domínio de Método (60% ou mais = bom). "
                 "Treina e domina, Treino ineficaz, Talento natural ou Crítico.",
    "risco": "Conta quantas falhas (Não, Nunca ou Às vezes) a loja teve em Q31 (inadimplência), Q24 (pendências) e Q32 (portabilidade). "
             "0 Sem risco, 1 Atenção, 2 Risco alto, 3 Risco crítico.",
    "estrutura": "Q36. Sem pendências: loja regular. Com chamado aberto: há reparo e o chamado foi registrado. "
                 "Demanda sem chamado: há problema estrutural sem chamado aberto (não conformidade). "
                 "Nos meses antigos, Sim conta como com chamado e Não como sem chamado.",
    "coerencia": "Compara o detalhe de cada chamado com palavras do motivo dele. Cita outro motivo: o detalhe fala de "
                 "outro tipo de problema. Não cita o motivo: nenhuma palavra do motivo aparece. Nos checklists antigos "
                 "o detalhe era um texto só para todos os chamados.",
    "escala": "Desde novembro de 2026, Q1 a Q35 são respondidas em 4 níveis: Nunca (0), Às vezes (1/3), "
              "Quase sempre (2/3) e Sempre (o ponto inteiro). Nunca e Às vezes contam como Não. "
              "Nos meses anteriores, Sim vale como Sempre e Não como Nunca.",
    "sla": "Prazo de atendimento da tabela de SLA do Facilities, contado em dias corridos da abertura do chamado "
           "até a data do preenchimento do checklist. Reforma, Comunicação visual e Outros não têm prazo fixo.",
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
