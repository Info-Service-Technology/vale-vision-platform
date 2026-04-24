# README_FRONTEND

## Objetivo

O frontend do Vale Vision é a interface operacional e corporativa do sistema.

Ele substitui o dashboard legado em Streamlit por uma aplicação moderna em:

- React
- Vite
- Material UI

## Responsabilidades

O frontend deve:

- exibir KPIs operacionais;
- mostrar o status atual por caçamba;
- listar eventos;
- permitir filtros por data, status, grupo e contaminação;
- exibir detalhe de evento com imagem e debug;
- servir como base para autenticação e perfis.

## Stack

- React
- Vite
- Material UI
- React Router
- Axios ou React Query

## Porta de desenvolvimento

A porta de desenvolvimento foi movida para `5174` para evitar conflito com o HDI.

Exemplo de configuração no `vite.config.ts`:

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5174,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://backend:8000",
        changeOrigin: true
      }
    }
  }
});
```

## Estrutura sugerida

```text
frontend/
├── src/
│   ├── app/
│   ├── pages/
│   ├── components/
│   ├── services/
│   ├── hooks/
│   ├── theme/
│   └── router/
├── public/
├── package.json
├── vite.config.ts
└── Dockerfile
```

## Páginas recomendadas

### Dashboard
- cards de resumo
- status por caçamba
- alertas de contaminação
- indicadores de volumetria

### Eventos
- tabela operacional
- filtros
- paginação
- exportação futura

### Detalhe do evento
- imagem original
- imagem debug
- materiais detectados
- contaminantes detectados
- status e severidade

### Administração
- usuários
- tenants/unidades
- câmeras
- caçambas

## Integração com backend

Principais endpoints esperados:

- `POST /api/auth/login`
- `GET /api/events`
- `POST /api/events`
- `GET /api/events/{id}`
- `GET /api/containers`
- `GET /api/cameras`

## Boas práticas

- usar componentes desacoplados;
- separar `services/` da camada visual;
- manter tema centralizado;
- não embutir URLs da API em múltiplos lugares;
- usar proxy do Vite no dev;
- tratar estados de loading/error explicitamente.

## Build

```bash
npm install
npm run dev
```

ou via Docker:

```bash
docker compose up --build frontend
```

## Produção

Em produção, o frontend pode ser servido por:

- container em ECS/Fargate atrás de ALB; ou
- build estático em S3 + CloudFront.

Para a fase inicial compartilhando ALB e mantendo simplicidade operacional, container em ECS é aceitável.
