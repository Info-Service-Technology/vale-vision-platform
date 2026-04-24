import cv2
import numpy as np

from config import (
    ERODE_KERNEL,
    MIN_COMPONENT_AREA,
    MIN_OPENING_AREA,
    SUSPECT_FLOOR_RATIO,
    SUSPECT_FLOOR_ZERO_MAX,
    BORDER_TOUCH_MIN_PIXELS,
    BORDER_TOUCH_MIN_RATIO,
    ALERTA_AMARELO,
    ALERTA_VERMELHO,
)


def detect_group(name: str) -> str:
    low = name.lower()
    if low.startswith("madeira_"):
        return "madeira"
    if low.startswith("plastico_"):
        return "plastico"
    if low.startswith("sucata_"):
        return "sucata"
    return "sem_grupo"


def touches_image_border(mask_bin):
    if mask_bin is None or mask_bin.size == 0:
        return False

    border_pixels = np.concatenate([
        mask_bin[0, :].ravel(),
        mask_bin[-1, :].ravel(),
        mask_bin[:, 0].ravel(),
        mask_bin[:, -1].ravel(),
    ])

    border_count = int(np.count_nonzero(border_pixels))
    total_area = int(np.count_nonzero(mask_bin))

    if total_area <= 0:
        return False

    border_ratio = border_count / total_area

    return (
        border_count >= BORDER_TOUCH_MIN_PIXELS
        and border_ratio >= BORDER_TOUCH_MIN_RATIO
    )


def remove_small_components(mask_bin, min_area=MIN_COMPONENT_AREA):
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
        mask_bin, connectivity=8
    )

    if num_labels <= 1:
        return mask_bin.astype(np.uint8)

    cleaned = np.zeros_like(mask_bin, dtype=np.uint8)

    comps = []
    for label in range(1, num_labels):
        area = int(stats[label, cv2.CC_STAT_AREA])
        comps.append((label, area))

    comps.sort(key=lambda x: x[1], reverse=True)

    # Mais conservador: não matar fragmentos úteis finos
    effective_min = max(24, int(min_area * 0.35))
    kept = 0

    for label, area in comps:
        if area >= min_area:
            cleaned[labels == label] = 1
            kept += 1
            continue

        # mantém alguns componentes menores, desde que não sejam ruído muito pequeno
        if area >= effective_min and kept < 8:
            cleaned[labels == label] = 1
            kept += 1

    # fallback: se tudo morrer, mantém o maior componente
    if np.count_nonzero(cleaned) == 0 and comps:
        cleaned[labels == comps[0][0]] = 1

    return cleaned.astype(np.uint8)


def build_opening_inner_with_fallback(opening_bin):
    # menos agressivo já na limpeza da opening
    opening_clean = remove_small_components(
        opening_bin, max(40, int(MIN_COMPONENT_AREA * 0.25))
    )

    if np.count_nonzero(opening_clean) == 0:
        return None, 0, "falhou"

    # pequeno fechamento para recompor borda quebrada
    close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    opening_clean = cv2.morphologyEx(opening_clean, cv2.MORPH_CLOSE, close_kernel)

    raw_area = int(np.count_nonzero(opening_clean))
    if raw_area <= 0:
        return None, 0, "falhou"

    # erosões mais leves; se destruir demais, cai para raw_clean
    best_candidate = None
    best_area = 0
    best_method = "raw_clean"

    for k in [11, 7]:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
        candidate = cv2.erode(opening_clean, kernel, iterations=1)
        candidate = (candidate > 0).astype(np.uint8)
        area = int(np.count_nonzero(candidate))

        if area > best_area:
            best_candidate = candidate
            best_area = area
            best_method = f"erode_{k}"

        # aceita só se não encolher demais a opening
        if area >= MIN_OPENING_AREA and area >= int(raw_area * 0.72):
            return candidate.astype(np.uint8), area, f"erode_{k}"

    # preferir a opening limpa sem erosão forte
    if raw_area >= MIN_OPENING_AREA:
        return opening_clean.astype(np.uint8), raw_area, "raw_clean"

    if best_candidate is not None and best_area >= MIN_OPENING_AREA:
        return best_candidate.astype(np.uint8), best_area, best_method

    return None, 0, "falhou"


def classificar_fill_percent(fill_percent):
    if fill_percent < 15:
        return "vazia"
    elif fill_percent < 40:
        return "baixa"
    elif fill_percent < 75:
        return "media"
    elif fill_percent < 90:
        return "alta"
    return "critica"


