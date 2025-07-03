# File: 2_Analisis_Jenjang.py
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Analisis Beasiswa", layout="wide")

st.title("📊 Analisis dan Filter Beasiswa")

if 'scraped_data' not in st.session_state or st.session_state.scraped_data.empty:
    st.warning("Data belum tersedia. Silakan jalankan scraper di halaman 'Scraper Beasiswa' terlebih dahulu.")
    st.stop() 

df = st.session_state.scraped_data

# --- Bagian Filter Berdasarkan Jenjang ---
st.header("Filter Beasiswa Berdasarkan Jenjang")
all_degrees = set()
for s in df['Jenjang'].dropna():
    degrees_list = [degree.strip() for degree in s.split(',')]
    all_degrees.update(degrees_list)

if '' in all_degrees:
    all_degrees.remove('')

selected_degrees = st.multiselect(
    "Pilih Jenjang yang ingin ditampilkan:",
    options=sorted(list(all_degrees)),
    default=sorted(list(all_degrees)) if all_degrees else [] 
)

if selected_degrees:
    filtered_df = df[df['Jenjang'].str.contains('|'.join(selected_degrees), na=False)]
else:
    filtered_df = df if not all_degrees else pd.DataFrame(columns=df.columns)

st.write(f"Menampilkan {len(filtered_df)} dari {len(df)} beasiswa.")
st.dataframe(filtered_df)

st.header("Visualisasi Data")
col1, col2 = st.columns(2)

with col1:
    # Visualisasi Negara
    st.subheader("Sebaran Beasiswa per Negara")
    if not filtered_df.empty:
        country_counts = filtered_df['Negara'].value_counts().reset_index()
        country_counts.columns = ['Negara', 'Jumlah']
        
        fig_country = px.bar(
            country_counts.head(15), 
            x='Negara',
            y='Jumlah',
            title='Top 15 Negara Tujuan Beasiswa',
            labels={'Jumlah': 'Total Beasiswa'},
            color='Jumlah',
            color_continuous_scale=px.colors.sequential.Teal,
            text='Jumlah'
        )
        fig_country.update_layout(xaxis={'categoryorder':'total descending'})
        st.plotly_chart(fig_country, use_container_width=True)
    else:
        st.info("Tidak ada data untuk divisualisasikan.")

with col2:
    # Visualisasi Jenjang (berdasarkan data yang sudah difilter)
    st.subheader("Popularitas Jenjang Beasiswa")
    if not filtered_df.empty:
        # Hitung ulang frekuensi jenjang dari data yang sudah difilter
        degree_counts = pd.Series([degree.strip() for s in filtered_df['Jenjang'].dropna() for degree in s.split(',') if degree.strip()]).value_counts().reset_index()
        degree_counts.columns = ['Jenjang', 'Jumlah']

        fig_degree = px.pie(
            degree_counts.head(10), 
            names='Jenjang',
            values='Jumlah',
            title='Top 10 Jenjang Beasiswa Paling Populer',
            hole=0.3 
        )
        st.plotly_chart(fig_degree, use_container_width=True)
    else:
        st.info("Tidak ada data untuk divisualisasikan.")