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


def save_detection_event(payload: dict):
    sql = """
        INSERT INTO events (
            data_ref,
            hora_ref,
            status,
            file_path,
            s3_key_raw,
            s3_key_debug,
            grupo,
            materiais_detectados_raw,
            contaminantes_detectados,
            alerta_contaminacao,
            tipo_contaminacao,
            severidade_contaminacao,
            cacamba_esperada,
            material_esperado,
            metadata_json
        )
        VALUES (
            CURDATE(),
            CURTIME(),
            %(status)s,
            %(file_path)s,
            %(s3_key_raw)s,
            %(s3_key_debug)s,
            %(grupo)s,
            %(materiais_detectados_raw)s,
            %(contaminantes_detectados)s,
            %(alerta_contaminacao)s,
            %(tipo_contaminacao)s,
            %(severidade_contaminacao)s,
            %(cacamba_esperada)s,
            %(material_esperado)s,
            %(metadata_json)s
        )
    """

    payload = {
        **payload,
        "metadata_json": json.dumps(payload.get("metadata", {}), ensure_ascii=False),
    }

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, payload)