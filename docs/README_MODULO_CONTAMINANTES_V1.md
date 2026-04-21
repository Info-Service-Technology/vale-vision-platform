\# MÓDULO DE CONTAMINANTES V1 — PROJETO VALE



\## Objetivo

Adicionar ao software de volumetria um módulo de visão computacional capaz de identificar materiais/contaminantes na caçamba e gerar alerta quando houver incompatibilidade entre o material detectado e o grupo esperado da caçamba.



Exemplos:

\- madeira entrando em caçamba de sucata

\- plástico entrando em caçamba de madeira

\- sucata entrando em caçamba de plástico



\## Status atual

A volumetria já está estabilizada na baseline:



`PRODUTO\_VOLUMETRIA\_RELEASE\_V8`



A estrutura do CSV e do dashboard já foi preparada para receber os campos do módulo de contaminantes.



\## Escopo do V1 de contaminantes

O V1 terá foco em:

\- detectar ou segmentar materiais visíveis na imagem

\- identificar presença de:

&#x20; - madeira

&#x20; - sucata

&#x20; - plastico

\- comparar com o grupo esperado da caçamba

\- gerar sinal de contaminação



\## Classes iniciais previstas

\- madeira

\- sucata

\- plastico



\## Estratégia recomendada

Usar segmentação como abordagem principal, e não apenas classificação simples.



\### Motivos

\- melhor auditoria visual

\- mais transparência do resultado

\- maior robustez para produto

\- melhor base para evoluir depois



\## Fonte inicial de dados

Dataset criado no Roboflow com aproximadamente 367 imagens segmentadas utilizando fluxo com SAM.



\## Integração com a RELEASE\_V8

A integração será feita sem quebrar a volumetria.



\### Pipeline futuro

1\. imagem entra no sistema

2\. módulo de volumetria roda

3\. módulo de contaminantes roda

4\. regras de compatibilidade são aplicadas

5\. CSV e dashboard recebem o resultado consolidado



\## Campos já preparados no CSV

\- contaminantes\_detectados

\- alerta\_contaminacao

\- tipo\_contaminacao

\- severidade\_contaminacao

\- cacamba\_esperada

\- material\_esperado



\## Regras de negócio

Arquivo base:



`config/regras\_contaminacao.json`



Exemplo:

\- grupo madeira aceita madeira

\- grupo sucata aceita sucata

\- grupo plastico aceita plastico

\- demais materiais são considerados contaminantes



\## Saída esperada do módulo

Para cada imagem, o módulo deverá produzir algo como:



\- classes detectadas

\- confiança por classe

\- máscara(s) ou detecção(ões)

\- contaminantes\_detectados

\- alerta\_contaminacao = 0 ou 1

\- tipo\_contaminacao

\- severidade\_contaminacao



\## Arquitetura proposta

\### 1. Detector/segmentador

Arquivo futuro sugerido:

`app/segmentador\_contaminantes.py`



Responsável por:

\- carregar modelo de contaminantes

\- rodar inferência

\- retornar classes e máscaras detectadas



\### 2. Motor de decisão

Arquivo futuro sugerido:

`app/motor\_contaminacao.py`



Responsável por:

\- receber grupo da caçamba

\- receber materiais detectados

\- aplicar regras do `regras\_contaminacao.json`

\- gerar saída padronizada para CSV e dashboard



\### 3. Integração com pipeline principal

Arquivo futuro sugerido:

`app/main\_incremental.py`



Responsável por:

\- chamar o módulo de contaminantes após a volumetria

\- consolidar a saída final no CSV



\## Ordem profissional de implementação

\### Etapa 1

Fechar arquitetura e documentação



\### Etapa 2

Preparar placeholders e interfaces Python



\### Etapa 3

Definir formato exato da saída do modelo de contaminantes



\### Etapa 4

Treinar/validar o modelo de materiais



\### Etapa 5

Integrar ao pipeline da RELEASE\_V8



\### Etapa 6

Ativar alerta de material errado em caçamba errada



\## Fora do escopo imediato

A integração automática via FTP continuará para etapa posterior.



Ordem correta:

1\. estabilizar volumetria

2\. integrar contaminantes

3\. depois integrar FTP



\## Conclusão

O módulo de contaminantes será a próxima grande evolução do software, agregando inteligência operacional além da volumetria.

A arquitetura da RELEASE\_V8 já está sendo organizada para receber esse módulo sem retrabalho estrutural.

