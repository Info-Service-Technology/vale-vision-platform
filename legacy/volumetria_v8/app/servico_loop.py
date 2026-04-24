import time
import traceback
from datetime import datetime

from ciclo_ftp import main as ciclo_main

INTERVALO_SEGUNDOS = 10

def main():
    print("[SERVICO] Loop iniciado")
    print(f"[SERVICO] Intervalo: {INTERVALO_SEGUNDOS}s")

    while True:
        try:
            agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print("")
            print(f"[SERVICO] Iniciando ciclo em {agora}")
            ciclo_main()
            print(f"[SERVICO] Ciclo concluido. Aguardando {INTERVALO_SEGUNDOS}s...")
        except Exception as e:
            print("[SERVICO][ERRO] Falha no loop")
            print(f"{type(e).__name__}: {e}")
            print(traceback.format_exc())

        time.sleep(INTERVALO_SEGUNDOS)

if __name__ == "__main__":
    main()
