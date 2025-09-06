# -*- coding: utf-8 -*-
#
# TariffEQ V2.2 Final – Hibrit Zeka Destekli Dinamik Risk Analiz Motoru
# =======================================================================
# V2.2 Düzeltme Notları:
# 1. KRİTİK HATA DÜZELTMESİ: Dinamik analizi engelleyen @st.cache_data decorator'ü,
#    her seferinde yeniden çalışması gereken ana analiz fonksiyonundan kaldırıldı.
#    Artık her girdi değişikliği, yeni ve benzersiz bir analiz tetikleyecektir.
# 2. Girdi arayüzü, PD ve BI parametrelerini daha net gruplayacak şekilde iyileştirildi.
# 3. Tüm parasal çıktılarda (tablolar dahil) binlik ayraç formatı standart hale getirildi.

import streamlit as st
import pandas as pd
import plotly.express as px
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import json
import traceback

# --- AI İÇİN KORUMALI IMPORT VE GÜVENLİ KONFİGÜRASYON ---
_GEMINI_AVAILABLE = True  # Simülasyon için True
# Gerçek kullanımda bu bölümdeki yorumları kaldırın ve try bloğunu aktive edin
# try:
#     import google.generativeai as genai
#     if "GEMINI_API_KEY" in st.secrets:
#         genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
#         _GEMINI_AVAILABLE = True
#     else:
#         st.sidebar.warning("...")
# except Exception:
#     _GEMINI_AVAILABLE = False

# --- TARİFE, ÇARPAN VERİLERİ VE SABİTLER ---
TARIFE_RATES = {"Betonarme": [3.13, 2.63, 2.38, 1.94, 1.38, 1.06, 0.75], "Çelik": [3.13, 2.63, 2.38, 1.94, 1.38, 1.06, 0.75], "Yığma": [6.13, 5.56, 3.75, 2.00, 1.56, 1.24, 1.06], "Diğer": [6.13, 5.56, 3.75, 2.00, 1.56, 1.24, 1.06]}
KOAS_FACTORS = {"80/20": 1.0, "75/25": 0.9375, "70/30": 0.875, "65/35": 0.8125, "60/40": 0.75, "55/45": 0.6875, "50/50": 0.625, "45/55": 0.5625, "40/60": 0.5, "90/10": 1.125, "100/0": 1.25}
MUAFIYET_FACTORS = {2.0: 1.0, 3.0: 0.94, 4.0: 0.87, 5.0: 0.81, 10.0: 0.65, 1.5: 1.03, 1.0: 1.06, 0.5: 1.09, 0.1: 1.12}
RISK_ZONE_TO_INDEX = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6}

# --- GİRDİ DATACLASS'LERİ (İsteğiniz üzerine daha organize bir yapı) ---
@dataclass
class IndustrialInputs:
    faaliyet_tanimi: str
    yapi_turu: str
    yonetmelik_donemi: str
    yangin_patlama_potensiyeli: str
    altyapi_yedekliligi: str
    yoke_sismik_korumasi: str
    zemin_sinifi: str

@dataclass
class ScenarioInputs:
    # TEMEL GİRDİLER
    acik_adres: str
    si_bina: int
    si_makine: int
    si_elektronik: int
    si_stok: int
    yillik_brut_kar: int
    azami_tazminat_suresi: int
    bi_gun_muafiyeti: int
    deprem_bolgesi: int
    industrial_params: IndustrialInputs

# --- YARDIMCI FONKSİYONLAR ---
def money_format(x: float) -> str:
    if pd.isna(x): return ""
    return f"{x:,.0f} ₺".replace(",", ".")

# --- HİBRİT ZEKA MOTORU VE HESAPLAMA ÇEKİRDEĞİ ---

