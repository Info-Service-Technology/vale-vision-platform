# README_BACKEND

## Objetivo

O backend do Vale Vision é a camada transacional e de serviço da plataforma.

Ele substitui o fluxo de leitura direta de SQLite pelo frontend e passa a centralizar:

- autenticação;
- autorização;
- regras de acesso;
- leitura e gravação de eventos;
- integração com banco relacional;
- APIs para frontend e pipeline.

## Stack

- FastAPI
- SQLAlchemy
- MySQL
- JWT
- Pydantic

## Responsabilidades

- expor APIs REST;
- persistir eventos de inferência;
- armazenar tenants, usuários, câmeras e caçambas;
- aplicar regras de escopo;
- preparar base para auditoria e histórico.

## Estrutura sugerida

```text
backend/
├── app/
│   ├── api/
│   │   └── routes/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   └── main.py
├── db/
│   └── schema.sql
├── requirements.txt
├── Dockerfile
└── .env.example
```

## Banco

O backend usa MySQL como banco principal.

Tabelas base esperadas:

- `tenants`
- `users`
- `user_tenants`
- `cameras`
- `containers`
- `events`

## Modelo central: events

Campos típicos:

- `data_ref`
- `hora_ref`
- `file_path`
- `debug_path`
- `status`
- `fill_percent`
- `materiais_detectados`
- `contaminantes_detectados`
- `alerta_contaminacao`
- `tipo_contaminacao`
- `cacamba_esperada`
- `material_esperado`

## Multi-tenant

A estrutura já deve nascer preparada para multi-tenant.

No contexto Vale Vision, isso pode ser usado para:

- planta;
- unidade;
- linha;
- área operacional.

Exemplo de uso:
- tenant A = unidade 1
- tenant B = unidade 2

## Autenticação

A recomendação é JWT com:
- login por e-mail/senha;
- claims de `user_id`, `role`, `tenant_id` ou lista de tenants;
- validade curta para access token.

## Integração com o pipeline

### Estado atual
O pipeline legado processa imagens, escreve CSV e depois sincroniza com SQLite.

### Estado alvo
O pipeline deve publicar os resultados diretamente na API.

Exemplo:

```python
requests.post(
    "http://backend:8000/api/events",
    json={
        "tenant_id": 1,
        "data_ref": "2026-04-20",
        "hora_ref": "22:00:00",
        "status": "ok",
        "alerta_contaminacao": 1,
        "tipo_contaminacao": "madeira",
        "cacamba_esperada": "sucata",
        "material_esperado": "sucata"
    }
)
```

## Proxy para o serviço de inferência

O backend expõe rotas que fazem proxy para o serviço de inferência local:

- `POST /api/inference/ftp/sync` — dispara um ciclo FTP no `inference`.
- `GET /api/inference/ftp/health` — verifica se o serviço de inferência está online.

As configurações do serviço de inferência devem estar em:

- `INFERENCE_SERVICE_SCHEME` (`http`)
- `INFERENCE_SERVICE_HOST` (`localhost` ou nome do host/container)
- `INFERENCE_SERVICE_PORT` (`8001`)

Se estiver usando `docker-compose`, defina `INFERENCE_SERVICE_HOST=inference` para que o backend resolva o serviço pelo nome do container.

## Variáveis de ambiente

Exemplo de `.env.example`:

```env
DATABASE_URL=mysql+pymysql://app:123456@mysql:3307/vale_vision
JWT_SECRET_KEY=change-me
JWT_ALGORITHM=HS256
APP_ENV=dev
```

## Docker

Exemplo simples de `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Boas práticas

- usar migrations;
- separar schemas/models/services;
- não deixar regras de domínio espalhadas em endpoints;
- usar Secrets Manager em produção;
- isolar credenciais de banco por ambiente;
- logs estruturados.

## Observações AWS

- RDS deve ficar em subnets privadas e com SG dedicado. citeturn940174search2turn940174search18
- Segredos devem ficar em AWS Secrets Manager, com rotação quando aplicável. citeturn940174search2turn940174search10turn940174search6
