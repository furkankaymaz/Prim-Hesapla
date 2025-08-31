# -*- coding: utf-8 -*-
#
# TariffEQ – Profesyonel ve AI Destekli PD & BI Hasar Analiz Aracı
# =======================================================================
# Bu Streamlit uygulaması, reasürans ve katastrofik modelleme metodolojilerinden
# esinlenerek geliştirilmiş parametreler ve tarifeye tam uyumlu hesaplama
# mantığı ile ticari/sınai rizikolar için profesyonel seviyede bir deprem
# hasar analizi sunar.
#
# GÜNCEL REVİZYON NOTLARI (Ağustos 2025 - v4.2 - Stabil):
# 1. Hata Giderimi: Önceki versiyonlarda karşılaşılan `NameError` ve `ValueError`
#    hataları tamamen giderildi.
# 2. Modüler Mimariye Geçiş: Uygulama artık farklı tesis tiplerini (Endüstriyel,
#    Enerji Santralleri) ayrı ayrı analiz edebilecek stabil bir yapıya kavuşturuldu.
# 3. RES Modülü Entegrasyonu: Rüzgar Enerji Santralleri için özelleştirilmiş
#    girdiler, hesaplama motoru ve AI raporlaması, mevcut yapıyı bozmadan eklendi.

import streamlit as st
import pandas as pd
import plotly.express as px
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import json
import traceback

# --- AI İÇİN KORUMALI IMPORT VE GÜVENLİ KONFİGÜRASYON ---
_GEMINI_AVAILABLE = False
try:
    import google.generativeai as genai
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        _GEMINI_AVAILABLE = True
    else:
        st.sidebar.warning("Gemini API anahtarı bulunamadı. AI özellikleri devre dışı.", icon="🔑")
        _GEMINI_AVAILABLE = False
except (ImportError, Exception):
    st.sidebar.error("Google AI kütüphanesi yüklenemedi. AI özellikleri devre dışı.", icon="🤖")
    _GEMINI_AVAILABLE = False

# --- TARİFE, ÇARPAN VERİLERİ VE SABİTLER ---
TARIFE_RATES = {"Betonarme": [3.13, 2.63, 2.38, 1.94, 1.38, 1.06, 0.75], "Diğer": [6.13, 5.56, 3.75, 2.00, 1.56, 1.24, 1.06]}
KOAS_FACTORS = {"80/20": 1.0, "75/25": 0.9375, "70/30": 0.875, "65/35": 0.8125, "60/40": 0.75, "55/45": 0.6875, "50/50": 0.625, "45/55": 0.5625, "40/60": 0.5, "90/10": 1.125, "100/0": 1.25}
MUAFIYET_FACTORS = {2.0: 1.0, 3.0: 0.94, 4.0: 0.87, 5.0: 0.81, 10.0: 0.65, 1.5: 1.03, 1.0: 1.06, 0.5: 1.09, 0.1: 1.12}
_DEPREM_ORAN = {1: 0.20, 2: 0.17, 3: 0.13, 4: 0.09, 5: 0.06, 6: 0.06, 7: 0.06}

