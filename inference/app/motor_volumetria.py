"""
motor_volumetria.py — Cálculo de volumetria (fill percent) da caçamba.

Portado do PACOTE_PILOTO_VM (motor_volumetria.py) para o pipeline novo.
Calcula a lotação pela razão entre a área de material dentro do ROI (boca)
e a área total da boca. Gera alerta quando o fill ultrapassa o limiar.
"""

import os
from typing import Any

import numpy as np

# Limiar de alerta de lotação (configurável por env)
ALERTA_LOTACAO_PERCENT = float(os.environ.get("ALERTA_LOTACAO_PERCENT", "75.0"))
# Limiares do legado (referência)
ALERTA_AMARELO = float(os.environ.get("ALERTA_AMARELO", "90.0"))
ALERTA_VERMELHO = float(os.environ.get("ALERTA_VERMELHO", "95.0"))

def calcular_fill_percent(resultado_contaminantes: dict[str, Any], roi_mask) -> float:
    """Calcula o percentual de lotação da caçamba.

    Fórmula: pixels de material dentro do ROI / área total do ROI * 100.
    As áreas em resultado['areas_px'] já vêm interseccionadas com o ROI
    (ver segmentador_contaminantes.inferir).

    Args:
        resultado_contaminantes: saída do segmentador (contém 'areas_px').
        roi_mask: máscara binária da boca da caçamba (ROI).

    Returns:
        float entre 0.0 e 100.0. Retorna 0.0 se não houver ROI.
    """
    if roi_mask is None:
        return 0.0

    roi_area = float(np.count_nonzero(roi_mask > 0))
    if roi_area <= 0:
        return 0.0

    material_px = float(sum(resultado_contaminantes.get("areas_px", {}).values()))
    fill = (material_px / roi_area) * 100.0
    return round(min(100.0, fill), 1)

def classificar_fill(fill_percent: float) -> str:
    """Classifica o estado de lotação (referência do legado)."""
    if fill_percent < 10:
        return "vazio"
    if fill_percent < 40:
        return "baixo"
    if fill_percent < 70:
        return "medio"
    if fill_percent < ALERTA_LOTACAO_PERCENT:
        return "alto"
    return "critico"

def decidir_alerta_lotacao(fill_percent: float) -> dict[str, Any]:
    """Decide o alerta de lotação com base no fill calculado.

    Returns:
        dict com: alerta_lotacao (0/1), fill_percent, estado, limiar.
    """
    alerta = 1 if fill_percent > ALERTA_LOTACAO_PERCENT else 0
    return {
        "alerta_lotacao": alerta,
        "fill_percent": fill_percent,
        "estado_lotacao": classificar_fill(fill_percent),
        "limiar_lotacao": ALERTA_LOTACAO_PERCENT,
    }