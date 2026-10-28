# Painel Checklist Gerencial Facta

Painel em Streamlit que substitui os três arquivos do Power BI (Coordenador, Regional e Monitoria & Desempenho).
Fica separado do app do formulário: só lê a planilha CheckListAcompanhamento, nunca escreve nela.

## Três apps, um código

| Arquivo | Para quem | O que mostra |
|---|---|---|
| `app_monitoria.py` | Monitoria & Desempenho | Rede, regional ou coordenador, todas as telas |
| `app_regional.py` | Regionais | Só visão de regional, ranking de coordenadores e de regionais, férias |
| `app_coordenador.py` | Coordenadores | Só visão de coordenador, ranking de coordenadores, sem férias |

Cada app é publicado separado, com a própria lista de acesso. As regras ficam num lugar só (`core/`),
então os três sempre mostram os mesmos números.

## Telas

Painel: Visão geral, Lojas, Diagnóstico da loja, Mês a mês.
Leituras: Pontos de atenção, O treino está funcionando?, Risco e estrutura, Casos graves.
Rede: Ranking, Controle de férias (só Monitoria e Regionais).

Na barra lateral escolhe o mês e a visão (Rede, Regional ou Coordenador).
Também dá para abrir direto por link: `?visao=coordenador&nome=JIANINI%20DA%20SILVA%20MARIN&mes=2026-09`

## Regras

Todas as regras de negócio estão em `core/regras.py` e os parâmetros (pesos, limiares, K do ranking,
textos de ajuda, apelidos de coordenador, casos de supervisão especial) em `core/config.py`.
A documentação completa das regras está no arquivo BASE_REGRAS_PAINEL_CHECKLIST.md.

Principais pontos:
1. Vale o último preenchimento de cada loja no mês.
2. Supervisão especial (fora do score e da cobertura do coordenador naquele mês, em destaque): LOJA SEM SUPERVISOR,
   SUPERVISOR EM LICENÇA, SUPERVISOR DE FÉRIAS, ou o próprio coordenador como supervisor (primeiro nome e pelo
   menos um sobrenome iguais; só o primeiro nome não basta).
3. Coordenador e regional do mês: o do preenchimento do mês. Sem preenchimento, o do preenchimento anterior,
   desde que essa pessoa tenha preenchido alguma loja naquele mês. Senão, o atual do cadastro.
4. Ranking por cobertura ajustada: (preenchidas + 3 x média da rede) / (carteira + 3).
5. Caso grave: preenchimento com Risco crítico, Reativa, Quadrante crítico, Treino ineficaz ou Ciclo frágil.
   O tempo conta os preenchimentos seguidos com sinal; mês sem preenchimento não zera.

## Rodar no computador

```
pip install -r requirements.txt
```

Com a planilha (produção): copie `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml`, preencha
com os dados da conta de serviço e rode:

```
streamlit run app_monitoria.py
streamlit run app_regional.py
streamlit run app_coordenador.py
```

Com arquivos locais (teste): coloque `Respostas.csv` e `Lojas.csv` numa pasta e aponte a variável
`CHECKLIST_DADOS_DIR` para ela antes de rodar. No Windows (PowerShell):

```
$env:CHECKLIST_DADOS_DIR="C:\caminho\da\pasta"
streamlit run app_monitoria.py
```

## Testes

```
pytest
```

São 39 testes cobrindo pesos, score, maturidade, risco, estrutura, último preenchimento, supervisão especial
(inclusive coordenador como supervisor), coordenador e regional do mês, ranking, casos graves e ausências.

## Publicar

1. Repositório privado no GitHub: painel_checklist_gerencial_facta.
2. No Streamlit Community Cloud, cada app é um deploy do mesmo repositório apontando para o seu arquivo
   (`app_monitoria.py`, `app_regional.py`, `app_coordenador.py`), com o mesmo conteúdo de secrets.
3. Limite do plano gratuito: cada workspace só pode ter um app privado por vez. Para os três ficarem
   privados ao mesmo tempo há dois caminhos:
   a. três workspaces (um por conta ou organização do GitHub), um app privado em cada;
   b. login com a conta Microsoft (`st.login` com Entra ID): o app pode ficar público, mas só abre para
      quem entrar com o e-mail da Facta. Precisa do registro do app pela TI.
4. A conta de serviço precisa ter acesso de leitor na planilha.

Quando o login entrar, ligar `TRAVAR_POR_EMAIL = true` nos secrets dos apps de regional e coordenador:
a pessoa deixa de escolher o nome e passa a ver só o seu, pelo e-mail da aba de lojas.

Nunca subir o `secrets.toml` nem os CSVs de teste (o `.gitignore` já bloqueia).

## Pendências

1. Login com conta Microsoft (Entra ID) aplicando a regra da Carteira, depois da migração.
2. Campo de observação na Q36 (no app do formulário).
3. Arquivo individual por loja com histórico e pontos de melhoria.
4. Foto mensal da hierarquia (coordenador e regional de cada loja no mês).
