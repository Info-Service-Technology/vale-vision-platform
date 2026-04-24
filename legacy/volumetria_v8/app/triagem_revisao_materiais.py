import csv
import shutil
from pathlib import Path

PRODUCT_ROOT = Path(r"E:\PROJETO VALE\PRODUTO_VOLUMETRIA_RELEASE_V8")

CSV_PATH = PRODUCT_ROOT / "output" / "csv" / "resultado_volumetria.csv"
INPUT_DIR = PRODUCT_ROOT / "input" / "images"
DEBUG_DIR = PRODUCT_ROOT / "output" / "debug"

REVIEW_ROOT = PRODUCT_ROOT / "review_materiais"
DIR_SEM_DETECCAO = REVIEW_ROOT / "01_sem_deteccao"
DIR_CONTAMINACAO = REVIEW_ROOT / "02_contaminacao_detectada"
DIR_SEM_GRUPO_COM_MATERIAL = REVIEW_ROOT / "03_sem_grupo_com_material"

MANIFEST_ALL = REVIEW_ROOT / "manifest_revisao_materiais.csv"
MANIFEST_SEM_DETECCAO = REVIEW_ROOT / "manifest_sem_deteccao.csv"


def limpar_pasta(p: Path):
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True, exist_ok=True)


def copiar_se_existir(src: Path, dst: Path):
    if src.exists():
        shutil.copy2(src, dst)


def to_int(v, default=0):
    try:
        if v is None or v == "":
            return default
        return int(float(v))
    except Exception:
        return default


def main():
    if not CSV_PATH.exists():
        raise RuntimeError(f"CSV não encontrado: {CSV_PATH}")

    limpar_pasta(REVIEW_ROOT)
    DIR_SEM_DETECCAO.mkdir(parents=True, exist_ok=True)
    DIR_CONTAMINACAO.mkdir(parents=True, exist_ok=True)
    DIR_SEM_GRUPO_COM_MATERIAL.mkdir(parents=True, exist_ok=True)

    with open(CSV_PATH, "r", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    review_rows = []
    sem_deteccao_rows = []

    n_sem_deteccao = 0
    n_contaminacao = 0
    n_sem_grupo_material = 0

    for row in rows:
        arquivo = row.get("arquivo", "").strip()
        grupo = row.get("grupo", "").strip()
        materiais_raw = row.get("materiais_detectados_raw", "").strip()
        contaminantes = row.get("contaminantes_detectados", "").strip()
        alerta_cont = to_int(row.get("alerta_contaminacao", 0), default=0)

        if not arquivo:
            continue

        img_src = INPUT_DIR / arquivo
        debug_src = DEBUG_DIR / f"{Path(arquivo).stem}_debug.jpg"

        categoria = None

        if materiais_raw == "":
            categoria = "sem_deteccao"
            n_sem_deteccao += 1
        elif alerta_cont == 1 or contaminantes != "":
            categoria = "contaminacao_detectada"
            n_contaminacao += 1
        elif grupo == "sem_grupo" and materiais_raw != "":
            categoria = "sem_grupo_com_material"
            n_sem_grupo_material += 1

        if categoria is None:
            continue

        if categoria == "sem_deteccao":
            dst_dir = DIR_SEM_DETECCAO
            sem_deteccao_rows.append(row)
        elif categoria == "contaminacao_detectada":
            dst_dir = DIR_CONTAMINACAO
        else:
            dst_dir = DIR_SEM_GRUPO_COM_MATERIAL

        copiar_se_existir(img_src, dst_dir / arquivo)
        copiar_se_existir(debug_src, dst_dir / f"{Path(arquivo).stem}_debug.jpg")

        review_rows.append({
            "categoria": categoria,
            "arquivo": arquivo,
            "grupo": grupo,
            "materiais_detectados_raw": materiais_raw,
            "contaminantes_detectados": contaminantes,
            "alerta_contaminacao": alerta_cont,
            "tipo_contaminacao": row.get("tipo_contaminacao", ""),
            "severidade_contaminacao": row.get("severidade_contaminacao", ""),
            "status_frame": row.get("status_frame", ""),
            "motivo_falha": row.get("motivo_falha", ""),
            "fill_percent_filtrado": row.get("fill_percent_filtrado", ""),
        })

    with open(MANIFEST_ALL, "w", newline="", encoding="utf-8-sig") as f:
        fieldnames = [
            "categoria",
            "arquivo",
            "grupo",
            "materiais_detectados_raw",
            "contaminantes_detectados",
            "alerta_contaminacao",
            "tipo_contaminacao",
            "severidade_contaminacao",
            "status_frame",
            "motivo_falha",
            "fill_percent_filtrado",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(review_rows)

    with open(MANIFEST_SEM_DETECCAO, "w", newline="", encoding="utf-8-sig") as f:
        fieldnames = list(sem_deteccao_rows[0].keys()) if sem_deteccao_rows else ["arquivo"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        if sem_deteccao_rows:
            writer.writerows(sem_deteccao_rows)

    print("TRIAGEM MATERIAIS CONCLUIDA")
    print("REVIEW_ROOT:", REVIEW_ROOT)
    print("MANIFEST_ALL:", MANIFEST_ALL)
    print("MANIFEST_SEM_DETECCAO:", MANIFEST_SEM_DETECCAO)
    print(f"SEM_DETECCAO: {n_sem_deteccao}")
    print(f"CONTAMINACAO_DETECTADA: {n_contaminacao}")
    print(f"SEM_GRUPO_COM_MATERIAL: {n_sem_grupo_material}")


if __name__ == "__main__":
    main()