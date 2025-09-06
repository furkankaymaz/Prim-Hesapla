# -*- coding: utf-8 -*-
#
# TariffEQ V2 Final – Hibrit Zeka Destekli Dinamik Risk Analiz Motoru
# =======================================================================
# Bu kod, kullanıcının girdilerinden ve dinamik internet araştırmalarından yola
# çıkarak her bir tesisi kendi bağlamında analiz eden, PD için yerel, BI için
# global standartları referans alan, AI ile hem sayısal parametreleri kalibre
# eden hem de spesifik raporlar üreten bütünleşik bir yapı sunar.

import streamlit as st
import pandas as pd
import plotly.express as px
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import json
import traceback

# --- AI İÇİN KORUMALI IMPORT VE GÜVENLİ KONFİGÜRASYON ---
_GEMINI_AVAILABLE = True  # Simülasyon için True, normalde False olmalı
try:
    # Gerçek kullanımda bu bölümdeki yorumları kaldırın
    # import google.generativeai as genai
    # if "GEMINI_API_KEY" in st.secrets:
    #     genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    #     _GEMINI_AVAILABLE = True
    # else:
    #     st.sidebar.warning("Gemini API anahtarı bulunamadı. AI özellikleri devre dışı.", icon="🔑")
    #     _GEMINI_AVAILABLE = False
    pass
except Exception:
    st.sidebar.error("Google AI kütüphanesi yüklenemedi. AI özellikleri devre dışı.", icon="🤖")
    _GEMINI_AVAILABLE = False

# --- TARİFE, ÇARPAN VERİLERİ VE SABİTLER (Orijinal yapı korundu) ---
TARIFE_RATES = {"Betonarme": [3.13, 2.63, 2.38, 1.94, 1.38, 1.06, 0.75], "Çelik": [3.13, 2.63, 2.38, 1.94, 1.38, 1.06, 0.75], "Yığma": [6.13, 5.56, 3.75, 2.00, 1.56, 1.24, 1.06], "Diğer": [6.13, 5.56, 3.75, 2.00, 1.56, 1.24, 1.06]}
KOAS_FACTORS = {"80/20": 1.0, "75/25": 0.9375, "70/30": 0.875, "65/35": 0.8125, "60/40": 0.75, "55/45": 0.6875, "50/50": 0.625, "45/55": 0.5625, "40/60": 0.5, "90/10": 1.125, "100/0": 1.25}
MUAFIYET_FACTORS = {2.0: 1.0, 3.0: 0.94, 4.0: 0.87, 5.0: 0.81, 10.0: 0.65, 1.5: 1.03, 1.0: 1.06, 0.5: 1.09, 0.1: 1.12}
RISK_ZONE_MAP = {1: 7, 2: 6, 3: 5, 4: 4, 5: 3, 6: 2, 7: 1} # Tarife bölgelerini slider'a uyumlu hale getirmek için

# --- V2 FİNAL DEĞİŞİKLİĞİ: BİRLEŞTİRİLMİŞ VE ZENGİNLEŞTİRİLMİŞ GİRDİ DATACLASS'İ ---
@dataclass
class ScenarioInputs:
    # TEMEL GİRDİLER
    tesis_tipi: str = "Endüstriyel Tesis"
    acik_adres: str = "Gebze Organize Sanayi Bölgesi, 12. Cadde No: 34, Kocaeli"
    yillik_brut_kar: int = 200_000_000
    azami_tazminat_suresi: int = 365
    bi_gun_muafiyeti: int = 21

    # GRANÜLER PD SİGORTA BEDELLERİ
    si_bina: int = 150_000_000
    si_makine: int = 250_000_000
    si_elektronik: int = 50_000_000
    si_stok: int = 50_000_000
    
    # ENDÜSTRİYEL TESİS GİRDİLERİ
    faaliyet_tanimi: str = "Otomotiv ana sanayiye metal şasi parçaları üreten bir tesis. Tesiste 5 adet 1000 tonluk hidrolik pres, CNC makineleri ve robotik kaynak hatları bulunmaktadır. Yüksek raflarda rulo sac malzeme stoklanmaktadır."
    yapi_turu: str = "Çelik"
    yonetmelik_donemi: str = "1998-2018 arası"
    yangin_patlama_potansiyeli: str = "Orta (Genel İmalat)"
    altyapi_yedekliligi: str = "Kısmi Yedekli (Jeneratör vb.)"
    yoke_sismik_korumasi: str = "Kısmi Koruma (Sadece kritik ekipman)"
    zemin_sinifi: str = "Bilmiyorum / AI Belirlesin"