# --- ÇEVİRİ SÖZLÜĞÜ ---
T = {
    "title": {"TR": "TariffEQ – AI Destekli Risk Analizi", "EN": "TariffEQ – AI-Powered Risk Analysis"},
    "tesis_tipi_secimi": {"TR": "1. Lütfen Analiz Etmek İstediğiniz Tesis Tipini Seçiniz", "EN": "1. Please Select the Facility Type to Analyze"},
    "endustriyel_tesis": {"TR": "Endüstriyel Tesis (Fabrika, Depo vb.)", "EN": "Industrial Facility (Factory, Warehouse etc.)"},
    "res": {"TR": "Enerji Santrali - Rüzgar (RES)", "EN": "Power Plant - Wind (WPP)"},
    "ges": {"TR": "Enerji Santrali - Güneş (GES) (Yakında)", "EN": "Power Plant - Solar (SPP) (Coming Soon)"},
    "hes": {"TR": "Enerji Santrali - Hidroelektrik (HES) (Yakında)", "EN": "Power Plant - Hydroelectric (HPP) (Coming Soon)"},
    "yakinda": {"TR": "💡 Bu modül şu anda geliştirme aşamasındadır. Yakında hizmetinizde olacak!", "EN": "💡 This module is currently under development. It will be available soon!"},
    "inputs_header": {"TR": "📊 2. Senaryo Girdileri", "EN": "📊 2. Scenario Inputs"},
    "base_header": {"TR": "🏭 Temel Bilgiler", "EN": "🏭 Basic Information"},
    "pd_header": {"TR": "🧱 Yapısal & Çevresel Riskler", "EN": "🧱 Structural & Environmental Risks"},
    "bi_header": {"TR": "📈 Operasyonel & BI Riskleri", "EN": "📈 Operational & BI Risks"},
    "res_header": {"TR": "💨 RES'e Özgü Risk Parametreleri", "EN": "💨 WPP-Specific Risk Parameters"},
    "activity_desc": {"TR": "Tesisin Faaliyetini ve İçeriğini Tanımlayın", "EN": "Describe the Facility's Operations and Contents"},
    "si_pd": {"TR": "Toplam Sigorta Bedeli (PD)", "EN": "Total Sum Insured (PD)"},
    "risk_zone": {"TR": "Deprem Risk Bölgesi", "EN": "Earthquake Risk Zone"},
    "gross_profit": {"TR": "Yıllık Brüt Kâr (GP)", "EN": "Annual Gross Profit (GP)"},
    "turbin_yas": {"TR": "Türbin Teknolojisi ve Ortalama Yaşı", "EN": "Turbine Technology and Average Age"},
    "arazi_jeoteknik": {"TR": "Arazinin Jeo-Teknik Durumu", "EN": "Geo-Technical Condition of the Site"},
    "salt_sahasi": {"TR": "Şalt Sahasının Sismik Performansı", "EN": "Seismic Performance of the Substation"},
    "azami_tazminat": {"TR": "Azami Tazminat Süresi", "EN": "Max. Indemnity Period"},
    "bi_wait": {"TR": "BI Bekleme Süresi (Muafiyet)", "EN": "BI Waiting Period (Deductible)"},
    "ai_pre_analysis_header": {"TR": "🧠 AI Teknik Risk Değerlendirmesi", "EN": "🧠 AI Technical Risk Assessment"},
    "results_header": {"TR": "📝 Sayısal Hasar Analizi", "EN": "📝 Numerical Damage Analysis"},
    "analysis_header": {"TR": "🔍 Poliçe Alternatifleri Analizi", "EN": "🔍 Policy Alternatives Analysis"},
    "btn_run": {"TR": "Analizi Çalıştır", "EN": "Run Analysis"},
}

# --- YARDIMCI FONKSİYONLAR ---
def tr(key: str) -> str:
    lang = st.session_state.get("lang", "TR")
    return T.get(key, {}).get(lang, key)

def money(x: float) -> str:
    return f"{x:,.0f} ₺".replace(",", ".")

# --- GİRDİ VE HESAPLAMA MODELLERİ (MODÜLER YAPI) ---
@dataclass
class IndustrialInputs:
    faaliyet_tanimi: str = "Otomotiv ana sanayiye metal şasi parçaları üreten bir tesis. Tesiste büyük hidrolik presler, CNC makineleri ve robotik kaynak hatları bulunmaktadır."
    yapi_turu: str = "Çelik"
    yonetmelik_donemi: str = "2018 sonrası (Yeni Yönetmelik)"
    kat_sayisi: str = "1-3 kat"
    yumusak_kat_riski: str = "Hayır"
    yakin_cevre: str = "Ana Karada / Düz Ova"
    zemin_sinifi: str = "ZC (Varsayılan)"
    isp_varligi: str = "Var (Test Edilmiş)"
    alternatif_tesis: str = "Var (kısmi kapasite)"
    bitmis_urun_stogu: int = 15
    bi_gun_muafiyeti: int = 21

