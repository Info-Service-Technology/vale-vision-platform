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

VALID_EXTS = [".jpg", ".jpeg", ".png", ".bmp", ".webp"]

RESULT_COLUMNS = [
    "arquivo",
    "grupo",
    "classe_predita",
    "status_frame",
    "motivo_falha",
    "confidence_final",
    "fill_percent_filtrado",
    "estado_dashboard",
    "fill_temporal",
    "estado_dashboard_temporal",
    "alerta_dashboard",
    "ok_consecutivos_criticos",
    "opening_area",
    "opening_area_ref",
    "opening_area_ratio_ref",
    "floor_area_bruto",
    "floor_area_filtrado",
    "expected_overlap_ratio",
    "filtered_vs_raw_ratio",
    "divergencia_pp",
    "suspeita_opening_borda",
    "suspeita_opening_area",
    "suspeita_floor_excessivo",
    "suspeita_floor_quase_zero",
    "suspeita_divergencia_bruto_filtrado",
    "suspeita_expected_overlap_baixo",
    "suspeita_floor_filtrado_colapsou",
    "materiais_detectados_raw",
    "deteccoes_contaminantes_json",
    "contaminantes_detectados",
    "alerta_contaminacao",
    "tipo_contaminacao",
    "severidade_contaminacao",
    "cacamba_esperada",
    "material_esperado",
]

DASHBOARD_COLUMNS = [
    "grupo",
    "ultimo_arquivo",
    "status_frame",
    "motivo_falha",
    "fill_percent_filtrado",
    "estado_dashboard",
    "alerta_dashboard",
    "materiais_detectados_raw",
    "contaminantes_detectados",
    "alerta_contaminacao",
    "tipo_contaminacao",
    "severidade_contaminacao",
]


def normalize_row(row: dict) -> dict:
    out = {k: row.get(k, "") for k in RESULT_COLUMNS}

    if out["alerta_contaminacao"] == "":
        out["alerta_contaminacao"] = 0
    if out["alerta_dashboard"] == "":
        out["alerta_dashboard"] = 0
    if out["ok_consecutivos_criticos"] == "":
        out["ok_consecutivos_criticos"] = 0
    if out["severidade_contaminacao"] == "":
        out["severidade_contaminacao"] = 0

    return out


def load_existing_rows(csv_path: Path) -> list[dict]:
    if not csv_path.exists():
        return []

    with open(csv_path, "r", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    return [normalize_row(r) for r in rows]


def write_rows(csv_path: Path, rows: list[dict]) -> None:
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=RESULT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def write_dashboard(csv_path: Path, rows: list[dict]) -> None:
    resumo_por_grupo = {}

    for row in rows:
        grupo = row.get("grupo", "")
        if not grupo:
            continue

        resumo_por_grupo[grupo] = {
            "grupo": grupo,
            "ultimo_arquivo": row.get("arquivo", ""),
            "status_frame": row.get("status_frame", ""),
            "motivo_falha": row.get("motivo_falha", ""),
            "fill_percent_filtrado": row.get("fill_percent_filtrado", ""),
            "estado_dashboard": row.get("estado_dashboard", ""),
            "alerta_dashboard": row.get("alerta_dashboard", 0),
            "materiais_detectados_raw": row.get("materiais_detectados_raw", ""),
            "contaminantes_detectados": row.get("contaminantes_detectados", ""),
            "alerta_contaminacao": row.get("alerta_contaminacao", 0),
            "tipo_contaminacao": row.get("tipo_contaminacao", ""),
            "severidade_contaminacao": row.get("severidade_contaminacao", 0),
        }

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=DASHBOARD_COLUMNS)
        writer.writeheader()
        writer.writerows(resumo_por_grupo.values())


def merge_rows(existing_rows: list[dict], new_rows: list[dict]) -> list[dict]:
    merged = {}
    order = []

    for row in existing_rows + new_rows:
        key = row["arquivo"]
        if key not in merged:
            order.append(key)
        merged[key] = normalize_row(row)

    return [merged[k] for k in order]


def parse_float_safe(v, default=0.0):
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default