def estado_dashboard_from_fill(fill_percent):
    if fill_percent >= ALERTA_VERMELHO:
        return "trocar_cacamba"
    elif fill_percent >= ALERTA_AMARELO:
        return "atencao"
    return "normal"


def compute_reference_opening_area(opening_masks):
    opening_areas = []

    for opening in opening_masks:
        opening_bin = (opening > 0).astype(np.uint8)

        if len(opening_bin.shape) == 3:
            opening_bin = opening_bin[:, :, 0]

        opening_inner, area, _ = build_opening_inner_with_fallback(opening_bin)
        if opening_inner is not None and area >= MIN_OPENING_AREA:
            opening_areas.append(area)

    if not opening_areas:
        return None

    return float(np.median(opening_areas))


def compute_confidence(feats):
    score = 100.0

    penalties = [
        "suspeita_opening_borda",
        "suspeita_floor_excessivo",
        "suspeita_floor_quase_zero",
    ]

    for key in penalties:
        if feats.get(key, False):
            score -= 18.0

    return max(0.0, min(100.0, score))


def define_status(feats, confidence_final):
    if feats["opening_area"] < MIN_OPENING_AREA:
        return "invalido"

    num_flags = sum(
        [
            int(feats["suspeita_opening_borda"]),
            int(feats["suspeita_floor_excessivo"]),
            int(feats["suspeita_floor_quase_zero"]),
        ]
    )

    if confidence_final < 40 or num_flags >= 3:
        return "invalido"

    if confidence_final < 85 or num_flags >= 1:
        return "suspeito"

    return "ok"


def extrair_features(opening, floor, wall=None, expected_floor_mask_base=None, opening_area_ref=None):
    opening_bin = (opening > 0).astype(np.uint8)
    floor_bin = (floor > 0).astype(np.uint8)

    if wall is None:
        wall_bin = np.zeros_like(floor_bin, dtype=np.uint8)
    else:
        wall_bin = (wall > 0).astype(np.uint8)

    if len(opening_bin.shape) == 3:
        opening_bin = opening_bin[:, :, 0]

    if len(floor_bin.shape) == 3:
        floor_bin = floor_bin[:, :, 0]

    if len(wall_bin.shape) == 3:
        wall_bin = wall_bin[:, :, 0]

    border_touch = touches_image_border(opening_bin)

    opening_inner, opening_area, opening_method = build_opening_inner_with_fallback(opening_bin)
    if opening_inner is None or opening_area < MIN_OPENING_AREA:
        return None

    floor_inner_raw = ((floor_bin > 0) & (opening_inner > 0)).astype(np.uint8)
    floor_inner_raw = remove_small_components(
        floor_inner_raw, max(24, int(MIN_COMPONENT_AREA * 0.30))
    )

    wall_inner_raw = ((wall_bin > 0) & (opening_inner > 0)).astype(np.uint8)
    wall_inner_raw = remove_small_components(
        wall_inner_raw, max(40, int(MIN_COMPONENT_AREA * 0.40))
    )

    visible_inner_raw = np.maximum(floor_inner_raw, wall_inner_raw).astype(np.uint8)
    visible_inner_raw = remove_small_components(
        visible_inner_raw, max(32, int(MIN_COMPONENT_AREA * 0.30))
    )

    floor_area_raw = int(np.count_nonzero(floor_inner_raw))
    wall_area_raw = int(np.count_nonzero(wall_inner_raw))
    visible_area_raw = int(np.count_nonzero(visible_inner_raw))

    floor_ratio_raw = floor_area_raw / opening_area if opening_area > 0 else 0.0
    visible_ratio_raw = visible_area_raw / opening_area if opening_area > 0 else 0.0
    visible_ratio_raw = max(0.0, min(1.0, visible_ratio_raw))

    expected_inside_opening = visible_inner_raw.copy()
    expected_overlap_ratio = 1.0

    floor_inner_filtered = visible_inner_raw.copy()
    floor_area_filtered = visible_area_raw
    filtered_vs_raw_ratio = 1.0

    fill_ratio_raw = 1.0 - visible_ratio_raw
    fill_ratio_raw = max(0.0, min(1.0, fill_ratio_raw))
    fill_percent_raw = fill_ratio_raw * 100.0

    fill_ratio_filtered = fill_ratio_raw
    fill_percent_filtered = fill_percent_raw

    suspeita_floor_excessivo = floor_ratio_raw >= SUSPECT_FLOOR_RATIO
    suspeita_floor_quase_zero = (
        fill_percent_filtered <= SUSPECT_FLOOR_ZERO_MAX * 100.0
    )
    suspeita_opening_borda = border_touch

    cheia_real_forte = (
        fill_percent_raw >= 97.0
        and visible_area_raw <= max(2500, int(opening_area * 0.015))
    )

    suspeita_opening_area = False
    opening_area_ratio_ref = 1.0
    divergencia_pp = 0.0
    suspeita_divergencia_bruto_filtrado = False
    suspeita_expected_overlap_baixo = False
    suspeita_floor_filtrado_colapsou = False

    classe = classificar_fill_percent(fill_percent_filtered)

    feats = {
        "opening_inner": opening_inner,
        "opening_method": opening_method,
        "expected_inside_opening": expected_inside_opening,
        "floor_inner_raw": floor_inner_raw,
        "wall_inner_raw": wall_inner_raw,
        "visible_inner_raw": visible_inner_raw,
        "floor_inner_filtered": floor_inner_filtered,
        "opening_area": opening_area,
        "opening_area_ref": 0.0,
        "opening_area_ratio_ref": opening_area_ratio_ref,
        "floor_area_raw": floor_area_raw,
        "wall_area_raw": wall_area_raw,
        "visible_area_raw": visible_area_raw,
        "floor_area_filtered": floor_area_filtered,
        "expected_overlap_ratio": expected_overlap_ratio,
        "filtered_vs_raw_ratio": filtered_vs_raw_ratio,
        "fill_ratio_raw": fill_ratio_raw,
        "fill_percent_raw": fill_percent_raw,
        "fill_ratio_filtered": fill_ratio_filtered,
        "fill_percent_filtered": fill_percent_filtered,
        "classe": classe,
        "suspeita_opening_borda": suspeita_opening_borda,
        "suspeita_opening_area": suspeita_opening_area,
        "suspeita_floor_excessivo": suspeita_floor_excessivo,
        "suspeita_floor_quase_zero": suspeita_floor_quase_zero,
        "suspeita_divergencia_bruto_filtrado": suspeita_divergencia_bruto_filtrado,
        "suspeita_expected_overlap_baixo": suspeita_expected_overlap_baixo,
        "suspeita_floor_filtrado_colapsou": suspeita_floor_filtrado_colapsou,
        "cheia_real_forte": cheia_real_forte,
        "divergencia_pp": divergencia_pp,
    }

    confidence_final = compute_confidence(feats)
    status_frame = define_status(feats, confidence_final)

    feats["confidence_final"] = confidence_final
    feats["status_frame"] = status_frame

    return feats


