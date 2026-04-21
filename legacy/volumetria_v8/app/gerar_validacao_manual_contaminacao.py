import csv
import shutil
from pathlib import Path

PRODUCT_ROOT = Path(r"E:\PROJETO VALE\PRODUTO_VOLUMETRIA_RELEASE_V8")
AUDIT_ROOT = PRODUCT_ROOT / "auditoria_visual_contaminantes_ineditas_lote_30"
AUDIT_CSV = AUDIT_ROOT / "auditoria_visual_contaminantes.csv"

OUT_ROOT = PRODUCT_ROOT / "validacao_manual_contaminacao"
OUT_CSV = OUT_ROOT / "validacao_manual_contaminacao.csv"

DIR_ORIG = OUT_ROOT / "originais"
DIR_ANN = OUT_ROOT / "anotadas"

VALIDATION_COLUMNS = [
    "arquivo",
    "grupo",
    "materiais_detectados_raw",
    "contaminantes_detectados",
    "alerta_contaminacao",
    "tipo_contaminacao",
    "severidade_contaminacao",
    "n_deteccoes",
    "n_materiais_unicos",
    "max_conf",
    "deteccoes_json",
    # preenchimento manual
    "contaminacao_real",
    "avaliacao_modelo",
    "avaliacao_final",
    "observacao_manual",
]


def limpar_pasta(p: Path):
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True, exist_ok=True)


def copiar_se_existir(src: Path, dst: Path):
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def to_int(v, default=0):
    try:
        if v is None or v == "":
            return default
        return int(float(v))
    except Exception:
        return default


def main():
    if not AUDIT_CSV.exists():
        raise RuntimeError(f"CSV de auditoria não encontrado: {AUDIT_CSV}")

    limpar_pasta(OUT_ROOT)
    DIR_ORIG.mkdir(parents=True, exist_ok=True)
    DIR_ANN.mkdir(parents=True, exist_ok=True)

    with open(AUDIT_CSV, "r", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    selecionados = []

    for row in rows:
        alerta = to_int(row.get("alerta_contaminacao", 0), default=0)
        n_materiais = to_int(row.get("n_materiais_unicos", 0), default=0)
        materiais_raw = row.get("materiais_detectados_raw", "").strip()

        # Casos que valem validação manual agora:
        # 1) contaminação detectada
        # 2) múltiplos materiais
        # 3) caso sem detecção (opcionalmente útil)
        if not (alerta == 1 or n_materiais >= 2 or materiais_raw == ""):
            continue

        arquivo = row.get("arquivo", "").strip()
        if not arquivo:
            continue

        orig_path = PRODUCT_ROOT / "input" / "images_ineditas_lote_30" / arquivo
        ann_path = AUDIT_ROOT / "00_todas_anotadas" / f"{Path(arquivo).stem}_annotated.jpg"

        copiar_se_existir(orig_path, DIR_ORIG / arquivo)
        copiar_se_existir(ann_path, DIR_ANN / f"{Path(arquivo).stem}_annotated.jpg")

        selecionados.append({
            "arquivo": arquivo,
            "grupo": row.get("grupo", ""),
            "materiais_detectados_raw": row.get("materiais_detectados_raw", ""),
            "contaminantes_detectados": row.get("contaminantes_detectados", ""),
            "alerta_contaminacao": row.get("alerta_contaminacao", ""),
            "tipo_contaminacao": row.get("tipo_contaminacao", ""),
            "severidade_contaminacao": row.get("severidade_contaminacao", ""),
            "n_deteccoes": row.get("n_deteccoes", ""),
            "n_materiais_unicos": row.get("n_materiais_unicos", ""),
            "max_conf": row.get("max_conf", ""),
            "deteccoes_json": row.get("deteccoes_json", ""),
            "contaminacao_real": "",
            "avaliacao_modelo": "",
            "avaliacao_final": "",
            "observacao_manual": "",
        })

    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=VALIDATION_COLUMNS)
        writer.writeheader()
        writer.writerows(selecionados)

    print("VALIDACAO MANUAL GERADA")
    print("OUT_ROOT:", OUT_ROOT)
    print("OUT_CSV:", OUT_CSV)
    print(f"TOTAL_CASOS: {len(selecionados)}")
    print("PASTA_ORIG:", DIR_ORIG)
    print("PASTA_ANNOTATED:", DIR_ANN)


if __name__ == "__main__":
    main()