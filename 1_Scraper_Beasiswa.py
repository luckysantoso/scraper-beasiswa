import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import json
import platform  # <-- Impor baru
import traceback # <-- Impor baru

# =============================================================================
# Konfigurasi Selenium dengan Deteksi OS untuk Deployment
# =============================================================================
@st.cache_resource
def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    try:
        # --- LOGIKA UNTUK DEPLOYMENT ---
        if platform.system() == 'Linux':
            # Jika berjalan di Streamlit Cloud (Linux)
            st.info("Menjalankan di lingkungan Linux (Deployment). Menggunakan driver sistem.")
            service = Service(executable_path="/usr/bin/chromedriver")
        else:
            # Jika berjalan di Windows/Mac (Lokal)
            st.info("Menjalankan di lingkungan lokal. Menggunakan WebDriver Manager.")
            service = Service(ChromeDriverManager().install())

        driver = webdriver.Chrome(service=service, options=options)
        return driver
        
    except Exception as e:
        st.error(f"Gagal menginisialisasi WebDriver: {e}")
        st.code(traceback.format_exc()) # Menampilkan traceback lengkap untuk debug
        return None

# =============================================================================
# FUNGSI PARSING (Tidak Berubah)
# =============================================================================
def parse_scholarships(page_source):
    soup = BeautifulSoup(page_source, 'html.parser')
    scholarships = []
    cards = soup.find_all('a', attrs={'wire:snapshot': True})

    for card in cards:
        try:
            snapshot_str = card['wire:snapshot']
            snapshot_data = json.loads(snapshot_str)
            data = snapshot_data.get('data', {})
            
            if 'scholarship_id' not in data:
                continue

            title = data.get('name', 'N/A')
            link = data.get('url', '#')
            deadline = data.get('close_date', 'N/A')
            start_date = data.get('open_date', 'N/A')
            
            countries_list = data.get('countries', [[]])[0]
            country = ', '.join(countries_list) if countries_list else "N/A"
            
            degrees_list = data.get('degrees', [[]])[0]
            degrees = ', '.join(degrees_list) if degrees_list else "N/A"

            scholarships.append({
                'Nama Beasiswa': title,
                'Jenjang': degrees,
                'Negara': country,
                'Tanggal Mulai': start_date,
                'Deadline': deadline,
                'Link': link
            })
        except (json.JSONDecodeError, KeyError, IndexError, TypeError):
            continue
            
    return scholarships

# =============================================================================
# FUNGSI SCRAPING (Tidak Berubah)
# =============================================================================
def scrape_month_data(month_num, driver):
    base_url = "https://luarkampus.id/beasiswa"
    target_url = f"{base_url}?month={month_num}"
    driver.get(target_url)
    all_scholarships = []
    page_num = 1
    first_card_selector = "a[wire\\:snapshot]"
    progress_bar = st.progress(0, text="Memulai scraping...")
    status_text = st.empty()

    while True:
        status_text.text(f"Mencari data di halaman {page_num}...")
        try:
            wait = WebDriverWait(driver, 25)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, first_card_selector)))
            time.sleep(2) 
        except TimeoutException:
            if page_num == 1: st.info("Tidak ada data beasiswa yang ditemukan untuk bulan ini (timeout).")
            break
        page_source = driver.page_source
        new_scholarships = parse_scholarships(page_source)
        if new_scholarships:
            all_scholarships.extend(new_scholarships)
            status_text.text(f"Halaman {page_num} berhasil di-scrape. Total data: {len(all_scholarships)}")
        else:
            if page_num == 1: st.warning("Gagal mem-parsing kartu apa pun dari halaman.")
            break
        try:
            next_button_xpath = "//button[contains(., 'Selanjutnya') and not(@disabled)]"
            next_button = driver.find_element(By.XPATH, next_button_xpath)
            first_card_element = driver.find_element(By.CSS_SELECTOR, first_card_selector)
            driver.execute_script("arguments[0].click();", next_button)
            wait.until(EC.staleness_of(first_card_element))
            page_num += 1
            progress_bar.progress(min(page_num / 20, 1.0), text=f"Pindah ke halaman {page_num}...")
        except (NoSuchElementException, TimeoutException):
            status_text.text("Mencapai halaman terakhir. Selesai.")
            break
        except Exception as e:
            st.error(f"Error saat pindah halaman: {e}")
            break
    progress_bar.progress(1.0, text=f"Scraping selesai! Total {len(all_scholarships)} data ditemukan.")
    return all_scholarships

# =============================================================================
# Antarmuka Streamlit untuk Halaman Scraper (Tidak Berubah)
# =============================================================================
st.set_page_config(page_title="Scraper Beasiswa", layout="wide")

st.title("🚀 Scraper Beasiswa Luarkampus.id")
st.markdown("Gunakan halaman ini untuk mengambil data beasiswa terbaru. Setelah data diambil, pindah ke halaman **Analisis Jenjang** di sidebar untuk melihat visualisasi dan melakukan filter.")

month_map = {'Januari': 1, 'Februari': 2, 'Maret': 3, 'April': 4, 'Mei': 5, 'Juni': 6, 'Juli': 7, 'Agustus': 8, 'September': 9, 'Oktober': 10, 'November': 11, 'Desember': 12}
selected_months_names = st.multiselect('Pilih Bulan untuk di-Scrape:', options=list(month_map.keys()), default=['Januari'])

if 'scraped_data' not in st.session_state:
    st.session_state.scraped_data = pd.DataFrame()

if st.button('Mulai Scraping', type="primary"):
    if not selected_months_names:
        st.warning("Silakan pilih minimal satu bulan.")
    else:
        all_data = []
        with st.spinner("Mempersiapkan browser (Selenium)..."):
            driver = get_driver()
        
        if driver:
            st.success("Browser siap. Memulai proses scraping...")
            for month_name in selected_months_names:
                st.subheader(f"Scraping data untuk bulan: {month_name}")
                data = scrape_month_data(month_map[month_name], driver)
                if data:
                    all_data.extend(data)
            
            if all_data:
                df = pd.DataFrame(all_data)
                df_unique = df.drop_duplicates(subset=['Link'])
                st.session_state.scraped_data = df_unique
                st.success(f"Scraping selesai! {len(df_unique)} beasiswa unik ditemukan. Silakan cek halaman Analisis.")
            else:
                st.session_state.scraped_data = pd.DataFrame()
            
            st.info("Proses selesai.")
        else:
            st.error("Gagal memulai driver. Proses dibatalkan.")

if not st.session_state.scraped_data.empty:
    st.subheader("📝 Preview Data Hasil Scraping")
    st.dataframe(st.session_state.scraped_data.head())
    
    @st.cache_data
    def convert_df_to_csv(df_to_convert):
        return df_to_convert.to_csv(index=False).encode('utf-8')

    csv_data = convert_df_to_csv(st.session_state.scraped_data)
    st.download_button(
       label="📥 Unduh Semua Data (CSV)",
       data=csv_data,
       file_name=f"data_beasiswa_luarkampus.csv",
       mime="text/csv",
    )
else:
    st.info("Hasil scraping akan disimpan di sini dan dapat dianalisis di halaman lain.")