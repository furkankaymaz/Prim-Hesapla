# -*- coding: utf-8 -*-
#
# AFAD Deprem Tehlike Parametreleri Sorgulama Aracı (v2.0 - Nihai ve Çalışan Sürüm)
# =====================================================================================
# Bu araç, AFAD'ın insan kullanıcılara hizmet veren web sitesiyle (main.xhtml)
# bir tarayıcı gibi iletişim kurarak, altyapıdaki değişikliklerden etkilenmeyen,
# kararlı bir yöntemle deprem tehlike verilerini çeker.

import streamlit as st
import requests
import pandas as pd
import json

# AFAD'ın ana web uygulaması adresi. API'lar değişse de bu adres kararlıdır.
AFAD_TARGET_URL = "https://tdth.afad.gov.tr/TDTH/main.xhtml"

@st.cache_data(show_spinner="AFAD sunucusuna bağlanılıyor ve veriler işleniyor...")
def get_afad_hazard_data_stable(lat: float, lon: float) -> dict:
    """
    AFAD web uygulamasıyla tam bir tarayıcı (browser) gibi etkileşime girerek
    kararlı bir şekilde deprem tehlike verilerini alır.
    """
    try:
        # 1. Adım: Ana sayfaya bağlanarak gerekli oturum bilgilerini (session cookies) al.
        session = requests.Session()
        initial_response = session.get(AFAD_TARGET_URL, timeout=20)
        initial_response.raise_for_status()

        # JSF (JavaServer Faces) tarafından kullanılan ViewState değerini HTML'den çek.
        # Bu, sunucunun bizim kim olduğumuzu anlaması için gereklidir.
        if 'name="javax.faces.ViewState"' not in initial_response.text:
            raise ValueError("AFAD sayfasından gerekli ViewState anahtarı alınamadı. Site yapısı değişmiş olabilir.")
        
        view_state = initial_response.text.split('name="javax.faces.ViewState"')[1].split('value="')[1].split('"')[0]

        # 2. Adım: Koordinatları ve oturum bilgilerini içeren POST isteğini gönder.
        # Bu, haritaya tıklama eylemini simüle eder.
        form_data = {
            'javax.faces.partial.ajax': 'true',
            'javax.faces.source': 'j_idt16',
            'javax.faces.partial.execute': '@all',
            'javax.faces.partial.render': 'koordinat',
            'j_idt16': 'j_idt16',
            'j_idt16_coords': f'{lat},{lon}',
            'javax.faces.ViewState': view_state,
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Faces-Request': 'partial/ajax',
        }

        data_response = session.post(AFAD_TARGET_URL, data=form_data, headers=headers, timeout=20)
        data_response.raise_for_status()
        
        # 3. Adım: Dönen XML cevabından JSON verisini ayıkla.
        # Sunucu, sayfanın sadece güncellenecek kısmını XML formatında gönderir.
        if "<![CDATA[" in data_response.text:
            # CDATA bloğunun içindeki JSON verisini bulup ayıklıyoruz
            json_string = data_response.text.split('{"data":')[1].split('}]]>')[0]
            full_json_string = '{"data":' + json_string + '}'
            parsed_json = json.loads(full_json_string)
            return parsed_json['data']
        else:
            raise ValueError("AFAD'dan gelen yanıtta beklenen veri formatı bulunamadı.")

    except requests.exceptions.HTTPError as e:
        raise ConnectionError(f"AFAD sunucusuna ulaşıldı ancak bir HTTP hatası alındı (örn: 404, 503): {e}")
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"AFAD sunucusuna bağlanırken bir ağ hatası oluştu: {e}")
    except (ValueError, IndexError, KeyError) as e:
        raise ValueError(f"AFAD'dan gelen yanıt işlenirken bir hata oluştu. Sunucu yanıt formatı değişmiş olabilir: {e}")


def main():
    st.set_page_config(page_title="AFAD PGA Sorgulama", layout="centered")
    st.image("https://www.afad.gov.tr/kurumlar/afad.gov.tr/2-YUKLENEN/2logo/afad-logo.png", width=150)
    st.title("📍 AFAD Deprem Tehlike Parametreleri Sorgulama (v2.0)")
    st.markdown("AFAD'ın **güncel ve kararlı** web uygulamasıyla entegre çalışarak bilimsel parametreleri sorgular.")

    lat_default = 40.9906 # Kadıköy
    lon_default = 29.0271

    col1, col2 = st.columns(2)
    with col1:
        lat = st.number_input("Enlem (Latitude)", value=lat_default, format="%.6f")
    with col2:
        lon = st.number_input("Boylam (Longitude)", value=lon_default, format="%.6f")

    if st.button("Deprem Tehlikesini Sorgula", type="primary"):
        try:
            data = get_afad_hazard_data_stable(lat, lon)
            
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

        except (ConnectionError, ValueError, Exception) as e:
            st.error(f"Hata: {e}")

if __name__ == "__main__":
    main()
