# README_AWS

## Objetivo

Documentar a arquitetura AWS alvo do Vale Vision e a estratégia de reaproveitamento da infraestrutura já existente do HDI.

## Princípios

A arquitetura segue o AWS Well-Architected Framework, com foco em:

- excelência operacional
- segurança
- confiabilidade
- eficiência de performance
- otimização de custos
- sustentabilidade citeturn940174search1turn940174search5

## Estratégia de reuso

### Compartilhar
- VPC
- subnets
- ECS cluster
- ALB
- Route 53 hosted zone
- ACM, se fizer sentido

### Criar recursos próprios Vale Vision
- ECR repositories
- ECS services
- task definitions
- target groups
- listener rules
- security groups
- log groups
- Secrets Manager
- bucket S3
- banco/schema próprio

## Arquitetura alvo

```text
Internet / operador
        ↓
ALB compartilhado
        ↓
Frontend Vale Vision (ECS/Fargate)
        ↓
Backend Vale Vision (ECS/Fargate)
        ↓
RDS MySQL / S3 / Secrets Manager / CloudWatch
        ↑
Worker de inferência (ECS/Fargate ou job)
```

## Componentes

### ECS/Fargate
Usado para:
- frontend
- backend
- inference worker

Para tasks em `awsvpc`, os target groups do ALB devem usar `target_type = "ip"`. citeturn940174search4turn940174search8turn940174search20

### ALB
Pode ser compartilhado com o HDI desde que o Vale Vision tenha:
- target groups próprios;
- regras próprias;
- SGs próprios;
- health checks próprios.

### RDS MySQL
Opções:
- fase 1: novo database na mesma instância do HDI;
- fase 2: instância própria.

A AWS recomenda tratar segurança de credenciais e isolamento adequadamente, inclusive usando Secrets Manager. citeturn940174search2turn940174search10

### S3
Usado para:
- imagens de entrada;
- imagens debug;
- máscaras;
- artefatos de inferência;
- datasets e amostras controladas.

Boas práticas:
- Block Public Access ativado;
- criptografia habilitada;
- bucket policies mínimas. citeturn940174search3turn940174search7turn940174search11turn940174search15

### CloudWatch
Usado para:
- logs de containers;
- métricas;
- troubleshooting;
- alarmes futuros.

### ECR
Usado para armazenar imagens:
- vale-vision-backend
- vale-vision-frontend
- vale-vision-inference

## Rede

### Recomendação
- ALB em subnets públicas
- ECS tasks em subnets privadas
- RDS em subnets privadas
- saída controlada via NAT Gateway

A AWS documenta NAT Gateway como o caminho mais simples para permitir saída de tasks privadas para outros serviços. citeturn940174search16

## Segurança

- SG próprio para ALB do Vale Vision
- SG próprio para ECS
- SG próprio para RDS
- segredos em Secrets Manager
- princípio do menor privilégio
- logs centralizados
- sem credenciais hardcoded

## Nomenclatura recomendada

Use prefixos claros para evitar conflito com o HDI:

- `vale-vision-prod-alb-sg`
- `vale-vision-prod-ecs-sg`
- `vale-vision-prod-rds-sg`
- `vale-vision-prod-backend-tg`
- `vale-vision-prod-frontend-tg`
- `vale-vision-prod-artifacts`

## Terraform

Estrutura sugerida:

```text
infra/
├── modules/
│   ├── app_alb_rules/
│   ├── app_ecs_service/
│   ├── app_ecr/
│   ├── app_s3/
│   ├── app_rds/
│   └── app_logs/
└── envs/
    ├── dev/
    └── prod/
```

## CI/CD

Fluxo recomendado:
- GitHub Actions
- build das imagens
- push para ECR
- deploy ECS
- Terraform para infra

## Escalabilidade

### Fase inicial
- ALB compartilhado
- ECS cluster compartilhado
- RDS compartilhado por instância, com database separado

### Fase madura
- banco próprio
- possível ALB próprio
- conta AWS própria, se houver exigência de governança

## O que não versionar no Git

Não colocar no Git normal:
- datasets grandes
- outputs
- debug massivo
- SQLite
- backups
- bancos gerados

Usar:
- Git para código e docs
- Git LFS com moderação para poucos binários
- S3 para artefatos pesados
