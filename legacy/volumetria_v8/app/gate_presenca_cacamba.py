from __future__ import annotations

"""
Gate conservador de presença de caçamba para o Projeto Vale.

Objetivo:
- Decidir primeiro se existe uma caçamba utilizável no frame.
- Separar cenários de:
    1) caçamba ausente / troca de caçamba
    2) caçamba presente porém vazia / quase vazia
    3) caçamba presente com conteúdo

Este módulo é independente do pipeline principal e pode ser plugado antes da
volumetria/refino de altos.

Entradas esperadas:
- image_bgr: frame BGR (numpy.ndarray)
- floor_mask: máscara binária do piso visível da caçamba
- wall_mask: máscara binária das paredes visíveis da caçamba
- opening_mask: máscara binária opcional da boca / região válida atual

Saídas:
- GatePresencaResult com decisão, score, motivo e métricas auxiliares.

Observação:
Este gate é propositalmente conservador. Em caso de dúvida, ele prefere
marcar suspeito em vez de afirmar presença de caçamba.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Tuple
import json
import math
import os

import cv2
import numpy as np


@dataclass
class GatePresencaResult:
    cacamba_presente: bool
    vazia_ou_quase_vazia: bool
    score_presenca: float
    score_vazio: float
    motivo: str
    detalhe: str
    metrics: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["metrics"] = {k: float(v) for k, v in self.metrics.items()}
        return d


# -----------------------------------------------------------------------------
# Utilidades básicas
# -----------------------------------------------------------------------------


def _ensure_mask(mask: Optional[np.ndarray], shape_hw: Tuple[int, int]) -> np.ndarray:
    h, w = shape_hw
    if mask is None:
        return np.zeros((h, w), dtype=np.uint8)
    if mask.ndim == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    if mask.shape[:2] != (h, w):
        mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
    mask = (mask > 0).astype(np.uint8) * 255
    return mask


def _largest_component(mask: np.ndarray) -> np.ndarray:
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8), 8)
    if num_labels <= 1:
        return np.zeros_like(mask)
    areas = stats[1:, cv2.CC_STAT_AREA]
    idx = 1 + int(np.argmax(areas))
    return ((labels == idx).astype(np.uint8) * 255)


def _mask_area_ratio(mask: np.ndarray) -> float:
    return float((mask > 0).mean())


def _bbox_from_mask(mask: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def _touch_flags(mask: np.ndarray) -> Dict[str, bool]:
    if mask.size == 0:
        return {"left": False, "right": False, "top": False, "bottom": False}
    h, w = mask.shape[:2]
    return {
        "left": bool(np.any(mask[:, 0] > 0)),
        "right": bool(np.any(mask[:, w - 1] > 0)),
        "top": bool(np.any(mask[0, :] > 0)),
        "bottom": bool(np.any(mask[h - 1, :] > 0)),
    }


def _column_coverage(mask: np.ndarray) -> np.ndarray:
    return (mask > 0).mean(axis=0)


def _row_coverage(mask: np.ndarray) -> np.ndarray:
    return (mask > 0).mean(axis=1)


def _side_wall_scores(wall_mask: np.ndarray) -> Tuple[float, float]:
    """
    Mede evidência de parede esquerda e direita.
    A ideia é privilegiar paredes altas/contínuas em faixas laterais.
    """
    h, w = wall_mask.shape[:2]
    left_band = wall_mask[:, : max(1, int(w * 0.22))]
    right_band = wall_mask[:, max(0, w - int(w * 0.22)) :]

    left_cols = _column_coverage(left_band)
    right_cols = _column_coverage(right_band)

    # melhor coluna + média das melhores colunas => favorece continuidade vertical
    left_score = 0.6 * float(left_cols.max(initial=0.0)) + 0.4 * float(np.mean(np.sort(left_cols)[-max(1, len(left_cols)//5):]))
    right_score = 0.6 * float(right_cols.max(initial=0.0)) + 0.4 * float(np.mean(np.sort(right_cols)[-max(1, len(right_cols)//5):]))
    return left_score, right_score


def _center_bias(mask: np.ndarray) -> float:
    """0 = centralizado, 1 = muito lateralizado."""
    bbox = _bbox_from_mask(mask)
    if bbox is None:
        return 1.0
    x1, _, x2, _ = bbox
    h, w = mask.shape[:2]
    cx = (x1 + x2) / 2.0
    return float(abs(cx - (w / 2.0)) / max(1.0, w / 2.0))


def _contour_complexity(mask: np.ndarray) -> float:
    cnts, _ = cv2.findContours((mask > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return 0.0
    c = max(cnts, key=cv2.contourArea)
    area = float(cv2.contourArea(c))
    if area <= 1.0:
        return 0.0
    peri = float(cv2.arcLength(c, True))
    return peri / math.sqrt(area)


def _interior_ground_ratio(image_bgr: np.ndarray, wall_mask: np.ndarray, floor_mask: np.ndarray) -> float:
    """
    Heurística fraca para detectar quando a área interna parece mais chão/ambiente do que caçamba.
    Usa V no HSV sobre região que não é parede nem piso segmentado.
    """
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    v = hsv[:, :, 2]

    union = ((wall_mask > 0) | (floor_mask > 0)).astype(np.uint8)
    bbox = _bbox_from_mask((union * 255).astype(np.uint8))
    if bbox is None:
        return 1.0
    x1, y1, x2, y2 = bbox
    crop_union = union[y1:y2+1, x1:x2+1]
    crop_v = v[y1:y2+1, x1:x2+1]
    if crop_union.size == 0:
        return 1.0

    unknown = (crop_union == 0)
    if unknown.mean() < 0.05:
        return 0.0

    # chão / céu / reflexo tende a ser mais homogêneo e claro; isso é só um sinal auxiliar
    score_bright = float((crop_v[unknown] > 135).mean()) if np.any(unknown) else 0.0
    return score_bright


# -----------------------------------------------------------------------------
# Gate principal
# -----------------------------------------------------------------------------


def evaluate_presenca_cacamba(
    image_bgr: np.ndarray,
    floor_mask: Optional[np.ndarray] = None,
    wall_mask: Optional[np.ndarray] = None,
    opening_mask: Optional[np.ndarray] = None,
) -> GatePresencaResult:
    h, w = image_bgr.shape[:2]
    floor_mask = _ensure_mask(floor_mask, (h, w))
    wall_mask = _ensure_mask(wall_mask, (h, w))
    opening_mask = _ensure_mask(opening_mask, (h, w))

    wall_lc = _largest_component(wall_mask)
    floor_lc = _largest_component(floor_mask)
    structure = cv2.bitwise_or(wall_lc, floor_lc)
    structure_lc = _largest_component(structure)

    wall_ratio = _mask_area_ratio(wall_lc)
    floor_ratio = _mask_area_ratio(floor_lc)
    structure_ratio = _mask_area_ratio(structure_lc)
    opening_ratio = _mask_area_ratio(opening_mask)

    left_wall_score, right_wall_score = _side_wall_scores(wall_lc)
    walls_good = float(left_wall_score >= 0.28) + float(right_wall_score >= 0.28)

    structure_bbox = _bbox_from_mask(structure_lc)
    if structure_bbox is None:
        bbox_w_ratio = 0.0
        bbox_h_ratio = 0.0
    else:
        x1, y1, x2, y2 = structure_bbox
        bbox_w_ratio = float((x2 - x1 + 1) / max(1, w))
        bbox_h_ratio = float((y2 - y1 + 1) / max(1, h))

    structure_center_bias = _center_bias(structure_lc)
    opening_center_bias = _center_bias(opening_mask) if opening_ratio > 0 else 1.0
    structure_complexity = _contour_complexity(structure_lc)
    opening_touches = _touch_flags(opening_mask)
    structure_touches = _touch_flags(structure_lc)
    bright_unknown_ratio = _interior_ground_ratio(image_bgr, wall_lc, floor_lc)

    metrics = {
        "wall_ratio": wall_ratio,
        "floor_ratio": floor_ratio,
        "structure_ratio": structure_ratio,
        "opening_ratio": opening_ratio,
        "left_wall_score": left_wall_score,
        "right_wall_score": right_wall_score,
        "walls_good_count": walls_good,
        "bbox_w_ratio": bbox_w_ratio,
        "bbox_h_ratio": bbox_h_ratio,
        "structure_center_bias": structure_center_bias,
        "opening_center_bias": opening_center_bias,
        "structure_complexity": structure_complexity,
        "bright_unknown_ratio": bright_unknown_ratio,
        "opening_touch_left": float(opening_touches["left"]),
        "opening_touch_right": float(opening_touches["right"]),
        "opening_touch_top": float(opening_touches["top"]),
        "opening_touch_bottom": float(opening_touches["bottom"]),
        "structure_touch_left": float(structure_touches["left"]),
        "structure_touch_right": float(structure_touches["right"]),
        "structure_touch_top": float(structure_touches["top"]),
        "structure_touch_bottom": float(structure_touches["bottom"]),
    }

    # ------------------------------------------------------------------
    # Score de presença
    # ------------------------------------------------------------------
    score_presenca = 0.0
    score_presenca += min(0.25, wall_ratio * 1.6)
    score_presenca += min(0.20, floor_ratio * 1.3)
    score_presenca += min(0.15, structure_ratio * 0.9)
    score_presenca += min(0.20, walls_good * 0.10)
    score_presenca += min(0.10, bbox_w_ratio * 0.12)
    score_presenca += min(0.10, bbox_h_ratio * 0.12)

    # penalizações fortes
    if structure_center_bias > 0.72:
        score_presenca -= 0.18
    if walls_good < 1 and structure_ratio < 0.10:
        score_presenca -= 0.25
    if bright_unknown_ratio > 0.72 and wall_ratio < 0.08 and floor_ratio < 0.10:
        score_presenca -= 0.20
    if structure_ratio < 0.05:
        score_presenca -= 0.30

    score_presenca = float(np.clip(score_presenca, 0.0, 1.0))

    # ------------------------------------------------------------------
    # Decisão de presença
    # ------------------------------------------------------------------
    if score_presenca < 0.30:
        return GatePresencaResult(
            cacamba_presente=False,
            vazia_ou_quase_vazia=False,
            score_presenca=score_presenca,
            score_vazio=0.0,
            motivo="suspeito_cacamba_ausente",
            detalhe="presenca_muito_baixa",
            metrics=metrics,
        )

    if walls_good < 1 and structure_ratio < 0.12:
        return GatePresencaResult(
            cacamba_presente=False,
            vazia_ou_quase_vazia=False,
            score_presenca=score_presenca,
            score_vazio=0.0,
            motivo="suspeito_cacamba_ausente",
            detalhe="paredes_insuficientes",
            metrics=metrics,
        )

    if bbox_w_ratio < 0.18 or bbox_h_ratio < 0.18:
        return GatePresencaResult(
            cacamba_presente=False,
            vazia_ou_quase_vazia=False,
            score_presenca=score_presenca,
            score_vazio=0.0,
            motivo="suspeito_cacamba_ausente",
            detalhe="estrutura_minima_insuficiente",
            metrics=metrics,
        )

    # ------------------------------------------------------------------
    # Score de vazio / quase vazio
    # ------------------------------------------------------------------
    score_vazio = 0.0
    if floor_ratio > 0.10:
        score_vazio += 0.25
    if floor_ratio > 0.18:
        score_vazio += 0.15
    if wall_ratio > 0.12:
        score_vazio += 0.10
    if opening_ratio < 0.02:
        score_vazio += 0.10
    if structure_center_bias < 0.40:
        score_vazio += 0.05
    if bright_unknown_ratio < 0.35:
        score_vazio += 0.05

    # mas evita chamar de vazio quando há massa estrutural grande e centralizada
    if structure_ratio > 0.22:
        score_vazio -= 0.18
    if opening_ratio > 0.08:
        score_vazio -= 0.12
    if structure_complexity > 22.0:
        score_vazio -= 0.08

    score_vazio = float(np.clip(score_vazio, 0.0, 1.0))

    if score_vazio >= 0.45:
        return GatePresencaResult(
            cacamba_presente=True,
            vazia_ou_quase_vazia=True,
            score_presenca=score_presenca,
            score_vazio=score_vazio,
            motivo="cacamba_vazia_ou_quase_vazia",
            detalhe="baixo_conteudo_estrutural",
            metrics=metrics,
        )

    return GatePresencaResult(
        cacamba_presente=True,
        vazia_ou_quase_vazia=False,
        score_presenca=score_presenca,
        score_vazio=score_vazio,
        motivo="cacamba_presente",
        detalhe="estrutura_valida",
        metrics=metrics,
    )


# -----------------------------------------------------------------------------
# Interface opcional para integração com pipeline
# -----------------------------------------------------------------------------


def apply_gate_before_volumetry(
    image_bgr: np.ndarray,
    floor_mask: Optional[np.ndarray],
    wall_mask: Optional[np.ndarray],
    opening_mask: Optional[np.ndarray],
    row: Optional[Dict[str, Any]] = None,
) -> Tuple[GatePresencaResult, Dict[str, Any]]:
    """
    Aplica o gate e, se necessário, já atualiza um dicionário estilo row do pipeline.
    """
    result = evaluate_presenca_cacamba(
        image_bgr=image_bgr,
        floor_mask=floor_mask,
        wall_mask=wall_mask,
        opening_mask=opening_mask,
    )

    row_out: Dict[str, Any] = dict(row or {})
    row_out.setdefault("status", "ok")
    row_out.setdefault("motivo", "")
    row_out.setdefault("estado", "normal")
    row_out.setdefault("fill_csv", "")

    if not result.cacamba_presente:
        row_out["status"] = "suspeito"
        row_out["estado"] = "revisar"
        row_out["motivo"] = result.motivo
        row_out["fill_csv"] = ""
    elif result.vazia_ou_quase_vazia:
        row_out["status"] = "ok"
        row_out["estado"] = "normal"
        row_out["motivo"] = result.motivo
        # O pipeline principal pode recalcular / fixar um low-fill conservador depois.
    return result, row_out


# -----------------------------------------------------------------------------
# CLI simples para testes locais
# -----------------------------------------------------------------------------


def _load_mask(path: Optional[str]) -> Optional[np.ndarray]:
    if not path:
        return None
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    return cv2.imread(path, cv2.IMREAD_GRAYSCALE)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Gate de presença de caçamba")
    parser.add_argument("--image", required=True, help="Caminho do frame")
    parser.add_argument("--floor", default=None, help="Máscara floor_visible PNG")
    parser.add_argument("--wall", default=None, help="Máscara wall_visible PNG")
    parser.add_argument("--opening", default=None, help="Máscara opening PNG")
    parser.add_argument("--pretty", action="store_true", help="Imprime JSON formatado")
    args = parser.parse_args()

    image = cv2.imread(args.image, cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(args.image)

    floor_mask = _load_mask(args.floor)
    wall_mask = _load_mask(args.wall)
    opening_mask = _load_mask(args.opening)

    result = evaluate_presenca_cacamba(
        image_bgr=image,
        floor_mask=floor_mask,
        wall_mask=wall_mask,
        opening_mask=opening_mask,
    )

    payload = result.to_dict()
    if args.pretty:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