def build_previous_critical_counters(rows: list[dict]) -> dict[str, int]:
    counters = {}

    for row in rows:
        grupo = row.get("grupo", "")
        if not grupo:
            continue

        if grupo not in counters:
            counters[grupo] = 0

        status_frame = row.get("status_frame", "")
        fill = parse_float_safe(row.get("fill_percent_filtrado", ""), default=0.0)

        if status_frame == "ok" and fill >= ALERTA_VERMELHO:
            counters[grupo] += 1
        else:
            counters[grupo] = 0

    return counters


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
        winStride=(4, 4),
        padding=(16, 16),
        scale=1.02
    )

    detections = []
    for (x, y, bw, bh), score in zip(rects, weights):
        score = float(score)

        if bw < 40 or bh < 80:
            continue

        if scale != 1.0:
            x = int(x / scale)
            y = int(y / scale)
            bw = int(bw / scale)
            bh = int(bh / scale)

        detections.append({
            "bbox": [int(x), int(y), int(x + bw), int(y + bh)],
            "score": round(score, 4),
        })

    return detections


def humano_intersecta_abertura(
    detections,
    opening_mask,
    min_overlap_pixels=1200,
    min_overlap_ratio=0.05,
    min_outside_pixels=900,
    max_inside_ratio=0.85,
):
    opening_bin = (opening_mask > 0).astype(np.uint8)
    h, w = opening_bin.shape[:2]

    for det in detections:
        x1, y1, x2, y2 = det["bbox"]

        x1 = max(0, min(w, x1))
        y1 = max(0, min(h, y1))
        x2 = max(0, min(w, x2))
        y2 = max(0, min(h, y2))

        if x2 <= x1 or y2 <= y1:
            continue

        roi = opening_bin[y1:y2, x1:x2]
        overlap_pixels = int(np.count_nonzero(roi))
        box_area = int((x2 - x1) * (y2 - y1))
        overlap_ratio = overlap_pixels / box_area if box_area > 0 else 0.0
        outside_pixels = box_area - overlap_pixels
        inside_ratio = overlap_ratio

        if (
            overlap_pixels >= min_overlap_pixels
            and overlap_ratio >= min_overlap_ratio
            and outside_pixels >= min_outside_pixels
            and inside_ratio <= max_inside_ratio
        ):
            out = det.copy()
            out["overlap_pixels"] = overlap_pixels
            out["overlap_ratio"] = round(overlap_ratio, 4)
            out["outside_pixels"] = int(outside_pixels)
            out["inside_ratio"] = round(inside_ratio, 4)
            return True, out

    return False, None


