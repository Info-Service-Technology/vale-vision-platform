from pathlib import Path

path = Path(r"E:\PROJETO VALE\PACOTE_PILOTO_VM\PRODUTO_VOLUMETRIA_RELEASE_V8\dashboard\app_dashboard_profissional_v5.py")
text = path.read_text(encoding="utf-8")

old1 = '''
def faixa_fill_text(f):
    if pd.isna(f):
        return "—"
    f = float(f)
    if f >= 95: return "95–100%"
    if f >= 85: return "85–95%"
    if f >= 60: return "60–85%"
    if f >= 30: return "30–60%"
    if f >= 5: return "5–30%"
    return "0–5%"
'''

new1 = '''
def faixa_fill_text(f):
    if pd.isna(f):
        return "—"
    f = float(f)
    if f >= 95: return "95–100%"
    if f >= 80: return "80–95%"
    if f >= 60: return "60–80%"
    if f >= 35: return "35–60%"
    if f >= 20: return "20–35%"
    if f >= 10: return "10–20%"
    return "0–10%"
'''

old2 = '''
def nivel_from_fill(f):
    if pd.isna(f):
        return "indeterminado"
    f = float(f)
    if f >= 95: return "crítico"
    if f >= 85: return "muito alto"
    if f >= 60: return "alto"
    if f >= 30: return "médio"
    if f >= 5: return "baixo"
    return "muito baixo"
'''

new2 = '''
def nivel_from_fill(f):
    if pd.isna(f):
        return "indeterminado"
    f = float(f)
    if f >= 95: return "crítico"
    if f >= 80: return "muito alto"
    if f >= 60: return "alto"
    if f >= 35: return "médio"
    if f >= 20: return "médio-baixo"
    if f >= 10: return "baixo"
    return "muito baixo"
'''

if old1 not in text:
    raise RuntimeError("Nao achei faixa_fill_text antiga")
if old2 not in text:
    raise RuntimeError("Nao achei nivel_from_fill antigo")

text = text.replace(old1, new1, 1)
text = text.replace(old2, new2, 1)

path.write_text(text, encoding="utf-8")
print("[OK] Patch das faixas operacionais da V5 aplicado com sucesso")