# --- YARDIMCI FONKSİYONLAR ---
def money_format(x: float) -> str:
    """Sayıları binlik ayraçlı string formatına çevirir."""
    return f"{x:,.0f} ₺".replace(",", ".")

# --- HİBRİT ZEKA MOTORU VE HESAPLAMA ÇEKİRDEĞİ ---

@st.cache_data(show_spinner="AI, tesisiniz için özel araştırma yapıyor...")
def run_dynamic_ai_analysis(_inputs: ScenarioInputs) -> Dict:
    """
    Tüm AI ve hesaplama mantığını yöneten ana fonksiyon.
    1. Dinamik arama sorguları oluşturur.
    2. Web araması yapar (simüle edildi).
    3. AI Analisti ile parametreleri üretir.
    4. AI Raporlayıcı ile metin raporunu oluşturur.
    """
    if not _GEMINI_AVAILABLE: return {}
    
    # Adım 1 & 2: Sorgu oluşturma ve web araması (simülasyon)
    # queries = create_dynamic_search_queries(_inputs)
    search_results_summary = "Simülasyon: 2023 depremi, bölgedeki tesislerde en büyük BI kaybının enerji altyapısı ve hammadde lojistiğindeki aksamalardan kaynaklandığını gösterdi. Global çip krizi, otomasyon hatlarının yedek parça tedarik süresini uzatıyor. 1999 Kocaeli depreminde prefabrik yapıların bağlantı noktalarında zafiyetler görüldü."

    # Adım 3: AI Analisti'ni çalıştır ve parametreleri üret
    analyst_prompt = f"""
    Rol: Kıdemli deprem risk mühendisi ve global BI uzmanı. Görevin: Sana sunulan girdileri ve web arama sonuçlarını SENTEZLEYEREK, bir hasar hesaplama modeli için GEREKLİ olan sayısal çarpanları ve kilit riskleri bir JSON formatında üretmek.
    KULLANICI GİRDİLERİ: Adres: "{_inputs.acik_adres}", Faaliyet: "{_inputs.faaliyet_tanimi}", Yapı: {_inputs.yapi_turu} ({_inputs.yonetmelik_donemi}), Yangın Potansiyeli: {_inputs.yangin_patlama_potansiyeli}, Altyapı Yedekliliği: {_inputs.altyapi_yedekliligi}
    WEB ARAMA ÖZETİ: "{search_results_summary}"
    İSTENEN ÇIKTI (SADECE JSON): {{"pd_faktörleri": {{"zemin_etkisi_çarpanı": 1.2, "yoke_hasar_çarpanı": 1.4, "ffeq_potansiyel_çarpanı": 1.3, "stok_devrilme_risk_çarpanı": 1.7}}, "bi_faktörleri": {{"kritik_ekipman_duruş_çarpanı": 2.1, "altyapı_bağımlılık_süre_ekle_ay": 1, "tedarik_zinciri_gecikme_riski_ay": 4}}, "anahtar_riskler_rapor_için": ["PD RİSKİ: Faaliyet tanımındaki 'yüksek raf sistemleri', en büyük finansal kaybın devrilecek stoklardan kaynaklanacağını göstermektedir.", "BI RİSKİ (İÇSEL): 'Hidrolik preslerin' hassas kalibrasyonu, en ufak bir hizalanma sorununda bile aylarca sürecek bir iş kesintisi riskini beraberinde getirir.", "BI RİSKİ (DIŞSAL): Tesisin bulunduğu bölgenin limanlara olan bağımlılığı, deprem sonrası lojistik aksamalarda 4 aya varan hammadde tedarik sorunları yaşanabileceğini gösteriyor."], "analiz_referansı": "2023 Maraş ve 1999 Kocaeli Depremleri Sanayi Raporları"}}
    """
    # Gerçek API Çağrısı (simüle ediliyor)
    # model = genai.GenerativeModel('gemini-1.5-flash')
    # response = model.generate_content(analyst_prompt, generation_config={"response_mime_type": "application/json"})
    # ai_factors = json.loads(response.text)
    ai_factors = json.loads('{"pd_faktörleri": {"zemin_etkisi_çarpanı": 1.2, "yoke_hasar_çarpanı": 1.4, "ffeq_potansiyel_çarpanı": 1.3, "stok_devrilme_risk_çarpanı": 1.7}, "bi_faktörleri": {"kritik_ekipman_duruş_çarpanı": 2.1, "altyapı_bağımlılık_süre_ekle_ay": 1, "tedarik_zinciri_gecikme_riski_ay": 4}, "anahtar_riskler_rapor_için": ["PD RİSKİ: Faaliyet tanımındaki \'yüksek raf sistemleri\', en büyük finansal kaybın devrilecek stoklardan kaynaklanacağını göstermektedir.", "BI RİSKİ (İÇSEL): \'Hidrolik preslerin\' hassas kalibrasyonu, en ufak bir hizalanma sorununda bile aylarca sürecek bir iş kesintisi riskini beraberinde getirir.", "BI RİSKİ (DIŞSAL): Tesisin bulunduğu bölgenin limanlara olan bağımlılığı, deprem sonrası lojistik aksamalarda 4 aya varan hammadde tedarik sorunları yaşanabileceğini gösteriyor."], "analiz_referansı": "2023 Maraş ve 1999 Kocaeli Depremleri Sanayi Raporları"}')

    # Adım 4: AI Raporlayıcı'yı çalıştır
    reporter_prompt = f"""
    Rol: Kıdemli risk danışmanı. Görevin: Sana iletilen yapılandırılmış teknik bulguları, bir üst yöneticiye sunulacak şekilde, net ve profesyonel bir dilde "Teknik Risk Değerlendirmesi" metnine dönüştürmek.
    TEKNİK BULGULAR: Analiz Referansı: "{ai_factors.get('analiz_referansı', 'Genel Veriler')}", Anahtar Riskler: "{', '.join(ai_factors.get('anahtar_riskler_rapor_için', []))}"
    TALİMATLAR: Başlık "### 🧠 AI Teknik Risk Değerlendirmesi" olacak. Her anahtar riski 🧱 (PD) veya 📈 (BI) emojisi ile başlatıp, "Tespit:" ve "Potansiyel Etki:" başlıkları altında detaylandır. Sonunda "Öncelikli Aksiyon Alanları:" başlığı ile 1-2 konuyu özetle. Metnin sonunda küçük puntolarla analiz referansını belirt.
    """
    # Gerçek API Çağrısı (simüle ediliyor)
    # model = genai.GenerativeModel('gemini-1.5-flash')
    # final_report_text = model.generate_content(reporter_prompt).text
    final_report_text = """
    ### 🧠 AI Teknik Risk Değerlendirmesi
    🧱 **Tespit:** Faaliyet tanımınızdaki 'yüksek raf sistemleri', en büyük finansal kaybın bina çökmesinden ziyade, devrilecek stoklardan kaynaklanacağını göstermektedir.
    **Potansiyel Etki:** Özellikle stoklarınız ve hassas elektronik cihazlarınızda, binanın kendi yapısal hasar oranından daha yüksek bir hasar oranı beklenmelidir. Deprem sonrası yangın (FFEQ) riski, hasar gören elektrik tavaları ve proses hatları nedeniyle artmaktadır.

    📈 **Tespit:** Üretiminizin 'hidrolik preslere' olan yüksek bağımlılığı, en kritik iş kesintisi (BI) riskini oluşturmaktadır. Bu tür ağır ve hassas ekipmanların sarsıntı sonrası yeniden kalibrasyonu ve hizalanması son derece zaman alıcıdır.
    **Potansiyel Etki:** Tesiste onarım gerektirecek ciddi bir bina hasarı olmasa bile, sadece pres hatlarındaki hizalanma sorunu üretimin aylarca durmasına neden olabilir.

    📈 **Tespit:** Tesisinizin bulunduğu bölgenin limanlara olan bağımlılığı, dışsal bir BI riski yaratmaktadır. 
    **Potansiyel Etki:** 2023'te bölgede yaşanan lojistik aksamalar, bu tesiste de hammadde temininde 4 aya varan gecikmeler yaşanabileceğini göstermektedir. Bu durum, tesisin onarımı bitse bile üretime başlayamaması anlamına gelir.

    **Öncelikli Aksiyon Alanları:** Yapısal olmayan elemanların (raflar, borular, tavalar) sismik korumasının güçlendirilmesi ve kritik ekipmanlar için alternatifli bir iş sürekliliği planının detaylandırılması önerilir.
    
    <small>Bu analiz, '2023 Maraş ve 1999 Kocaeli Depremleri Sanayi Raporları' referans alınarak yapılmıştır.</small>
    """
    return {"ai_factors": ai_factors, "report_text": final_report_text}

