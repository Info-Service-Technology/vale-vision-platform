from pathlib import Path

path = Path(r"E:\PROJETO VALE\PACOTE_PILOTO_VM\PRODUTO_VOLUMETRIA_RELEASE_V8\app\main_incremental.py")
text = path.read_text(encoding="utf-8")

helper_anchor = """def build_previous_critical_counters(rows: list[dict]) -> dict[str, int]:
"""
helper_code = """
def is_truthy_flag(v) -> bool:
    s = str(v).strip().lower()
    return s in {"1", "true", "sim", "yes", "y"}


def sanitize_feats_for_dashboard(feats: dict) -> dict:
    if feats is None:
        return feats

    status = str(feats.get("status_frame", "")).strip().lower()
    motivo = str(feats.get("motivo_falha", "")).strip().lower()

    floor_bruto = parse_float_safe(feats.get("floor_area_bruto", ""), default=0.0)
    floor_filtrado = parse_float_safe(feats.get("floor_area_filtrado", ""), default=0.0)
    expected_overlap = parse_float_safe(feats.get("expected_overlap_ratio", ""), default=0.0)
    filtered_ratio = parse_float_safe(feats.get("filtered_vs_raw_ratio", ""), default=0.0)
    fill_val = parse_float_safe(feats.get("fill_percent_filtrado", ""), default=-1.0)

    suspeita_floor_quase_zero = is_truthy_flag(feats.get("suspeita_floor_quase_zero", ""))
    suspeita_expected_overlap_baixo = is_truthy_flag(feats.get("suspeita_expected_overlap_baixo", ""))
    suspeita_floor_filtrado_colapsou = is_truthy_flag(feats.get("suspeita_floor_filtrado_colapsou", ""))
    suspeita_divergencia = is_truthy_flag(feats.get("suspeita_divergencia_bruto_filtrado", ""))

    colapsou = (
        status != "ok"
        or motivo == "suspeito_generico"
        or suspeita_floor_quase_zero
        or suspeita_expected_overlap_baixo
        or suspeita_floor_filtrado_colapsou
        or suspeita_divergencia
        or floor_filtrado <= 0
        or (floor_bruto > 0 and filtered_ratio < 0.04)
        or expected_overlap < 0.06
        or fill_val < 1.0
    )

    if colapsou:
        feats["fill_percent_filtrado"] = ""
        feats["fill_temporal"] = ""
        feats["alerta_dashboard"] = 0

        if status == "invalido":
            feats["estado_dashboard"] = "invalido"
            feats["estado_dashboard_temporal"] = "invalido"
        else:
            feats["estado_dashboard"] = "revisar"
            feats["estado_dashboard_temporal"] = "revisar"
            if status == "ok":
                feats["status_frame"] = "suspeito"
            if not motivo:
                feats["motivo_falha"] = "suspeito_generico"

    return feats


""" + helper_anchor

if "def sanitize_feats_for_dashboard(feats: dict) -> dict:" not in text:
    if helper_anchor not in text:
        raise RuntimeError("Nao achei ancora para inserir helper")
    text = text.replace(helper_anchor, helper_code, 1)

target = '        feats["grupo"] = grupo'
replacement = '''        feats["grupo"] = grupo
        feats = sanitize_feats_for_dashboard(feats)'''

if replacement not in text:
    if target not in text:
        raise RuntimeError('Nao achei ponto para aplicar sanitize_feats_for_dashboard')
    text = text.replace(target, replacement, 1)

path.write_text(text, encoding="utf-8")
print("[OK] Gate 1 aplicado com sucesso")
