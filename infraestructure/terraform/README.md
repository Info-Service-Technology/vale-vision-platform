# Sansx Vision Terraform

Esta stack provisiona a camada de aplicacao do `sansx-vision-platform` reaproveitando a base compartilhada do HDI na AWS, mas com o deploy realinhado para o mesmo padrao operacional do HDI.

## Padrao Arquitetural
- o frontend React continua separado no desenvolvimento
- em producao o frontend e buildado e copiado para dentro do backend FastAPI
- o backend serve a SPA, os assets do frontend e os uploads em `/static`
- o ALB aponta o host canonico e o subdominio de API para o mesmo servico ECS do backend
- o servico de inference continua separado

Esse desenho reduz custo, simplifica deploy e deixa a operacao coerente com o HDI. Se no futuro o produto precisar, ainda e possivel separar frontend ou banco sem reescrever toda a base Terraform.

## Modos de Operacao
- Shared platform mode: reutiliza `VPC`, `ECS Cluster`, `ALB HTTPS Listener` e `Route 53` ja existentes
- Dedicated DB mode: cria um `RDS MySQL` proprio para o Vision
- Dedicated ECS mode: cria um `ECS Cluster` proprio para o Vision, mantendo ALB e rede compartilhados se desejado

## Estrutura
- `envs/prd`: composicao do ambiente de producao
- `modules/ecr`: repositorios ECR de `backend` e `inference`
- `modules/s3`: bucket de artefatos
- `modules/logs`: grupos de log do CloudWatch
- `modules/secrets`: segredos do Secrets Manager
- `modules/security`: security groups de ECS, ALB e RDS
- `modules/alb_app`: target group e listener rules do ALB compartilhado
- `modules/ecs_app`: task definitions, IAM roles e servicos ECS
- `modules/rds`: RDS opcional para isolamento futuro do Vision
- `modules/github_oidc`: role OIDC para GitHub Actions

## O Que Foi Reaproveitado Do HDI
- Terraform modular
- estrategia de plataforma compartilhada
- GitHub OIDC para autenticacao na AWS
- fluxo `frontend build -> copia para backend -> deploy da imagem web`
- padrao `ECR + ECS + ALB`

## O Que Foi Adaptado Para O Vision
- prefixo `sansx`
- dominio canonico `sensxvisionplatform.com`
- redirects HTTPS de:
  - `www.sensxvisionplatform.com`
  - `sensxvisionplatform.com.br`
  - `www.sensxvisionplatform.com.br`
- host de API dedicado em `api.sensxvisionplatform.com`
- servico `inference` independente
- opcao de RDS dedicado no futuro
- opcao de ECS Cluster dedicado no proprio Terraform

## Estrategia de Dominio
- host canonico da plataforma: `sensxvisionplatform.com`
- host de API: `api.sensxvisionplatform.com`
- aliases com redirect 301 HTTPS para o canonico:
  - `www.sensxvisionplatform.com`
  - `sensxvisionplatform.com.br`
  - `www.sensxvisionplatform.com.br`

O redirect e tratado no listener HTTPS do ALB compartilhado.

## CI/CD
- `ci.yml`: validacao de backend, frontend, inference e Terraform
- `terraform.yml`: execucao manual da stack quando houver mudanca real de infraestrutura
- `deploy.yml`: build do frontend, copia para `backend/app/web`, build da imagem do backend, push no ECR e rollout no ECS

## Regra Operacional Atual
- mudancas de frontend, backend e inference devem seguir apenas o fluxo de `deploy.yml`
- `terraform.yml` nao deve rodar em todo push
- `terraform apply` deve ser reservado para mudancas intencionais de infraestrutura
- essa separacao reduz risco em componentes criticos como `RDS`, `IAM`, `Secrets Manager` e `ECS task definition`

## Secrets Manager
- `modules/secrets` agora suporta secret dedicado para SMTP
- o valor de `SMTP_PASSWORD` pode ser criado pelo proprio Terraform com `create_smtp_secret = true`
- ou pode ser reaproveitado a partir de um secret existente com `existing_smtp_secret_arn`
- o ECS injeta `SMTP_PASSWORD` como secret, sem expor a senha em `environment`

## Segredos E Variaveis Do GitHub

### Secret obrigatorio
- `AWS_GITHUB_ACTIONS_ROLE_ARN`
- `TF_VAR_DB_PASSWORD` se `create_dedicated_rds = true`
- `TF_VAR_SMTP_PASSWORD` se `create_smtp_secret = true`

### Variables recomendadas
- `ECR_BACKEND_REPOSITORY_VISION`
- `ECR_INFERENCE_REPOSITORY_VISION`
- `ECS_CLUSTER_NAME_VISION`
- `ECS_BACKEND_SERVICE_NAME_VISION`
- `ECS_INFERENCE_SERVICE_NAME_VISION`

## Documentacao Complementar
- arquitetura e CI/CD: [`docs/INFRA_CICD_VISION_AWS.md`](/home/mauroslucios/workspace/python/vale-vision-platform/docs/INFRA_CICD_VISION_AWS.md)
- dominios e Route 53: [`docs/GUIA_DOMINIOS_VISION_AWS.md`](/home/mauroslucios/workspace/python/vale-vision-platform/docs/GUIA_DOMINIOS_VISION_AWS.md)
- post-mortem operacional: [`docs/POST_MORTEM_VISION_AWS_CICD_2026-05.md`](/home/mauroslucios/workspace/python/vale-vision-platform/docs/POST_MORTEM_VISION_AWS_CICD_2026-05.md)
- runbook operacional: [`docs/RUNBOOK_VISION_AWS_OPERACAO.md`](/home/mauroslucios/workspace/python/vale-vision-platform/docs/RUNBOOK_VISION_AWS_OPERACAO.md)

## Observacoes
- registros apex no Route 53 devem usar `A Alias`, nao `CNAME`
- o health check do ALB para o backend usa `/api/health`
- a validacao local de Terraform pode falhar sem acesso ao `registry.terraform.io`
- para producao, prefira passar `db_password` e `smtp_password` via `TF_VAR_*` no GitHub Actions, nao em `terraform.tfvars`
