# Infra e CI/CD do Sansx Vision na AWS

## Objetivo
Este documento descreve a arquitetura de infraestrutura e o fluxo de CI/CD do `sansx-vision-platform`, seguindo o mesmo principio operacional do HDI: frontend buildado e servido pelo backend.

## Arquitetura Atual
- `frontend`: React + Vite, usado separadamente no desenvolvimento
- `backend`: FastAPI, exposto no ECS Fargate
- `inference`: servico separado para processamento
- `ALB`: listener HTTPS compartilhado
- `Route 53`: dominios e redirects
- `ECR`: imagens de `backend` e `inference`
- `RDS`: pode ser compartilhado com o HDI agora ou dedicado ao Vision depois
- `ECS Cluster`: pode ser compartilhado ou dedicado ao Vision

## Fluxo de Producao
1. O GitHub Actions builda o frontend.
2. O bundle do frontend e copiado para `backend/app/web`.
3. O backend FastAPI e empacotado com esse bundle.
4. O ECS publica um unico servico web principal para a plataforma.
5. O ALB envia tanto `sensxvisionplatform.com` quanto `api.sensxvisionplatform.com` para esse backend.

## Por Que Esse Modelo
- replica o padrao do HDI
- simplifica operacao
- reduz custo de um servico ECS extra para frontend
- elimina a necessidade de Nginx dedicado neste momento
- mantem um caminho claro para separar componentes no futuro

## Componentes Terraform
- `infraestructure/terraform/envs/prd`
- `infraestructure/terraform/modules/alb_app`
- `infraestructure/terraform/modules/ecs_app`
- `infraestructure/terraform/modules/ecr`
- `infraestructure/terraform/modules/github_oidc`
- `infraestructure/terraform/modules/rds`
- `infraestructure/terraform/modules/secrets`

## CI/CD

### `ci.yml`
- valida `backend`
- valida `frontend`
- valida `inference`
- executa `terraform fmt` e `terraform validate`

### `terraform.yml`
- executa `terraform plan`
- executa `terraform apply` com OIDC

### `deploy.yml`
- builda o frontend
- copia `frontend/dist` para `backend/app/web`
- builda e publica a imagem do backend
- builda e publica a imagem do `inference`
- faz rollout no ECS

## Variaveis de Repositorio
- `ECR_BACKEND_REPOSITORY_VISION`
- `ECR_INFERENCE_REPOSITORY_VISION`
- `ECS_CLUSTER_NAME_VISION`
- `ECS_BACKEND_SERVICE_NAME_VISION`
- `ECS_INFERENCE_SERVICE_NAME_VISION`

## Secret Obrigatorio
- `AWS_GITHUB_ACTIONS_ROLE_ARN`
- `TF_VAR_DB_PASSWORD` quando houver RDS dedicado criado por Terraform
- `TF_VAR_SMTP_PASSWORD` quando o Terraform for criar o secret SMTP

## Secrets Manager para SMTP
- o `SMTP_PASSWORD` nao precisa ficar hardcoded no Terraform
- o ambiente `prd` suporta:
  - `create_smtp_secret = true`
  - `smtp_password = "APP_PASSWORD_DO_GOOGLE"`
- ou, se voce ja tiver um secret criado:
  - `existing_smtp_secret_arn = "arn:aws:secretsmanager:..."`
- o ECS recebe esse valor como secret runtime em `SMTP_PASSWORD`
- `SMTP_USERNAME`, `EMAIL_FROM_ADDRESS`, `EMAIL_REPLY_TO` e `EMAIL_SUPPORT_ADDRESS` continuam como configuracoes normais
- no GitHub Actions, o recomendado e publicar a senha como `TF_VAR_SMTP_PASSWORD`

## Dominio e HTTPS
- canonico: `sensxvisionplatform.com`
- API: `api.sensxvisionplatform.com`
- redirects:
  - `www.sensxvisionplatform.com`
  - `sensxvisionplatform.com.br`
  - `www.sensxvisionplatform.com.br`

Todos os acessos devem terminar em HTTPS no dominio canonico `.com`.

## RDS Compartilhado vs Dedicado

### Compartilhado agora
- menor custo inicial
- menos operacao
- mais rapido para subir

### Dedicado depois
- melhor isolamento
- menor risco de `noisy neighbor`
- manutencao independente
- tuning proprio do Vision

## Recomendacao
- curto prazo: manter a stack compartilhada quando isso acelerar o go-live
- medio prazo: provisionar RDS proprio para o Vision se carga, criticidade ou compliance crescerem
- para o caso atual do Vision, o Terraform ja suporta `create_ecs_cluster = true` para isolar o cluster sem redesenhar o restante da stack
