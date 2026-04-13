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
# KONFIGURASI & STYLING HALAMAN
# ==========================================
st.set_page_config(page_title="KUDO Data Processing", page_icon="🟠", layout="wide")

# Custom CSS untuk tampilan Dashboard & Welcome
st.markdown("""
<style>
    /* Styling Dasar */
    .stApp { background-color: #0e1117; }
    h1, h2, h3 { color: #FF7A00 !important; }
    
    /* Welcome Banner */
    .welcome-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 50px;
        border-radius: 20px;
        border: 2px solid #FF7A00;
        text-align: center;
        margin: 50px auto;
        box-shadow: 0 10px 30px rgba(255, 122, 0, 0.2);
    }
    
    /* Tombol Navigasi */
    div.stButton > button {
        background-color: #FF7A00;
        color: white;
        border-radius: 10px;
        padding: 20px;
        font-weight: bold;
        border: none;
        width: 100%;
        transition: 0.3s;
    }
    div.stButton > button:hover {
        background-color: #e66e00;
        transform: scale(1.02);
    }
    
    /* Grid Menu Text */
    .menu-label {
        text-align: center;
        color: white;
        font-weight: 600;
        margin-top: -10px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# STATE MANAGEMENT
# ==========================================
if 'page' not in st.session_state:
    st.session_state.page = 'welcome'
if 'default_region' not in st.session_state:
    st.session_state.default_region = "Kota Solok"

# ==========================================
# FUNGSI UTILITAS
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

# Regex Functions
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
# LOGIKA HALAMAN
# ==========================================

# 1. WELCOME SCREEN
if st.session_state.page == 'welcome':
    st.markdown(f"""
    <div class="welcome-card">
        <h1 style="font-size: 4rem; letter-spacing: 10px; margin-bottom:0;">KUDO</h1>
        <p style="color: #ccc; font-size: 1.2rem;">KOREK USAHA DIGITAL ONLINE</p>
    </div>
    """, unsafe_allow_html=True)
    
    col_l, col_c, col_r = st.columns([1,2,1])
    with col_c:
        if st.button("WELCOME KUDO - Klik Disini"):
            st.session_state.page = 'region_selection'
            st.rerun()

# 2. SELEKSI WILAYAH
elif st.session_state.page == 'region_selection':
    st.markdown("<h2 style='text-align:center;'>Pilih Wilayah Default</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:white;'>Wilayah ini akan otomatis digunakan untuk fitur Ekstrak IG</p>", unsafe_allow_html=True)
    
    col_l, col_c, col_r = st.columns([1,1,1])
    with col_c:
        region = st.selectbox("Pilih Wilayah:", 
            ("Kota Solok", "Kota Padang", "Kota Bukittinggi", "Kota Sawahlunto", "Kota Pariaman", "Kota Payakumbuh", "Kota Padang Panjang",
            "Kabupaten Agam", "Kabupaten Dharmasraya", "Kabupaten Kepulauan Mentawai", "Kabupaten Lima Puluh Kota", "Kabupaten Padang Pariaman",
            "Kabupaten Pasaman", "Kabupaten Pasaman Barat", "Kabupaten Pesisir Selatan", "Kabupaten Sijunjung", "Kabupaten Solok", "Kabupaten Solok Selatan",
            "Kabupaten Tanah Datar"))
        
        if st.button("Lanjutkan ke Dashboard"):
            st.session_state.default_region = region
            st.session_state.page = 'dashboard'
            st.rerun()

# 3. DASHBOARD MENU (GRID STYLE)
elif st.session_state.page == 'dashboard':
    st.markdown("<h1 style='text-align:center;'>MAIN MENU KUDO</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; color:gray;'>Wilayah Aktif: {st.session_state.default_region}</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🖨️\n\nFilter Kolom"): st.session_state.page = 'm1'; st.rerun()
        st.markdown("<div class='menu-label'>1. Filter Kolom</div>", unsafe_allow_html=True)
        
        if st.button("☁️\n\nDuplicate"): st.session_state.page = 'm2'; st.rerun()
        st.markdown("<div class='menu-label'>2. Hapus Duplikat</div>", unsafe_allow_html=True)
        
        if st.button("📥\n\nMerge Data"): st.session_state.page = 'm3'; st.rerun()
        st.markdown("<div class='menu-label'>3. Gabung File</div>", unsafe_allow_html=True)

    with col2:
        if st.button("🖥️\n\nEkstrak IG"): st.session_state.page = 'm4'; st.rerun()
        st.markdown("<div class='menu-label'>4. Ekstrak IG (Auto Wilayah)</div>", unsafe_allow_html=True)
        
        if st.button("⚙️\n\nProcessors"): st.session_state.page = 'm5'; st.rerun()
        st.markdown("<div class='menu-label'>5. Ekstrak Alamat Maps</div>", unsafe_allow_html=True)
        
        if st.button("📊\n\nInfo Data"): st.session_state.page = 'm7'; st.rerun()
        st.markdown("<div class='menu-label'>7. Cek Tipe Data</div>", unsafe_allow_html=True)

    with col3:
        if st.button("🎧\n\nHeadsets"): st.session_state.page = 'm6'; st.rerun()
        st.markdown("<div class='menu-label'>6. Visualisasi Peta</div>", unsafe_allow_html=True)
        
        if st.button("🖱️\n\nMouse"): st.session_state.page = 'm8'; st.rerun()
        st.markdown("<div class='menu-label'>8. Edit/Workspace</div>", unsafe_allow_html=True)
        
        if st.button("🔄\n\nGanti Wilayah"): st.session_state.page = 'region_selection'; st.rerun()
        st.markdown("<div class='menu-label'>Reset Wilayah</div>", unsafe_allow_html=True)

# ==========================================
# LOGIKA FITUR (SETIAP MENU)
# ==========================================

def back_btn():
    if st.button("⬅️ Kembali ke Menu Utama"):
        st.session_state.page = 'dashboard'
        st.rerun()

if st.session_state.page == 'm1':
    st.header("1. Filter Kolom Tertentu")
    back_btn()
    uploaded_file = st.file_uploader("Upload file", type=['csv', 'xlsx', 'json'])
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None:
            selected = st.multiselect("Pilih kolom:", df.columns.tolist(), default=df.columns.tolist())
            if st.button("Download Filtered"):
                st.download_button("📥 Download", data=to_excel(df[selected]), file_name="filtered.xlsx")

elif st.session_state.page == 'm2':
    st.header("2. Hapus Duplikat")
    back_btn()
    uploaded_file = st.file_uploader("Upload file", type=['csv', 'xlsx', 'json'])
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None:
            cols = st.multiselect("Acuan duplikat (Kosongkan = semua):", df.columns.tolist())
            if st.button("Proses Hapus"):
                df_clean = df.drop_duplicates(subset=cols if cols else None)
                st.success(f"Berhasil! Dari {len(df)} baris menjadi {len(df_clean)}")
                st.download_button("📥 Download Clean", data=to_excel(df_clean), file_name="clean.xlsx")

elif st.session_state.page == 'm3':
    st.header("3. Gabung File (Merge)")
    back_btn()
    files = st.file_uploader("Upload file (Maks 15)", accept_multiple_files=True)
    if files:
        dfs = [load_data(f) for f in files]
        if st.button("Gabungkan Sekarang"):
            merged = pd.concat(dfs, ignore_index=True)
            st.write(f"Total baris: {len(merged)}")
            st.download_button("📥 Download", data=to_excel(merged), file_name="merged.xlsx")

elif st.session_state.page == 'm4':
    st.header("4. Ekstrak Instagram")
    st.info(f"📍 Wilayah Default: **{st.session_state.default_region}**")
    back_btn()
    uploaded_file = st.file_uploader("Upload file scraping IG", type=['csv', 'xlsx', 'json'])
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None:
            target = st.selectbox("Kolom Bio:", df.columns.tolist())
            if st.button("Mulai Ekstrak"):
                df['nomor_hp'] = df[target].apply(extract_phone_number)
                df['alamat_ig'] = df[target].apply(lambda x: extract_address_ig(x, st.session_state.default_region))
                st.dataframe(df[[target, 'nomor_hp', 'alamat_ig']].head())
                st.download_button("📥 Download Hasil", data=to_excel(df), file_name="ekstrak_ig.xlsx")

elif st.session_state.page == 'm5':
    st.header("5. Ekstrak Alamat Google Maps")
    back_btn()
    uploaded_file = st.file_uploader("Upload file Maps", type=['csv', 'xlsx', 'json'])
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None:
            target = st.selectbox("Kolom Alamat Raw:", df.columns.tolist())
            if st.button("Ekstrak Alamat"):
                df['alamat_bersih'] = df[target].apply(extract_address_gmaps)
                st.dataframe(df[[target, 'alamat_bersih']].head())
                st.download_button("📥 Download", data=to_excel(df), file_name="maps_clean.xlsx")

elif st.session_state.page == 'm6':
    st.header("6. Visualisasi Peta & SHP")
    back_btn()
    uploaded_file = st.file_uploader("Upload file Koordinat", type=['csv', 'xlsx', 'json'])
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None:
            lat = st.selectbox("Latitude:", df.columns.tolist(), index=0)
            lon = st.selectbox("Longitude:", df.columns.tolist(), index=1)
            if st.button("Tampilkan Peta"):
                m = folium.Map(location=[df[lat].mean(), df[lon].mean()], zoom_start=12)
                for _, row in df.iterrows():
                    folium.Marker([row[lat], row[lon]]).add_to(m)
                st_folium(m, width=700)
                st.download_button("📥 Download SHP (Zip)", data=to_shp_zip(df, lat, lon), file_name="peta.zip")

elif st.session_state.page == 'm7':
    st.header("7. Informasi Struktur Data")
    back_btn()
    uploaded_file = st.file_uploader("Upload file", type=['csv', 'xlsx', 'json'])
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None:
            st.write(df.dtypes)
            st.write(f"Total Missing: {df.isnull().sum().sum()}")

elif st.session_state.page == 'm8':
    st.header("8. Workspace Editor")
    back_btn()
    uploaded_file = st.file_uploader("Upload file", type=['csv', 'xlsx', 'json'])
    if uploaded_file:
        df = load_data(uploaded_file)
        edited_df = st.data_editor(df)
        st.download_button("📥 Simpan Perubahan", data=to_excel(edited_df), file_name="edited.xlsx")

st.sidebar.caption("© 2026 BPS Kota Solok - KUDO v2.0")
