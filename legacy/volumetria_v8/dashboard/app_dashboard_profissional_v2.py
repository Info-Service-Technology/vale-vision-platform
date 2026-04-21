import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_autorefresh import st_autorefresh

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
    background: linear-gradient(180deg, #08111f 0%, #0f172a 100%);
}
.block-container {
    padding-top: 1.0rem;
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
    font-size: 13px;
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
.section-box {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 20px;
    padding: 16px;
    margin-bottom: 12px;
}
.thumb-box {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 10px;
    min-height: 250px;
}
hr {
    border-color: rgba(255,255,255,0.08);
}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=20)
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


@st.cache_data(ttl=20)
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
    if estado in ["atencao", "atenção", "amarelo", "revisar"]:
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


def evento_label(row):
    return f"{int(row['id'])} | {row['grupo']} | {row['arquivo_nome']}"


df = prepare_df(load_eventos())
df_exec = load_execucoes()

if "selected_event_id" not in st.session_state:
    st.session_state.selected_event_id = None

with st.sidebar:
    st.header("Painel")

    auto_refresh = st.checkbox("Atualização automática", value=True)
    intervalo = st.selectbox("Intervalo", [15, 30, 60, 120], index=2)

    if st.button("Atualizar agora", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.header("Filtros")

    incluir_sem_grupo = st.checkbox("Incluir sem_grupo", value=False)

    base_sidebar = df.copy()
    if not base_sidebar.empty and not incluir_sem_grupo:
        base_sidebar = base_sidebar[base_sidebar["grupo"].str.lower() != "sem_grupo"]

    grupos = sorted([x for x in base_sidebar["grupo"].dropna().unique().tolist() if x])
    grupos_sel = st.multiselect("Grupo", grupos, default=grupos)

    status_list = sorted([x for x in base_sidebar["status"].dropna().unique().tolist() if x])
    status_sel = st.multiselect("Status", status_list, default=status_list)

    estado_list = sorted([x for x in base_sidebar["estado_dashboard"].dropna().unique().tolist() if x])
    estado_sel = st.multiselect("Estado dashboard", estado_list, default=estado_list)

    dias = sorted(base_sidebar["dia"].dropna().unique().tolist()) if not base_sidebar.empty else []
    dias_sel = st.multiselect("Dias", dias, default=dias[-7:] if len(dias) > 7 else dias)

    somente_cont = st.checkbox("Somente com alerta de contaminação", value=False)
    somente_falha = st.checkbox("Somente com falha", value=False)

if auto_refresh:
    st_autorefresh(interval=intervalo * 1000, key="auto_refresh_dashboard")

top1, top2 = st.columns([0.82, 0.18])
with top1:
    st.title("Projeto Vale — Dashboard Operacional")
    st.caption("Release V8 | monitoramento contínuo | leitura direta do SQLite")
with top2:
    st.markdown(
        f"""
        <div class="section-box" style="text-align:center;padding:14px;">
            <div class="card-title">atualização</div>
            <div class="card-value" style="font-size:22px;">{intervalo}s</div>
        </div>
        """,
        unsafe_allow_html=True
    )

if df.empty:
    st.warning("Nenhum evento encontrado no banco ainda.")
    st.stop()

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

if f.empty:
    st.warning("Sem dados para os filtros atuais.")
    st.stop()

total = len(f)
total_cont = int((f["alerta_contaminacao"] == 1).sum())
total_falha = int(f["motivo_falha"].str.strip().ne("").sum())
fill_medio = round(float(f["fill_percent"].dropna().mean()), 2) if not f["fill_percent"].dropna().empty else 0.0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Eventos filtrados", total)
m2.metric("Alertas de contaminação", total_cont)
m3.metric("Eventos com falha", total_falha)
m4.metric("Fill médio (%)", fill_medio)

st.markdown("---")

st.subheader("Situação atual por caçamba")
ult = ultimo_evento_por_grupo(f)
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

st.subheader("Última análise")
ultimo = f.sort_values("ts_processamento", ascending=False).iloc[0]

c1, c2 = st.columns([1.15, 0.85])

with c1:
    debug_path = ultimo.get("debug_path", None)
    if debug_path and Path(str(debug_path)).exists():
        st.image(str(debug_path), use_container_width=True)
    else:
        st.info("Sem imagem debug disponível para a última análise.")

with c2:
    st.markdown("### Resumo do evento atual")
    campos = [
        ("arquivo", "arquivo_nome"),
        ("grupo", "grupo"),
        ("status", "status"),
        ("fill", "fill_percent"),
        ("estado", "estado_dashboard"),
        ("materiais", "materiais_detectados_raw"),
        ("contaminantes", "contaminantes_detectados"),
        ("alerta contaminação", "alerta_contaminacao"),
        ("motivo falha", "motivo_falha"),
        ("processado em", "ts_processamento"),
    ]
    for titulo, chave in campos:
        valor = ultimo.get(chave, "")
        if chave == "fill_percent" and pd.notna(valor):
            valor = f"{float(valor):.2f}%"
        st.write(f"**{titulo}:** {valor if str(valor).strip() else '-'}")

st.markdown("---")

st.subheader("Últimas 20 análises")
ult20 = f.sort_values("ts_processamento", ascending=False).head(20).copy()

# galeria em linhas de 4
for start in range(0, len(ult20), 4):
    cols = st.columns(4)
    bloco = ult20.iloc[start:start+4]

    for idx, (_, row) in enumerate(bloco.iterrows()):
        with cols[idx]:
            st.markdown('<div class="thumb-box">', unsafe_allow_html=True)
            debug_path = row.get("debug_path", None)
            if debug_path and Path(str(debug_path)).exists():
                st.image(str(debug_path), use_container_width=True)
            else:
                st.info("Sem debug")

            fill_txt = "-" if pd.isna(row.get("fill_percent", None)) else f"{float(row['fill_percent']):.2f}%"
            st.write(f"**{row['grupo']}**")
            st.caption(f"{row['arquivo_nome']}")
            st.caption(f"status: {row['status']} | fill: {fill_txt}")

            if st.button("Ver detalhe", key=f"det_{int(row['id'])}", use_container_width=True):
                st.session_state.selected_event_id = int(row["id"])

            st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

st.subheader("Detalhe visual selecionado")

if st.session_state.selected_event_id is None:
    st.session_state.selected_event_id = int(ultimo["id"])

row_sel_df = f[f["id"] == st.session_state.selected_event_id]
if row_sel_df.empty:
    row_sel = ultimo
else:
    row_sel = row_sel_df.iloc[0]

d1, d2 = st.columns([1.0, 1.1])

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
        valor = row_sel.get(c, "")
        if c == "fill_percent" and pd.notna(valor):
            valor = f"{float(valor):.2f}%"
        st.write(f"**{c}:** {valor if str(valor).strip() else '-'}")

with d2:
    debug_path = row_sel.get("debug_path", None)
    if debug_path and Path(str(debug_path)).exists():
        st.markdown("### Imagem debug")
        st.image(str(debug_path), use_container_width=True)
    else:
        st.info("Sem imagem debug disponível para este evento.")

st.markdown("---")

g1, g2 = st.columns([1.2, 1])

with g1:
    st.subheader("Eventos por dia e grupo")
    serie = f.groupby(["dia", "grupo"], as_index=False).agg(eventos=("id", "count"))
    fig = px.bar(
        serie,
        x="dia",
        y="eventos",
        color="grupo",
        barmode="group",
        template="plotly_dark"
    )
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, use_container_width=True)

with g2:
    st.subheader("Distribuição de status")
    if f["status"].str.strip().ne("").any():
        dist = f.groupby("status", as_index=False).agg(eventos=("id", "count"))
        fig2 = px.pie(
            dist,
            names="status",
            values="eventos",
            hole=0.55,
            template="plotly_dark"
        )
        fig2.update_layout(height=340, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Sem status para exibir.")

st.subheader("Tabela operacional")
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
st.dataframe(f[cols_exibir], use_container_width=True, height=320, hide_index=True)

st.markdown("---")

st.subheader("Execuções recentes do serviço")
if not df_exec.empty:
    st.dataframe(df_exec, use_container_width=True, height=220, hide_index=True)
else:
    st.info("Nenhuma execução registrada ainda.")