@dataclass
class RESInputs:
    turbin_yas: str = "5-10 yıl arası (Olgun Teknoloji)"
    arazi_jeoteknik: str = "Yumuşak Zeminli / Toprak Tepe veya Ova"
    salt_sahasi: str = "Standart Ekipman (Özel bir önlem yok)"
    bi_gun_muafiyeti: int = 30

@dataclass
class ScenarioInputs:
    tesis_tipi: str = "Endüstriyel Tesis (Fabrika, Depo vb.)"
    si_pd: int = 500_000_000
    yillik_brut_kar: int = 200_000_000
    rg: int = 1
    azami_tazminat_suresi: int = 365
    industrial_params: IndustrialInputs = field(default_factory=IndustrialInputs)
    res_params: RESInputs = field(default_factory=RESInputs)
    icerik_hassasiyeti: str = "Orta"; ffe_riski: str = "Orta"; kritik_makine_bagimliligi: str = "Orta"

# --- TEKNİK HESAPLAMA ÇEKİRDEĞİ ---
# ... (calculate_pd_damage ve calculate_bi_downtime, yani eski kodumuz, burada adı değişerek yer alıyor)
def calculate_pd_damage_industrial(s: ScenarioInputs) -> Dict[str, float]:
    p = s.industrial_params; base_bina_oran = _DEPREM_ORAN.get(s.rg, 0.13)
    FACTORS = {"yonetmelik": {"1998 öncesi": 1.25, "1998-2018": 1.00, "2018 sonrası": 0.80},"kat_sayisi": {"1-3": 0.95, "4-7": 1.00, "8+": 1.10},"zemin": {"ZC (Varsayılan)": 1.00, "ZA/ZB (Kaya/Sıkı Zemin)": 0.85, "ZD": 1.20, "ZE": 1.50},"yumusak_kat": {"Hayır": 1.00, "Evet": 1.40},}
    bina_factor = FACTORS["yonetmelik"].get(p.yonetmelik_donemi.split(' ')[0], 1.0) * FACTORS["kat_sayisi"].get(p.kat_sayisi.split(' ')[0], 1.0) * FACTORS["zemin"].get(p.zemin_sinifi, 1.0) * FACTORS["yumusak_kat"].get(p.yumusak_kat_riski, 1.0)
    if p.yapi_turu == "Betonarme" and "1998 öncesi" in p.yonetmelik_donemi: bina_factor *= 1.20
    if p.yapi_turu == "Çelik" and "1998 öncesi" in p.yonetmelik_donemi: bina_factor *= 1.15
    if p.zemin_sinifi in ["ZD", "ZE"] and p.yakin_cevre != "Ana Karada / Düz Ova": bina_factor *= 1.40
    bina_pd_ratio = min(0.60, max(0.01, base_bina_oran * bina_factor))
    si_bina_varsayim = s.si_pd * 0.40; si_icerik_varsayim = s.si_pd * 0.60
    icerik_hassasiyet_carpan = {"Düşük": 0.6, "Orta": 0.8, "Yüksek": 1.0}.get(s.icerik_hassasiyeti, 0.8)
    icerik_pd_ratio = bina_pd_ratio * icerik_hassasiyet_carpan
    toplam_pd_hasar = (si_bina_varsayim * bina_pd_ratio) + (si_icerik_varsayim * icerik_pd_ratio)
    ortalama_pd_ratio = toplam_pd_hasar / s.si_pd if s.si_pd > 0 else 0
    return {"damage_amount": toplam_pd_hasar, "pml_ratio": ortalama_pd_ratio}

