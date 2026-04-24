# Vale Vision Platform

Plataforma para monitoramento visual de caçambas da Vale S.A., com foco em:

- identificação do material depositado por imagem;
- validação de compatibilidade entre material detectado e caçamba esperada;
- cálculo de volumetria;
- geração de alertas de contaminação e operação;
- rastreabilidade por evento, imagem e artefatos de debug.

## Objetivo do projeto

O sistema foi desenhado para responder a uma regra operacional simples e crítica:

- caçamba de **sucata** deve receber **sucata**;
- caçamba de **plástico** deve receber **plástico**;
- caçamba de **madeira** deve receber **madeira**.

Quando o pipeline detecta material divergente, o evento deve ser registrado com:

- caçamba esperada;
- material esperado;
- materiais detectados;
- contaminantes detectados;
- severidade;
- imagem e evidências de debug.

No pipeline legado, essa regra já existe na camada de decisão de contaminação e produz campos como `contaminantes_detectados`, `alerta_contaminacao`, `tipo_contaminacao`, `cacamba_esperada` e `material_esperado`.

## Visão geral da arquitetura alvo

A arquitetura alvo separa o sistema em quatro blocos principais:

1. **Frontend**
   - React + Vite + Material UI
   - interface operacional e corporativa
   - dashboards, filtros, tabela de eventos e detalhe visual

2. **Backend**
   - FastAPI
   - autenticação JWT
   - API REST para eventos, usuários, tenants, câmeras e caçambas
   - acesso a MySQL

3. **Inference / Pipeline**
   - serviço Python separado para processar imagens
   - inferência de volumetria
   - inferência de contaminantes
   - regras de decisão e publicação dos resultados

4. **AWS**
   - ECS/Fargate para execução dos containers
   - ALB para exposição dos serviços
   - RDS MySQL para persistência
   - S3 para artefatos (imagens, debug, máscaras, outputs)
   - ECR para imagens Docker
   - CloudWatch para logs
   - Secrets Manager para segredos

## Fluxo macro

```text
Câmera / upload / ingestão
        ↓
S3 / diretório de entrada
        ↓
Worker de inferência
        ↓
API / banco MySQL
        ↓
Frontend React/MUI
```

## Estrutura sugerida do repositório

```text
vale-vision-platform/
├── frontend/
├── backend/
├── inference/
├── infra/
├── docs/
├── legacy/
└── samples/
```

## Documentação deste repositório

- `README_FRONTEND.md`
- `README_BACKEND.md`
- `README_AWS.md`

## Observações de arquitetura

- A arquitetura proposta segue os princípios do AWS Well-Architected Framework, que organiza boas práticas em seis pilares: excelência operacional, segurança, confiabilidade, eficiência de performance, otimização de custos e sustentabilidade. citeturn940174search1turn940174search5
- Para workloads em ECS com `awsvpc`, os target groups do ALB devem usar `target_type = "ip"`. citeturn940174search4turn940174search20
- Para o banco, o uso de credenciais em Secrets Manager é a direção recomendada pela AWS para RDS. citeturn940174search2turn940174search10turn940174search6
- Para S3, a prática recomendada é manter bloqueio de acesso público e criptografia habilitados. citeturn940174search3turn940174search7turn940174search11

## Estado atual x estado alvo

### Estado atual
- Streamlit
- SQLite
- CSV como integração principal
- loop manual/infinito para processamento
- artefatos locais

### Estado alvo
- React/MUI
- FastAPI
- MySQL
- containers
- ECS/Fargate
- S3
- ALB compartilhado com isolamento lógico
- Terraform
- CI/CD

## Decisão de reuso da infra do HDI

A recomendação para a fase inicial é:

- reutilizar:
  - VPC
  - subnets
  - ECS cluster
  - ALB
  - hosted zone / domínio
- criar recursos próprios do Vale Vision:
  - target groups
  - listener rules
  - security groups
  - ECR
  - log groups
  - Secrets Manager
  - bucket S3
  - banco/schema próprio

Isso reduz custo e evita duplicação de recursos-base, sem misturar identidades, logs, segredos e permissões da aplicação.

## Versionamento

Não devem ir para o Git normal:

- datasets completos
- outputs
- debug
- masks
- bancos SQLite
- backups massivos

Devem ir para Git:

- código
- configs
- docs
- scripts
- samples pequenos
