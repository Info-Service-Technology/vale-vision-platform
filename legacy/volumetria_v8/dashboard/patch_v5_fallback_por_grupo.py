from pathlib import Path

path = Path(r"E:\PROJETO VALE\PACOTE_PILOTO_VM\PRODUTO_VOLUMETRIA_RELEASE_V8\dashboard\app_dashboard_profissional_v5.py")
text = path.read_text(encoding="utf-8")

old_fill = '''
def fill_operacional(status, fill, motivo):
    status = (status or "").lower()
    motivo = (motivo or "").lower()

    if status == "ok" and not pd.isna(fill):
        return f"{float(fill):.2f}%"

    if motivo == "suspeito_floor_quase_zero":
        return "85–100%"

    if not pd.isna(fill):
        return faixa_fill_text(fill)

    return "indeterminado"
'''

new_fill = '''
def fill_operacional(status, fill, motivo, grupo):
    status = (status or "").lower()
    motivo = (motivo or "").lower()
    grupo = (grupo or "").lower()

    if status == "ok" and not pd.isna(fill):
        return f"{float(fill):.2f}%"

    if motivo == "suspeito_floor_quase_zero":
        if grupo == "madeira":
            return "85–100%"
        if grupo in ("sucata", "plastico"):
            return "0–10%"
        return "indeterminado"

    if not pd.isna(fill):
        return faixa_fill_text(fill)

    return "indeterminado"
'''

old_nivel = '''
def nivel_operacional(status, fill, motivo):
    status = (status or "").lower()
    motivo = (motivo or "").lower()

    if status == "ok" and not pd.isna(fill):
        return nivel_from_fill(fill)

    if motivo == "suspeito_floor_quase_zero":
        return "muito alto"

    if not pd.isna(fill):
        return nivel_from_fill(fill)

    return "indeterminado"
'''

new_nivel = '''
def nivel_operacional(status, fill, motivo, grupo):
    status = (status or "").lower()
    motivo = (motivo or "").lower()
    grupo = (grupo or "").lower()

    if status == "ok" and not pd.isna(fill):
        return nivel_from_fill(fill)

    if motivo == "suspeito_floor_quase_zero":
        if grupo == "madeira":
            return "muito alto"
        if grupo in ("sucata", "plastico"):
            return "muito baixo"
        return "indeterminado"

    if not pd.isna(fill):
        return nivel_from_fill(fill)

    return "indeterminado"
'''

old_acao = '''
def acao_operacional(status, estado, fill, motivo):
    status = (status or "").lower()
    motivo = (motivo or "").lower()

    if motivo == "suspeito_floor_quase_zero":
        return "revisar e programar troca"

    if status != "ok":
        return "revisão visual obrigatória"

    if pd.isna(fill):
        return "revisão visual"

    f = float(fill)
    if f >= 95:
        return "trocar caçamba"
    if f >= 85:
        return "programar troca"
    if f >= 60:
        return "monitorar alto enchimento"
    return "operação normal"
'''

new_acao = '''
def acao_operacional(status, estado, fill, motivo, grupo):
    status = (status or "").lower()
    motivo = (motivo or "").lower()
    grupo = (grupo or "").lower()

    if motivo == "suspeito_floor_quase_zero":
        if grupo == "madeira":
            return "revisar e programar troca"
        if grupo in ("sucata", "plastico"):
            return "revisar, tendência de vazio"
        return "revisão visual obrigatória"

    if status != "ok":
        return "revisão visual obrigatória"

    if pd.isna(fill):
        return "revisão visual"

    f = float(fill)
    if f >= 95:
        return "trocar caçamba"
    if f >= 85:
        return "programar troca"
    if f >= 60:
        return "monitorar alto enchimento"
    return "operação normal"
'''

text = text.replace(old_fill, new_fill, 1)
text = text.replace(old_nivel, new_nivel, 1)
text = text.replace(old_acao, new_acao, 1)

text = text.replace(
    'fill_op = fill_operacional(status, fill, motivo)',
    'fill_op = fill_operacional(status, fill, motivo, grupo)'
)
text = text.replace(
    'nivel = nivel_operacional(status, fill, motivo)',
    'nivel = nivel_operacional(status, fill, motivo, grupo)'
)
text = text.replace(
    'acao = acao_operacional(status, estado, fill, motivo)',
    'acao = acao_operacional(status, estado, fill, motivo, grupo)'
)

text = text.replace(
    'f["fill_operacional_exibicao"] = f.apply(lambda r: fill_operacional(r["status"], r["fill_percent"], r["motivo_falha"]), axis=1)',
    'f["fill_operacional_exibicao"] = f.apply(lambda r: fill_operacional(r["status"], r["fill_percent"], r["motivo_falha"], r["grupo"]), axis=1)'
)
text = text.replace(
    'f["nivel_operacional"] = f.apply(lambda r: nivel_operacional(r["status"], r["fill_percent"], r["motivo_falha"]), axis=1)',
    'f["nivel_operacional"] = f.apply(lambda r: nivel_operacional(r["status"], r["fill_percent"], r["motivo_falha"], r["grupo"]), axis=1)'
)
text = text.replace(
    'f["acao_operacional"] = f.apply(lambda r: acao_operacional(r["status"], r["estado_dashboard"], r["fill_percent"], r["motivo_falha"]), axis=1)',
    'f["acao_operacional"] = f.apply(lambda r: acao_operacional(r["status"], r["estado_dashboard"], r["fill_percent"], r["motivo_falha"], r["grupo"]), axis=1)'
)

path.write_text(text, encoding="utf-8")
print("[OK] Patch V5 fallback por grupo aplicado com sucesso")
