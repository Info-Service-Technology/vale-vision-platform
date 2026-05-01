# Guia Operacional do Super-Admin SensX

## Objetivo

Este guia resume como o `super-admin` da SensX deve operar a plataforma no dia a dia.

O foco aqui nao e arquitetura tecnica. O foco e operacao:

- como entrar;
- como criar e ajustar tenants;
- como aprovar usuarios;
- como agir sobre billing;
- como acompanhar auditoria;
- como entender bloqueios operacionais.

## Quem e o super-admin

O `super-admin` e o perfil global da SensX.

Esse perfil pode:

- acessar qualquer tenant;
- aprovar usuarios de qualquer tenant;
- gerenciar usuarios de qualquer tenant;
- editar billing de qualquer tenant;
- criar e editar tenants;
- cadastrar dominios permitidos de tenant;
- consultar auditoria administrativa global;
- operar mesmo quando um tenant esta com restricao de billing.

## Como entrar

Na tela de login:

1. selecione `Usuario SensX`;
2. informe o e-mail SensX;
3. informe a senha;
4. entre sem precisar selecionar mineradora/tenant.

Observacao:

- usuarios SensX com perfil global nao dependem do tenant do cliente para entrar;
- hoje o usuario de teste principal esta configurado como `admin@sensx.com`.

## Menu principal do super-admin

O `super-admin` possui acesso aos modulos:

- `Painel`
- `Caçambas`
- `Billing`
- `Perfil`
- `Sistema`
- `Ajuda`
- `Administracao de usuarios`
- `Tenants`
- `Auditoria`

## Fluxo recomendado de onboarding de novo cliente

Quando uma nova organizacao for entrar na plataforma, o fluxo recomendado e:

1. criar o tenant
2. cadastrar os dominios autorizados do tenant
3. criar o primeiro `admin-tenant`
4. revisar billing inicial
5. liberar operacao

## Como criar um tenant

Pagina:

- `/admin/tenants`

Passos:

1. clique em `Novo tenant`
2. preencha:
   - nome
   - slug
   - tipo de escopo
   - valor do escopo
   - contato financeiro
   - plano
   - status ativo/inativo
3. salve

Boas praticas:

- use `slug` curto, estavel e sem espacos;
- pense no tenant como organizacao cliente, nao como tela ou modulo;
- use `scope_type` e `scope_value` de forma generica, sem prender o sistema a um nicho.

## Como cadastrar dominios do tenant

Pagina:

- `/admin/tenants`

Bloco:

- `Dominios do tenant`

Passos:

1. selecione o tenant
2. clique em `Novo dominio`
3. informe o dominio
4. escolha o `match_mode`
5. defina se e primario
6. salve

Uso esperado:

- isso prepara descoberta automatica de tenant por dominio;
- evita fallback inseguro;
- permite onboarding mais confiavel.

### Quando usar `exact`

Use `exact` quando:

- apenas um dominio institucional especifico deve ser aceito

Exemplo:

- `mineradora.com.br`

### Quando usar `suffix`

Use `suffix` quando:

- subdominios controlados tambem devem ser aceitos

Exemplo:

- `operacao.mineradora.com.br`
- `unidade1.mineradora.com.br`

## Como criar o primeiro admin do tenant

Pagina:

- `/admin/users`

Passos:

1. clique em `Adicionar Novo Usuario`
2. informe nome, e-mail e senha inicial
3. escolha o papel `admin-tenant`
4. vincule ao tenant correto
5. salve

Esse usuario sera o administrador local do cliente.

## Como aprovar usuarios pendentes

Pagina:

- `/admin/users`

Bloco:

- `Usuarios Pendentes`

O `super-admin` pode:

- aprovar usuario
- rejeitar usuario

Regras atuais:

- o `super-admin` pode aprovar usuarios SensX;
- o `super-admin` pode aprovar usuarios de qualquer tenant;
- `admin-tenant` aprova apenas usuarios do proprio tenant.

## Como operar billing

Pagina:

- `/billing`

O `super-admin` consegue:

