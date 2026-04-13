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

st.markdown("""
<style>
    /* Sembunyikan Sidebar */
    [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none; }
    
    .stApp { background-color: #0e1117; }
    h1, h2, h3 { color: #FF7A00 !important; font-family: 'Segoe UI', sans-serif; }
    
    /* Welcome Card */
    .welcome-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 60px;
        border-radius: 25px;
        border: 2px solid #FF7A00;
        text-align: center;
        margin: 50px auto;
        box-shadow: 0 15px 35px rgba(255, 122, 0, 0.2);
    }
    
    /* Grid Tombol Dashboard */
    div.stButton > button {
        background-color: #FF7A00;
        color: white;
        border-radius: 15px;
        padding: 25px;
        font-weight: bold;
        border: none;
        width: 100%;
        min-height: 140px;
        font-size: 1.2rem;
        transition: 0.3s ease;
        margin-bottom: 30px;
    }
    div.stButton > button:hover {
        background-color: #e66e00;
        transform: translateY(-5px);
        box-shadow: 0 8px 20px rgba(255, 122, 0, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# STATE MANAGEMENT
# ==========================================
if 'page' not in st.session_state: st.session_state.page = 'welcome'
if 'default_region' not in st.session_state: st.session_state.default_region = "Kota Solok"
if 'edit_df' not in st.session_state: st.session_state['edit_df'] = None

# ==========================================
# FUNGSI UTILITAS & PROCESSING
# ==========================================
@st.cache_data
def load_data(file):
    file_name = file.name.lower()
    try:
        if file_name.endswith('.csv'): return pd.read_csv(file)
        elif file_name.endswith(('.xlsx', '.xls')): return pd.read_excel(file)
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
            f_path = os.path.join(temp_dir, f"{base_filename}{ext}")
            if os.path.exists(f_path): zip_file.write(f_path, f"{base_filename}{ext}")
    return zip_buffer.getvalue()

def extract_phone_number(text):
    if pd.isna(text): return None
    pattern = r'\+62[\s-]?\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}|\b62[\s-]?\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}|\b08\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}'
    matches = re.findall(pattern, str(text))
    return ', '.join([m.strip() for m in matches]) if matches else None

def extract_address_ig(text, default_region):
    if pd.isna(text): return default_region
    match = re.search(r'(?i)\b(jl|jalan|jln)\b[.\s]*[^\n]+', str(text))
    return match.group(0).strip(' ,.-') if match else default_region

def extract_address_gmaps(text):
    if pd.isna(text): return None
    pattern = r'(?i)\b(jl|jalan|jln|raya|dusun|desa|komplek|gedung|rt|rw|blok)\b.*?(?:\d{5}|indonesia|$)'
    match = re.search(pattern, str(text))
    return match.group(0).strip(' ,.-') if match else str(text).strip(' ,.-')

def back_btn():
    if st.button("⬅️ Kembali ke Menu Utama"):
        st.session_state.page = 'dashboard'
        st.rerun()

# ==========================================
# ALUR HALAMAN
# ==========================================

# 1. WELCOME SCREEN
if st.session_state.page == 'welcome':
    st.markdown('<div class="welcome-card"><h1>KUDO</h1><p style="color:#ccc">KOREK USAHA DIGITAL ONLINE</p></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        if st.button("WELCOME KUDO - Klik Disini"):
            st.session_state.page = 'select_region'
            st.rerun()

# 2. PILIH WILAYAH
elif st.session_state.page == 'select_region':
    st.markdown("<h2 style='text-align:center;'>Pilih Wilayah Default</h2>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        region = st.selectbox("Wilayah ini otomatis untuk fitur Ekstrak IG:", 
            ("Kota Solok", "Kota Padang", "Kota Bukittinggi", "Kota Sawahlunto", "Kota Pariaman", "Kota Payakumbuh", "Kota Padang Panjang", "Kabupaten Solok", "Kabupaten Tanah Datar"))
        if st.button("Masuk Dashboard"):
            st.session_state.default_region = region
            st.session_state.page = 'dashboard'
            st.rerun()

# 3. MAIN DASHBOARD (TANPA TEKS LABEL)
elif st.session_state.page == 'dashboard':
    st.markdown(f"<h1 style='text-align:center;'>MAIN MENU KUDO</h1><p style='text-align:center; color:gray;'>Wilayah: {st.session_state.default_region}</p>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🖨️\n\nFilter Kolom"): st.session_state.page = 'f1'; st.rerun()
        if st.button("☁️\n\nDuplicate"): st.session_state.page = 'f2'; st.rerun()
        if st.button("📥\n\nMerge Data"): st.session_state.page = 'f3'; st.rerun()
    with col2:
        if st.button("🖥️\n\nEkstrak IG"): st.session_state.page = 'f4'; st.rerun()
        if st.button("⚙️\n\nProcessors"): st.session_state.page = 'f5'; st.rerun()
        if st.button("📊\n\nInfo Data"): st.session_state.page = 'f7'; st.rerun()
    with col3:
        if st.button("🎧\n\nVisualisasi"): st.session_state.page = 'f6'; st.rerun()
        if st.button("🖱️\n\nWorkspace"): st.session_state.page = 'f8'; st.rerun()
        if st.button("🔄\n\nGanti Wilayah"): st.session_state.page = 'select_region'; st.rerun()

# ==========================================
# DETAIL FITUR DALAM
# ==========================================

elif st.session_state.page == 'f1':
    st.header("1. Filter Kolom")
    back_btn()
    up = st.file_uploader("Upload File", type=['csv', 'xlsx'])
    if up:
        df = load_data(up)
        if df is not None:
            sel = st.multiselect("Pilih Kolom:", df.columns.tolist(), default=df.columns.tolist())
            st.download_button("Download", data=to_excel(df[sel]), file_name="filtered.xlsx")

elif st.session_state.page == 'f2':
    st.header("2. Hapus Duplikat")
    back_btn()
    up = st.file_uploader("Upload File", type=['csv', 'xlsx'])
    if up:
        df = load_data(up)
        if df is not None:
            dup_cols = st.multiselect("Kolom Acuan:", df.columns.tolist())
            if st.button("Hapus Duplikat"):
                df_c = df.drop_duplicates(subset=dup_cols if dup_cols else None)
                st.success(f"Sisa {len(df_c)} baris")
                st.download_button("Download Clean", data=to_excel(df_c), file_name="clean.xlsx")

elif st.session_state.page == 'f3':
    st.header("3. Merge Data")
    back_btn()
    files = st.file_uploader("Upload Beberapa File", accept_multiple_files=True)
    if files:
        if st.button("Gabungkan"):
            merged = pd.concat([load_data(f) for f in files], ignore_index=True)
            st.success(f"Total: {len(merged)} baris")
            st.download_button("Download Merged", data=to_excel(merged), file_name="merged.xlsx")

elif st.session_state.page == 'f4':
    st.header("4. Ekstrak Instagram")
    st.info(f"Wilayah: {st.session_state.default_region}")
    back_btn()
    up = st.file_uploader("Upload Data Scraping IG", type=['csv', 'xlsx'])
    if up:
        df = load_data(up)
        if df is not None:
            col = st.selectbox("Kolom Bio:", df.columns.tolist())
            if st.button("Ekstrak"):
                df['nomor_hp'] = df[col].apply(extract_phone_number)
                df['alamat_ig'] = df[col].apply(lambda x: extract_address_ig(x, st.session_state.default_region))
                st.dataframe(df.head())
                st.download_button("Download Hasil", data=to_excel(df), file_name="ig_extracted.xlsx")

elif st.session_state.page == 'f5':
    st.header("5. Ekstrak Alamat Maps")
    back_btn()
    up = st.file_uploader("Upload Data Maps", type=['csv', 'xlsx'])
    if up:
        df = load_data(up)
        if df is not None:
            col = st.selectbox("Kolom Alamat:", df.columns.tolist())
            if st.button("Mulai Ekstrak"):
                df['alamat_ekstrak'] = df[col].apply(extract_address_gmaps)
                st.dataframe(df.head())
                st.download_button("Download", data=to_excel(df), file_name="maps_extracted.xlsx")

elif st.session_state.page == 'f6':
    st.header("6. Visualisasi Peta")
    back_btn()
    up = st.file_uploader("Upload Data Koordinat", type=['csv', 'xlsx'])
    if up:
        df = load_data(up)
        if df is not None:
            lat = st.selectbox("Latitude:", df.columns.tolist(), index=0)
            lon = st.selectbox("Longitude:", df.columns.tolist(), index=1)
            if st.button("Render Peta"):
                m = folium.Map(location=[df[lat].mean(), df[lon].mean()], zoom_start=12)
                for _, r in df.iterrows(): folium.CircleMarker([r[lat], r[lon]], radius=5, color="#FF7A00").add_to(m)
                st_folium(m, width=1000)
                st.download_button("Download SHP", data=to_shp_zip(df, lat, lon), file_name="peta.zip")

elif st.session_state.page == 'f7':
    st.header("7. Info Data")
    back_btn()
    up = st.file_uploader("Upload File", type=['csv', 'xlsx'])
    if up:
        df = load_data(up)
        if df is not None:
            st.write("### Struktur Data")
            st.write(df.dtypes)
            st.metric("Total Baris", len(df))
            st.metric("Total Kolom", len(df.columns))

elif st.session_state.page == 'f8':
    st.header("8. Workspace Editor")
    back_btn()
    up = st.file_uploader("Upload File", type=['csv', 'xlsx'])
    if up:
        if st.session_state.edit_df is None: st.session_state.edit_df = load_data(up)
        new_df = st.data_editor(st.session_state.edit_df, num_rows="dynamic")
        if st.button("Simpan Perubahan"):
            st.session_state.edit_df = new_df
            st.success("Tersimpan!")
        st.download_button("Download Hasil Edit", data=to_excel(new_df), file_name="edited.xlsx")

st.markdown("---")
st.caption("© 2026 BPS Kota Solok - KUDO v2.0")
