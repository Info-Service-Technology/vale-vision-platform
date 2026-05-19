import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from ultralytics import YOLO


BORDER_MODEL_PATH = Path(
    os.environ.get(
        "BORDA_CACAMBA_MODEL_PATH",
        os.environ.get("BIN_OPENING_MODEL_PATH", "/app/model/borda_cacamba.pt"),
    )
)
BORDER_IMG_SIZE = int(os.environ.get("BORDA_CACAMBA_IMG_SIZE", "1024"))
BORDER_CONF_THRES = float(os.environ.get("BORDA_CACAMBA_CONF_THRES", "0.35"))
MIN_MASK_AREA_RATIO = float(os.environ.get("BORDA_CACAMBA_MIN_MASK_AREA_RATIO", "0.03"))


class SegmentadorBordaCacamba:
    def __init__(self, model_path: Path | None = None):
        self.model_path = Path(model_path) if model_path else BORDER_MODEL_PATH
        self.model = None
        self.ativo = False

        try:
            if self.model_path.exists():
                self.model = YOLO(str(self.model_path))
                self.ativo = True
        except Exception:
            self.ativo = False

    @staticmethod
    def _keep_largest_component(mask_bin: np.ndarray) -> np.ndarray:
        mask_u8 = (mask_bin > 0).astype(np.uint8)
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask_u8, connectivity=8)

        if num_labels <= 1:
            return np.zeros_like(mask_u8)

        best_label = None
        best_area = 0
        for label in range(1, num_labels):
            area = int(stats[label, cv2.CC_STAT_AREA])
            if area > best_area:
                best_area = area
                best_label = label

        if best_label is None:
            return np.zeros_like(mask_u8)

        out = np.zeros_like(mask_u8)
        out[labels == best_label] = 1
        return out

    @staticmethod
    def _mask_to_polygon(mask_bin: np.ndarray) -> list[list[int]]:
        contours, _ = cv2.findContours(mask_bin.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return []

        contour = max(contours, key=cv2.contourArea)
        hull = cv2.convexHull(contour)
        perimeter = cv2.arcLength(hull, True)
        approx = cv2.approxPolyDP(hull, max(2.0, 0.01 * perimeter), True)

        return [[int(pt[0][0]), int(pt[0][1])] for pt in approx]

    def detectar(self, img_path: Path) -> dict[str, Any]:
        if not self.ativo or self.model is None:
            return {
                "ok": False,
                "motivo": "modelo_borda_indisponivel",
                "mask": None,
                "polygon": [],
            }

        image = cv2.imread(str(img_path))
        if image is None:
            return {
                "ok": False,
                "motivo": "imagem_invalida",
                "mask": None,
                "polygon": [],
            }

        h, w = image.shape[:2]
        result = self.model.predict(
            source=image,
            conf=BORDER_CONF_THRES,
            imgsz=BORDER_IMG_SIZE,
            retina_masks=True,
            verbose=False,
        )[0]

        if result.masks is None or result.boxes is None or len(result.boxes) == 0:
            return {
                "ok": False,
                "motivo": "sem_borda_detectada",
                "mask": None,
                "polygon": [],
            }

        masks_np = result.masks.data.cpu().numpy()
        confs = result.boxes.conf.cpu().numpy()

        best_index = int(np.argmax(confs))
        best_mask = masks_np[best_index]

        if best_mask.shape[:2] != (h, w):
            best_mask = cv2.resize(best_mask, (w, h), interpolation=cv2.INTER_NEAREST)

        mask_bin = self._keep_largest_component(best_mask > 0.5)
        mask_area = int(np.count_nonzero(mask_bin))
        mask_ratio = mask_area / float(max(1, h * w))

        if mask_area == 0 or mask_ratio < MIN_MASK_AREA_RATIO:
            return {
                "ok": False,
                "motivo": "borda_area_insuficiente",
                "mask": None,
                "polygon": [],
                "mask_area_ratio": round(mask_ratio, 4),
            }

        return {
            "ok": True,
            "motivo": "ok",
            "mask": mask_bin.astype(np.uint8),
            "polygon": self._mask_to_polygon(mask_bin),
            "mask_area_ratio": round(mask_ratio, 4),
            "confianca": round(float(confs[best_index]), 4),
        }
