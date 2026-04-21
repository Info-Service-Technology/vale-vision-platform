import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

BASE_DIR = Path(r"E:\PROJETO VALE\PACOTE_PILOTO_VM\PRODUTO_VOLUMETRIA_RELEASE_V8")
DB_PATH = BASE_DIR / "data" / "eventos.db"

st.set_page_config(
    page_title="Vale | Dashboard Operacional",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: "Segoe UI", sans-serif;
}
.main {
    background: linear-gradient(180deg, #0b1220 0%, #111827 100%);
}
.block-container {
    padding-top: 1.2rem;
    padding-bottom: 1rem;
    max-width: 96%;
}
h1, h2, h3 {
    color: #f8fafc !important;
}
div[data-testid="stMetric"] {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    padding: 16px;
    border-radius: 18px;
}
.card-custom {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 20px;
    padding: 18px;
    margin-bottom: 12px;
}
.card-title {
    font-size: 14px;
    color: #94a3b8;
    margin-bottom: 6px;
}
.card-value {
    font-size: 28px;
    font-weight: 700;
    color: #f8fafc;
}
.small-muted {
    font-size: 12px;
    color: #94a3b8;
}
hr {
    border-color: rgba(255,255,255,0.08);
}
</style>
""", unsafe_allow_html=True)


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
            LIMIT 100
            """,
            conn
        )
    return df


def prepare_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    df["ts_processamento"] = pd.to_datetime(df["ts_processamento"], errors="coerce")
    df["fill_percent"] = pd.to_numeric(df["fill_percent"], errors="coerce")
    df["alerta_contaminacao"] = pd.to_numeric(df["alerta_contaminacao"], errors="coerce").fillna(0).astype(int)
    df["alerta"] = pd.to_numeric(df["alerta"], errors="coerce").fillna(0).astype(int)
    df["ok_consec"] = pd.to_numeric(df["ok_consec"], errors="coerce").fillna(0).astype(int)

    for c in ["grupo", "status", "estado_dashboard", "motivo_falha", "materiais_detectados_raw", "contaminantes_detectados"]:
        if c in df.columns:
            df[c] = df[c].fillna("").astype(str)

    df["dia"] = df["ts_processamento"].dt.date.astype(str)
    return df


