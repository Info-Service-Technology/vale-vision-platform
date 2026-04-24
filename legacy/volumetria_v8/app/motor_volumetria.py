import cv2
import numpy as np

from config import (
    EXPECTED_FLOOR_MASK_PATH,
    ERODE_KERNEL,
    MIN_COMPONENT_AREA,
    MIN_OPENING_AREA,
    SUSPECT_FLOOR_RATIO,
    SUSPECT_FLOOR_ZERO_MAX,
    SUSPECT_DIVERGENCE_PP,
    OPENING_AREA_TOLERANCE,
    MIN_EXPECTED_OVERLAP_RATIO,
    MIN_FILTERED_VS_RAW_RATIO,
    BORDER_TOUCH_MIN_PIXELS,
    BORDER_TOUCH_MIN_RATIO,
    ALERTA_AMARELO,
    ALERTA_VERMELHO,
)

# -------------------------------------------------------------------------
# Camada operacional conservadora, agora balanceada
# -------------------------------------------------------------------------
NUM_BANDS = 5
BAND_VISIBLE_MIN = 0.03

FRAGMENTED_MIN_COMPONENTS = 4
FRAGMENTED_LARGEST_MAX = 0.55

COHERENT_HIGH_FILL_RATIO_MAX = 0.035
COHERENT_STRONG_FILL_RATIO_MAX = 0.015

COHERENT_HIGH_BBOX_MAX = 0.16
COHERENT_STRONG_BBOX_MAX = 0.10

SEVERE_BBOX_MAX = 0.24


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
    cleaned = np.zeros_like(mask_bin)

    for label in range(1, num_labels):
        area = stats[label, cv2.CC_STAT_AREA]
        if area >= min_area:
            cleaned[labels == label] = 1

    return cleaned.astype(np.uint8)


def build_opening_inner_with_fallback(opening_bin):
    opening_clean = remove_small_components(opening_bin, MIN_COMPONENT_AREA)

    for k in [ERODE_KERNEL, 25, 11]:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
        candidate = cv2.erode(opening_clean, kernel, iterations=1)
        candidate = (candidate > 0).astype(np.uint8)
        area = int(np.count_nonzero(candidate))
        if area >= MIN_OPENING_AREA:
            return candidate, area, f"erode_{k}"

    raw_area = int(np.count_nonzero(opening_clean))
    if raw_area >= MIN_OPENING_AREA:
        return opening_clean.astype(np.uint8), raw_area, "raw_clean"

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


def load_expected_floor_mask():
    mask = cv2.imread(str(EXPECTED_FLOOR_MASK_PATH), cv2.IMREAD_GRAYSCALE)
    if mask is None:
        raise RuntimeError(
            f"Máscara esperada não encontrada: {EXPECTED_FLOOR_MASK_PATH}"
        )

    if len(mask.shape) == 3:
        mask = mask[:, :, 0]

    return (mask > 0).astype(np.uint8)


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


def compute_component_metrics(mask_bin):
    total_area = int(np.count_nonzero(mask_bin))
    if total_area <= 0:
        return {
            "num_components": 0,
            "largest_area": 0,
            "largest_ratio": 0.0,
        }

    num_labels, _, stats, _ = cv2.connectedComponentsWithStats(
        mask_bin.astype(np.uint8), connectivity=8
    )

    areas = []
    for label in range(1, num_labels):
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area > 0:
            areas.append(area)

    if not areas:
        return {
            "num_components": 0,
            "largest_area": 0,
            "largest_ratio": 0.0,
        }

    largest_area = max(areas)
    return {
        "num_components": len(areas),
        "largest_area": largest_area,
        "largest_ratio": largest_area / total_area if total_area > 0 else 0.0,
    }


def compute_mask_bbox_height_ratio(mask_bin, ref_mask):
    ys_ref = np.where(ref_mask > 0)[0]
    if ys_ref.size == 0:
        return 0.0

    ref_h = int(ys_ref.max() - ys_ref.min() + 1)
    if ref_h <= 0:
        return 0.0

    ys = np.where(mask_bin > 0)[0]
    if ys.size == 0:
        return 0.0

    h = int(ys.max() - ys.min() + 1)
    return h / ref_h


