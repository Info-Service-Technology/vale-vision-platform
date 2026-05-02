# Post-Mortem: Vision AWS, CI/CD e Recuperacao Operacional

## Resumo Executivo
No dia 1 de maio de 2026, durante uma janela de ajustes na stack AWS do `vale-vision-platform`, tivemos uma combinacao de falhas operacionais que afetou:
- visualizacao de imagens dos eventos no S3
- autenticacao da aplicacao
- consistencia entre runtime do ECS, secrets e banco RDS
- uploads de avatar e logo

O problema inicial era de acesso as imagens no S3, mas a correcao encostou em componentes mais sensiveis da plataforma: `ECS task definition`, IAM, secrets e configuracao de banco. Isso aumentou o raio de impacto e gerou instabilidade temporaria na aplicacao, inclusive com necessidade de restaurar a base no RDS a partir do dump no bastion.

Ao final da recuperacao:
- o banco `vale_vision` foi restaurado com sucesso
- o login voltou a funcionar
- a leitura de imagens do S3 voltou a funcionar
- avatar e logo passaram a aparecer corretamente apos upload
- o fluxo de CI/CD foi separado de Terraform para reduzir risco operacional

## Impacto
- usuarios nao conseguiam visualizar imagens de eventos em producao
- em momentos da janela de mudanca, o login falhou
- houve instabilidade na interpretacao do estado real do banco por conta da troca de task definitions e restauracao do dump
- a equipe precisou executar recuperacao manual via bastion

## Sintomas Observados
- modal de evento exibindo "Imagem nao disponivel"
- backend respondendo `500` no login
- logs do ECS mostrando erros como:
  - `Access denied for user 'app'`
  - `Unknown database 'sansxvision'`
  - `Table 'vale_vision.users' doesn't exist`
- upload de avatar/logo retornando sucesso, mas a imagem nao aparecia na interface
- testes locais de MySQL falhando com timeout por o RDS estar privado

## Causa Raiz

### 1. Permissao incompleta para leitura dos buckets de imagem
O backend gerava URLs/fluxos dependentes de objetos que estavam em buckets de imagem, mas a task role do ECS nao tinha acesso completo aos buckets realmente usados pelos eventos.

Impacto:
- imagens do S3 nao carregavam na interface

Correcao:
- inclusao de permissao de leitura para:
  - `vale-vision-artifacts-dev`
  - `vale-vision-raw-dev`
  - `vale-vision-debug-dev`

### 2. Divergencia entre a configuracao real do banco e a task definition do ECS
O runtime do backend precisava usar:
- host do RDS dedicado
- banco `vale_vision`
- usuario `sansxvision_app`
- senha vinda do Secrets Manager

Durante a janela de mudanca, havia divergencias entre:
- valores esperados pelo backend
- valores declarados na task definition
- estado restaurado da base

Impacto:
- falha de autenticacao no banco
- tentativa de acesso a banco/schema incorreto
- erro de login da aplicacao

Correcao:
- alinhar `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DB`, `MYSQL_USER`
- injetar `MYSQL_PASSWORD` via secret runtime

### 3. Mistura de deploy de aplicacao com mudanca de infraestrutura critica
O problema original era de app/S3, mas a intervencao encostou em:
- IAM
- task definition
- secrets
- RDS
- Terraform de producao

Isso transformou um ajuste localizado em uma mudanca estrutural da stack.

Impacto:
- risco operacional alto
- dificuldade maior para diagnosticar rapidamente o que era problema de codigo, o que era problema de permissao e o que era problema de infra

### 4. Caminho incorreto para uploads de avatar e logo
Avatar e logo eram gravados fora da pasta realmente servida pelo FastAPI em `/static`.

Impacto:
- upload concluia com sucesso
- URL era salva
- arquivo nao aparecia na interface

Correcao:
- gravar uploads em `backend/app/static/uploads`

## Fatores Contribuintes
- o Vision ainda estava em fase de consolidacao da infra, ao contrario do HDI, que ja esta operacionalmente mais maduro
- o health check `/api/health` nao validava consulta real em tabelas criticas da aplicacao
- testes locais contra o RDS privado geravam falsos caminhos de investigacao, porque a falha era de rede local e nao necessariamente do banco
- falta de separacao mais rigida entre:
  - deploy da aplicacao
  - mudancas de Terraform

