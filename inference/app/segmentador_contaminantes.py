import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from ultralytics import YOLO

MODEL_PATH = Path(os.environ.get("CONTAMINANTES_MODEL_PATH", os.environ.get("MODEL_PATH", "/app/model/yolov8n.pt")))
IMG_SIZE = int(os.environ.get("CONTAMINANTES_IMG_SIZE", os.environ.get("IMG_SIZE", "1024")))
PREDICT_CONF_THRES = float(os.environ.get("CONTAMINANTES_PREDICT_CONF_THRES", "0.05"))

CLASS_MIN_CONF = {
    "madeira": 0.22,
    "plastico": 0.22,
    "sucata": 0.08,
    "papelao": float(os.environ.get("CONTAMINANTES_PAPELAO_MIN_CONF", "0.03")),
}

CLASS_MIN_AREA_RATIO = {
    "madeira": 0.03,
    "plastico": 0.03,
    "sucata": 0.02,
    "papelao": float(os.environ.get("CONTAMINANTES_PAPELAO_MIN_AREA_RATIO", "0.003")),
}

MAX_POLYGON_POINTS = 80
MIN_INSIDE_ROI_RATIO = float(os.environ.get("CONTAMINANTES_MIN_INSIDE_ROI_RATIO", "0.2"))


class SegmentadorContaminantes:
    def __init__(self, model_path: Path | None = None):
        self.model_path = Path(model_path) if model_path else MODEL_PATH
        self.model = None
        self.ativo = False
        self.class_names: dict[int, str] = {}

        try:
            if self.model_path.exists():
                self.model = YOLO(str(self.model_path))
                self.class_names = self.model.names
                self.ativo = True
        except Exception:
            self.ativo = False

    @staticmethod
    def _normalizar_nome_classe(nome: str) -> str:
        s = str(nome).strip().lower()
        mapa = {
            "madeira": "madeira",
            "wood": "madeira",
            "timber": "madeira",
            "mdf": "madeira",
            "sucata": "sucata",
            "metal": "sucata",
            "metais": "sucata",
            "ferro": "sucata",
            "steel": "sucata",
            "iron": "sucata",
            "scrap": "sucata",
            "scrap_metal": "sucata",
            "filtro_oleo": "sucata",
            "filtro de oleo": "sucata",
            "filtro de óleo": "sucata",
            "oil_filter": "sucata",
            "plastico": "plastico",
            "plástico": "plastico",
            "plastic": "plastico",
            "papelao": "papelao",
            "papelão": "papelao",
            "cardboard": "papelao",
            "paperboard": "papelao",
            "boxboard": "papelao",
            "carton": "papelao",
            "papelao_molhado": "papelao",
        }
        return mapa.get(s, s)

    @staticmethod
    def _classe_passa_limiar(nome: str, conf: float) -> bool:
        limiar = CLASS_MIN_CONF.get(nome, 0.20)
        return conf >= limiar

    @staticmethod
    def _area_ratio_minimo(nome: str) -> float:
        return CLASS_MIN_AREA_RATIO.get(nome, 0.03)

    @staticmethod
    def _ordenar_por_valor_desc(d: dict) -> list[tuple[str, float]]:
        return sorted(d.items(), key=lambda x: x[1], reverse=True)

    @staticmethod
    def _classe_principal(areas_ratio: dict[str, float], materiais_unicos: list[str]) -> str | None:
        if areas_ratio:
            return max(areas_ratio.items(), key=lambda x: x[1])[0]
        if materiais_unicos:
            return materiais_unicos[0]
        return None

    @staticmethod
    def _bbox_from_xyxy(xyxy_row: Any) -> tuple[list[int] | None, list[int] | None]:
        if xyxy_row is None or len(xyxy_row) < 4:
            return None, None

        x1, y1, x2, y2 = [int(round(float(v))) for v in xyxy_row[:4]]
        if x2 < x1:
            x1, x2 = x2, x1
        if y2 < y1:
            y1, y2 = y2, y1

        w = max(0, x2 - x1)
        h = max(0, y2 - y1)
        return [x1, y1, x2, y2], [x1, y1, w, h]

    @staticmethod
    def _simplificar_poligono(poly: Any, max_points: int = MAX_POLYGON_POINTS) -> list[list[int]]:
        if poly is None:
            return []

        arr = np.asarray(poly)
        if arr.ndim != 2 or arr.shape[0] < 3 or arr.shape[1] < 2:
            return []

        pts = arr[:, :2]
        n = len(pts)
        if n > max_points:
            idx = np.linspace(0, n - 1, num=max_points, dtype=int)
            pts = pts[idx]

        return [[int(round(float(p[0]))), int(round(float(p[1])))] for p in pts]

    @staticmethod
    def _normalizar_roi_mask(mask: Any, shape: tuple[int, int]) -> np.ndarray | None:
        if mask is None:
            return None

        arr = np.asarray(mask)
        if arr.ndim != 2:
            return None

        h, w = shape
        if arr.shape[:2] != (h, w):
            arr = cv2.resize(arr.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST)

        return (arr > 0).astype(np.uint8)

    def inferir(self, img_path: Path, analysis_mask: Any = None) -> dict[str, Any]:
        if not self.ativo or self.model is None:
            return {
                "materiais_detectados": [],
                "materiais_relevantes": [],
                "materiais_detectados_brutos": [],
                "deteccoes": [],
                "areas_px": {},
                "areas_ratio": {},
                "observacao": "modelo_contaminantes_nao_disponivel",
            }

        result = self.model.predict(
            source=str(img_path),
            conf=PREDICT_CONF_THRES,
            imgsz=IMG_SIZE,
            retina_masks=True,
            verbose=False,
        )[0]

        image_shape = None
        if result.orig_shape and len(result.orig_shape) >= 2:
            image_shape = (int(result.orig_shape[0]), int(result.orig_shape[1]))

        analysis_mask_bin = self._normalizar_roi_mask(analysis_mask, image_shape) if image_shape else None

        deteccoes: list[dict[str, Any]] = []
        areas_px: dict[str, float] = {}

        boxes_ok = result.boxes is not None and len(result.boxes) > 0
        masks_ok = result.masks is not None and result.masks.data is not None and len(result.masks.data) > 0

        classes = []
        confs = []
        boxes_xyxy = None
        if boxes_ok:
            classes = result.boxes.cls.cpu().numpy().astype(int)
            confs = result.boxes.conf.cpu().numpy()
            boxes_xyxy = result.boxes.xyxy.cpu().numpy()

        masks_np = None
        masks_xy = None
        if masks_ok:
            masks_np = result.masks.data.cpu().numpy()
            try:
                masks_xy = result.masks.xy
            except Exception:
                masks_xy = None

        if boxes_ok:
            for i, (cls_id, conf) in enumerate(zip(classes, confs)):
                nome = self.class_names.get(int(cls_id), str(cls_id))
                nome = self._normalizar_nome_classe(nome)
                conf = round(float(conf), 4)

                if not self._classe_passa_limiar(nome, conf):
                    continue

                area_px = 0.0
                inside_roi_ratio = 1.0
                if masks_np is not None and i < len(masks_np):
                    mask_bin = masks_np[i] > 0.5
                    total_mask_px = float(np.count_nonzero(mask_bin))

                    if analysis_mask_bin is not None:
                        mask_inside_roi = mask_bin & (analysis_mask_bin > 0)
                        inside_roi_ratio = (
                            float(np.count_nonzero(mask_inside_roi)) / total_mask_px
                            if total_mask_px > 0
                            else 0.0
                        )

                        if inside_roi_ratio < MIN_INSIDE_ROI_RATIO:
                            continue

                        mask_bin = mask_inside_roi

                    area_px = float(np.count_nonzero(mask_bin))
                    if area_px <= 0:
                        continue

                    areas_px[nome] = areas_px.get(nome, 0.0) + area_px

                bbox_xyxy, bbox_xywh = self._bbox_from_xyxy(boxes_xyxy[i] if boxes_xyxy is not None and i < len(boxes_xyxy) else None)
                polygon: list[list[int]] = []
                if masks_xy is not None and i < len(masks_xy):
                    polygon = self._simplificar_poligono(masks_xy[i])

                deteccoes.append({
                    "classe": nome,
                    "confianca": conf,
                    "area_px": round(float(area_px), 2),
                    "bbox_xyxy": bbox_xyxy,
                    "bbox_xywh": bbox_xywh,
                    "polygon": polygon,
                    "tem_geometria": bool(bbox_xyxy or polygon),
                    "inside_roi_ratio": round(float(inside_roi_ratio), 4),
                })
        elif masks_ok:
            return {
                "materiais_detectados": [],
                "materiais_relevantes": [],
                "materiais_detectados_brutos": [],
                "deteccoes": [],
                "areas_px": {},
                "areas_ratio": {},
                "observacao": "masks_sem_boxes_validos",
            }

        deteccoes.sort(key=lambda x: x["confianca"], reverse=True)

        vistos = set()
        materiais_unicos: list[str] = []
        for d in deteccoes:
            nome = d["classe"]
            if nome not in vistos:
                vistos.add(nome)
                materiais_unicos.append(nome)

        total_area = float(sum(areas_px.values()))
        areas_ratio = {k: float(v) / total_area for k, v in areas_px.items()} if total_area > 0 else {}

        classe_principal = self._classe_principal(areas_ratio, materiais_unicos)

        materiais_relevantes: list[str] = []
        if classe_principal:
            materiais_relevantes.append(classe_principal)

        for nome, ratio in self._ordenar_por_valor_desc(areas_ratio):
            if nome == classe_principal:
                continue
            if ratio >= self._area_ratio_minimo(nome):
                materiais_relevantes.append(nome)

        materiais_detectados_saida: list[str] = []
        for nome in materiais_relevantes:
            if nome not in materiais_detectados_saida:
                materiais_detectados_saida.append(nome)

        if not materiais_detectados_saida and materiais_unicos:
            materiais_detectados_saida = [materiais_unicos[0]]

        deteccoes_enriquecidas: list[dict[str, Any]] = []
        for d in deteccoes:
            nome = d["classe"]
            area_ratio = round(float(areas_ratio.get(nome, 0.0)), 4)
            deteccoes_enriquecidas.append({
                "classe": nome,
                "confianca": d["confianca"],
                "area_px": d["area_px"],
                "area_ratio": area_ratio,
                "bbox_xyxy": d.get("bbox_xyxy"),
                "bbox_xywh": d.get("bbox_xywh"),
                "polygon": d.get("polygon", []),
                "tem_geometria": bool(d.get("tem_geometria", False)),
                "inside_roi_ratio": d.get("inside_roi_ratio", 1.0),
                "fraca": bool(d["confianca"] < 0.15 and area_ratio < self._area_ratio_minimo(nome)),
            })

        return {
            "materiais_detectados": materiais_detectados_saida,
            "materiais_relevantes": materiais_detectados_saida,
            "materiais_detectados_brutos": materiais_unicos,
            "deteccoes": deteccoes_enriquecidas,
            "areas_px": {k: round(float(v), 2) for k, v in areas_px.items()},
            "areas_ratio": {k: round(float(v), 4) for k, v in areas_ratio.items()},
            "analysis_mask_applied": bool(analysis_mask_bin is not None),
            "observacao": "ok",
        }


if __name__ == "__main__":
    seg = SegmentadorContaminantes()
    print("ativo =", seg.ativo)
    print("model_path =", seg.model_path)