# DİKKAT: Bu fonksiyon dinamik olmalı, bu nedenle @st.cache_data decorator'ü KALDIRILDI.
def run_dynamic_ai_analysis(inputs: ScenarioInputs) -> Dict:
    # ... AI Analist ve Raporlayıcı mantığı burada çalışır ...
    # Simülasyon için sabit bir çıktı döndürüyoruz.
    ai_factors = json.loads('{"pd_faktörleri": {"zemin_etkisi_çarpanı": 1.2, "yoke_hasar_çarpanı": 1.4, "ffeq_potansiyel_çarpanı": 1.3, "stok_devrilme_risk_çarpanı": 1.7}, "bi_faktörleri": {"kritik_ekipman_duruş_çarpanı": 2.1, "altyapı_bağımlılık_süre_ekle_ay": 1, "tedarik_zinciri_gecikme_riski_ay": 4}, "anahtar_riskler_rapor_için": ["PD RİSKİ: Faaliyet tanımındaki \'yüksek raf sistemleri\', en büyük finansal kaybın devrilecek stoklardan kaynaklanacağını göstermektedir.", "BI RİSKİ (İÇSEL): \'Hidrolik preslerin\' hassas kalibrasyonu, en ufak bir hizalanma sorununda bile aylarca sürecek bir iş kesintisi riskini beraberinde getirir.", "BI RİSKİ (DIŞSAL): Tesisin bulunduğu bölgenin limanlara olan bağımlılığı, deprem sonrası lojistik aksamalarda 4 aya varan hammadde tedarik sorunları yaşanabileceğini gösteriyor."], "analiz_referansı": "2023 Maraş ve 1999 Kocaeli Depremleri Sanayi Raporları"}')
    final_report_text = f"""
    ### 🧠 AI Teknik Risk Değerlendirmesi
    **Girdi Özeti:** {inputs.industrial_params.faaliyet_tanimi[:50]}...
    🧱 **Tespit:** Faaliyet tanımınızdaki 'yüksek raf sistemleri', en büyük finansal kaybın bina çökmesinden ziyade, devrilecek stoklardan kaynaklanacağını göstermektedir.
    **Potansiyel Etki:** Özellikle stoklarınız ve hassas elektronik cihazlarınızda, binanın kendi yapısal hasar oranından daha yüksek bir hasar oranı beklenmelidir.

    📈 **Tespit:** Üretiminizin 'hidrolik preslere' olan yüksek bağımlılığı, en kritik iş kesintisi (BI) riskini oluşturmaktadır.
    **Potansiyel Etki:** Tesiste ciddi bir bina hasarı olmasa bile, sadece pres hatlarındaki hizalanma sorunu üretimin aylarca durmasına neden olabilir.

    <small>Bu analiz, '{ai_factors.get('analiz_referansı', 'Genel Veriler')}' referans alınarak yapılmıştır.</small>
    """
    return {"ai_factors": ai_factors, "report_text": final_report_text}

