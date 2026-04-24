import argparse
import csv
import json
import shutil
from pathlib import Path

import cv2

from config import INPUT_DIR, CONTAMINANTES_CONF_THRES, IMG_SIZE
from segmentador_contaminantes import SegmentadorContaminantes
from motor_contaminacao import avaliar_contaminacao
from motor_volumetria_permissivo import detect_group

VALID_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
LOW_CONF_THRES = 0.45


def copiar_se_existir(src: Path, dst: Path):
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def limpar_pasta(p: Path):
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True, exist_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source_dir",
        default=str(INPUT_DIR),
        help="Pasta com imagens a auditar"
    )
    parser.add_argument(
        "--out_root",
        default=r"E:\PROJETO VALE\PRODUTO_VOLUMETRIA_RELEASE_V8\auditoria_visual_contaminantes_atual",
        help="Pasta de saída da auditoria"
    )
    args = parser.parse_args()

    source_dir = Path(args.source_dir)
    out_root = Path(args.out_root)

    if not source_dir.exists():
        raise RuntimeError(f"Pasta source_dir não encontrada: {source_dir}")

    seg = SegmentadorContaminantes()
    if not seg.ativo or seg.model is None:
        raise RuntimeError("Modelo de contaminantes não está ativo.")

    dir_all = out_root / "00_todas_anotadas"
    dir_sem_det = out_root / "01_sem_deteccao"
    dir_multi_det = out_root / "02_multiplas_deteccoes"
    dir_multi_mat = out_root / "03_multiplos_materiais"
    dir_cont = out_root / "04_possivel_contaminacao"
    dir_low_conf = out_root / "05_baixa_confianca"

    limpar_pasta(out_root)
    for d in [dir_all, dir_sem_det, dir_multi_det, dir_multi_mat, dir_cont, dir_low_conf]:
        d.mkdir(parents=True, exist_ok=True)

    images = sorted([p for p in source_dir.iterdir() if p.suffix.lower() in VALID_EXTS])
    if not images:
        raise RuntimeError(f"Nenhuma imagem encontrada em: {source_dir}")

    rows = []

    n_sem_det = 0
    n_multi_det = 0
    n_multi_mat = 0
    n_cont = 0
    n_low_conf = 0

    for img_path in images:
        result = seg.model.predict(
            source=str(img_path),
            conf=CONTAMINANTES_CONF_THRES,
            imgsz=IMG_SIZE,
            retina_masks=True,
            verbose=False
        )[0]

        deteccoes = []
        materiais = []

        if result.boxes is not None and len(result.boxes) > 0:
            classes = result.boxes.cls.cpu().numpy().astype(int)
            confs = result.boxes.conf.cpu().numpy()

            for cls_id, conf in zip(classes, confs):
                nome = seg.class_names.get(int(cls_id), str(cls_id))
                nome = seg._normalizar_nome_classe(nome)

                deteccoes.append({
                    "classe": nome,
                    "confianca": round(float(conf), 4),
                })
                materiais.append(nome)

        # remove repetidos preservando ordem
        vistos = set()
        materiais_unicos = []
        for m in materiais:
            if m not in vistos:
                vistos.add(m)
                materiais_unicos.append(m)

        grupo = detect_group(img_path.stem)
        cont = avaliar_contaminacao(grupo, materiais_unicos)

        annotated = result.plot()
        annotated_path = dir_all / f"{img_path.stem}_annotated.jpg"
        cv2.imwrite(str(annotated_path), annotated)

        materiais_raw = ",".join(materiais_unicos) if materiais_unicos else ""
        max_conf = max([d["confianca"] for d in deteccoes], default=0.0)
        min_conf = min([d["confianca"] for d in deteccoes], default=0.0)

        row = {
            "arquivo": img_path.name,
            "grupo": grupo,
            "materiais_detectados_raw": materiais_raw,
            "n_deteccoes": len(deteccoes),
            "n_materiais_unicos": len(materiais_unicos),
            "max_conf": round(float(max_conf), 4),
            "min_conf": round(float(min_conf), 4),
            "contaminantes_detectados": cont["contaminantes_detectados"],
            "alerta_contaminacao": cont["alerta_contaminacao"],
            "tipo_contaminacao": cont["tipo_contaminacao"],
            "severidade_contaminacao": cont["severidade_contaminacao"],
            "cacamba_esperada": cont["cacamba_esperada"],
            "material_esperado": cont["material_esperado"],
            "deteccoes_json": json.dumps(deteccoes, ensure_ascii=False),
        }
        rows.append(row)

        # categorias de revisão
        if len(deteccoes) == 0:
            n_sem_det += 1
            copiar_se_existir(img_path, dir_sem_det / img_path.name)
            copiar_se_existir(annotated_path, dir_sem_det / f"{img_path.stem}_annotated.jpg")

        if len(deteccoes) >= 2:
            n_multi_det += 1
            copiar_se_existir(img_path, dir_multi_det / img_path.name)
            copiar_se_existir(annotated_path, dir_multi_det / f"{img_path.stem}_annotated.jpg")

        if len(materiais_unicos) >= 2:
            n_multi_mat += 1
            copiar_se_existir(img_path, dir_multi_mat / img_path.name)
            copiar_se_existir(annotated_path, dir_multi_mat / f"{img_path.stem}_annotated.jpg")

        if cont["alerta_contaminacao"] == 1:
            n_cont += 1
            copiar_se_existir(img_path, dir_cont / img_path.name)
            copiar_se_existir(annotated_path, dir_cont / f"{img_path.stem}_annotated.jpg")

        if len(deteccoes) > 0 and max_conf < LOW_CONF_THRES:
            n_low_conf += 1
            copiar_se_existir(img_path, dir_low_conf / img_path.name)
            copiar_se_existir(annotated_path, dir_low_conf / f"{img_path.stem}_annotated.jpg")

        print(
            f"{img_path.name} | grupo={grupo} | materiais={materiais_raw if materiais_raw else 'nenhum'} "
            f"| det={len(deteccoes)} | cont={cont['contaminantes_detectados'] if cont['contaminantes_detectados'] else '-'}"
        )

    csv_path = out_root / "auditoria_visual_contaminantes.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        fieldnames = [
            "arquivo",
            "grupo",
            "materiais_detectados_raw",
            "n_deteccoes",
            "n_materiais_unicos",
            "max_conf",
            "min_conf",
            "contaminantes_detectados",
            "alerta_contaminacao",
            "tipo_contaminacao",
            "severidade_contaminacao",
            "cacamba_esperada",
            "material_esperado",
            "deteccoes_json",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print()
    print("AUDITORIA VISUAL CONTAMINANTES CONCLUIDA")
    print("SOURCE_DIR:", source_dir)
    print("OUT_ROOT:", out_root)
    print("CSV:", csv_path)
    print(f"TOTAL_IMAGENS: {len(images)}")
    print(f"SEM_DETECCAO: {n_sem_det}")
    print(f"MULTIPLAS_DETECCOES: {n_multi_det}")
    print(f"MULTIPLOS_MATERIAIS: {n_multi_mat}")
    print(f"CONTAMINACAO_DETECTADA: {n_cont}")
    print(f"BAIXA_CONFIANCA: {n_low_conf}")


if __name__ == "__main__":
    main()