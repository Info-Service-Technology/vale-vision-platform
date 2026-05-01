# Guia de Dominios do Sansx Vision na AWS

## Objetivo
Criar e publicar os dominios:
- `sensxvisionplatform.com`
- `sensxvisionplatform.com.br`

Com a seguinte regra:
- dominio canonico final: `https://sensxvisionplatform.com`
- todos os aliases e variacoes devem redirecionar para o canonico em HTTPS

## Dominios Esperados
- `sensxvisionplatform.com`
- `www.sensxvisionplatform.com`
- `api.sensxvisionplatform.com`
- `sensxvisionplatform.com.br`
- `www.sensxvisionplatform.com.br`

## Arquitetura de DNS
- `sensxvisionplatform.com` -> `A Alias` no Route 53 apontando para o ALB
- `api.sensxvisionplatform.com` -> `A Alias` no Route 53 apontando para o ALB
- aliases `.com.br` e `www` -> `A Alias` no Route 53 apontando para o mesmo ALB
- o redirect 301 para o canonico e feito pelo listener HTTPS do ALB

## Antes de Comecar
Voce precisa confirmar:
- em qual conta AWS estao os dominios
- se ja existem hosted zones no Route 53
- se o ALB HTTPS compartilhado do HDI sera reutilizado
- se ja existe certificado ACM cobrindo os novos dominios

Se o dominio `healthdataanalytics.net` estiver no mesmo padrao de hospedagem, ele pode servir de referencia para hosted zone, certificado e listener compartilhado.

## Passo a Passo

### 1. Confirmar registro dos dominios
Verifique onde `sensxvisionplatform.com` e `sensxvisionplatform.com.br` estao registrados.

### 2. Criar ou localizar as hosted zones
No Route 53:
- localizar ou criar a hosted zone publica de `sensxvisionplatform.com`
- localizar ou criar a hosted zone publica de `sensxvisionplatform.com.br`

Anote:
- `primary_hosted_zone_id`
- `secondary_hosted_zone_id`

### 3. Confirmar o ALB compartilhado
No ambiente AWS do HDI, localizar:
- `ALB HTTPS listener ARN`
- `ALB security group`
- `ECS cluster ARN`
- `ECS cluster name`
- `VPC ID`
- `private subnet IDs`

### 4. Emitir ou atualizar o certificado ACM
No ACM em `sa-east-1`, o certificado precisa cobrir:
- `sensxvisionplatform.com`
- `www.sensxvisionplatform.com`
- `api.sensxvisionplatform.com`
- `sensxvisionplatform.com.br`
- `www.sensxvisionplatform.com.br`

Se ja houver um certificado compartilhado, confirmar se ele aceita incluir esses SANs.

### 5. Atualizar o `terraform.tfvars`
Arquivo: [`infraestructure/terraform/envs/prd/terraform.tfvars.example`](/home/mauroslucios/workspace/python/vale-vision-platform/infraestructure/terraform/envs/prd/terraform.tfvars.example)

Defina pelo menos:
- `vpc_id`
- `private_subnet_ids`
- `public_subnet_ids`
- `ecs_cluster_arn`
- `ecs_cluster_name`
- `alb_https_listener_arn`
- `shared_alb_sg_id`
- `primary_hosted_zone_id`
- `secondary_hosted_zone_id`
- `frontend_host = "sensxvisionplatform.com"`
- `backend_host = "api.sensxvisionplatform.com"`

### 6. Revisar os aliases
No `terraform.tfvars`, mantenha:

```hcl
frontend_redirect_hosts = [
  "www.sensxvisionplatform.com",
  "sensxvisionplatform.com.br",
  "www.sensxvisionplatform.com.br"
]

frontend_dns_records = [
  { zone_id = "ZPRIMARY123", name = "www.sensxvisionplatform.com" },
  { zone_id = "ZSECONDARY456", name = "sensxvisionplatform.com.br" },
  { zone_id = "ZSECONDARY456", name = "www.sensxvisionplatform.com.br" }
]
```

### 7. Planejar com Terraform
Rodar:

```bash
terraform -chdir=infraestructure/terraform/envs/prd init
terraform -chdir=infraestructure/terraform/envs/prd plan
```

### 8. Aplicar
Rodar:

```bash
terraform -chdir=infraestructure/terraform/envs/prd apply
```

### 9. Validar
Testar:
- `https://sensxvisionplatform.com`
- `https://www.sensxvisionplatform.com`
- `https://sensxvisionplatform.com.br`
- `https://www.sensxvisionplatform.com.br`
- `https://api.sensxvisionplatform.com/api/health`

Resultados esperados:
- o dominio canonico responde a aplicacao
- `www` e `.com.br` redirecionam para `https://sensxvisionplatform.com`
- o host de API responde `{"status":"ok"}`

## Checklist Rapido
- dominios registrados
- hosted zones publicas criadas
- certificado ACM valido
- listener HTTPS compartilhado confirmado
- variaveis do Terraform preenchidas
- plan revisado
- apply executado
- redirects validados