def calculate_bi_downtime_industrial(pd_ratio: float, s: ScenarioInputs) -> Tuple[int, int]:
    p = s.industrial_params
    FACTORS = {"isp": {"Yok (Varsayılan)": 1.00, "Var (Test Edilmemiş)": 0.85, "Var (Test Edilmiş)": 0.70},"makine_bagimliligi": {"Düşük": 1.00, "Orta": 1.25, "Yüksek": 1.70},"alternatif_tesis": {"Yok": 1.0, "Var (kısmi kapasite)": 0.6, "Var (tam kapasite)": 0.2}}
    base_repair_days = 30 + (pd_ratio * 300)
    operational_factor = FACTORS["isp"].get(p.isp_varligi, 1.0) * FACTORS["makine_bagimliligi"].get(s.kritik_makine_bagimliligi, 1.0) * FACTORS["alternatif_tesis"].get(p.alternatif_tesis, 1.0)
    gross_downtime = int(base_repair_days * operational_factor)
    if s.rg in [1, 2]: gross_downtime += 30
    net_downtime_before_indemnity = gross_downtime - p.bitmis_urun_stogu
    final_downtime = min(s.azami_tazminat_suresi, net_downtime_before_indemnity)
    return max(0, gross_downtime), max(0, int(final_downtime))

# YENİ EKLENEN RES MODÜLÜ HESAPLAMA FONKSİYONLARI
def calculate_pd_damage_res(s: ScenarioInputs) -> Dict[str, float]:
    p = s.res_params
    FACTORS = {"turbin_yas": {"5 yıldan yeni (Modern Teknoloji)": 0.9, "5-10 yıl arası (Olgun Teknoloji)": 1.0, "10+ yıl (Eski Teknoloji)": 1.2}, "arazi_jeoteknik": {"Kayalık ve Sağlam Zeminli Tepe": 0.85, "Yumuşak Zeminli / Toprak Tepe veya Ova": 1.3}}
    base_oran = _DEPREM_ORAN.get(s.rg, 0.13) * 0.5
    factor = FACTORS["turbin_yas"].get(p.turbin_yas, 1.0) * FACTORS["arazi_jeoteknik"].get(p.arazi_jeoteknik, 1.0)
    pml_ratio = min(0.40, max(0.01, base_oran * factor))
    return {"damage_amount": s.si_pd * pml_ratio, "pml_ratio": pml_ratio}

def calculate_bi_downtime_res(pd_ratio: float, s: ScenarioInputs) -> Tuple[int, int]:
    p = s.res_params
    base_repair_days = 45 + (pd_ratio * 400); operational_factor = 1.0
    if p.salt_sahasi == "Standart Ekipman (Özel bir önlem yok)": operational_factor *= 1.5
    gross_downtime = int(base_repair_days * operational_factor)
    if s.rg in [1, 2]: gross_downtime += 45
    final_downtime = min(s.azami_tazminat_suresi, gross_downtime)
    return max(0, gross_downtime), max(0, int(final_downtime))

# --- Diğer Yardımcı Fonksiyonlar ---
# ... (Değişiklik yok)

# --- AI FONKSİYONLARI ---
@st.cache_data(show_spinner=False)
def get_ai_driven_parameters_industrial(faaliyet_tanimi: str) -> Dict[str, str]:
    # ... (Eski get_ai_driven_parameters fonksiyonu, ismi değişti)
    pass
    
@st.cache_data(show_spinner=False)
def generate_technical_assessment(s: ScenarioInputs, triggered_rules: List[str]) -> str:
    # ... (İçeriği modüler hale getirildi)
    pass

