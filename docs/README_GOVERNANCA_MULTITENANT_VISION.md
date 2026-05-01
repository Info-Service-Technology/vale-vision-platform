# Governanca Multi-Tenant, Billing e Administracao

## Visao geral

Este documento consolida a evolucao aplicada ao `sansx-vision-platform` para transformar o projeto em uma plataforma de monitoramento multi-tenant, inspirada na arquitetura do HDI, mas adaptada para um produto generico de monitoramento.

O principio adotado foi:

- nao amarrar a plataforma a uma mineradora especifica;
- tratar `cacambas` como um caso de uso atual;
- manter a base reutilizavel para outros nichos de monitoramento, como transito, agronegocio, seguranca ou operacoes industriais;
- reaproveitar do HDI principalmente a governanca de tenant, billing, aprovacoes, auditoria e administracao global.

## Base conceitual herdada do HDI

As referencias principais reaproveitadas do HDI foram:

- descoberta e governanca de tenant por configuracao explicita;
- separacao entre tenant, dominios do tenant e billing;
- fluxo de aprovacao de usuarios;
- papel global de `super-admin`;
- auditoria administrativa;
- UX de billing e governanca operacional.

No `sansx-vision-platform`, essa linha foi adaptada para:

- `super-admin` SensX com visao global;
- `admin-tenant` restrito ao proprio tenant;
- usuarios `operator` e `viewer`;
- plataforma de monitoramento multi-nicho, nao presa a saude.

## O que foi criado

### 1. Autenticacao, sessao e conta

#### Backend

- `backend/app/api/routes/auth.py`
  - login por JWT
  - registro de usuario vinculado a tenant
  - bloqueio de login para usuario pendente ou inativo
  - troca e reset de senha em nivel de base logica
- `backend/app/api/routes/account.py`
  - `GET /api/account/me`
  - `PUT /api/account/me`
  - `POST /api/account/avatar`

#### Frontend

- `frontend/src/context/AuthContext.tsx`
  - sessao centralizada
  - estado do usuario
  - estado do tenant
  - leitura do status de billing do tenant
- `frontend/src/pages/LoginPage.tsx`
  - modo `Usuario Mineradora`
  - modo `Usuario SensX`
- `frontend/src/pages/RegisterPage.tsx`
- `frontend/src/pages/ForgotPasswordPage.tsx`
- `frontend/src/pages/ResetPasswordPage.tsx`

#### E-mail transacional

- `backend/app/services/email.py`
  - notificacao de cadastro pendente
  - notificacao para aprovadores
  - notificacao de aprovacao ou rejeicao
  - envio de reset de senha por SMTP

Documentacao complementar:

- `docs/EMAIL_AUTENTICACAO_VISION.md`

### 2. Perfis e papeis

Papeis atualmente suportados:

- `super-admin`
- `admin-tenant`
- `operator`
- `viewer`

Regras atuais:

- `super-admin`
  - visao global da plataforma
  - gerencia tenants, billing e usuarios de qualquer tenant
  - pode operar mesmo quando o tenant esta com restricao de billing
- `admin-tenant`
  - gerencia usuarios do proprio tenant
  - sem acesso administrativo global
  - sujeito a restricao operacional por billing
- `operator`
  - perfil operacional
  - sujeito a restricao operacional por billing
- `viewer`
  - acesso de consulta
  - nao resolve monitoramentos manualmente

### 3. Aprovacao de usuarios

#### Banco

Na tabela `users` foram adicionados:

- `approval_status`
- `is_active`

#### Backend

- `backend/app/api/routes/admin_users.py`
  - listagem de usuarios
  - criacao de usuarios
  - edicao de usuarios
  - exclusao de usuarios
  - listagem de pendentes
  - aprovacao e rejeicao

#### Frontend

- `frontend/src/pages/AdminUsersPage.tsx`
  - gestao de usuarios
  - aprovacao de pendentes
  - filtros basicos

### 4. Tenant atual e plataforma multi-tenant

#### Conceito

O projeto deixou de estar conceitualmente preso a uma organizacao unica.

Tenant passou a representar:

- uma mineradora;
- uma operacao;
- um cliente;
- ou qualquer organizacao que consuma a plataforma de monitoramento.

#### Backend

- `backend/app/api/routes/tenants.py`
  - `GET /api/tenants/current`
  - `GET /api/tenants`
  - `POST /api/tenants/current/logo`

#### Frontend

