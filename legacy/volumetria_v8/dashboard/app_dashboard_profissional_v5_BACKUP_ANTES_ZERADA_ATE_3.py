import re
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_autorefresh import st_autorefresh

BASE_DIR = Path(r"E:\PROJETO VALE\PACOTE_PILOTO_VM\PRODUTO_VOLUMETRIA_RELEASE_V8")
DB_PATH = BASE_DIR / "data" / "eventos.db"
INPUT_TESTE_DIR = BASE_DIR / "input" / "images"

st.set_page_config(
    page_title="Vale | Dashboard Operacional V5",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
html, body, [class*="css"] { font-family: "Segoe UI", sans-serif; }
.main { background: linear-gradient(180deg, #08111f 0%, #0f172a 100%); }
.block-container { padding-top: 1rem; padding-bottom: 1rem; max-width: 96%; }
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
.thumb-box { min-height: 265px; }
.card-title { font-size: 13px; color: #94a3b8; margin-bottom: 6px; }
.card-value { font-size: 28px; font-weight: 700; color: #f8fafc; }
.small-muted { font-size: 12px; color: #94a3b8; }
.badge {
    display:inline-block; padding: 4px 10px; border-radius: 999px;
    font-size: 12px; font-weight: 700; margin-right: 6px; margin-bottom: 6px;
}
.contam-box {
    margin-top: 10px;
    padding: 10px 12px;
    border-radius: 14px;
    font-size: 13px;
    font-weight: 800;
}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=20)
def load_eventos():
    if not DB_PATH.exists():
        return pd.DataFrame()

    wanted_cols = [
        "id", "ts_processamento", "data_ref", "hora_ref",
        "arquivo_nome", "arquivo_path", "grupo", "status",
        "fill_percent", "estado_dashboard", "ok_consec", "alerta",
        "materiais_detectados_raw", "contaminantes_detectados",
        "alerta_contaminacao", "tipo_contaminacao", "severidade_contaminacao",
        "motivo_falha",
        "modelo_volumetria_versao", "modelo_contaminantes_versao",
        "evidencia_path", "debug_path", "origem",
        "processado_com_sucesso", "criado_em"
    ]

    defaults = {
        "id": None,
        "ts_processamento": None,
        "data_ref": "",
        "hora_ref": "",
        "arquivo_nome": "",
        "arquivo_path": "",
        "grupo": "",
        "status": "",
        "fill_percent": None,
        "estado_dashboard": "",
        "ok_consec": 0,
        "alerta": 0,
        "materiais_detectados_raw": "",
        "contaminantes_detectados": "",
        "alerta_contaminacao": 0,
        "tipo_contaminacao": "",
        "severidade_contaminacao": 0,
        "motivo_falha": "",
        "modelo_volumetria_versao": "",
        "modelo_contaminantes_versao": "",
        "evidencia_path": "",
        "debug_path": "",
        "origem": "",
        "processado_com_sucesso": 0,
        "criado_em": "",
    }

    with sqlite3.connect(DB_PATH) as conn:
        cols_df = pd.read_sql_query("PRAGMA table_info(eventos)", conn)
        existing_cols = set(cols_df["name"].astype(str).tolist())

        select_cols = [c for c in wanted_cols if c in existing_cols]
        if not select_cols:
            return pd.DataFrame(columns=wanted_cols)

        sql = f"""
            SELECT {", ".join(select_cols)}
            FROM eventos
            ORDER BY id DESC
        """
        df = pd.read_sql_query(sql, conn)

    for c in wanted_cols:
        if c not in df.columns:
            df[c] = defaults.get(c, "")

    return df[wanted_cols]


@st.cache_data(ttl=20)
def load_execucoes():
    if not DB_PATH.exists():
        return pd.DataFrame()
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(
            """
            SELECT id, ts_inicio, ts_fim, status, mensagem
            FROM execucoes_servico
            ORDER BY id DESC
            LIMIT 100
            """,
            conn
        )


def prepare_df(df):
    if df.empty:
        return df
    df = df.copy()
    df["ts_processamento"] = pd.to_datetime(df["ts_processamento"], errors="coerce")
    df["fill_percent"] = pd.to_numeric(df["fill_percent"], errors="coerce")
    df["alerta_contaminacao"] = pd.to_numeric(df["alerta_contaminacao"], errors="coerce").fillna(0).astype(int)
    df["severidade_contaminacao"] = pd.to_numeric(df["severidade_contaminacao"], errors="coerce").fillna(0).astype(int)

    for c in [
        "grupo", "status", "estado_dashboard", "motivo_falha",
        "materiais_detectados_raw", "contaminantes_detectados",
        "tipo_contaminacao"
    ]:
        if c in df.columns:
            df[c] = df[c].fillna("").astype(str)

    df["dia"] = df["ts_processamento"].dt.date.astype(str)
    return df


def cor_estado(estado):
    e = (estado or "").lower()
    if e in ["critico", "crítico", "trocar_cacamba", "vermelho"]:
        return "#ef4444"
    if e in ["atencao", "atenção", "amarelo", "revisar"]:
        return "#f59e0b"
    return "#22c55e"


def badge(txt, bg, fg="#ffffff"):
    return f'<span class="badge" style="background:{bg};color:{fg};">{txt}</span>'


def faixa_fill_text(f):
    if pd.isna(f):
        return "—"
    f = max(0.0, min(100.0, float(f)))
    if f < 10:
        return "zerada"
    if f >= 90:
        return "90 - 100%"
    inicio = int(f // 10) * 10
    fim = min(100, inicio + 10)
    return f"{inicio} - {fim}%"


def nivel_from_fill(f):
    if pd.isna(f):
        return "indeterminado"
    f = max(0.0, min(100.0, float(f)))
    if f < 10:
        return "zerada"
    if f >= 90:
        return "muito alto"
    if f >= 80:
        return "alto"
    if f >= 60:
        return "médio"
    if f >= 40:
        return "médio-baixo"
    if f >= 20:
        return "baixo"
    return "muito baixo"

def fill_tecnico(status, fill):
    try:
        if fill is None or pd.isna(fill):
            return "—"
        return f"{float(fill):.2f}%"
    except Exception:
        return "—"

def fill_operacional(status, fill, motivo, grupo):
    status = (status or "").lower()
    motivo = (motivo or "").lower()
    grupo = (grupo or "").lower()

    if status == "ok" and not pd.isna(fill):
        return faixa_fill_text(fill)

    if motivo == "suspeito_floor_quase_zero":
        if grupo == "madeira":
            return "90 - 100%"
        if grupo in ("sucata", "plastico"):
            return "zerada"
        return "indeterminado"

    if not pd.isna(fill):
        return faixa_fill_text(fill)

    return "indeterminado"


def nivel_operacional(status, fill, motivo, grupo):
    status = (status or "").lower()
    motivo = (motivo or "").lower()
    grupo = (grupo or "").lower()

    if status == "ok" and not pd.isna(fill):
        return nivel_from_fill(fill)

    if motivo == "suspeito_floor_quase_zero":
        if grupo == "madeira":
            return "muito alto"
        if grupo in ("sucata", "plastico"):
            return "zerada"
        return "indeterminado"

    if not pd.isna(fill):
        return nivel_from_fill(fill)

    return "indeterminado"


def confianca_fill(status, fill):
    if (status or "").lower() == "ok" and not pd.isna(fill):
        return "alta"
    return "baixa"


def acao_operacional(status, estado, fill, motivo, grupo):
    status = (status or "").lower()
    motivo = (motivo or "").lower()
    grupo = (grupo or "").lower()

    if motivo == "suspeito_floor_quase_zero":
        if grupo == "madeira":
            return "revisar e programar troca"
        if grupo in ("sucata", "plastico"):
            return "revisar, tendência de vazio"
        return "revisão visual obrigatória"

    if status != "ok":
        return "revisão visual obrigatória"

    if pd.isna(fill):
        return "revisão visual"

    f = float(fill)
    if f >= 95:
        return "trocar caçamba"
    if f >= 85:
        return "programar troca"
    if f >= 60:
        return "monitorar alto enchimento"
    return "operação normal"


def texto_alerta_contaminacao(alerta, tipo):
    try:
        alerta = int(alerta)
    except Exception:
        alerta = 0

    tipo = str(tipo or "").strip()
    if alerta == 1:
        return f"CONTAMINAÇÃO DETECTADA: {tipo.upper() if tipo else 'SIM'}"
    return "sem contaminação"


def cor_alerta_contaminacao(alerta):
    try:
        alerta = int(alerta)
    except Exception:
        alerta = 0
    return "#dc2626" if alerta == 1 else "#166534"


def render_box_contaminacao(alerta, tipo, contaminantes):
    try:
        alerta_num = int(alerta)
    except Exception:
        alerta_num = 0

    tipo = str(tipo or "").strip()
    contaminantes = str(contaminantes or "").strip()

    if alerta_num == 1:
        label = tipo.upper() if tipo else "SIM"
        extra = f"<div class='small-muted' style='color:#fecaca;margin-top:4px;'>contaminantes: <b>{contaminantes or label}</b></div>"
        return f"""
        <div class="contam-box" style="background:rgba(220,38,38,0.16);border:1px solid rgba(220,38,38,0.55);color:#fecaca;">
            CONTAMINAÇÃO DETECTADA: {label}
            {extra}
        </div>
        """

    return """
    <div class="contam-box" style="background:rgba(22,101,52,0.16);border:1px solid rgba(34,197,94,0.45);color:#bbf7d0;">
        sem contaminação
    </div>
    """


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
    alerta_contam = row.get("alerta_contaminacao", 0)
    tipo_contam = row.get("tipo_contaminacao", "")
    contaminantes = row.get("contaminantes_detectados", "")

    fill_tec = fill_tecnico(status, fill)
    fill_op = fill_operacional(status, fill, motivo, grupo)
    conf = confianca_fill(status, fill)
    nivel = nivel_operacional(status, fill, motivo, grupo)
    acao = acao_operacional(status, estado, fill, motivo, grupo)
    cor = cor_estado(estado)
    contam_html = render_box_contaminacao(alerta_contam, tipo_contam, contaminantes)

    st.markdown(
        f"""
        <div class="card-custom">
            <div class="card-title">{grupo.upper()}</div>
            <div class="card-value">{fill_op}</div>
            <div class="small-muted">fill técnico: <b>{fill_tec}</b></div>
            <div class="small-muted">nível operacional: <b>{nivel}</b></div>
            <div class="small-muted">confiança: <b>{conf}</b></div>
            <div class="small-muted">estado: <span style="color:{cor};font-weight:700;">{estado or "-"}</span></div>
            <div class="small-muted">ação: <b>{acao}</b></div>
            {contam_html}
        </div>
        """,
        unsafe_allow_html=True
    )


def sanitize_filename(name: str) -> str:
    name = name.strip()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    name = re.sub(r"_+", "_", name)
    return name or "arquivo.jpg"


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

    INPUT_TESTE_DIR.mkdir(parents=True, exist_ok=True)

    stem = Path(nome_limpo).stem
    suffix = Path(nome_limpo).suffix.lower() or ".jpg"
    ts = datetime.now().strftime("%Y%m%d%H%M%S%f")

    destino = INPUT_TESTE_DIR / f"{grupo_final}_manual_{ts}_{stem}{suffix}"
    destino.write_bytes(uploaded_file.getbuffer())
    return destino, grupo_final


df = prepare_df(load_eventos())
df_exec = load_execucoes()

if "selected_event_id_v5" not in st.session_state:
    st.session_state.selected_event_id_v5 = None

with st.sidebar:
    st.header("Teste manual")
    grupo_upload = st.selectbox("Grupo do teste", ["madeira", "plastico", "sucata"], index=0)
    uploaded_file = st.file_uploader(
        "Enviar imagem para teste",
        type=["jpg", "jpeg", "png", "bmp", "webp"],
        key="upload_manual_teste"
    )

    if uploaded_file is not None:
        st.caption(f"Arquivo selecionado: {uploaded_file.name}")
        if st.button("Enviar imagem para teste", use_container_width=True):
            destino, grupo_final = salvar_upload_teste(uploaded_file, grupo_upload)
            st.success(f"Imagem enviada para fila de teste: {destino.name}")

            if grupo_final != grupo_upload:
                st.warning(f"Grupo detectado pelo nome do arquivo: {grupo_final}. O grupo selecionado foi ignorado.")
            else:
                st.info(f"Grupo efetivo do teste: {grupo_final}")

            st.info("O loop vai processar automaticamente. Com intervalo de 10s, ela deve aparecer no painel em poucos segundos.")
            st.cache_data.clear()

    st.markdown("---")
    st.header("Painel")
    auto_refresh = st.checkbox("Atualização automática", value=True)
    intervalo = st.selectbox("Intervalo", [2, 3, 5, 10, 15, 30, 60, 120], index=0)
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

if auto_refresh:
    st_autorefresh(interval=intervalo * 1000, key="auto_refresh_dashboard_v5")

top1, top2 = st.columns([0.82, 0.18])
with top1:
    st.title("Projeto Vale — Dashboard Operacional")
    st.caption("Release V8 | camada operacional V5 com upload manual")
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

if f.empty:
    st.warning("Sem dados para os filtros atuais.")
    st.stop()

f["fill_tecnico_exibicao"] = f.apply(lambda r: fill_tecnico(r["status"], r["fill_percent"]), axis=1)
f["fill_operacional_exibicao"] = f.apply(lambda r: fill_operacional(r["status"], r["fill_percent"], r["motivo_falha"], r["grupo"]), axis=1)
f["confianca_fill"] = f.apply(lambda r: confianca_fill(r["status"], r["fill_percent"]), axis=1)
f["nivel_operacional"] = f.apply(lambda r: nivel_operacional(r["status"], r["fill_percent"], r["motivo_falha"], r["grupo"]), axis=1)
f["acao_operacional"] = f.apply(lambda r: acao_operacional(r["status"], r["estado_dashboard"], r["fill_percent"], r["motivo_falha"], r["grupo"]), axis=1)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Eventos filtrados", len(f))
m2.metric("Alertas contaminação", int((f["alerta_contaminacao"] == 1).sum()))
m3.metric("Frames suspeitos", int((f["status"].str.lower() != "ok").sum()))
ok_fill = f.loc[f["status"].str.lower() == "ok", "fill_percent"].dropna()
m4.metric("Fill médio confiável", f"{ok_fill.mean():.2f}%" if not ok_fill.empty else "—")

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
        st.info("Sem imagem debug disponível.")

with c2:
    st.markdown("### Resumo operacional")

    alerta_contam_ult = ultimo.get("alerta_contaminacao", 0)
    tipo_contam_ult = ultimo.get("tipo_contaminacao", "")
    contaminantes_ult = ultimo.get("contaminantes_detectados", "")

    badges_html = (
        badge(f"status: {ultimo['status']}", "#1f2937") +
        badge(f"fill operacional: {ultimo['fill_operacional_exibicao']}", "#7c3aed") +
        badge(f"nível: {ultimo['nivel_operacional']}", "#0f766e") +
        badge(f"confiança: {ultimo['confianca_fill']}", "#92400e")
    )

    try:
        alerta_contam_num = int(alerta_contam_ult)
    except Exception:
        alerta_contam_num = 0

    if alerta_contam_num == 1:
        badges_html += badge(
            f"CONTAMINAÇÃO: {str(tipo_contam_ult).upper() if str(tipo_contam_ult).strip() else 'SIM'}",
            "#dc2626"
        )

    st.markdown(badges_html, unsafe_allow_html=True)

    campos = [
        ("arquivo", "arquivo_nome"),
        ("grupo", "grupo"),
        ("fill técnico", "fill_tecnico_exibicao"),
        ("fill operacional", "fill_operacional_exibicao"),
        ("estado", "estado_dashboard"),
        ("ação", "acao_operacional"),
        ("motivo", "motivo_falha"),
        ("materiais detectados", "materiais_detectados_raw"),
        ("contaminantes detectados", "contaminantes_detectados"),
        ("tipo de contaminação", "tipo_contaminacao"),
        ("alerta contaminação", "alerta_contaminacao"),
        ("processado em", "ts_processamento"),
    ]
    for titulo, chave in campos:
        st.write(f"**{titulo}:** {ultimo.get(chave, '—')}")

    st.markdown(
        render_box_contaminacao(alerta_contam_ult, tipo_contam_ult, contaminantes_ult),
        unsafe_allow_html=True
    )

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
            st.caption(f"fill operacional: {row['fill_operacional_exibicao']}")
            st.caption(f"técnico: {row['fill_tecnico_exibicao']} | confiança: {row['confianca_fill']}")

            try:
                alerta_thumb = int(row.get("alerta_contaminacao", 0))
            except Exception:
                alerta_thumb = 0

            if alerta_thumb == 1:
                tipo_thumb = str(row.get("tipo_contaminacao", "")).strip().upper() or "SIM"
                st.markdown(
                    f"<div style='color:#fecaca;font-weight:800;font-size:12px;'>CONTAMINAÇÃO: {tipo_thumb}</div>",
                    unsafe_allow_html=True
                )

            if st.button("Ver detalhe", key=f"v5_det_{int(row['id'])}", use_container_width=True):
                st.session_state.selected_event_id_v5 = int(row["id"])

            st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

st.subheader("Detalhe visual selecionado")

if st.session_state.selected_event_id_v5 is None:
    st.session_state.selected_event_id_v5 = int(ultimo["id"])

row_sel_df = f[f["id"] == st.session_state.selected_event_id_v5]
row_sel = row_sel_df.iloc[0] if not row_sel_df.empty else ultimo

d1, d2 = st.columns([1.0, 1.1])
with d1:
    st.markdown("### Metadados e decisão")

    alerta_sel = row_sel.get("alerta_contaminacao", 0)
    tipo_sel = row_sel.get("tipo_contaminacao", "")
    contaminantes_sel = row_sel.get("contaminantes_detectados", "")

    badges_html = (
        badge(f"status: {row_sel['status']}", "#1f2937") +
        badge(f"fill operacional: {row_sel['fill_operacional_exibicao']}", "#7c3aed") +
        badge(f"nível: {row_sel['nivel_operacional']}", "#0f766e") +
        badge(f"confiança: {row_sel['confianca_fill']}", "#92400e")
    )

    try:
        alerta_sel_num = int(alerta_sel)
    except Exception:
        alerta_sel_num = 0

    if alerta_sel_num == 1:
        badges_html += badge(
            f"CONTAMINAÇÃO: {str(tipo_sel).upper() if str(tipo_sel).strip() else 'SIM'}",
            "#dc2626"
        )

    st.markdown(badges_html, unsafe_allow_html=True)

    meta_cols = [
        "arquivo_nome",
        "grupo",
        "fill_tecnico_exibicao",
        "fill_operacional_exibicao",
        "estado_dashboard",
        "acao_operacional",
        "motivo_falha",
        "materiais_detectados_raw",
        "contaminantes_detectados",
        "tipo_contaminacao",
        "alerta_contaminacao",
        "ts_processamento",
    ]
    for c in meta_cols:
        st.write(f"**{c}:** {row_sel.get(c, '—')}")

    st.markdown(
        render_box_contaminacao(alerta_sel, tipo_sel, contaminantes_sel),
        unsafe_allow_html=True
    )

with d2:
    debug_path = row_sel.get("debug_path", None)
    if debug_path and Path(str(debug_path)).exists():
        st.markdown("### Imagem debug")
        st.image(str(debug_path), use_container_width=True)
    else:
        st.info("Sem imagem debug disponível.")

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
    "fill_tecnico_exibicao", "fill_operacional_exibicao",
    "nivel_operacional", "confianca_fill", "acao_operacional",
    "estado_dashboard", "motivo_falha",
    "materiais_detectados_raw", "contaminantes_detectados",
    "tipo_contaminacao", "alerta_contaminacao"
]
st.dataframe(f[cols_exibir], use_container_width=True, height=320, hide_index=True)

st.markdown("---")

st.subheader("Execuções recentes do serviço")
if not df_exec.empty:
    st.dataframe(df_exec, use_container_width=True, height=220, hide_index=True)
else:
    st.info("Nenhuma execução registrada ainda.")