def ultimo_evento_por_grupo(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return df.sort_values("ts_processamento", ascending=False).groupby("grupo", as_index=False).first()


def color_estado(estado: str) -> str:
    estado = (estado or "").lower()
    if estado in ["critico", "trocar_cacamba", "vermelho"]:
        return "#ef4444"
    if estado in ["atencao", "atenção", "amarelo"]:
        return "#f59e0b"
    return "#22c55e"


def render_group_card(row):
    grupo = row.get("grupo", "-")
    fill = row.get("fill_percent", None)
    estado = row.get("estado_dashboard", "")
    cont = row.get("contaminantes_detectados", "")
    arquivo = row.get("arquivo_nome", "")
    status = row.get("status", "")
    cor = color_estado(estado)

    fill_txt = "-" if pd.isna(fill) else f"{float(fill):.2f}%"
    cont_txt = cont if str(cont).strip() else "nenhum"

    st.markdown(
        f"""
        <div class="card-custom">
            <div class="card-title">{grupo.upper()}</div>
            <div class="card-value">{fill_txt}</div>
            <div class="small-muted">estado: <span style="color:{cor};font-weight:700;">{estado or "-"}</span></div>
            <div class="small-muted">status: {status or "-"}</div>
            <div class="small-muted">contaminante: {cont_txt}</div>
            <div class="small-muted">último arquivo: {arquivo}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


df = prepare_df(load_eventos())
df_exec = load_execucoes()

top1, top2 = st.columns([0.8, 0.2])
with top1:
    st.title("Projeto Vale — Dashboard Operacional")
    st.caption("Release V8 | monitoramento contínuo | leitura direta do SQLite")
with top2:
    if st.button("Atualizar painel", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

if df.empty:
    st.warning("Nenhum evento encontrado no banco ainda.")
    st.stop()

with st.sidebar:
    st.header("Filtros")

    incluir_sem_grupo = st.checkbox("Incluir sem_grupo", value=False)

    base = df.copy()
    if not incluir_sem_grupo:
        base = base[base["grupo"].str.lower() != "sem_grupo"]

    grupos = sorted([x for x in base["grupo"].dropna().unique().tolist() if x])
    grupos_sel = st.multiselect("Grupo", grupos, default=grupos)

    status_list = sorted([x for x in base["status"].dropna().unique().tolist() if x])
    status_sel = st.multiselect("Status", status_list, default=status_list)

    estado_list = sorted([x for x in base["estado_dashboard"].dropna().unique().tolist() if x])
    estado_sel = st.multiselect("Estado dashboard", estado_list, default=estado_list)

    dias = sorted(base["dia"].dropna().unique().tolist())
    dias_sel = st.multiselect("Dias", dias, default=dias[-7:] if len(dias) > 7 else dias)

    somente_cont = st.checkbox("Somente com alerta de contaminação", value=False)
    somente_falha = st.checkbox("Somente com falha", value=False)

f = df.copy()

if not incluir_sem_grupo:
    f = f[f["grupo"].str.lower() != "sem_grupo"]
if grupos_sel:
    f = f[f["grupo"].isin(grupos_sel)]
if status_sel:
    f = f[f["status"].isin(status_sel)]
if estado_sel:
    f = f[f["estado_dashboard"].isin(estado_sel)]
if dias_sel:
    f = f[f["dia"].isin(dias_sel)]
if somente_cont:
    f = f[f["alerta_contaminacao"] == 1]
if somente_falha:
    f = f[f["motivo_falha"].str.strip() != ""]

total = len(f)
total_cont = int((f["alerta_contaminacao"] == 1).sum()) if not f.empty else 0
total_falha = int(f["motivo_falha"].str.strip().ne("").sum()) if not f.empty else 0
fill_medio = round(float(f["fill_percent"].dropna().mean()), 2) if not f["fill_percent"].dropna().empty else 0.0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Eventos filtrados", total)
m2.metric("Alertas de contaminação", total_cont)
m3.metric("Eventos com falha", total_falha)
m4.metric("Fill médio (%)", fill_medio)

st.markdown("---")

st.subheader("Situação atual por caçamba")
ult = ultimo_evento_por_grupo(f if not f.empty else df)
cards = st.columns(3)
ordem = ["madeira", "plastico", "sucata"]
for i, grupo in enumerate(ordem):
    row_df = ult[ult["grupo"] == grupo]
    with cards[i]:
        if not row_df.empty:
            render_group_card(row_df.iloc[0].to_dict())
        else:
            st.markdown(
                f"""
                <div class="card-custom">
                    <div class="card-title">{grupo.upper()}</div>
                    <div class="card-value">-</div>
                    <div class="small-muted">sem eventos nos filtros atuais</div>
                </div>
                """,
                unsafe_allow_html=True
            )

st.markdown("---")

g1, g2 = st.columns([1.2, 1])

with g1:
    st.subheader("Eventos por dia e grupo")
    if not f.empty:
        serie = f.groupby(["dia", "grupo"], as_index=False).agg(eventos=("id", "count"))
        fig = px.bar(
            serie,
            x="dia",
            y="eventos",
            color="grupo",
            barmode="group",
            template="plotly_dark"
        )
        fig.update_layout(height=360, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados para o gráfico.")

with g2:
    st.subheader("Distribuição de status")
    if not f.empty and f["status"].str.strip().ne("").any():
        dist = f.groupby("status", as_index=False).agg(eventos=("id", "count"))
        fig2 = px.pie(
            dist,
            names="status",
            values="eventos",
            hole=0.55,
            template="plotly_dark"
        )
        fig2.update_layout(height=360, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Sem status para exibir.")

g3, g4 = st.columns([1, 1])

with g3:
    st.subheader("Fill médio por grupo")
    if not f.empty:
        resumo = (
            f.groupby("grupo", as_index=False)
            .agg(
                eventos=("id", "count"),
                fill_medio=("fill_percent", "mean"),
                alertas_cont=("alerta_contaminacao", "sum")
            )
        )
        resumo["fill_medio"] = resumo["fill_medio"].round(2)
        fig3 = px.bar(
            resumo,
            x="grupo",
            y="fill_medio",
            text="fill_medio",
            color="grupo",
            template="plotly_dark"
        )
        fig3.update_layout(height=340, margin=dict(l=10, r=10, t=20, b=10), showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)
        st.dataframe(resumo, use_container_width=True, hide_index=True)
    else:
        st.info("Sem dados para resumo.")

with g4:
    st.subheader("Contaminação por grupo")
    if not f.empty:
        resumo2 = (
            f.groupby("grupo", as_index=False)
            .agg(
                alertas_cont=("alerta_contaminacao", "sum"),
                eventos=("id", "count")
            )
        )
        fig4 = px.bar(
            resumo2,
            x="grupo",
            y="alertas_cont",
            text="alertas_cont",
            color="grupo",
            template="plotly_dark"
        )
        fig4.update_layout(height=340, margin=dict(l=10, r=10, t=20, b=10), showlegend=False)
        st.plotly_chart(fig4, use_container_width=True)
        st.dataframe(resumo2, use_container_width=True, hide_index=True)
    else:
        st.info("Sem dados para contaminação.")

st.markdown("---")

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
st.dataframe(f[cols_exibir], use_container_width=True, height=320, hide_index=True)

st.markdown("---")

st.subheader("Análise visual do evento")
if not f.empty:
    opcoes = [
        f"{row['id']} | {row['grupo']} | {row['arquivo_nome']}"
        for _, row in f.head(200).iterrows()
    ]
    escolha = st.selectbox("Selecione um evento", opcoes, index=0)
    id_sel = int(escolha.split("|")[0].strip())
    row = f[f["id"] == id_sel].iloc[0]

    d1, d2 = st.columns([0.95, 1.25])

    with d1:
        st.markdown("### Metadados")
        meta_cols = [
            "arquivo_nome", "grupo", "status", "fill_percent", "estado_dashboard",
            "materiais_detectados_raw", "contaminantes_detectados",
            "alerta_contaminacao", "motivo_falha",
            "modelo_volumetria_versao", "modelo_contaminantes_versao",
            "ts_processamento"
        ]
        for c in meta_cols:
            if c in row.index:
                st.write(f"**{c}:** {row[c]}")

    with d2:
        debug_path = row.get("debug_path", None)
        if debug_path and Path(str(debug_path)).exists():
            st.markdown("### Imagem debug")
            st.image(str(debug_path), use_container_width=True)
        else:
            st.info("Sem imagem debug disponível para este evento.")

st.markdown("---")

st.subheader("Execuções recentes do serviço")
if not df_exec.empty:
    st.dataframe(df_exec, use_container_width=True, height=220, hide_index=True)
else:
    st.info("Nenhuma execução registrada ainda.")