- tenant mantido em sessao no `AuthContext`
- logo do tenant refletido em:
  - `frontend/src/components/Sidebar.tsx`
  - `frontend/src/pages/SystemPage.tsx`

### 5. Billing por tenant

#### Banco

Na tabela `tenants` foram adicionados:

- `billing_status`
- `billing_due_date`
- `billing_grace_until`
- `billing_suspended_at`
- `billing_contact_email`
- `billing_notes`
- `payment_method`
- `contract_type`
- `billing_amount`
- `billing_currency`
- `billing_cycle`
- `plan_slug`
- `is_active`

#### Backend

- `backend/app/api/routes/billing.py`
  - `GET /api/billing/current`
  - `GET /api/billing/tenants`
  - `PUT /api/admin/billing/tenants/{tenant_id}`

#### Frontend

- `frontend/src/pages/BillingPage.tsx`
  - visao de billing por tenant
  - edicao de billing para `super-admin`
  - visao restrita para perfis nao globais

### 6. Restricao operacional por billing

Foi criada uma politica reutilizavel de acesso:

- `backend/app/services/billing_access.py`

Estados considerados restritivos:

- `suspended_read_only`
- `suspended_full`
- `terminated`

Aplicacao atual:

- backend bloqueia escrita operacional e administrativa de tenant restrito em:
  - `backend/app/api/routes/events.py`
  - `backend/app/api/routes/admin_users.py`
  - `backend/app/api/routes/tenants.py` para alteracao de logo
- frontend reflete isso em:
  - `frontend/src/utils/billing.ts`
  - `frontend/src/context/AuthContext.tsx`
  - `frontend/src/components/BillingStatusBanner.tsx`

Efeitos visiveis:

- tenant pode ficar em modo acompanhamento/leitura;
- resolucao manual de monitoramentos pode ser bloqueada;
- admins de tenant podem perder escrita sem perder a visao.

### 7. Auditoria administrativa

#### Banco

Foi criada a tabela:

- `audit_logs`

#### Backend

- `backend/app/services/audit.py`
- `backend/app/api/routes/admin_audit.py`

Eventos auditados atualmente incluem:

- criacao de usuario
- edicao de usuario
- exclusao de usuario
- aprovacao de usuario
- rejeicao de usuario
- upload de avatar
- upload de logo
- atualizacao de perfil
- resolucao manual de monitoramento
- alteracao de billing
- criacao e exclusao de dominio de tenant
- criacao e edicao de tenant

#### Frontend

- `frontend/src/pages/AdminAuditPage.tsx`

### 8. Perfil do usuario e branding

#### Banco

Na tabela `users` foram adicionados:

- `avatar_url`
- `phone`
- `about`

Na tabela `tenants` foi adicionada:

- `company_logo_url`

#### Backend

- avatar do usuario:
  - `POST /api/account/avatar`
- perfil do usuario:
  - `PUT /api/account/me`
- logo do tenant:
  - `POST /api/tenants/current/logo`

#### Frontend

- `frontend/src/pages/ProfilePage.tsx`
- `frontend/src/pages/SystemPage.tsx`
- `frontend/src/components/Header.tsx`
- `frontend/src/components/Sidebar.tsx`

Regra de upload:

- imagens com no maximo `5 MB`

### 9. Ajuda e sistema

#### Frontend

- `frontend/src/pages/HelpPage.tsx`
- `frontend/src/pages/SystemPage.tsx`

Essas paginas foram adaptadas para a linguagem de:

- plataforma de monitoramento;
- governanca multi-tenant;
- operacao generica;
- sem dependencia do dominio de saude do HDI.

### 10. Traducoes e i18n

Foi trazida a base de traducoes do HDI e aplicada ao frontend:

- `frontend/src/i18n/locales/*.json`
- `frontend/src/i18n/translations.ts`
- `frontend/src/context/LocaleContext.tsx`

Foi mantido um overlay com textos especificos do Vision Platform, especialmente para:

- login SensX x tenant
- monitoramento generico
- billing
- perfil
- sistema

### 11. Modal de imagem e UX operacional

Foi alinhado o padrao visual entre telas operacionais:

