import re
import shutil
from datetime import datetime
from pathlib import Path

from db_eventos import registrar_arquivo_ignorado

BASE_DIR = Path(r"E:\PROJETO VALE\PACOTE_PILOTO_VM\PRODUTO_VOLUMETRIA_RELEASE_V8")
FTP_DIR = BASE_DIR / "input_ftp"
STAGING_DIR = BASE_DIR / "input" / "images"
ERRO_DIR = BASE_DIR / "output_erro"
VALID_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

GRUPOS = ["madeira", "plastico", "sucata"]


def limpar_nome(s: str) -> str:
    s = s.strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^A-Za-z0-9_\-\.]", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_") or "sem_nome"


def mover_para_erro(src: Path, grupo: str, motivo: str):
    dest_dir = ERRO_DIR / grupo
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name

    if dest.exists():
        ts = datetime.now().strftime("%Y%m%d%H%M%S%f")
        dest = dest_dir / f"{src.stem}_{ts}{src.suffix.lower()}"

    shutil.move(str(src), str(dest))
    registrar_arquivo_ignorado(
        arquivo_nome=src.name,
        arquivo_path=str(src),
        grupo=grupo,
        motivo=motivo,
    )
    print(f"[IGNORADO] {src.name} | grupo={grupo} | motivo={motivo}")


def main():
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    total_movidos = 0
    total_ignorados = 0

    for grupo in GRUPOS:
        origem = FTP_DIR / grupo
        origem.mkdir(parents=True, exist_ok=True)

        arquivos = sorted([p for p in origem.iterdir() if p.is_file()])
        for src in arquivos:
            ext = src.suffix.lower()

            if ext not in VALID_EXTS:
                mover_para_erro(src, grupo, "extensao_invalida")
                total_ignorados += 1
                continue

            try:
                size = src.stat().st_size
            except Exception:
                mover_para_erro(src, grupo, "erro_stat_arquivo")
                total_ignorados += 1
                continue

            if size <= 0:
                mover_para_erro(src, grupo, "arquivo_zerokb")
                total_ignorados += 1
                continue

            stem = limpar_nome(src.stem)

            # remove prefixo duplicado, se já vier prefixado
            low = stem.lower()
            prefixo = f"{grupo}_"
            if low.startswith(prefixo):
                stem = stem[len(prefixo):] or "sem_nome"

            ts = datetime.now().strftime("%Y%m%d%H%M%S%f")
            novo_nome = f"{grupo}_{ts}_{stem}{ext}"
            dest = STAGING_DIR / novo_nome

            shutil.move(str(src), str(dest))
            total_movidos += 1
            print(f"[MOVIDO] {src.name} -> {dest.name}")

    print("")
    print(f"TOTAL MOVIDOS: {total_movidos}")
    print(f"TOTAL IGNORADOS: {total_ignorados}")
    print(f"STAGING_DIR: {STAGING_DIR}")


if __name__ == "__main__":
    main()
