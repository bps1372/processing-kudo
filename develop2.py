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

custom_css = """
<style>
    h2, h3 { color: #FF7A00 !important; font-family: 'Segoe UI', sans-serif; }
    .pro-banner {
        background: linear-gradient(135deg, #FF7A00 0%, #FFA733 100%);
        padding: 30px; border-radius: 12px; color: white; text-align: center;
        margin-bottom: 25px; box-shadow: 0 4px 15px rgba(255, 122, 0, 0.3);
    }
    .pro-banner h1 { color: white !important; margin: 0; font-size: 2.8rem; font-weight: 800; }
    div.stButton > button {
        background-color: #FF7A00; color: white; border-radius: 8px; font-weight: 600;
        width: 100%;
    }
    [data-testid="stSidebar"] { border-right: 3px solid #FF7A00; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ==========================================
# SESSION STATE UNTUK LANDING PAGE
# ==========================================
if 'app_mode' not in st.session_state:
    st.session_state['app_mode'] = 'landing'
if 'selected_region' not in st.session_state:
    st.session_state['selected_region'] = "Kota Solok"

# ==========================================
# FUNGSI-FUNGSI UTAMA (TETAP SAMA)
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
# LOGIKA TAMPILAN
# ==========================================

if st.session_state['app_mode'] == 'landing':
    # --- HALAMAN PERTAMA (LANDING PAGE) ---
    st.markdown("""
    <div class="pro-banner">
        <h1>KUDO - Korek Usaha Digital Online</h1>
        <p style="font-size: 1.2rem;">Sistem Pengolahan Data Hasil Scraping & Digitalisasi Usaha</p>
    </div>
    """, unsafe_allow_html=True)
    
    col_l, col_c, col_r = st.columns([1, 2, 1])
    
    with col_c:
        st.write("### 👋 Selamat Datang!")
        st.write("Sebelum memulai, silakan pilih wilayah kerja Anda. Wilayah ini akan menjadi nilai default pada fitur Ekstrak Instagram.")
        
        region_list = (
            "Kota Solok", "Kota Padang", "Kota Bukittinggi", "Kota Sawahlunto", "Kota Pariaman", 
            "Kota Payakumbuh", "Kota Padang Panjang", "Kabupaten Agam", "Kabupaten Dharmasraya",
            "Kabupaten Kepulauan Mentawai", "Kabupaten Lima Puluh Kota","Kabupaten Padang Pariaman",
            "Kabupaten Pasaman", "Kabupaten Pasaman Barat", "Kabupaten Pesisir Selatan", 
            "Kabupaten Sijunjung", "Kabupaten Solok", "Kabupaten Solok Selatan", "Kabupaten Tanah Datar"
        )
        
        choice = st.selectbox("Pilih Wilayah Anda:", region_list)
        
        if st.button("Masuk ke Dashboard Menu"):
            st.session_state['selected_region'] = choice
            st.session_state['app_mode'] = 'main'
            st.rerun()

else:
    # --- HALAMAN UTAMA (SETELAH PILIH WILAYAH) ---
    st.markdown("""
    <div class="pro-banner">
        <h1>KUDO Data Processing</h1>
        <p>Alat untuk processing data hasil scraping</p>
    </div>
    """, unsafe_allow_html=True)

    # SIDEBAR NAVIGASI
    st.sidebar.markdown("<h2>🟠 Menu KUDO</h2>", unsafe_allow_html=True)
    st.sidebar.info(f"📍 Wilayah: **{st.session_state['selected_region']}**")
    
    menu = st.sidebar.radio(
        "Silakan Pilih Fitur yang digunakan:",
        ("1. Filter Kolom", "2. Duplikasi Data", "3. Merge Data", 
         "4. Ekstrak No Telp & Alamat (Instagram)", "5. Ekstrak Alamat (Google Maps)",
         "6. Visualisasi Peta & Convert excel to shp", "7. Cek Info & Tipe Data", "8. Edit/Hapus Data")
    )
    
    if st.sidebar.button("🔄 Ganti Wilayah"):
        st.session_state['app_mode'] = 'landing'
        st.rerun()
        
    st.sidebar.markdown("---")
    st.sidebar.caption("© 2026 BPS Kota Solok")

    # KONTEN BERDASARKAN MENU
    if menu == "4. Ekstrak No Telp & Alamat (Instagram)":
        st.header("4. Ekstrak Nomor HP dan Alamat (Instagram)")
        st.write("Melakukan Ekstraksi informasi nomor hp dan alamat dari bio profil instagram.")
        
        st.info(f"Wilayah default saat ini: **{st.session_state['selected_region']}** (Wilayah ini digunakan jika alamat tidak ditemukan di bio)")
        
        uploaded_file = st.file_uploader("Upload file hasil scraping instagram", type=['csv', 'xlsx', 'json'], key='m4')
        
        if uploaded_file:
            df = load_data(uploaded_file)
            if df is not None:
                target_col = st.selectbox("Pilih kolom berisi biografi profil instagram:", df.columns.tolist())
                
                if st.button("Mulai Ekstrak Data"):
                    with st.spinner('Sedang memproses data...'):
                        df['nomor_hp'] = df[target_col].apply(extract_phone_number)
                        df['alamat_ig'] = df[target_col].apply(lambda x: extract_address_ig(x, st.session_state['selected_region']))
                    
                    st.success(f"Proses Selesai! Detail jalan yang kosong otomatis diisi: {st.session_state['selected_region']}")
                    st.dataframe(df[[target_col, 'nomor_hp', 'alamat_ig']].head(10))
                    
                    excel_data = to_excel(df)
                    st.download_button("📥 Download Hasil Ekstrak (XLSX)", data=excel_data, file_name=f"hasil_ekstrak_ig_{st.session_state['selected_region'].lower().replace(' ', '_')}.xlsx")

    elif menu == "1. Filter Kolom":
        st.header("1. Filter Kolom Tertentu")
        uploaded_file = st.file_uploader("Upload file (CSV, XLSX, JSON)", type=['csv', 'xlsx', 'json'], key='m1')
        if uploaded_file:
            df = load_data(uploaded_file)
            if df is not None:
                st.dataframe(df.head())
                selected_columns = st.multiselect("Pilih kolom:", df.columns.tolist(), default=df.columns.tolist())
                if selected_columns:
                    df_filtered = df[selected_columns]
                    st.download_button("📥 Download Data (XLSX)", data=to_excel(df_filtered), file_name="data_filtered.xlsx")

    elif menu == "2. Duplikasi Data":
        st.header("2. Cek & Hapus Baris Duplikat Data")
        uploaded_file = st.file_uploader("Upload file", type=['csv', 'xlsx', 'json'], key='m2')
        if uploaded_file:
            df = load_data(uploaded_file)
            if df is not None:
                dup_columns = st.multiselect("Pilih acuan kolom duplikat:", df.columns.tolist())
                if st.button("Hapus Duplikat"):
                    subset = dup_columns if dup_columns else None
                    df_clean = df.drop_duplicates(subset=subset, keep='first')
                    st.success(f"Selesai! Baris awal: {len(df)}, Baris bersih: {len(df_clean)}")
                    st.dataframe(df_clean.head())
                    st.download_button("📥 Download Data Bersih (XLSX)", data=to_excel(df_clean), file_name="data_clean.xlsx")

    elif menu == "3. Merge Data":
        st.header("3. Gabungkan Beberapa File")
        uploaded_files = st.file_uploader("Upload file (Maks 15)", type=['csv', 'xlsx', 'json'], accept_multiple_files=True, key='m3')
        if uploaded_files:
            dfs = [load_data(f) for f in uploaded_files if load_data(f) is not None]
            if dfs and st.button("Merge Sekarang"):
                merged_df = pd.concat(dfs, ignore_index=True)
                st.success(f"Berhasil menggabungkan {len(dfs)} file!")
                st.dataframe(merged_df.head())
                st.download_button("📥 Download Hasil Merge (XLSX)", data=to_excel(merged_df), file_name="data_merged.xlsx")

    elif menu == "5. Ekstrak Alamat (Google Maps)":
        st.header("5. Ekstrak Alamat Saja (Google Maps)")
        uploaded_file = st.file_uploader("Upload file", type=['csv', 'xlsx', 'json'], key='m5')
        if uploaded_file:
            df = load_data(uploaded_file)
            if df is not None:
                target_col = st.selectbox("Pilih kolom sumber alamat:", df.columns.tolist())
                if st.button("Ekstrak Alamat Maps"):
                    df['alamat_ekstrak'] = df[target_col].apply(extract_address_gmaps)
                    st.success("Ekstraksi Selesai!")
                    st.dataframe(df[[target_col, 'alamat_ekstrak']].head(10))
                    st.download_button("📥 Download (XLSX)", data=to_excel(df), file_name="maps_extracted.xlsx")

    elif menu == "6. Visualisasi Peta & Convert excel to shp":
        st.header("6. Visualisasi Peta & Export Shapefile")
        uploaded_file = st.file_uploader("Upload file", type=['csv', 'xlsx', 'json'], key='m6')
        if uploaded_file:
            df = load_data(uploaded_file)
            if df is not None:
                all_columns = df.columns.tolist()
                col1, col2 = st.columns(2)
                lat_col = col1.selectbox("Latitude:", all_columns)
                lon_col = col2.selectbox("Longitude:", all_columns)
                info_cols = st.multiselect("Popup Info:", all_columns)
                
                if st.button("Render Peta"):
                    map_df = df.copy()
                    map_df['lat'] = pd.to_numeric(map_df[lat_col], errors='coerce')
                    map_df['lon'] = pd.to_numeric(map_df[lon_col], errors='coerce')
                    map_df = map_df.dropna(subset=['lat', 'lon'])
                    
                    m = folium.Map(location=[map_df['lat'].mean(), map_df['lon'].mean()], zoom_start=12)
                    for _, row in map_df.iterrows():
                        folium.CircleMarker([row['lat'], row['lon']], radius=5, color='#FF7A00', fill=True).add_to(m)
                    st_folium(m, width=1000, height=500)
                    
                    st.download_button("🗺️ Download SHP (ZIP)", data=to_shp_zip(map_df, 'lat', 'lon'), file_name="peta.zip")

    elif menu == "7. Cek Info & Tipe Data":
        st.header("7. Cek Struktur Data")
        uploaded_file = st.file_uploader("Upload file", type=['csv', 'xlsx', 'json'], key='m7')
        if uploaded_file:
            df = load_data(uploaded_file)
            if df is not None:
                st.write(f"Total: {df.shape[0]} baris, {df.shape[1]} kolom")
                st.dataframe(pd.DataFrame({"Tipe": df.dtypes.astype(str), "Missing": df.isnull().sum()}))

    elif menu == "8. Edit/Hapus Data":
        st.header("8. Workspace Edit Data")
        uploaded_file = st.file_uploader("Upload file", type=['csv', 'xlsx', 'json'], key='m8')
        if uploaded_file:
            if 'edit_df' not in st.session_state or st.session_state.get('last_uploaded') != uploaded_file.name:
                st.session_state['edit_df'] = load_data(uploaded_file)
                st.session_state['last_uploaded'] = uploaded_file.name
            
            edited_df = st.data_editor(st.session_state['edit_df'], num_rows="dynamic", use_container_width=True)
            st.download_button("📥 Download Hasil Edit", data=to_excel(edited_df), file_name="edited_data.xlsx")
