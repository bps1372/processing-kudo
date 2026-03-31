import streamlit as st
import pandas as pd
import re
import io 
import geopandas as gpd
from shapely.geometry import Point
import tempfile
import zipfile
import os
import folium
from streamlit_folium import st_folium

# ==========================================
# ADVANCED UI CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="KUDO Engine", 
    page_icon="🟠", 
    layout="wide",
    initial_sidebar_state="expanded"
)

def inject_modern_css():
    st.markdown("""
        <style>
        /* Import Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

        /* Global Styling */
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* Menghilangkan Menu Bawaan Streamlit */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        /* Styling Background & Container */
        .stApp {
            background-color: #F8FAFC;
        }

        /* Sidebar Styling yang Lebih Elegan */
        [data-testid="stSidebar"] {
            background-color: #FFFFFF;
            border-right: 1px solid #E2E8F0;
            padding-top: 2rem;
        }
        [data-testid="stSidebarNav"] {display: none;} /* Sembunyikan navigasi default */

        /* Header Card */
        .main-card {
            background: #FFFFFF;
            padding: 2.5rem;
            border-radius: 16px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
            margin-bottom: 2rem;
            border: 1px solid #F1F5F9;
        }

        .hero-text {
            color: #1E293B;
            font-weight: 800;
            font-size: 2.2rem;
            margin-bottom: 0.5rem;
            letter-spacing: -0.025em;
        }

        .sub-text {
            color: #64748B;
            font-size: 1.1rem;
            margin-bottom: 2rem;
        }

        /* Tombol Custom */
        div.stButton > button {
            background: #FF7A00;
            color: white;
            border: none;
            padding: 0.6rem 1.2rem;
            border-radius: 10px;
            font-weight: 600;
            width: 100%;
            transition: all 0.2s;
        }
        div.stButton > button:hover {
            background: #E66E00;
            box-shadow: 0 10px 15px -3px rgba(255, 122, 0, 0.3);
            transform: translateY(-1px);
        }

        /* File Uploader Customization */
        [data-testid="stFileUploadDropzone"] {
            border: 2px dashed #CBD5E1;
            border-radius: 12px;
            background: #F8FAFC;
        }

        /* Metrics Styling */
        [data-testid="stMetricValue"] {
            color: #FF7A00;
            font-weight: 800;
        }

        /* Tag Menu Sidebar */
        .menu-label {
            padding: 10px 15px;
            border-radius: 8px;
            margin-bottom: 5px;
            font-weight: 600;
            color: #475569;
            cursor: pointer;
        }
        </style>
    """, unsafe_allow_html=True)

inject_modern_css()

# ==========================================
# UTILS & LOGIC (Tetap Sama)
# ==========================================

@st.cache_data
def load_data(file):
    file_name = file.name.lower()
    try:
        if file_name.endswith('.csv'): return pd.read_csv(file)
        elif file_name.endswith(('.xlsx', '.xls')): return pd.read_excel(file)
        elif file_name.endswith('.json'): return pd.read_json(file)
    except Exception as e:
        st.error(f"Error: {e}")
    return None

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

def extract_phone_number(text):
    if pd.isna(text): return None
    p = r'\+62[\s-]?\d{2,12}|\b62[\s-]?\d{2,12}|\b08\d{2,12}|\b07\d{2,12}'
    m = re.findall(p, str(text))
    return ', '.join([x.strip() for x in m]) if m else None

# ... (Fungsi ekstraksi alamat lainnya tetap sama)

