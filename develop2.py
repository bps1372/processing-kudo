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
    /* Gradient Background ORANYE */
    .stApp {
        background: linear-gradient(135deg, #FF7A00 0%, #FFB347 100%);
    }
    
    /* SIDEBAR CUSTOM - Gelap */
    [data-testid="stSidebar"] {
        background-color: rgba(30, 30, 30, 0.9) !important;
        border-right: 2px solid #FF7A00;
    }
    
    /* Teks Sidebar menjadi Putih */
    [data-testid="stSidebar"] .stText, [data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] h2 {
        color: white !important;
    }
    
    /* Judul Utama KUDO */
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

    /* Banner Tengah Fitur */
    .pro-banner {
        background: rgba(255, 255, 255, 0.2);
        backdrop-filter: blur(10px);
        padding: 40px; border-radius: 20px; color: white; text-align: center;
        margin-bottom: 30px; border: 1px solid rgba(255,255,255,0.3);
    }
    .pro-banner h1 { color: white !important; margin: 0; font-size: 3rem; font-weight: 800; }
    
    /* Styling Button Dashboard & Sidebar */
    div.stButton > button {
        background-color: #FF7A00; color: white; border-radius: 10px; font-weight: 600;
        border: 1px solid white; transition: 0.3s; width: 100%;
    }
    div.stButton > button:hover {
        background-color: white; color: #FF7A00; border: 1px solid #FF7A00;
    }

    /* Container Menu Dashboard */
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
        margin-top: -5px;
        margin-bottom: 15px;
    }

    /* Header Tabel & Dataframe */
    .stDataFrame { background-color: white; border-radius: 10px; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ==========================================
# SESSION STATE (LOGIKA NAVIGASI)
# ==========================================
if 'app_mode' not in st.session_state:
    st.session_state['app_mode'] = 'landing'
if 'selected_region' not in st.session_state:
    st.session_state['selected_region'] = "Kota Solok"
if 'active_menu' not in st.session_state:
    st.session_state['active_menu'] = "1. Filter Kolom"

# ==========================================
# FUNGSI PENGOLAHAN DATA (CORE)
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
# FUNGSI EKSTRAKSI (REGEX)
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
# DAFTAR WILAYAH
# ==========================================
region_list = ("Kota Solok", "Kota Padang", "Kota Bukittinggi", "Kota Sawahlunto", "Kota Pariaman", "Kota Payakumbuh", "Kota Padang Panjang", "Kabupaten Agam", "Kabupaten Dharmasraya", "Kabupaten Kepulauan Mentawai", "Kabupaten Lima Puluh Kota", "Kabupaten Padang Pariaman", "Kabupaten Pasaman", "Kabupaten Pasaman Barat", "Kabupaten Pesisir Selatan", "Kabupaten Sijunjung", "Kabupaten Solok", "Kabupaten Solok Selatan", "Kabupaten Tanah Datar")

# ==========================================
# TAMPILAN 1: LANDING PAGE
# ==========================================
if st.session_state['app_mode'] == 'landing':
    st.markdown('<h1 class="kudo-header">KUDO</h1>', unsafe_allow_html=True)
    st.markdown('<p class="kudo-subtitle">KOREK USAHA DIGITAL ONLINE - BPS KOTA SOLOK</p>', unsafe_allow_html=True)
    
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        st.markdown('<div style="color:white; margin-bottom:10px; text-align:center;">Silakan pilih wilayah Anda:</div>', unsafe_allow_html=True)
        choice = st.selectbox("Wilayah", region_list, label_visibility="collapsed")
        if st.button("Masuk Ke Dashboard"):
            st.session_state['selected_region'] = choice
            st.session_state['app_mode'] = 'main'
            st.rerun()

# ==========================================
# TAMPILAN 2: DASHBOARD UTAMA (IKON)
# ==========================================
elif st.session_state['app_mode'] == 'main':
    st.markdown('<h1 class="kudo-header">KUDO</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="kudo-subtitle">MENU UTAMA - Wilayah Aktif: {st.session_state["selected_region"]}</p>', unsafe_allow_html=True)
    
    st.markdown('<div class="menu-container">', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown('<h2 style="text-align:center;">🖨️</h2>', unsafe_allow_html=True)
        if st.button("1. Filter Kolom"): st.session_state['active_menu'], st.session_state['app_mode'] = "1. Filter Kolom", "feature_active"; st.rerun()
        st.markdown('<p class="menu-item-desc">Filter kolom data</p>', unsafe_allow_html=True)
    with c2:
        st.markdown('<h2 style="text-align:center;">🖥️</h2>', unsafe_allow_html=True)
        if st.button("2. Duplikasi"): st.session_state['active_menu'], st.session_state['app_mode'] = "2. Duplikasi Data", "feature_active"; st.rerun()
        st.markdown('<p class="menu-item-desc">Hapus data ganda</p>', unsafe_allow_html=True)
    with c3:
        st.markdown('<h2 style="text-align:center;">🎧</h2>', unsafe_allow_html=True)
        if st.button("3. Merge Data"): st.session_state['active_menu'], st.session_state['app_mode'] = "3. Merge Data", "feature_active"; st.rerun()
        st.markdown('<p class="menu-item-desc">Gabung banyak file</p>', unsafe_allow_html=True)
    with c4:
        st.markdown('<h2 style="text-align:center;">📸</h2>', unsafe_allow_html=True)
        if st.button("4. Instagram"): st.session_state['active_menu'], st.session_state['app_mode'] = "4. Ekstrak No Telp & Alamat (Instagram)", "feature_active"; st.rerun()
        st.markdown('<p class="menu-item-desc">Ekstrak Bio IG</p>', unsafe_allow_html=True)

    st.markdown('<div style="width:100%; height:10px;"></div>', unsafe_allow_html=True)

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        st.markdown('<h2 style="text-align:center;">⚙️</h2>', unsafe_allow_html=True)
        if st.button("5. GMaps"): st.session_state['active_menu'], st.session_state['app_mode'] = "5. Ekstrak Alamat (Google Maps)", "feature_active"; st.rerun()
        st.markdown('<p class="menu-item-desc">Ekstrak Alamat Maps</p>', unsafe_allow_html=True)
    with c6:
        st.markdown('<h2 style="text-align:center;">🖱️</h2>', unsafe_allow_html=True)
        if st.button("6. Peta & SHP"): st.session_state['active_menu'], st.session_state['app_mode'] = "6. Visualisasi Peta & Convert excel to shp", "feature_active"; st.rerun()
        st.markdown('<p class="menu-item-desc">Peta & Shapefile</p>', unsafe_allow_html=True)
    with c7:
        st.markdown('<h2 style="text-align:center;">⬇️</h2>', unsafe_allow_html=True)
        if st.button("7. Cek Tipe"): st.session_state['active_menu'], st.session_state['app_mode'] = "7. Cek Info & Tipe Data", "feature_active"; st.rerun()
        st.markdown('<p class="menu-item-desc">Info struktur data</p>', unsafe_allow_html=True)
    with c8:
        st.markdown('<h2 style="text-align:center;">📝</h2>', unsafe_allow_html=True)
        if st.button("8. Edit Data"): st.session_state['active_menu'], st.session_state['app_mode'] = "8. Edit/Hapus Data", "feature_active"; st.rerun()
        st.markdown('<p class="menu-item-desc">Workspace Edit</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    col_back = st.columns([2,1,2])
    if col_back[1].button("🔄 Ganti Wilayah"): st.session_state['app_mode'] = 'landing'; st.rerun()

# ==========================================
# TAMPILAN 3: HALAMAN FITUR (AKTIF)
# ==========================================
elif st.session_state['app_mode'] == 'feature_active':
    # Sidebar Fitur
    st.sidebar.markdown("<h2 style='text-align:center;'>🟠 Menu KUDO</h2>", unsafe_allow_html=True)
    st.sidebar.markdown(f"<div style='background-color:#FF7A00; padding:10px; border-radius:10px; color:white; text-align:center; font-weight:bold; margin-bottom:20px;'>📍 {st.session_state['selected_region']}</div>", unsafe_allow_html=True)
    
    all_menus = ("1. Filter Kolom", "2. Duplikasi Data", "3. Merge Data", "4. Ekstrak No Telp & Alamat (Instagram)", "5. Ekstrak Alamat (Google Maps)", "6. Visualisasi Peta & Convert excel to shp", "7. Cek Info & Tipe Data", "8. Edit/Hapus Data")
    
    selected_menu = st.sidebar.radio("Pilih Fitur:", all_menus, index=all_menus.index(st.session_state['active_menu']))
    st.session_state['active_menu'] = selected_menu # Update jika diganti lewat sidebar

    if st.sidebar.button("🔙 Kembali ke Dashboard"):
        st.session_state['app_mode'] = 'main'
        st.rerun()

    # --- KONTEN FITUR ---
    st.markdown(f'<div class="pro-banner"><h1>KUDO Data Processing</h1><p>{selected_menu}</p></div>', unsafe_allow_html=True)

    if selected_menu == "1. Filter Kolom":
        uploaded_file = st.file_uploader("Upload file", type=['csv', 'xlsx', 'json'], key="f1")
        if uploaded_file:
            df = load_data(uploaded_file)
            if df is not None:
                st.write("Preview Data:")
                st.dataframe(df.head())
                cols = st.multiselect("Pilih kolom yang ingin dipertahankan:", df.columns.tolist(), default=df.columns.tolist())
                if st.button("Download Data Terfilter"):
                    st.download_button("📥 Download XLSX", data=to_excel(df[cols]), file_name="filtered.xlsx")

    elif selected_menu == "2. Duplikasi Data":
        uploaded_file = st.file_uploader("Upload file", type=['csv', 'xlsx', 'json'], key="f2")
        if uploaded_file:
            df = load_data(uploaded_file)
            if df is not None:
                subset = st.multiselect("Pilih kolom acuan duplikat (Kosongkan untuk semua kolom):", df.columns.tolist())
                if st.button("Proses Hapus Duplikat"):
                    df_clean = df.drop_duplicates(subset=subset if subset else None)
                    st.success(f"Berhasil! Dari {len(df)} baris menjadi {len(df_clean)} baris.")
                    st.dataframe(df_clean.head())
                    st.download_button("📥 Download Bersih", data=to_excel(df_clean), file_name="clean.xlsx")

    elif selected_menu == "3. Merge Data":
        uploaded_files = st.file_uploader("Upload beberapa file (Maks 15)", type=['csv', 'xlsx', 'json'], accept_multiple_files=True)
        if uploaded_files:
            dfs = [load_data(f) for f in uploaded_files if load_data(f) is not None]
            if dfs and st.button("Gabungkan Sekarang"):
                merged = pd.concat(dfs, ignore_index=True)
                st.success(f"Total baris gabungan: {len(merged)}")
                st.dataframe(merged.head())
                st.download_button("📥 Download Hasil Gabung", data=to_excel(merged), file_name="merged.xlsx")

    elif selected_menu == "4. Ekstrak No Telp & Alamat (Instagram)":
        st.info(f"Wilayah Default: {st.session_state['selected_region']}")
        uploaded_file = st.file_uploader("Upload file scraping IG", type=['csv', 'xlsx', 'json'])
        if uploaded_file:
            df = load_data(uploaded_file)
            if df is not None:
                target_col = st.selectbox("Pilih kolom Bio/Profil:", df.columns.tolist())
                if st.button("Ekstrak"):
                    df['nomor_hp'] = df[target_col].apply(extract_phone_number)
                    df['alamat_ig'] = df[target_col].apply(lambda x: extract_address_ig(x, st.session_state['selected_region']))
                    st.dataframe(df[[target_col, 'nomor_hp', 'alamat_ig']].head())
                    st.download_button("📥 Download Hasil", data=to_excel(df), file_name="extracted_ig.xlsx")

    elif selected_menu == "5. Ekstrak Alamat (Google Maps)":
        uploaded_file = st.file_uploader("Upload file GMaps", type=['csv', 'xlsx', 'json'])
        if uploaded_file:
            df = load_data(uploaded_file)
            if df is not None:
                target_col = st.selectbox("Pilih kolom alamat mentah:", df.columns.tolist())
                if st.button("Bersihkan Alamat"):
                    df['alamat_bersih'] = df[target_col].apply(extract_address_gmaps)
                    st.dataframe(df[[target_col, 'alamat_bersih']].head())
                    st.download_button("📥 Download", data=to_excel(df), file_name="cleaned_maps.xlsx")

    elif selected_menu == "6. Visualisasi Peta & Convert excel to shp":
        uploaded_file = st.file_uploader("Upload data spasial", type=['csv', 'xlsx', 'json'])
        if uploaded_file:
            df = load_data(uploaded_file)
            if df is not None:
                all_cols = df.columns.tolist()
                c1, c2 = st.columns(2)
                lat_c = c1.selectbox("Kolom Latitude:", all_cols)
                lon_c = c2.selectbox("Kolom Longitude:", all_cols)
                info_c = st.multiselect("Kolom Info Popup:", all_cols)
                
                if st.button("Render Peta"):
                    df_map = df.dropna(subset=[lat_c, lon_c]).copy()
                    df_map[lat_c] = pd.to_numeric(df_map[lat_c], errors='coerce')
                    df_map[lon_c] = pd.to_numeric(df_map[lon_c], errors='coerce')
                    
                    m = folium.Map(location=[df_map[lat_c].mean(), df_map[lon_c].mean()], zoom_start=12)
                    for _, row in df_map.iterrows():
                        popup_txt = "<br>".join([f"<b>{c}:</b> {row[c]}" for c in info_c])
                        folium.CircleMarker([row[lat_c], row[lon_c]], radius=6, color="#FF7A00", fill=True, popup=popup_txt).add_to(m)
                    st_folium(m, width=900, height=500)
                    
                    st.download_button("🗺️ Download SHP (.zip)", data=to_shp_zip(df_map, lat_c, lon_c), file_name="peta.zip")

    elif selected_menu == "7. Cek Info & Tipe Data":
        uploaded_file = st.file_uploader("Upload file", type=['csv', 'xlsx', 'json'])
        if uploaded_file:
            df = load_data(uploaded_file)
            if df is not None:
                res = pd.DataFrame({"Tipe": df.dtypes.astype(str), "Null": df.isnull().sum(), "Non-Null": df.notnull().sum()})
                st.write(f"Baris: {len(df)}, Kolom: {len(df.columns)}")
                st.table(res)

    elif selected_menu == "8. Edit/Hapus Data":
        uploaded_file = st.file_uploader("Upload file", type=['csv', 'xlsx', 'json'])
        if uploaded_file:
            if 'temp_df' not in st.session_state or st.session_state.get('last_file') != uploaded_file.name:
                st.session_state['temp_df'] = load_data(uploaded_file)
                st.session_state['last_file'] = uploaded_file.name
            
            edited = st.data_editor(st.session_state['temp_df'], num_rows="dynamic", use_container_width=True)
            if st.button("Simpan & Download Hasil Edit"):
                st.download_button("📥 Download XLSX", data=to_excel(edited), file_name="edited.xlsx")
