
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


import importlib.util

try:
    from gate_presenca_cacamba import apply_gate_before_volumetry
except Exception:
    apply_gate_before_volumetry = None

try:
    from detector_boca_v2 import detectar_boca
except Exception:
    detectar_boca = None

BASE_CANDIDATES = [
    Path(__file__).resolve().parent / "main_incremental_BASELINE_FINAL_20260404.py",
    Path(__file__).resolve().parent / "main_incremental_reverter_baseline.py",
    Path(__file__).resolve().parent / "main_incremental_OK_20260404.py",
]
_base_path = next((p for p in BASE_CANDIDATES if p.exists()), None)
if _base_path is None:
    raise FileNotFoundError("Nao achei arquivo baseline para importar como base.")
_spec = importlib.util.spec_from_file_location("main_incremental_base_module", str(_base_path))
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)


VALID_EXTS = base.VALID_EXTS



class PlasticHighORBRefiner:
    # V2.4:
    # - mantém veto duro para toque lateral / topo e casos realmente parciais
    # - amplia o resgate soft para plástico alto com ORB forte
    # - libera mais casos de estrutura pequena / clip embaixo quando o alinhamento estiver convincente
    GATE_BORDER_MARGIN_PX = 14
    GATE_ALLOW_BOTTOM_TOUCH_ONLY = True
    GATE_MIN_INSIDE_RATIO_IF_BOTTOM_TOUCH = 0.86
    GATE_MAX_BOTTOM_EXCESS_PX_RATIO = 0.18

    GATE_MIN_CAND_AREA_RATIO = 0.010
    GATE_MIN_CAND_W_RATIO = 0.28
    GATE_MIN_CAND_H_RATIO = 0.07
    GATE_MAX_CAND_W_RATIO = 0.95
    GATE_MAX_CAND_H_RATIO = 0.55

    GATE_MIN_STRUCT_AREA_RATIO = 0.020
    GATE_MIN_STRUCT_W_RATIO = 0.35
    GATE_MIN_STRUCT_H_RATIO = 0.12

    GATE_MIN_INSIDE_RATIO = 0.72
    GATE_HULL_DILATE_PX = 21

    GATE_MAX_CENTER_SHIFT_X = 0.30
    GATE_MAX_CENTER_SHIFT_Y = 0.28

    SOFT_RESCUE_ENABLED = True
    SOFT_RESCUE_MIN_FILL_OLD = 34.0
    SOFT_RESCUE_MIN_MATCHES = 70
    SOFT_RESCUE_MIN_INLIERS = 28
    SOFT_RESCUE_MIN_INLIER_RATIO = 0.28
    SOFT_RESCUE_MIN_INSIDE_RATIO = 0.72
    SOFT_RESCUE_STRONG_MIN_MATCHES = 90
    SOFT_RESCUE_STRONG_MIN_INLIERS = 40

    SOFT_RESCUE_CLIP_BOTTOM_MIN_MATCHES = 85
    SOFT_RESCUE_CLIP_BOTTOM_MIN_INLIERS = 40

    SOFT_RESCUE_STRUCT_SMALL_MIN_MATCHES = 80
    SOFT_RESCUE_STRUCT_SMALL_MIN_INLIERS = 38
    SOFT_RESCUE_STRUCT_SMALL_HIGHFILL_OLD = 52.0
    SOFT_RESCUE_STRUCT_SMALL_HIGHFILL_MATCHES = 70
    SOFT_RESCUE_STRUCT_SMALL_HIGHFILL_INLIERS = 28
    SOFT_RESCUE_STRUCT_SMALL_HIGHFILL_INLIER_RATIO = 0.33

    def __init__(self):
        app_dir = Path(__file__).resolve().parent

        self.ref_img_path = app_dir / "opening_ref_image_v2_plastico.jpg"
        self.ref_mask_path = app_dir / "opening_ref_mask_v2_plastico.png"

        if not self.ref_img_path.exists():
            fallback_img = Path(r"E:\PROJETO VALE\V2_ALTOS\REF\plastico_GF0191275_20260305123930508_MD_WITH_TARGET.jpg")
            if fallback_img.exists():
                self.ref_img_path = fallback_img

        if not self.ref_mask_path.exists():
            fallback_mask = Path(r"E:\PROJETO VALE\V2_ALTOS\REF\opening_ref_mask.png")
            if fallback_mask.exists():
                self.ref_mask_path = fallback_mask

        self.ativo = False
        self.ref_img = None
        self.ref_mask = None
        self.ref_gray = None
        self.orb = None
        self.bf = None
        self.kp_ref = None
        self.des_ref = None

        try:
            if self.ref_img_path.exists() and self.ref_mask_path.exists():
                self.ref_img = cv2.imread(str(self.ref_img_path))
                self.ref_mask = cv2.imread(str(self.ref_mask_path), cv2.IMREAD_GRAYSCALE)

                if self.ref_img is not None and self.ref_mask is not None:
                    self.ref_gray = cv2.cvtColor(self.ref_img, cv2.COLOR_BGR2GRAY)

                    self.orb = cv2.ORB_create(
                        nfeatures=5000,
                        scaleFactor=1.2,
                        nlevels=8,
                        edgeThreshold=15,
                        patchSize=31,
                        fastThreshold=10,
                    )
                    self.bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
                    self.kp_ref, self.des_ref = self.orb.detectAndCompute(self.ref_gray, None)

                    if self.des_ref is not None and len(self.kp_ref) >= 20:
                        self.ativo = True
        except Exception:
            self.ativo = False

        self.debug_dir = DEBUG_DIR / "orb_v2_plastico"
        self.debug_dir.mkdir(parents=True, exist_ok=True)

        self.reject_debug_dir = DEBUG_DIR / "orb_v2_plastico_rejeitados"
        self.reject_debug_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _mask255(mask):
        return ((mask > 0).astype(np.uint8) * 255)

    @staticmethod
    def _largest_component(mask_u8):
        if mask_u8 is None:
            return None

        m = ((mask_u8 > 0).astype(np.uint8))
        if int(np.count_nonzero(m)) <= 0:
            return None

        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
        if num_labels <= 1:
            return None

        idx = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
        out = np.zeros_like(m, dtype=np.uint8)
        out[labels == idx] = 255
        return out

    @staticmethod
    def _bbox(mask_u8):
        if mask_u8 is None:
            return None
        ys, xs = np.where(mask_u8 > 0)
        if len(xs) == 0 or len(ys) == 0:
            return None
        x1 = int(xs.min())
        x2 = int(xs.max())
        y1 = int(ys.min())
        y2 = int(ys.max())
        w = int(x2 - x1 + 1)
        h = int(y2 - y1 + 1)
        return (x1, y1, x2, y2, w, h)

    def _touches_border(self, mask_u8, margin=None):
        if mask_u8 is None:
            return False, {}, {}

        margin = int(margin or self.GATE_BORDER_MARGIN_PX)
        margin = max(2, margin)

        h, w = mask_u8.shape[:2]
        min_strip_pixels = max(40, margin * 6)

        counts = {
            "left": int(np.count_nonzero(mask_u8[:, :margin] > 0)),
            "right": int(np.count_nonzero(mask_u8[:, w - margin:] > 0)),
            "top": int(np.count_nonzero(mask_u8[:margin, :] > 0)),
            "bottom": int(np.count_nonzero(mask_u8[h - margin:, :] > 0)),
        }
        flags = {k: (v >= min_strip_pixels) for k, v in counts.items()}
        return any(flags.values()), flags, counts

    @staticmethod
    def _convex_hull_mask(mask_u8):
        if mask_u8 is None:
            return None

        m = (mask_u8 > 0).astype(np.uint8)
        contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        pts = np.vstack(contours)
        hull = cv2.convexHull(pts)
        out = np.zeros_like(mask_u8, dtype=np.uint8)
        cv2.fillConvexPoly(out, hull, 255)
        return out

    def _build_structural_support(self, floor, wall):
        floor_u8 = self._mask255(floor) if floor is not None else None
        wall_u8 = self._mask255(wall) if wall is not None else None

        pieces = [p for p in [floor_u8, wall_u8] if p is not None and int(np.count_nonzero(p > 0)) > 0]
        if not pieces:
            return None

        support = np.zeros_like(pieces[0], dtype=np.uint8)
        for p in pieces:
            support = cv2.bitwise_or(support, p)

        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        support = cv2.morphologyEx(support, cv2.MORPH_CLOSE, k, iterations=2)
        support = cv2.dilate(support, k, iterations=1)
        support = self._largest_component(support)
        if support is None:
            return None

        hull = self._convex_hull_mask(support)
        if hull is None:
            return support

        return hull

    @staticmethod
    def _inside_ratio(mask_a, mask_b):
        area_a = int(np.count_nonzero(mask_a > 0))
        if area_a <= 0:
            return 0.0
        inter = cv2.bitwise_and(mask_a, mask_b)
        inter_area = int(np.count_nonzero(inter > 0))
        return inter_area / float(area_a)

    def _save_gate_reject_debug(self, img_path, img_bgr, warped_mask, support_mask, gate_info, fill_old, info):
        try:
            overlay = img_bgr.copy()

            if support_mask is not None and int(np.count_nonzero(support_mask > 0)) > 0:
                support_bool = support_mask > 0
                cyan = np.zeros_like(overlay)
                cyan[:, :] = (255, 255, 0)
                overlay[support_bool] = cv2.addWeighted(overlay, 0.78, cyan, 0.22, 0)[support_bool]
                contours_support, _ = cv2.findContours((support_mask > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(overlay, contours_support, -1, (255, 255, 0), 2)

            if warped_mask is not None and int(np.count_nonzero(warped_mask > 0)) > 0:
                warp_bool = warped_mask > 0
                red = np.zeros_like(overlay)
                red[:, :] = (0, 0, 255)
                overlay[warp_bool] = cv2.addWeighted(overlay, 0.74, red, 0.26, 0)[warp_bool]
                contours_warp, _ = cv2.findContours((warped_mask > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(overlay, contours_warp, -1, (0, 255, 255), 3)

            line1 = f"GATE_REJEITADO | motivo={gate_info.get('motivo','?')} | detalhe={gate_info.get('detalhe','?')}"
            line2 = (
                f"fill_old={fill_old:.2f} | matches={info.get('matches',0)} | "
                f"inliers={info.get('inliers',0)} | inside={gate_info.get('inside_ratio',0.0):.3f} | "
                f"geom_exag={int(bool(gate_info.get('cand_geometria_exagerada', False)))} | "
                f"bottom_only={int(bool(gate_info.get('cand_bottom_touch_only', False)))}"
            )
            cv2.putText(overlay, line1[:180], (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.70, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(overlay, line2[:180], (20, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.70, (255, 255, 255), 2, cv2.LINE_AA)

            cv2.imwrite(str(self.reject_debug_dir / f"{img_path.stem}_orb_v2_rejeitado.jpg"), overlay)
            if warped_mask is not None:
                cv2.imwrite(str(self.reject_debug_dir / f"{img_path.stem}_opening_v2_rejeitada.png"), warped_mask)
            if support_mask is not None:
                cv2.imwrite(str(self.reject_debug_dir / f"{img_path.stem}_estrutura_gate.png"), support_mask)
        except Exception:
            pass

    def _mark_feats_as_suspect(self, feats_atual, motivo):
        feats_novo = dict(feats_atual)
        feats_novo["status_frame"] = "suspeito"
        feats_novo["motivo_falha"] = motivo
        return feats_novo

    def _run_commercial_gate(self, warped_mask, floor, wall, img_shape):
        h, w = img_shape[:2]
        frame_area = float(max(1, h * w))

        cand = self._largest_component(self._mask255(warped_mask))
        if cand is None:
            return False, None, {
                "motivo": "referencia_desalinhada",
                "detalhe": "sem_candidato_orb",
                "inside_ratio": 0.0,
            }

        cand_area = int(np.count_nonzero(cand > 0))
        cand_bbox = self._bbox(cand)
        if cand_bbox is None:
            return False, None, {
                "motivo": "referencia_desalinhada",
                "detalhe": "bbox_candidata_invalida",
                "inside_ratio": 0.0,
            }

        x1, y1, x2, y2, bw, bh = cand_bbox
        cand_area_ratio = cand_area / frame_area
        bw_ratio = bw / float(max(1, w))
        bh_ratio = bh / float(max(1, h))

        if cand_area_ratio < self.GATE_MIN_CAND_AREA_RATIO:
            return False, None, {
                "motivo": "referencia_desalinhada",
                "detalhe": "boca_muito_pequena",
                "inside_ratio": 0.0,
            }

        if bw_ratio < self.GATE_MIN_CAND_W_RATIO or bh_ratio < self.GATE_MIN_CAND_H_RATIO:
            return False, None, {
                "motivo": "referencia_desalinhada",
                "detalhe": "geometria_boca_pequena",
                "inside_ratio": 0.0,
            }

        cand_geometria_exagerada = (
            bw_ratio > self.GATE_MAX_CAND_W_RATIO
            or bh_ratio > self.GATE_MAX_CAND_H_RATIO
        )

        cand_border_touch, cand_border_flags, cand_border_counts = self._touches_border(cand)

        cand_bottom_touch_only = (
            cand_border_touch
            and bool(cand_border_flags.get("bottom"))
            and not bool(cand_border_flags.get("left"))
            and not bool(cand_border_flags.get("right"))
            and not bool(cand_border_flags.get("top"))
        )

        if cand_border_touch and not (self.GATE_ALLOW_BOTTOM_TOUCH_ONLY and cand_bottom_touch_only):
            return False, None, {
                "motivo": "frame_parcial",
                "detalhe": f"boca_encosta_borda_{cand_border_flags}",
                "inside_ratio": 0.0,
            }

        support = self._build_structural_support(floor, wall)
        if support is None:
            return False, None, {
                "motivo": "referencia_desalinhada",
                "detalhe": "sem_estrutura_real",
                "inside_ratio": 0.0,
            }

        support_area = int(np.count_nonzero(support > 0))
        support_bbox = self._bbox(support)
        if support_bbox is None:
            return False, support, {
                "motivo": "referencia_desalinhada",
                "detalhe": "bbox_estrutura_invalida",
                "inside_ratio": 0.0,
            }

        sx1, sy1, sx2, sy2, sw, sh = support_bbox
        support_area_ratio = support_area / frame_area
        sw_ratio = sw / float(max(1, w))
        sh_ratio = sh / float(max(1, h))

        if support_area_ratio < self.GATE_MIN_STRUCT_AREA_RATIO:
            return False, support, {
                "motivo": "referencia_desalinhada",
                "detalhe": "estrutura_insuficiente",
                "inside_ratio": 0.0,
            }

        if sw_ratio < self.GATE_MIN_STRUCT_W_RATIO or sh_ratio < self.GATE_MIN_STRUCT_H_RATIO:
            return False, support, {
                "motivo": "frame_parcial",
                "detalhe": "estrutura_pequena",
                "inside_ratio": 0.0,
            }

        struct_cx = ((sx1 + sx2) / 2.0) / float(max(1, w))
        struct_cy = ((sy1 + sy2) / 2.0) / float(max(1, h))
        if abs(struct_cx - 0.5) > self.GATE_MAX_CENTER_SHIFT_X or abs(struct_cy - 0.5) > self.GATE_MAX_CENTER_SHIFT_Y:
            return False, support, {
                "motivo": "frame_parcial",
                "detalhe": "estrutura_muito_deslocada",
                "inside_ratio": 0.0,
            }

        support_border_touch, support_border_flags, support_border_counts = self._touches_border(support)
        if support_border_touch and (sw_ratio < 0.60 or sh_ratio < 0.20):
            return False, support, {
                "motivo": "frame_parcial",
                "detalhe": f"estrutura_clip_borda_{support_border_flags}",
                "inside_ratio": 0.0,
            }

        dilate_px = max(9, int(self.GATE_HULL_DILATE_PX))
        if dilate_px % 2 == 0:
            dilate_px += 1

        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate_px, dilate_px))
        support_guard = cv2.dilate(support, k, iterations=1)
        inside_ratio = self._inside_ratio(cand, support_guard)

        if inside_ratio < self.GATE_MIN_INSIDE_RATIO:
            motivo = "frame_parcial" if support_border_touch else "referencia_desalinhada"
            return False, support, {
                "motivo": motivo,
                "detalhe": f"boca_fora_envelope_{inside_ratio:.3f}",
                "inside_ratio": float(inside_ratio),
            }

        if cand_bottom_touch_only:
            max_bottom_excess_px = int(self.GATE_MAX_BOTTOM_EXCESS_PX_RATIO * h)
            if y2 > (sy2 + max_bottom_excess_px):
                return False, support, {
                    "motivo": "frame_parcial",
                    "detalhe": f"boca_muito_abaixo_estrutura_{y2 - sy2}px",
                    "inside_ratio": float(inside_ratio),
                }

            if inside_ratio < self.GATE_MIN_INSIDE_RATIO_IF_BOTTOM_TOUCH:
                return False, support, {
                    "motivo": "frame_parcial",
                    "detalhe": f"borda_inferior_sem_suporte_{inside_ratio:.3f}",
                    "inside_ratio": float(inside_ratio),
                }

        tolerancia_vertical = int(0.08 * h)
        if y2 > (sy2 + tolerancia_vertical):
            return False, support, {
                "motivo": "referencia_desalinhada",
                "detalhe": "boca_abaixo_estrutura",
                "inside_ratio": float(inside_ratio),
            }

        return True, support, {
            "motivo": "ok",
            "detalhe": "gate_orb_v2_ok",
            "inside_ratio": float(inside_ratio),
            "cand_area_ratio": float(cand_area_ratio),
            "support_area_ratio": float(support_area_ratio),
            "cand_w_ratio": float(bw_ratio),
            "cand_h_ratio": float(bh_ratio),
            "cand_geometria_exagerada": bool(cand_geometria_exagerada),
            "cand_bottom_touch_only": bool(cand_bottom_touch_only),
            "cand_border_flags": cand_border_flags,
            "support_w_ratio": float(sw_ratio),
            "support_h_ratio": float(sh_ratio),
        }

    def _detail_has_only_bottom_touch(self, detalhe):
        detalhe = str(detalhe or "")
        if "bottom': True" not in detalhe:
            return False
        if "left': True" in detalhe or "right': True" in detalhe or "top': True" in detalhe:
            return False
        return True

    def _allow_soft_gate_rescue(self, gate_info, orb_info, fill_old):
        if not self.SOFT_RESCUE_ENABLED:
            return False

        detalhe = str((gate_info or {}).get("detalhe", "") or "")
        motivo = str((gate_info or {}).get("motivo", "") or "")
        if motivo != "frame_parcial":
            return False

        # Nunca resgata quando lateral/topo encostam.
        if detalhe.startswith("boca_encosta_borda_"):
            return False

        matches = int((orb_info or {}).get("matches", 0) or 0)
        inliers = int((orb_info or {}).get("inliers", 0) or 0)
        inlier_ratio = inliers / float(max(1, matches))
        inside_ratio = float((gate_info or {}).get("inside_ratio", 0.0) or 0.0)

        if fill_old < self.SOFT_RESCUE_MIN_FILL_OLD:
            return False
        if matches < self.SOFT_RESCUE_MIN_MATCHES:
            return False
        if inliers < self.SOFT_RESCUE_MIN_INLIERS:
            return False
        if inlier_ratio < self.SOFT_RESCUE_MIN_INLIER_RATIO:
            return False

        # Casos suaves permitidos:
        # 1) estrutura clipada apenas embaixo
        if detalhe.startswith("estrutura_clip_borda_"):
            if not self._detail_has_only_bottom_touch(detalhe):
                return False
            return (
                matches >= self.SOFT_RESCUE_CLIP_BOTTOM_MIN_MATCHES
                and inliers >= self.SOFT_RESCUE_CLIP_BOTTOM_MIN_INLIERS
            )

        # 2) borda inferior sem suporte suficiente, mas ORB convincente
        if detalhe.startswith("borda_inferior_sem_suporte_"):
            return (
                inside_ratio >= self.SOFT_RESCUE_MIN_INSIDE_RATIO
                and matches >= self.SOFT_RESCUE_MIN_MATCHES
                and inliers >= self.SOFT_RESCUE_MIN_INLIERS
            )

        # 3) estrutura pequena para alto plástico
        if detalhe == "estrutura_pequena":
            if (
                matches >= self.SOFT_RESCUE_STRUCT_SMALL_MIN_MATCHES
                and inliers >= self.SOFT_RESCUE_STRUCT_SMALL_MIN_INLIERS
            ):
                return True

            if (
                fill_old >= self.SOFT_RESCUE_STRUCT_SMALL_HIGHFILL_OLD
                and matches >= self.SOFT_RESCUE_STRUCT_SMALL_HIGHFILL_MATCHES
                and inliers >= self.SOFT_RESCUE_STRUCT_SMALL_HIGHFILL_INLIERS
                and inlier_ratio >= self.SOFT_RESCUE_STRUCT_SMALL_HIGHFILL_INLIER_RATIO
            ):
                return True

            return False

        return False

    def _warp_opening(self, img_bgr):
        if not self.ativo:
            return None, {"matches": 0, "inliers": 0, "motivo": "refiner_inativo"}

        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        kp_dst, des_dst = self.orb.detectAndCompute(gray, None)

        if des_dst is None or len(kp_dst) < 20:
            return None, {"matches": 0, "inliers": 0, "motivo": "poucos_pontos_destino"}

        knn = self.bf.knnMatch(self.des_ref, des_dst, k=2)
        good = []
        for pair in knn:
            if len(pair) < 2:
                continue
            m, n = pair
            if m.distance < 0.78 * n.distance:
                good.append(m)

        if len(good) < 12:
            return None, {"matches": len(good), "inliers": 0, "motivo": "matches_insuficientes"}

        src_pts = np.float32([self.kp_ref[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp_dst[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

        H, inlier_mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 6.0)
        if H is None:
            return None, {"matches": len(good), "inliers": 0, "motivo": "homography_falhou"}

        inliers = int(inlier_mask.sum()) if inlier_mask is not None else 0

        warped = cv2.warpPerspective(
            self.ref_mask,
            H,
            (img_bgr.shape[1], img_bgr.shape[0]),
            flags=cv2.INTER_NEAREST,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        )
        warped = (warped > 127).astype(np.uint8) * 255

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        warped = cv2.erode(warped, kernel, iterations=1)

        if int(np.count_nonzero(warped > 0)) <= 0:
            return None, {"matches": len(good), "inliers": inliers, "motivo": "warp_vazio"}

        return warped.astype(np.uint8), {
            "matches": len(good),
            "inliers": inliers,
            "motivo": "ok",
        }

    def maybe_refine(self, img_path, img_bgr, grupo, opening_repair, floor, wall, feats_atual):
        if not self.ativo:
            return feats_atual, opening_repair, None

        if grupo != "plastico":
            return feats_atual, opening_repair, None

        status_old = str(feats_atual.get("status_frame", "")).strip().lower()
        if status_old != "ok":
            return feats_atual, opening_repair, None

        try:
            fill_old = float(feats_atual.get("fill_percent_filtered", 0.0))
        except Exception:
            fill_old = 0.0

        opening_bin = (opening_repair > 0).astype(np.uint8)
        floor_in_open = ((floor > 0) & (opening_bin > 0)).astype(np.uint8)
        wall_in_open = ((wall > 0) & (opening_bin > 0)).astype(np.uint8)

        opening_area = int(np.count_nonzero(opening_bin))
        floor_area = int(np.count_nonzero(floor_in_open))
        wall_area = int(np.count_nonzero(wall_in_open))

        if opening_area <= 0:
            return feats_atual, opening_repair, None

        floor_vs_opening = floor_area / float(opening_area)
        wall_vs_opening = wall_area / float(opening_area)

        candidato = (
            fill_old >= 30.0
            and fill_old <= 68.0
            and floor_vs_opening <= 0.12
            and wall_vs_opening >= 0.08
        )

        if not candidato:
            return feats_atual, opening_repair, None

        warped_mask, info = self._warp_opening(img_bgr)
        if warped_mask is None:
            return feats_atual, opening_repair, info

        gate_ok, support_mask, gate_info = self._run_commercial_gate(
            warped_mask=warped_mask,
            floor=floor,
            wall=wall,
            img_shape=img_bgr.shape,
        )

        if not gate_ok:
            if self._allow_soft_gate_rescue(gate_info, info, fill_old):
                gate_ok = True
                gate_info = {
                    **gate_info,
                    "motivo": "ok",
                    "detalhe": f"gate_orb_v2_rescue_soft|{gate_info.get('detalhe', '')}",
                    "soft_rescue": True,
                }
            else:
                self._save_gate_reject_debug(
                    img_path=img_path,
                    img_bgr=img_bgr,
                    warped_mask=warped_mask,
                    support_mask=support_mask,
                    gate_info=gate_info,
                    fill_old=fill_old,
                    info=info,
                )
                feats_rejeitado = self._mark_feats_as_suspect(
                    feats_atual,
                    gate_info.get("motivo", "referencia_desalinhada"),
                )
                return feats_rejeitado, opening_repair, {
                    **info,
                    **gate_info,
                    "fill_old": fill_old,
                    "motivo": "gate_rejeitado",
                }

        feats_v2 = extrair_features(warped_mask, floor, wall, None, None)
        if feats_v2 is None:
            return feats_atual, opening_repair, {
                **info,
                "fill_old": fill_old,
                "motivo": "extrair_features_v2_falhou",
            }

        try:
            fill_v2 = float(feats_v2.get("fill_percent_filtered", 0.0))
        except Exception:
            fill_v2 = 0.0

        status_v2 = str(feats_v2.get("status_frame", "")).strip().lower()

        aceita = (
            status_v2 == "ok"
            and fill_v2 >= fill_old + 8.0
            and fill_v2 >= 68.0
            and fill_v2 <= 92.0
            and info.get("matches", 0) >= 50
            and info.get("inliers", 0) >= 25
        )

        if not aceita:
            return feats_atual, opening_repair, {
                **info,
                **gate_info,
                "fill_old": fill_old,
                "fill_v2": fill_v2,
                "status_v2": status_v2,
                "motivo": "nao_aceito",
            }

        feats_v2["grupo"] = grupo
        motivo_antigo = str(feats_atual.get("motivo_falha", "")).strip()
        if motivo_antigo:
            feats_v2["motivo_falha"] = motivo_antigo + "|plastico_alto_orb_v2"
        else:
            feats_v2["motivo_falha"] = "plastico_alto_orb_v2"

        overlay = img_bgr.copy()
        green = np.zeros_like(overlay)
        green[:, :] = (0, 255, 0)
        mbool = warped_mask > 0
        overlay[mbool] = cv2.addWeighted(overlay, 0.72, green, 0.28, 0)[mbool]
        contours, _ = cv2.findContours((warped_mask > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(overlay, contours, -1, (0, 255, 255), 3)

        txt = (
            f"OLD={fill_old:.2f} | V2={fill_v2:.2f} | m={info.get('matches',0)} | "
            f"in={info.get('inliers',0)} | inside={gate_info.get('inside_ratio', 0.0):.3f}"
        )
        cv2.putText(overlay, txt[:180], (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.82, (255, 255, 255), 2, cv2.LINE_AA)
        detalhe_gate = str(gate_info.get('detalhe', ''))
        if detalhe_gate:
            cv2.putText(overlay, detalhe_gate[:180], (20, 74), cv2.FONT_HERSHEY_SIMPLEX, 0.68, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.imwrite(str(self.debug_dir / f"{img_path.stem}_orb_v2.jpg"), overlay)
        cv2.imwrite(str(self.debug_dir / f"{img_path.stem}_opening_v2.png"), warped_mask)

        return feats_v2, warped_mask, {
            **info,
            **gate_info,
            "fill_old": fill_old,
            "fill_v2": fill_v2,
            "status_v2": status_v2,
            "motivo": "aceito",
        }


def _evaluate_gate_presenca_cacamba_if_available(
    image_bgr,
    floor_mask,
    wall_mask,
    opening_mask,
):
    if apply_gate_before_volumetry is None:
        return None

    try:
        gate_result, _ = apply_gate_before_volumetry(
            image_bgr=image_bgr,
            floor_mask=floor_mask,
            wall_mask=wall_mask,
            opening_mask=opening_mask,
            row={},
        )
        if hasattr(gate_result, "to_dict"):
            return gate_result.to_dict()
        if isinstance(gate_result, dict):
            return gate_result
        return None
    except Exception as e:
        return {
            "cacamba_presente": True,
            "vazia_ou_quase_vazia": False,
            "score_presenca": 0.0,
            "score_vazio": 0.0,
            "motivo": "gate_presenca_falhou",
            "detalhe": str(e),
            "metrics": {},
        }


def _render_debug_gate_presenca(img_bgr, gate_dict):
    overlay = img_bgr.copy()
    h, w = overlay.shape[:2]

    panel_h = 118
    panel = overlay.copy()
    cv2.rectangle(panel, (0, 0), (w, panel_h), (0, 0, 0), -1)
    overlay = cv2.addWeighted(panel, 0.55, overlay, 0.45, 0)

    motivo = str((gate_dict or {}).get("motivo", "gate_presenca"))
    detalhe = str((gate_dict or {}).get("detalhe", ""))
    presente = bool((gate_dict or {}).get("cacamba_presente", True))
    vazio = bool((gate_dict or {}).get("vazia_ou_quase_vazia", False))
    score_presenca = float((gate_dict or {}).get("score_presenca", 0.0) or 0.0)
    score_vazio = float((gate_dict or {}).get("score_vazio", 0.0) or 0.0)

    if not presente:
        color = (0, 0, 255)
        title = "GATE PRESENCA: CACAMBA AUSENTE / TROCA"
    elif vazio:
        color = (0, 180, 255)
        title = "GATE PRESENCA: CACAMBA VAZIA / QUASE VAZIA"
    else:
        color = (0, 200, 0)
        title = "GATE PRESENCA: CACAMBA PRESENTE"

    cv2.putText(overlay, title, (20, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.90, color, 2, cv2.LINE_AA)
    cv2.putText(
        overlay,
        f"motivo={motivo} | detalhe={detalhe}"[:170],
        (20, 68),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.68,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        overlay,
        f"score_presenca={score_presenca:.3f} | score_vazio={score_vazio:.3f} | presente={presente} | vazio={vazio}",
        (20, 98),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.64,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    return overlay


def _render_debug_boca_v2(img_bgr, boca_result):
    overlay = img_bgr.copy()
    h, w = overlay.shape[:2]

    panel_h = 118
    panel = overlay.copy()
    cv2.rectangle(panel, (0, 0), (w, panel_h), (0, 0, 0), -1)
    overlay = cv2.addWeighted(panel, 0.55, overlay, 0.45, 0)

    ok = bool((boca_result or {}).get("ok", False))
    motivo = str((boca_result or {}).get("motivo", "sem_boca_modelo_v2"))
    conf = float((boca_result or {}).get("conf", 0.0) or 0.0)
    mask = (boca_result or {}).get("mask", None)
    poly = (boca_result or {}).get("poly", None)
    mask_area = int((boca_result or {}).get("mask_area", 0) or 0)
    comp_ratio = float((boca_result or {}).get("component_ratio", 0.0) or 0.0)

    if mask is not None and int(np.count_nonzero(mask > 0)) > 0:
        green = np.zeros_like(overlay)
        green[:, :] = (0, 255, 0)
        mbool = mask > 0
        overlay[mbool] = cv2.addWeighted(overlay, 0.80, green, 0.20, 0)[mbool]

    if poly is not None and len(poly) >= 3:
        pts = np.asarray(poly, dtype=np.int32).reshape((-1, 1, 2))
        cv2.polylines(overlay, [pts], True, (0, 255, 255), 3)

    color = (0, 200, 0) if ok else (0, 0, 255)
    title = "BOCA V2: OK" if ok else "BOCA V2: REJEITADA"
    cv2.putText(overlay, title, (20, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.90, color, 2, cv2.LINE_AA)
    cv2.putText(overlay, f"motivo={motivo} | conf={conf:.3f}"[:170], (20, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.68, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(overlay, f"mask_area={mask_area} | comp_ratio={comp_ratio:.3f}"[:170], (20, 98), cv2.FONT_HERSHEY_SIMPLEX, 0.64, (255, 255, 255), 2, cv2.LINE_AA)
    return overlay


def main():
    csv_path = CSV_DIR / "resultado_volumetria.csv"
    resumo_path = CSV_DIR / "dashboard_resumo.csv"
    run_info_path = CSV_DIR / "run_info.json"
    repair_audit_path = CSV_DIR / "opening_repair_audit.csv"
    repair_audit_rows = []

    repair_debug_dir = DEBUG_DIR / "opening_repair"
    repair_debug_dir.mkdir(parents=True, exist_ok=True)

    existing_rows = base.load_existing_rows(csv_path)
    processed_names = {r["arquivo"] for r in existing_rows if r.get("arquivo")}

    segmentador = SegmentadorVolumetria()
    segmentador_contaminantes = SegmentadorContaminantes()
    human_detector = base.build_human_detector()
    plastic_orb_v2 = PlasticHighORBRefiner()
    boca_v2_ativo = detectar_boca is not None
    gate_presenca_ativo = False

    image_files = sorted([p for p in INPUT_DIR.glob("*") if p.suffix.lower() in VALID_EXTS])
    if not image_files:
        print("Nenhuma imagem encontrada em:", INPUT_DIR)
        return

    new_image_files = [p for p in image_files if p.name not in processed_names]

    print(f"TOTAL INPUT = {len(image_files)}")
    print(f"JA PROCESSADAS = {len(processed_names)}")
    print(f"NOVAS = {len(new_image_files)}")

    if not new_image_files:
        base.write_rows(csv_path, existing_rows)
        base.write_dashboard(resumo_path, existing_rows)

        run_info = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "mode": "incremental_boca_v2_gate_estrutural",
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
            "orb_v2_rejeitados_debug_dir": str(plastic_orb_v2.reject_debug_dir),
            "masks_opening_dir": str(OPENING_MASK_DIR),
            "masks_floor_dir": str(FLOOR_MASK_DIR),
            "masks_wall_dir": str(WALL_MASK_DIR),
            "contaminantes_modelo_ativo": segmentador_contaminantes.ativo,
            "human_gate_ativo": True,
            "overflow_detector_ativo": True,
            "plastic_orb_v2_ativo": plastic_orb_v2.ativo,
            "boca_v2_ativo": boca_v2_ativo,
            "gate_presenca_cacamba_ativo": gate_presenca_ativo,
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
    print(f"PLASTIC_ORB_V2 = {'ATIVO' if plastic_orb_v2.ativo else 'INATIVO'}")
    print(f"BOCA_V2_GATE = {'ATIVO' if boca_v2_ativo else 'INATIVO'}")
    print(f"GATE_PRESENCA_CACAMBA = {'ATIVO' if gate_presenca_ativo else 'INATIVO'}")

    new_rows = []
    ok_consec_criticos_by_group = base.build_previous_critical_counters(existing_rows)

    for img_path, img, opening, floor, wall in stage:
        name = img_path.stem
        grupo = detect_group(name)

        boca_v2_result = None
        if boca_v2_ativo:
            try:
                boca_v2_result = detectar_boca(img)
            except Exception as e:
                boca_v2_result = {
                    "ok": False,
                    "motivo": "boca_v2_falhou",
                    "conf": 0.0,
                    "mask": None,
                    "poly": None,
                    "erro": str(e),
                }

            print(
                f"{img_path.name} -> BOCA_V2 | "
                f"ok={boca_v2_result.get('ok')} | "
                f"motivo={boca_v2_result.get('motivo')} | "
                f"conf={float(boca_v2_result.get('conf', 0.0) or 0.0):.3f} | "
                f"mask_area={int(boca_v2_result.get('mask_area', 0) or 0)} | "
                f"comp_ratio={float(boca_v2_result.get('component_ratio', 0.0) or 0.0):.3f}"
            )

            if not bool(boca_v2_result.get("ok", False)):
                motivo_gate = str(boca_v2_result.get("motivo") or "sem_boca_modelo_v2")
                detalhe_gate = str(boca_v2_result.get("erro") or "")
                dbg_gate = _render_debug_boca_v2(img, boca_v2_result)
                cv2.imwrite(str(DEBUG_DIR / f"{name}_debug.jpg"), dbg_gate)

                row = base.normalize_row({
                    "arquivo": img_path.name,
                    "grupo": grupo,
                    "classe_predita": "",
                    "status_frame": "suspeito",
                    "motivo_falha": motivo_gate,
                    "confidence_final": f"{float(boca_v2_result.get('conf', 0.0) or 0.0):.2f}",
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
                    "materiais_detectados_raw": "",
                    "deteccoes_contaminantes_json": "",
                    "contaminantes_detectados": "",
                    "alerta_contaminacao": 0,
                    "tipo_contaminacao": "",
                    "severidade_contaminacao": "",
                    "cacamba_esperada": "",
                    "material_esperado": "",
                })
                row = base.sanitize_row_final(row)
                new_rows.append(row)

                print(
                    f"{img_path.name} -> grupo={grupo} | status=suspeito | "
                    f"fill= | estado=revisar | ok_consec=0 | alerta=0 | "
                    f"motivo={motivo_gate} | detalhe={detalhe_gate if detalhe_gate else '-'}"
                )
                continue

            opening = (boca_v2_result["mask"].copy() > 0).astype(np.uint8) * 255
        else:
            gate_presenca = _evaluate_gate_presenca_cacamba_if_available(
                image_bgr=img,
                floor_mask=floor,
                wall_mask=wall,
                opening_mask=opening,
            )

            if gate_presenca is not None:
                print(
                    f"{img_path.name} -> GATE PRESENCA | "
                    f"presente={gate_presenca.get('cacamba_presente')} | "
                    f"vazio={gate_presenca.get('vazia_ou_quase_vazia')} | "
                    f"motivo={gate_presenca.get('motivo')} | "
                    f"score_presenca={float(gate_presenca.get('score_presenca', 0.0) or 0.0):.3f} | "
                    f"score_vazio={float(gate_presenca.get('score_vazio', 0.0) or 0.0):.3f}"
                )

            if gate_presenca is not None and (
                (not bool(gate_presenca.get("cacamba_presente", True)))
                or bool(gate_presenca.get("vazia_ou_quase_vazia", False))
            ):
                motivo_gate = str(gate_presenca.get("motivo") or "suspeito_cacamba_ausente")
                detalhe_gate = str(gate_presenca.get("detalhe") or "")
                dbg_gate = _render_debug_gate_presenca(img, gate_presenca)
                cv2.imwrite(str(DEBUG_DIR / f"{name}_debug.jpg"), dbg_gate)

                row = base.normalize_row({
                    "arquivo": img_path.name,
                    "grupo": grupo,
                    "classe_predita": "",
                    "status_frame": "suspeito",
                    "motivo_falha": motivo_gate,
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
                    "materiais_detectados_raw": "",
                    "deteccoes_contaminantes_json": "",
                    "contaminantes_detectados": "",
                    "alerta_contaminacao": 0,
                    "tipo_contaminacao": "",
                    "severidade_contaminacao": "",
                    "cacamba_esperada": "",
                    "material_esperado": "",
                })
                row = base.sanitize_row_final(row)
                new_rows.append(row)

                print(
                    f"{img_path.name} -> grupo={grupo} | status=suspeito | "
                    f"fill= | estado=revisar | ok_consec=0 | alerta=0 | "
                    f"motivo={motivo_gate} | detalhe={detalhe_gate if detalhe_gate else '-'}"
                )
                continue

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

        human_dets = base.detectar_humanos(human_detector, img)
        human_hit, human_info = base.humano_intersecta_abertura(human_dets, opening)

        if human_hit:
            dbg = base.render_debug_humano(img, opening, human_info)
            cv2.imwrite(str(DEBUG_DIR / f"{name}_debug.jpg"), dbg)

            row = base.normalize_row({
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
            row = base.sanitize_row_final(row)
            new_rows.append(row)

            print(
                f"{img_path.name} -> grupo={grupo} | status=suspeito | "
                f"fill= | estado=revisar | ok_consec=0 | alerta=0 | "
                f"motivo=humano_na_abertura | materiais={materiais_detectados_raw if materiais_detectados_raw else 'nenhum'}"
            )
            continue

        opening_raw = opening.copy()
        if boca_v2_ativo and boca_v2_result is not None and boca_v2_result.get("ok"):
            opening_repair = opening_raw.copy()
            repair_info = {"aplicado": False, "repair_kind": "boca_v2", "motivos": ["boca_v2"]}
        else:
            opening_repair, repair_info = base.reparar_opening_fragmentada(opening_raw, wall)

        op_stats_dbg = base._mask_stats((opening_raw > 0).astype(np.uint8) * 255)
        op_after_stats_dbg = base._mask_stats((opening_repair > 0).astype(np.uint8) * 255)
        wall_stats_dbg = base._mask_stats(base._largest_component(wall))

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
            dbg_repair = base.render_debug_opening_repair(
                img,
                opening_raw,
                wall,
                opening_repair,
                repair_info,
            )
            cv2.imwrite(str(repair_debug_dir / f"{name}_opening_repair.jpg"), dbg_repair)

        feats = extrair_features(opening_repair, floor, wall, None, None)
        if feats is None:
            row = base.normalize_row({
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
            row = base.sanitize_row_final(row)
            new_rows.append(row)
            print(f"SEM OPENING INNER VALIDO: {img_path.name}")
            continue

        feats["grupo"] = grupo
        feats = base.sanitize_feats_for_dashboard(feats)

        feats, opening_repair_v2, orb_info = plastic_orb_v2.maybe_refine(
            img_path=img_path,
            img_bgr=img,
            grupo=grupo,
            opening_repair=opening_repair,
            floor=floor,
            wall=wall,
            feats_atual=feats,
        )

        if orb_info and orb_info.get("motivo") == "aceito":
            opening_repair = opening_repair_v2
            feats = base.sanitize_feats_for_dashboard(feats)
            print(
                f"{img_path.name} -> PLASTICO ALTOS V2 ORB | "
                f"fill_old={orb_info.get('fill_old', 0.0):.2f} | "
                f"fill_v2={orb_info.get('fill_v2', 0.0):.2f} | "
                f"matches={orb_info.get('matches', 0)} | "
                f"inliers={orb_info.get('inliers', 0)}"
            )
        elif orb_info and orb_info.get("motivo") == "gate_rejeitado":
            feats = base.sanitize_feats_for_dashboard(feats)
            print(
                f"{img_path.name} -> PLASTICO ALTOS V2 GATE REJEITADO | "
                f"motivo={feats.get('motivo_falha', orb_info.get('motivo', 'gate_rejeitado'))} | "
                f"detalhe={orb_info.get('detalhe', '')} | "
                f"matches={orb_info.get('matches', 0)} | "
                f"inliers={orb_info.get('inliers', 0)}"
            )

        motivo_falha_existente = str(feats.get("motivo_falha", "")).strip()
        motivo_falha = ""
        motivos_gate_preservados = {"frame_parcial", "referencia_desalinhada"}

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
            if motivo_falha_existente in motivos_gate_preservados:
                motivo_falha = motivo_falha_existente
            elif feats["suspeita_expected_overlap_baixo"]:
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

        row = base.normalize_row({
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
        row = base.sanitize_row_final(row)
        new_rows.append(row)

        print(
            f"{img_path.name} -> grupo={grupo} | status={row['status_frame']} | "
            f"fill_csv={row['fill_percent_filtrado'] if row['fill_percent_filtrado'] != '' else 'VAZIO'} | "
            f"estado={row['estado_dashboard']} | "
            f"ok_consec={ok_consecutivos_criticos} | alerta={row['alerta_dashboard']} | "
            f"motivo={row['motivo_falha']} | "
            f"materiais={materiais_detectados_raw if materiais_detectados_raw else 'nenhum'}"
        )

    all_rows = base.merge_rows(existing_rows, new_rows)

    base.write_rows(csv_path, all_rows)
    base.write_dashboard(resumo_path, all_rows)

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
        "mode": "incremental_boca_v2_gate_estrutural",
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
        "orb_v2_rejeitados_debug_dir": str(plastic_orb_v2.reject_debug_dir),
        "masks_opening_dir": str(OPENING_MASK_DIR),
        "masks_floor_dir": str(FLOOR_MASK_DIR),
        "masks_wall_dir": str(WALL_MASK_DIR),
        "contaminantes_modelo_ativo": segmentador_contaminantes.ativo,
        "human_gate_ativo": True,
        "overflow_detector_ativo": True,
        "plastic_orb_v2_ativo": plastic_orb_v2.ativo,
        "gate_presenca_cacamba_ativo": gate_presenca_ativo,
    }

    with open(run_info_path, "w", encoding="utf-8") as f:
        json.dump(run_info, f, ensure_ascii=False, indent=2)

    print()
    print("CONCLUIDO")
    print("MODO: incremental_boca_v2_gate_estrutural")
    print("CSV:", csv_path)
    print("RESUMO:", resumo_path)
    print("RUN_INFO:", run_info_path)
    print("OPENING REPAIR AUDIT:", repair_audit_path)
    print("DEBUG:", DEBUG_DIR)
    print("DEBUG OPENING REPAIR:", repair_debug_dir)
    print("DEBUG ORB V2 REJEITADOS:", plastic_orb_v2.reject_debug_dir)
    print("MASK OPENING:", OPENING_MASK_DIR)
    print("MASK FLOOR:", FLOOR_MASK_DIR)
    print("MASK WALL:", WALL_MASK_DIR)
    print(f"NOVAS PROCESSADAS: {len(new_rows)}")
    print(f"TOTAL NO CSV: {len(all_rows)}")


if __name__ == "__main__":
    main()
