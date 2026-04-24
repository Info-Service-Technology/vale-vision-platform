import csv
import json
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from config import (
    INPUT_DIR,
    CSV_DIR,
    DEBUG_DIR,
    OPENING_MASK_DIR,
    FLOOR_MASK_DIR,
    WALL_MASK_DIR,
    CONSEC_OK_PARA_TROCA,
    ALERTA_VERMELHO,
    MODEL_PATH,
)
from segmentador import SegmentadorVolumetria
from segmentador_contaminantes import SegmentadorContaminantes
from motor_volumetria_permissivo import (
    detect_group,
    extrair_features,
    estado_dashboard_from_fill,
    render_debug,
)
from motor_contaminacao import avaliar_contaminacao

VALID_EXTS = [".jpg", ".jpeg", ".png", ".bmp", ".webp"]

# Thresholds do detector de overflow
OVERFLOW_FLOOR_VS_OPENING_MAX = 0.08
OVERFLOW_WALL_VS_OPENING_MAX = 0.45
OVERFLOW_WALL_VS_OPENING_MIN = 0.01
OVERFLOW_FILL_MINIMO = 85.0

RESULT_COLUMNS = [
    "arquivo",
    "grupo",
    "classe_predita",
    "status_frame",
    "motivo_falha",
    "confidence_final",
    "fill_percent_filtrado",
    "estado_dashboard",
    "fill_temporal",
    "estado_dashboard_temporal",
    "alerta_dashboard",
    "ok_consecutivos_criticos",
    "opening_area",
    "opening_area_ref",
    "opening_area_ratio_ref",
    "floor_area_bruto",
    "floor_area_filtrado",
    "expected_overlap_ratio",
    "filtered_vs_raw_ratio",
    "divergencia_pp",
    "suspeita_opening_borda",
    "suspeita_opening_area",
    "suspeita_floor_excessivo",
    "suspeita_floor_quase_zero",
    "suspeita_divergencia_bruto_filtrado",
    "suspeita_expected_overlap_baixo",
    "suspeita_floor_filtrado_colapsou",
    "materiais_detectados_raw",
    "deteccoes_contaminantes_json",
    "contaminantes_detectados",
    "alerta_contaminacao",
    "tipo_contaminacao",
    "severidade_contaminacao",
    "cacamba_esperada",
    "material_esperado",
]

DASHBOARD_COLUMNS = [
    "grupo",
    "ultimo_arquivo",
    "status_frame",
    "motivo_falha",
    "fill_percent_filtrado",
    "estado_dashboard",
    "alerta_dashboard",
    "materiais_detectados_raw",
    "contaminantes_detectados",
    "alerta_contaminacao",
    "tipo_contaminacao",
    "severidade_contaminacao",
]


def detectar_overflow(opening_uint8, floor_uint8, wall_uint8):
    """
    Overflow controlado mais sensível para os casos altos que ainda escaparam.
    """
    resultado = {
        "overflow_detectado": False,
        "fill_estimado": None,
        "confianca": 0.0,
        "motivo": "",
    }

    opening_area = int(np.count_nonzero(opening_uint8 > 0))
    floor_area = int(np.count_nonzero(floor_uint8 > 0))
    wall_area = int(np.count_nonzero(wall_uint8 > 0))

    if opening_area <= 0:
        return resultado

    floor_vs_opening = floor_area / float(opening_area)
    wall_vs_opening = wall_area / float(opening_area)
    total_visible_vs_opening = (floor_area + wall_area) / float(opening_area)

    score = 0
    motivos = []

    # Sinal principal: piso quase sumiu
    if floor_vs_opening < 0.12:
        score += 3
        motivos.append("piso_colapsado")
        if floor_vs_opening < 0.06:
            score += 1
            motivos.append("piso_colapsado_forte")

    # Paredes ainda presentes, mas curtas / pouco úteis
    if 0.005 < wall_vs_opening < 0.60:
        score += 1
        motivos.append("paredes_curtas")

    # Quase nada visível dentro da boca
    if total_visible_vs_opening < 0.08:
        score += 2
        motivos.append("interior_quase_invisivel")

    # Caso extremo: piso quase zero sozinho já é forte indício
    if floor_vs_opening < 0.03:
        score += 1
        motivos.append("piso_quase_zero")

    if score >= 3:
        resultado["overflow_detectado"] = True
        resultado["motivo"] = "+".join(motivos)

        if score >= 6:
            resultado["fill_estimado"] = 93.0
            resultado["confianca"] = 0.82
        elif score >= 4:
            resultado["fill_estimado"] = 85.0
            resultado["confianca"] = 0.72
        else:
            resultado["fill_estimado"] = OVERFLOW_FILL_MINIMO
            resultado["confianca"] = 0.62

    return resultado


def normalize_row(row: dict) -> dict:
    out = {k: row.get(k, "") for k in RESULT_COLUMNS}

    if out["alerta_contaminacao"] == "":
        out["alerta_contaminacao"] = 0
    if out["alerta_dashboard"] == "":
        out["alerta_dashboard"] = 0
    if out["ok_consecutivos_criticos"] == "":
        out["ok_consecutivos_criticos"] = 0
    if out["severidade_contaminacao"] == "":
        out["severidade_contaminacao"] = 0

    return out


def load_existing_rows(csv_path: Path) -> list[dict]:
    if not csv_path.exists():
        return []

    with open(csv_path, "r", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    return [normalize_row(r) for r in rows]


def write_rows(csv_path: Path, rows: list[dict]) -> None:
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=RESULT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def write_dashboard(csv_path: Path, rows: list[dict]) -> None:
    resumo_por_grupo = {}

    for row in rows:
        grupo = row.get("grupo", "")
        if not grupo:
            continue

        resumo_por_grupo[grupo] = {
            "grupo": grupo,
            "ultimo_arquivo": row.get("arquivo", ""),
            "status_frame": row.get("status_frame", ""),
            "motivo_falha": row.get("motivo_falha", ""),
            "fill_percent_filtrado": row.get("fill_percent_filtrado", ""),
            "estado_dashboard": row.get("estado_dashboard", ""),
            "alerta_dashboard": row.get("alerta_dashboard", 0),
            "materiais_detectados_raw": row.get("materiais_detectados_raw", ""),
            "contaminantes_detectados": row.get("contaminantes_detectados", ""),
            "alerta_contaminacao": row.get("alerta_contaminacao", 0),
            "tipo_contaminacao": row.get("tipo_contaminacao", ""),
            "severidade_contaminacao": row.get("severidade_contaminacao", 0),
        }

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=DASHBOARD_COLUMNS)
        writer.writeheader()
        writer.writerows(resumo_por_grupo.values())


def merge_rows(existing_rows: list[dict], new_rows: list[dict]) -> list[dict]:
    merged = {}
    order = []

    for row in existing_rows + new_rows:
        key = row["arquivo"]
        if key not in merged:
            order.append(key)
        merged[key] = normalize_row(row)

    return [merged[k] for k in order]


def parse_float_safe(v, default=0.0):
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default


def is_truthy_flag(v) -> bool:
    s = str(v).strip().lower()
    return s in {"1", "true", "sim", "yes", "y"}


