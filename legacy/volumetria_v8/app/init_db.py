import sqlite3
from pathlib import Path

BASE_DIR = Path(r"E:\PROJETO VALE\PACOTE_PILOTO_VM\PRODUTO_VOLUMETRIA_RELEASE_V8")
DB_PATH = BASE_DIR / "data" / "eventos.db"

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_processamento TEXT NOT NULL,
    data_ref TEXT,
    hora_ref TEXT,

    arquivo_nome TEXT NOT NULL,
    arquivo_path TEXT NOT NULL,
    arquivo_hash TEXT,
    grupo TEXT NOT NULL,

    status TEXT,
    fill_percent REAL,
    estado_dashboard TEXT,
    ok_consec INTEGER,
    alerta INTEGER,

    materiais_detectados_raw TEXT,
    contaminantes_detectados TEXT,
    alerta_contaminacao INTEGER,

    motivo_falha TEXT,

    modelo_volumetria_versao TEXT,
    modelo_contaminantes_versao TEXT,

    evidencia_path TEXT,
    debug_path TEXT,

    origem TEXT DEFAULT 'ftp',
    processado_com_sucesso INTEGER DEFAULT 0,

    criado_em TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_eventos_arquivo_path
ON eventos(arquivo_path);

CREATE INDEX IF NOT EXISTS idx_eventos_ts
ON eventos(ts_processamento);

CREATE INDEX IF NOT EXISTS idx_eventos_grupo
ON eventos(grupo);

CREATE INDEX IF NOT EXISTS idx_eventos_status
ON eventos(status);

CREATE INDEX IF NOT EXISTS idx_eventos_estado_dashboard
ON eventos(estado_dashboard);

CREATE INDEX IF NOT EXISTS idx_eventos_alerta_contaminacao
ON eventos(alerta_contaminacao);

CREATE TABLE IF NOT EXISTS execucoes_servico (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_inicio TEXT NOT NULL,
    ts_fim TEXT,
    status TEXT,
    mensagem TEXT
);

CREATE TABLE IF NOT EXISTS arquivos_ignorados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_registro TEXT NOT NULL,
    arquivo_nome TEXT NOT NULL,
    arquivo_path TEXT NOT NULL,
    grupo TEXT,
    motivo TEXT
);
"""

def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA)
        conn.commit()

    print(f"[OK] Banco criado/validado em: {DB_PATH}")

if __name__ == "__main__":
    main()
