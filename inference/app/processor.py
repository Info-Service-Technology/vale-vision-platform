import os
import re
from pathlib import Path
from typing import Any

from app.db_client import save_detection_event
from app.motor_contaminacao import avaliar_contaminacao
from app.s3_client import download_s3_object
from app.segmentador_borda_cacamba import SegmentadorBordaCacamba
from app.segmentador_contaminantes import SegmentadorContaminantes

CAMERA_GROUP_MAP_RAW = os.environ.get(
    "CAMERA_GROUP_MAP",
    "cammadeira=madeira,campapelao=papelao,camplastico=plastico,camsucata=sucata",
)

SEGMENTADOR_CONTAMINANTES = SegmentadorContaminantes()
SEGMENTADOR_BORDA = SegmentadorBordaCacamba()


def _normalize_material(material: str) -> str:
    if not material:
        return ""

    return (
        material.strip()
        .lower()
        .replace("ã", "a")
        .replace("á", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )


def _parse_camera_group_map() -> dict[str, str]:
    mapping: dict[str, str] = {}

    for item in CAMERA_GROUP_MAP_RAW.split(","):
        if "=" not in item:
            continue

        camera_name, group = item.split("=", 1)
        camera_name = camera_name.strip().lower()
        group = _normalize_material(group)

        if camera_name and group:
            mapping[camera_name] = group

    return mapping


CAMERA_GROUP_MAP = _parse_camera_group_map()


def _parse_float(value: Any) -> float | None:
    if value is None or value == "":
        return None

    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    return float(max(0.0, min(100.0, value)))


def inferir_materiais(local_image_path: Path) -> list[str]:
    if SEGMENTADOR_CONTAMINANTES.ativo:
        resultado = SEGMENTADOR_CONTAMINANTES.inferir(local_image_path)
        materiais = resultado.get("materiais_detectados", [])
        if materiais:
            return materiais

    return []


def inferir_grupo_por_materiais(materiais_detectados: list[str]) -> str:
    if not materiais_detectados:
        return "desconhecido"
    return materiais_detectados[0]


def _extract_camera_name_from_key(key: str) -> str:
    match = re.search(r"(?:^|/)camera=([^/]+)", key, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return "desconhecido"


def inferir_grupo_por_camera(camera_name: str) -> str:
    normalized_camera = camera_name.strip().lower()
    if not normalized_camera:
        return "desconhecido"

    mapped = CAMERA_GROUP_MAP.get(normalized_camera)
    if mapped:
        return mapped

    aliases = {
        "madeira": ["madeira", "wood", "md"],
        "papelao": ["papelao", "papelao", "papel", "cardboard"],
        "plastico": ["plastico", "plastic"],
        "sucata": ["sucata", "ferro", "metal", "scrap"],
    }
    for group, terms in aliases.items():
        if any(term in normalized_camera for term in terms):
            return group

    return "desconhecido"


def _infer_fill_percent(metadata: dict[str, Any]) -> float:
    for key in ("fill_percent", "fillLevel", "ocupacao_percent", "occupancy_percent"):
        parsed = _parse_float(metadata.get(key))
        if parsed is not None:
            return parsed
    return 0.0


def _calculate_contamination_percent(
    materiais_detectados: list[str], contaminantes_detectados: str
) -> float:
    contaminants = [m.strip() for m in contaminantes_detectados.split(",") if m.strip()]
    if not materiais_detectados or not contaminants:
        return 0.0
    percent = (len(contaminants) / len(materiais_detectados)) * 100
    return round(percent, 1)


def _resolve_expected_group(
    key: str,
    metadata: dict[str, Any],
    explicit_group: str | None = None,
    camera_name: str | None = None,
) -> tuple[str, str]:
    if explicit_group:
        return _normalize_material(explicit_group), camera_name or _extract_camera_name_from_key(key)

    for candidate_key in ("grupo", "expected_group", "cacamba_esperada", "material_esperado"):
        candidate = metadata.get(candidate_key)
        if candidate:
            return _normalize_material(str(candidate)), camera_name or _extract_camera_name_from_key(key)

    resolved_camera = camera_name or metadata.get("camera_name") or _extract_camera_name_from_key(key)
    return inferir_grupo_por_camera(str(resolved_camera)), str(resolved_camera)


def process_image_from_s3(
    bucket: str,
    key: str,
    grupo: str | None = None,
    camera_name: str | None = None,
    fill_percent: float | None = None,
    metadata: dict[str, Any] | None = None,
):
    metadata = metadata or {}
    local_path = download_s3_object(bucket=bucket, key=key)
    file_name = local_path.name
    grupo, resolved_camera_name = _resolve_expected_group(
        key=key,
        metadata=metadata,
        explicit_group=grupo,
        camera_name=camera_name,
    )

    border_result = SEGMENTADOR_BORDA.detectar(local_path)
    analysis_mask = border_result.get("mask") if border_result.get("ok") else None
    resultado_contaminantes = SEGMENTADOR_CONTAMINANTES.inferir(
        local_path,
        analysis_mask=analysis_mask,
    )
    materiais_detectados = resultado_contaminantes.get("materiais_detectados", [])

    if grupo == "desconhecido" and materiais_detectados:
        grupo = inferir_grupo_por_materiais(materiais_detectados)

    decisao = avaliar_contaminacao(
        grupo=grupo,
        materiais_detectados=materiais_detectados,
    )

    fill_percent_resolved = _parse_float(fill_percent)
    if fill_percent_resolved is None:
        fill_percent_resolved = _infer_fill_percent(metadata)

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
        "fill_percent": fill_percent_resolved,
        "contamination_percent": contamination_percent,
        **decisao,
        "metadata": {
            **metadata,
            "bucket": bucket,
            "key": key,
            "worker_version": "v1",
            "camera_name": resolved_camera_name,
            "bin_roi_detected": bool(border_result.get("ok")),
            "bin_roi_reason": border_result.get("motivo"),
            "bin_roi_polygon": border_result.get("polygon", []),
            "analysis_mask_applied": bool(resultado_contaminantes.get("analysis_mask_applied", False)),
            "deteccoes": resultado_contaminantes.get("deteccoes", []),
            "areas_ratio": resultado_contaminantes.get("areas_ratio", {}),
        },
    }

    if int(decisao.get("alerta_contaminacao", 0)) != 1:
        print("[processor] Sem contaminação detectada. Não grava no MySQL.", flush=True)
        return payload

    save_detection_event(payload)

    print(f"[processor] Resultado salvo: {payload}", flush=True)

    return payload
