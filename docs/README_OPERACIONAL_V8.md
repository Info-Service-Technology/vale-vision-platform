\# PRODUTO VOLUMETRIA RELEASE V8



\## Status atual

Baseline operacional oficial atual do software de volumetria do Projeto Vale.



\## Objetivo

Processar imagens de caçambas, calcular volumetria, classificar status operacional e gerar saídas auditáveis.



\## Arquitetura atual

\- Modelo principal: `best\_pre\_rotulagem\_atual.pt`

\- Classes do modelo: `floor\_visible`, `wall\_visible`

\- Opening: `config/expected\_opening\_mask.png` fixo

\- Motor volumétrico atual: `motor\_volumetria\_permissivo.py`

\- Fluxo: segmentação -> volumetria -> status -> dashboard



\## Estrutura principal

\- `app/` -> código principal

\- `config/` -> máscaras e regras

\- `input/images/` -> imagens de entrada

\- `output/csv/` -> CSVs e metadados

\- `output/debug/` -> imagens de debug

\- `output/masks\_opening/` -> máscaras de opening

\- `output/masks\_floor/` -> máscaras de floor

\- `output/masks\_wall/` -> máscaras de wall



\## Modos de execução



\### 1. Execução completa

Arquivo:

`rodar\_release.bat`



Uso:

Processa novamente todo o lote atual da pasta `input/images`.



\### 2. Execução incremental

Arquivo:

`rodar\_release\_incremental.bat`



Uso:

Processa apenas imagens novas que ainda não estão no `resultado\_volumetria.csv`.



\## Saídas principais



\### resultado\_volumetria.csv

Arquivo principal com saída por imagem:

\- grupo

\- status\_frame

\- fill\_percent\_filtrado

\- estado\_dashboard

\- alerta\_dashboard

\- métricas geométricas

\- campos preparados para contaminantes



\### dashboard\_resumo.csv

Resumo final por grupo de caçamba.



\### run\_info.json

Metadados da execução:

\- timestamp

\- modelo usado

\- pasta de entrada

\- quantidade processada

\- caminhos de saída



\## Regras operacionais atuais

\- `ok` = aceitar

\- `suspeito` = revisar

\- `invalido` = descartar frame



\## Baseline validada

Resultado validado:

\- total: 150 imagens

\- ok: 150

\- suspeito: 0

\- invalido: 0



\## Contaminantes

A arquitetura já foi preparada para o módulo futuro de contaminantes.



Arquivo de regras:

`config/regras\_contaminacao.json`



Campos já previstos no CSV:

\- `contaminantes\_detectados`

\- `alerta\_contaminacao`

\- `tipo\_contaminacao`

\- `severidade\_contaminacao`

\- `cacamba\_esperada`

\- `material\_esperado`



\## Próxima evolução prevista

Adicionar detector de contaminantes/objetos para alertar entrada de material errado em caçamba errada, por exemplo:

\- madeira em sucata

\- plástico em madeira

\- sucata em plástico



\## Observação importante

A baseline histórica anterior continua preservada em:

`PRODUTO\_VOLUMETRIA\_RELEASE\_V1`

