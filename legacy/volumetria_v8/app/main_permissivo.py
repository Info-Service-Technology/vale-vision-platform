import csv
from pathlib import Path
import cv2

from config import (
    INPUT_DIR,
    CSV_DIR,
    DEBUG_DIR,
    OPENING_MASK_DIR,
    FLOOR_MASK_DIR,
    CONSEC_OK_PARA_TROCA,
    ALERTA_VERMELHO,
)
from segmentador import SegmentadorVolumetria
from motor_volumetria_permissivo import (
    detect_group,
    load_expected_floor_mask,
    compute_reference_opening_area,
    extrair_features,
    estado_dashboard_from_fill,
    render_debug,
)

VALID_EXTS = [".jpg", ".jpeg", ".png", ".bmp", ".webp"]


def main():
    segmentador = SegmentadorVolumetria()
    expected_floor_mask = load_expected_floor_mask()

    image_files = sorted([p for p in INPUT_DIR.glob("*") if p.suffix.lower() in VALID_EXTS])
    if not image_files:
        print("Nenhuma imagem encontrada em:", INPUT_DIR)
        return

    # 1) segmentar tudo e salvar máscaras
    opening_masks_for_ref = []
    stage = []

    for img_path in image_files:
        img, opening_mask, floor_mask = segmentador.segmentar(img_path)

        segmentador.salvar_mask(opening_mask, OPENING_MASK_DIR / f"{img_path.stem}.png")
        segmentador.salvar_mask(floor_mask, FLOOR_MASK_DIR / f"{img_path.stem}.png")

        opening_masks_for_ref.append((opening_mask * 255).astype("uint8"))
        stage.append(
            (
                img_path,
                img,
                (opening_mask * 255).astype("uint8"),
                (floor_mask * 255).astype("uint8"),
            )
        )

    opening_area_ref = compute_reference_opening_area(opening_masks_for_ref)
    if opening_area_ref is None:
        print("ERRO: nao foi possivel calcular opening_area_ref")
        return

    print(f"OPENING_AREA_REF = {opening_area_ref:.2f}")

    rows = []
    dashboard_resumo = {}
    ok_consec_criticos_by_group = {}

    # 2) volumetria
    for img_path, img, opening, floor in stage:
        name = img_path.stem
        grupo = detect_group(name)

        feats = extrair_features(opening, floor, expected_floor_mask, opening_area_ref)
        if feats is None:
            rows.append({
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
                "opening_area_ref": f"{opening_area_ref:.2f}",
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
            })
            print(f"SEM OPENING INNER VALIDO: {img_path.name}")
            continue

        feats["grupo"] = grupo

        motivo_falha = ""

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
            if feats["suspeita_expected_overlap_baixo"]:
                motivo_falha = "suspeito_overlap"
            elif feats["suspeita_floor_filtrado_colapsou"]:
                motivo_falha = "suspeito_colapso_filtro"
            elif feats["suspeita_opening_area"]:
                motivo_falha = "suspeito_opening_area"
            elif feats["suspeita_opening_borda"]:
                motivo_falha = "suspeito_borda"
            else:
                motivo_falha = "suspeito_generico"

        feats["motivo_falha"] = motivo_falha

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

        rows.append({
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
            "opening_area_ref": f"{feats['opening_area_ref']:.2f}",
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
        })

        dashboard_resumo[grupo] = {
            "grupo": grupo,
            "ultimo_arquivo": img_path.name,
            "status_frame": feats["status_frame"],
            "motivo_falha": feats["motivo_falha"],
            "fill_percent_filtrado": f"{feats['fill_percent_filtered']:.6f}",
            "estado_dashboard": feats["estado_dashboard"],
            "alerta_dashboard": feats["alerta_dashboard"],
        }

        print(
            f"{img_path.name} -> grupo={grupo} | status={feats['status_frame']} | "
            f"fill={fill:.2f}% | estado={estado_dashboard} | "
            f"ok_consec={ok_consecutivos_criticos} | alerta={alerta_dashboard}"
        )

    csv_path = CSV_DIR / "resultado_volumetria.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)

    resumo_path = CSV_DIR / "dashboard_resumo.csv"
    with open(resumo_path, "w", newline="", encoding="utf-8-sig") as f:
        fieldnames = [
            "grupo",
            "ultimo_arquivo",
            "status_frame",
            "motivo_falha",
            "fill_percent_filtrado",
            "estado_dashboard",
            "alerta_dashboard",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(dashboard_resumo.values())

    print()
    print("CONCLUIDO")
    print("CSV:", csv_path)
    print("RESUMO:", resumo_path)
    print("DEBUG:", DEBUG_DIR)
    print("MASK OPENING:", OPENING_MASK_DIR)
    print("MASK FLOOR:", FLOOR_MASK_DIR)


if __name__ == "__main__":
    main()