# ==========================================
# SIDEBAR CUSTOM NAVIGATION
# ==========================================
with st.sidebar:
    st.markdown("<div style='text-align: center; margin-bottom: 2rem;'><h2 style='color: #FF7A00; font-weight: 800;'>KUDO.</h2></div>", unsafe_allow_html=True)
    
    menu = st.radio(
        "MAIN OPERATIONS",
        ["Dashboard", "Cleanup & Filter", "Instagram Extractor", "Geo-Spatial Tool", "Advanced Workspace"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.caption("BPS Kota Solok • v2.0")

# ==========================================
# MAIN CONTENT AREA
# ==========================================

# Hero Section
st.markdown(f"""
    <div class="main-card">
        <div class="hero-text">Data Processing Engine</div>
        <div class="sub-text">Sistem otomasi pembersihan dan ekstraksi data scraping.</div>
    </div>
""", unsafe_allow_html=True)

if menu == "Dashboard":
    col1, col2, col3 = st.columns(3)
    col1.metric("Status", "Operational", "Ready")
    col2.metric("Engine", "V2-Turbo")
    col3.metric("Year", "2026")
    
    st.markdown("### 📥 Mulai Unggah Data")
    uploaded_file = st.file_uploader("", type=['csv', 'xlsx', 'json'])
    
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None:
            st.success(f"File '{uploaded_file.name}' berhasil dimuat.")
            st.dataframe(df.head(10), use_container_width=True)

elif menu == "Cleanup & Filter":
    st.markdown("### 🛠️ Data Cleanup Center")
    uploaded_file = st.file_uploader("Upload file untuk dibersihkan", type=['csv', 'xlsx', 'json'])
    
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None:
            tab1, tab2 = st.tabs(["Filter Kolom", "Hapus Duplikat"])
            
            with tab1:
                selected = st.multiselect("Kolom yang ingin dipertahankan:", df.columns.tolist(), default=df.columns.tolist())
                if st.button("Proses Filter"):
                    df_res = df[selected]
                    st.download_button("Download Result", to_excel(df_res), "filtered_data.xlsx")
            
            with tab2:
                st.info(f"Ditemukan {df.duplicated().sum()} baris duplikat.")
                if st.button("Hapus Semua Duplikat"):
                    df_clean = df.drop_duplicates()
                    st.success("Selesai!")
                    st.download_button("Download Clean Data", to_excel(df_clean), "clean_data.xlsx")

elif menu == "Instagram Extractor":
    st.markdown("### 📸 Instagram Bio Extractor")
    uploaded_file = st.file_uploader("Upload file scraping IG", type=['csv', 'xlsx', 'json'])
    
    if uploaded_file:
        df = load_data(uploaded_file)
        col = st.selectbox("Pilih kolom biografi:", df.columns)
        if st.button("Ekstrak Kontak & Alamat"):
            with st.spinner("Processing..."):
                df['phone'] = df[col].apply(extract_phone_number)
                st.dataframe(df[[col, 'phone']].head())
                st.download_button("Export Results", to_excel(df), "ig_extracted.xlsx")

elif menu == "Geo-Spatial Tool":
    st.markdown("### 📍 Mapping & SHP Converter")
    uploaded_file = st.file_uploader("Upload data koordinat", type=['csv', 'xlsx', 'json'])
    
    if uploaded_file:
        df = load_data(uploaded_file)
        c1, c2 = st.columns(2)
        lat = c1.selectbox("Latitude", df.columns)
        lon = c2.selectbox("Longitude", df.columns)
        
        if st.button("Render Map"):
            # Logic map sederhana
            m = folium.Map(location=[df[lat].mean(), df[lon].mean()], zoom_start=12)
            st_folium(m, width="100%", height=500)

elif menu == "Advanced Workspace":
    st.markdown("### 🏗️ Advanced Editor")
    uploaded_file = st.file_uploader("Upload ke Workspace", type=['csv', 'xlsx', 'json'])
    
    if uploaded_file:
        df = load_data(uploaded_file)
        if 'df_work' not in st.session_state:
            st.session_state.df_work = df
            
        edited_df = st.data_editor(st.session_state.df_work, use_container_width=True, num_rows="dynamic")
        
        if st.button("Simpan Perubahan"):
            st.session_state.df_work = edited_df
            st.toast("Data tersimpan di session!")