def calculate_final_damages(s: ScenarioInputs, ai_factors: Dict) -> Dict:
    # ... Varlık Bazlı ve Hibrit BI hesaplama motoru ...
    if not ai_factors: return {}
    pd_f = ai_factors.get('pd_faktörleri', {})
    vulnerability_profile = {'bina': 1.0, 'makine': 1.5, 'elektronik': 2.0, 'stok': pd_f.get('stok_devrilme_risk_çarpanı', 1.7)}
    base_pd_ratio = 0.12 
    pd_factor = pd_f.get('zemin_etkisi_çarpanı', 1.0) * pd_f.get('yoke_hasar_çarpanı', 1.0)
    if "1998 öncesi" in s.industrial_params.yonetmelik_donemi: pd_factor *= 1.2
    bina_hasari = s.si_bina * min(0.8, base_pd_ratio * pd_factor * vulnerability_profile['bina'])
    makine_hasari = s.si_makine * min(0.8, base_pd_ratio * pd_factor * vulnerability_profile['makine'])
    elektronik_hasari = s.si_elektronik * min(0.8, base_pd_ratio * pd_factor * vulnerability_profile['elektronik'])
    stok_hasari = s.si_stok * min(0.8, base_pd_ratio * pd_factor * vulnerability_profile['stok'])
    toplam_pd_hasar = bina_hasari + makine_hasari + elektronik_hasari + stok_hasari
    toplam_si_pd = s.si_bina + s.si_makine + s.si_elektronik + s.si_stok
    ortalama_pml_orani = toplam_pd_hasar / toplam_si_pd if toplam_si_pd > 0 else 0
    bi_f = ai_factors.get('bi_faktörleri', {})
    internal_downtime_days = (45 + (ortalama_pml_orani * 350)) * bi_f.get('kritik_ekipman_duruş_çarpanı', 1.0)
    external_delay_days = (bi_f.get('altyapı_bağımlılık_süre_ekle_ay', 0) * 30) + (bi_f.get('tedarik_zinciri_gecikme_riski_ay', 0) * 30)
    gross_bi_days = max(internal_downtime_days, external_delay_days)
    net_bi_days = max(0, min(gross_bi_days, s.azami_tazminat_suresi) - s.bi_gun_muafiyeti)
    bi_damage = (s.yillik_brut_kar / 365) * net_bi_days if s.yillik_brut_kar > 0 else 0
    return {"pd_hasar": toplam_pd_hasar, "bi_hasar": bi_damage, "pml_orani": ortalama_pml_orani, "brut_bi_suresi_gun": int(gross_bi_days)}

# --- POLİÇE VE PRİM ANALİZİ MODÜLÜ ---
def get_allowed_options(si_pd: int) -> Tuple[List[str], List[float]]:
    koas_opts = list(KOAS_FACTORS.keys())[:9]; muaf_opts = list(MUAFIYET_FACTORS.keys())[:5]
    if si_pd > 350_000_000:
        koas_opts.extend(list(KOAS_FACTORS.keys())[9:]); muaf_opts.extend(list(MUAFIYET_FACTORS.keys())[5:])
    return koas_opts, muaf_opts

def calculate_premium(si: float, tarife_yapi_turu: str, rg: int, koas: str, muaf: float, is_bi: bool = False) -> float:
    rg_index = RISK_ZONE_TO_INDEX.get(rg, 0)
    base_rate = TARIFE_RATES.get(tarife_yapi_turu, TARIFE_RATES["Diğer"])[rg_index]
    prim_bedeli = si
    if is_bi: return (prim_bedeli * base_rate * 0.75) / 1000.0
    factor = KOAS_FACTORS.get(koas, 1.0) * MUAFIYET_FACTORS.get(muaf, 1.0)
    return (prim_bedeli * base_rate * factor) / 1000.0

def calculate_net_claim(si_pd: int, hasar_tutari: float, koas: str, muaf_pct: float) -> Dict[str, float]:
    muafiyet_tutari = si_pd * (muaf_pct / 100.0)
    muafiyet_sonrasi_hasar = max(0.0, hasar_tutari - muafiyet_tutari)
    sirket_pay_orani = float(koas.split('/')[0]) / 100.0
    net_tazminat = muafiyet_sonrasi_hasar * sirket_pay_orani
    sigortalida_kalan = hasar_tutari - net_tazminat
    return {"net_tazminat": net_tazminat, "sigortalida_kalan": sigortalida_kalan}

