from pathlib import Path
import cv2
import numpy as np

SRC_DIR = Path(r"E:\PROJETO VALE\PRODUTO_VOLUMETRIA_RELEASE_V1\output\masks_opening")
OUT_MASK = Path(r"E:\PROJETO VALE\PRODUTO_VOLUMETRIA_RELEASE_V8\config\expected_opening_mask.png")
OUT_PREVIEW = Path(r"E:\PROJETO VALE\PRODUTO_VOLUMETRIA_RELEASE_V8\config\expected_opening_mask_preview.png")

VOTE_THRESHOLD = 0.15   # 15% das máscaras
MIN_COMPONENT_AREA = 5000

def keep_largest_component(mask_bin: np.ndarray) -> np.ndarray:
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask_bin, connectivity=8)
    if num_labels <= 1:
        return mask_bin

    best_label = 0
    best_area = 0
    for label in range(1, num_labels):
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area > best_area:
            best_area = area
            best_label = label

    out = np.zeros_like(mask_bin)
    if best_label > 0:
        out[labels == best_label] = 1
    return out.astype(np.uint8)

def remove_small_components(mask_bin: np.ndarray, min_area: int) -> np.ndarray:
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask_bin, connectivity=8)
    out = np.zeros_like(mask_bin)
    for label in range(1, num_labels):
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area >= min_area:
            out[labels == label] = 1
    return out.astype(np.uint8)

paths = sorted(SRC_DIR.glob("*.png"))
if not paths:
    raise RuntimeError(f"Nenhuma máscara encontrada em: {SRC_DIR}")

base = cv2.imread(str(paths[0]), cv2.IMREAD_GRAYSCALE)
if base is None:
    raise RuntimeError(f"Falha ao abrir: {paths[0]}")

h, w = base.shape[:2]
acc = np.zeros((h, w), dtype=np.float32)
ok = 0

for p in paths:
    m = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
    if m is None:
        print(f"[IGNORADO] {p.name}")
        continue

    if m.shape[:2] != (h, w):
        m = cv2.resize(m, (w, h), interpolation=cv2.INTER_NEAREST)

    m = (m > 0).astype(np.uint8)
    acc += m
    ok += 1

if ok == 0:
    raise RuntimeError("Nenhuma máscara válida foi lida.")

freq = acc / float(ok)

# envelope robusto do opening
mask = (freq >= VOTE_THRESHOLD).astype(np.uint8)

# fecha pequenos vãos
k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k_close, iterations=1)

# limpa e mantém o componente principal
mask = remove_small_components(mask, MIN_COMPONENT_AREA)
mask = keep_largest_component(mask)

# hull final para estabilizar o contorno da boca
contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
if not contours:
    raise RuntimeError("Não foi possível gerar contorno final do expected_opening_mask.")

largest = max(contours, key=cv2.contourArea)
hull = cv2.convexHull(largest)

final_mask = np.zeros_like(mask, dtype=np.uint8)
cv2.drawContours(final_mask, [hull], -1, 255, thickness=-1)

OUT_MASK.parent.mkdir(parents=True, exist_ok=True)
cv2.imwrite(str(OUT_MASK), final_mask)

preview = (freq * 255.0).clip(0, 255).astype(np.uint8)
cv2.imwrite(str(OUT_PREVIEW), preview)

print(f"MÁSCARAS LIDAS: {ok}")
print(f"SALVO: {OUT_MASK}")
print(f"PREVIEW: {OUT_PREVIEW}")