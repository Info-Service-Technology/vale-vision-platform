from pathlib import Path

path = Path(r"E:\PROJETO VALE\PACOTE_PILOTO_VM\PRODUTO_VOLUMETRIA_RELEASE_V8\dashboard\app_dashboard_profissional_v5.py")
text = path.read_text(encoding="utf-8")

old_func = '''
def salvar_upload_teste(uploaded_file, grupo: str) -> Path:
    grupo_dir = INPUT_FTP_DIR / grupo
    grupo_dir.mkdir(parents=True, exist_ok=True)

    nome_limpo = sanitize_filename(uploaded_file.name)
    stem = Path(nome_limpo).stem
    suffix = Path(nome_limpo).suffix.lower() or ".jpg"
    ts = datetime.now().strftime("%Y%m%d%H%M%S%f")

    destino = grupo_dir / f"manual_{ts}_{stem}{suffix}"
    destino.write_bytes(uploaded_file.getbuffer())
    return destino
'''

new_func = '''
def detectar_grupo_do_nome(nome: str):
    low = nome.strip().lower()
    for grupo in ("madeira", "plastico", "sucata"):
        if low.startswith(grupo + "_"):
            return grupo
    return None


def salvar_upload_teste(uploaded_file, grupo: str):
    nome_limpo = sanitize_filename(uploaded_file.name)
    grupo_detectado = detectar_grupo_do_nome(nome_limpo)
    grupo_final = grupo_detectado if grupo_detectado else grupo

    grupo_dir = INPUT_FTP_DIR / grupo_final
    grupo_dir.mkdir(parents=True, exist_ok=True)

    stem = Path(nome_limpo).stem
    suffix = Path(nome_limpo).suffix.lower() or ".jpg"
    ts = datetime.now().strftime("%Y%m%d%H%M%S%f")

    destino = grupo_dir / f"manual_{ts}_{stem}{suffix}"
    destino.write_bytes(uploaded_file.getbuffer())
    return destino, grupo_final
'''

old_call = '''
            destino = salvar_upload_teste(uploaded_file, grupo_upload)
            st.success(f"Imagem enviada para fila de teste: {destino.name}")
            st.info("O loop vai processar automaticamente. Com intervalo de 10s, ela deve aparecer no painel em poucos segundos.")
            st.cache_data.clear()
'''

new_call = '''
            destino, grupo_final = salvar_upload_teste(uploaded_file, grupo_upload)
            st.success(f"Imagem enviada para fila de teste: {destino.name}")

            if grupo_final != grupo_upload:
                st.warning(f"Grupo detectado pelo nome do arquivo: {grupo_final}. O grupo selecionado foi ignorado.")
            else:
                st.info(f"Grupo efetivo do teste: {grupo_final}")

            st.info("O loop vai processar automaticamente. Com intervalo de 10s, ela deve aparecer no painel em poucos segundos.")
            st.cache_data.clear()
'''

if old_func not in text:
    raise RuntimeError("Nao achei a funcao antiga salvar_upload_teste")

text = text.replace(old_func, new_func, 1)

if old_call not in text:
    raise RuntimeError("Nao achei o bloco antigo do botao de upload")

text = text.replace(old_call, new_call, 1)

path.write_text(text, encoding="utf-8")
print("[OK] Patch V5 grupo hibrido aplicado com sucesso")
