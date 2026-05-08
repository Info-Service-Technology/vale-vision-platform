import json
from pathlib import Path
from typing import Any

from app.db_client import save_detection_event
from app.s3_client import download_s3_object
from app.motor_contaminacao import avaliar_contaminacao


def _json_safe(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False)
    return value


def _normalize_payload_for_db(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: _json_safe(value) for key, value in payload.items()}


def inferir_materiais(local_image_path: Path) -> list[str]:
    """
    TODO: substituir pelo modelo real.
    """
    return ["sucata", "plastico","papelao"]


def inferir_grupo_por_nome_arquivo(filename: str) -> str:
    nome = filename.lower()

    if "papelao" in nome or "papelão" in nome:
        return "papelao"

    if "plastico" in nome or "plástico" in nome:
        return "plastico"

    if "sucata" in nome or "ferro" in nome:
        return "sucata"

    return "desconhecido"


def process_image_from_s3(bucket: str, key: str):
    local_path = download_s3_object(bucket=bucket, key=key)

    grupo = inferir_grupo_por_nome_arquivo(local_path.name)

    materiais_detectados = inferir_materiais(local_path)

    decisao = avaliar_contaminacao(
        grupo=grupo,
        materiais_detectados=materiais_detectados,
    )

    status_evento = (
        "contamination"
        if int(decisao.get("alerta_contaminacao", 0)) == 1
        else "processed"
    )

    payload = {
        "status": status_evento,
        "file_path": local_path.name,
        "s3_key_raw": key,
        "s3_key_debug": None,
        "grupo": grupo,
        "materiais_detectados_raw": materiais_detectados,
        **decisao,
        "metadata": {
            "bucket": bucket,
            "key": key,
            "worker_version": "v1",
        },
    }

    payload_db = _normalize_payload_for_db(payload)

    save_detection_event(payload_db)

    print(f"[processor] Resultado salvo: {payload_db}", flush=True)

    return payload