def compute_horizontal_band_coverages(floor_mask, ref_mask, num_bands=NUM_BANDS):
    ys = np.where(ref_mask > 0)[0]
    if ys.size == 0:
        return [0.0] * num_bands, 0, 0.0, 0.0, 0.0

    y_min = int(ys.min())
    y_max = int(ys.max()) + 1

    edges = np.linspace(y_min, y_max, num_bands + 1).astype(int)

    coverages = []
    for i in range(num_bands):
        y0 = int(edges[i])
        y1 = int(edges[i + 1])

        if y1 <= y0:
            coverages.append(0.0)
            continue

        ref_band = (ref_mask[y0:y1, :] > 0).astype(np.uint8)
        ref_area = int(np.count_nonzero(ref_band))
        if ref_area <= 0:
            coverages.append(0.0)
            continue

        floor_band = (
            (floor_mask[y0:y1, :] > 0) & (ref_mask[y0:y1, :] > 0)
        ).astype(np.uint8)
        floor_area = int(np.count_nonzero(floor_band))

        coverages.append(floor_area / ref_area)

    bands_with_floor = int(sum(1 for c in coverages if c >= BAND_VISIBLE_MIN))
    min_cov = min(coverages) if coverages else 0.0
    max_cov = max(coverages) if coverages else 0.0
    mean_cov = float(np.mean(coverages)) if coverages else 0.0

    return coverages, bands_with_floor, min_cov, max_cov, mean_cov


def compute_confidence(feats):
    score = 100.0

    if feats.get("suspeita_opening_borda", False):
        score -= 12.0

    if feats.get("suspeita_opening_area", False):
        score -= 10.0

    if feats.get("suspeita_floor_excessivo", False):
        score -= 10.0

    if feats.get("suspeita_divergencia_bruto_filtrado", False):
        score -= 12.0

    if feats.get("suspeita_expected_overlap_baixo", False):
        score -= 10.0

    if feats.get("suspeita_floor_filtrado_colapsou", False):
        if feats.get("coerencia_cheio_visual", False):
            score -= 4.0
        else:
            score -= 14.0

    # Piso quase zero não é suspeita forte se o padrão espacial estiver coerente com cheio.
    if feats.get("suspeita_floor_quase_zero", False):
        if feats.get("coerencia_cheio_visual", False):
            score -= 2.0
        else:
            score -= 8.0

    if feats.get("floor_fragmentado", False):
        score -= 8.0

    fill_geom = feats.get("fill_percent_filtered_geom", 0.0)

    if fill_geom >= ALERTA_VERMELHO:
        if feats.get("bands_with_floor", 0) >= 2:
            score -= 10.0
        elif feats.get("bands_with_floor", 0) == 1:
            score -= 4.0

        if feats.get("floor_bbox_height_ratio", 0.0) > SEVERE_BBOX_MAX:
            score -= 10.0
        elif feats.get("floor_bbox_height_ratio", 0.0) > COHERENT_HIGH_BBOX_MAX:
            score -= 4.0

        if feats.get("floor_num_components", 0) >= 4:
            score -= 10.0
        elif feats.get("floor_num_components", 0) >= 2:
            score -= 4.0

    return max(0.0, min(100.0, score))


def define_status(feats, confidence_final):
    if feats["opening_area"] < MIN_OPENING_AREA:
        return "invalido"

    # Só invalidar colapso do filtrado quando não houver coerência de cheio.
    if feats["suspeita_floor_filtrado_colapsou"] and not feats.get("coerencia_cheio_visual", False):
        return "invalido"

    num_flags = 0

    num_flags += int(feats["suspeita_opening_borda"])
    num_flags += int(feats["suspeita_opening_area"])
    num_flags += int(feats["suspeita_floor_excessivo"])
    num_flags += int(feats["suspeita_divergencia_bruto_filtrado"])
    num_flags += int(feats["suspeita_expected_overlap_baixo"])

    if feats["suspeita_floor_filtrado_colapsou"] and not feats.get("coerencia_cheio_visual", False):
        num_flags += 1

    if feats.get("floor_fragmentado", False):
        num_flags += 1

    # Piso quase zero só conta como flag quando NÃO existe coerência espacial de cheio.
    if feats["suspeita_floor_quase_zero"] and not feats.get("coerencia_cheio_visual", False):
        num_flags += 1

    fill_geom = feats.get("fill_percent_filtered_geom", 0.0)

    if fill_geom >= ALERTA_VERMELHO and feats.get("bands_with_floor", 0) >= 2:
        num_flags += 1

    if fill_geom >= ALERTA_VERMELHO and feats.get("floor_bbox_height_ratio", 0.0) > SEVERE_BBOX_MAX:
        num_flags += 1

    if confidence_final < 35 or num_flags >= 5:
        return "invalido"

    if confidence_final < 72 or num_flags >= 2:
        return "suspeito"

    return "ok"