def calculate_final_damages(s: ScenarioInputs, ai_factors: Dict) -> Dict:
    # Varlık bazlı ve AI kalibreli hasar hesaplama motoru (önceki cevaptaki gibi)
    if not ai_factors: return {}
    pd_f = ai_factors.get('pd_faktörleri', {})
    vulnerability_profile = {'bina': 1.0, 'makine': 1.5, 'elektronik': 2.0, 'stok': pd_f.get('stok_devrilme_risk_çarpanı', 1.7)}
    base_pd_ratio = 0.12 
    pd_factor = pd_f.get('zemin_etkisi_çarpanı', 1.0) * pd_f.get('yoke_hasar_çarpanı', 1.0)
    if "1998 öncesi" in s.yonetmelik_donemi: pd_factor *= 1.2
    
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

# --- POLİÇE VE PRİM ANALİZİ MODÜLÜ (Orijinal yapı korundu) ---
def get_allowed_options(si_pd: int) -> Tuple[List[str], List[float]]:
    koas_opts = list(KOAS_FACTORS.keys())[:9]; muaf_opts = list(MUAFIYET_FACTORS.keys())[:5]
    if si_pd > 3_500_000_000: koas_opts.extend(list(KOAS_FACTORS.keys())[9:]); muaf_opts.extend(list(MUAFIYET_FACTORS.keys())[5:])
    return koas_opts, muaf_opts

