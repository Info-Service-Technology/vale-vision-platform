import json
from pathlib import Path
from typing import Any

from app.contaminacao import avaliar_contaminacao
from app.db_client import save_detection_event
from app.s3_client import download_s3_object


def _json_safe(value: Any) -> Any:
    """
    Converte dict/list em JSON string para evitar erro no MySQL:
    'dict can not be used as parameter'.
    Mantém valores simples inalterados.
    """
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False)
    return value


def _normalize_payload_for_db(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: _json_safe(value) for key, value in payload.items()}


def inferir_materiais(local_image_path: Path) -> list[str]:
    """
    TODO:
    Aqui entra a chamada real do seu modelo.

    Exemplo futuro:
        segmentador = SegmentadorContaminantes(...)
        resultado = segmentador.predict(local_image_path)
        return resultado.classes_detectadas

    Por enquanto, este retorno é placeholder.
    """
    return []


def inferir_grupo_por_nome_arquivo(filename: str) -> str:
    nome = filename.lower()

    if "madeira" in nome:
        return "madeira"

    if "plastico" in nome or "plástico" in nome:
        return "plastico"

    if "sucata" in nome:
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

    payload = {
        "status": "processed",
        "file_path": local_path.name,
        "s3_key_raw": key,
        "s3_key_debug": None,
        "grupo": grupo,
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
