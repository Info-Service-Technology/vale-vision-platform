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


def _load_event_columns(cursor):
    cursor.execute("SHOW COLUMNS FROM events")
    rows = cursor.fetchall()
    return {row["Field"] for row in rows}


def save_detection_event(payload: dict):
    metadata = payload.get("metadata", {})
    materiais_detectados_value = (
        payload.get("materiais_detectados_raw")
        or payload.get("materiais_detectados")
        or []
    )
    material_detectado_principal = None
    if isinstance(materiais_detectados_value, list) and materiais_detectados_value:
        material_detectado_principal = materiais_detectados_value[0]

    payload_db = {
        **payload,
        "processing_status": payload.get("processing_status", "processed"),
        "s3_bucket": payload.get("s3_bucket") or metadata.get("bucket"),
        "materiais_detectados": _to_db_text(
            materiais_detectados_value or ""
        ),
        "contaminantes_detectados": _to_db_text(
            payload.get("contaminantes_detectados") or ""
        ),
        "fill_percent": payload.get("fill_percent") or 0.0,
        "contamination_percent": payload.get("contamination_percent") or 0.0,
        "severidade_contaminacao": payload.get(
            "severidade_contaminacao",
            "baixa"
        ),
        "material_detectado": material_detectado_principal,
    }

    # Guarantee placeholders for optional DB columns that may exist in the
    # schema even when the current processing path has no value for them.
    for optional_field in (
        "debug_path",
        "s3_key_debug",
        "tenant_id",
        "camera_id",
        "container_id",
    ):
        payload_db.setdefault(optional_field, None)

    payload_db.pop("metadata", None)
    payload_db.pop("materiais_detectados_raw", None)

    with get_connection() as conn:
        with conn.cursor() as cursor:
            event_columns = _load_event_columns(cursor)

            sql_fields = []
            sql_values = []

            fixed_fields = {
                "data_ref": "CURDATE()",
                "hora_ref": "CURTIME()",
                "image_received_at": "NOW()",
            }

            optional_field_order = [
                "status",
                "processing_status",
                "file_path",
                "debug_path",
                "s3_bucket",
                "s3_key_raw",
                "s3_key_debug",
                "grupo",
                "materiais_detectados",
                "contaminantes_detectados",
                "alerta_contaminacao",
                "tipo_contaminacao",
                "severidade_contaminacao",
                "cacamba_esperada",
                "material_esperado",
                "material_detectado",
                "fill_percent",
                "contamination_percent",
                "tenant_id",
                "camera_id",
                "container_id",
            ]

            for field, raw_sql in fixed_fields.items():
                if field in event_columns:
                    sql_fields.append(field)
                    sql_values.append(raw_sql)

            for field in optional_field_order:
                if field in event_columns:
                    sql_fields.append(field)
                    sql_values.append(f"%({field})s")

            sql = f"""
                INSERT INTO events (
                    {", ".join(sql_fields)}
                )
                VALUES (
                    {", ".join(sql_values)}
                )
            """

            cursor.execute(sql, payload_db)
