from pathlib import Path
import json

from segmentador_contaminantes import SegmentadorContaminantes

TEST_IMAGES = [
    Path(r"E:\PROJETO VALE\PRODUTO_VOLUMETRIA_RELEASE_V8\input\images\madeira_GF0191277_20260304094044524_MD_WITH_TARGET.jpg"),
    Path(r"E:\PROJETO VALE\PRODUTO_VOLUMETRIA_RELEASE_V8\input\images\plastico_GF0191275_20260304094034849_MD_WITH_TARGET.jpg"),
    Path(r"E:\PROJETO VALE\PRODUTO_VOLUMETRIA_RELEASE_V8\input\images\sucata_GF0191272_20260309141258871_MD_WITH_TARGET.jpg"),
]

def main():
    seg = SegmentadorContaminantes()

    print("ativo =", seg.ativo)
    print("model_path =", seg.model_path)
    print()

    for img_path in TEST_IMAGES:
        print("=" * 80)
        print("imagem:", img_path)

        if not img_path.exists():
            print("ERRO: imagem não encontrada")
            continue

        result = seg.inferir(str(img_path))
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()