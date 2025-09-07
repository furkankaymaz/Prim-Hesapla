# -*- coding: utf-8 -*-
#
# AFAD Deprem Tehlike Parametreleri Sorgulama Aracı
# ==========================================================
# Bu basit Streamlit uygulaması, girilen enlem ve boylam
# bilgisi için AFAD'ın resmi web servisinden (tdth.afad.gov.tr)
# DD-2 deprem yer hareketi düzeyi (475 yıl tekrarlanma periyodu)
# için deprem tehlike parametrelerini çeker.

import streamlit as st
import requests
import pandas as pd

# AFAD'ın web servis adresi
AFAD_API_URL = "httpsd.afad.gov.tr/esSorgu/post른Sorgu"

@st.cache_data(show_spinner="AFAD sunucusundan veriler alınıyor...")
def get_afad_hazard_data(lat: float, lon: float) -> dict:
    """
    Belirtilen enlem ve boylam için AFAD web servisinden deprem tehlike verilerini alır.
    """
    # AFAD servisinin beklediği JSON formatında istek gövdesi oluşturulur.
    # DD-2: 475 yilda bir olma olasiligi %10 olan deprem (Standart Tasarim Depremi)
    payload = {
        "enlem": lat,
        "boylam": lon,
        "hesapTipi": "Ycs",
        "kaynakVs30": "Y",
        "vs30": 760, # Zemin sınıfı bilinmediğinde standart olarak 760 (ZC/kaya) kullanılır.
        "depremDuzeyi": "DD-2"
    }

    # Servise POST isteği gönderilir.
    headers = {
        'Content-Type': 'application/json',
    }

    try:
        # SSL sertifika doğrulaması (verify=False) bazı sistemlerde gerekebilir.
        # Genellikle kamu sitelerinin sertifikalarıyla ilgili sorunları aşmak için kullanılır.
        response = requests.post(AFAD_API_URL, headers=headers, json=payload, timeout=15, verify=False)
        
        # İstek başarılıysa ve dönen veri varsa
        if response.status_code == 200 and response.text:
            return response.json()
        else:
            raise ConnectionError(f"AFAD sunucusundan yanıt alınamadı. Durum Kodu: {response.status_code}")
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"AFAD sunucusuna bağlanırken bir ağ hatası oluştu: {e}")


def main():
    st.set_page_config(page_title="AFAD PGA Sorgulama", layout="centered")
    st.title("📍 AFAD Deprem Tehlike Parametreleri Sorgulama")
    st.markdown("Girilen coğrafi koordinat için AFAD'ın Deprem Tehlike Haritası'ndan bilimsel parametreleri sorgular.")

    # Örnek olarak İstanbul koordinatları
    lat_default = 41.0082
    lon_default = 28.9784

    col1, col2 = st.columns(2)
    with col1:
        lat = st.number_input("Enlem (Latitude)", value=lat_default, format="%.6f")
    with col2:
        lon = st.number_input("Boylam (Longitude)", value=lon_default, format="%.6f")

    if st.button("Deprem Tehlikesini Sorgula", type="primary"):
        try:
            data = get_afad_hazard_data(lat, lon)
            
            st.success(f"**{data.get('enlem')}°, {data.get('boylam')}°** konumu için veriler başarıyla alındı.")

            pga_value = data.get("pga475")
            
            col_pga, col_pgv = st.columns(2)
            with col_pga:
                st.metric(label="PGA (Zirve Yer İvmesi - g)", value=f"{pga_value:.4f}")
            with col_pgv:
                st.metric(label="PGV (Zirve Yer Hızı - cm/s)", value=f"{data.get('pgv475'):.2f}")

            st.markdown("---")
            st.subheader("Spektral İvme Değerleri (DD-2 / 475 Yıl)")

            # Verileri daha okunaklı bir DataFrame'e dönüştür
            spectral_data = {
                "Parametre": ["Ss (Kısa Periyot)", "S1 (1 Saniye Periyot)"],
                "Değer (g)": [data.get("ss475"), data.get("s1475")]
            }
            df = pd.DataFrame(spectral_data)
            st.table(df)

            with st.expander("Tüm Ham Veriyi Görüntüle"):
                st.json(data)

        except (ConnectionError, Exception) as e:
            st.error(f"Hata: {e}")

if __name__ == "__main__":
    main()
