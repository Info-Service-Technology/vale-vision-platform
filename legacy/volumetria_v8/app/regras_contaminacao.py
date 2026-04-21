import json
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = PRODUCT_ROOT / "config" / "regras_contaminacao.json"


def load_regras_contaminacao():
    if not RULES_PATH.exists():
        raise RuntimeError(f"Arquivo de regras não encontrado: {RULES_PATH}")

    with open(RULES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "grupos" not in data or not isinstance(data["grupos"], dict):
        raise RuntimeError("regras_contaminacao.json inválido: chave 'grupos' ausente ou inválida")

    if "saida_padrao" not in data or not isinstance(data["saida_padrao"], dict):
        raise RuntimeError("regras_contaminacao.json inválido: chave 'saida_padrao' ausente ou inválida")

    return data


def get_regras_grupo(regras: dict, grupo: str) -> dict:
    grupos = regras.get("grupos", {})
    return grupos.get(grupo, grupos.get("sem_grupo", {}))


def get_saida_padrao_contaminacao(regras: dict) -> dict:
    saida = regras.get("saida_padrao", {})
    return {
        "contaminantes_detectados": saida.get("contaminantes_detectados", []),
        "alerta_contaminacao": saida.get("alerta_contaminacao", 0),
        "tipo_contaminacao": saida.get("tipo_contaminacao", ""),
        "severidade_contaminacao": saida.get("severidade_contaminacao", 0),
    }


def build_contaminacao_placeholder(regras: dict, grupo: str) -> dict:
    regras_grupo = get_regras_grupo(regras, grupo)
    saida_padrao = get_saida_padrao_contaminacao(regras)

    material_esperado = regras_grupo.get("material_esperado", "desconhecido")

    return {
        "contaminantes_detectados": ",".join(saida_padrao["contaminantes_detectados"]) if saida_padrao["contaminantes_detectados"] else "",
        "alerta_contaminacao": int(saida_padrao["alerta_contaminacao"]),
        "tipo_contaminacao": saida_padrao["tipo_contaminacao"],
        "severidade_contaminacao": int(saida_padrao["severidade_contaminacao"]),
        "cacamba_esperada": grupo,
        "material_esperado": material_esperado,
    }