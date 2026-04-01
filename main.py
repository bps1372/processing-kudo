elif menu == "4. Ekstrak No Telp & Alamat (Instagram)":
    st.header("4. Ekstrak Nomor HP dan Alamat (Instagram)")
    st.info("Menggunakan aturan regex bio Instagram. Jika tidak ditemukan detail jalan, alamat akan menggunakan wilayah default yang dipilih.")
    
    uploaded_file = st.file_uploader("Upload file", type=['csv', 'xlsx', 'json'], key='m4')
    
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None:
            st.write(f"**Preview Data Asli** ({len(df)} baris):")
            st.dataframe(df.head())
            st.write("---")
            
            # --- TAMBAHAN PILIHAN WILAYAH ---
            col_a, col_b = st.columns(2)
            with col_a:
                target_col = st.selectbox("Pilih kolom biografi/profil Instagram:", df.columns.tolist())
            with col_b:
                selected_region = st.selectbox(
                    "Pilih Wilayah Default (Jika jalan tidak ditemukan):", 
                    ("Kota Solok", "Kota Padang", "Kota Bukittinggi")
                )
            # -------------------------------

            if st.button("Ekstrak Data Instagram"):
                with st.spinner('Memproses ekstraksi data...'):
                    # Ekstrak nomor HP tetap seperti biasa
                    df['nomor_hp'] = df[target_col].apply(extract_phone_number)
                    
                    # Ekstrak alamat dengan membawa variabel selected_region
                    df['alamat_ig'] = df[target_col].apply(lambda x: extract_address_ig(x, selected_region))
                
                st.success(f"Ekstraksi Selesai dengan wilayah default: {selected_region}!")
                
                st.write("**Preview Hasil Ekstraksi:**")
                # Menampilkan kolom yang relevan saja untuk preview
                preview_cols = [target_col, 'nomor_hp', 'alamat_ig']
                st.dataframe(df[preview_cols].head(10))
                
                st.download_button(
                    label="📥 Download Hasil Ekstrak IG (XLSX)", 
                    data=to_excel(df), 
                    file_name=f"data_ig_{selected_region.lower().replace(' ','_')}.xlsx"
                )