def decide_operational_output(feats, confidence_final, status_frame):
    fill_geom = float(feats["fill_percent_filtered_geom"])

    coerencia_cheio_visual = bool(feats.get("coerencia_cheio_visual", False))
    coerencia_cheio_forte = bool(feats.get("coerencia_cheio_forte", False))
    ambiguidade_cheio_alta = bool(feats.get("ambiguidade_cheio_alta", False))

    fill_final = float(fill_geom)

    if status_frame == "invalido":
        estado_operacional = "invalido"
        fill_final = min(fill_final, 85.0)

    elif fill_geom >= ALERTA_VERMELHO:
        if coerencia_cheio_forte and confidence_final >= 82.0 and not ambiguidade_cheio_alta:
            # Continua conservador: frame isolado não vira trocar_cacamba.
            estado_operacional = "atencao"
            fill_final = min(max(fill_final, 95.0), 98.0)

        elif coerencia_cheio_visual and confidence_final >= 70.0 and not ambiguidade_cheio_alta:
            estado_operacional = "atencao"
            fill_final = min(max(fill_final, 92.0), 96.0)

        elif confidence_final >= 65.0 and not ambiguidade_cheio_alta:
            estado_operacional = "atencao"
            fill_final = min(max(fill_final, 90.0), 94.0)

        else:
            estado_operacional = "suspeito"
            fill_final = min(max(fill_final, 86.0), 91.0)

    elif fill_geom >= ALERTA_AMARELO:
        if status_frame == "ok":
            estado_operacional = "atencao"
            fill_final = fill_geom
        else:
            if confidence_final >= 70.0:
                estado_operacional = "atencao"
                fill_final = fill_geom
            else:
                estado_operacional = "suspeito"
                fill_final = fill_geom

    else:
        if status_frame == "suspeito":
            estado_operacional = "suspeito"
        else:
            estado_operacional = "normal"

    confianca_operacional = float(confidence_final)
    if ambiguidade_cheio_alta:
        confianca_operacional = max(0.0, confianca_operacional - 12.0)
    if feats.get("floor_fragmentado", False):
        confianca_operacional = max(0.0, confianca_operacional - 6.0)

    return {
        "fill_percent_final": fill_final,
        "fill_ratio_final": fill_final / 100.0,
        "estado_operacional": estado_operacional,
        "confianca_operacional": confianca_operacional,
        "evidencia_cheio_forte": coerencia_cheio_forte,
        "evidencia_cheio_moderada": coerencia_cheio_visual,
        "ambiguidade_cheio": ambiguidade_cheio_alta,
    }


