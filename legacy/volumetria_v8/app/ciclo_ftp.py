import os
import traceback
from pathlib import Path

from db_eventos import registrar_execucao_inicio, registrar_execucao_fim
from ingestor_ftp import main as ingestor_main
from sync_csv_para_db import main as sync_main

BASE_DIR = Path(r"E:\PROJETO VALE\PACOTE_PILOTO_VM\PRODUTO_VOLUMETRIA_RELEASE_V8")
STAGING_DIR = BASE_DIR / "input" / "images"

def main():
    execucao_id = registrar_execucao_inicio(
        status="iniciado",
        mensagem="ciclo_ftp iniciado"
    )

    try:
        STAGING_DIR.mkdir(parents=True, exist_ok=True)

        os.environ["VALE_INPUT_DIR"] = str(STAGING_DIR)

        ingestor_main()

        from main_incremental import main as pipeline_main
        pipeline_main()

        sync_main()

        registrar_execucao_fim(
            execucao_id,
            status="ok",
            mensagem="ciclo_ftp finalizado com sucesso"
        )
        print("[OK] ciclo_ftp finalizado com sucesso")

    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        registrar_execucao_fim(
            execucao_id,
            status="erro",
            mensagem=msg
        )
        print("[ERRO] ciclo_ftp falhou")
        print(msg)
        print(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
