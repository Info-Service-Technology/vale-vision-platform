import json
import os

import pymysql


def get_connection():
    kwargs = {
        "host": os.getenv("DB_HOST"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME"),
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": True,
        "connect_timeout": 10,
        "read_timeout": 60,
        "write_timeout": 60,
        "charset": "utf8mb4",
    }

    ssl_ca = os.getenv("DB_SSL_CA")
    verify_identity = os.getenv("DB_SSL_VERIFY_IDENTITY", "true").lower() == "true"

    if ssl_ca:
        kwargs["ssl"] = {
            "ca": ssl_ca,
            "check_hostname": verify_identity,
        }

    return pymysql.connect(**kwargs)


def _to_db_text(value):
    if value is None:
        return None

    if isinstance(value, str):
        return value

    return json.dumps(value, ensure_ascii=False)


def _to_db_text(value):
    if value is None:
        return None

    if isinstance(value, str):
        return value

    return json.dumps(value, ensure_ascii=False)


def save_detection_event(payload: dict):
    sql = """
        INSERT INTO events (
            data_ref,
            hora_ref,
            status,
            processing_status,
            file_path,
            s3_bucket,
            s3_key_raw,
            s3_key_debug,
            grupo,
            materiais_detectados,
            contaminantes_detectados,
            alerta_contaminacao,
            tipo_contaminacao,
            severidade_contaminacao,
            cacamba_esperada,
            material_esperado,
            image_received_at
        )
        VALUES (
            CURDATE(),
            CURTIME(),
            %(status)s,
            %(processing_status)s,
            %(file_path)s,
            %(s3_bucket)s,
            %(s3_key_raw)s,
            %(s3_key_debug)s,
            %(grupo)s,
            %(materiais_detectados)s,
            %(contaminantes_detectados)s,
            %(alerta_contaminacao)s,
            %(tipo_contaminacao)s,
            %(severidade_contaminacao)s,
            %(cacamba_esperada)s,
            %(material_esperado)s,
            NOW()
        )
    """

    metadata = payload.get("metadata", {})

    payload_db = {
        **payload,
        "processing_status": payload.get(
            "processing_status",
            "processed"
        ),
        "s3_bucket": payload.get("s3_bucket")
            or metadata.get("bucket"),

        "materiais_detectados": _to_db_text(
            payload.get("materiais_detectados_raw")
            or payload.get("materiais_detectados")
            or ""
        ),

        "contaminantes_detectados": _to_db_text(
            payload.get("contaminantes_detectados")
            or ""
        ),

        "severidade_contaminacao": payload.get(
            "severidade_contaminacao",
            "baixa"
        ),
    }

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, payload_db)