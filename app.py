import os
import json
import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from PIL import Image
import scraper

# Configurações de layout da página Streamlit
st.set_page_config(
    page_title="GeoVagas - Oportunidades Georreferenciadas",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS completa em Neumorphism / Glassmorphism (Soft UI)
st.markdown("""
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        background-color: #e6ecf5;
        color: #2d3748;
    }

    /* Fundo da aplicação principal */
    .stApp {
        background: linear-gradient(135deg, #e4ebf5 0%, #edf2f7 100%);
    }

    /* Barra Lateral - Estilo Neumórfico Suave */
    [data-testid="stSidebar"] {
        background: #e6ecf5 !important;
        box-shadow: 8px 0px 20px rgba(163, 177, 198, 0.45);
        border-right: 1px solid rgba(255, 255, 255, 0.6);
    }
    
    [data-testid="stSidebar"] > div:first-child {
        background: transparent;
        padding-top: 1rem;
    }

    /* Rótulos e Títulos dos Filtros com Alto Contraste */
    [data-testid="stSidebar"] label {
        color: #1a202c !important;
        font-weight: 700 !important;
        font-size: 0.92rem !important;
        letter-spacing: 0.2px;
        margin-top: 6px;
    }

    [data-testid="stSidebar"] .stMarkdown h3 {
        color: #1e3a8a !important;
        font-weight: 800 !important;
        font-size: 1.25rem !important;
        border-bottom: 2px solid #cbd5e1;
        padding-bottom: 8px;
        margin-bottom: 16px;
    }

    /* Caixas de seleção e inputs neumórficos */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div {
        background: #e6ecf5 !important;
        border-radius: 12px !important;
        border: 1px solid rgba(255, 255, 255, 0.9) !important;
        box-shadow: inset 3px 3px 6px #bcc8d6, inset -3px -3px 6px #ffffff !important;
        color: #1a202c !important;
    }

    /* Botão Neumórfico */
    .stButton > button {
        background: #e6ecf5 !important;
        color: #1d4ed8 !important;
        font-weight: 700 !important;
        border-radius: 14px !important;
        border: 1px solid rgba(255, 255, 255, 0.8) !important;
        box-shadow: 5px 5px 10px #c2cddb, -5px -5px 10px #ffffff !important;
        transition: all 0.2s ease-in-out !important;
        padding: 0.55rem 1rem !important;
    }
    .stButton > button:hover {
        box-shadow: 2px 2px 5px #c2cddb, -2px -2px 5px #ffffff !important;
        transform: translateY(1px);
        color: #1e40af !important;
    }
    .stButton > button:active {
        box-shadow: inset 3px 3px 6px #bcc8d6, inset -3px -3px 6px #ffffff !important;
    }

    /* Cartões Neumórficos (Morphism Containers) */
    .morph-card {
        background: #e6ecf5;
        border-radius: 20px;
        box-shadow: 8px 8px 16px #c4d0de, -8px -8px 16px #ffffff;
        padding: 22px 26px;
        margin-bottom: 22px;
        border: 1px solid rgba(255, 255, 255, 0.7);
    }

    .morph-card-compact {
        background: #e6ecf5;
        border-radius: 16px;
        box-shadow: 6px 6px 12px #c4d0de, -6px -6px 12px #ffffff;
        padding: 14px 18px;
        border: 1px solid rgba(255, 255, 255, 0.7);
    }

    /* Header styling */
    .hero-title {
        font-size: 2.1rem;
        font-weight: 800;
        color: #1e3a8a;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .hero-subtitle {
        color: #4b5563;
        font-size: 1rem;
        margin-top: 4px;
        margin-bottom: 0;
    }

    /* Badge de contagem */
    .stat-pill {
        display: inline-flex;
        align-items: center;
        background: #e6ecf5;
        padding: 8px 18px;
        border-radius: 30px;
        box-shadow: inset 2px 2px 4px #c2cddb, inset -2px -2px 4px #ffffff;
        font-weight: 700;
        color: #2563eb;
        font-size: 0.95rem;
    }

    /* Container do Mapa */
    .map-container {
        border-radius: 18px;
        overflow: hidden;
        box-shadow: inset 4px 4px 8px #bcc8d6, inset -4px -4px 8px #ffffff;
        padding: 6px;
        background: #e6ecf5;
    }

    /* Seção da Tabela com destaque */
    .section-title {
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 1.25rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "logo", "logo_geovagas.png")

# Sidebar com Estilo e Filtros de Alto Contraste
with st.sidebar:
    if os.path.exists(LOGO_PATH):
        try:
            logo_img = Image.open(LOGO_PATH)
            st.image(logo_img, use_container_width=True)
        except Exception:
            st.markdown("## 📍 GeoVagas")
    else:
        st.markdown("## 📍 GeoVagas")
        
    st.markdown("### 🔍 Filtros de Vagas")
    
    # Botão de atualização
    if st.button("🔄 Atualizar Vagas da PBH", use_container_width=True):
        with st.spinner("Raspando vagas atualizadas e geolocalizando..."):
            scraper.scrape_vagas()
            st.success("Dados sincronizados com sucesso!")
            st.rerun()

    # Carregar dados
    vagas_todas = scraper.get_vagas_cached()
    
    if not vagas_todas:
        st.warning("Nenhuma vaga carregada. Clique no botão acima para sincronizar.")
        st.stop()

    df_todas = pd.DataFrame(vagas_todas)
    
    # 1. Filtro de Contratação
    tipos_contratacao = sorted([c for c in df_todas['contratacao'].dropna().unique() if str(c).strip()])
    filtro_contratacao = st.multiselect(
        "Tipo de Contratação:",
        options=tipos_contratacao,
        default=[],
        help="Selecione um ou mais tipos de contratação (ex: Estágio, CLT)."
    )

    # 2. Filtro de Escolaridade
    escolaridades = sorted([e for e in df_todas['escolaridade'].dropna().unique() if str(e).strip()])
    filtro_escolaridade = st.multiselect(
        "Escolaridade:",
        options=escolaridades,
        default=[],
        help="Selecione o nível de escolaridade exigido."
    )

    # 3. Filtro de Horário
    horarios = sorted([h for h in df_todas['horario'].dropna().unique() if str(h).strip()])
    filtro_horario = st.multiselect(
        "Horário de Trabalho:",
        options=horarios,
        default=[],
        help="Turno de trabalho (Manhã, Tarde, Indiferente, etc.)."
    )

    # 4. Filtro de Carga Horária
    cargas = sorted([c for c in df_todas['carga_horaria'].dropna().unique() if str(c).strip()])
    filtro_carga = st.multiselect(
        "Carga Horária:",
        options=cargas,
        default=[],
        help="Carga horária semanal."
    )
    
    # Busca textual livre
    filtro_busca = st.text_input(
        "Palavra-chave (Cargo, Local, Requisito):",
        placeholder="Ex: Informática, Afonso Pena..."
    )
    
    st.markdown("---")
    st.caption("📍 **GeoVagas** • Fonte oficial: Prefeitura de Belo Horizonte (GO BH)")

# Aplicação dos Filtros
df_filtrado = df_todas.copy()

if filtro_contratacao:
    df_filtrado = df_filtrado[df_filtrado['contratacao'].isin(filtro_contratacao)]

if filtro_escolaridade:
    df_filtrado = df_filtrado[df_filtrado['escolaridade'].isin(filtro_escolaridade)]

if filtro_horario:
    df_filtrado = df_filtrado[df_filtrado['horario'].isin(filtro_horario)]

if filtro_carga:
    df_filtrado = df_filtrado[df_filtrado['carga_horaria'].isin(filtro_carga)]

if filtro_busca:
    termo = filtro_busca.lower().strip()
    df_filtrado = df_filtrado[
        df_filtrado['titulo'].str.lower().str.contains(termo, na=False) |
        df_filtrado['local_trabalho'].str.lower().str.contains(termo, na=False) |
        df_filtrado['descricao_detalhada'].str.lower().str.contains(termo, na=False) |
        df_filtrado['empresa'].str.lower().str.contains(termo, na=False)
    ]

# Cabeçalho Principal no estilo Morphism
st.markdown(f"""
<div class="morph-card" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px;">
    <div>
        <h1 class="hero-title">Oportunidades em Belo Horizonte</h1>
        <p class="hero-subtitle">Visualização geoespacial interativa de vagas e estágios do GO BH</p>
    </div>
    <div class="stat-pill">
        📍 {len(df_filtrado)} de {len(df_todas)} vagas filtradas
    </div>
</div>
""", unsafe_allow_html=True)

# Layout em Duas Colunas ou Bloco Principal
# Mapa em destaque com altura equilibrada
col_map, col_info = st.columns([3, 1])

with col_info:
    st.markdown("""
    <div class="morph-card-compact" style="height: 100%; display: flex; flex-direction: column; justify-content: space-between;">
        <div>
            <div style="font-weight: 700; color: #1e3a8a; font-size: 1.05rem; margin-bottom: 8px;">
                💡 Navegação no Mapa
            </div>
            <p style="font-size: 0.88rem; color: #475569; line-height: 1.45; margin-bottom: 10px;">
                • Clique nos <b>círculos numéricos (clusters)</b> para aproximar na região.<br>
                • Clique em um <b>marcador de vaga</b> para ver dados detalhados e o link de candidatura.<br>
                • As vagas também estão detalhadas na tabela logo abaixo.
            </p>
        </div>
        <div style="border-top: 1px solid #cbd5e1; padding-top: 10px; font-size: 0.82rem; color: #64748b;">
            Base de mapas 100% livre: <b>OpenStreetMap</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_map:
    # Ponto central do mapa (Belo Horizonte)
    map_center = [-19.9208, -43.9378]
    zoom_start = 12

    if not df_filtrado.empty:
        valid_coords = df_filtrado.dropna(subset=['lat', 'lon'])
        if not valid_coords.empty:
            map_center = [valid_coords['lat'].mean(), valid_coords['lon'].mean()]

    # Mapa Folium usando OpenStreetMap padrão (sem necessidade de chaves/tokens)
    m = folium.Map(
        location=map_center,
        zoom_start=zoom_start,
        tiles="OpenStreetMap"
    )

    marker_cluster = MarkerCluster().add_to(m)

    for _, row in df_filtrado.iterrows():
        lat = row.get('lat')
        lon = row.get('lon')
        if pd.isna(lat) or pd.isna(lon):
            continue
        
        # Popup neumórfico estilizado
        popup_html = f"""
        <div style="font-family: 'Plus Jakarta Sans', Arial, sans-serif; font-size: 13px; line-height: 1.45; width: 280px; padding: 4px;">
            <h4 style="color: #1e3a8a; margin: 0 0 6px 0; font-size: 14px; font-weight: 700;">{row['titulo']}</h4>
            <p style="margin: 0 0 4px 0; color: #334155;"><b>🏢 Empregador:</b> {row['empresa']}</p>
            <p style="margin: 0 0 4px 0; color: #334155;"><b>📍 Local:</b> {row['local_trabalho']}</p>
            <p style="margin: 0 0 4px 0; color: #334155;"><b>📋 Contratação:</b> {row['contratacao']}</p>
            <p style="margin: 0 0 4px 0; color: #334155;"><b>🎓 Escolaridade:</b> {row['escolaridade']}</p>
            <p style="margin: 0 0 4px 0; color: #334155;"><b>⏰ Horário:</b> {row['horario']} ({row['carga_horaria']})</p>
            <p style="margin: 0 0 10px 0; color: #16a34a; font-weight: 700; font-size: 14px;"><b>💰 Salário:</b> {row['salario']}</p>
            <a href="{row['link_gobh']}" target="_blank" style="display: block; background: #2563eb; color: #ffffff; padding: 8px 12px; text-decoration: none; border-radius: 8px; font-weight: 600; text-align: center; box-shadow: 0 3px 6px rgba(37,99,235,0.3);">
                Acessar Vaga no GO BH ↗
            </a>
        </div>
        """
        
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=320),
            tooltip=f"{row['titulo']} - {row['empresa']}",
            icon=folium.Icon(color="blue", icon="briefcase", prefix="fa")
        ).add_to(marker_cluster)

    # Renderiza o mapa com altura confortável (400px) para manter a tabela logo visível na tela
    map_data = st_folium(m, width="100%", height=400, returned_objects=["last_object_clicked"])

