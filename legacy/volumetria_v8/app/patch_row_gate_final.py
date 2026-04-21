from pathlib import Path

path = Path(r"E:\PROJETO VALE\PACOTE_PILOTO_VM\PRODUTO_VOLUMETRIA_RELEASE_V8\app\main_incremental.py")
text = path.read_text(encoding="utf-8")

helper_anchor = """def build_previous_critical_counters(rows: list[dict]) -> dict[str, int]:
"""
helper_code = """
def sanitize_row_final(row: dict) -> dict:
    if row is None:
        return row

    status = str(row.get("status_frame", "")).strip().lower()
    motivo = str(row.get("motivo_falha", "")).strip().lower()

    def is_true(v):
        return str(v).strip().lower() in {"1", "true", "sim", "yes", "y"}

    def to_float(v, default=0.0):
        try:
            if v in (None, ""):
                return default
            return float(v)
        except Exception:
            return default

    fill_val = to_float(row.get("fill_percent_filtrado", ""), default=-1.0)
    floor_bruto = to_float(row.get("floor_area_bruto", ""), default=0.0)
    floor_filtrado = to_float(row.get("floor_area_filtrado", ""), default=0.0)
    expected_overlap = to_float(row.get("expected_overlap_ratio", ""), default=0.0)
    filtered_ratio = to_float(row.get("filtered_vs_raw_ratio", ""), default=0.0)

    suspeita_floor_quase_zero = is_true(row.get("suspeita_floor_quase_zero", ""))
    suspeita_expected_overlap_baixo = is_true(row.get("suspeita_expected_overlap_baixo", ""))
    suspeita_floor_filtrado_colapsou = is_true(row.get("suspeita_floor_filtrado_colapsou", ""))
    suspeita_divergencia = is_true(row.get("suspeita_divergencia_bruto_filtrado", ""))

    colapsou = (
        status != "ok"
        or motivo in {"suspeito_generico", "suspeito_floor_quase_zero"}
        or suspeita_floor_quase_zero
        or suspeita_expected_overlap_baixo
        or suspeita_floor_filtrado_colapsou
        or suspeita_divergencia
        or floor_bruto <= 0
        or floor_filtrado <= 0
        or expected_overlap < 0.06
        or filtered_ratio < 0.04
        or fill_val < 5.0
    )

    if colapsou:
        row["fill_percent_filtrado"] = ""
        row["fill_temporal"] = ""
        row["alerta_dashboard"] = 0

        if status == "invalido":
            row["estado_dashboard"] = "invalido"
            row["estado_dashboard_temporal"] = "invalido"
        else:
            row["status_frame"] = "suspeito"
            row["estado_dashboard"] = "revisar"
            row["estado_dashboard_temporal"] = "revisar"

            if suspeita_floor_quase_zero:
                row["motivo_falha"] = "suspeito_floor_quase_zero"
            elif not motivo:
                row["motivo_falha"] = "suspeito_generico"

    return row


""" + helper_anchor

if "def sanitize_row_final(row: dict) -> dict:" not in text:
    if helper_anchor not in text:
        raise RuntimeError("Nao achei ancora para inserir sanitize_row_final")
    text = text.replace(helper_anchor, helper_code, 1)

target = "            new_rows.append(row)"
replacement = """            row = sanitize_row_final(row)
            new_rows.append(row)"""

if target not in text:
    raise RuntimeError("Nao achei new_rows.append(row) para aplicar patch")

text = text.replace(target, replacement)

path.write_text(text, encoding="utf-8")
print("[OK] Patch row_gate_final aplicado com sucesso")
