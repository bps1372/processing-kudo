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
import time

# ==========================================
# KONFIGURASI & STYLING HALAMAN
# ==========================================
st.set_page_config(page_title="KUDO - BPS Kota Solok", page_icon="🟠", layout="wide")

custom_css = """
<style>
    /* Gradient Background ORANYE (Bukan Merah) */
    .stApp {
        background: linear-gradient(135deg, #FF7A00 0%, #FFB347 100%);
    }
    
    /* SIDEBAR CUSTOM - Tidak Putih */
    [data-testid="stSidebar"] {
        background-color: rgba(30, 30, 30, 0.9) !important; /* Gelap Transparan */
        border-right: 2px solid #FF7A00;
    }
    
    /* Teks Sidebar menjadi Putih agar terbaca */
    [data-testid="stSidebar"] .stText, [data-testid="stSidebar"] label, [data-testid="stSidebar"] p {
        color: white !important;
    }
    
    /* Judul Utama */
    .kudo-header {
        text-align: center;
        color: white !important;
        margin-top: 30px;
        margin-bottom: 5px;
        font-weight: 800;
        font-size: 4rem !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    .kudo-subtitle {
        text-align: center;
        color: white;
        font-size: 1.2rem;
        margin-bottom: 25px;
        font-weight: 500;
    }

    /* Banner Tengah */
    .pro-banner {
        background: rgba(255, 255, 255, 0.2);
        backdrop-filter: blur(10px);
        padding: 40px; border-radius: 20px; color: white; text-align: center;
        margin-bottom: 30px; border: 1px solid rgba(255,255,255,0.3);
    }
    .pro-banner h1 { color: white !important; margin: 0; font-size: 3.5rem; font-weight: 800; }
    
    /* Styling Button */
    div.stButton > button {
        background-color: #FF7A00; color: white; border-radius: 10px; font-weight: 600;
        border: 1px solid white; transition: 0.3s;
    }
    div.stButton > button:hover {
        background-color: white; color: #FF7A00; border: 1px solid #FF7A00;
    }

    /* Container Menu Utama */
    .menu-container {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 20px;
        max-width: 1000px;
        margin: 20px auto;
        padding: 30px;
        background: rgba(255, 255, 255, 0.15);
        border-radius: 20px;
        backdrop-filter: blur(5px);
    }
    
    .menu-item-desc {
        text-align: center;
        color: white;
        font-size: 0.85rem;
        margin-top: -10px;
        margin-bottom: 10px;
    }
    
    /* Custom Info Box */
    .stInfo {
        background-color: rgba(255, 255, 255, 0.2) !important;
        color: white !important;
        border: none !important;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ==========================================
# SESSION STATE LOGIC
# ==========================================
if 'app_mode' not in st.session_state:
    st.session_state['app_mode'] = 'landing'
if 'selected_region' not in st.session_state:
    st.session_state['selected_region'] = "Kota Solok"
if 'active_menu' not in st.session_state:
    st.session_state['active_menu'] = None

# ==========================================
# CORE FUNCTIONS (TETAP SAMA)
# ==========================================
@st.cache_data
def load_data(file):
    file_name = file.name.lower()
    try:
        if file_name.endswith('.csv'): return pd.read_csv(file)
        elif file_name.endswith('.xlsx') or file_name.endswith('.xls'): return pd.read_excel(file)
        elif file_name.endswith('.json'): return pd.read_json(file)
    except Exception as e:
        st.error(f"Gagal membaca file: {e}")
    return None

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

def to_shp_zip(df, lat_col, lon_col):
    geometry = [Point(xy) for xy in zip(df[lon_col], df[lat_col])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
    temp_dir = tempfile.mkdtemp()
    base_filename = "peta_lokasi"
    shp_path = os.path.join(temp_dir, f"{base_filename}.shp")
    gdf.to_file(shp_path, driver='ESRI Shapefile')
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg']:
            file_path = os.path.join(temp_dir, f"{base_filename}{ext}")
            if os.path.exists(file_path): zip_file.write(file_path, f"{base_filename}{ext}")
    return zip_buffer.getvalue()

# ==========================================
# EXTRACTION FUNCTIONS
# ==========================================
def extract_phone_number(text):
    if pd.isna(text): return None
    phone_patterns = r'\+62[\s-]?\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}|\b62[\s-]?\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}|\b08\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}|\b07\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}'
    matches = re.findall(phone_patterns, str(text))
    return ', '.join([m.strip() for m in matches]) if matches else None

def extract_address_ig(text, default_region):
    if pd.isna(text): return default_region
    bio_str = str(text)
    address_pattern = r'(?i)\b(jl|jalan|jln)\b[.\s]*[^\n]+'
    match = re.search(address_pattern, bio_str)
    if match: return match.group(0).strip(' ,.-')
    return default_region

def extract_address_gmaps(text):
    if pd.isna(text): return None
    bio_str = str(text)
    address_pattern = r'(?i)\b(jl|jalan|jln|raya|dusun|desa|komplek|gedung|rt|rw|blok)\b.*?(?:\d{5}|indonesia|$)'
    match = re.search(address_pattern, bio_str)
    if match: return match.group(0).strip(' ,.-')
    return bio_str.strip(' ,.-')

# ==========================================
# APP VIEWS
# ==========================================
region_list = ("Kota Solok", "Kota Padang", "Kota Bukittinggi", "Kota Sawahlunto", "Kota Pariaman", "Kota Payakumbuh", "Kota Padang Panjang", "Kabupaten Agam", "Kabupaten Dharmasraya","Kabupaten Kepulauan Mentawai", "Kabupaten Lima Puluh Kota","Kabupaten Padang Pariaman", "Kabupaten Pasaman", "Kabupaten Pasaman Barat", "Kabupaten Pesisir Selatan", "Kabupaten Sijunjung", "Kabupaten Solok", "Kabupaten Solok Selatan", "Kabupaten Tanah Datar")

if st.session_state['app_mode'] == 'landing':
    st.markdown('<h1 class="kudo-header">KUDO</h1>', unsafe_allow_html=True)
    st.markdown('<p class="kudo-subtitle">KOREK USAHA DIGITAL ONLINE - BPS KOTA SOLOK</p>', unsafe_allow_html=True)
    
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        st.markdown('<div style="color:white; margin-bottom:10px;">Pilih Wilayah Anda:</div>', unsafe_allow_html=True)
        choice = st.selectbox("Wilayah", region_list, label_visibility="collapsed")
        if st.button("Masuk"):
            st.session_state['selected_region'] = choice
            st.session_state['app_mode'] = 'main'
            st.rerun()

elif st.session_state['app_mode'] == 'main':
    st.markdown('<h1 class="kudo-header">KUDO</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="kudo-subtitle">KOREK USAHA DIGITAL ONLINE - Wilayah: {st.session_state["selected_region"]}</p>', unsafe_allow_html=True)
    
    st.markdown('<div class="menu-container">', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<h2 style="text-align:center;">🖨️</h2>', unsafe_allow_html=True)
        if st.button('1. Filter Kolom'):
            st.session_state['active_menu'], st.session_state['app_mode'] = "1. Filter Kolom", 'feature_active'
            st.rerun()
        st.markdown('<p class="menu-item-desc">Filter kolom data</p>', unsafe_allow_html=True)

    with col2:
        st.markdown('<h2 style="text-align:center;">🖥️</h2>', unsafe_allow_html=True)
        if st.button('2. Duplikasi'):
            st.session_state['active_menu'], st.session_state['app_mode'] = "2. Duplikasi Data", 'feature_active'
            st.rerun()
        st.markdown('<p class="menu-item-desc">Hapus data ganda</p>', unsafe_allow_html=True)

    with col3:
        st.markdown('<h2 style="text-align:center;">🎧</h2>', unsafe_allow_html=True)
        if st.button('3. Merge Data'):
            st.session_state['active_menu'], st.session_state['app_mode'] = "3. Merge Data", 'feature_active'
            st.rerun()
        st.markdown('<p class="menu-item-desc">Gabung banyak file</p>', unsafe_allow_html=True)

    with col4:
        st.markdown('<h2 style="text-align:center;">📸</h2>', unsafe_allow_html=True)
        if st.button('4. Instagram'):
            st.session_state['active_menu'], st.session_state['app_mode'] = "4. Ekstrak No Telp & Alamat (Instagram)", 'feature_active'
            st.rerun()
        st.markdown('<p class="menu-item-desc">Ekstrak Bio IG</p>', unsafe_allow_html=True)

    st.markdown('<div style="width:100%; height:20px;"></div>', unsafe_allow_html=True)

    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.markdown('<h2 style="text-align:center;">⚙️</h2>', unsafe_allow_html=True)
        if st.button('5. GMaps'):
            st.session_state['active_menu'], st.session_state['app_mode'] = "5. Ekstrak Alamat (Google Maps)", 'feature_active'
            st.rerun()
        st.markdown('<p class="menu-item-desc">Ekstrak Alamat Maps</p>', unsafe_allow_html=True)

    with col6:
        st.markdown('<h2 style="text-align:center;">🖱️</h2>', unsafe_allow_html=True)
        if st.button('6. Peta & SHP'):
            st.session_state['active_menu'], st.session_state['app_mode'] = "6. Visualisasi Peta & Convert excel to shp", 'feature_active'
            st.rerun()
        st.markdown('<p class="menu-item-desc">Visualisasi & SHP</p>', unsafe_allow_html=True)

    with col7:
        st.markdown('<h2 style="text-align:center;">⬇️</h2>', unsafe_allow_html=True)
        if st.button('7. Cek Tipe'):
            st.session_state['active_menu'], st.session_state['app_mode'] = "7. Cek Info & Tipe Data", 'feature_active'
            st.rerun()
        st.markdown('<p class="menu-item-desc">Cek struktur data</p>', unsafe_allow_html=True)

    with col8:
        st.markdown('<h2 style="text-align:center;">📝</h2>', unsafe_allow_html=True)
        if st.button('8. Edit Data'):
            st.session_state['active_menu'], st.session_state['app_mode'] = "8. Edit/Hapus Data", 'feature_active'
            st.rerun()
        st.markdown('<p class="menu-item-desc">Workspace Edit</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state['app_mode'] == 'feature_active':
    st.markdown(f'<div class="pro-banner"><h1>KUDO Data Processing</h1><p>Wilayah: {st.session_state["selected_region"]}</p></div>', unsafe_allow_html=True)

    # SIDEBAR - GELAP
    st.sidebar.markdown("<h2 style='color:white;'>🟠 Menu KUDO</h2>", unsafe_allow_html=True)
    st.sidebar.markdown(f"<div style='background-color:#FF7A00; padding:10px; border-radius:10px; color:white;'>📍 Wilayah: {st.session_state['selected_region']}</div>", unsafe_allow_html=True)
    
    menu = st.sidebar.radio("Pilih Fitur:", ("1. Filter Kolom", "2. Duplikasi Data", "3. Merge Data", "4. Ekstrak No Telp & Alamat (Instagram)", "5. Ekstrak Alamat (Google Maps)", "6. Visualisasi Peta & Convert excel to shp", "7. Cek Info & Tipe Data", "8. Edit/Hapus Data"), index=0)
    
    if st.sidebar.button("🔙 Kembali ke Dashboard"):
        st.session_state['app_mode'] = 'main'
        st.rerun()
    if st.sidebar.button("🔄 Ganti Wilayah"):
        st.session_state['app_mode'] = 'landing'
        st.rerun()

    # LOGIKA FITUR 1-8 (Gunakan kode asli Anda di sini)
    if menu == "6. Visualisasi Peta & Convert excel to shp":
        st.header("6. Visualisasi Peta & Export Shapefile")
        uploaded_file = st.file_uploader("Upload file data spasial", type=['csv', 'xlsx', 'json'])
        if uploaded_file:
            df = load_data(uploaded_file)
            if df is not None:
                st.dataframe(df.head())
                # ... Lanjutkan logika peta sesuai kode asli Anda ...