## Timeline Resumida
1. Identificado problema de imagem nao carregando do S3.
2. Validado que a aplicacao subia, mas a task role nao tinha acesso correto aos buckets usados pelos eventos.
3. Ajustada a policy da task role para leitura dos buckets de imagem.
4. Durante os ajustes de Terraform e task definition, surgiram falhas de login e erros de banco no ECS.
5. Validado que o RDS correto era:
   - host: `sansx-vision-prd-mysql.c3840aukce1w.sa-east-1.rds.amazonaws.com`
   - user: `sansxvision_app`
   - db: `vale_vision`
6. Houve necessidade de restaurar a base via bastion usando o dump `vale_vision_dump.sql`.
7. Confirmada restauracao com:
   - `users_count = 4`
   - `events_count = 25`
8. Corrigido o caminho dos uploads de avatar/logo.
9. Validado funcionamento final:
   - login ok
   - dashboard ok
   - imagens de evento ok
   - avatar/logo ok

## O Que Mudou no Codigo e na Operacao

### CI/CD
- `deploy.yml` continua automatico para a aplicacao
- `deploy.yml` agora:
  - usa `concurrency`
  - aguarda `aws ecs wait services-stable`

### Terraform
- `terraform.yml` nao deve mais rodar automaticamente
- `terraform apply` fica restrito a disparo manual
- objetivo: evitar mudanca acidental de infra em deploy comum de app

### ECS / Runtime
- task role com leitura dos buckets corretos de imagem
- task definition com variaveis de banco alinhadas ao RDS real

### Uploads
- novos uploads de avatar/logo passam a ser servidos corretamente por `/static`

## Estado Estavel Apos a Recuperacao

### Aplicacao
- frontend funcional
- backend funcional
- inference funcional
- imagens do S3 aparecendo
- avatar/logo aparecendo

### Banco
- schema `vale_vision` restaurado
- tabelas validadas
- dados minimos validados:
  - `users = 4`
  - `events = 25`

### Operacao
- deploy de aplicacao deve acontecer via GitHub Actions
- Terraform nao deve rodar em toda mudanca de codigo

## Modelo Operacional Recomendado

### O que deve acontecer em um push comum
- build do frontend
- copia do frontend para `backend/app/web`
- build da nova imagem do backend
- push da imagem no ECR
- rollout automatico do ECS

### O que nao deve acontecer em um push comum
- `terraform apply`
- alteracao de RDS
- mudanca de secrets criticos
- mudanca estrutural de IAM sem revisao

### Quando Terraform deve rodar
Somente quando houver mudanca real de infraestrutura, por exemplo:
- novo bucket
- mudanca de ALB
- novo secret
- alteracao de ECS service/module
- mudanca em RDS

E mesmo assim:
- por disparo manual
- com revisao de plan
- com janela consciente de operacao

## Aprendizados
1. Nem todo problema de app deve ser corrigido com `terraform apply`.
2. Em plataforma ainda em consolidacao, misturar S3, ECS, IAM, secrets e banco na mesma janela aumenta muito o risco.
3. `health check 200` nao significa que o login ou o banco estao realmente saudaveis.
4. RDS privado deve ser validado via bastion, ECS ou DBeaver com acesso na VPC, nao pela maquina local.
5. O HDI parece mais "simples" porque sua operacao ja esta madura; o Vision ainda estava consolidando a camada de runtime e dados.
6. Deploy de app e mudanca de infra devem ser tratados como fluxos diferentes.

## Acoes Permanentes
- manter `terraform.yml` manual
- manter `deploy.yml` automatico apenas para aplicacao
- nao reexecutar Terraform em producao sem necessidade real
- preservar dump e bastion como mecanismos de contingencia
- validar qualquer mudanca de banco com checklist operacional previo

## Checklist Antes de Novas Mudancas
- a mudanca e so de frontend/backend/inference?
  - se sim, usar apenas `deploy.yml`
- ha necessidade real de Terraform?
  - se nao, nao rodar
- a mudanca toca banco, secrets ou IAM?
  - se sim, revisar o plano com cuidado
- o RDS precisa ser validado?
  - usar bastion, nao a maquina local

## Conclusao
O incidente mostrou que o maior risco nao estava no GitHub Actions em si, mas em usar a mesma trilha para corrigir problema de aplicacao e alterar infraestrutura sensivel ao mesmo tempo.

Com a recuperacao concluida, a plataforma voltou a um estado operacional estavel. O caminho recomendado daqui para frente e:
- deploy automatico de app
- Terraform manual
- mudancas pequenas e isoladas
- banco tratado como componente critico, com validacao e rollback claros