def render_debug_humano(img, opening_mask, deteccao):
    dbg = img.copy()

    opening_bin = (opening_mask > 0).astype(np.uint8)
    contours, _ = cv2.findContours(opening_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(dbg, contours, -1, (0, 255, 255), 2)

    red = np.zeros_like(dbg)
    red[:, :] = (0, 0, 255)
    mask_open = opening_bin.astype(bool)
    dbg[mask_open] = cv2.addWeighted(dbg, 0.85, red, 0.15, 0)[mask_open]

    if deteccao is not None:
        x1, y1, x2, y2 = deteccao["bbox"]
        cv2.rectangle(dbg, (x1, y1), (x2, y2), (0, 0, 255), 3)
        txt = f"HUMANO overlap={deteccao['overlap_ratio']:.2f}"
        cv2.putText(
            dbg,
            txt,
            (x1, max(30, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )

    return dbg


def main():
    csv_path = CSV_DIR / "resultado_volumetria.csv"
    resumo_path = CSV_DIR / "dashboard_resumo.csv"
    run_info_path = CSV_DIR / "run_info.json"

    existing_rows = load_existing_rows(csv_path)
    processed_names = {r["arquivo"] for r in existing_rows if r.get("arquivo")}

    segmentador = SegmentadorVolumetria()
    segmentador_contaminantes = SegmentadorContaminantes()
    human_detector = build_human_detector()

    image_files = sorted([p for p in INPUT_DIR.glob("*") if p.suffix.lower() in VALID_EXTS])
    if not image_files:
        print("Nenhuma imagem encontrada em:", INPUT_DIR)
        return

    new_image_files = [p for p in image_files if p.name not in processed_names]

    print(f"TOTAL INPUT = {len(image_files)}")
    print(f"JA PROCESSADAS = {len(processed_names)}")
    print(f"NOVAS = {len(new_image_files)}")

    if not new_image_files:
        write_rows(csv_path, existing_rows)
        write_dashboard(resumo_path, existing_rows)

        run_info = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "mode": "incremental",
            "model_path": str(MODEL_PATH),
            "input_dir": str(INPUT_DIR),
            "total_imagens_input": len(image_files),
            "ja_processadas": len(processed_names),
            "novas_processadas": 0,
            "total_rows_csv": len(existing_rows),
            "csv_resultado": str(csv_path),
            "csv_dashboard": str(resumo_path),
            "debug_dir": str(DEBUG_DIR),
            "masks_opening_dir": str(OPENING_MASK_DIR),
            "masks_floor_dir": str(FLOOR_MASK_DIR),
            "masks_wall_dir": str(WALL_MASK_DIR),
            "contaminantes_modelo_ativo": segmentador_contaminantes.ativo,
            "human_gate_ativo": True,
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

    new_rows = []
    ok_consec_criticos_by_group = build_previous_critical_counters(existing_rows)

    for img_path, img, opening, floor, wall in stage:
        name = img_path.stem
        grupo = detect_group(name)

        # 1) SEMPRE roda contaminantes primeiro
        cont_pred = segmentador_contaminantes.inferir(str(img_path))
        materiais_detectados = cont_pred.get("materiais_detectados", [])
        deteccoes = cont_pred.get("deteccoes", [])
        cont_result = avaliar_contaminacao(grupo, materiais_detectados)

        materiais_detectados_raw = ",".join(materiais_detectados) if materiais_detectados else ""
        deteccoes_contaminantes_json = json.dumps(deteccoes, ensure_ascii=False)

        # 2) Depois roda gate de humano
        human_dets = detectar_humanos(human_detector, img)
        human_hit, human_info = humano_intersecta_abertura(human_dets, opening)

        if human_hit:
            dbg = render_debug_humano(img, opening, human_info)
            cv2.imwrite(str(DEBUG_DIR / f"{name}_debug.jpg"), dbg)

            row = normalize_row({
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
            new_rows.append(row)

            print(
                f"{img_path.name} -> grupo={grupo} | status=suspeito | "
                f"fill= | estado=revisar | ok_consec=0 | alerta=0 | "
                f"motivo=humano_na_abertura | materiais={materiais_detectados_raw if materiais_detectados_raw else 'nenhum'} | "
                f"alerta_contam={cont_result['alerta_contaminacao']} | "
                f"tipo_contam={cont_result['tipo_contaminacao'] if cont_result['tipo_contaminacao'] else 'nenhum'}"
            )
            continue

        feats = extrair_features(opening, floor, wall, None, None)
        if feats is None:
            row = normalize_row({
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
            new_rows.append(row)
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

        row = normalize_row({
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
        new_rows.append(row)

        print(
            f"{img_path.name} -> grupo={grupo} | status={feats['status_frame']} | "
            f"fill={fill:.2f}% | estado={estado_dashboard} | "
            f"ok_consec={ok_consecutivos_criticos} | alerta={alerta_dashboard} | "
            f"materiais={materiais_detectados_raw if materiais_detectados_raw else 'nenhum'}"
        )

    all_rows = merge_rows(existing_rows, new_rows)

    write_rows(csv_path, all_rows)
    write_dashboard(resumo_path, all_rows)

    run_info = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "mode": "incremental",
        "model_path": str(MODEL_PATH),
        "input_dir": str(INPUT_DIR),
        "total_imagens_input": len(image_files),
        "ja_processadas_antes": len(processed_names),
        "novas_processadas": len(new_rows),
        "total_rows_csv": len(all_rows),
        "csv_resultado": str(csv_path),
        "csv_dashboard": str(resumo_path),
        "debug_dir": str(DEBUG_DIR),
        "masks_opening_dir": str(OPENING_MASK_DIR),
        "masks_floor_dir": str(FLOOR_MASK_DIR),
        "masks_wall_dir": str(WALL_MASK_DIR),
        "contaminantes_modelo_ativo": segmentador_contaminantes.ativo,
        "human_gate_ativo": True,
    }

    with open(run_info_path, "w", encoding="utf-8") as f:
        json.dump(run_info, f, ensure_ascii=False, indent=2)

    print()
    print("CONCLUIDO")
    print("MODO: incremental")
    print("CSV:", csv_path)
    print("RESUMO:", resumo_path)
    print("RUN_INFO:", run_info_path)
    print("DEBUG:", DEBUG_DIR)
    print("MASK OPENING:", OPENING_MASK_DIR)
    print("MASK FLOOR:", FLOOR_MASK_DIR)
    print("MASK WALL:", WALL_MASK_DIR)
    print(f"NOVAS PROCESSADAS: {len(new_rows)}")
    print(f"TOTAL NO CSV: {len(all_rows)}")


if __name__ == "__main__":
    main()