import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
RULES_FILE = BASE_DIR / "config" / "regras_contaminacao.json"


with open(RULES_FILE, "r", encoding="utf-8") as f:
    REGRAS = json.load(f)


def normalizar_material(material: str) -> str:
    if not material:
        return ""

    return (
        material.strip()
        .lower()
        .replace("ã", "a")
        .replace("á", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )


def avaliar_contaminacao(grupo: str, materiais_detectados: list):
    grupo = normalizar_material(grupo)

    materiais_detectados = [
        normalizar_material(m)
        for m in materiais_detectados
        if m
    ]

    regra = REGRAS.get(grupo)

    if not regra:
        contaminantes = materiais_detectados[1:] if len(materiais_detectados) > 1 else []
        alerta = 1 if contaminantes else 0
        if alerta:
            tipo_contaminacao = f"{'_'.join(contaminantes)}_em_{grupo or 'desconhecido'}"
            severidade = "media" if len(contaminantes) == 1 else "alta"
        else:
            tipo_contaminacao = "grupo_desconhecido"
            severidade = "baixa"

        return {
            "cacamba_esperada": grupo,
            "material_esperado": "",
            "contaminantes_detectados": ", ".join(contaminantes),
            "alerta_contaminacao": alerta,
            "tipo_contaminacao": tipo_contaminacao,
            "severidade_contaminacao": severidade
        }

    materiais_aceitos = [
        normalizar_material(m)
        for m in regra.get("aceita", [])
    ]

    contaminantes = []

    for material in materiais_detectados:
        if material not in materiais_aceitos:
            contaminantes.append(material)

    alerta = 1 if contaminantes else 0

    if alerta:
        tipo_contaminacao = (
            f"{'_'.join(contaminantes)}_em_{grupo}"
        )
    else:
        tipo_contaminacao = "sem_contaminacao"

    severidade = "baixa"

    if len(contaminantes) >= 2:
        severidade = "alta"
    elif len(contaminantes) == 1:
        severidade = "media"

    return {
        "cacamba_esperada": grupo,
        "material_esperado": ", ".join(materiais_aceitos),
        "contaminantes_detectados": ", ".join(contaminantes),
        "alerta_contaminacao": alerta,
        "tipo_contaminacao": tipo_contaminacao,
        "severidade_contaminacao": severidade
    }