import re
from pathlib import Path

path = Path(r"E:\PROJETO VALE\PACOTE_PILOTO_VM\PRODUTO_VOLUMETRIA_RELEASE_V8\app\main_incremental.py")
text = path.read_text(encoding="utf-8")

novo_bloco = r'''
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

        # HOTFIX CONSERVADOR:
        # - sobe score minimo
        # - exige bbox com tamanho/plausibilidade de pessoa
        # - reduz falsos positivos em quinas/chapas/estruturas
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

        # HOTFIX CONSERVADOR:
        # - exige intersecao mais real com a abertura
        # - mata falso positivo fraco como o da lateral azul
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


def render_debug_humano(
'''

pattern = r'def build_human_detector\(\):.*?def render_debug_humano\('
novo_texto, n = re.subn(pattern, novo_bloco, text, flags=re.DOTALL)

if n != 1:
    raise RuntimeError(f"Falha no patch. Substituicoes encontradas: {n}")

path.write_text(novo_texto, encoding="utf-8")
print("[OK] Patch do gate de humano aplicado com sucesso")
