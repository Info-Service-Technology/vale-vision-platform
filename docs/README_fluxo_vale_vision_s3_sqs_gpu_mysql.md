# Vale Vision — Fluxo S3 Raw → SQS → ECS GPU → MySQL → Dashboard

## 1. Objetivo

Consolidar o fluxo operacional do Vale Vision para detecção de contaminantes em caçambas.

O fluxo principal não deve depender de upload manual pelo dashboard. As câmeras detectam movimento, capturam imagens e um módulo de captura envia essas imagens para o S3 em `raw/`. A partir daí, o pipeline deve ser automático: S3 notifica SQS, o worker GPU processa a imagem, grava o resultado no MySQL e o dashboard exibe apenas os eventos que precisam de ação operacional.

---

## 2. Fluxo principal

```text
Câmera detecta movimento
→ captura várias imagens
→ módulo de captura faz upload para S3 raw/
→ S3 Event Notification envia evento para SQS
→ ECS GPU Worker consome a fila
→ baixa imagem do S3
→ IA detecta materiais/contaminantes
→ motor de contaminação aplica regras
→ grava evento no MySQL
→ dashboard exibe itens pendentes
→ operador resolve
→ backend marca resolved e registra histórico
→ item aparece em “Itens Resolvidos”
```

---

## 3. Componentes

| Camada | Componente | Responsabilidade |
|---|---|---|
| Captura | Câmera / módulo externo | Detectar movimento e enviar imagens |
| Armazenamento | Amazon S3 `raw/` | Armazenar imagens brutas |
| Mensageria | Amazon SQS | Desacoplar upload e processamento |
| Processamento | ECS GPU Worker | Rodar inferência da IA |
| IA | YOLO / segmentador | Detectar materiais visíveis |
| Regras | Motor de contaminação | Comparar material detectado com grupo esperado |
| Persistência | MySQL / RDS | Gravar eventos e status |
| API | Backend Flask | Servir eventos, resolver ocorrências e gerar URLs de imagem |
| UI | Dashboard React | Exibir pendências e itens resolvidos |

---

## 4. Prefixos S3

### Imagens brutas

```text
raw/tenant=vale/camera=cam01/year=YYYY/month=MM/day=DD/<arquivo>.jpg
```

### Imagens processadas/debug

```text
processed/tenant=vale/camera=cam01/year=YYYY/month=MM/day=DD/<arquivo>.jpg
debug/tenant=vale/camera=cam01/year=YYYY/month=MM/day=DD/<arquivo>.jpg
```

### Imagens resolvidas

```text
resolved/tenant=vale/camera=cam01/year=YYYY/month=MM/day=DD/<arquivo>.jpg
```

---

## 5. Mensagem SQS esperada

O worker aceita o formato simples:

```json
{
  "bucket": "vale-vision-artifacts-dev",
  "key": "raw/tenant=vale/camera=cam01/year=2026/month=04/day=25/imagem.jpg"
}
```

Também deve aceitar evento nativo do S3 via `Records`.

---

## 6. Tabela MySQL `events`

Campos centrais:

| Campo | Uso |
|---|---|
| `id` | Identificador do evento |
| `status` | Estado operacional |
| `file_path` | Nome do arquivo |
| `s3_bucket` | Bucket da imagem |
| `s3_key_raw` | Caminho raw no S3 |
| `s3_key_debug` | Caminho debug/processado |
| `grupo` | Grupo esperado: `madeira`, `sucata`, `plastico` |
| `materiais_detectados` | Materiais detectados pela IA |
| `contaminantes_detectados` | Materiais incompatíveis |
| `alerta_contaminacao` | `0` sem alerta, `1` com alerta |
| `tipo_contaminacao` | Tipo lógico da contaminação |
| `cacamba_esperada` | Grupo esperado |
| `material_esperado` | Material esperado |
| `processing_status` | Status técnico |
| `resolved_at` | Data/hora de resolução |
| `resolved_by` | Usuário que resolveu |
| `resolved_reason` | Motivo/observação |
| `resolved_s3_key` | Caminho da imagem em resolvidos |

---

## 7. Estados operacionais

### Sem contaminação

```text
status = processed
alerta_contaminacao = 0
tipo_contaminacao = sem_contaminacao
```

Não precisa aparecer no dashboard de pendências.

### Com contaminação

```text
status = contamination
alerta_contaminacao = 1
resolved_at = NULL
```

Deve aparecer no dashboard principal.

### Resolvido

```text
status = resolved
resolved_at IS NOT NULL
```

Deve aparecer em **Itens Resolvidos**.

---

## 8. Regras de contaminação

| Grupo esperado | Aceita | Contaminante se detectar |
|---|---|---|
| `madeira` | madeira | sucata, plastico |
| `sucata` | sucata | madeira, plastico |
| `plastico` | plastico | madeira, sucata |

Exemplo:

```json
{
  "grupo": "plastico",
  "materiais_detectados": ["plastico", "madeira"],
  "contaminantes_detectados": ["madeira"],
  "alerta_contaminacao": 1,
  "tipo_contaminacao": "madeira_em_plastico"
}
```

---

## 9. Backend necessário

Endpoints sugeridos:

```text
GET  /api/events/pending
GET  /api/events/resolved
POST /api/events/<id>/resolve
GET  /api/events/<id>/image-url
```

Opcional para teste/manual:

```text
POST /api/events/upload-image
```

O fluxo principal deve ser upload das câmeras para S3 `raw/` + S3 Event Notification para SQS.

---

## 10. Frontend necessário

Sidebar:

```text
Itens resolvidos
```

Dashboard principal:

```sql
WHERE status = 'contamination'
```

Página Itens Resolvidos:

```sql
WHERE status = 'resolved'
```

---

## 11. Ordem de implementação

1. Configurar S3 Event Notification para SQS.
2. Ajustar worker para ler `grupo` da mensagem/metadados quando disponível.
3. Implementar motor real de contaminação.
4. Integrar YOLO/segmentador real.
5. Gravar `status = contamination` quando `alerta_contaminacao = 1`.
6. Criar `POST /api/events/<id>/resolve`.
7. Criar página **Itens Resolvidos**.
8. Copiar/mover imagem para `resolved/`.
9. Criar política de limpeza/retentativa para mensagens inválidas.
10. Automatizar deploy por GitHub Actions/Terraform.

---

## 12. Situação validada

Já foi validado:

```text
SQS → ECS GPU Worker → S3 → processamento → MySQL → delete da mensagem SQS
```

Log validado:

```text
[processor] Resultado salvo
[worker] Mensagem processada e removida da fila.
```

A infraestrutura base está pronta. O próximo trabalho é transformar a lógica mockada em IA real e consolidar o ciclo `contamination → resolved`.
