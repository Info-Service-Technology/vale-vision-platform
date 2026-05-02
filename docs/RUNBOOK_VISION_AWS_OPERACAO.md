# Runbook Operacional: Vision AWS

## Objetivo
Este runbook consolida o procedimento operacional do `vale-vision-platform` em producao na AWS.

Ele deve ser usado para:
- deploy normal da aplicacao
- validacao rapida de saude
- resposta a incidentes comuns
- operacao segura sem reabrir risco desnecessario em Terraform

## Regra de Ouro
- mudanca de `frontend`, `backend` ou `inference`: usar apenas o CI/CD da aplicacao
- mudanca de infraestrutura: usar `terraform.yml` manualmente
- nao rodar `terraform apply` em deploy comum

## Arquitetura Operacional Atual
- frontend buildado e copiado para `backend/app/web`
- backend FastAPI servido no ECS
- inference em servico ECS separado
- imagens publicadas no ECR
- ALB compartilhado na frente
- RDS dedicado do Vision
- imagens de eventos vindas do S3
- uploads locais de avatar/logo servidos em `/static`

## Deploy Normal da Aplicacao

### Quando usar
- alteracao em `frontend/**`
- alteracao em `backend/**`
- alteracao em `inference/**`
- alteracao no workflow de deploy da aplicacao

### O que acontece
1. GitHub Actions roda `deploy.yml`
2. frontend e buildado
3. `frontend/dist` e copiado para `backend/app/web`
4. imagem do backend e rebuildada
5. imagem do inference e rebuildada
6. imagens vao para o ECR
7. ECS faz rollout
8. workflow espera os servicos estabilizarem

### O que nao deve acontecer
- `terraform apply`
- recriacao de banco
- alteracao estrutural de IAM
- mudanca involuntaria de secrets

## Terraform

### Quando usar
Somente quando houver mudanca real de infraestrutura, por exemplo:
- novo bucket
- alteracao de ECS module
- mudanca de ALB
- novo secret
- alteracao de RDS

### Como usar
- executar `terraform.yml` por `workflow_dispatch`
- revisar o plano antes de aceitar qualquer alteracao
- preferir janela controlada

### Regra operacional
Se a mudanca nao exige infraestrutura nova ou alteracao estrutural, nao usar Terraform.

## Variaveis e Secrets do GitHub

### Variables
- `ECR_BACKEND_REPOSITORY_VISION`
- `ECR_INFERENCE_REPOSITORY_VISION`
- `ECS_CLUSTER_NAME_VISION`
- `ECS_BACKEND_SERVICE_NAME_VISION`
- `ECS_INFERENCE_SERVICE_NAME_VISION`

### Secrets
- `AWS_GITHUB_ACTIONS_ROLE_ARN`
- `TF_VAR_DB_PASSWORD`
- `TF_VAR_SMTP_PASSWORD`

## Validacao Rapida de Saude

### 1. ECS
```bash
aws ecs describe-services \
  --cluster sansx-vision-prd-cluster \
  --services sansx-vision-prd-backend sansx-vision-prd-inference \
  --region sa-east-1 \
  --no-cli-pager
```

Verificar:
- `runningCount` esperado
- `pendingCount = 0`
- `rolloutState = COMPLETED`

### 2. Logs do backend
```bash
aws logs tail /ecs/sansx-vision-prd-backend \
  --since 10m \
  --follow \
  --region sa-east-1
```

### 3. Logs do inference
```bash
aws logs tail /ecs/sansx-vision-prd-inference \
  --since 10m \
  --follow \
  --region sa-east-1
```

### 4. Aplicacao
Validar manualmente:
- login
- dashboard
- tela de caambas
- abertura de imagem do evento
- upload de avatar
- upload de logo

## Banco de Dados

### Banco atual
- host: `sansx-vision-prd-mysql.c3840aukce1w.sa-east-1.rds.amazonaws.com`
- user: `sansxvision_app`
- db: `vale_vision`

### Observacao importante
O RDS e privado. Testes de conexao devem ser feitos por:
- bastion
- DBeaver com acesso pela VPC
- workload dentro da AWS

Nao usar a maquina local como fonte de verdade para diagnostico de conectividade do RDS.

### Validacao no bastion
```bash
mysql -h sansx-vision-prd-mysql.c3840aukce1w.sa-east-1.rds.amazonaws.com \
  -P 3306 \
  -u sansxvision_app \
  -p \
  -D vale_vision \
  -e "SHOW TABLES; SELECT COUNT(*) AS users_count FROM users; SELECT COUNT(*) AS events_count FROM events;"
```

## Incidentes Comuns

### 1. Imagem do evento nao carrega
Checar:
- bucket salvo no evento
- permissao da task role do ECS
- se o objeto existe no S3
- logs do backend ao abrir o evento

Buckets esperados de leitura:
- `vale-vision-artifacts-dev`
- `vale-vision-raw-dev`
- `vale-vision-debug-dev`

### 2. Login falhando
Checar:
- logs do backend
- task definition ativa
- variaveis:
  - `MYSQL_HOST`
  - `MYSQL_PORT`
  - `MYSQL_DB`
  - `MYSQL_USER`
- secret de `MYSQL_PASSWORD`
- existencia de `users` no banco restaurado

### 3. Avatar ou logo nao aparece
Checar:
- upload retornou sucesso
- arquivo foi salvo em `backend/app/static/uploads`
- URL gerada aponta para `/static/uploads/...`

### 4. RDS parece indisponivel localmente
Se o erro vier da maquina local com timeout de rede:
- nao concluir que o banco caiu
- repetir validacao via bastion

## Recuperacao de Banco via Bastion

### Quando usar
- schema perdido
- restauracao de base
- repopulacao apos incidente

### Procedimento
1. opcionalmente reduzir backend para `desired-count 0`
2. garantir que o dump existe no bastion
3. restaurar:

```bash
mysql -h sansx-vision-prd-mysql.c3840aukce1w.sa-east-1.rds.amazonaws.com \
  -P 3306 \
  -u sansxvision_app \
  -p \
  vale_vision < ~/vale_vision_dump.sql
```

4. validar tabelas e contagens
5. religar backend

## Checklist Antes de Rodar Terraform
- essa mudanca e realmente de infraestrutura?
- o deploy normal da app nao resolve?
- o plano foi revisado?
- existe risco de tocar:
  - RDS
  - task definition
  - IAM
  - secrets
- existe dump acessivel e caminho de rollback?

Se qualquer resposta for "nao sei", pausar e revisar antes do apply.

## Checklist Antes de Considerar a Plataforma Estavel
- login funcionando
- dashboard abrindo
- imagens de eventos abrindo
- avatar funcionando
- logo funcionando
- backend `COMPLETED`
- inference `COMPLETED`
- sem erro novo nos logs criticos

## Artefatos Sensiveis
Nao versionar no repositorio:
- dumps
- arquivos temporarios de diagnostico da AWS
- exports de task definition com senha
- `task.json` gerado localmente para debug

## Referencias
- [`docs/INFRA_CICD_VISION_AWS.md`](/home/mauroslucios/workspace/python/vale-vision-platform/docs/INFRA_CICD_VISION_AWS.md)
- [`docs/POST_MORTEM_VISION_AWS_CICD_2026-05.md`](/home/mauroslucios/workspace/python/vale-vision-platform/docs/POST_MORTEM_VISION_AWS_CICD_2026-05.md)
- [`infraestructure/terraform/README.md`](/home/mauroslucios/workspace/python/vale-vision-platform/infraestructure/terraform/README.md)
