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
    st.write("Melakukan filter kolom tertentu, sehingga hanya download data dengan kolom yang dipilih saja")
    uploaded_file = st.file_uploader("Upload file (CSV, XLSX, JSON)", type=['csv', 'xlsx', 'json'], key='m1')
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None:
            st.write(f"**Preview Data Asli** ({len(df)} baris):")
            st.dataframe(df.head())
            selected_columns = st.multiselect("Pilih kolom:", df.columns.tolist(), default=df.columns.tolist())
            if selected_columns:
                df_filtered = df[selected_columns]
                st.download_button("📥 Download Data (XLSX)", data=to_excel(df_filtered), file_name="data_filtered.xlsx")

    elif selected_menu == "2. Duplikasi Data":
    st.header("2. Cek & Hapus Baris Duplikat Data")
    st.write("Melakukan pengecekan baris data duplikat berdasarkan kolom tertentu")
    uploaded_file = st.file_uploader("Upload file (CSV, XLSX, JSON)", type=['csv', 'xlsx', 'json'], key='m2')
    
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None:
            st.write(f"**Preview Data Asli** ({len(df)} baris):")
            st.dataframe(df.head())
            
            dup_columns = st.multiselect("Pilih acuan kolom duplikat (Kosongkan jika ingin cek seluruh kolom):", df.columns.tolist())
            
            if st.button("Hapus Duplikat"):
                subset = dup_columns if dup_columns else None
                df_duplicates = df[df.duplicated(subset=subset, keep='first')]
                df_clean = df.drop_duplicates(subset=subset, keep='first')
                
                st.success("Proses pengecekan duplikat selesai!")
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Data Raw", f"{len(df)} baris")
                col2.metric("Data Duplikat", f"{len(df_duplicates)} baris")
                col3.metric("Data Bersih", f"{len(df_clean)} baris")
                
                st.write("---")
                tab1, tab2, tab3 = st.tabs(["Tabel Data Raw", "Tabel Data Duplikat", "Tabel Data Bersih"])
                
                with tab1:
                    st.dataframe(df)
                with tab2:
                    if len(df_duplicates) > 0:
                        st.dataframe(df_duplicates)
                    else:
                        st.info("Tidak ada data duplikat yang ditemukan.")
                with tab3:
                    st.dataframe(df_clean)
                
                st.write("---")
                st.download_button(
                    label="📥 Download Data Bersih (XLSX)", 
                    data=to_excel(df_clean), 
                    file_name="data_clean_dedup.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )


    
    elif selected_menu == "3. Merge Data":
    st.write("Merge/ mengabungkan beberapa file format sama menjadi satu file")
    uploaded_files = st.file_uploader("Upload file (Maks 15)", type=['csv', 'xlsx', 'json'], accept_multiple_files=True, key='m3')
    if uploaded_files:
        if len(uploaded_files) > 15:
            st.error("Maksimal 15 file.")
        else:
            dfs = []
            for f in uploaded_files:
                df = load_data(f)
                if df is not None:
                    dfs.append(df)
                    with st.expander(f"📄 Preview: {f.name} ({len(df)} baris)"):
                        st.dataframe(df.head())

            if dfs and st.button("Merge Sekarang"):
                merged_df = pd.concat(dfs, ignore_index=True)
                st.success(f"Berhasil! Total baris setelah di-merge: {len(merged_df)}")
                st.dataframe(merged_df.head())
                st.download_button("📥 Download Hasil Merge (XLSX)", data=to_excel(merged_df), file_name="data_merged.xlsx")

    
    elif selected_menu == "4. Ekstrak No Telp & Alamat (Instagram)":
        st.header("4. Ekstrak  Nomor HP dan Alamat (Instagram)")
    st.write("Melakukan Ekstraksi informasi nomor hp dan alamat yang ada pada bio profil akun instagram ke kolom nomor hp dan kolom alamat ")
    st.write("")
    st.subheader("Langkah 2: Upload Data")
    uploaded_file = st.file_uploader("Upload file hasil scraping instagram", type=['csv', 'xlsx', 'json'], key='m4')
    
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None:
            st.info(f"Wilayah yang dipilih: **{region_choice}**")
            
            target_col = st.selectbox("Pilih kolom berisi biografi profil instagram (alamat dan nomor hp):", df.columns.tolist())
            
            if st.button("Mulai Ekstrak Data"):
                with st.spinner('Sedang memproses data...'):
                    df['nomor_hp'] = df[target_col].apply(extract_phone_number)
                    # Mengirim region_choice yang dipilih di awal ke dalam fungsi
                    df['alamat_ig'] = df[target_col].apply(lambda x: extract_address_ig(x, region_choice))
                
                st.success(f"Proses Selesai! Detail jalan yang kosong otomatis diisi: {region_choice}")
                st.dataframe(df[[target_col, 'nomor_hp', 'alamat_ig']].head(10))
                
                excel_data = to_excel(df)
                st.download_button("📥 Download Hasil Ekstrak (XLSX)", data=excel_data, file_name=f"hasil_ekstrak_ig_{region_choice.lower().replace(' ', '_')}.xlsx")

    elif selected_menu == "5. Ekstrak Alamat (Google Maps)":
    st.header("5. Ekstrak Alamat Saja (Google Maps)")
    st.write("Melakukan ekstrak informasi alamat dari data scraping google Maps")
    st.write("Contoh: 6M64+C8Q, Jl. Sutan Sjahrir >> menjadi >> Jl. Sutan Sjahrir")
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

    

    elif selected_menu == "6. Visualisasi Peta & Convert excel to shp":
    st.header("6. Visualisasi Peta & Export Shapefile")
    st.write("Melakukan Visualisasi Peta dari data hasil scraping Google Maps dan bisa export ke format file shp (shapefile) untuk kebutuhan peta")
    
    uploaded_file = st.file_uploader("Upload file data spasial", type=['csv', 'xlsx', 'json'], key='m6')
    
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None:
            st.write(f"**Preview Data Spasial** ({len(df)} baris):")
            st.dataframe(df.head())
            st.write("---")
            
            all_columns = df.columns.tolist()
            
            col1, col2 = st.columns(2)
            with col1:
                lat_col = st.selectbox("Pilih kolom Latitude (Lintang):", all_columns, index=0)
            with col2:
                lon_col = st.selectbox("Pilih kolom Longitude (Bujur):", all_columns, index=1 if len(all_columns)>1 else 0)
            
            st.write("---")
            info_cols = st.multiselect("Pilih kolom yang ingin ditampilkan saat titik diklik (Popup Detail):", all_columns)
            
            if st.button("Render Peta Spasial"):
                map_df = df.copy()
                map_df['lat'] = pd.to_numeric(map_df[lat_col], errors='coerce')
                map_df['lon'] = pd.to_numeric(map_df[lon_col], errors='coerce')
                map_df = map_df.dropna(subset=['lat', 'lon'])
                
                if map_df.empty:
                    st.warning("Data koordinat tidak valid.")
                else:
                    st.success(f"Memetakan {len(map_df)} titik lokasi.")
                    
                    center_lat = map_df['lat'].mean()
                    center_lon = map_df['lon'].mean()
                    
                    m = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles=None)
                    
                    folium.TileLayer(
                        tiles='http://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}',
                        attr='Google',
                        name='Google Maps',
                        overlay=False,
                        control=True
                    ).add_to(m)
                    
                    for idx, row in map_df.iterrows():
                        popup_html = f"<div style='min-width: 200px; font-family: Arial;'>"
                        popup_html += f"<h4 style='margin-top: 0px; color: #FF7A00;'>Detail Info</h4>"
                        
                        if info_cols:
                            for col in info_cols:
                                popup_html += f"<b>{col}:</b> {row[col]}<br>"
                        else:
                            popup_html += f"<b>Lat:</b> {row['lat']}<br><b>Lon:</b> {row['lon']}"
                        
                        popup_html += "</div>"
                        
                        folium.CircleMarker(
                            location=[row['lat'], row['lon']],
                            radius=7, 
                            color='#FF7A00', 
                            fill=True,
                            fill_color='#FFB74D', 
                            fill_opacity=0.8,
                            weight=2,
                            popup=folium.Popup(popup_html, max_width=300),
                            tooltip="Klik untuk detail" 
                        ).add_to(m)
                    
                    st_folium(m, width=1000, height=600, returned_objects=[])

                    st.write("---")
                    shp_zip = to_shp_zip(map_df, 'lat', 'lon')
                    st.download_button(
                        label="🗺️ Download Shapefile (.zip)",
                        data=shp_zip,
                        file_name="peta_lokasi_shp.zip",
                        mime="application/zip"
                    )



    

    elif selected_menu == "7. Cek Info & Tipe Data":
    st.header("7. Cek Nama Kolom dan Tipe Datanya")
    uploaded_file = st.file_uploader("Upload file", type=['csv', 'xlsx', 'json'], key='m7')
    
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None:
            info_df = pd.DataFrame({
                "Nama Kolom": df.columns,
                "Tipe Data": df.dtypes.astype(str),
                "Missing Value (Kosong)": df.isnull().sum().values,
                "Terisi (Non-Null)": df.notnull().sum().values
            })
            
            col1, col2 = st.columns(2)
            col1.info(f"**Total Baris:** {df.shape[0]}")
            col2.info(f"**Total Kolom:** {df.shape[1]}")
            
            st.write("### Detail Struktur Tabel:")
            st.dataframe(info_df, use_container_width=True)

    

    elif selected_menu == "8. Edit/Hapus Data":
    st.header("8. Workspace Edit Data")
    uploaded_file = st.file_uploader("Upload file", type=['csv', 'xlsx', 'json'], key='m8')
    
    if uploaded_file:
        df = load_data(uploaded_file)
        
        if df is not None:
            if 'edit_df' not in st.session_state or st.session_state.get('last_uploaded') != uploaded_file.name:
                st.session_state['edit_df'] = df.copy()
                st.session_state['last_uploaded'] = uploaded_file.name
                
            st.write("---")
            
            with st.expander("✏️ Ganti Nama Kolom"):
                col1, col2 = st.columns(2)
                with col1:
                    old_col = st.selectbox("Pilih kolom:", st.session_state['edit_df'].columns, key="old_col")
                with col2:
                    new_col = st.text_input("Nama kolom baru:", value=old_col)
                    
                if st.button("Ubah Nama Kolom"):
                    if new_col and new_col != old_col:
                        st.session_state['edit_df'].rename(columns={old_col: new_col}, inplace=True)
                        st.success(f"Kolom berhasil diubah dari '{old_col}' menjadi '{new_col}'")
                        st.rerun()
            
            with st.expander("🗑️ Hapus Kolom (Drop Column)"):
                cols_to_drop = st.multiselect("Pilih kolom yang tidak digunakan:", st.session_state['edit_df'].columns)
                if st.button("Hapus Kolom Terpilih"):
                    if cols_to_drop:
                        st.session_state['edit_df'].drop(columns=cols_to_drop, inplace=True)
                        st.success(f"{len(cols_to_drop)} kolom berhasil dihapus.")
                        st.rerun()

            st.write("---")
            st.write("### 🔍 Filter & Editor Data Pintar")
            st.info("💡 **Tips:** Klik 2x pada cell tabel untuk mengedit teks. Centang kotak paling kiri lalu tekan **Delete** di keyboard untuk menghapus baris.")
            
            search_query = st.text_input("Ketik kata kunci untuk memfilter baris:")
            
            if search_query:
                mask = st.session_state['edit_df'].astype(str).apply(
                    lambda x: x.str.contains(search_query, case=False, na=False)
                ).any(axis=1)
                display_df = st.session_state['edit_df'][mask]
                st.caption(f"Menampilkan {len(display_df)} baris yang cocok dengan '{search_query}'.")
            else:
                display_df = st.session_state['edit_df']
            
            edited_df = st.data_editor(
                display_df,
                num_rows="dynamic",
                use_container_width=True,
                key="editor"
            )
            
            st.write("---")
            st.download_button(
                label="📥 Download Data Hasil Edit (XLSX)",
                data=to_excel(edited_df),
                file_name="data_hasil_edit.xlsx"
            )
