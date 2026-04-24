from pathlib import Path

path = Path(r"E:\PROJETO VALE\PACOTE_PILOTO_VM\PRODUTO_VOLUMETRIA_RELEASE_V8\app\main_incremental.py")
lines = path.read_text(encoding="utf-8").splitlines()

out = []
inserted = 0

for line in lines:
    stripped = line.strip()

    if stripped == "new_rows.append(row)":
        prev = out[-1].strip() if out else ""
        if prev != "row = sanitize_row_final(row)":
            indent = line[:len(line) - len(line.lstrip())]
            out.append(f"{indent}row = sanitize_row_final(row)")
            inserted += 1

    out.append(line)

path.write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"[OK] Patch branch principal aplicado | insercoes={inserted}")