# Área da Tabela de Vagas em Card Neumórfico de Alto Destaque
st.markdown("""
<div class="morph-card" style="margin-top: 10px;">
    <div class="section-title">
        <span>📋</span> Tabela Completa de Vagas e Detalhes
    </div>
    <p style="color: #64748b; font-size: 0.9rem; margin-top: -6px; margin-bottom: 14px;">
        Os registros abaixo refletem os filtros selecionados. Clique nos títulos das colunas para ordenar.
    </p>
""", unsafe_allow_html=True)

if df_filtrado.empty:
    st.info("Nenhuma vaga encontrada para os filtros selecionados.")
else:
    # Preparar DataFrame para exibição amigável
    display_cols = [
        'titulo', 'empresa', 'local_trabalho', 'contratacao', 
        'escolaridade', 'horario', 'carga_horaria', 'salario', 'link_gobh'
    ]
    df_display = df_filtrado[display_cols].copy()
    df_display.columns = [
        'Cargo / Vaga', 'Empregador', 'Local de Trabalho', 'Contratação',
        'Escolaridade', 'Horário', 'Carga Horária', 'Salário', 'Link Oficial'
    ]

    # Exibição da tabela com altura controlada e scroll interno
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        height=320,
        column_config={
            "Link Oficial": st.column_config.LinkColumn(
                "Link no GO BH",
                display_text="Acessar Vaga ↗"
            )
        }
    )

st.markdown("</div>", unsafe_allow_html=True)
