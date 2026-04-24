import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(r"E:\PROJETO VALE\PACOTE_PILOTO_VM\PRODUTO_VOLUMETRIA_RELEASE_V8")
DB_PATH = BASE_DIR / "data" / "eventos.db"

st.set_page_config(
    page_title="Vale - Volumetria",
    page_icon="📊",
    layout="wide"
)

@st.cache_data(ttl=15)
def load_eventos():
    if not DB_PATH.exists():
        return pd.DataFrame()

    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(
            """
            SELECT
                id,
                ts_processamento,
                data_ref,
                hora_ref,
                arquivo_nome,
                arquivo_path,
                grupo,
                status,
                fill_percent,
                estado_dashboard,
                ok_consec,
                alerta,
                materiais_detectados_raw,
                contaminantes_detectados,
                alerta_contaminacao,
                motivo_falha,
                modelo_volumetria_versao,
                modelo_contaminantes_versao,
                evidencia_path,
                debug_path,
                origem,
                processado_com_sucesso,
                criado_em
            FROM eventos
            ORDER BY id DESC
            """,
            conn
        )
    return df

@st.cache_data(ttl=15)
def load_execucoes():
    if not DB_PATH.exists():
        return pd.DataFrame()

    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(
            """
            SELECT id, ts_inicio, ts_fim, status, mensagem
            FROM execucoes_servico
            ORDER BY id DESC
            LIMIT 50
            """,
            conn
        )
    return df

df = load_eventos()
df_exec = load_execucoes()

st.title("Projeto Vale — Dashboard Operacional")
st.caption("Release V8 | leitura direta do SQLite")

if df.empty:
    st.warning("Nenhum evento encontrado no banco ainda.")
    st.stop()

for col in ["fill_percent", "alerta_contaminacao", "alerta", "ok_consec"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

with st.sidebar:
    st.header("Filtros")

    grupos = sorted([x for x in df["grupo"].dropna().unique().tolist() if x])
    grupos_sel = st.multiselect("Grupo", grupos, default=grupos)

    status_list = sorted([x for x in df["status"].dropna().unique().tolist() if x])
    status_sel = st.multiselect("Status", status_list, default=status_list)

    estado_list = sorted([x for x in df["estado_dashboard"].dropna().unique().tolist() if x])
    estado_sel = st.multiselect("Estado dashboard", estado_list, default=estado_list)

    somente_contaminacao = st.checkbox("Somente com alerta de contaminação", value=False)
    somente_falha = st.checkbox("Somente com motivo de falha", value=False)

f = df.copy()

if grupos_sel:
    f = f[f["grupo"].isin(grupos_sel)]
if status_sel:
    f = f[f["status"].isin(status_sel)]
if estado_sel:
    f = f[f["estado_dashboard"].isin(estado_sel)]
if somente_contaminacao:
    f = f[f["alerta_contaminacao"] == 1]
if somente_falha:
    f = f[f["motivo_falha"].fillna("").str.strip() != ""]

total = len(f)
total_cont = int((f["alerta_contaminacao"] == 1).sum()) if "alerta_contaminacao" in f.columns else 0
total_falha = int(f["motivo_falha"].fillna("").str.strip().ne("").sum())
fill_medio = round(float(f["fill_percent"].dropna().mean()), 2) if f["fill_percent"].dropna().shape[0] else 0.0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Eventos filtrados", total)
c2.metric("Alertas contaminação", total_cont)
c3.metric("Com falha", total_falha)
c4.metric("Fill médio (%)", fill_medio)

st.subheader("Resumo por grupo")
if not f.empty:
    resumo = (
        f.groupby("grupo", dropna=False)
        .agg(
            eventos=("id", "count"),
            fill_medio=("fill_percent", "mean"),
            alertas_cont=("alerta_contaminacao", "sum"),
        )
        .reset_index()
    )
    resumo["fill_medio"] = resumo["fill_medio"].round(2)
    st.dataframe(resumo, use_container_width=True)
else:
    st.info("Sem dados para os filtros escolhidos.")

st.subheader("Últimos eventos")
cols_exibir = [
    "ts_processamento",
    "arquivo_nome",
    "grupo",
    "status",
    "fill_percent",
    "estado_dashboard",
    "materiais_detectados_raw",
    "contaminantes_detectados",
    "alerta_contaminacao",
    "motivo_falha",
]
cols_exibir = [c for c in cols_exibir if c in f.columns]
st.dataframe(f[cols_exibir], use_container_width=True, height=380)

st.subheader("Detalhe visual")
if not f.empty:
    opcoes = [
        f"{row['id']} | {row['ts_processamento']} | {row['arquivo_nome']}"
        for _, row in f.head(100).iterrows()
    ]
    escolha = st.selectbox("Selecione um evento", opcoes)

    id_sel = int(escolha.split("|")[0].strip())
    row = f[f["id"] == id_sel].iloc[0]

    d1, d2 = st.columns([1, 1])

    with d1:
        st.markdown("**Metadados**")
        meta_cols = [
            "arquivo_nome", "grupo", "status", "fill_percent", "estado_dashboard",
            "materiais_detectados_raw", "contaminantes_detectados",
            "alerta_contaminacao", "motivo_falha",
            "modelo_volumetria_versao", "modelo_contaminantes_versao"
        ]
        for c in meta_cols:
            if c in row.index:
                st.write(f"**{c}:** {row[c]}")

    with d2:
        debug_path = row.get("debug_path", None)
        if debug_path and Path(debug_path).exists():
            st.markdown("**Imagem debug**")
            st.image(str(debug_path), use_container_width=True)
        else:
            st.info("Sem imagem debug disponível para este evento.")

st.subheader("Execuções do serviço")
if not df_exec.empty:
    st.dataframe(df_exec, use_container_width=True, height=240)
else:
    st.info("Nenhuma execução registrada ainda.")
