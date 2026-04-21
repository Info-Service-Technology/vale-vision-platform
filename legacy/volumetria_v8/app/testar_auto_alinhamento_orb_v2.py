
from pathlib import Path
import sys
import cv2
import numpy as np

# ===== AJUSTE ESTES CAMINHOS SE PRECISAR =====
APP_DIR = Path(r"E:\PROJETO VALE\PACOTE_PILOTO_VM\PRODUTO_VOLUMETRIA_RELEASE_V8\app")
REF_IMG = Path(r"E:\PROJETO VALE\V2_ALTOS\REF\plastico_GF0191275_20260305123930508_MD_WITH_TARGET.jpg")
REF_MASK = Path(r"E:\PROJETO VALE\V2_ALTOS\REF\opening_ref_mask.png")
ALTOS_DIR = Path(r"E:\PROJETO VALE\V2_ALTOS\ALTOS_ERRADOS")
OUT_DIR = Path(r"E:\PROJETO VALE\V2_ALTOS\ORB_AUTO_V2")
OUT_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(APP_DIR))
from segmentador import SegmentadorVolumetria
from motor_volumetria_permissivo import extrair_features

def mask255(mask):
    return ((mask > 0).astype(np.uint8) * 255)

def fill_of(opening_mask, floor_mask, wall_mask):
    feats = extrair_features(mask255(opening_mask), mask255(floor_mask), mask255(wall_mask), None, None)
    if feats is None:
        return None, "erro"
    try:
        return float(feats.get("fill_percent_filtered", 0.0)), str(feats.get("status_frame", ""))
    except Exception:
        return None, "erro"

def main():
    ref_img = cv2.imread(str(REF_IMG))
    ref_mask = cv2.imread(str(REF_MASK), cv2.IMREAD_GRAYSCALE)

    if ref_img is None:
        raise RuntimeError(f"Falha ao ler imagem referência: {REF_IMG}")
    if ref_mask is None:
        raise RuntimeError(f"Falha ao ler máscara referência: {REF_MASK}")

    ref_gray = cv2.cvtColor(ref_img, cv2.COLOR_BGR2GRAY)

    orb = cv2.ORB_create(
        nfeatures=5000,
        scaleFactor=1.2,
        nlevels=8,
        edgeThreshold=15,
        patchSize=31,
        fastThreshold=10
    )
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)

    kp_ref, des_ref = orb.detectAndCompute(ref_gray, None)
    if des_ref is None or len(kp_ref) < 20:
        raise RuntimeError("Poucos pontos ORB na referência")

    seg = SegmentadorVolumetria()
    rows = ["arquivo,fill_old,status_old,fill_orb,status_orb,matches,inliers"]

    for img_path in sorted(ALTOS_DIR.glob("*.jpg")):
        img = cv2.imread(str(img_path))
        if img is None:
            continue

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        kp_dst, des_dst = orb.detectAndCompute(gray, None)
        if des_dst is None or len(kp_dst) < 20:
            print(f"FALHA ORB: {img_path.name} | poucos pontos no destino")
            continue

        knn = bf.knnMatch(des_ref, des_dst, k=2)
        good = []
        for pair in knn:
            if len(pair) < 2:
                continue
            m, n = pair
            if m.distance < 0.78 * n.distance:
                good.append(m)

        if len(good) < 12:
            print(f"FALHA MATCH: {img_path.name} | good={len(good)}")
            continue

        src_pts = np.float32([kp_ref[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp_dst[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

        H, inlier_mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 6.0)
        if H is None:
            print(f"FALHA HOMOGRAPHY: {img_path.name}")
            continue

        inliers = int(inlier_mask.sum()) if inlier_mask is not None else 0

        warped = cv2.warpPerspective(
            ref_mask,
            H,
            (img.shape[1], img.shape[0]),
            flags=cv2.INTER_NEAREST,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0
        )
        warped = (warped > 127).astype(np.uint8) * 255

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        warped = cv2.erode(warped, kernel, iterations=1)

        _, opening_old, floor, wall = seg.segmentar(img_path)

        fill_old, status_old = fill_of(opening_old, floor, wall)
        fill_orb, status_orb = fill_of(warped, floor, wall)

        overlay = img.copy()
        green = np.zeros_like(overlay)
        green[:, :] = (0, 255, 0)
        mbool = warped > 0
        overlay[mbool] = cv2.addWeighted(overlay, 0.72, green, 0.28, 0)[mbool]

        contours, _ = cv2.findContours(warped, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(overlay, contours, -1, (0, 255, 255), 3)

        old_txt = "NA" if fill_old is None else f"{fill_old:.2f}"
        orb_txt = "NA" if fill_orb is None else f"{fill_orb:.2f}"
        txt = f"OLD={old_txt} | ORB={orb_txt} | m={len(good)} | in={inliers}"
        cv2.putText(overlay, txt, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255,255,255), 2, cv2.LINE_AA)

        out_overlay = OUT_DIR / f"{img_path.stem}_overlay_orb.jpg"
        out_mask = OUT_DIR / f"{img_path.stem}_opening_orb.png"
        cv2.imwrite(str(out_overlay), overlay)
        cv2.imwrite(str(out_mask), warped)

        old_s = "" if fill_old is None else f"{fill_old:.6f}"
        orb_s = "" if fill_orb is None else f"{fill_orb:.6f}"
        rows.append(f'"{img_path.name}","{old_s}","{status_old}","{orb_s}","{status_orb}","{len(good)}","{inliers}"')

        print(f"{img_path.name} | OLD={old_s} ({status_old}) | ORB={orb_s} ({status_orb}) | matches={len(good)} | inliers={inliers}")

    csv_path = OUT_DIR / "comparativo_fill_orb_auto.csv"
    csv_path.write_text("\n".join(rows), encoding="utf-8-sig")
    print(f"\nCSV GERADO: {csv_path}")
    print(f"RESULTADOS EM: {OUT_DIR}")

if __name__ == "__main__":
    main()