def sanitize_feats_for_dashboard(feats: dict) -> dict:
    """
    Ajuste leve no dicionário vindo do motor, SEM apagar o fill técnico.
    O objetivo aqui é só marcar estado/status de revisão quando necessário,
    deixando o valor numérico existir para o CSV/dashboard.
    """
    if feats is None:
        return feats

    status = str(feats.get("status_frame", "")).strip().lower()
    motivo = str(feats.get("motivo_falha", "")).strip().lower()

    floor_bruto = parse_float_safe(feats.get("floor_area_raw", ""), default=0.0)
    floor_filtrado = parse_float_safe(feats.get("floor_area_filtered", ""), default=0.0)
    expected_overlap = parse_float_safe(feats.get("expected_overlap_ratio", ""), default=0.0)
    filtered_ratio = parse_float_safe(feats.get("filtered_vs_raw_ratio", ""), default=0.0)

    fill_val = parse_float_safe(
        feats.get("fill_percent_filtered", feats.get("fill_percent_filtrado", "")),
        default=-1.0,
    )

    suspeita_floor_quase_zero = is_truthy_flag(feats.get("suspeita_floor_quase_zero", ""))
    suspeita_expected_overlap_baixo = is_truthy_flag(feats.get("suspeita_expected_overlap_baixo", ""))
    suspeita_floor_filtrado_colapsou = is_truthy_flag(feats.get("suspeita_floor_filtrado_colapsou", ""))
    suspeita_divergencia = is_truthy_flag(feats.get("suspeita_divergencia_bruto_filtrado", ""))

    invalido_real = status == "invalido"

    suspeito_estrutural = (
        suspeita_expected_overlap_baixo
        or suspeita_floor_filtrado_colapsou
        or suspeita_divergencia
        or suspeita_floor_quase_zero
        or expected_overlap < 0.06
        or (floor_bruto > 0 and filtered_ratio < 0.04)
    )

    sem_base_numerica = (
        fill_val < 0
        or (floor_bruto <= 0 and floor_filtrado <= 0)
    )

    if invalido_real:
        feats["estado_dashboard"] = "invalido"
        feats["estado_dashboard_temporal"] = "invalido"
        feats["alerta_dashboard"] = 0
        return feats

    if status == "suspeito" or motivo == "suspeito_generico" or suspeito_estrutural or sem_base_numerica:
        feats["status_frame"] = "suspeito"
        feats["estado_dashboard"] = "revisar"
        feats["estado_dashboard_temporal"] = "revisar"
        feats["alerta_dashboard"] = 0

        if suspeita_floor_quase_zero:
            feats["motivo_falha"] = "suspeito_floor_quase_zero"
        elif not motivo:
            feats["motivo_falha"] = "suspeito_generico"

    return feats


def sanitize_row_final(row: dict) -> dict:
    """
    Regra final para o CSV/dashboard.
    """
    if row is None:
        return row

    status = str(row.get("status_frame", "")).strip().lower()
    motivo = str(row.get("motivo_falha", "")).strip().lower()

    def is_true(v):
        return str(v).strip().lower() in {"1", "true", "sim", "yes", "y"}

    def to_float_or_none(v):
        try:
            if v in (None, ""):
                return None
            return float(v)
        except Exception:
            return None

    fill_val = to_float_or_none(row.get("fill_percent_filtrado", ""))
    floor_bruto = to_float_or_none(row.get("floor_area_bruto", ""))
    floor_filtrado = to_float_or_none(row.get("floor_area_filtrado", ""))
    expected_overlap = to_float_or_none(row.get("expected_overlap_ratio", ""))
    filtered_ratio = to_float_or_none(row.get("filtered_vs_raw_ratio", ""))

    suspeita_floor_quase_zero = is_true(row.get("suspeita_floor_quase_zero", ""))
    suspeita_expected_overlap_baixo = is_true(row.get("suspeita_expected_overlap_baixo", ""))
    suspeita_floor_filtrado_colapsou = is_true(row.get("suspeita_floor_filtrado_colapsou", ""))
    suspeita_divergencia = is_true(row.get("suspeita_divergencia_bruto_filtrado", ""))

    has_numeric_fill = fill_val is not None and 0.0 <= fill_val <= 100.0
    has_any_floor_signal = (
        (floor_bruto is not None and floor_bruto > 0)
        or (floor_filtrado is not None and floor_filtrado > 0)
    )

    # PRESERVA explicitamente o overflow estimado
    if motivo.startswith("suspeito_overflow_estimado:"):
        row["status_frame"] = "suspeito"
        row["estado_dashboard"] = "revisar"
        row["estado_dashboard_temporal"] = "revisar"
        row["alerta_dashboard"] = 0
        if row.get("fill_temporal", "") in (None, ""):
            row["fill_temporal"] = row.get("fill_percent_filtrado", "")
        return row

    if status == "invalido" or motivo in {"humano_na_abertura", "sem_opening_inner_valido"}:
        row["fill_percent_filtrado"] = ""
        row["fill_temporal"] = ""
        row["alerta_dashboard"] = 0
        row["estado_dashboard"] = "invalido" if status == "invalido" else "revisar"
        row["estado_dashboard_temporal"] = row["estado_dashboard"]
        return row

    soft_suspect = (
        status == "suspeito"
        or motivo.startswith("suspeito")
        or suspeita_floor_quase_zero
        or suspeita_expected_overlap_baixo
        or suspeita_floor_filtrado_colapsou
        or suspeita_divergencia
        or (
            expected_overlap is not None
            and expected_overlap < 0.06
        )
        or (
            filtered_ratio is not None
            and filtered_ratio < 0.04
        )
    )

    if soft_suspect:
        row["status_frame"] = "suspeito"
        row["estado_dashboard"] = "revisar"
        row["estado_dashboard_temporal"] = "revisar"
        row["alerta_dashboard"] = 0

        if suspeita_floor_quase_zero and not motivo.startswith("suspeito_overflow_estimado:"):
            row["motivo_falha"] = "suspeito_floor_quase_zero"
        elif not motivo:
            row["motivo_falha"] = "suspeito_generico"

        if has_numeric_fill:
            if row.get("fill_temporal", "") in (None, ""):
                row["fill_temporal"] = row.get("fill_percent_filtrado", "")
        else:
            row["fill_percent_filtrado"] = ""
            row["fill_temporal"] = ""

        return row

    if not has_numeric_fill:
        row["fill_percent_filtrado"] = ""
        row["fill_temporal"] = ""
        row["alerta_dashboard"] = 0
        row["status_frame"] = "suspeito"
        row["estado_dashboard"] = "revisar"
        row["estado_dashboard_temporal"] = "revisar"
        if not motivo:
            row["motivo_falha"] = "suspeito_generico"
        return row

    if has_numeric_fill and not has_any_floor_signal and status != "ok":
        row["status_frame"] = "suspeito"
        row["estado_dashboard"] = "revisar"
        row["estado_dashboard_temporal"] = "revisar"
        row["alerta_dashboard"] = 0
        if not motivo:
            row["motivo_falha"] = "suspeito_generico"
        if row.get("fill_temporal", "") in (None, ""):
            row["fill_temporal"] = row.get("fill_percent_filtrado", "")
        return row

    return row



def build_previous_critical_counters(rows: list[dict]) -> dict[str, int]:
    counters = {}

    for row in rows:
        grupo = row.get("grupo", "")
        if not grupo:
            continue

        if grupo not in counters:
            counters[grupo] = 0

        status_frame = row.get("status_frame", "")
        fill = parse_float_safe(row.get("fill_percent_filtrado", ""), default=0.0)

        if status_frame == "ok" and fill >= ALERTA_VERMELHO:
            counters[grupo] += 1
        else:
            counters[grupo] = 0

    return counters


def build_human_detector():
    hog = cv2.HOGDescriptor()
    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
    return hog


def detectar_humanos(hog, img_bgr, max_width=1280):
    h, w = img_bgr.shape[:2]
    scale = 1.0
    img_small = img_bgr

    if w > max_width:
        scale = max_width / float(w)
        img_small = cv2.resize(
            img_bgr,
            (int(w * scale), int(h * scale)),
            interpolation=cv2.INTER_LINEAR
        )

    rects, weights = hog.detectMultiScale(
        img_small,
        winStride=(8, 8),
        padding=(8, 8),
        scale=1.05
    )

    img_h, img_w = img_small.shape[:2]
    img_area = max(1, img_h * img_w)

    detections = []
    for (x, y, bw, bh), score in zip(rects, weights):
        score = float(score)
        area = float(bw * bh)
        area_ratio = area / float(img_area)
        aspect = bh / float(max(1, bw))

        if score < 1.20:
            continue
        if area_ratio < 0.015:
            continue
        if area_ratio > 0.40:
            continue
        if aspect < 1.40 or aspect > 4.50:
            continue

        x1 = int(round(x / scale))
        y1 = int(round(y / scale))
        x2 = int(round((x + bw) / scale))
        y2 = int(round((y + bh) / scale))

        x1 = max(0, min(x1, w - 1))
        y1 = max(0, min(y1, h - 1))
        x2 = max(0, min(x2, w))
        y2 = max(0, min(y2, h))

        if x2 <= x1 or y2 <= y1:
            continue

        detections.append({
            "bbox": (x1, y1, x2, y2),
            "score": score,
            "area_ratio": area_ratio,
            "aspect": aspect,
        })

    detections = sorted(
        detections,
        key=lambda d: (d["score"], d["area_ratio"]),
        reverse=True
    )
    return detections