- `frontend/src/components/ImageModal.tsx`
- `frontend/src/pages/CacambasPage.tsx`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/features/events/EventsTable.tsx`
- `frontend/src/pages/AuditPage.tsx`

## Governanca de tenants no estilo HDI

### 12. Cadastro formal de tenants

#### Backend

- `backend/app/api/routes/admin_tenants.py`
  - `GET /api/admin/tenants`
  - `POST /api/admin/tenants`
  - `PUT /api/admin/tenants/{tenant_id}`

#### Frontend

- `frontend/src/pages/AdminTenantsPage.tsx`
- rota:
  - `/admin/tenants`

Capacidades atuais:

- criar tenant
- editar tenant
- definir nome
- definir slug
- definir escopo
- definir contato financeiro
- definir plano
- ativar ou desativar tenant

### 13. Dominios autorizados do tenant

#### Banco

Foi criada a tabela:

- `tenant_domains`

Campos:

- `tenant_id`
- `domain`
- `is_verified`
- `is_primary`
- `is_active`
- `match_mode`

#### Backend

Em `backend/app/api/routes/admin_tenants.py`:

- `GET /api/admin/tenants/{tenant_id}/domains`
- `POST /api/admin/tenants/{tenant_id}/domains`
- `DELETE /api/admin/tenants/domains/{domain_id}`

#### Frontend

Em `frontend/src/pages/AdminTenantsPage.tsx`:

- listagem de dominios
- criacao de dominio
- remocao de dominio

Objetivo arquitetural:

- preparar descoberta segura de tenant por dominio
- evitar fallback inseguro
- seguir o principio do HDI de configuracao explicita

### 14. Historico de billing por tenant

#### Banco

Foi criada a tabela:

- `billing_events`

Campos:

- `tenant_id`
- `event_type`
- `previous_status`
- `next_status`
- `message`
- `actor_user_id`
- `created_at`

#### Backend

Em `backend/app/api/routes/admin_tenants.py`:

- `GET /api/admin/tenants/{tenant_id}/billing-events`

Em `backend/app/api/routes/billing.py`:

- alteracoes de billing passam a registrar evento historico

#### Frontend

Em `frontend/src/pages/AdminTenantsPage.tsx`:

- listagem do historico de billing do tenant selecionado

## Estrutura de paginas principais

### Publicas

- `/login`
- `/register`
- `/forgot-password`
- `/reset-password`

### Operacionais autenticadas

- `/dashboard`
- `/cacambas`
- `/audit`
- `/perfil`
- `/sistema`
- `/ajuda`
- `/billing`

### Administrativas

- `/admin/users`
- `/admin/audit`
- `/admin/tenants`

## Tabelas e alteracoes de banco aplicadas

### `users`

Campos adicionados:

- `approval_status`
- `is_active`
- `avatar_url`
- `phone`
- `about`

### `tenants`

Campos adicionados:

- `company_logo_url`
- `billing_status`
- `billing_due_date`
- `billing_grace_until`
- `billing_suspended_at`
- `billing_contact_email`
- `billing_notes`
- `payment_method`
- `contract_type`
- `billing_amount`
- `billing_currency`
- `billing_cycle`
- `plan_slug`
- `is_active`

### Novas tabelas

- `audit_logs`
- `tenant_domains`
- `billing_events`

## O que ainda nao esta completo

Itens preparados, mas ainda nao totalmente finalizados:

- envio real de e-mail por SMTP Google
- aprovacao por e-mail automatica
- reset de senha com entrega real de e-mail
- descoberta automatica de tenant por dominio no cadastro/login
- onboarding completo do primeiro `tenant-admin`
- tela de billing com automacao financeira externa
- persistencia de configuracoes globais de sistema no backend
- otimização de bundle do frontend

## Estado atual recomendado

O sistema ja possui base para:

- multi-tenant real
- governanca de usuarios
- billing por tenant
- restricao operacional por billing
- auditoria administrativa
- branding por usuario e tenant
- administracao global pela SensX

Na pratica, a fundacao principal do modelo HDI ja foi transplantada para o Vision Platform, mas ainda faltam os fluxos mais automatizados de onboarding, descoberta por dominio e notificacao por e-mail.

## Proximos passos recomendados

1. Implementar descoberta de tenant por `tenant_domains` no login e no registro.
2. Bloquear cadastro publico quando o dominio nao corresponder a um tenant autorizado.
3. Criar fluxo de onboarding para o primeiro `tenant-admin`.
4. Integrar SMTP real para aprovacao, reset de senha e notificacoes.
5. Evoluir billing para contratos, assinaturas e historico mais rico.

## Documentos relacionados

- `ARCHITECTURE.md`
- `README_GOVERNANCA_MULTITENANT_VISION.md`
- `GUIA_OPERACIONAL_SUPER_ADMIN_SENSX.md`
