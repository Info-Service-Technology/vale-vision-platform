from pathlib import Path

path = Path(r"E:\PROJETO VALE\PACOTE_PILOTO_VM\PRODUTO_VOLUMETRIA_RELEASE_V8\app\main_incremental.py")
text = path.read_text(encoding="utf-8")

old = """    colapsou = (
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
"""

new = """    colapsou = (
        status != "ok"
        or motivo == "suspeito_generico"
        or suspeita_floor_quase_zero
        or suspeita_expected_overlap_baixo
        or suspeita_floor_filtrado_colapsou
        or suspeita_divergencia
        or floor_filtrado <= 0
        or floor_bruto <= 0
        or (floor_bruto > 0 and filtered_ratio < 0.04)
        or expected_overlap < 0.06
        or fill_val < 5.0
    )
"""

if old not in text:
    raise RuntimeError("Bloco colapsou nao encontrado para patch")

text = text.replace(old, new, 1)

old2 = """            if status == "ok":
                feats["status_frame"] = "suspeito"
            if not motivo:
                feats["motivo_falha"] = "suspeito_generico"
"""

new2 = """            if status == "ok":
                feats["status_frame"] = "suspeito"
            if suspeita_floor_quase_zero:
                feats["motivo_falha"] = "suspeito_floor_quase_zero"
            elif not motivo:
                feats["motivo_falha"] = "suspeito_generico"
"""

if old2 not in text:
    raise RuntimeError("Bloco motivo_falha nao encontrado para patch")

text = text.replace(old2, new2, 1)

path.write_text(text, encoding="utf-8")
print("[OK] Gate 1.1 aplicado com sucesso")
