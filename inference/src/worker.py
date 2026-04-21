"""Worker de inferência.

Responsabilidades esperadas:
- ler imagens novas do S3 ou fila
- executar segmentação e classificação
- aplicar regras de contaminação
- persistir resultado no MySQL
- salvar debug no S3
"""


def main() -> None:
    print("Inference worker bootstrap")


if __name__ == "__main__":
    main()