def render_debug(img, feats):
    dbg = img.copy()

    opening_inner = feats["opening_inner"]
    floor_inner_raw = feats["floor_inner_raw"]
    wall_inner_raw = feats.get("wall_inner_raw", np.zeros_like(floor_inner_raw))
    visible_inner_raw = feats.get("visible_inner_raw", floor_inner_raw)
    floor_inner_filtered = feats["floor_inner_filtered"]

    contours, _ = cv2.findContours(
        opening_inner, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    cv2.drawContours(dbg, contours, -1, (0, 255, 255), 2)

    blue = np.zeros_like(dbg)
    blue[:, :] = (255, 0, 0)
    mask_wall = wall_inner_raw.astype(bool)
    dbg[mask_wall] = cv2.addWeighted(dbg, 0.75, blue, 0.25, 0)[mask_wall]

    red = np.zeros_like(dbg)
    red[:, :] = (0, 0, 255)
    mask_floor = floor_inner_raw.astype(bool)
    dbg[mask_floor] = cv2.addWeighted(dbg, 0.75, red, 0.25, 0)[mask_floor]

    cyan = np.zeros_like(dbg)
    cyan[:, :] = (255, 255, 0)
    mask_visible = visible_inner_raw.astype(bool)
    dbg[mask_visible] = cv2.addWeighted(dbg, 0.82, cyan, 0.18, 0)[mask_visible]

    green = np.zeros_like(dbg)
    green[:, :] = (0, 255, 0)
    mask_filtered = floor_inner_filtered.astype(bool)
    dbg[mask_filtered] = cv2.addWeighted(dbg, 0.55, green, 0.45, 0)[mask_filtered]

    return dbg
