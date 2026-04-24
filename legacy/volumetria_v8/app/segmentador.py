import cv2
import numpy as np
from ultralytics import YOLO

from config import (
    MODEL_PATH,
    CONF_THRES,
    IMG_SIZE,
    CLS_FLOOR,
    CLS_WALL,
)


class SegmentadorVolumetria:
    def __init__(self):
        self.model = YOLO(str(MODEL_PATH))
        self.class_names = self.model.names

    def _run_predict(self, img_path, conf, imgsz):
        return self.model.predict(
            source=str(img_path),
            conf=conf,
            imgsz=imgsz,
            retina_masks=True,
            verbose=False
        )[0]

    @staticmethod
    def _remove_small_components(mask_bin, min_area=200):
        mask_bin = (mask_bin > 0).astype(np.uint8)
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            mask_bin, connectivity=8
        )
        cleaned = np.zeros_like(mask_bin)

        for label in range(1, num_labels):
            area = int(stats[label, cv2.CC_STAT_AREA])
            if area >= min_area:
                cleaned[labels == label] = 1

        return cleaned.astype(np.uint8)

    def _extract_floor_wall_masks(self, result, h, w):
        floor_mask = np.zeros((h, w), dtype=np.uint8)
        wall_mask = np.zeros((h, w), dtype=np.uint8)

        if result.masks is None or result.boxes is None or len(result.boxes) == 0:
            return floor_mask, wall_mask

        masks_data = result.masks.data.cpu().numpy()
        classes = result.boxes.cls.cpu().numpy().astype(int)

        for i in range(len(classes)):
            cls_id = classes[i]
            mask_i = masks_data[i]

            if mask_i.shape[:2] != (h, w):
                mask_i = cv2.resize(mask_i, (w, h), interpolation=cv2.INTER_NEAREST)

            mask_bin = (mask_i > 0.5).astype(np.uint8)

            if cls_id == CLS_FLOOR:
                floor_mask = np.maximum(floor_mask, mask_bin)
            elif cls_id == CLS_WALL:
                wall_mask = np.maximum(wall_mask, mask_bin)

        floor_mask = self._remove_small_components(floor_mask, min_area=120)
        wall_mask = self._remove_small_components(wall_mask, min_area=120)

        return floor_mask.astype(np.uint8), wall_mask.astype(np.uint8)

    def _infer_opening_mask(self, floor_mask, wall_mask):
        base = np.maximum(floor_mask, wall_mask).astype(np.uint8)
        base = self._remove_small_components(base, min_area=500)

        if int(np.count_nonzero(base)) == 0:
            return base.astype(np.uint8)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (41, 41))
        closed = cv2.morphologyEx(base, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return closed.astype(np.uint8)

        largest = max(contours, key=cv2.contourArea)
        hull = cv2.convexHull(largest)

        opening = np.zeros_like(base)
        cv2.drawContours(opening, [hull], -1, 1, -1)

        return opening.astype(np.uint8)

    def segmentar(self, img_path):
        img = cv2.imread(str(img_path))
        if img is None:
            raise RuntimeError(f"Falha ao ler imagem: {img_path}")

        h, w = img.shape[:2]

        result_main = self._run_predict(img_path, conf=CONF_THRES, imgsz=IMG_SIZE)
        floor_mask, wall_mask = self._extract_floor_wall_masks(result_main, h, w)

        area_main = int(np.count_nonzero(floor_mask)) + int(np.count_nonzero(wall_mask))
        if area_main == 0:
            result_fb = self._run_predict(img_path, conf=0.03, imgsz=1536)
            floor_fb, wall_fb = self._extract_floor_wall_masks(result_fb, h, w)

            if int(np.count_nonzero(floor_fb)) > int(np.count_nonzero(floor_mask)):
                floor_mask = floor_fb
            if int(np.count_nonzero(wall_fb)) > int(np.count_nonzero(wall_mask)):
                wall_mask = wall_fb

        opening_mask = self._infer_opening_mask(floor_mask, wall_mask)

        return img, opening_mask.astype(np.uint8), floor_mask.astype(np.uint8), wall_mask.astype(np.uint8)

    @staticmethod
    def salvar_mask(mask_u8, out_path):
        cv2.imwrite(str(out_path), (mask_u8.astype(np.uint8) * 255))