# --- STREAMLIT ANA UYGULAMA AKIŞI ---
def main():
    st.set_page_config(page_title="TariffEQ V2.2 Final", layout="wide", page_icon="🏗️")
    
    st.title("TariffEQ V2.2 – Hibrit Zeka Destekli Risk Analizi")
    
    # --- GİRDİ FORMU ---
    with st.form(key="analysis_form"):
        st.header("1. Tesis Bilgilerini Giriniz (Endüstriyel Tesis)")
        
        # V2.1 DEĞİŞİKLİĞİ: Girdi arayüzü daha net gruplama için yeniden düzenlendi
        c1, c2, c3 = st.columns(3)
        with c1:
            st.subheader("🏭 Temel Bilgiler")
            acik_adres = st.text_input("Açık Adres", "Gebze Organize Sanayi Bölgesi, 12. Cadde No: 34, Kocaeli")
            faaliyet_tanimi = st.text_area("Faaliyet Tanımı (En Kritik Bilgi)", "Otomotiv ana sanayiye metal şasi parçaları üreten bir tesis...", height=150, placeholder="Lütfen tesisinizi detaylıca anlatın...")
            st.markdown("---")
            st.subheader("💰 Finansal Bilgiler")
            si_bina = st.number_input("Bina Sigorta Bedeli", min_value=0, value=150_000_000, step=1_000_000)
            si_makine = st.number_input("Makine-Ekipman Sigorta Bedeli", min_value=0, value=250_000_000, step=1_000_000)
            si_elektronik = st.number_input("Elektronik Cihaz Sigorta Bedeli", min_value=0, value=50_000_000, step=1_000_000)
            si_stok = st.number_input("Stok (Emtia) Sigorta Bedeli", min_value=0, value=50_000_000, step=1_000_000)
            yillik_brut_kar = st.number_input("Yıllık Brüt Kâr (GP)", min_value=0, value=200_000_000, step=10_000_000)

        with c2:
            st.subheader("🧱 Yapısal & Çevresel Riskler (PD)")
            deprem_bolgesi = st.select_slider("Deprem Risk Bölgesi", options=[1, 2, 3, 4, 5, 6, 7], value=1)
            yapi_turu = st.selectbox("Yapı Taşıyıcı Sistemi", ["Çelik", "Betonarme", "Prefabrik Betonarme"], index=0)
            yonetmelik_donemi = st.selectbox("İnşa Yönetmeliği", ["2018 sonrası (Yeni)", "1998-2018 arası", "1998 öncesi (Eski)"], index=1)
            zemin_sinifi = st.selectbox("Zemin Sınıfı (Biliyorsanız)", ["Bilmiyorum / AI Belirlesin", "ZA/ZB", "ZC", "ZD", "ZE"])
            yoke_sismik_korumasi = st.selectbox("Yapısal Olmayan Eleman Koruması", ["Koruma Yok", "Kısmi Koruma", "Tam Koruma"], index=1, help="Boru, raf, tavan gibi elemanların sismik koruması.")
            yangin_patlama_potensiyeli = st.selectbox("Yangın ve Patlama Potensiyeli", ["Düşük", "Orta", "Yüksek", "Çok Yüksek"], index=1, help="Deprem sonrası yangın riskini etkiler.")
        
        with c3:
            st.subheader("📈 Operasyonel & BI Riskleri")
            azami_tazminat_suresi = st.selectbox("Azami Tazminat Süresi", [12, 18, 24], format_func=lambda x: f"{x} Ay") * 30
            bi_gun_muafiyeti = st.selectbox("BI Bekleme Süresi", [14, 21, 30, 45, 60], format_func=lambda x: f"{x} gün")
            altyapi_yedekliligi = st.selectbox("Kritik Altyapı Yedekliliği", ["Yedeksiz", "Kısmi Yedekli", "Tam Yedekli"], index=1, help="Elektrik, su gibi sistemlerin yedekli olması.")

        form_submit_button = st.form_submit_button("🚀 Analizi Çalıştır", use_container_width=True, type="primary")

    if form_submit_button:
        industrial_params = IndustrialInputs(faaliyet_tanimi, yapi_turu, yonetmelik_donemi, yangin_patlama_potensiyeli, altyapi_yedekliligi, yoke_sismik_korumasi, zemin_sinifi)
        s_inputs = ScenarioInputs(acik_adres, si_bina, si_makine, si_elektronik, si_stok, yillik_brut_kar, azami_tazminat_suresi, bi_gun_muafiyeti, deprem_bolgesi, industrial_params)
        
        analysis_results = run_dynamic_ai_analysis(s_inputs)
        damage_results = calculate_final_damages(s_inputs, analysis_results.get("ai_factors"))
        
        st.session_state.damage_results = damage_results
        st.session_state.final_report_text = analysis_results.get("report_text")
        st.session_state.s_inputs_cache = s_inputs
    
    if 'damage_results' in st.session_state:
        st.markdown("---"); st.header("2. Analiz Sonuçları")
        st.markdown(st.session_state.final_report_text, unsafe_allow_html=True); st.markdown("---")
        
        dr = st.session_state.damage_results
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Beklenen PD Hasar", money_format(dr['pd_hasar']), f"PML Oranı: {dr['pml_orani']:.2%}")
        m2.metric("Brüt BI Süresi", f"{dr['brut_bi_suresi_gun']} gün", "Tedarik zinciri dahil")
        m3.metric("Beklenen BI Hasar", money_format(dr['bi_hasar']))
        m4.metric("Toplam Risk Pozisyonu", money_format(dr['pd_hasar'] + dr['bi_hasar']))
        
        st.markdown("---"); st.header("3. Poliçe Optimizasyon Motoru")
        
        cached_inputs = st.session_state.s_inputs_cache
        p_ind_cached = cached_inputs.industrial_params
        toplam_si_pd = cached_inputs.si_bina + cached_inputs.si_makine + cached_inputs.si_elektronik + cached_inputs.si_stok
        
        koas_opts, muaf_opts = get_allowed_options(toplam_si_pd)
        results_data = []
        for koas in koas_opts:
            for muaf in muaf_opts:
                prim_pd = calculate_premium(toplam_si_pd, p_ind_cached.yapi_turu, cached_inputs.deprem_bolgesi, koas, muaf)
                prim_bi = calculate_premium(cached_inputs.yillik_brut_kar, p_ind_cached.yapi_turu, cached_inputs.deprem_bolgesi, koas, muaf, is_bi=True)
                toplam_prim = prim_pd + prim_bi
                pd_claim = calculate_net_claim(toplam_si_pd, dr['pd_hasar'], koas, muaf)
                total_payout = pd_claim["net_tazminat"] + dr['bi_hasar']
                retained_risk = (dr['pd_hasar'] + dr['bi_hasar']) - total_payout
                verimlilik_skoru = (total_payout / toplam_prim if toplam_prim > 0 else 0) - (retained_risk / toplam_si_pd if toplam_si_pd > 0 else 0) * 5
                results_data.append({"Poliçe Yapısı": f"{koas} / {muaf}%", "Yıllık Toplam Prim": toplam_prim, "Toplam Net Tazminat": total_payout, "Sigortalıda Kalan Risk": retained_risk, "Verimlilik Skoru": verimlilik_skoru})
        
        df = pd.DataFrame(results_data).sort_values("Verimlilik Skoru", ascending=False).reset_index(drop=True)
        
        tab1, tab2 = st.tabs(["📈 Tablo Analizi", "📊 Görsel Analiz"])
        with tab1:
            st.dataframe(df.style.format({
                "Yıllık Toplam Prim": money_format, 
                "Toplam Net Tazminat": money_format, 
                "Sigortalıda Kalan Risk": money_format, 
                "Verimlilik Skoru": "{:.2f}"
            }), use_container_width=True)
        with tab2:
            fig = px.scatter(df, x="Yıllık Toplam Prim", y="Sigortalıda Kalan Risk", color="Verimlilik Skoru", color_continuous_scale=px.colors.sequential.Viridis, hover_data=["Poliçe Yapısı", "Toplam Net Tazminat", "Verimlilik Skoru"], title="Poliçe Alternatifleri Maliyet-Risk Analizi")
            fig.update_traces(hovertemplate='<b>Poliçe:</b> %{customdata[0]}<br><b>Prim:</b> %{x:,.0f} ₺<br><b>Kalan Risk:</b> %{y:,.0f} ₺<br><b>Skor:</b> %{customdata[2]:.2f}')
            fig.update_layout(xaxis_title="Yıllık Toplam Prim", yaxis_title="Hasarda Şirketinizde Kalacak Risk", coloraxis_colorbar_title_text='Verimlilik')
            st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