- selecionar qualquer tenant
- visualizar status financeiro
- editar status financeiro
- ajustar vencimento
- ajustar tolerancia
- ajustar suspensao
- informar contato financeiro
- informar observacoes
- definir plano
- registrar alteracoes no historico

## Significado dos status de billing

### `active`

- tenant operando normalmente

### `past_due`

- existe debito em aberto
- operacao continua normal
- tenant deve regularizar

### `grace_period`

- tenant em tolerancia
- ainda sem bloqueio operacional total

### `suspended_read_only`

- tenant entra em modo leitura
- consulta continua disponivel
- acoes sensiveis de escrita ficam bloqueadas para perfis nao globais

### `suspended_full`

- tenant suspenso operacionalmente
- operacao fica fortemente restringida

### `terminated`

- tenant encerrado
- qualquer retomada depende de nova validacao operacional/financeira

## Efeito pratico do billing sobre a operacao

Quando um tenant entra em restricao:

- `viewer` continua como consulta
- `operator` pode perder acoes de escrita
- `admin-tenant` pode perder gestao operacional e administrativa local
- `super-admin` SensX continua com override operacional

Exemplos de impacto:

- resolver monitoramento manualmente pode ficar bloqueado;
- administrar usuarios pode ficar bloqueado para o tenant;
- alteracoes sensiveis locais podem ser interrompidas;
- banners de status passam a aparecer no frontend.

## Como acompanhar auditoria

Pagina:

- `/admin/audit`

Ali o `super-admin` pode revisar:

- quem criou usuario
- quem aprovou usuario
- quem rejeitou usuario
- quem alterou billing
- quem alterou tenant
- quem subiu logo
- quem atualizou perfil
- quem executou acoes administrativas

Use essa pagina para:

- investigar problemas
- validar trilha de governanca
- apoiar suporte
- revisar operacao multi-tenant

## Como usar a pagina de tenants no dia a dia

Pagina:

- `/admin/tenants`

Uso recomendado:

1. selecione o tenant
2. revise status e plano
3. revise dominios autorizados
4. revise historico de billing
5. ajuste tenant quando necessario

Essa pagina e a base da governanca global no estilo HDI.

## Sistema e branding

Pagina:

- `/sistema`

Uso esperado:

- ajustar logo da empresa
- ajustar configuracoes globais
- revisar idioma padrao

Observacao:

- nem toda configuracao global ja esta persistida no backend;
- parte da experiencia ainda usa persistencia local no navegador.

## Perfil

Pagina:

- `/perfil`

O `super-admin` pode:

- alterar nome
- alterar telefone
- alterar campo `sobre`
- subir avatar

Limite atual:

- imagem de ate `5 MB`

## O que ja esta pronto

O `super-admin` ja possui base funcional para:

- login global SensX
- gestao de usuarios
- aprovacao de usuarios
- billing por tenant
- banners e restricoes por billing
- auditoria administrativa
- perfil e avatar
- sistema e logo
- governanca de tenants
- governanca de dominios
- historico de billing

## O que ainda esta pendente

Itens ainda nao finalizados:

- descoberta automatica de tenant por dominio no login e no cadastro
- notificacao real por e-mail
- onboarding guiado do primeiro `admin-tenant`
- automacao financeira externa
- configuracoes globais 100% persistidas no backend

## Checklist recomendado para um novo tenant

1. criar tenant
2. cadastrar dominio principal
3. cadastrar dominios secundarios, se houver
4. definir plano inicial
5. revisar contato financeiro
6. criar primeiro `admin-tenant`
7. validar login do tenant
8. validar permissao do tenant
9. revisar billing inicial
10. acompanhar primeiros usuarios pendentes

## Checklist recomendado para suporte

Quando um cliente relatar problema de acesso:

1. verificar se o usuario esta aprovado
2. verificar se o usuario esta ativo
3. verificar tenant vinculado
4. verificar status de billing do tenant
5. verificar auditoria administrativa
6. verificar se o tenant esta ativo
7. verificar dominios configurados, quando esse fluxo estiver automatizado