def extrair_features(opening, floor, expected_floor_mask_base, opening_area_ref):
    opening_bin = (opening > 0).astype(np.uint8)
    floor_bin = (floor > 0).astype(np.uint8)

    if len(opening_bin.shape) == 3:
        opening_bin = opening_bin[:, :, 0]

    if len(floor_bin.shape) == 3:
        floor_bin = floor_bin[:, :, 0]

    if len(expected_floor_mask_base.shape) == 3:
        expected_floor_mask_base = expected_floor_mask_base[:, :, 0]

    border_touch = touches_image_border(opening_bin)

    opening_inner, opening_area, opening_method = build_opening_inner_with_fallback(opening_bin)
    if opening_inner is None or opening_area < MIN_OPENING_AREA:
        return None

    h, w = opening_inner.shape[:2]
    expected_floor_mask = expected_floor_mask_base

    if expected_floor_mask.shape[:2] != (h, w):
        expected_floor_mask = cv2.resize(
            expected_floor_mask.astype(np.uint8),
            (w, h),
            interpolation=cv2.INTER_NEAREST,
        )
        expected_floor_mask = (expected_floor_mask > 0).astype(np.uint8)

    floor_inner_raw = ((floor_bin > 0) & (opening_inner > 0)).astype(np.uint8)
    floor_inner_raw = remove_small_components(floor_inner_raw, MIN_COMPONENT_AREA)

    floor_area_raw = int(np.count_nonzero(floor_inner_raw))
    floor_ratio_raw = floor_area_raw / opening_area if opening_area > 0 else 0.0

    expected_inside_opening = (
        (expected_floor_mask > 0) & (opening_inner > 0)
    ).astype(np.uint8)
    expected_overlap_area = int(np.count_nonzero(expected_inside_opening))
    expected_overlap_ratio = (
        expected_overlap_area / opening_area if opening_area > 0 else 0.0
    )

    floor_inner_filtered = (
        (floor_inner_raw > 0) & (expected_inside_opening > 0)
    ).astype(np.uint8)
    floor_inner_filtered = remove_small_components(
        floor_inner_filtered, MIN_COMPONENT_AREA
    )

    floor_area_filtered = int(np.count_nonzero(floor_inner_filtered))
    floor_ratio_filtered = floor_area_filtered / opening_area if opening_area > 0 else 0.0

    filtered_vs_raw_ratio = (
        floor_area_filtered / floor_area_raw if floor_area_raw > 0 else 1.0
    )

    fill_ratio_raw_geom = 1.0 - floor_ratio_raw
    fill_ratio_raw_geom = max(0.0, min(1.0, fill_ratio_raw_geom))
    fill_percent_raw_geom = fill_ratio_raw_geom * 100.0

    fill_ratio_filtered_geom = 1.0 - floor_ratio_filtered
    fill_ratio_filtered_geom = max(0.0, min(1.0, fill_ratio_filtered_geom))
    fill_percent_filtered_geom = fill_ratio_filtered_geom * 100.0

    component_metrics = compute_component_metrics(floor_inner_filtered)
    floor_num_components = component_metrics["num_components"]
    largest_component_area = component_metrics["largest_area"]
    largest_component_ratio = component_metrics["largest_ratio"]

    floor_bbox_height_ratio = compute_mask_bbox_height_ratio(
        floor_inner_filtered, expected_inside_opening
    )

    band_coverages, bands_with_floor, band_min_cov, band_max_cov, band_mean_cov = (
        compute_horizontal_band_coverages(
            floor_inner_filtered, expected_inside_opening, NUM_BANDS
        )
    )

    floor_fragmentado = (
        floor_num_components >= FRAGMENTED_MIN_COMPONENTS
        and largest_component_ratio < FRAGMENTED_LARGEST_MAX
    )

    suspeita_floor_excessivo = floor_ratio_raw >= SUSPECT_FLOOR_RATIO
    suspeita_floor_quase_zero = floor_ratio_filtered <= SUSPECT_FLOOR_ZERO_MAX
    suspeita_opening_borda = border_touch

    cheia_real_forte = (
        fill_percent_raw_geom >= 97.0
        and floor_area_raw <= max(2500, int(opening_area * 0.015))
    )

    if opening_area_ref is None or opening_area_ref <= 0:
        suspeita_opening_area = False
        opening_area_ratio_ref = 1.0
    else:
        opening_area_ratio_ref = opening_area / opening_area_ref
        suspeita_opening_area = not (
            (1.0 - OPENING_AREA_TOLERANCE)
            <= opening_area_ratio_ref
            <= (1.0 + OPENING_AREA_TOLERANCE)
        )

    divergencia_pp = abs(fill_percent_filtered_geom - fill_percent_raw_geom)
    suspeita_divergencia_bruto_filtrado = (
        divergencia_pp >= SUSPECT_DIVERGENCE_PP
    )

    suspeita_expected_overlap_baixo = (
        expected_overlap_ratio < MIN_EXPECTED_OVERLAP_RATIO
    )

    suspeita_floor_filtrado_colapsou = (
        floor_area_raw > 0 and filtered_vs_raw_ratio < MIN_FILTERED_VS_RAW_RATIO
    )

    # ---------------------------------------------------------------------
    # Nova coerência espacial de cheio
    # ---------------------------------------------------------------------
    coerencia_cheio_visual = (
        fill_percent_filtered_geom >= ALERTA_VERMELHO
        and floor_ratio_filtered <= COHERENT_HIGH_FILL_RATIO_MAX
        and bands_with_floor <= 1
        and floor_bbox_height_ratio <= COHERENT_HIGH_BBOX_MAX
        and floor_num_components <= 2
        and not floor_fragmentado
        and filtered_vs_raw_ratio >= 0.45
    )

    coerencia_cheio_forte = (
        fill_percent_filtered_geom >= 97.0
        and floor_ratio_filtered <= COHERENT_STRONG_FILL_RATIO_MAX
        and bands_with_floor == 0
        and floor_bbox_height_ratio <= COHERENT_STRONG_BBOX_MAX
        and floor_num_components <= 1
        and not floor_fragmentado
        and filtered_vs_raw_ratio >= 0.75
        and divergencia_pp <= 5.0
    )

    ambiguidade_cheio_alta = (
        fill_percent_filtered_geom >= ALERTA_VERMELHO
        and (
            bands_with_floor >= 2
            or floor_bbox_height_ratio > SEVERE_BBOX_MAX
            or floor_num_components >= 4
            or floor_fragmentado
            or filtered_vs_raw_ratio < 0.30
            or expected_overlap_ratio < MIN_EXPECTED_OVERLAP_RATIO
            or divergencia_pp >= 12.0
        )
    )

    # Se houver uma coerência espacial boa de cheio, "piso quase zero" deixa de ser suspeita forte.
    if coerencia_cheio_visual:
        suspeita_floor_quase_zero = False

    # Se for cheio forte no bruto, overlap baixo deixa de ser sinal importante.
    if cheia_real_forte:
        suspeita_expected_overlap_baixo = False

    classe_geom = classificar_fill_percent(fill_percent_filtered_geom)

    feats = {
        "opening_inner": opening_inner,
        "opening_method": opening_method,
        "expected_inside_opening": expected_inside_opening,
        "floor_inner_raw": floor_inner_raw,
        "floor_inner_filtered": floor_inner_filtered,
        "opening_area": opening_area,
        "opening_area_ref": opening_area_ref if opening_area_ref is not None else 0.0,
        "opening_area_ratio_ref": opening_area_ratio_ref,
        "floor_area_raw": floor_area_raw,
        "floor_area_filtered": floor_area_filtered,
        "floor_ratio_raw": floor_ratio_raw,
        "floor_ratio_filtered": floor_ratio_filtered,
        "expected_overlap_ratio": expected_overlap_ratio,
        "filtered_vs_raw_ratio": filtered_vs_raw_ratio,
        "fill_ratio_raw_geom": fill_ratio_raw_geom,
        "fill_percent_raw_geom": fill_percent_raw_geom,
        "fill_ratio_filtered_geom": fill_ratio_filtered_geom,
        "fill_percent_filtered_geom": fill_percent_filtered_geom,
        "fill_ratio_raw": fill_ratio_raw_geom,
        "fill_percent_raw": fill_percent_raw_geom,
        "classe_geom": classe_geom,
        "floor_num_components": floor_num_components,
        "largest_component_area": largest_component_area,
        "largest_component_ratio": largest_component_ratio,
        "floor_bbox_height_ratio": floor_bbox_height_ratio,
        "band_coverages": band_coverages,
        "band_1_coverage": band_coverages[0] if len(band_coverages) > 0 else 0.0,
        "band_2_coverage": band_coverages[1] if len(band_coverages) > 1 else 0.0,
        "band_3_coverage": band_coverages[2] if len(band_coverages) > 2 else 0.0,
        "band_4_coverage": band_coverages[3] if len(band_coverages) > 3 else 0.0,
        "band_5_coverage": band_coverages[4] if len(band_coverages) > 4 else 0.0,
        "bands_with_floor": bands_with_floor,
        "band_min_cov": band_min_cov,
        "band_max_cov": band_max_cov,
        "band_mean_cov": band_mean_cov,
        "floor_fragmentado": floor_fragmentado,
        "suspeita_opening_borda": suspeita_opening_borda,
        "suspeita_opening_area": suspeita_opening_area,
        "suspeita_floor_excessivo": suspeita_floor_excessivo,
        "suspeita_floor_quase_zero": suspeita_floor_quase_zero,
        "suspeita_divergencia_bruto_filtrado": suspeita_divergencia_bruto_filtrado,
        "suspeita_expected_overlap_baixo": suspeita_expected_overlap_baixo,
        "suspeita_floor_filtrado_colapsou": suspeita_floor_filtrado_colapsou,
        "cheia_real_forte": cheia_real_forte,
        "coerencia_cheio_visual": coerencia_cheio_visual,
        "coerencia_cheio_forte": coerencia_cheio_forte,
        "ambiguidade_cheio_alta": ambiguidade_cheio_alta,
        "evidencia_cheio_forte": coerencia_cheio_forte,
        "divergencia_pp": divergencia_pp,
    }

    confidence_final = compute_confidence(feats)
    status_frame = define_status(feats, confidence_final)

    saida_operacional = decide_operational_output(
        feats, confidence_final, status_frame
    )

    fill_percent_final = saida_operacional["fill_percent_final"]
    fill_ratio_final = saida_operacional["fill_ratio_final"]
    classe_final = classificar_fill_percent(fill_percent_final)

    feats["confidence_final"] = confidence_final
    feats["status_frame"] = status_frame

    feats["confianca_operacional"] = saida_operacional["confianca_operacional"]
    feats["estado_operacional"] = saida_operacional["estado_operacional"]
    feats["ambiguidade_cheio"] = saida_operacional["ambiguidade_cheio"]
    feats["evidencia_cheio_moderada"] = saida_operacional["evidencia_cheio_moderada"]
    feats["evidencia_cheio_forte"] = saida_operacional["evidencia_cheio_forte"]

    feats["fill_percent_final"] = fill_percent_final
    feats["fill_ratio_final"] = fill_ratio_final
    feats["classe_final"] = classe_final

    # Compatibilidade com o restante do sistema:
    feats["fill_ratio_filtered"] = fill_ratio_final
    feats["fill_percent_filtered"] = fill_percent_final
    feats["classe"] = classe_final
    feats["estado_dashboard"] = saida_operacional["estado_operacional"]

    return feats


