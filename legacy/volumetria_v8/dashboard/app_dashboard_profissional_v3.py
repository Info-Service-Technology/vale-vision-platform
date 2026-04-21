import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_autorefresh import st_autorefresh

BASE_DIR = Path(r"E:\PROJETO VALE\PACOTE_PILOTO_VM\PRODUTO_VOLUMETRIA_RELEASE_V8")
DB_PATH = BASE_DIR / "data" / "eventos.db"

st.set_page_config(
    page_title="Vale | Dashboard Operacional V3",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
html, body, [class*="css"] { font-family: "Segoe UI", sans-serif; }
.main { background: linear-gradient(180deg, #08111f 0%, #0f172a 100%); }
.block-container { padding-top: 1.0rem; padding-bottom: 1rem; max-width: 96%; }
h1, h2, h3 { color: #f8fafc !important; }
div[data-testid="stMetric"] {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    padding: 16px;
    border-radius: 18px;
}
.card-custom, .section-box, .thumb-box {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 20px;
    padding: 16px;
}
.thumb-box { min-height: 255px; }
.card-title { font-size: 13px; color: #94a3b8; margin-bottom: 6px; }
.card-value { font-size: 28px; font-weight: 700; color: #f8fafc; }
.small-muted { font-size: 12px; color: #94a3b8; }
.badge {
    display:inline-block; padding: 4px 10px; border-radius: 999px;
    font-size: 12px; font-weight: 700; margin-right: 6px; margin-bottom: 6px;
}
hr { border-color: rgba(255,255,255,0.08); }
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
                id, ts_processamento, data_ref, hora_ref,
                arquivo_nome, arquivo_path, grupo, status,
                fill_percent, estado_dashboard, ok_consec, alerta,
                materiais_detectados_raw, contaminantes_detectados,
                alerta_contaminacao, motivo_falha,
                modelo_volumetria_versao, modelo_contaminantes_versao,
                evidencia_path, debug_path, origem,
                processado_com_sucesso, criado_em
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
    for c in ["grupo","status","estado_dashboard","motivo_falha","materiais_detectados_raw","contaminantes_detectados"]:
        df[c] = df[c].fillna("").astype(str)
    df["dia"] = df["ts_processamento"].dt.date.astype(str)
    return df

def cor_estado(estado: str) -> str:
    e = (estado or "").lower()
    if e in ["critico", "crítico", "trocar_cacamba", "vermelho"]:
        return "#ef4444"
    if e in ["atencao", "atenção", "amarelo", "revisar"]:
        return "#f59e0b"
    return "#22c55e"

def badge(txt: str, bg: str, fg: str = "#ffffff") -> str:
    return f'<span class="badge" style="background:{bg};color:{fg};">{txt}</span>'

def faixa_fill(fill):
    if pd.isna(fill):
        return "—"
    f = float(fill)
    if f >= 95: return "crítico"
    if f >= 85: return "muito alto"
    if f >= 60: return "alto"
    if f >= 30: return "médio"
    return "baixo"

def acao_operacional(status, estado, fill, motivo):
    status = (status or "").lower()
    estado = (estado or "").lower()
    motivo = (motivo or "").lower()

    if status != "ok":
        if motivo == "suspeito_floor_quase_zero":
            return "revisão visual obrigatória"
        return "revisar imagem"

    if pd.isna(fill):
        return "revisar imagem"

    f = float(fill)
    if f >= 95:
        return "trocar caçamba"
    if f >= 85:
        return "programar troca"
    if f >= 60:
        return "monitorar alto enchimento"
    return "operação normal"

def confianca_fill(status, fill):
    status = (status or "").lower()
    if status == "ok" and not pd.isna(fill):
        return "alta"
    return "baixa"

def fill_tecnico_exibicao(status, fill):
    status = (status or "").lower()
    if status == "ok" and not pd.isna(fill):
        return f"{float(fill):.2f}%"
    return "—"

def nivel_operacional(status, fill, motivo):
    status = (status or "").lower()
    motivo = (motivo or "").lower()

    if status != "ok":
        if motivo == "suspeito_floor_quase_zero":
            return "indeterminado"
        return "revisar"

    return faixa_fill(fill)

def ultimo_evento_por_grupo(df):
    if df.empty:
        return df
    return df.sort_values("ts_processamento", ascending=False).groupby("grupo", as_index=False).first()

def render_group_card(row):
    grupo = row.get("grupo", "-")
    fill = row.get("fill_percent", None)
    estado = row.get("estado_dashboard", "")
    status = row.get("status", "")
    motivo = row.get("motivo_falha", "")
    conf = confianca_fill(status, fill)
    nivel = nivel_operacional(status, fill, motivo)
    fill_txt = fill_tecnico_exibicao(status, fill)
    acao = acao_operacional(status, estado, fill, motivo)

    cor = cor_estado(estado)

    st.markdown(
        f"""
        <div class="card-custom">
            <div class="card-title">{grupo.upper()}</div>
            <div class="card-value">{fill_txt}</div>
            <div class="small-muted">nível operacional: <b>{nivel}</b></div>
            <div class="small-muted">confiança: <b>{conf}</b></div>
            <div class="small-muted">estado: <span style="color:{cor};font-weight:700;">{estado or "-"}</span></div>
            <div class="small-muted">ação: <b>{acao}</b></div>
        </div>
        """,
        unsafe_allow_html=True
    )

df = prepare_df(load_eventos())
df_exec = load_execucoes()

if "selected_event_id_v3" not in st.session_state:
    st.session_state.selected_event_id_v3 = None

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

    base = df.copy()
    if not base.empty and not incluir_sem_grupo:
        base = base[base["grupo"].str.lower() != "sem_grupo"]

    grupos = sorted([x for x in base["grupo"].dropna().unique().tolist() if x])
    grupos_sel = st.multiselect("Grupo", grupos, default=grupos)

    status_list = sorted([x for x in base["status"].dropna().unique().tolist() if x])
    status_sel = st.multiselect("Status", status_list, default=status_list)

    estado_list = sorted([x for x in base["estado_dashboard"].dropna().unique().tolist() if x])
    estado_sel = st.multiselect("Estado dashboard", estado_list, default=estado_list)

    dias = sorted(base["dia"].dropna().unique().tolist()) if not base.empty else []
    dias_sel = st.multiselect("Dias", dias, default=dias[-7:] if len(dias) > 7 else dias)

    somente_cont = st.checkbox("Somente com alerta de contaminação", value=False)
    somente_falha = st.checkbox("Somente com falha", value=False)

if auto_refresh:
    st_autorefresh(interval=intervalo * 1000, key="auto_refresh_dashboard_v3")

top1, top2 = st.columns([0.82, 0.18])
with top1:
    st.title("Projeto Vale — Dashboard Operacional")
    st.caption("Release V8 | camada operacional V3")
with top2:
    st.markdown(
        f"""
        <div class="section-box" style="text-align:center;">
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

f["fill_tecnico_exibicao"] = f.apply(lambda r: fill_tecnico_exibicao(r["status"], r["fill_percent"]), axis=1)
f["confianca_fill"] = f.apply(lambda r: confianca_fill(r["status"], r["fill_percent"]), axis=1)
f["nivel_operacional"] = f.apply(lambda r: nivel_operacional(r["status"], r["fill_percent"], r["motivo_falha"]), axis=1)
f["acao_operacional"] = f.apply(lambda r: acao_operacional(r["status"], r["estado_dashboard"], r["fill_percent"], r["motivo_falha"]), axis=1)

total = len(f)
total_cont = int((f["alerta_contaminacao"] == 1).sum())
total_falha = int(f["motivo_falha"].str.strip().ne("").sum())
fill_medio_ok = round(float(f.loc[f["status"].str.lower() == "ok", "fill_percent"].dropna().mean()), 2) if not f.loc[f["status"].str.lower() == "ok", "fill_percent"].dropna().empty else 0.0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Eventos filtrados", total)
m2.metric("Alertas de contaminação", total_cont)
m3.metric("Eventos com falha", total_falha)
m4.metric("Fill médio confiável (%)", fill_medio_ok)

st.markdown("---")

st.subheader("Situação atual por caçamba")
ult = ultimo_evento_por_grupo(f)
cards = st.columns(3)
for i, grupo in enumerate(["madeira", "plastico", "sucata"]):
    row_df = ult[ult["grupo"] == grupo]
    with cards[i]:
        if not row_df.empty:
            render_group_card(row_df.iloc[0].to_dict())
        else:
            st.markdown(
                f"""
                <div class="card-custom">
                    <div class="card-title">{grupo.upper()}</div>
                    <div class="card-value">—</div>
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
    st.markdown("### Resumo operacional")
    st.markdown(
        badge(f"status: {ultimo['status']}", "#1f2937") +
        badge(f"nível: {ultimo['nivel_operacional']}", "#7c3aed") +
        badge(f"confiança: {ultimo['confianca_fill']}", "#0f766e") +
        badge(f"ação: {ultimo['acao_operacional']}", "#92400e"),
        unsafe_allow_html=True
    )

    campos = [
        ("arquivo", "arquivo_nome"),
        ("grupo", "grupo"),
        ("fill técnico", "fill_tecnico_exibicao"),
        ("estado", "estado_dashboard"),
        ("materiais", "materiais_detectados_raw"),
        ("contaminantes", "contaminantes_detectados"),
        ("motivo", "motivo_falha"),
        ("processado em", "ts_processamento"),
    ]
    for titulo, chave in campos:
        valor = ultimo.get(chave, "")
        st.write(f"**{titulo}:** {valor if str(valor).strip() else '—'}")

st.markdown("---")

st.subheader("Últimas 20 análises")
ult20 = f.sort_values("ts_processamento", ascending=False).head(20).copy()

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

            st.write(f"**{row['grupo']}**")
            st.caption(row["arquivo_nome"])
            st.caption(f"fill técnico: {row['fill_tecnico_exibicao']}")
            st.caption(f"nível: {row['nivel_operacional']} | confiança: {row['confianca_fill']}")

            if st.button("Ver detalhe", key=f"v3_det_{int(row['id'])}", use_container_width=True):
                st.session_state.selected_event_id_v3 = int(row["id"])

            st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

st.subheader("Detalhe visual selecionado")

if st.session_state.selected_event_id_v3 is None:
    st.session_state.selected_event_id_v3 = int(ultimo["id"])

row_sel_df = f[f["id"] == st.session_state.selected_event_id_v3]
row_sel = row_sel_df.iloc[0] if not row_sel_df.empty else ultimo

d1, d2 = st.columns([1.0, 1.1])

with d1:
    st.markdown("### Metadados e decisão")
    st.markdown(
        badge(f"status: {row_sel['status']}", "#1f2937") +
        badge(f"nível: {row_sel['nivel_operacional']}", "#7c3aed") +
        badge(f"confiança: {row_sel['confianca_fill']}", "#0f766e") +
        badge(f"ação: {row_sel['acao_operacional']}", "#92400e"),
        unsafe_allow_html=True
    )

    meta_cols = [
        "arquivo_nome", "grupo", "fill_tecnico_exibicao", "estado_dashboard",
        "materiais_detectados_raw", "contaminantes_detectados",
        "alerta_contaminacao", "motivo_falha",
        "modelo_volumetria_versao", "modelo_contaminantes_versao",
        "ts_processamento"
    ]
    for c in meta_cols:
        valor = row_sel.get(c, "")
        st.write(f"**{c}:** {valor if str(valor).strip() else '—'}")

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
    fig = px.bar(serie, x="dia", y="eventos", color="grupo", barmode="group", template="plotly_dark")
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, use_container_width=True)

with g2:
    st.subheader("Distribuição de ação operacional")
    dist = f.groupby("acao_operacional", as_index=False).agg(eventos=("id", "count"))
    fig2 = px.pie(dist, names="acao_operacional", values="eventos", hole=0.55, template="plotly_dark")
    fig2.update_layout(height=320, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig2, use_container_width=True)

st.subheader("Tabela operacional")
cols_exibir = [
    "ts_processamento", "arquivo_nome", "grupo", "status",
    "fill_tecnico_exibicao", "nivel_operacional", "confianca_fill",
    "acao_operacional", "estado_dashboard", "motivo_falha"
]
st.dataframe(f[cols_exibir], use_container_width=True, height=320, hide_index=True)

st.markdown("---")

st.subheader("Execuções recentes do serviço")
if not df_exec.empty:
    st.dataframe(df_exec, use_container_width=True, height=220, hide_index=True)
else:
    st.info("Nenhuma execução registrada ainda.")
