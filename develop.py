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
# KONFIGURASI & STYLING HALAMAN (HTML/CSS)
# ==========================================
st.set_page_config(page_title="KUDO Data Processing", page_icon="🟠", layout="wide")

custom_css = """
<style>
    /* Mengimpor Font Modern */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* Gradient Banner Utama */
    .pro-banner {
        background: linear-gradient(135deg, #FF7A00 0%, #FFA733 100%);
        padding: 40px;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 10px 30px rgba(255, 122, 0, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }

    .pro-banner h1 {
        color: white !important;
        margin: 0;
        font-size: 3rem;
        font-weight: 800;
        letter-spacing: -1px;
    }

    .pro-banner p {
        font-size: 1.1rem;
        opacity: 0.95;
        margin-top: 10px;
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #fcfcfc;
        border-right: 2px solid #FF7A00;
    }

    h2, h3 { 
        color: #FF7A00 !important; 
        font-weight: 700 !important;
    }

    /* Button Customization */
    div.stButton > button {
        background: #FF7A00;
        color: white;
        border-radius: 12px;
        border: none;
        padding: 10px 20px;
        font-weight: 600;
        transition: all 0.3s ease;
        width: 100%;
    }

    div.stButton > button:hover {
        background: #E66E00;
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(255, 122, 0, 0.3);
        color: white;
    }

    /* Card Look for Dataframe */
    [data-testid="stDataFrame"] {
        border-radius: 15px;
        border: 1px solid #eee;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# Render Banner
st.markdown("""
<div class="pro-banner">
    <h1>KUDO Data Processing</h1>
    <p>Solusi cerdas pengolahan data scraping dengan standar industri</p>