def render_debug(img, feats):
    dbg = img.copy()

    opening_inner = feats["opening_inner"]
    expected_inside_opening = feats["expected_inside_opening"]
    floor_inner_raw = feats["floor_inner_raw"]
    floor_inner_filtered = feats["floor_inner_filtered"]

    contours, _ = cv2.findContours(
        opening_inner, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    cv2.drawContours(dbg, contours, -1, (0, 255, 255), 2)

    blue = np.zeros_like(dbg)
    blue[:, :] = (255, 0, 0)
    mask_expected = expected_inside_opening.astype(bool)
    dbg[mask_expected] = cv2.addWeighted(dbg, 0.80, blue, 0.20, 0)[mask_expected]

    red = np.zeros_like(dbg)
    red[:, :] = (0, 0, 255)
    mask_raw = floor_inner_raw.astype(bool)
    dbg[mask_raw] = cv2.addWeighted(dbg, 0.75, red, 0.25, 0)[mask_raw]

    green = np.zeros_like(dbg)
    green[:, :] = (0, 255, 0)
    mask_filtered = floor_inner_filtered.astype(bool)
    dbg[mask_filtered] = cv2.addWeighted(dbg, 0.55, green, 0.45, 0)[mask_filtered]

    ys = np.where(expected_inside_opening > 0)[0]
    if ys.size > 0:
        y_min = int(ys.min())
        y_max = int(ys.max()) + 1
        edges = np.linspace(y_min, y_max, NUM_BANDS + 1).astype(int)

        for i in range(1, len(edges) - 1):
            y = int(edges[i])
            cv2.line(dbg, (0, y), (dbg.shape[1] - 1, y), (255, 255, 0), 1)

    return dbg