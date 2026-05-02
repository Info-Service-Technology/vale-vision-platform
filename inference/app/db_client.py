import json
import os

import pymysql


def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


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