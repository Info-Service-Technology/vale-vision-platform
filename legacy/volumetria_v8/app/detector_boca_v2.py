from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import cv2
import numpy as np
from ultralytics import YOLO


MODEL_PATH = r"E:\PROJETO VALE\DATASET_BOCA_V2\MODELOS_BOCA\best_boca_cacamba_v2_20260408.pt"

CONF_THRES = 0.70
IOU_THRES = 0.50
IMGSZ = 1024

MIN_COMPONENT_RATIO = 0.90
MIN_MASK_AREA = 120000
MAX_MASK_AREA = 2000000


_model: Optional[YOLO] = None


def _get_model() -> YOLO:
    global _model
    if _model is None:
        _model = YOLO(MODEL_PATH)
    return _model


def _keep_largest_component(mask_bin: np.ndarray):
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask_bin, connectivity=8)
    if num_labels <= 1:
        return np.zeros_like(mask_bin), 0, 0

    best_label = None
    best_area = 0
    for lab in range(1, num_labels):
        area = int(stats[lab, cv2.CC_STAT_AREA])
        if area > best_area:
            best_area = area
            best_label = lab

    if best_label is None:
        return np.zeros_like(mask_bin), 0, 0

    out = np.zeros_like(mask_bin)
    out[labels == best_label] = 255
    total_fg = int((mask_bin > 0).sum())
    return out, best_area, total_fg


def _contour_from_mask(mask_bin: np.ndarray):
    contours, _ = cv2.findContours(mask_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    cnt = max(contours, key=cv2.contourArea)
    return cnt.reshape(-1, 2)


def _simplify_polygon(poly: np.ndarray):
    if poly is None or len(poly) < 3:
        return None

    cnt = poly.astype(np.int32).reshape((-1, 1, 2))
    hull = cv2.convexHull(cnt)
    peri = cv2.arcLength(hull, True)

    best = hull
    for frac in [0.002, 0.004, 0.006, 0.008, 0.010, 0.015, 0.020, 0.030]:
        approx = cv2.approxPolyDP(hull, frac * peri, True)
        if 4 <= len(approx) <= 8:
            best = approx
            break

    return best.reshape(-1, 2)


def _touches_border(mask_bin: np.ndarray) -> Dict[str, bool]:
    h, w = mask_bin.shape[:2]
    return {
        "left": bool((mask_bin[:, 0] > 0).any()),
        "right": bool((mask_bin[:, w - 1] > 0).any()),
        "top": bool((mask_bin[0, :] > 0).any()),
        "bottom": bool((mask_bin[h - 1, :] > 0).any()),
    }


def detectar_boca(img_bgr: np.ndarray) -> Dict[str, Any]:
    model = _get_model()
    h, w = img_bgr.shape[:2]

    results = model.predict(
        source=img_bgr,
        conf=CONF_THRES,
        iou=IOU_THRES,
        imgsz=IMGSZ,
        verbose=False,
        save=False
    )

    r = results[0]

    if r.masks is None or r.boxes is None or len(r.boxes) == 0:
        return {
            "ok": False,
            "motivo": "sem_boca_modelo_v2",
            "conf": 0.0,
            "mask": None,
            "poly": None,
        }

    masks_data = r.masks.data.cpu().numpy()

    best_conf = -1.0
    best_mask = None

    for i in range(len(r.boxes)):
        conf = float(r.boxes.conf[i].item())
        if conf > best_conf:
            best_conf = conf
            best_mask = masks_data[i]

    if best_mask is None:
        return {
            "ok": False,
            "motivo": "sem_boca_modelo_v2",
            "conf": 0.0,
            "mask": None,
            "poly": None,
        }

    if best_mask.shape[0] != h or best_mask.shape[1] != w:
        best_mask = cv2.resize(best_mask, (w, h), interpolation=cv2.INTER_NEAREST)

    mask_bin = (best_mask > 0.5).astype(np.uint8) * 255
    clean_mask, largest_px, total_px = _keep_largest_component(mask_bin)

    if largest_px <= 0:
        return {
            "ok": False,
            "motivo": "mask_vazia",
            "conf": best_conf,
            "mask": None,
            "poly": None,
        }

    comp_ratio = largest_px / float(max(1, total_px))

    if largest_px < MIN_MASK_AREA:
        return {
            "ok": False,
            "motivo": "boca_pequena",
            "conf": best_conf,
            "mask": clean_mask,
            "poly": None,
        }

    if largest_px > MAX_MASK_AREA:
        return {
            "ok": False,
            "motivo": "boca_grande_demais",
            "conf": best_conf,
            "mask": clean_mask,
            "poly": None,
        }

    if comp_ratio < MIN_COMPONENT_RATIO:
        return {
            "ok": False,
            "motivo": "mask_fragmentada",
            "conf": best_conf,
            "mask": clean_mask,
            "poly": None,
        }

    border_touch = _touches_border(clean_mask)

    # regra conservadora:
    # topo encostando é aceitável em muitos casos;
    # laterais ou base encostando demais costuma indicar cena ruim
    if border_touch["left"] and border_touch["right"]:
        return {
            "ok": False,
            "motivo": "boca_encosta_laterais",
            "conf": best_conf,
            "mask": clean_mask,
            "poly": None,
        }

    poly_raw = _contour_from_mask(clean_mask)
    poly = _simplify_polygon(poly_raw)

    if poly is None or len(poly) < 4:
        return {
            "ok": False,
            "motivo": "poly_invalido",
            "conf": best_conf,
            "mask": clean_mask,
            "poly": None,
        }

    return {
        "ok": True,
        "motivo": "ok",
        "conf": best_conf,
        "mask": clean_mask,
        "poly": poly.astype(np.int32),
        "component_ratio": comp_ratio,
        "mask_area": largest_px,
        "touch_border": border_touch,
    }