def humano_intersecta_abertura(detections, opening_mask):
    if not detections:
        return False, None

    if opening_mask is None or opening_mask.size == 0:
        return False, None

    opening_bin = (opening_mask > 0).astype("uint8")
    opening_area = int(np.count_nonzero(opening_bin))
    if opening_area <= 0:
        return False, None

    h, w = opening_bin.shape[:2]
    best = None

    for det in detections:
        x1, y1, x2, y2 = det["bbox"]

        x1 = max(0, min(x1, w - 1))
        y1 = max(0, min(y1, h - 1))
        x2 = max(0, min(x2, w))
        y2 = max(0, min(y2, h))

        if x2 <= x1 or y2 <= y1:
            continue

        crop = opening_bin[y1:y2, x1:x2]
        if crop.size == 0:
            continue

        inter_pixels = int(np.count_nonzero(crop))
        if inter_pixels <= 0:
            continue

        bbox_area = max(1, (x2 - x1) * (y2 - y1))
        overlap_ratio = inter_pixels / float(bbox_area)
        opening_ratio = inter_pixels / float(opening_area)

        if overlap_ratio < 0.12:
            continue
        if opening_ratio < 0.02:
            continue
        if inter_pixels < 1200:
            continue

        cand = {
            **det,
            "overlap_ratio": overlap_ratio,
            "opening_ratio": opening_ratio,
            "inter_pixels": inter_pixels,
        }

        if best is None:
            best = cand
        else:
            key_best = (best["overlap_ratio"], best["score"], best["inter_pixels"])
            key_cand = (cand["overlap_ratio"], cand["score"], cand["inter_pixels"])
            if key_cand > key_best:
                best = cand

    return (best is not None), best


