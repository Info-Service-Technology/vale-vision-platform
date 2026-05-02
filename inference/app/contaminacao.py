from typing import Dict, List


REGRAS_CONTAMINACAO = {
    "madeira": ["madeira"],
    "plastico": ["plastico"],
    "sucata": ["sucata"],
}


def avaliar_contaminacao(grupo: str, materiais_detectados: List[str]) -> Dict:
    grupo_normalizado = (grupo or "").strip().lower()
    materiais = [m.strip().lower() for m in materiais_detectados if m]

    materiais_aceitos = REGRAS_CONTAMINACAO.get(grupo_normalizado, [])
    contaminantes = sorted(set([m for m in materiais if m not in materiais_aceitos]))

    alerta = 1 if contaminantes else 0

    if alerta:
        tipo = f"Material incompatível na caçamba de {grupo_normalizado}"
        severidade = "alta" if len(contaminantes) >= 2 else "media"
    else:
        tipo = "sem_contaminacao"
        severidade = "baixa"

    return {
        "cacamba_esperada": grupo_normalizado,
        "material_esperado": ",".join(materiais_aceitos),
        "materiais_detectados_raw": ",".join(materiais),
        "contaminantes_detectados": ",".join(contaminantes),
        "alerta_contaminacao": alerta,
        "tipo_contaminacao": tipo,
        "severidade_contaminacao": severidade,
    }