import os
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parents[1]

# Modelos ficam dentro do prÃ³prio pacote piloto
MODEL_PATH = PRODUCT_ROOT / "models" / "best_v2_yolov8s_seg_1024_20260403.pt"
CONTAMINANTES_MODEL_PATH = PRODUCT_ROOT / "models" / "contaminantes_rf_v1.pt"

# MÃ¡scaras estruturais esperadas
EXPECTED_FLOOR_MASK_PATH = PRODUCT_ROOT / "config" / "expected_floor_mask.png"
EXPECTED_OPENING_MASK_PATH = PRODUCT_ROOT / "config" / "expected_opening_mask.png"

# Entrada configurÃ¡vel por variÃ¡vel de ambiente
INPUT_DIR = Path(os.getenv("VALE_INPUT_DIR", str(PRODUCT_ROOT / "input" / "images")))

OUTPUT_DIR = PRODUCT_ROOT / "output"
CSV_DIR = OUTPUT_DIR / "csv"
DEBUG_DIR = OUTPUT_DIR / "debug"
OPENING_MASK_DIR = OUTPUT_DIR / "masks_opening"
FLOOR_MASK_DIR = OUTPUT_DIR / "masks_floor"
WALL_MASK_DIR = OUTPUT_DIR / "masks_wall"

CSV_DIR.mkdir(parents=True, exist_ok=True)
DEBUG_DIR.mkdir(parents=True, exist_ok=True)
OPENING_MASK_DIR.mkdir(parents=True, exist_ok=True)
FLOOR_MASK_DIR.mkdir(parents=True, exist_ok=True)
WALL_MASK_DIR.mkdir(parents=True, exist_ok=True)

# Classes do modelo V8 promovido
CLS_FLOOR = 0
CLS_WALL = 1

# Thresholds
CONF_THRES = 0.10
CONTAMINANTES_CONF_THRES = 0.25
IMG_SIZE = 1024

ERODE_KERNEL = 41
MIN_COMPONENT_AREA = 400
MIN_OPENING_AREA = 1500

SUSPECT_FLOOR_RATIO = 0.85
SUSPECT_FLOOR_ZERO_MAX = 0.05
SUSPECT_DIVERGENCE_PP = 35.0

OPENING_AREA_TOLERANCE = 0.75
MIN_EXPECTED_OVERLAP_RATIO = 0.06
MIN_FILTERED_VS_RAW_RATIO = 0.04

BORDER_TOUCH_MIN_PIXELS = 120
BORDER_TOUCH_MIN_RATIO = 0.01

ALERTA_AMARELO = 90.0
ALERTA_VERMELHO = 95.0
CONSEC_OK_PARA_TROCA = 2
