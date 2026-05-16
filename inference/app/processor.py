import json
import re
from pathlib import Path
from typing import Any

from app.db_client import save_detection_event
from app.s3_client import download_s3_object
from app.motor_contaminacao import avaliar_contaminacao

IGNORED_OBJECTS = {
    "human",
    "humano",
    "pessoa",
    "pessoas",
    "animal",
    "animais",
    "cao",
    "cachorro",
    "gato",
    "car",
    "carro",
    "truck",
    "vehicle",
    "onibus",
    "bus",
}

MATERIAL_KEYWORDS = {
    "madeira": ["madeira", "papelao", "papelão", "papel"],
    "plastico": ["plastico", "plástico", "plastic"],
    "sucata": ["sucata", "ferro", "scrap", "metal"],
}

OUTSIDE_BIN_TERMS = {
    "outside",
    "fora",
    "exterior",
    "street",
    "road",
    "pista",
    "estrada",
    "carro",
    "car",
    "truck",
    "bus",
    "onibus",
}


def _json_safe(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False)
    return value


def _normalize_payload_for_db(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: _json_safe(value) for key, value in payload.items()}


def _normalize_material(material: str) -> str:
    return material.strip().lower()


def _is_inside_bin(filename: str) -> bool:
    name = filename.lower()
    return not any(term in name for term in OUTSIDE_BIN_TERMS)


def _infer_fill_percent(filename: str) -> float:
    name = filename.lower()
    match = re.search(r"(\d{1,3})\s*%", name)
    if not match:
        match = re.search(r"(?:fill|ocupacao|lotacao|lotação)[_-]?(\d{1,3})", name)
    if match:
        value = int(match.group(1))
        return float(max(0, min(100, value)))
    return 0.0


def inferir_materiais(local_image_path: Path) -> list[str]:
    """
    TODO: substituir pelo modelo real.
    """
    filename = local_image_path.name.lower()
    if any(term in filename for term in IGNORED_OBJECTS):
        return []

    materiais = []
    for material, terms in MATERIAL_KEYWORDS.items():
        if any(term in filename for term in terms):
            materiais.append(material)

    return materiais


def inferir_grupo_por_nome_arquivo(filename: str) -> str:
    nome = filename.lower()

    if "papelao" in nome or "papelão" in nome:
        return "papelao"

    if "plastico" in nome or "plástico" in nome:
        return "plastico"

    if "sucata" in nome or "ferro" in nome:
        return "sucata"

    return "desconhecido"


def _calculate_contamination_percent(
    materiais_detectados: list[str], contaminantes_detectados: str
) -> float:
    contaminants = [m.strip() for m in contaminantes_detectados.split(",") if m.strip()]
    if not materiais_detectados or not contaminants:
        return 0.0
    percent = (len(contaminants) / len(materiais_detectados)) * 100
    return round(percent, 1)


def process_image_from_s3(bucket: str, key: str):
    local_path = download_s3_object(bucket=bucket, key=key)
    file_name = local_path.name

    if not _is_inside_bin(file_name):
        result = {
            "status": "ignored_outside_bin",
            "file_path": file_name,
            "s3_key_raw": key,
            "s3_key_debug": None,
            "grupo": inferir_grupo_por_nome_arquivo(file_name),
            "materiais_detectados_raw": [],
            "materiais_detectados": [],
            "contaminantes_detectados": "",
            "alerta_contaminacao": 0,
            "tipo_contaminacao": "fora_da_cacamba",
            "severidade_contaminacao": "baixa",
            "cacamba_esperada": "",
            "material_esperado": "",
            "fill_percent": _infer_fill_percent(file_name),
            "contamination_percent": 0.0,
            "metadata": {
                "bucket": bucket,
                "key": key,
                "worker_version": "v1",
            },
        }
        print("[processor] Imagem fora da caçamba. Ignorada.", flush=True)
        return result

    grupo = inferir_grupo_por_nome_arquivo(file_name)
    materiais_detectados = inferir_materiais(local_path)

    decisao = avaliar_contaminacao(
        grupo=grupo,
        materiais_detectados=materiais_detectados,
    )

    fill_percent = _infer_fill_percent(file_name)
    contaminantes_text = decisao.get("contaminantes_detectados", "")
    contamination_percent = _calculate_contamination_percent(
        materiais_detectados,
        contaminantes_text,
    )

    payload = {
        "status": "contamination" if int(decisao.get("alerta_contaminacao", 0)) == 1 else "ok",
        "file_path": file_name,
        "s3_key_raw": key,
        "s3_key_debug": None,
        "grupo": grupo,
        "materiais_detectados_raw": materiais_detectados,
        "materiais_detectados": materiais_detectados,
        "fill_percent": fill_percent,
        "contamination_percent": contamination_percent,
        **decisao,
        "metadata": {
            "bucket": bucket,
            "key": key,
            "worker_version": "v1",
        },
    }

    if int(decisao.get("alerta_contaminacao", 0)) != 1:
        print("[processor] Sem contaminação detectada. Não grava no MySQL.", flush=True)
        return payload

    save_detection_event(payload)

    print(f"[processor] Resultado salvo: {payload}", flush=True)

    return payload