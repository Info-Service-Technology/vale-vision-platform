import csv
import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(r"E:\PROJETO VALE\PACOTE_PILOTO_VM\PRODUTO_VOLUMETRIA_RELEASE_V8")
CSV_PATH = BASE_DIR / "output" / "csv" / "resultado_volumetria.csv"
DB_PATH = BASE_DIR / "data" / "eventos.db"
DEBUG_DIR = BASE_DIR / "output" / "debug"

MODELO_VOLUMETRIA_VERSAO = "release_v8"
MODELO_CONTAMINANTES_VERSAO = "best_materiais_v1_152imgs_gpu_s_1024"


def parse_int(v, default=0):
    try:
        if v in (None, ""):
            return default
        return int(float(v))
    except Exception:
        return default


def parse_float(v, default=None):
    try:
        if v in (None, ""):
            return default
        return float(v)
    except Exception:
        return default


def ensure_parent_dir(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def arquivo_hash_from_path(arquivo_path: str) -> str:
    return hashlib.sha1(arquivo_path.strip().lower().encode("utf-8")).hexdigest()


def ensure_schema(conn: sqlite3.Connection):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_processamento TEXT,
            data_ref TEXT,
            hora_ref TEXT,
            arquivo_nome TEXT,
            arquivo_path TEXT,
            arquivo_hash TEXT,
            grupo TEXT,
            status TEXT,
            fill_percent REAL,
            estado_dashboard TEXT,
            ok_consec INTEGER,
            alerta INTEGER,
            materiais_detectados_raw TEXT,
            contaminantes_detectados TEXT,
            alerta_contaminacao INTEGER,
            tipo_contaminacao TEXT,
            severidade_contaminacao INTEGER,
            motivo_falha TEXT,
            deteccoes_contaminantes_json TEXT,
            cacamba_esperada TEXT,
            material_esperado TEXT,
            modelo_volumetria_versao TEXT,
            modelo_contaminantes_versao TEXT,
            evidencia_path TEXT,
            debug_path TEXT,
            origem TEXT,
            processado_com_sucesso INTEGER,
            criado_em TEXT
        )
        """
    )

    existing_cols = {
        row[1]
        for row in conn.execute("PRAGMA table_info(eventos)").fetchall()
    }

    wanted_cols = {
        "ts_processamento": "TEXT",
        "data_ref": "TEXT",
        "hora_ref": "TEXT",
        "arquivo_nome": "TEXT",
        "arquivo_path": "TEXT",
        "arquivo_hash": "TEXT",
        "grupo": "TEXT",
        "status": "TEXT",
        "fill_percent": "REAL",
        "estado_dashboard": "TEXT",
        "ok_consec": "INTEGER",
        "alerta": "INTEGER",
        "materiais_detectados_raw": "TEXT",
        "contaminantes_detectados": "TEXT",
        "alerta_contaminacao": "INTEGER",
        "tipo_contaminacao": "TEXT",
        "severidade_contaminacao": "INTEGER",
        "motivo_falha": "TEXT",
        "deteccoes_contaminantes_json": "TEXT",
        "cacamba_esperada": "TEXT",
        "material_esperado": "TEXT",
        "modelo_volumetria_versao": "TEXT",
        "modelo_contaminantes_versao": "TEXT",
        "evidencia_path": "TEXT",
        "debug_path": "TEXT",
        "origem": "TEXT",
        "processado_com_sucesso": "INTEGER",
        "criado_em": "TEXT",
    }

    for col, col_type in wanted_cols.items():
        if col not in existing_cols:
            conn.execute(f"ALTER TABLE eventos ADD COLUMN {col} {col_type}")

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_eventos_arquivo_path ON eventos(arquivo_path)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_eventos_arquivo_hash ON eventos(arquivo_hash)"
    )
    conn.commit()


def buscar_evento_existente(conn: sqlite3.Connection, arquivo_path: str):
    row = conn.execute(
        """
        SELECT id
        FROM eventos
        WHERE arquivo_path = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (arquivo_path,),
    ).fetchone()
    return row[0] if row else None