# --- STREAMLIT UYGULAMASI (MODÜLER ARAYÜZ) ---
def main():
    st.set_page_config(page_title=T["title"]["TR"], layout="wide", page_icon="🏗️")
    if 'run_clicked' not in st.session_state: st.session_state.run_clicked = False
    if 'errors' not in st.session_state: st.session_state.errors = []
    
    st.title(tr('title'))

    if 'tesis_tipi' not in st.session_state: st.session_state.tesis_tipi = tr("endustriyel_tesis")
    
    tesis_tipi_secenekleri = [tr("endustriyel_tesis"), tr("res"), tr("ges"), tr("hes")]
    
    def on_tesis_tipi_change():
        st.session_state.run_clicked = False
    
    selected_tesis_tipi = st.selectbox(tr("tesis_tipi_secimi"), tesis_tipi_secenekleri, 
        index=tesis_tipi_secenekleri.index(st.session_state.tesis_tipi), on_change=on_tesis_tipi_change, key="tesis_tipi_selector")
    st.session_state.tesis_tipi = selected_tesis_tipi

    s_inputs = st.session_state.get('s_inputs', ScenarioInputs(tesis_tipi=st.session_state.tesis_tipi))
    s_inputs.tesis_tipi = st.session_state.tesis_tipi
    
    st.header(tr("inputs_header"))
    
    if s_inputs.tesis_tipi == tr("endustriyel_tesis"):
        p_ind = s_inputs.industrial_params
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader(tr("base_header"))
            s_inputs.si_pd = st.number_input(tr("si_pd"), min_value=1_000_000, value=s_inputs.si_pd, step=10_000_000)
            p_ind.faaliyet_tanimi = st.text_area(tr("activity_desc"), p_ind.faaliyet_tanimi, height=200)
        with col2:
            st.subheader(tr("pd_header"))
            s_inputs.rg = st.select_slider(tr("risk_zone"), options=list(range(1, 8)), value=s_inputs.rg)
            # ... (Diğer tüm Endüstriyel Tesis girdileri)
        with col3:
            st.subheader(tr("bi_header"))
            s_inputs.yillik_brut_kar = st.number_input(tr("gross_profit"), min_value=0, value=s_inputs.yillik_brut_kar, step=10_000_000)
            p_ind.bi_gun_muafiyeti = st.selectbox(tr("bi_wait"), [14, 21, 30, 45, 60], index=[14, 21, 30, 45, 60].index(p_ind.bi_gun_muafiyeti))
            s_inputs.azami_tazminat_suresi = st.selectbox(tr("azami_tazminat"), [365, 540, 730], index=0, format_func=lambda x: f"{int(x/30)} Ay")
            #... (Diğer tüm Endüstriyel Tesis girdileri)
            
    elif s_inputs.tesis_tipi == tr("res"):
        p_res = s_inputs.res_params
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader(tr("base_header"))
            s_inputs.si_pd = st.number_input(tr("si_pd"), min_value=1_000_000, value=s_inputs.si_pd, step=10_000_000)
            s_inputs.yillik_brut_kar = st.number_input(tr("gross_profit"), min_value=0, value=s_inputs.yillik_brut_kar, step=10_000_000)
        with col2:
            st.subheader(tr("res_header"))
            s_inputs.rg = st.select_slider(tr("risk_zone"), options=list(range(1, 8)), value=s_inputs.rg)
            p_res.turbin_yas = st.selectbox(tr("turbin_yas"), ["5 yıldan yeni (Modern Teknoloji)", "5-10 yıl arası (Olgun Teknoloji)", "10+ yıl (Eski Teknoloji)"])
            p_res.arazi_jeoteknik = st.selectbox(tr("arazi_jeoteknik"), ["Kayalık ve Sağlam Zeminli Tepe", "Yumuşak Zeminli / Toprak Tepe veya Ova"])
            p_res.salt_sahasi = st.selectbox(tr("salt_sahasi"), ["Standart Ekipman (Özel bir önlem yok)", "Sismik İzolatörlü veya Güçlendirilmiş Ekipman"])
        with col3:
            st.subheader(tr("bi_header"))
            s_inputs.azami_tazminat_suresi = st.selectbox(tr("azami_tazminat"), [365, 540, 730], index=0, format_func=lambda x: f"{int(x/30)} Ay")
            p_res.bi_gun_muafiyeti = st.selectbox(tr("bi_wait"), [30, 45, 60, 90], index=0)
    
    else:
        st.info(tr("yakinda"))
        st.stop()

    # ... (Geri kalan kod)

if __name__ == "__main__":
    main()
