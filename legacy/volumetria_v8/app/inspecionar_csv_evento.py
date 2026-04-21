import csv
from pathlib import Path

CSV_PATH = Path(r"E:\PROJETO VALE\PACOTE_PILOTO_VM\PRODUTO_VOLUMETRIA_RELEASE_V8\output\csv\resultado_volumetria.csv")

PADRAO = "madeira_20260329102921559793_"

if not CSV_PATH.exists():
    print("CSV_NAO_ENCONTRADO")
    raise SystemExit(1)

with open(CSV_PATH, "r", newline="", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

achou = False
for row in reversed(rows):
    arq = row.get("arquivo", "")
    if PADRAO in arq:
        achou = True
        for k, v in row.items():
            print(f"{k}: {v}")
        break

if not achou:
    print("EVENTO_NAO_ENCONTRADO")