def upsert_evento(conn: sqlite3.Connection, payload: dict):
    existing_id = buscar_evento_existente(conn, payload["arquivo_path"])

    if existing_id is not None:
        conn.execute(
            """
            UPDATE eventos
            SET
                ts_processamento = ?,
                data_ref = ?,
                hora_ref = ?,
                arquivo_nome = ?,
                arquivo_hash = ?,
                grupo = ?,
                status = ?,
                fill_percent = ?,
                estado_dashboard = ?,
                ok_consec = ?,
                alerta = ?,
                materiais_detectados_raw = ?,
                contaminantes_detectados = ?,
                alerta_contaminacao = ?,
                tipo_contaminacao = ?,
                severidade_contaminacao = ?,
                motivo_falha = ?,
                deteccoes_contaminantes_json = ?,
                cacamba_esperada = ?,
                material_esperado = ?,
                modelo_volumetria_versao = ?,
                modelo_contaminantes_versao = ?,
                evidencia_path = ?,
                debug_path = ?,
                origem = ?,
                processado_com_sucesso = ?,
                criado_em = ?
            WHERE id = ?
            """,
            (
                payload["ts_processamento"],
                payload["data_ref"],
                payload["hora_ref"],
                payload["arquivo_nome"],
                payload["arquivo_hash"],
                payload["grupo"],
                payload["status"],
                payload["fill_percent"],
                payload["estado_dashboard"],
                payload["ok_consec"],
                payload["alerta"],
                payload["materiais_detectados_raw"],
                payload["contaminantes_detectados"],
                payload["alerta_contaminacao"],
                payload["tipo_contaminacao"],
                payload["severidade_contaminacao"],
                payload["motivo_falha"],
                payload["deteccoes_contaminantes_json"],
                payload["cacamba_esperada"],
                payload["material_esperado"],
                payload["modelo_volumetria_versao"],
                payload["modelo_contaminantes_versao"],
                payload["evidencia_path"],
                payload["debug_path"],
                payload["origem"],
                payload["processado_com_sucesso"],
                payload["criado_em"],
                existing_id,
            ),
        )
        return "updated"

    conn.execute(
        """
        INSERT INTO eventos (
            ts_processamento,
            data_ref,
            hora_ref,
            arquivo_nome,
            arquivo_path,
            arquivo_hash,
            grupo,
            status,
            fill_percent,
            estado_dashboard,
            ok_consec,
            alerta,
            materiais_detectados_raw,
            contaminantes_detectados,
            alerta_contaminacao,
            tipo_contaminacao,
            severidade_contaminacao,
            motivo_falha,
            deteccoes_contaminantes_json,
            cacamba_esperada,
            material_esperado,
            modelo_volumetria_versao,
            modelo_contaminantes_versao,
            evidencia_path,
            debug_path,
            origem,
            processado_com_sucesso,
            criado_em
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload["ts_processamento"],
            payload["data_ref"],
            payload["hora_ref"],
            payload["arquivo_nome"],
            payload["arquivo_path"],
            payload["arquivo_hash"],
            payload["grupo"],
            payload["status"],
            payload["fill_percent"],
            payload["estado_dashboard"],
            payload["ok_consec"],
            payload["alerta"],
            payload["materiais_detectados_raw"],
            payload["contaminantes_detectados"],
            payload["alerta_contaminacao"],
            payload["tipo_contaminacao"],
            payload["severidade_contaminacao"],
            payload["motivo_falha"],
            payload["deteccoes_contaminantes_json"],
            payload["cacamba_esperada"],
            payload["material_esperado"],
            payload["modelo_volumetria_versao"],
            payload["modelo_contaminantes_versao"],
            payload["evidencia_path"],
            payload["debug_path"],
            payload["origem"],
            payload["processado_com_sucesso"],
            payload["criado_em"],
        ),
    )
    return "inserted"


def main():
    if not CSV_PATH.exists():
        print(f"[AVISO] CSV nao encontrado: {CSV_PATH}")
        return

    ensure_parent_dir(DB_PATH)

    with open(CSV_PATH, "r", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    inseridos = 0
    atualizados = 0
    ignorados = 0

    with sqlite3.connect(DB_PATH) as conn:
        ensure_schema(conn)

        now = datetime.now()
        ts_processamento = now.isoformat(timespec="seconds")
        data_ref = now.strftime("%Y-%m-%d")
        hora_ref = now.strftime("%H:%M:%S")

        for row in rows:
            arquivo_nome = row.get("arquivo", "").strip()
            grupo = row.get("grupo", "").strip()

            if not arquivo_nome or not grupo:
                ignorados += 1
                continue

            arquivo_path = str(BASE_DIR / "input" / "images" / arquivo_nome)
            arquivo_hash = arquivo_hash_from_path(arquivo_path)

            debug_path = str(DEBUG_DIR / f"{Path(arquivo_nome).stem}_debug.jpg")
            debug_path_final = debug_path if Path(debug_path).exists() else None

            payload = {
                "ts_processamento": ts_processamento,
                "data_ref": data_ref,
                "hora_ref": hora_ref,
                "arquivo_nome": arquivo_nome,
                "arquivo_path": arquivo_path,
                "arquivo_hash": arquivo_hash,
                "grupo": grupo,
                "status": row.get("status_frame", ""),
                "fill_percent": parse_float(row.get("fill_percent_filtrado")),
                "estado_dashboard": row.get("estado_dashboard", ""),
                "ok_consec": parse_int(row.get("ok_consecutivos_criticos"), 0),
                "alerta": parse_int(row.get("alerta_dashboard"), 0),
                "materiais_detectados_raw": row.get("materiais_detectados_raw", ""),
                "contaminantes_detectados": row.get("contaminantes_detectados", ""),
                "alerta_contaminacao": parse_int(row.get("alerta_contaminacao"), 0),
                "tipo_contaminacao": row.get("tipo_contaminacao", ""),
                "severidade_contaminacao": parse_int(row.get("severidade_contaminacao"), 0),
                "motivo_falha": row.get("motivo_falha", ""),
                "deteccoes_contaminantes_json": row.get("deteccoes_contaminantes_json", ""),
                "cacamba_esperada": row.get("cacamba_esperada", ""),
                "material_esperado": row.get("material_esperado", ""),
                "modelo_volumetria_versao": MODELO_VOLUMETRIA_VERSAO,
                "modelo_contaminantes_versao": MODELO_CONTAMINANTES_VERSAO,
                "evidencia_path": None,
                "debug_path": debug_path_final,
                "origem": "ftp",
                "processado_com_sucesso": 1,
                "criado_em": ts_processamento,
            }

            resultado = upsert_evento(conn, payload)
            if resultado == "inserted":
                inseridos += 1
            else:
                atualizados += 1

        conn.commit()

    print(
        f"[OK] sync_csv_para_db finalizado | inseridos={inseridos} | atualizados={atualizados} | ignorados={ignorados}"
    )


if __name__ == "__main__":
    main()