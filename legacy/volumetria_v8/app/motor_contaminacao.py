from regras_contaminacao import load_regras_contaminacao, get_regras_grupo


def normalizar_materiais_detectados(materiais):
    if materiais is None:
        return []

    if isinstance(materiais, str):
        materiais = [materiais]

    out = []
    for m in materiais:
        if m is None:
            continue
        s = str(m).strip().lower()
        if s:
            out.append(s)

    # remove repetidos preservando ordem
    vistos = set()
    final = []
    for m in out:
        if m not in vistos:
            vistos.add(m)
            final.append(m)

    return final


def avaliar_contaminacao(grupo: str, materiais_detectados):
    regras = load_regras_contaminacao()
    regras_grupo = get_regras_grupo(regras, grupo)

    materiais = normalizar_materiais_detectados(materiais_detectados)

    material_esperado = regras_grupo.get("material_esperado", "desconhecido")
    aceitos = set([str(x).strip().lower() for x in regras_grupo.get("aceita", [])])
    contaminantes_config = set([str(x).strip().lower() for x in regras_grupo.get("contaminantes", [])])

    contaminantes_encontrados = []
    for mat in materiais:
        if mat in contaminantes_config:
            contaminantes_encontrados.append(mat)
        elif aceitos and mat not in aceitos:
            contaminantes_encontrados.append(mat)

    # remove repetidos preservando ordem
    vistos = set()
    contaminantes_unicos = []
    for c in contaminantes_encontrados:
        if c not in vistos:
            vistos.add(c)
            contaminantes_unicos.append(c)

    alerta = 1 if contaminantes_unicos else 0

    if not contaminantes_unicos:
        tipo = ""
        severidade = 0
    elif len(contaminantes_unicos) == 1:
        tipo = contaminantes_unicos[0]
        severidade = 1
    else:
        tipo = ",".join(contaminantes_unicos)
        severidade = 2

    return {
        "contaminantes_detectados": ",".join(contaminantes_unicos),
        "alerta_contaminacao": alerta,
        "tipo_contaminacao": tipo,
        "severidade_contaminacao": severidade,
        "cacamba_esperada": grupo,
        "material_esperado": material_esperado,
    }


if __name__ == "__main__":
    exemplos = [
        ("madeira", ["madeira"]),
        ("madeira", ["sucata"]),
        ("sucata", ["madeira", "sucata"]),
        ("plastico", ["plastico", "madeira"]),
        ("sem_grupo", []),
    ]

    for grupo, mats in exemplos:
        print(grupo, mats, "->", avaliar_contaminacao(grupo, mats))