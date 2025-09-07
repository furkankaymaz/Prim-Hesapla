# -*- coding: utf-8 -*-
#
# AFAD Deprem Tehlike Parametreleri Sorgulama Aracı (v1.2 - Çalışan & Onaylanmış Sürüm)
# =====================================================================================
# Bu basit Streamlit uygulaması, girilen enlem ve boylam
# bilgisi için AFAD'ın GÜNCEL ve ÇALIŞAN web servisinden (tdth.afad.gov.tr)
# DD-2 deprem yer hareketi düzeyi (475 yıl tekrarlanma periyodu)
# için deprem tehlike parametrelerini çeker.

import streamlit as st
import requests
import pandas as pd
import json

# AFAD'ın web servis adresi (YENİ VE ÇALIŞAN ADRES)
AFAD_API_URL = "https://tdth.afad.gov.tr/Home/GetGridParameters"

@st.cache_data(show_spinner="AFAD sunucusundan veriler alınıyor...")
def get_afad_hazard_data(lat: float, lon: float) -> dict:
    """
    Belirtilen enlem ve boylam için AFAD web servisinden deprem tehlike verilerini alır.
    """
    # PAYLOAD FORMATI DEĞİŞTİ (JSON YERİNE FORM-DATA)
    # Yeni servis, veriyi bu formatta bekliyor.
    payload = {
        'Lat': str(lat),
        'Lon': str(lon),
        'Dt': "DD-2"  # DD-2: 475 yilda bir olma olasiligi %10 olan deprem
    }

    # Servise POST isteği gönderilir.
    headers = {
        # Tarayıcı gibi davranmak için User-Agent eklemek genellikle iyi bir pratiktir.
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        # `json=payload` yerine `data=payload` KULLANILDI. Bu, verinin form-data olarak gönderilmesini sağlar.
        response = requests.post(AFAD_API_URL, headers=headers, data=payload, timeout=20)
        
        # İstek başarılıysa (hatalı durum kodları için istisna fırlatır)
        response.raise_for_status() 
        
        if response.text:
            # AFAD'ın yanıtı doğrudan JSON değil, içinde JSON olan bir string.
            # Bu nedenle önce stringi parse edip içindeki JSON'ı çıkarmamız gerekiyor.
            result = response.json()
            if result.get("Message") == "OK" and result.get("GridParameter"):
                 # JSON stringini tekrar parse ederek gerçek veri sözlüğüne ulaşıyoruz.
                return json.loads(result["GridParameter"])
            else:
                raise ValueError(f"AFAD'dan beklenen formatta veri alınamadı. Sunucu mesajı: {result.get('Message')}")
        else:
            raise ValueError("AFAD sunucusundan boş yanıt alındı.")
            
    except requests.exceptions.HTTPError as e:
        raise ConnectionError(f"AFAD sunucusuna ulaşıldı ancak bir HTTP hatası alındı (örn: 404, 500): {e}")
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"AFAD sunucusuna bağlanırken bir ağ hatası oluştu: {e}")


def main():
    st.set_page_config(page_title="AFAD PGA Sorgulama", layout="centered")
    st.image("https://www.afad.gov.tr/kurumlar/afad.gov.tr/2-YUKLENEN/2logo/afad-logo.png", width=150)
    st.title("📍 AFAD Deprem Tehlike Parametreleri Sorgulama (v1.2)")
    st.markdown("Girilen coğrafi koordinat için AFAD'ın **güncel** Deprem Tehlike Haritası'ndan bilimsel parametreleri sorgular.")

    # Örnek olarak İstanbul - Kadıköy koordinatları
    lat_default = 40.9906
    lon_default = 29.0271

    col1, col2 = st.columns(2)
    with col1:
        lat = st.number_input("Enlem (Latitude)", value=lat_default, format="%.6f")
    with col2:
        lon = st.number_input("Boylam (Longitude)", value=lon_default, format="%.6f")

    if st.button("Deprem Tehlikesini Sorgula", type="primary"):
        try:
            data = get_afad_hazard_data(lat, lon)
            
            st.success(f"**{lat}°, {lon}°** konumu için veriler başarıyla alındı.")

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

        except (ConnectionError, ValueError, Exception) as e:
            st.error(f"Hata: {e}")

if __name__ == "__main__":
    main()