</div>
""", unsafe_allow_html=True)

# ==========================================
# FUNGSI-FUNGSI UTAMA (LOGIC)
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
# SIDEBAR NAVIGASI
# ==========================================
st.sidebar.markdown("<h2>🟠 Menu KUDO</h2>", unsafe_allow_html=True)
menu = st.sidebar.radio(
    "Silakan Pilih Fitur:",
    ("1. Filter Kolom", "2. Duplikasi Data", "3. Merge Data", 
     "4. Ekstrak No Telp & Alamat (Instagram)", "5. Ekstrak Alamat (Google Maps)",
     "6. Visualisasi Peta & Convert to SHP", "7. Cek Info Data", "8. Edit/Hapus Data")
)
st.sidebar.markdown("---")
st.sidebar.caption("© 2026 BPS Kota Solok")

# ==========================================
# LOGIC PER MENU
# ==========================================

if menu == "1. Filter Kolom":
    st.header("1. Filter Kolom Tertentu")
    uploaded_file = st.file_uploader("Upload file", type=['csv', 'xlsx', 'json'], key='m1')
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None:
            selected_columns = st.multiselect("Pilih kolom yang ingin disimpan:", df.columns.tolist(), default=df.columns.tolist())
            if st.button("Download Hasil Filter"):
                st.download_button("📥 Download (XLSX)", data=to_excel(df[selected_columns]), file_name="filtered_data.xlsx")

elif menu == "2. Duplikasi Data":
    st.header("2. Pembersihan Data Duplikat")
    uploaded_file = st.file_uploader("Upload file", type=['csv', 'xlsx', 'json'], key='m2')
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None:
            dup_cols = st.multiselect("Acuan kolom duplikat:", df.columns.tolist())
            if st.button("Hapus Duplikat"):
                df_clean = df.drop_duplicates(subset=dup_cols if dup_cols else None)
                st.success(f"Data bersih: {len(df_clean)} baris")
                st.dataframe(df_clean.head())
                st.download_button("📥 Download Data Bersih", data=to_excel(df_clean), file_name="clean_data.xlsx")

elif menu == "3. Merge Data":
    st.header("3. Gabungkan Beberapa File")
    uploaded_files = st.file_uploader("Upload file (Maks 15)", type=['csv', 'xlsx', 'json'], accept_multiple_files=True)
    if uploaded_files and st.button("Proses Merge"):
        all_dfs = [load_data(f) for f in uploaded_files]
        merged_df = pd.concat(all_dfs, ignore_index=True)
        st.success(f"Total baris gabungan: {len(merged_df)}")
        st.download_button("📥 Download Hasil Merge", data=to_excel(merged_df), file_name="merged_data.xlsx")

elif menu == "4. Ekstrak No Telp & Alamat (Instagram)":
    st.header("4. Ekstrak Data Bio Instagram")
    region_choice = st.selectbox("Pilih Wilayah Default:", ("Kota Solok", "Kota Padang", "Kota Bukittinggi", "Lainnya"))
    uploaded_file = st.file_uploader("Upload data Instagram", type=['csv', 'xlsx', 'json'])
    if uploaded_file:
        df = load_data(uploaded_file)
        target_col = st.selectbox("Pilih kolom Biografi:", df.columns.tolist())
        if st.button("Ekstrak Sekarang"):
            df['nomor_hp'] = df[target_col].apply(extract_phone_number)
            df['alamat_ig'] = df[target_col].apply(lambda x: extract_address_ig(x, region_choice))
            st.dataframe(df[[target_col, 'nomor_hp', 'alamat_ig']].head())
            st.download_button("📥 Download Hasil", data=to_excel(df), file_name="ig_extracted.xlsx")

elif menu == "5. Ekstrak Alamat (Google Maps)":
    st.header("5. Ekstrak Alamat Google Maps")
    uploaded_file = st.file_uploader("Upload data Maps", type=['csv', 'xlsx', 'json'])
    if uploaded_file:
        df = load_data(uploaded_file)
        target_col = st.selectbox("Kolom alamat asli:", df.columns.tolist())
        if st.button("Ekstrak Alamat"):
            df['alamat_clean'] = df[target_col].apply(extract_address_gmaps)
            st.dataframe(df[[target_col, 'alamat_clean']].head())
            st.download_button("📥 Download", data=to_excel(df), file_name="maps_cleaned.xlsx")

elif menu == "6. Visualisasi Peta & Convert to SHP":
    st.header("6. Visualisasi Peta Spasial")
    uploaded_file = st.file_uploader("Upload data koordinat", type=['csv', 'xlsx', 'json'])
    if uploaded_file:
        df = load_data(uploaded_file)
        lat_col = st.selectbox("Kolom Latitude:", df.columns.tolist())
        lon_col = st.selectbox("Kolom Longitude:", df.columns.tolist())
        if st.button("Tampilkan Peta"):
            df_map = df.dropna(subset=[lat_col, lon_col])
            m = folium.Map(location=[df_map[lat_col].mean(), df_map[lon_col].mean()], zoom_start=12)
            for _, row in df_map.iterrows():
                folium.CircleMarker([row[lat_col], row[lon_col]], radius=5, color='#FF7A00', fill=True).add_to(m)
            st_folium(m, width=900)
            st.download_button("🗺️ Download Shapefile (.zip)", data=to_shp_zip(df_map, lat_col, lon_col), file_name="peta_kudo.zip")

elif menu == "7. Cek Info Data":
    st.header("7. Informasi Struktur Data")
    uploaded_file = st.file_uploader("Upload file", type=['csv', 'xlsx', 'json'])
    if uploaded_file:
        df = load_data(uploaded_file)
        st.write(f"Baris: {df.shape[0]} | Kolom: {df.shape[1]}")
        st.dataframe(pd.DataFrame({"Tipe": df.dtypes.astype(str), "Null": df.isnull().sum()}))

elif menu == "8. Edit/Hapus Data":
    st.header("8. Workspace Editor")
    uploaded_file = st.file_uploader("Upload file untuk diedit", type=['csv', 'xlsx', 'json'])
    if uploaded_file:
        df = load_data(uploaded_file)
        edited_df = st.data_editor(df, num_rows="dynamic")
        st.download_button("📥 Simpan Perubahan (XLSX)", data=to_excel(edited_df), file_name="edited_data.xlsx")
