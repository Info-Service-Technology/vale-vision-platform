# Inference Service

Serviço responsável pelo pipeline de visão computacional e regras de contaminação.

## FTP watcher

O watcher FTP detecta imagens novas enviadas pelas câmeras via FTP e faz upload para o S3 em `raw/`.

### Como usar

- `python ftp_watcher.py --once` — executa um ciclo único.
- `python ftp_watcher.py` — executa em loop contínuo.

### HTTP endpoint de sync

- `POST /ftp/sync` — dispara um ciclo de sincronização FTP uma vez.
- `GET /health` — health check do serviço de inferência.
- `POST /process-s3` — processa manualmente uma imagem existente no S3, recebendo `bucket` e `key` no corpo JSON.

Quando o container roda com `run_service.py`, o worker SQS é iniciado em background e a API fica disponível para trigger manual.

### Teste local recomendado

1. copie ou configure `inference/.env` com as variáveis necessárias:
   - `FTP_HOST`
   - `FTP_USER`
   - `FTP_PASSWORD`
   - `S3_BUCKET`
   - `S3_PREFIX_RAW`
   - `AWS_REGION`
2. execute o serviço de inferência:
   - `cd inference`
   - `python run_service.py`
3. verifique o service health:
   - `curl http://localhost:8001/health`
4. dispare o sync FTP manualmente:
   - `curl -X POST http://localhost:8001/ftp/sync`
5. se preferir testar pelo backend proxy:
   - `curl -X POST http://localhost:8000/api/inference/ftp/sync`
   - `curl http://localhost:8000/api/inference/ftp/health`

### Teste com docker-compose

Se estiver usando `docker-compose`, a configuração atual expõe o serviço de inferência em `localhost:8001`.

1. `docker-compose up backend inference`
2. `curl http://localhost:8001/health`
3. `curl -X POST http://localhost:8001/ftp/sync`
4. `curl -X POST http://localhost:8000/api/inference/ftp/sync`

### Variáveis de ambiente

- `FTP_HOST` — host FTP.
- `FTP_PORT` — porta FTP (padrão `21`).
- `FTP_USER` — usuário FTP.
- `FTP_PASSWORD` — senha FTP.
- `FTP_BASE_DIR` — diretório base no FTP (padrão `/upload`).
- `FTP_CAMERA_DIRS` — lista de pastas de câmeras, separada por vírgula.
- `FTP_POLL_INTERVAL_SECONDS` — intervalo de varredura em segundos (padrão `60`).
- `FTP_DOWNLOAD_DIR` — diretório local temporário para downloads (padrão `/tmp/ftp_download`).
- `FTP_STATE_FILE` — arquivo local de estado para evitar reprocessamento.
- `FTP_MOVE_PROCESSED` — se `true`, tenta mover o arquivo remoto para `processed/` após upload.
- `FTP_PROCESSED_SUBDIR` — nome do subdiretório remoto usado para arquivos processados.
- `S3_BUCKET` — bucket S3 de destino.
- `S3_PREFIX_RAW` — prefixo S3 raw (padrão `raw/`).
- `TENANT` — tenant atual, usado para separar clientes como `tenant=vale`.
- `AWS_REGION` — região AWS.
