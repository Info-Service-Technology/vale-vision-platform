import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional

BASE_DIR = Path(r"E:\PROJETO VALE\PACOTE_PILOTO_VM\PRODUTO_VOLUMETRIA_RELEASE_V8")
DB_PATH = BASE_DIR / "data" / "eventos.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def evento_ja_processado(arquivo_path: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM eventos WHERE arquivo_path = ? LIMIT 1",
            (arquivo_path,)
        ).fetchone()
    return row is not None


def registrar_evento(
    arquivo_nome: str,
    arquivo_path: str,
    grupo: str,
    status: Optional[str] = None,
    fill_percent: Optional[float] = None,
    estado_dashboard: Optional[str] = None,
    ok_consec: Optional[int] = None,
    alerta: Optional[int] = None,
    materiais_detectados_raw: Optional[str] = None,
    contaminantes_detectados: Optional[str] = None,
    alerta_contaminacao: Optional[int] = None,
    motivo_falha: Optional[str] = None,
    modelo_volumetria_versao: Optional[str] = None,
    modelo_contaminantes_versao: Optional[str] = None,
    evidencia_path: Optional[str] = None,
    debug_path: Optional[str] = None,
    arquivo_hash: Optional[str] = None,
    origem: str = "ftp",
    processado_com_sucesso: int = 1,
):
    agora = datetime.now()
    ts_processamento = agora.strftime("%Y-%m-%d %H:%M:%S")
    data_ref = agora.strftime("%Y-%m-%d")
    hora_ref = agora.strftime("%H:%M:%S")

    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO eventos (
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
                motivo_falha,
                modelo_volumetria_versao,
                modelo_contaminantes_versao,
                evidencia_path,
                debug_path,
                origem,
                processado_com_sucesso
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
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
                motivo_falha,
                modelo_volumetria_versao,
                modelo_contaminantes_versao,
                evidencia_path,
                debug_path,
                origem,
                processado_com_sucesso,
            ),
        )
        conn.commit()


def registrar_arquivo_ignorado(
    arquivo_nome: str,
    arquivo_path: str,
    grupo: Optional[str],
    motivo: str,
):
    ts_registro = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO arquivos_ignorados (
                ts_registro,
                arquivo_nome,
                arquivo_path,
                grupo,
                motivo
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (ts_registro, arquivo_nome, arquivo_path, grupo, motivo),
        )
        conn.commit()


def registrar_execucao_inicio(status: str = "iniciado", mensagem: str = "") -> int:
    ts_inicio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO execucoes_servico (
                ts_inicio,
                status,
                mensagem
            ) VALUES (?, ?, ?)
            """,
            (ts_inicio, status, mensagem),
        )
        conn.commit()
        return cur.lastrowid


def registrar_execucao_fim(execucao_id: int, status: str = "finalizado", mensagem: str = ""):
    ts_fim = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE execucoes_servico
            SET ts_fim = ?, status = ?, mensagem = ?
            WHERE id = ?
            """,
            (ts_fim, status, mensagem, execucao_id),
        )
        conn.commit()


if __name__ == "__main__":
    print("[OK] db_eventos.py criado e pronto para uso")