def calculate_premium(si: float, tarife_yapi_turu: str, rg: int, koas: str, muaf: float, is_bi: bool = False) -> float:
    base_rate = TARIFE_RATES.get(tarife_yapi_turu, TARIFE_RATES["Diğer"])[rg - 1]; prim_bedeli = si
    if is_bi: return (prim_bedeli * base_rate * 0.75) / 1000.0
    factor = KOAS_FACTORS.get(koas, 1.0) * MUAFIYET_FACTORS.get(muaf, 1.0)
    return (prim_bedeli * base_rate * factor) / 1000.0

def calculate_net_claim(si_pd: int, hasar_tutari: float, koas: str, muaf_pct: float) -> Dict[str, float]:
    muafiyet_tutari = si_pd * (muaf_pct / 100.0); muafiyet_sonrasi_hasar = max(0.0, hasar_tutari - muafiyet_tutari)
    sirket_pay_orani = float(koas.split('/')[0]) / 100.0; net_tazminat = muafiyet_sonrasi_hasar * sirket_pay_orani
    sigortalida_kalan = hasar_tutari - net_tazminat
    return {"net_tazminat": net_tazminat, "sigortalida_kalan": sigortalida_kalan}

# --- STREAMLIT ANA UYGULAMA AKIŞI ---
def main():
    st.set_page_config(page_title="TariffEQ V2 Final", layout="wide", page_icon="🏗️")
    
    if 's_inputs' not in st.session_state: st.session_state.s_inputs = ScenarioInputs()

    st.title("TariffEQ V2 – Hibrit Zeka Destekli Risk Analizi")
    st.markdown("Bu araç, tesisinize özel PD ve BI risklerini, yerel ve global verileri AI ile dinamik olarak analiz ederek modeller.")
    
    s_inputs = st.session_state.s_inputs

    with st.form(key="analysis_form"):
        st.header("1. Tesis Bilgilerini Giriniz (Endüstriyel Tesis)")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("🏭 Tesis ve Süreç")
            s_inputs.acik_adres = st.text_input("Açık Adres", value=s_inputs.acik_adres, placeholder="Örn: Gebze Organize Sanayi Bölgesi...")
            s_inputs.faaliyet_tanimi = st.text_area("Faaliyet Tanımı (En Kritik Bilgi)", value=s_inputs.faaliyet_tanimi, height=330, placeholder="Lütfen tesisinizi detaylıca anlatın...")
        with col2:
            st.subheader("🧱 Yapısal ve Finansal")
            s_inputs.si_bina = st.number_input("Bina Sigorta Bedeli", min_value=0, value=s_inputs.si_bina, step=1_000_000)
            s_inputs.si_makine = st.number_input("Makine-Ekipman Sigorta Bedeli", min_value=0, value=s_inputs.si_makine, step=1_000_000)
            s_inputs.si_elektronik = st.number_input("Elektronik Cihaz Sigorta Bedeli", min_value=0, value=s_inputs.si_elektronik, step=1_000_000)
            s_inputs.si_stok = st.number_input("Stok (Emtia) Sigorta Bedeli", min_value=0, value=s_inputs.si_stok, step=1_000_000)
            st.markdown("---")
            s_inputs.yillik_brut_kar = st.number_input("Yıllık Brüt Kâr (GP)", min_value=0, value=s_inputs.yillik_brut_kar, step=10_000_000)
        with col3:
            st.subheader("🔧 Risk Parametreleri")
            s_inputs.yapi_turu = st.selectbox("Yapı Taşıyıcı Sistemi", ["Çelik", "Betonarme", "Prefabrik Betonarme"], index=0)
            s_inputs.yonetmelik_donemi = st.selectbox("İnşa Yönetmeliği", ["2018 sonrası (Yeni)", "1998-2018 arası", "1998 öncesi (Eski)"], index=1)
            s_inputs.yangin_patlama_potansiyeli = st.selectbox("Yangın ve Patlama Potansiyeli", ["Düşük", "Orta", "Yüksek", "Çok Yüksek"], index=1)
            s_inputs.altyapi_yedekliligi = st.selectbox("Kritik Altyapı Yedekliliği", ["Yedeksiz", "Kısmi Yedekli", "Tam Yedekli"], index=1)
            s_inputs.yoke_sismik_korumasi = st.selectbox("Yapısal Olmayan Eleman Koruması", ["Koruma Yok", "Kısmi Koruma", "Tam Koruma"], index=1)
            s_inputs.zemin_sinifi = st.selectbox("Zemin Sınıfı (Biliyorsanız)", ["Bilmiyorum / AI Belirlesin", "ZA/ZB", "ZC", "ZD", "ZE"])
            s_inputs.azami_tazminat_suresi = st.selectbox("Azami Tazminat Süresi", [12, 18, 24], format_func=lambda x: f"{x} Ay") * 30
            s_inputs.bi_gun_muafiyeti = st.selectbox("BI Bekleme Süresi", [14, 21, 30, 45, 60], format_func=lambda x: f"{x} gün")
            
        form_submit_button = st.form_submit_button("🚀 Analizi Çalıştır", use_container_width=True, type="primary")

    if form_submit_button:
        st.session_state.form_submitted = True
        st.session_state.s_inputs = s_inputs
        
        analysis_results = run_dynamic_ai_analysis(s_inputs)
        damage_results = calculate_final_damages(s_inputs, analysis_results.get("ai_factors"))
        
        st.session_state.damage_results = damage_results
        st.session_state.final_report_text = analysis_results.get("report_text")
        st.session_state.s_inputs_cache = s_inputs

    if st.session_state.get('form_submitted', False):
        st.markdown("---"); st.header("2. Analiz Sonuçları")
        
        st.markdown(st.session_state.final_report_text, unsafe_allow_html=True)
        st.markdown("---")
        
        dr = st.session_state.damage_results
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Beklenen PD Hasar", money_format(dr['pd_hasar']), f"PML Oranı: {dr['pml_orani']:.2%}")
        m2.metric("Brüt BI Süresi", f"{dr['brut_bi_suresi_gun']} gün", "Tedarik zinciri dahil")
        m3.metric("Beklenen BI Hasar", money_format(dr['bi_hasar']))
        m4.metric("Toplam Risk Pozisyonu", money_format(dr['pd_hasar'] + dr['bi_hasar']))
        
        st.markdown("---"); st.header("3. Poliçe Optimizasyon Motoru")
        
        cached_inputs = st.session_state.s_inputs_cache
        toplam_si_pd = cached_inputs.si_bina + cached_inputs.si_makine + cached_inputs.si_elektronik + cached_inputs.si_stok
        
        # Tarife için risk bölgesi belirlenmeli (Örnek olarak 1. bölge alındı, normalde adresten çıkarılmalı)
        risk_bolgesi_tarife = 1 
        koas_opts, muaf_opts = get_allowed_options(toplam_si_pd)
        results_data = []
        for koas in koas_opts:
            for muaf in muaf_opts:
                prim_pd = calculate_premium(toplam_si_pd, cached_inputs.yapi_turu, risk_bolgesi_tarife, koas, muaf)
                prim_bi = calculate_premium(cached_inputs.yillik_brut_kar, cached_inputs.yapi_turu, risk_bolgesi_tarife, koas, muaf, is_bi=True)
                toplam_prim = prim_pd + prim_bi
                pd_claim = calculate_net_claim(toplam_si_pd, dr['pd_hasar'], koas, muaf)
                total_payout = pd_claim["net_tazminat"] + dr['bi_hasar']
                retained_risk = (dr['pd_hasar'] + dr['bi_hasar']) - total_payout
                verimlilik_skoru = (total_payout / toplam_prim if toplam_prim > 0 else 0) - (retained_risk / toplam_si_pd if toplam_si_pd > 0 else 0) * 5
                results_data.append({"Poliçe Yapısı": f"{koas} / {muaf}%", "Yıllık Toplam Prim": toplam_prim, "Toplam Net Tazminat": total_payout, "Sigortalıda Kalan Risk": retained_risk, "Verimlilik Skoru": verimlilik_skoru})
        
        df = pd.DataFrame(results_data).sort_values("Verimlilik Skoru", ascending=False).reset_index(drop=True)
        
        tab1, tab2 = st.tabs(["📈 Tablo Analizi", "📊 Görsel Analiz"])
        with tab1:
            st.dataframe(df.style.format({"Yıllık Toplam Prim": money_format, "Toplam Net Tazminat": money_format, "Sigortalıda Kalan Risk": money_format, "Verimlilik Skoru": "{:.2f}"}), use_container_width=True)
        with tab2:
            fig = px.scatter(df, x="Yıllık Toplam Prim", y="Sigortalıda Kalan Risk", color="Verimlilik Skoru", color_continuous_scale=px.colors.sequential.Viridis, hover_data=["Poliçe Yapısı", "Toplam Net Tazminat", "Verimlilik Skoru"], title="Poliçe Alternatifleri Maliyet-Risk Analizi")
            fig.update_traces(hovertemplate='<b>Poliçe:</b> %{customdata[0]}<br><b>Prim:</b> %{x:,.0f} ₺<br><b>Kalan Risk:</b> %{y:,.0f} ₺<br><b>Skor:</b> %{customdata[2]:.2f}')
            fig.update_layout(xaxis_title="Yıllık Toplam Prim", yaxis_title="Hasarda Şirketinizde Kalacak Risk", coloraxis_colorbar_title_text='Verimlilik')
            st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    if 'form_submitted' not in st.session_state: st.session_state.form_submitted = False
    main()