def render_debug_humano(img, opening_mask, deteccao):
    dbg = img.copy()

    opening_bin = (opening_mask > 0).astype(np.uint8)
    contours, _ = cv2.findContours(opening_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(dbg, contours, -1, (0, 255, 255), 2)

    red = np.zeros_like(dbg)
    red[:, :] = (0, 0, 255)
    mask_open = opening_bin.astype(bool)
    dbg[mask_open] = cv2.addWeighted(dbg, 0.85, red, 0.15, 0)[mask_open]

    if deteccao is not None:
        x1, y1, x2, y2 = deteccao["bbox"]
        cv2.rectangle(dbg, (x1, y1), (x2, y2), (0, 0, 255), 3)
        txt = f"HUMANO overlap={deteccao['overlap_ratio']:.2f}"
        cv2.putText(
            dbg,
            txt,
            (x1, max(30, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )

    return dbg


def _largest_component(mask_uint8):
    bin_mask = (mask_uint8 > 0).astype(np.uint8)
    if np.count_nonzero(bin_mask) == 0:
        return (bin_mask * 255).astype("uint8")

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(bin_mask, connectivity=8)
    if num_labels <= 1:
        return (bin_mask * 255).astype("uint8")

    best_label = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
    out = np.zeros_like(bin_mask)
    out[labels == best_label] = 1
    return (out * 255).astype("uint8")


def _mask_bbox(mask_uint8):
    ys, xs = np.where(mask_uint8 > 0)
    if len(xs) == 0 or len(ys) == 0:
        return None
    x1, x2 = int(xs.min()), int(xs.max())
    y1, y2 = int(ys.min()), int(ys.max())
    return (x1, y1, x2, y2)


def _mask_stats(mask_uint8):
    h, w = mask_uint8.shape[:2]
    area = int(np.count_nonzero(mask_uint8 > 0))
    bbox = _mask_bbox(mask_uint8)

    if bbox is None:
        return {
            "area": 0,
            "bbox": None,
            "bbox_w": 0,
            "bbox_h": 0,
            "cx": 0.0,
            "cy": 0.0,
            "area_ratio_img": 0.0,
            "width_ratio_img": 0.0,
            "height_ratio_img": 0.0,
        }

    x1, y1, x2, y2 = bbox
    bw = max(1, x2 - x1 + 1)
    bh = max(1, y2 - y1 + 1)

    ys, xs = np.where(mask_uint8 > 0)
    cx = float(xs.mean()) if len(xs) else 0.0
    cy = float(ys.mean()) if len(ys) else 0.0

    return {
        "area": area,
        "bbox": bbox,
        "bbox_w": bw,
        "bbox_h": bh,
        "cx": cx,
        "cy": cy,
        "area_ratio_img": area / float(max(1, h * w)),
        "width_ratio_img": bw / float(max(1, w)),
        "height_ratio_img": bh / float(max(1, h)),
    }


def _collect_contour_points(mask_uint8, min_area=150, y_min=None, y_max=None):
    bin_mask = (mask_uint8 > 0).astype(np.uint8)
    contours, _ = cv2.findContours(bin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    pts = []
    for c in contours:
        a = cv2.contourArea(c)
        if a < min_area:
            continue

        arr = c.reshape(-1, 2)

        if y_min is not None:
            arr = arr[arr[:, 1] >= int(y_min)]
        if y_max is not None:
            arr = arr[arr[:, 1] <= int(y_max)]

        if len(arr) >= 3:
            pts.append(arr)

    if not pts:
        return None

    return np.vstack(pts).astype(np.int32)


def _odd_kernel(v, min_value=3):
    v = max(int(v), int(min_value))
    return v if v % 2 == 1 else v + 1


def _fill_mask_holes(mask_uint8):
    bin_mask = ((mask_uint8 > 0).astype(np.uint8) * 255)
    if np.count_nonzero(bin_mask) == 0:
        return bin_mask.astype("uint8")

    h, w = bin_mask.shape[:2]

    seed = None
    border_points = []
    for x in range(w):
        border_points.append((x, 0))
        border_points.append((x, h - 1))
    for y in range(h):
        border_points.append((0, y))
        border_points.append((w - 1, y))

    for x, y in border_points:
        if bin_mask[y, x] == 0:
            seed = (x, y)
            break

    if seed is None:
        return bin_mask.astype("uint8")

    flood = bin_mask.copy()
    flood_mask = np.zeros((h + 2, w + 2), np.uint8)
    cv2.floodFill(flood, flood_mask, seed, 255)
    flood_inv = cv2.bitwise_not(flood)
    filled = cv2.bitwise_or(bin_mask, flood_inv)
    return filled.astype("uint8")


def _clip_mask_to_window(mask_uint8, x1, y1, x2, y2):
    h, w = mask_uint8.shape[:2]
    x1 = max(0, min(int(x1), w - 1))
    y1 = max(0, min(int(y1), h - 1))
    x2 = max(x1, min(int(x2), w - 1))
    y2 = max(y1, min(int(y2), h - 1))

    out = np.zeros_like(mask_uint8)
    out[y1:y2 + 1, x1:x2 + 1] = mask_uint8[y1:y2 + 1, x1:x2 + 1]
    return out.astype("uint8")


def reparar_opening_fragmentada(opening_uint8, wall_uint8):
    """
    Reparo estrutural da opening focado na boca inteira da caçamba.

    Mudanças principais desta versão:
    - não descarta fragmentos menores da opening logo no início;
    - evita hull em cima da parede inteira, que puxa a máscara para baixo e para as laterais;
    - reconstrói a opening usando somente a faixa superior estrutural da wall;
    - privilegia largura, centralidade e altura coerente da boca.
    """
    opening_raw = ((opening_uint8 > 0).astype(np.uint8) * 255)
    wall = _largest_component(wall_uint8)

    opening_main = _largest_component(opening_raw) if np.count_nonzero(opening_raw > 0) else opening_raw

    op_stats = _mask_stats(opening_main)
    wall_stats = _mask_stats(wall)

    info = {
        "aplicado": False,
        "motivos": [],
        "opening_area_before": op_stats["area"],
        "opening_area_after": op_stats["area"],
        "bbox_w_before": op_stats["bbox_w"],
        "bbox_w_after": op_stats["bbox_w"],
        "repair_kind": "none",
    }

    if wall_stats["area"] <= 0 or wall_stats["bbox"] is None:
        return opening_main, info

    h, w = opening_main.shape[:2]
    wall_x1, wall_y1, wall_x2, wall_y2 = wall_stats["bbox"]
    wall_bw = max(1, wall_stats["bbox_w"])
    wall_bh = max(1, wall_stats["bbox_h"])

    width_rel_vs_wall = 0.0
    area_rel_vs_wall = 0.0
    height_rel_vs_wall = 0.0
    cx_local = 0.5
    center_err_before = 0.0

    fragmentada = False
    strong_trigger = False

    if op_stats["area"] <= 0 or op_stats["bbox"] is None:
        fragmentada = True
        strong_trigger = True
        info["motivos"].append("opening_vazia")
    else:
        width_rel_vs_wall = op_stats["bbox_w"] / float(max(1, wall_bw))
        area_rel_vs_wall = op_stats["area"] / float(max(1, wall_stats["area"]))
        height_rel_vs_wall = op_stats["bbox_h"] / float(max(1, wall_bh))
        cx_local = (op_stats["cx"] - wall_x1) / float(max(1, wall_bw))
        center_err_before = abs(cx_local - 0.5)

        if width_rel_vs_wall < 0.86:
            fragmentada = True
            info["motivos"].append("opening_estreita")

        if area_rel_vs_wall < 0.34:
            fragmentada = True
            info["motivos"].append("opening_pequena_vs_wall")

        if height_rel_vs_wall < 0.10:
            fragmentada = True
            info["motivos"].append("opening_baixa_altura")

        if center_err_before > 0.18:
            fragmentada = True
            info["motivos"].append("opening_lateralizada")

        if width_rel_vs_wall < 0.72:
            strong_trigger = True
            info["motivos"].append("opening_estreita_forte")

        if area_rel_vs_wall < 0.20:
            strong_trigger = True
            info["motivos"].append("opening_muito_pequena_vs_wall")

        if center_err_before > 0.26:
            strong_trigger = True
            info["motivos"].append("opening_lateralizada_forte")

    if not fragmentada:
        return opening_main, info

    if op_stats["bbox"] is not None:
        _, op_y1, _, op_y2 = op_stats["bbox"]
        band_top = max(0, min(wall_y1, op_y1))
        band_bottom = max(
            op_y2 + int(round(0.08 * wall_bh)),
            wall_y1 + int(round(0.24 * wall_bh)),
        )
    else:
        band_top = max(0, wall_y1)
        band_bottom = wall_y1 + int(round(0.34 * wall_bh))

    band_bottom = min(
        h - 1,
        max(
            band_top + 10,
            min(band_bottom, wall_y1 + int(round(0.55 * wall_bh))),
        ),
    )

    pad_x = int(round(wall_bw * 0.03))
    clip_x1 = max(0, wall_x1 - pad_x)
    clip_x2 = min(w - 1, wall_x2 + pad_x)

    pts_open = _collect_contour_points(opening_raw, min_area=20)
    pts_wall_top = _collect_contour_points(
        wall,
        min_area=80,
        y_max=min(band_bottom, wall_y1 + int(round(0.42 * wall_bh))),
    )

    if pts_wall_top is None:
        pts_wall_top = _collect_contour_points(wall, min_area=80, y_max=band_bottom)

    if pts_wall_top is None:
        return opening_main, info

    def _finalize_candidate(mask_uint8):
        mask_uint8 = cv2.bitwise_or(mask_uint8.astype(np.uint8), opening_raw)
        mask_uint8 = _clip_mask_to_window(mask_uint8, clip_x1, band_top, clip_x2, band_bottom)

        kx = _odd_kernel(max(17, int(round(wall_bw * 0.06))), 17)
        ky = _odd_kernel(max(11, int(round(wall_bh * 0.05))), 11)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kx, ky))

        mask_uint8 = cv2.morphologyEx(mask_uint8, cv2.MORPH_CLOSE, kernel)
        mask_uint8 = _fill_mask_holes(mask_uint8)
        mask_uint8 = _largest_component(mask_uint8)
        return mask_uint8.astype("uint8")

    cand_top_hull = np.zeros_like(opening_main, dtype=np.uint8)
    pts_top_all = pts_wall_top if pts_open is None else np.vstack([pts_open, pts_wall_top])
    if pts_top_all is not None and len(pts_top_all) >= 3:
        hull_top = cv2.convexHull(pts_top_all.reshape(-1, 1, 2))
        cv2.drawContours(cand_top_hull, [hull_top], -1, 255, thickness=-1)
        cand_top_hull = _finalize_candidate(cand_top_hull)

    cand_wall_band = np.zeros_like(opening_main, dtype=np.uint8)
    wall_top_mask = np.zeros_like(opening_main, dtype=np.uint8)
    hull_wall_top = cv2.convexHull(pts_wall_top.reshape(-1, 1, 2))
    cv2.drawContours(wall_top_mask, [hull_wall_top], -1, 255, thickness=-1)
    wall_top_mask = _clip_mask_to_window(wall_top_mask, clip_x1, band_top, clip_x2, band_bottom)
    cv2.rectangle(cand_wall_band, (clip_x1, band_top), (clip_x2, band_bottom), 255, thickness=-1)
    cand_wall_band = cv2.bitwise_or(cand_wall_band, wall_top_mask)
    cand_wall_band = _finalize_candidate(cand_wall_band)

    def _candidate_score(mask_uint8):
        stats = _mask_stats(mask_uint8)
        if stats["area"] <= 0 or stats["bbox"] is None:
            return -1e9, stats, 0.0, 0.0, 0.0, 0.0, 1.0

        area_gain_local = stats["area"] / float(max(1, op_stats["area"]))
        width_gain_local = stats["bbox_w"] / float(max(1, op_stats["bbox_w"]))
        width_rel_local = stats["bbox_w"] / float(max(1, wall_bw))
        area_rel_local = stats["area"] / float(max(1, wall_stats["area"]))
        height_rel_local = stats["bbox_h"] / float(max(1, wall_bh))
        cx_local_local = (stats["cx"] - wall_x1) / float(max(1, wall_bw))
        center_err_local = abs(cx_local_local - 0.5)

        score = (
            3.0 * min(width_rel_local, 1.05)
            + 0.9 * min(width_gain_local, 2.0)
            + 0.5 * min(area_gain_local, 2.5)
            - 2.6 * center_err_local
            - 1.2 * max(0.0, height_rel_local - 0.60)
            - 1.0 * max(0.0, 0.08 - height_rel_local)
            - 1.6 * max(0.0, area_rel_local - 1.15)
        )

        if width_rel_local < 0.72:
            score -= 4.0
        if area_rel_local > 1.20:
            score -= 3.0
        if height_rel_local > 0.62:
            score -= 3.0
        if cx_local_local < 0.14 or cx_local_local > 0.86:
            score -= 4.0

        return (
            score,
            stats,
            area_gain_local,
            width_gain_local,
            width_rel_local,
            area_rel_local,
            center_err_local,
        )

    score_hull, stats_hull, area_gain_hull, width_gain_hull, width_rel_hull, area_rel_hull, center_err_hull = _candidate_score(cand_top_hull)
    score_band, stats_band, area_gain_band, width_gain_band, width_rel_band, area_rel_band, center_err_band = _candidate_score(cand_wall_band)

    if score_band >= score_hull:
        best_mask = cand_wall_band
        best_stats = stats_band
        best_area_gain = area_gain_band
        best_width_gain = width_gain_band
        best_width_rel = width_rel_band
        best_area_rel = area_rel_band
        best_center_err = center_err_band
        best_kind = "top_band"
    else:
        best_mask = cand_top_hull
        best_stats = stats_hull
        best_area_gain = area_gain_hull
        best_width_gain = width_gain_hull
        best_width_rel = width_rel_hull
        best_area_rel = area_rel_hull
        best_center_err = center_err_hull
        best_kind = "top_hull"

    if best_stats["area"] <= 0:
        return opening_main, info

    if strong_trigger:
        aceita = (
            best_width_rel >= max(width_rel_vs_wall + 0.03, 0.76)
            and best_center_err <= 0.30
            and best_area_rel <= 1.20
        )
    else:
        aceita = (
            best_width_rel >= max(width_rel_vs_wall + 0.05, 0.82)
            and best_center_err <= max(center_err_before + 0.02, 0.20)
            and best_area_rel <= 1.15
        )

    if not aceita:
        return opening_main, info

    info["aplicado"] = True
    info["opening_area_after"] = best_stats["area"]
    info["bbox_w_after"] = best_stats["bbox_w"]
    info["repair_kind"] = best_kind

    return best_mask.astype("uint8"), info


def render_debug_opening_repair(img_bgr, opening_before, wall_mask, opening_after, info):
    dbg = img_bgr.copy()

    before_bin = (opening_before > 0).astype(np.uint8)
    wall_bin = (wall_mask > 0).astype(np.uint8)
    after_bin = (opening_after > 0).astype(np.uint8)

    blue = np.zeros_like(dbg)
    blue[:, :] = (255, 0, 0)
    dbg[wall_bin.astype(bool)] = cv2.addWeighted(dbg, 0.80, blue, 0.20, 0)[wall_bin.astype(bool)]

    red = np.zeros_like(dbg)
    red[:, :] = (0, 0, 255)
    dbg[before_bin.astype(bool)] = cv2.addWeighted(dbg, 0.75, red, 0.25, 0)[before_bin.astype(bool)]

    green = np.zeros_like(dbg)
    green[:, :] = (0, 255, 0)
    dbg[after_bin.astype(bool)] = cv2.addWeighted(dbg, 0.65, green, 0.35, 0)[after_bin.astype(bool)]

    txt1 = (
        f"repair={info.get('aplicado', False)} "
        f"kind={info.get('repair_kind', 'none')} "
        f"motivos={','.join(info.get('motivos', []))}"
    )
    txt2 = (
        f"area_before={info.get('opening_area_before', 0)} "
        f"area_after={info.get('opening_area_after', 0)} "
        f"bboxw_before={info.get('bbox_w_before', 0)} "
        f"bboxw_after={info.get('bbox_w_after', 0)}"
    )

    cv2.putText(dbg, txt1, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.70, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(dbg, txt2, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (255, 255, 255), 2, cv2.LINE_AA)

    return dbg


def _build_overflow_row(
    img_path,
    img,
    name,
    grupo,
    opening_repair,
    floor,
    wall,
    overflow,
    cont_result,
    materiais_detectados_raw,
    deteccoes_contaminantes_json,
):
    fill_ov = float(overflow["fill_estimado"])
    conf_ov = float(overflow["confianca"])

    # Overflow controlado seguro:
    # mostra fill alto estimado, mas mantém como suspeito/revisar
    estado_dashboard = "revisar"
    status_frame = "suspeito"
    motivo_falha = f"suspeito_overflow_estimado:{overflow['motivo']}"

    feats_ov = {
        "opening_inner": (opening_repair > 0).astype(np.uint8),
        "floor_inner_raw": (floor > 0).astype(np.uint8),
        "wall_inner_raw": (wall > 0).astype(np.uint8),
        "visible_inner_raw": np.maximum((floor > 0), (wall > 0)).astype(np.uint8),
        "floor_inner_filtered": (floor > 0).astype(np.uint8),
        "fill_percent_filtered": fill_ov,
        "status_frame": status_frame,
        "classe": "overflow_estimado",
        "confidence_final": conf_ov * 100.0,
        "motivo_falha": motivo_falha,
        "opening_area": int(np.count_nonzero(opening_repair > 0)),
        "floor_area_raw": int(np.count_nonzero(floor > 0)),
        "floor_area_filtered": int(np.count_nonzero(floor > 0)),
        "expected_overlap_ratio": 0.0,
        "filtered_vs_raw_ratio": 1.0,
        "divergencia_pp": 0.0,
        "opening_area_ratio_ref": 0.0,
        "suspeita_opening_borda": False,
        "suspeita_opening_area": False,
        "suspeita_floor_excessivo": False,
        "suspeita_floor_quase_zero": True,
        "suspeita_divergencia_bruto_filtrado": False,
        "suspeita_expected_overlap_baixo": False,
        "suspeita_floor_filtrado_colapsou": False,
    }

    dbg = render_debug(img, feats_ov)
    cv2.imwrite(str(DEBUG_DIR / f"{name}_debug.jpg"), dbg)

    row = normalize_row({
        "arquivo": img_path.name,
        "grupo": grupo,
        "classe_predita": "overflow_estimado",
        "status_frame": status_frame,
        "motivo_falha": motivo_falha,
        "confidence_final": f"{conf_ov:.2f}",
        "fill_percent_filtrado": f"{fill_ov:.6f}",
        "estado_dashboard": estado_dashboard,
        "fill_temporal": f"{fill_ov:.6f}",
        "estado_dashboard_temporal": estado_dashboard,
        "alerta_dashboard": 0,
        "ok_consecutivos_criticos": 0,
        "opening_area": int(np.count_nonzero(opening_repair > 0)),
        "opening_area_ref": "",
        "opening_area_ratio_ref": "1.000000",
        "floor_area_bruto": int(np.count_nonzero(floor > 0)),
        "floor_area_filtrado": int(np.count_nonzero(floor > 0)),
        "expected_overlap_ratio": "0.000000",
        "filtered_vs_raw_ratio": "1.000000",
        "divergencia_pp": "0.000000",
        "suspeita_opening_borda": "False",
        "suspeita_opening_area": "False",
        "suspeita_floor_excessivo": "False",
        "suspeita_floor_quase_zero": "True",
        "suspeita_divergencia_bruto_filtrado": "False",
        "suspeita_expected_overlap_baixo": "False",
        "suspeita_floor_filtrado_colapsou": "False",
        "materiais_detectados_raw": materiais_detectados_raw,
        "deteccoes_contaminantes_json": deteccoes_contaminantes_json,
        "contaminantes_detectados": cont_result["contaminantes_detectados"],
        "alerta_contaminacao": cont_result["alerta_contaminacao"],
        "tipo_contaminacao": cont_result["tipo_contaminacao"],
        "severidade_contaminacao": cont_result["severidade_contaminacao"],
        "cacamba_esperada": cont_result["cacamba_esperada"],
        "material_esperado": cont_result["material_esperado"],
    })

    row = sanitize_row_final(row)
    return row


def main():
    csv_path = CSV_DIR / "resultado_volumetria.csv"
    resumo_path = CSV_DIR / "dashboard_resumo.csv"
    run_info_path = CSV_DIR / "run_info.json"
    repair_audit_path = CSV_DIR / "opening_repair_audit.csv"
    repair_audit_rows = []

    repair_debug_dir = DEBUG_DIR / "opening_repair"
    repair_debug_dir.mkdir(parents=True, exist_ok=True)

    existing_rows = load_existing_rows(csv_path)
    processed_names = {r["arquivo"] for r in existing_rows if r.get("arquivo")}

    segmentador = SegmentadorVolumetria()
    segmentador_contaminantes = SegmentadorContaminantes()
    human_detector = build_human_detector()

    image_files = sorted([p for p in INPUT_DIR.glob("*") if p.suffix.lower() in VALID_EXTS])
    if not image_files:
        print("Nenhuma imagem encontrada em:", INPUT_DIR)
        return

    new_image_files = [p for p in image_files if p.name not in processed_names]

    print(f"TOTAL INPUT = {len(image_files)}")
    print(f"JA PROCESSADAS = {len(processed_names)}")
    print(f"NOVAS = {len(new_image_files)}")

    if not new_image_files:
        write_rows(csv_path, existing_rows)
        write_dashboard(resumo_path, existing_rows)

        run_info = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "mode": "incremental",
            "model_path": str(MODEL_PATH),
            "input_dir": str(INPUT_DIR),
            "total_imagens_input": len(image_files),
            "ja_processadas": len(processed_names),
            "novas_processadas": 0,
            "total_rows_csv": len(existing_rows),
            "csv_resultado": str(csv_path),
            "csv_dashboard": str(resumo_path),
            "opening_repair_audit_csv": str(repair_audit_path),
            "debug_dir": str(DEBUG_DIR),
            "opening_repair_debug_dir": str(repair_debug_dir),
            "masks_opening_dir": str(OPENING_MASK_DIR),
            "masks_floor_dir": str(FLOOR_MASK_DIR),
            "masks_wall_dir": str(WALL_MASK_DIR),
            "contaminantes_modelo_ativo": segmentador_contaminantes.ativo,
            "human_gate_ativo": True,
            "overflow_detector_ativo": True,
            "observacao": "Nenhuma imagem nova encontrada.",
        }

        with open(run_info_path, "w", encoding="utf-8") as f:
            json.dump(run_info, f, ensure_ascii=False, indent=2)

        print("Nenhuma imagem nova encontrada. Dashboard e run_info atualizados.")
        return

    stage = []
    for img_path in new_image_files:
        img, opening_mask, floor_mask, wall_mask = segmentador.segmentar(img_path)

        segmentador.salvar_mask(opening_mask, OPENING_MASK_DIR / f"{img_path.stem}.png")
        segmentador.salvar_mask(floor_mask, FLOOR_MASK_DIR / f"{img_path.stem}.png")
        segmentador.salvar_mask(wall_mask, WALL_MASK_DIR / f"{img_path.stem}.png")

        stage.append(
            (
                img_path,
                img,
                (opening_mask * 255).astype("uint8"),
                (floor_mask * 255).astype("uint8"),
                (wall_mask * 255).astype("uint8"),
            )
        )

    print("OPENING_AREA_REF = DESABILITADO")

    new_rows = []
    ok_consec_criticos_by_group = build_previous_critical_counters(existing_rows)

    for img_path, img, opening, floor, wall in stage:
        name = img_path.stem
        grupo = detect_group(name)

        cont_pred = segmentador_contaminantes.inferir(str(img_path))

        materiais_relevantes = cont_pred.get("materiais_relevantes", []) or []
        materiais_detectados = cont_pred.get("materiais_detectados", []) or []
        areas_ratio = cont_pred.get("areas_ratio", {}) or {}
        deteccoes = cont_pred.get("deteccoes", []) or []

        materiais_para_contaminacao = []
        for nome_mat in materiais_relevantes + materiais_detectados:
            if nome_mat not in materiais_para_contaminacao:
                materiais_para_contaminacao.append(nome_mat)

        cont_result = avaliar_contaminacao(grupo, materiais_para_contaminacao)

        raw_parts = []

        if areas_ratio:
            raw_parts.extend(
                f"{k}:{float(v):.3f}"
                for k, v in sorted(areas_ratio.items(), key=lambda x: x[1], reverse=True)
            )

        classes_sem_area = [c for c in materiais_detectados if c not in areas_ratio]
        raw_parts.extend([f"{c}:fraco" for c in classes_sem_area])

        materiais_detectados_raw = ",".join(raw_parts) if raw_parts else ""

        deteccoes_contaminantes_json = json.dumps(
            {
                "materiais_relevantes": materiais_relevantes,
                "materiais_detectados": materiais_detectados,
                "areas_ratio": areas_ratio,
                "deteccoes": deteccoes,
            },
            ensure_ascii=False
        )

        human_dets = detectar_humanos(human_detector, img)
        human_hit, human_info = humano_intersecta_abertura(human_dets, opening)

        if human_hit:
            dbg = render_debug_humano(img, opening, human_info)
            cv2.imwrite(str(DEBUG_DIR / f"{name}_debug.jpg"), dbg)

            row = normalize_row({
                "arquivo": img_path.name,
                "grupo": grupo,
                "classe_predita": "",
                "status_frame": "suspeito",
                "motivo_falha": "humano_na_abertura",
                "confidence_final": "0.00",
                "fill_percent_filtrado": "",
                "estado_dashboard": "revisar",
                "fill_temporal": "",
                "estado_dashboard_temporal": "revisar",
                "alerta_dashboard": 0,
                "ok_consecutivos_criticos": 0,
                "opening_area": 0,
                "opening_area_ref": "",
                "opening_area_ratio_ref": "",
                "floor_area_bruto": 0,
                "floor_area_filtrado": 0,
                "expected_overlap_ratio": "",
                "filtered_vs_raw_ratio": "",
                "divergencia_pp": "",
                "suspeita_opening_borda": "",
                "suspeita_opening_area": "",
                "suspeita_floor_excessivo": "",
                "suspeita_floor_quase_zero": "",
                "suspeita_divergencia_bruto_filtrado": "",
                "suspeita_expected_overlap_baixo": "",
                "suspeita_floor_filtrado_colapsou": "",
                "materiais_detectados_raw": materiais_detectados_raw,
                "deteccoes_contaminantes_json": deteccoes_contaminantes_json,
                "contaminantes_detectados": cont_result["contaminantes_detectados"],
                "alerta_contaminacao": cont_result["alerta_contaminacao"],
                "tipo_contaminacao": cont_result["tipo_contaminacao"],
                "severidade_contaminacao": cont_result["severidade_contaminacao"],
                "cacamba_esperada": cont_result["cacamba_esperada"],
                "material_esperado": cont_result["material_esperado"],
            })
            row = sanitize_row_final(row)
            new_rows.append(row)

            print(
                f"{img_path.name} -> grupo={grupo} | status=suspeito | "
                f"fill= | estado=revisar | ok_consec=0 | alerta=0 | "
                f"motivo=humano_na_abertura | materiais={materiais_detectados_raw if materiais_detectados_raw else 'nenhum'} | "
                f"alerta_contam={cont_result['alerta_contaminacao']} | "
                f"tipo_contam={cont_result['tipo_contaminacao'] if cont_result['tipo_contaminacao'] else 'nenhum'}"
            )
            continue

        opening_raw = opening.copy()
        opening_repair, repair_info = reparar_opening_fragmentada(opening_raw, wall)

        op_stats_dbg = _mask_stats((opening_raw > 0).astype(np.uint8) * 255)
        op_after_stats_dbg = _mask_stats((opening_repair > 0).astype(np.uint8) * 255)
        wall_stats_dbg = _mask_stats(_largest_component(wall))

        width_rel_vs_wall_dbg = 0.0
        area_rel_vs_wall_dbg = 0.0
        cx_local_dbg = 0.0
        width_rel_vs_wall_after_dbg = 0.0
        area_rel_vs_wall_after_dbg = 0.0
        cx_local_after_dbg = 0.0

        if wall_stats_dbg["bbox"] is not None and wall_stats_dbg["bbox_w"] > 0:
            wall_x1_dbg, _, _, _ = wall_stats_dbg["bbox"]
            width_rel_vs_wall_dbg = op_stats_dbg["bbox_w"] / float(max(1, wall_stats_dbg["bbox_w"]))
            area_rel_vs_wall_dbg = op_stats_dbg["area"] / float(max(1, wall_stats_dbg["area"]))
            cx_local_dbg = (op_stats_dbg["cx"] - wall_x1_dbg) / float(max(1, wall_stats_dbg["bbox_w"]))

            width_rel_vs_wall_after_dbg = op_after_stats_dbg["bbox_w"] / float(max(1, wall_stats_dbg["bbox_w"]))
            area_rel_vs_wall_after_dbg = op_after_stats_dbg["area"] / float(max(1, wall_stats_dbg["area"]))
            cx_local_after_dbg = (op_after_stats_dbg["cx"] - wall_x1_dbg) / float(max(1, wall_stats_dbg["bbox_w"]))

        repair_audit_rows.append({
            "arquivo": img_path.name,
            "grupo": grupo,
            "opening_area": op_stats_dbg["area"],
            "opening_bbox_w": op_stats_dbg["bbox_w"],
            "opening_area_after": op_after_stats_dbg["area"],
            "opening_bbox_w_after": op_after_stats_dbg["bbox_w"],
            "wall_area": wall_stats_dbg["area"],
            "wall_bbox_w": wall_stats_dbg["bbox_w"],
            "width_rel_vs_wall": f"{width_rel_vs_wall_dbg:.6f}",
            "area_rel_vs_wall": f"{area_rel_vs_wall_dbg:.6f}",
            "cx_local": f"{cx_local_dbg:.6f}",
            "width_rel_vs_wall_after": f"{width_rel_vs_wall_after_dbg:.6f}",
            "area_rel_vs_wall_after": f"{area_rel_vs_wall_after_dbg:.6f}",
            "cx_local_after": f"{cx_local_after_dbg:.6f}",
            "repair_aplicado": int(bool(repair_info["aplicado"])),
            "repair_kind": repair_info.get("repair_kind", "none"),
            "repair_motivos": ",".join(repair_info["motivos"]),
        })

        if repair_info["aplicado"]:
            dbg_repair = render_debug_opening_repair(
                img,
                opening_raw,
                wall,
                opening_repair,
                repair_info,
            )
            cv2.imwrite(str(repair_debug_dir / f"{name}_opening_repair.jpg"), dbg_repair)

            print(
                f"{img_path.name} -> OPENING_REPAIR aplicado | "
                f"motivos={','.join(repair_info['motivos'])} | "
                f"area_before={repair_info['opening_area_before']} | "
                f"area_after={repair_info['opening_area_after']} | "
                f"bboxw_before={repair_info['bbox_w_before']} | "
                f"bboxw_after={repair_info['bbox_w_after']}"
            )

        # OVERFLOW PRÉ-MOTOR DESLIGADO
        # Estava engolindo baixas e médias.
        # Vamos manter somente o RESGATE PÓS-MOTOR mais abaixo.


        feats = extrair_features(opening_repair, floor, wall, None, None)
        if feats is None:
            row = normalize_row({
                "arquivo": img_path.name,
                "grupo": grupo,
                "classe_predita": "",
                "status_frame": "invalido",
                "motivo_falha": "sem_opening_inner_valido",
                "confidence_final": "0.00",
                "fill_percent_filtrado": "",
                "estado_dashboard": "invalido",
                "fill_temporal": "",
                "estado_dashboard_temporal": "invalido",
                "alerta_dashboard": 0,
                "ok_consecutivos_criticos": 0,
                "opening_area": 0,
                "opening_area_ref": "",
                "opening_area_ratio_ref": "",
                "floor_area_bruto": 0,
                "floor_area_filtrado": 0,
                "expected_overlap_ratio": "",
                "filtered_vs_raw_ratio": "",
                "divergencia_pp": "",
                "suspeita_opening_borda": "",
                "suspeita_opening_area": "",
                "suspeita_floor_excessivo": "",
                "suspeita_floor_quase_zero": "",
                "suspeita_divergencia_bruto_filtrado": "",
                "suspeita_expected_overlap_baixo": "",
                "suspeita_floor_filtrado_colapsou": "",
                "materiais_detectados_raw": materiais_detectados_raw,
                "deteccoes_contaminantes_json": deteccoes_contaminantes_json,
                "contaminantes_detectados": cont_result["contaminantes_detectados"],
                "alerta_contaminacao": cont_result["alerta_contaminacao"],
                "tipo_contaminacao": cont_result["tipo_contaminacao"],
                "severidade_contaminacao": cont_result["severidade_contaminacao"],
                "cacamba_esperada": cont_result["cacamba_esperada"],
                "material_esperado": cont_result["material_esperado"],
            })
            row = sanitize_row_final(row)
            new_rows.append(row)
            print(f"SEM OPENING INNER VALIDO: {img_path.name}")
            continue

        feats["grupo"] = grupo
        feats = sanitize_feats_for_dashboard(feats)

        # RESGATE FINAL: casos altos que ainda escaparam do detector de overflow
        # VERSAO TRAVADA:
        # - nao pode puxar caçamba vazia/baixa para 80-90%
        # - exige evidência estrutural forte de caçamba realmente alta
        # - nao mexe em contaminantes
        fill_tmp = float(feats.get("fill_percent_filtered", 0.0))
        suspeita_floor_qz = bool(feats.get("suspeita_floor_quase_zero", False))
        status_tmp = str(feats.get("status_frame", "")).strip().lower()

        opening_area_tmp = int(np.count_nonzero(opening_repair > 0))
        floor_area_tmp = int(np.count_nonzero(floor > 0))
        wall_area_tmp = int(np.count_nonzero(wall > 0))

        floor_vs_opening_tmp = (
            floor_area_tmp / float(opening_area_tmp)
            if opening_area_tmp > 0 else 0.0
        )
        wall_vs_opening_tmp = (
            wall_area_tmp / float(opening_area_tmp)
            if opening_area_tmp > 0 else 0.0
        )

        estrutura_tmp = floor_area_tmp + wall_area_tmp
        floor_share_tmp = (
            floor_area_tmp / float(estrutura_tmp)
            if estrutura_tmp > 0 else 0.0
        )
        wall_share_tmp = (
            wall_area_tmp / float(estrutura_tmp)
            if estrutura_tmp > 0 else 0.0
        )

        expected_overlap_tmp = float(feats.get("expected_overlap_ratio", 0.0))
        filtered_vs_raw_tmp = float(feats.get("filtered_vs_raw_ratio", 0.0))

        aciona_resgate_pos_motor = (
            status_tmp == "suspeito"
            and suspeita_floor_qz
            and fill_tmp <= 25.0
            and opening_area_tmp > 0
            and estrutura_tmp > 0
            and floor_vs_opening_tmp <= 0.06
            and floor_share_tmp <= 0.16
            and wall_share_tmp >= 0.84
            and wall_vs_opening_tmp >= 0.12
            and expected_overlap_tmp >= 0.02
            and filtered_vs_raw_tmp >= 0.02
        )

        if aciona_resgate_pos_motor:
            ganho = min(1.0, max(0.0, (wall_share_tmp - 0.84) / 0.12))
            fill_resgate = 80.0 + (10.0 * ganho)
            fill_resgate = min(90.0, max(fill_tmp, fill_resgate))

            overflow_rescue = {
                "overflow_detectado": True,
                "fill_estimado": float(fill_resgate),
                "confianca": 0.68,
                "motivo": "resgate_pos_motor_floor_quase_zero",
            }

            row = _build_overflow_row(
                img_path=img_path,
                img=img,
                name=name,
                grupo=grupo,
                opening_repair=opening_repair,
                floor=floor,
                wall=wall,
                overflow=overflow_rescue,
                cont_result=cont_result,
                materiais_detectados_raw=materiais_detectados_raw,
                deteccoes_contaminantes_json=deteccoes_contaminantes_json,
            )
            new_rows.append(row)

            print(
                f"{img_path.name} -> OVERFLOW RESGATE POS-MOTOR | grupo={grupo} | "
                f"fill_csv={row['fill_percent_filtrado']} | "
                f"status={row['status_frame']} | estado={row['estado_dashboard']} | "
                f"motivo={row['motivo_falha']} | "
                f"floor/open={floor_vs_opening_tmp:.4f} | wall/open={wall_vs_opening_tmp:.4f} | "
                f"floor_share={floor_share_tmp:.4f} | wall_share={wall_share_tmp:.4f} | "
                f"materiais={materiais_detectados_raw if materiais_detectados_raw else 'nenhum'}"
            )
            continue


        # RESGATE 2 DESATIVADO
        # Auditoria visual mostrou que estava promovendo casos baixos para
        # fills altos artificiais. Reprovado para baseline atual.

        opening_area_tmp = int(np.count_nonzero(opening_repair > 0))
        floor_area_tmp = int(np.count_nonzero(floor > 0))
        wall_area_tmp = int(np.count_nonzero(wall > 0))

        floor_vs_opening_tmp = (
            floor_area_tmp / float(opening_area_tmp)
            if opening_area_tmp > 0 else 0.0
        )
        wall_vs_opening_tmp = (
            wall_area_tmp / float(opening_area_tmp)
            if opening_area_tmp > 0 else 0.0
        )
        estrutura_tmp = floor_area_tmp + wall_area_tmp

        floor_share_tmp = (
            floor_area_tmp / float(estrutura_tmp)
            if estrutura_tmp > 0 else 0.0
        )
        wall_share_tmp = (
            wall_area_tmp / float(estrutura_tmp)
            if estrutura_tmp > 0 else 0.0
        )

        expected_overlap_tmp = float(feats.get("expected_overlap_ratio", 0.0) or 0.0)
        filtered_vs_raw_tmp = float(feats.get("filtered_vs_raw_ratio", 0.0) or 0.0)

        classe_motor_tmp = str(feats.get("classe", "")).strip().lower()

        # trava correta:
        # nao basta "ter plastico em algum lugar"; o grupo precisa ser plastico
        eh_plastico_alvo_tmp = (grupo == "plastico")

        aciona_resgate_2 = False

        if aciona_resgate_2:
            ganho_wall = min(1.0, max(0.0, (wall_share_tmp - 0.78) / 0.12))
            ganho_floor = min(1.0, max(0.0, (0.20 - floor_vs_opening_tmp) / 0.10))
            ganho_mix = max(ganho_wall, ganho_floor)

            fill_rescue_2 = 58.0 + (12.0 * ganho_mix)
            fill_rescue_2 = max(fill_tmp, min(fill_rescue_2, 70.0))

            feats["fill_percent_filtered"] = fill_rescue_2
            feats["fill_temporal"] = fill_rescue_2
            feats["classe"] = feats.get("classe", "media")

            motivo_existente = str(feats.get("motivo_falha", "")).strip()
            if motivo_existente:
                feats["motivo_falha"] = motivo_existente + "|resgate2_ok_baixo_visual_alto"
            else:
                feats["motivo_falha"] = "resgate2_ok_baixo_visual_alto"

            print(
                f"{img_path.name} -> RESGATE 2 POS-MOTOR | grupo={grupo} | "
                f"classe_motor={classe_motor_tmp} | "
                f"fill_antigo={fill_tmp:.2f} | fill_novo={fill_rescue_2:.2f} | "
                f"opening={opening_area_tmp} | floor={floor_area_tmp} | wall={wall_area_tmp} | "
                f"wall_share={wall_share_tmp:.3f} | floor_vs_opening={floor_vs_opening_tmp:.3f}"
            )

            fill_tmp = fill_rescue_2

        motivo_falha_existente = str(feats.get("motivo_falha", "")).strip()
        motivo_falha = ""

        if feats["status_frame"] == "invalido":
            if feats["suspeita_expected_overlap_baixo"]:
                motivo_falha = "expected_overlap_baixo"
            elif feats["suspeita_floor_filtrado_colapsou"]:
                motivo_falha = "floor_filtrado_colapsou"
            elif feats["suspeita_opening_area"]:
                motivo_falha = "opening_area_fora_ref"
            elif feats["suspeita_opening_borda"]:
                motivo_falha = "opening_toca_borda"
            elif feats["suspeita_floor_quase_zero"]:
                motivo_falha = "floor_quase_zero"
            else:
                motivo_falha = "invalido_generico"

        elif feats["status_frame"] == "suspeito":
            if feats["suspeita_expected_overlap_baixo"]:
                motivo_falha = "suspeito_overlap"
            elif feats["suspeita_floor_filtrado_colapsou"]:
                motivo_falha = "suspeito_colapso_filtro"
            elif feats["suspeita_opening_area"]:
                motivo_falha = "suspeito_opening_area"
            elif feats["suspeita_opening_borda"]:
                motivo_falha = "suspeito_borda"
            elif feats["suspeita_floor_quase_zero"]:
                motivo_falha = "suspeito_floor_quase_zero"
            else:
                motivo_falha = "suspeito_generico"

        if motivo_falha:
            feats["motivo_falha"] = motivo_falha
        else:
            feats["motivo_falha"] = motivo_falha_existente

        fill = feats["fill_percent_filtered"]

        if feats["status_frame"] == "ok":
            estado_dashboard = estado_dashboard_from_fill(fill)
        elif feats["status_frame"] == "suspeito":
            estado_dashboard = "revisar"
        else:
            estado_dashboard = "invalido"

        if grupo not in ok_consec_criticos_by_group:
            ok_consec_criticos_by_group[grupo] = 0

        if feats["status_frame"] == "ok" and fill >= ALERTA_VERMELHO:
            ok_consec_criticos_by_group[grupo] += 1
        else:
            ok_consec_criticos_by_group[grupo] = 0

        ok_consecutivos_criticos = ok_consec_criticos_by_group[grupo]

        alerta_dashboard = 1 if (
            feats["status_frame"] == "ok"
            and ok_consecutivos_criticos >= CONSEC_OK_PARA_TROCA
        ) else 0

        feats["estado_dashboard"] = estado_dashboard
        feats["alerta_dashboard"] = alerta_dashboard
        feats["ok_consecutivos_criticos"] = ok_consecutivos_criticos
        feats["fill_temporal"] = fill
        feats["estado_dashboard_temporal"] = estado_dashboard

        dbg = render_debug(img, feats)
        cv2.imwrite(str(DEBUG_DIR / f"{name}_debug.jpg"), dbg)

        row = normalize_row({
            "arquivo": img_path.name,
            "grupo": grupo,
            "classe_predita": feats["classe"],
            "status_frame": feats["status_frame"],
            "motivo_falha": feats["motivo_falha"],
            "confidence_final": f"{feats['confidence_final']:.2f}",
            "fill_percent_filtrado": f"{feats['fill_percent_filtered']:.6f}",
            "estado_dashboard": feats["estado_dashboard"],
            "fill_temporal": f"{feats['fill_temporal']:.6f}",
            "estado_dashboard_temporal": feats["estado_dashboard_temporal"],
            "alerta_dashboard": feats["alerta_dashboard"],
            "ok_consecutivos_criticos": feats["ok_consecutivos_criticos"],
            "opening_area": feats["opening_area"],
            "opening_area_ref": "",
            "opening_area_ratio_ref": f"{feats['opening_area_ratio_ref']:.6f}",
            "floor_area_bruto": feats["floor_area_raw"],
            "floor_area_filtrado": feats["floor_area_filtered"],
            "expected_overlap_ratio": f"{feats['expected_overlap_ratio']:.6f}",
            "filtered_vs_raw_ratio": f"{feats['filtered_vs_raw_ratio']:.6f}",
            "divergencia_pp": f"{feats['divergencia_pp']:.6f}",
            "suspeita_opening_borda": str(feats["suspeita_opening_borda"]),
            "suspeita_opening_area": str(feats["suspeita_opening_area"]),
            "suspeita_floor_excessivo": str(feats["suspeita_floor_excessivo"]),
            "suspeita_floor_quase_zero": str(feats["suspeita_floor_quase_zero"]),
            "suspeita_divergencia_bruto_filtrado": str(feats["suspeita_divergencia_bruto_filtrado"]),
            "suspeita_expected_overlap_baixo": str(feats["suspeita_expected_overlap_baixo"]),
            "suspeita_floor_filtrado_colapsou": str(feats["suspeita_floor_filtrado_colapsou"]),
            "materiais_detectados_raw": materiais_detectados_raw,
            "deteccoes_contaminantes_json": deteccoes_contaminantes_json,
            "contaminantes_detectados": cont_result["contaminantes_detectados"],
            "alerta_contaminacao": cont_result["alerta_contaminacao"],
            "tipo_contaminacao": cont_result["tipo_contaminacao"],
            "severidade_contaminacao": cont_result["severidade_contaminacao"],
            "cacamba_esperada": cont_result["cacamba_esperada"],
            "material_esperado": cont_result["material_esperado"],
        })
        row = sanitize_row_final(row)
        new_rows.append(row)

        print(
            f"{img_path.name} -> grupo={grupo} | status={row['status_frame']} | "
            f"fill_csv={row['fill_percent_filtrado'] if row['fill_percent_filtrado'] != '' else 'VAZIO'} | "
            f"estado={row['estado_dashboard']} | "
            f"ok_consec={ok_consecutivos_criticos} | alerta={row['alerta_dashboard']} | "
            f"motivo={row['motivo_falha']} | "
            f"materiais={materiais_detectados_raw if materiais_detectados_raw else 'nenhum'}"
        )

    all_rows = merge_rows(existing_rows, new_rows)

    write_rows(csv_path, all_rows)
    write_dashboard(resumo_path, all_rows)

    with open(repair_audit_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "arquivo",
                "grupo",
                "opening_area",
                "opening_bbox_w",
                "opening_area_after",
                "opening_bbox_w_after",
                "wall_area",
                "wall_bbox_w",
                "width_rel_vs_wall",
                "area_rel_vs_wall",
                "cx_local",
                "width_rel_vs_wall_after",
                "area_rel_vs_wall_after",
                "cx_local_after",
                "repair_aplicado",
                "repair_kind",
                "repair_motivos",
            ],
        )
        writer.writeheader()
        writer.writerows(repair_audit_rows)

    run_info = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "mode": "incremental",
        "model_path": str(MODEL_PATH),
        "input_dir": str(INPUT_DIR),
        "total_imagens_input": len(image_files),
        "ja_processadas_antes": len(processed_names),
        "novas_processadas": len(new_rows),
        "total_rows_csv": len(all_rows),
        "csv_resultado": str(csv_path),
        "csv_dashboard": str(resumo_path),
        "opening_repair_audit_csv": str(repair_audit_path),
        "debug_dir": str(DEBUG_DIR),
        "opening_repair_debug_dir": str(repair_debug_dir),
        "masks_opening_dir": str(OPENING_MASK_DIR),
        "masks_floor_dir": str(FLOOR_MASK_DIR),
        "masks_wall_dir": str(WALL_MASK_DIR),
        "contaminantes_modelo_ativo": segmentador_contaminantes.ativo,
        "human_gate_ativo": True,
        "overflow_detector_ativo": True,
    }

    with open(run_info_path, "w", encoding="utf-8") as f:
        json.dump(run_info, f, ensure_ascii=False, indent=2)

    print()
    print("CONCLUIDO")
    print("MODO: incremental")
    print("CSV:", csv_path)
    print("RESUMO:", resumo_path)
    print("RUN_INFO:", run_info_path)
    print("OPENING REPAIR AUDIT:", repair_audit_path)
    print("DEBUG:", DEBUG_DIR)
    print("DEBUG OPENING REPAIR:", repair_debug_dir)
    print("MASK OPENING:", OPENING_MASK_DIR)
    print("MASK FLOOR:", FLOOR_MASK_DIR)
    print("MASK WALL:", WALL_MASK_DIR)
    print(f"NOVAS PROCESSADAS: {len(new_rows)}")
    print(f"TOTAL NO CSV: {len(all_rows)}")


if __name__ == "__main__":
    main()