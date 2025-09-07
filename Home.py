# -*- coding: utf-8 -*-
#
# AFAD Deprem Tehlike Parametreleri Sorgulama Aracı (v3.0 - Selenium ile Kararlı Çözüm)
# =====================================================================================
# Bu araç, AFAD'ın JavaScript-yoğun web sitesiyle tam uyumlu çalışmak üzere,
# arka planda bir web tarayıcısını otomatize eden Selenium kütüphanesini kullanır.
# Bu yöntem, en kararlı ve güvenilir çözümdür.

import streamlit as st
import pandas as pd
import json
import time

# Gerekli Selenium kütüphaneleri
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# AFAD'ın ana web uygulaması adresi
AFAD_TARGET_URL = "https://tdth.afad.gov.tr/TDTH/main.xhtml"

@st.cache_data(show_spinner="Web tarayıcısı başlatılıyor ve AFAD sitesine bağlanılıyor...")
def get_afad_hazard_data_selenium(lat: float, lon: float) -> dict:
    """
    Selenium kullanarak AFAD web sitesinden kararlı bir şekilde deprem tehlike verilerini alır.
    """
    # Chrome'u arka planda (headless) çalıştırmak için ayarlar
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    # Chrome sürücüsünü otomatik olarak indirip kurar
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        # 1. Sayfaya git
        driver.get(AFAD_TARGET_URL)

        # 2. Koordinat giriş kutularının yüklenmesini bekle ve değerleri gir
        wait = WebDriverWait(driver, 20) # 20 saniye bekleme süresi
        lat_input = wait.until(EC.presence_of_element_located((By.ID, "enlem")))
        lon_input = driver.find_element(By.ID, "boylam")
        
        lat_input.clear()
        lat_input.send_keys(str(lat))
        
        lon_input.clear()
        lon_input.send_keys(str(lon))

        # 3. Sorgula butonuna tıkla
        query_button = driver.find_element(By.ID, "j_idt30")
        query_button.click()

        # 4. Sonuçların yüklenmesini bekle (PGA değeri görünür olana kadar)
        result_pga_element = wait.until(EC.visibility_of_element_located((By.ID, "pga475")))
        
        # 5. Sonuçları elementlerden oku
        pga_value = float(driver.find_element(By.ID, "pga475").text)
        pgv_value = float(driver.find_element(By.ID, "pgv475").text)
        ss_value = float(driver.find_element(By.ID, "ss475").text)
        s1_value = float(driver.find_element(By.ID, "s1475").text)

        # 6. Sonuçları standart formatımızda bir sözlük olarak döndür
        return {
            "enlem": lat,
            "boylam": lon,
            "pga475": pga_value,
            "pgv475": pgv_value,
            "ss475": ss_value,
            "s1475": s1_value,
        }

    finally:
        # Her durumda tarayıcıyı kapat
        driver.quit()

def main():
    st.set_page_config(page_title="AFAD PGA Sorgulama", layout="centered")
    st.image("https://www.afad.gov.tr/kurumlar/afad.gov.tr/2-YUKLENEN/2logo/afad-logo.png", width=150)
    st.title("📍 AFAD Deprem Tehlike Sorgulama (v3.0 - Kararlı Sürüm)")
    st.markdown("Bu araç, arka planda bir web tarayıcısı kullanarak AFAD'dan **güvenilir** şekilde veri çeker.")

    lat_default = 40.9906 # Kadıköy
    lon_default = 29.0271

    col1, col2 = st.columns(2)
    with col1:
        lat = st.number_input("Enlem (Latitude)", value=lat_default, format="%.6f")
    with col2:
        lon = st.number_input("Boylam (Longitude)", value=lon_default, format="%.6f")

    if st.button("Deprem Tehlikesini Sorgula", type="primary"):
        try:
            data = get_afad_hazard_data_selenium(lat, lon)
            
            st.success(f"**{data.get('enlem')}°, {data.get('boylam')}°** konumu için veriler başarıyla alındı.")
            pga_value = data.get("pga475")
            
            col_pga, col_pgv = st.columns(2)
            with col_pga:
                st.metric(label="PGA (Zirve Yer İvmesi - g)", value=f"{pga_value:.4f}")
            with col_pgv:
                st.metric(label="PGV (Zirve Yer Hızı - cm/s)", value=f"{data.get('pgv475'):.2f}")

            st.markdown("---")
            st.subheader("Spektral İvme Değerleri (DD-2 / 475 Yıl)")
            spectral_data = {
                "Parametre": ["Ss (Kısa Periyot)", "S1 (1 Saniye Periyot)"],
                "Değer (g)": [data.get("ss475"), data.get("s1475")]
            }
            df = pd.DataFrame(spectral_data)
            st.table(df.style.format({"Değer (g)": "{:.4f}"}))

            with st.expander("Tüm Ham Veriyi Görüntüle"):
                st.json(data)

        except Exception as e:
            st.error(f"Hata: {e}")
            st.info("Olası Çözüm: İnternet bağlantınızı kontrol edin. Hata devam ederse, AFAD sitesi geçici olarak hizmet dışı olabilir.")

if __name__ == "__main__":
    main()
