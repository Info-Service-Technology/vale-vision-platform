from pathlib import Path

import numpy as np
from ultralytics import YOLO

from config import CONTAMINANTES_MODEL_PATH, IMG_SIZE


# Estratégia:
# 1) rodar a predição com conf baixo para não matar classes fracas
# 2) filtrar por confiança por classe
# 3) usar área de máscara por classe como critério principal de saída
# 4) NÃO deixar classe minúscula virar contaminante só porque passou em confiança
# 5) manter detecções brutas para auditoria/debug
PREDICT_CONF_THRES = 0.05

CLASS_MIN_CONF = {
    "madeira": 0.22,
    "plastico": 0.22,
    "sucata": 0.08,
    "papelao": 0.08,
}

# razão mínima da área total segmentada para considerar a classe como relevante
# ajuste principal: sucata ficou mais rígida para matar falsos positivos pequenos
CLASS_MIN_AREA_RATIO = {
    "madeira": 0.03,
    "plastico": 0.03,
    "sucata": 0.02,
    "papelao": 0.01,
}


class SegmentadorContaminantes:
    """
    Segmentador de contaminantes/materiais.

    Saída padronizada:
    {
        "materiais_detectados": ["madeira", "sucata"],
        "materiais_relevantes": ["madeira", "sucata"],
        "materiais_detectados_brutos": ["madeira", "sucata", "papelao"],
        "deteccoes": [
            {
                "classe": "madeira",
                "confianca": 0.91,
                "area_px": 12345.0,
                "area_ratio": 0.42,
                "fraca": False
            }
        ],
        "areas_px": {
            "madeira": 12345.0,
            "sucata": 17000.0
        },
        "areas_ratio": {
            "madeira": 0.42,
            "sucata": 0.58
        },
        "observacao": "ok"
    }
    """

    def __init__(self, model_path=None):
        self.model_path = Path(model_path) if model_path else Path(CONTAMINANTES_MODEL_PATH)
        self.model = None
        self.ativo = False
        self.class_names = {}

        if self.model_path.exists():
            self.model = YOLO(str(self.model_path))
            self.class_names = self.model.names
            self.ativo = True

    @staticmethod
    def _normalizar_nome_classe(nome: str) -> str:
        s = str(nome).strip().lower()

        mapa = {
            # madeira
            "madeira": "madeira",
            "wood": "madeira",
            "timber": "madeira",
            "mdf": "madeira",

            # sucata
            "sucata": "sucata",
            "metal": "sucata",
            "metais": "sucata",
            "ferro": "sucata",
            "steel": "sucata",
            "iron": "sucata",
            "scrap": "sucata",
            "scrap_metal": "sucata",
            "filtro_oleo": "sucata",
            "filtro de oleo": "sucata",
            "filtro de óleo": "sucata",
            "oil_filter": "sucata",

            # plástico
            "plastico": "plastico",
            "plástico": "plastico",
            "plastic": "plastico",

            # papelão
            "papelao": "papelao",
            "papelão": "papelao",
            "cardboard": "papelao",
            "paperboard": "papelao",
            "boxboard": "papelao",
            "carton": "papelao",
            "papelao_molhado": "papelao",
        }

        return mapa.get(s, s)

    @staticmethod
    def _classe_passa_limiar(nome: str, conf: float) -> bool:
        limiar = CLASS_MIN_CONF.get(nome, 0.20)
        return conf >= limiar

    @staticmethod
    def _area_ratio_minimo(nome: str) -> float:
        return CLASS_MIN_AREA_RATIO.get(nome, 0.03)

    @staticmethod
    def _ordenar_por_valor_desc(d: dict) -> list:
        return sorted(d.items(), key=lambda x: x[1], reverse=True)

    @staticmethod
    def _classe_principal(areas_ratio: dict, materiais_unicos: list) -> str | None:
        if areas_ratio:
            return max(areas_ratio.items(), key=lambda x: x[1])[0]
        if materiais_unicos:
            return materiais_unicos[0]
        return None

    def inferir(self, img_path):
        if not self.ativo or self.model is None:
            return {
                "materiais_detectados": [],
                "materiais_relevantes": [],
                "materiais_detectados_brutos": [],
                "deteccoes": [],
                "areas_px": {},
                "areas_ratio": {},
                "observacao": "modelo_contaminantes_ainda_nao_integrado",
            }

        result = self.model.predict(
            source=str(img_path),
            conf=PREDICT_CONF_THRES,
            imgsz=IMG_SIZE,
            retina_masks=True,
            verbose=False
        )[0]

        deteccoes = []
        areas_px = {}

        boxes_ok = result.boxes is not None and len(result.boxes) > 0
        masks_ok = result.masks is not None and result.masks.data is not None and len(result.masks.data) > 0

        classes = []
        confs = []

        if boxes_ok:
            classes = result.boxes.cls.cpu().numpy().astype(int)
            confs = result.boxes.conf.cpu().numpy()

        masks_np = None
        if masks_ok:
            masks_np = result.masks.data.cpu().numpy()

        # Se houver boxes, usa as confidências por instância.
        # Se também houver masks, agrega área por classe.
        if boxes_ok:
            for i, (cls_id, conf) in enumerate(zip(classes, confs)):
                nome = self.class_names.get(int(cls_id), str(cls_id))
                nome = self._normalizar_nome_classe(nome)
                conf = round(float(conf), 4)

                if not self._classe_passa_limiar(nome, conf):
                    continue

                area_px = 0.0
                if masks_np is not None and i < len(masks_np):
                    mask_bin = masks_np[i] > 0.5
                    area_px = float(np.count_nonzero(mask_bin))
                    areas_px[nome] = areas_px.get(nome, 0.0) + area_px

                deteccoes.append({
                    "classe": nome,
                    "confianca": conf,
                    "area_px": round(float(area_px), 2),
                })

        # fallback: se por algum motivo houver máscara sem box aproveitável
        elif masks_ok:
            return {
                "materiais_detectados": [],
                "materiais_relevantes": [],
                "materiais_detectados_brutos": [],
                "deteccoes": [],
                "areas_px": {},
                "areas_ratio": {},
                "observacao": "masks_sem_boxes_validos",
            }

        # Ordena por confiança desc
        deteccoes.sort(key=lambda x: x["confianca"], reverse=True)

        # Classes únicas por confiança (brutas, sem filtro de área)
        vistos = set()
        materiais_unicos = []
        for d in deteccoes:
            nome = d["classe"]
            if nome not in vistos:
                vistos.add(nome)
                materiais_unicos.append(nome)

        total_area = float(sum(areas_px.values()))
        if total_area > 0:
            areas_ratio = {k: float(v) / total_area for k, v in areas_px.items()}
        else:
            areas_ratio = {}

        # principal = maior área
        classe_principal = self._classe_principal(areas_ratio, materiais_unicos)

        # relevantes = principal + secundários que passam área mínima
        materiais_relevantes = []
        if classe_principal:
            materiais_relevantes.append(classe_principal)

        for nome, ratio in self._ordenar_por_valor_desc(areas_ratio):
            if nome == classe_principal:
                continue
            if ratio >= self._area_ratio_minimo(nome):
                materiais_relevantes.append(nome)

        # remove duplicidade mantendo ordem
        materiais_detectados_saida = []
        for nome in materiais_relevantes:
            if nome not in materiais_detectados_saida:
                materiais_detectados_saida.append(nome)

        # fallback seguro: se por algum motivo não entrou nada, mantém a melhor classe bruta
        if not materiais_detectados_saida and materiais_unicos:
            materiais_detectados_saida = [materiais_unicos[0]]

        # enriquece detecções com area_ratio
        deteccoes_enriquecidas = []
        for d in deteccoes:
            nome = d["classe"]
            area_ratio = round(float(areas_ratio.get(nome, 0.0)), 4)

            deteccoes_enriquecidas.append({
                "classe": nome,
                "confianca": d["confianca"],
                "area_px": d["area_px"],
                "area_ratio": area_ratio,
                "fraca": bool(d["confianca"] < 0.15 and area_ratio < self._area_ratio_minimo(nome)),
            })

        return {
            "materiais_detectados": materiais_detectados_saida,
            "materiais_relevantes": materiais_detectados_saida,
            "materiais_detectados_brutos": materiais_unicos,
            "deteccoes": deteccoes_enriquecidas,
            "areas_px": {k: round(float(v), 2) for k, v in areas_px.items()},
            "areas_ratio": {k: round(float(v), 4) for k, v in areas_ratio.items()},
            "observacao": "ok",
        }


if __name__ == "__main__":
    s = SegmentadorContaminantes()
    print("ativo =", s.ativo)
    print("model_path =", s.model_path)