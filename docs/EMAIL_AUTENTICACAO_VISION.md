# E-mail de Aprovacao e Reset de Senha

## Estado atual
O `sansx-vision-platform` agora tem a camada de envio de e-mail preparada no backend, com suporte a SMTP e comportamento de fallback em desenvolvimento.

Arquivo principal:
- [`backend/app/services/email.py`](/home/mauroslucios/workspace/python/vale-vision-platform/backend/app/services/email.py)

## Fluxos cobertos

### Cadastro publico
Quando um usuario se registra:
- a conta nasce com `approval_status = pending`
- o proprio usuario recebe um e-mail informando que o cadastro esta aguardando aprovacao
- os aprovadores recebem um e-mail avisando que existe um novo usuario pendente

Aprovadores notificados:
- todos os `super-admin`
- todos os `admin-tenant` do tenant do usuario
- `email_support_address`, se configurado e nao houver aprovadores encontrados

### Aprovacao de usuario
Quando o admin aprova um usuario:
- o usuario recebe um e-mail informando que a conta foi aprovada

### Rejeicao de usuario
Quando o admin rejeita um usuario:
- o usuario recebe um e-mail informando que o cadastro nao foi aprovado

### Recuperacao de senha
Quando o usuario solicita reset:
- o sistema gera um token de reset
- o sistema envia um link para `frontend_public_url/reset-password?token=...`

## Configuracao

Variaveis novas no backend:
- `FRONTEND_PUBLIC_URL`
- `API_PUBLIC_URL`
- `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES`
- `EMAIL_ENABLED`
- `EMAIL_FROM_NAME`
- `EMAIL_FROM_ADDRESS`
- `EMAIL_REPLY_TO`
- `EMAIL_SUPPORT_ADDRESS`
- `EMAIL_DEBUG_RETURN_TOKENS`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_USE_STARTTLS`
- `SMTP_USE_SSL`
- `SMTP_TIMEOUT_SECONDS`

## Comportamento em desenvolvimento
Se `EMAIL_ENABLED=false`, o backend nao quebra os fluxos.

No `forgot-password`, se o e-mail estiver desabilitado e `EMAIL_DEBUG_RETURN_TOKENS=true`, a API devolve:
- `reset_token`
- `reset_url`

Isso ajuda a testar o fluxo antes de configurar SMTP ou SES.

## Exemplo com Gmail SMTP

```env
EMAIL_ENABLED=true
EMAIL_FROM_NAME=SensX Vision Platform
EMAIL_FROM_ADDRESS=admin@sensx.com
EMAIL_REPLY_TO=admin@sensx.com
EMAIL_SUPPORT_ADDRESS=admin@sensx.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=admin@sensx.com
SMTP_PASSWORD=SUA_APP_PASSWORD
SMTP_USE_STARTTLS=true
SMTP_USE_SSL=false
FRONTEND_PUBLIC_URL=https://sensxvisionplatform.com
API_PUBLIC_URL=https://api.sensxvisionplatform.com
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES=60
```

Observacao importante:
- para Gmail, o recomendado e usar `App Password`, nao a senha normal da conta

## Passo a passo para testar com Gmail

1. No Google, habilite `2-Step Verification` para a conta remetente.
2. Gere uma `App Password` para `Mail`.
3. No arquivo [`backend/.env.example`](/home/mauroslucios/workspace/python/vale-vision-platform/backend/.env.example), copie as variaveis para o seu `backend/.env`.
4. Ajuste:
   - `EMAIL_ENABLED=true`
   - `SMTP_USERNAME=admin@sensx.com`
   - `SMTP_PASSWORD=<APP_PASSWORD_DO_GOOGLE>`
   - `EMAIL_FROM_ADDRESS=admin@sensx.com`
   - `FRONTEND_PUBLIC_URL=http://localhost:5174` em dev ou `https://sensxvisionplatform.com` em producao
5. Reinicie o backend.
6. Teste o fluxo:
   - cadastro publico para validar e-mail de aprovacao
   - aprovacao de usuario para validar e-mail de conta aprovada
   - `Esqueci minha senha` para validar o reset

## Comportamento esperado em dev
- com `EMAIL_ENABLED=true`, o backend tenta enviar e-mail real
- com `EMAIL_ENABLED=false`, o backend nao envia e, no reset, pode retornar `reset_token` e `reset_url`

## Recomendacao para producao
- curto prazo: SMTP do Google ou provedor corporativo
- medio prazo: migrar para `Amazon SES`
- publicar `SPF`, `DKIM` e `DMARC`
- usar remetente do dominio oficial da plataforma
