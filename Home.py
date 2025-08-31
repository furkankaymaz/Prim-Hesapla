# -*- coding: utf-8 -*-
#
# TariffEQ – Profesyonel ve AI Destekli PD & BI Hasar Analiz Aracı
# =======================================================================
# Bu Streamlit uygulaması, reasürans ve katastrofik modelleme metodolojilerinden
# esinlenerek geliştirilmiş parametreler ve tarifeye tam uyumlu hesaplama
# mantığı ile ticari/sınai rizikolar için profesyonel seviyede bir deprem
# hasar analizi sunar.
#
# GÜNCEL REVİZYON NOTLARI (Ağustos 2025 - v4.3 - Final):
# 1. Tam Modüler Entegrasyon: RES modülü, hesaplama ve poliçe analizi dahil
#    olmak üzere tüm özellikleriyle ana yapıya sorunsuz şekilde entegre edildi.
# 2. Akıllı Girdi Optimizasyonu: Metin alanları, kullanıcının daha önce seçtiği
#    bilgileri tekrar girmesini önleyecek şekilde yeniden tasarlandı.
# 3. Gelişmiş AI Sentezi: AI, artık yapılandırılmış girdiler (dropdown'lar) ile
#    serbest metin girdisini birleştirerek çok daha derinlemesine analizler yapıyor.
# 4. Hata Giderimi ve Stabilite: Önceki tüm hatalar giderildi ve kodun kararlı
#    çalışması sağlandı.

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
TARIFE_RATES = {"Betonarme": [3.13, 2.63, 2.38, 1.94, 1.38, 1.06, 0.75], "Çelik": [3.13, 2.63, 2.38, 1.94, 1.38, 1.06, 0.75], "Yığma": [6.13, 5.56, 3.75, 2.00, 1.56, 1.24, 1.06], "Diğer": [6.13, 5.56, 3.75, 2.00, 1.56, 1.24, 1.06]}
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
    "res_header": {"TR": "💨 RES'e Özgü Riskler", "EN": "💨 WPP-Specific Risks"},
    "activity_desc_industrial": {"TR": "Süreç, Ekipman ve Stoklara Dair Ek Detaylar", "EN": "Additional Details on Processes, Equipment, and Stock"},
    "activity_desc_res": {"TR": "Türbin, Saha ve Ekipmanlara Dair Ek Detaylar", "EN": "Additional Details on Turbines, Site, and Equipment"},
    "si_pd": {"TR": "Toplam Sigorta Bedeli (PD)", "EN": "Total Sum Insured (PD)"},
    "risk_zone": {"TR": "Deprem Risk Bölgesi", "EN": "Earthquake Risk Zone"},
    "gross_profit": {"TR": "Yıllık Brüt Kâr (GP)", "EN": "Annual Gross Profit (GP)"},
    "turbin_yas": {"TR": "Türbin Teknolojisi ve Ortalama Yaşı", "EN": "Turbine Technology and Average Age"},
    "arazi_jeoteknik": {"TR": "Arazinin Jeo-Teknik Durumu", "EN": "Geo-Technical Condition of the Site"},
    "salt_sahasi": {"TR": "Şalt Sahasının Sismik Performansı", "EN": "Seismic Performance of the Substation"},
    "azami_tazminat": {"TR": "Azami Tazminat Süresi", "EN": "Max. Indemnity Period"},
    "bi_wait": {"TR": "BI Bekleme Süresi (Muafiyet)", "EN": "BI Waiting Period (Deductible)"},
    "yumusak_kat": {"TR": "Zemin Katta Geniş Vitrin/Cephe (Yumuşak Kat Riski)", "EN": "Large Ground Floor Facade/Windows (Soft Story Risk)"},
    "yumusak_kat_help": {"TR": "Binanızın zemin katı, üst katlara göre daha az perde duvara sahip ve büyük oranda cam cephe/vitrin/garaj kapısı gibi açıklıklardan mı oluşuyor?", "EN": "Does your building's ground floor have significantly fewer shear walls than the upper floors, consisting mostly of open spaces like glass facades, storefronts, or garage doors?"},
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
    faaliyet_tanimi: str = "Otomotiv ana sanayiye metal şasi parçaları üreten bir tesis. Tesiste 5 adet 1000 tonluk hidrolik pres, CNC makineleri ve robotik kaynak hatları bulunmaktadır. Yüksek raflarda rulo sac malzeme stoklanmaktadır."
    yapi_turu: str = "Çelik"; yonetmelik_donemi: str = "2018 sonrası (Yeni Yönetmelik)"; kat_sayisi: str = "1-3 kat"
    yumusak_kat_riski: str = "Hayır"; yakin_cevre: str = "Ana Karada / Düz Ova"; zemin_sinifi: str = "ZC (Varsayılan)"
    isp_varligi: str = "Var (Test Edilmiş)"; alternatif_tesis: str = "Var (kısmi kapasite)"; bitmis_urun_stogu: int = 15; bi_gun_muafiyeti: int = 21

@dataclass
class RESInputs:
    ek_detaylar: str = "Manisa'da, temel iyileştirmesi yapılmış bir yamaçta kurulu 25 adet 8 yıllık Nordex N90 türbini. Şalt sahası standart tipte ve tesise 1km uzakta."
    turbin_yas: str = "5-10 yıl arası (Olgun Teknoloji)"
    arazi_jeoteknik: str = "Yumuşak Zeminli / Toprak Tepe veya Ova"
    salt_sahasi: str = "Standart Ekipman (Özel bir önlem yok)"
    bi_gun_muafiyeti: int = 30

@dataclass
class ScenarioInputs:
    tesis_tipi: str = tr("endustriyel_tesis")
    si_pd: int = 500_000_000
    yillik_brut_kar: int = 200_000_000
    rg: int = 1
    azami_tazminat_suresi: int = 365
    industrial_params: IndustrialInputs = field(default_factory=IndustrialInputs)
    res_params: RESInputs = field(default_factory=RESInputs)
    icerik_hassasiyeti: str = "Orta"; ffe_riski: str = "Orta"; kritik_makine_bagimliligi: str = "Orta"

# --- TEKNİK HESAPLAMA ÇEKİRDEĞİ ---
def calculate_pd_damage_industrial(s: ScenarioInputs) -> Dict[str, float]:
    p = s.industrial_params; base_bina_oran = _DEPREM_ORAN.get(s.rg, 0.13)
    FACTORS = {"yonetmelik": {"1998 öncesi (Eski Yönetmelik)": 1.25, "1998-2018 arası (Varsayılan)": 1.00, "2018 sonrası (Yeni Yönetmelik)": 0.80},"kat_sayisi": {"1-3 kat": 0.95, "4-7 kat": 1.00, "8+ kat": 1.10},"zemin": {"ZC (Varsayılan)": 1.00, "ZA/ZB (Kaya/Sıkı Zemin)": 0.85, "ZD": 1.20, "ZE": 1.50},"yumusak_kat": {"Hayır": 1.00, "Evet": 1.40}}
    bina_factor = FACTORS["yonetmelik"].get(p.yonetmelik_donemi, 1.0) * FACTORS["kat_sayisi"].get(p.kat_sayisi, 1.0) * FACTORS["zemin"].get(p.zemin_sinifi, 1.0) * FACTORS["yumusak_kat"].get(p.yumusak_kat_riski, 1.0)
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

def calculate_pd_damage_res(s: ScenarioInputs) -> Dict[str, float]:
    p = s.res_params
    FACTORS = {"turbin_yas": {"5 yıldan yeni (Modern Teknoloji)": 0.9, "5-10 yıl arası (Olgun Teknoloji)": 1.0, "10+ yıl (Eski Teknoloji)": 1.25}, "arazi_jeoteknik": {"Kayalık ve Sağlam Zeminli Tepe": 0.85, "Yumuşak Zeminli / Toprak Tepe veya Ova": 1.35}}
    base_oran = _DEPREM_ORAN.get(s.rg, 0.13) * 0.5
    factor = FACTORS["turbin_yas"].get(p.turbin_yas, 1.0) * FACTORS["arazi_jeoteknik"].get(p.arazi_jeoteknik, 1.0)
    pml_ratio = min(0.40, max(0.01, base_oran * factor))
    return {"damage_amount": s.si_pd * pml_ratio, "pml_ratio": pml_ratio}

def calculate_bi_downtime_res(pd_ratio: float, s: ScenarioInputs) -> Tuple[int, int]:
    p = s.res_params
    base_repair_days = 45 + (pd_ratio * 400); operational_factor = 1.0
    if p.salt_sahasi == "Standart Ekipman (Özel bir önlem yok)": operational_factor *= 1.5
    if "10+" in p.turbin_yas: operational_factor *= 1.1 # Eski türbinlerin onarımı daha uzun sürer (dişli kutusu vb.)
    gross_downtime = int(base_repair_days * operational_factor)
    if s.rg in [1, 2]: gross_downtime += 45
    final_downtime = min(s.azami_tazminat_suresi, gross_downtime)
    return max(0, gross_downtime), max(0, int(final_downtime))

def get_allowed_options(si_pd: int) -> Tuple[List[str], List[float]]:
    koas_opts = list(KOAS_FACTORS.keys())[:9]; muaf_opts = list(MUAFIYET_FACTORS.keys())[:5]
    if si_pd > 3_500_000_000: koas_opts.extend(list(KOAS_FACTORS.keys())[9:]); muaf_opts.extend(list(MUAFIYET_FACTORS.keys())[5:])
    return koas_opts, muaf_opts

def calculate_premium(si: float, tarife_yapi_turu: str, rg: int, koas: str, muaf: float, is_bi: bool = False) -> float:
    base_rate = TARIFE_RATES.get(tarife_yapi_turu, TARIFE_RATES["Diğer"])[rg - 1]; prim_bedeli = min(si, 3_500_000_000) if not is_bi else si
    if is_bi: return (prim_bedeli * base_rate * 0.75) / 1000.0
    factor = KOAS_FACTORS.get(koas, 1.0) * MUAFIYET_FACTORS.get(muaf, 1.0)
    return (prim_bedeli * base_rate * factor) / 1000.0

def calculate_net_claim(si_pd: int, hasar_tutari: float, koas: str, muaf_pct: float) -> Dict[str, float]:
    muafiyet_tutari = si_pd * (muaf_pct / 100.0); muafiyet_sonrasi_hasar = max(0.0, hasar_tutari - muafiyet_tutari)
    sirket_pay_orani = float(koas.split('/')[0]) / 100.0; net_tazminat = muafiyet_sonrasi_hasar * sirket_pay_orani
    sigortalida_kalan = hasar_tutari - net_tazminat
    return {"net_tazminat": net_tazminat, "sigortalida_kalan": sigortalida_kalan}

# --- AI FONKSİYONLARI ---
@st.cache_data(show_spinner=False)
def get_ai_driven_parameters_industrial(faaliyet_tanimi: str) -> Dict[str, str]:
    default_params = {"icerik_hassasiyeti": "Orta", "ffe_riski": "Orta", "kritik_makine_bagimliligi": "Orta"}
    if not _GEMINI_AVAILABLE: return default_params
    prompt = f"""
    Rolün: Kıdemli bir deprem risk mühendisi.
    Görevin: Bir endüstriyel tesisin süreç, ekipman ve stok detaylarını analiz edip, 3 risk parametresini skorlamak.
    Kısıtlar: Yanıtın SADECE JSON formatında olmalı.
    Ek Detaylar: "{faaliyet_tanimi}"
    Önemli Notlar: Modern bir yapı bile olsa, metindeki ekipman (pres, CNC, raf) ve süreç (boyahane, kimyasal) detayları 'içerik hassasiyeti' ve 'kritik makine bağımlılığı'nı yükseltebilir. Eğer metinde "ilaç", "laboratuvar", "elektronik" gibi kelimeler varsa, parametreleri tereddütsüz 'Yüksek' olarak ata.
    SADECE ŞU JSON'u DÖNDÜR: {{"icerik_hassasiyeti": "...", "ffe_riski": "...", "kritik_makine_bagimliligi": "..."}}
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash'); generation_config = {"temperature": 0.1, "top_p": 0.8, "response_mime_type": "application/json"}
        response = model.generate_content(prompt, generation_config=generation_config); params = json.loads(response.text)
        for key in default_params:
            if params.get(key) not in ['Düşük', 'Orta', 'Yüksek']: params[key] = default_params[key]
        return params
    except Exception as e:
        st.session_state.errors.append(f"AI Parametre Hatası: {str(e)}\n{traceback.format_exc()}"); return default_params

@st.cache_data(show_spinner=False)
def generate_technical_assessment(s: ScenarioInputs, triggered_rules: List[str]) -> str:
    if not _GEMINI_AVAILABLE: return "AI servisi aktif değil."
    
    if s.tesis_tipi == tr("endustriyel_tesis"):
        p = s.industrial_params
        prompt = f"""
        Rolün: TariffEQ için çalışan uzman bir AI teknik underwriter'ı (Endüstriyel Tesisler).
        Görevin: Sana iletilen yapılandırılmış ve serbest metin girdilerini sentezleyerek, en önemli 2-3 risk faktörünü seçip görsel ve ikna edici bir "AI Teknik Risk Değerlendirmesi" oluşturmak.
        Kesin Kurallar: Başlık "### 🧠 AI Teknik Risk Değerlendirmesi (Endüstriyel Tesis)" olacak. Emoji kullan (🧱, 💧, 🏭, 🔧). Her faktörü "Tespit:" ve "Etki:" ile açıkla. Sonunda "Sonuçsal Beklenti:" başlığıyla kalitatif yorum yap. ASLA PML oranı verme.
        Gerekçelendirme Talimatı: 'Tespitlerini' yaparken, hem yapılandırılmış girdilerden (örn: 'Yönetmelik: 1998 öncesi') hem de serbest metindeki anahtar kelimelerden (örn: metindeki 'pres hattı' kelimesi) çıkarımlar yap.
        ---
        YAPILANDIRILMIŞ GİRDİLER: Yapı Türü: {p.yapi_turu}, Yönetmelik: {p.yonetmelik_donemi}, Zemin: {p.zemin_sinifi}, Yakın Çevre: {p.yakin_cevre}, Yumuşak Kat: {p.yumusak_kat_riski}
        SERBEST METİN (Ek Detaylar): "{p.faaliyet_tanimi}"
        SİSTEM TARAFINDAN TESPİT EDİLEN AKTİF RİSK FAKTÖRLERİ: {triggered_rules}
        ---
        Lütfen bu bilgilerle Teknik Risk Değerlendirmesini oluştur.
        """
    elif s.tesis_tipi == tr("res"):
        p = s.res_params
        prompt = f"""
        Rolün: TariffEQ için çalışan uzman bir AI teknik underwriter'ı (Rüzgar Enerji Santralleri).
        Görevin: Sana iletilen yapılandırılmış ve serbest metin girdilerini sentezleyerek, en önemli 2-3 risk faktörünü seçip bir RES tesisi için görsel ve ikna edici bir "AI Teknik Risk Değerlendirmesi" oluşturmak.
        Kesin Kurallar: Başlık "### 🧠 AI Teknik Risk Değerlendirmesi (Rüzgar Enerji Santrali)" olacak. Emoji kullan (💨, 🏔️, ⚡️). Her faktörü "Tespit:" ve "Etki:" ile açıkla. Sonunda "Sonuçsal Beklenti:" başlığıyla kalitatif yorum yap. ASLA PML oranı verme.
        Gerekçelendirme Talimatı: 'Tespitlerini' yaparken, hem yapılandırılmış girdilerden (örn: 'Türbin Yaşı: 10+ yıl') hem de serbest metindeki anahtar kelimelerden (örn: metindeki 'Nordex N90' ifadesi) çıkarımlar yap. 'YUMUSAK_ZEMIN' için 'salınım (rocking) etkisi' ve 'kule-temel birleşimi' risklerini vurgula. 'ESKI_TEKNOLOJI' için 'dişli kutusu (gearbox) hizalanması' ve 'metal yorgunluğu' risklerini vurgula. 'STANDART_SALT_SAHASI' için ise 'porselen izolatör' kırılganlığının BI için en zayıf halka olduğunu belirt.
        ---
        YAPILANDIRILMIŞ GİRDİLER: Türbin Yaşı: {p.turbin_yas}, Arazi Durumu: {p.arazi_jeoteknik}, Şalt Sahası: {p.salt_sahasi}, Risk Bölgesi: {s.rg}
        SERBEST METİN (Ek Detaylar): "{p.ek_detaylar}"
        SİSTEM TARAFINDAN TESPİT EDİLEN AKTİF RİSK FAKTÖRLERİ: {triggered_rules}
        ---
        Lütfen bu bilgilerle Teknik Risk Değerlendirmesini oluştur.
        """
    else: return "Seçilen tesis tipi için AI değerlendirmesi henüz aktif değil."
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt, generation_config={"temperature": 0.2})
        return response.text
    except Exception as e:
        st.session_state.errors.append(f"AI Rapor Hatası: {str(e)}\n{traceback.format_exc()}"); return "AI Teknik Değerlendirme raporu oluşturulamadı."

# --- STREAMLIT UYGULAMASI ---
def main():
    st.set_page_config(page_title=T["title"]["TR"], layout="wide", page_icon="🏗️")
    if 'run_clicked' not in st.session_state: st.session_state.run_clicked = False
    if 'errors' not in st.session_state: st.session_state.errors = []
    
    st.title(tr('title'))

    if 's_inputs' not in st.session_state:
        st.session_state.s_inputs = ScenarioInputs()

    tesis_tipi_secenekleri = [tr("endustriyel_tesis"), tr("res"), tr("ges"), tr("hes")]
    
    def on_tesis_tipi_change():
        st.session_state.run_clicked = False
        st.session_state.s_inputs = ScenarioInputs(tesis_tipi=st.session_state.tesis_tipi_selector)

    try:
        current_index = tesis_tipi_secenekleri.index(st.session_state.s_inputs.tesis_tipi)
    except ValueError:
        st.session_state.s_inputs = ScenarioInputs()
        current_index = 0
    
    selected_tesis_tipi = st.selectbox(tr("tesis_tipi_secimi"), tesis_tipi_secenekleri, 
                                       index=current_index, 
                                       on_change=on_tesis_tipi_change, key="tesis_tipi_selector")
    
    s_inputs = st.session_state.s_inputs
    s_inputs.tesis_tipi = selected_tesis_tipi
    
    st.header(tr("inputs_header"))
    
    if s_inputs.tesis_tipi == tr("endustriyel_tesis"):
        p_ind = s_inputs.industrial_params
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader(tr("base_header")); s_inputs.si_pd = st.number_input(tr("si_pd"), min_value=1_000_000, value=s_inputs.si_pd, step=10_000_000)
            p_ind.faaliyet_tanimi = st.text_area(tr("activity_desc_industrial"), p_ind.faaliyet_tanimi, height=200, placeholder="Örn: ...hidrolik presler, CNC makineleri ve robotik kaynak hatları bulunmaktadır. Yüksek raflarda rulo sac malzeme stoklanmaktadır.")
        with col2:
            st.subheader(tr("pd_header")); s_inputs.rg = st.select_slider(tr("risk_zone"), options=list(range(1, 8)), value=s_inputs.rg)
            p_ind.yapi_turu = st.selectbox("Yapı Türü", ["Betonarme", "Çelik", "Yığma", "Diğer"])
            p_ind.yonetmelik_donemi = st.selectbox("Yönetmelik Dönemi", ["1998 öncesi (Eski Yönetmelik)", "1998-2018 arası (Varsayılan)", "2018 sonrası (Yeni Yönetmelik)"])
            p_ind.kat_sayisi = st.selectbox("Kat Sayısı", ["1-3 kat", "4-7 kat", "8+ kat"])
            p_ind.zemin_sinifi = st.selectbox("Zemin Sınıfı", ["ZE", "ZD", "ZC (Varsayılan)", "ZA/ZB (Kaya/Sıkı Zemin)"])
            p_ind.yakin_cevre = st.selectbox("Tesisin Yakın Çevresi", ["Nehir Yatağı / Göl Kenarı / Kıyı Şeridi", "Ana Karada / Düz Ova", "Dolgu Zemin Üzerinde"])
            p_ind.yumusak_kat_riski = st.selectbox(tr("yumusak_kat"), ["Hayır", "Evet"], help=tr("yumusak_kat_help"))
        with col3:
            st.subheader(tr("bi_header")); s_inputs.yillik_brut_kar = st.number_input(tr("gross_profit"), min_value=0, value=s_inputs.yillik_brut_kar, step=10_000_000)
            p_ind.bi_gun_muafiyeti = st.selectbox(tr("bi_wait"), [14, 21, 30, 45, 60])
            s_inputs.azami_tazminat_suresi = st.selectbox(tr("azami_tazminat"), [365, 540, 730], format_func=lambda x: f"{int(x/30)} Ay")
            p_ind.isp_varligi = st.selectbox("İş Sürekliliği Planı", ["Yok (Varsayılan)", "Var (Test Edilmemiş)", "Var (Test Edilmiş)"])
            p_ind.alternatif_tesis = st.selectbox("Alternatif Tesis", ["Yok", "Var (kısmi kapasite)", "Var (tam kapasite)"])
            p_ind.bitmis_urun_stogu = st.number_input("Bitmiş Ürün Stoğu (gün)", value=p_ind.bitmis_urun_stogu, min_value=0)
            
    elif s_inputs.tesis_tipi == tr("res"):
        p_res = s_inputs.res_params
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader(tr("base_header")); s_inputs.si_pd = st.number_input(tr("si_pd"), min_value=1_000_000, value=s_inputs.si_pd, step=10_000_000)
            s_inputs.yillik_brut_kar = st.number_input(tr("gross_profit"), min_value=0, value=s_inputs.yillik_brut_kar, step=10_000_000)
            p_res.ek_detaylar = st.text_area(tr("activity_desc_res"), p_res.ek_detaylar, height=125, placeholder="Örn: Manisa'da, temel iyileştirmesi yapılmış bir yamaçta kurulu 25 adet 8 yıllık Nordex N90 türbini...")
        with col2:
            st.subheader(tr("res_header")); s_inputs.rg = st.select_slider(tr("risk_zone"), options=list(range(1, 8)), value=s_inputs.rg)
            p_res.turbin_yas = st.selectbox(tr("turbin_yas"), ["5 yıldan yeni (Modern Teknoloji)", "5-10 yıl arası (Olgun Teknoloji)", "10+ yıl (Eski Teknoloji)"])
            p_res.arazi_jeoteknik = st.selectbox(tr("arazi_jeoteknik"), ["Kayalık ve Sağlam Zeminli Tepe", "Yumuşak Zeminli / Toprak Tepe veya Ova"])
            p_res.salt_sahasi = st.selectbox(tr("salt_sahasi"), ["Standart Ekipman (Özel bir önlem yok)", "Sismik İzolatörlü veya Güçlendirilmiş Ekipman"])
        with col3:
            st.subheader(tr("bi_header")); s_inputs.azami_tazminat_suresi = st.selectbox(tr("azami_tazminat"), [365, 540, 730], format_func=lambda x: f"{int(x/30)} Ay")
            p_res.bi_gun_muafiyeti = st.selectbox(tr("bi_wait"), [30, 45, 60, 90])
    
    else:
        st.info(tr("yakinda")); st.stop()
        
    st.markdown("---")
    
    if st.button(f"🚀 {tr('btn_run')}", use_container_width=True, type="primary"):
        st.session_state.run_clicked = True
        st.session_state.s_inputs = s_inputs
        st.session_state.errors = []
    
    if st.session_state.run_clicked:
        s_inputs = st.session_state.s_inputs
        triggered_rules = []
        
        if s_inputs.tesis_tipi == tr("endustriyel_tesis"):
            with st.spinner("AI, endüstriyel tesisinizi analiz ediyor..."):
                ai_params = get_ai_driven_parameters_industrial(s_inputs.industrial_params.faaliyet_tanimi)
                s_inputs.icerik_hassasiyeti, s_inputs.kritik_makine_bagimliligi = ai_params["icerik_hassasiyeti"], ai_params["kritik_makine_bagimliligi"]
            p_ind = s_inputs.industrial_params
            if p_ind.yapi_turu == "Betonarme" and "1998 öncesi" in p_ind.yonetmelik_donemi: triggered_rules.append("ESKI_PREFABRIK_RISKI")
            if p_ind.yapi_turu == "Çelik" and "1998 öncesi" in p_ind.yonetmelik_donemi: triggered_rules.append("CELIK_KAYNAK_RISKI")
            if p_ind.zemin_sinifi in ["ZD", "ZE"] and p_ind.yakin_cevre != "Ana Karada / Düz Ova": triggered_rules.append("SIVILASMA_RISKI")
            if p_ind.yumusak_kat_riski == "Evet": triggered_rules.append("YUMUSAK_KAT_RISKI")
            if s_inputs.icerik_hassasiyeti == 'Yüksek' or s_inputs.kritik_makine_bagimliligi == 'Yüksek': triggered_rules.append("SEKTOREL_HASSASIYET")
            if s_inputs.rg in [1, 2]: triggered_rules.append("ALTYAPI_RISKI")
            pd_results = calculate_pd_damage_industrial(s_inputs)
            gross_bi_days, net_bi_days_raw = calculate_bi_downtime_industrial(pd_results["pml_ratio"], s_inputs)
            net_bi_days_final = max(0, net_bi_days_raw - p_ind.bi_gun_muafiyeti)
            tarife_yapi_turu = p_ind.yapi_turu
            
        elif s_inputs.tesis_tipi == tr("res"):
            p_res = s_inputs.res_params
            if "10+" in p_res.turbin_yas: triggered_rules.append("ESKI_TEKNOLOJI")
            if "Yumuşak Zeminli" in p_res.arazi_jeoteknik: triggered_rules.append("YUMUSAK_ZEMIN")
            if "Standart Ekipman" in p_res.salt_sahasi: triggered_rules.append("STANDART_SALT_SAHASI")
            pd_results = calculate_pd_damage_res(s_inputs)
            gross_bi_days, net_bi_days_raw = calculate_bi_downtime_res(pd_results["pml_ratio"], s_inputs)
            net_bi_days_final = max(0, net_bi_days_raw - p_res.bi_gun_muafiyeti)
            tarife_yapi_turu = "Diğer"

        st.header(tr("ai_pre_analysis_header"))
        with st.spinner("AI Teknik Underwriter'ı senaryoyu değerlendiriyor..."):
            assessment_report = generate_technical_assessment(s_inputs, triggered_rules)
            st.markdown(assessment_report, unsafe_allow_html=True)
            
        pd_damage_amount = pd_results["damage_amount"]; pd_ratio = pd_results["pml_ratio"]
        bi_damage_amount = (s_inputs.yillik_brut_kar / 365.0) * net_bi_days_final if s_inputs.yillik_brut_kar > 0 else 0
        
        st.header(tr("results_header"))
        m1, m2, m3 = st.columns(3)
        m1.metric("Beklenen PD Hasar Tutarı", money(pd_damage_amount), f"PML: {pd_ratio:.2%}")
        m2.metric("Brüt / Net İş Kesintisi", f"{gross_bi_days} / {net_bi_days_final} gün", "Onarım / Tazmin edilebilir")
        m3.metric("Beklenen BI Hasar Tutarı", money(bi_damage_amount))
        
        st.markdown("---")
        st.header(tr("analysis_header"))
        koas_opts, muaf_opts = get_allowed_options(s_inputs.si_pd)
        results = []
        for koas in koas_opts:
            for muaf in muaf_opts:
                prim_pd = calculate_premium(s_inputs.si_pd, tarife_yapi_turu, s_inputs.rg, koas, muaf)
                prim_bi = calculate_premium(s_inputs.yillik_brut_kar, tarife_yapi_turu, s_inputs.rg, koas, muaf, is_bi=True)
                toplam_prim = prim_pd + prim_bi
                pd_claim = calculate_net_claim(s_inputs.si_pd, pd_damage_amount, koas, muaf)
                total_payout = pd_claim["net_tazminat"] + bi_damage_amount
                retained_risk = (pd_damage_amount + bi_damage_amount) - total_payout
                verimlilik_skoru = (total_payout / toplam_prim if toplam_prim > 0 else 0) - (retained_risk / s_inputs.si_pd if s_inputs.si_pd > 0 else 0)
                results.append({"Poliçe Yapısı": f"{koas} / {muaf}%", "Yıllık Toplam Prim": toplam_prim, "Toplam Net Tazminat": total_payout, "Sigortalıda Kalan Risk": retained_risk, "Verimlilik Skoru": verimlilik_skoru})
        df = pd.DataFrame(results).sort_values("Verimlilik Skoru", ascending=False).reset_index(drop=True)
        
        tab1, tab2 = st.tabs(["📈 Tablo Analizi", "📊 Görsel Analiz"])
        with tab1:
            st.dataframe(df.style.format({"Yıllık Toplam Prim": money, "Toplam Net Tazminat": money, "Sigortalıda Kalan Risk": money, "Verimlilik Skoru": "{:.2f}"}), use_container_width=True)
        with tab2:
            fig = px.scatter(df, x="Yıllık Toplam Prim", y="Sigortalıda Kalan Risk", color="Verimlilik Skoru", color_continuous_scale=px.colors.sequential.Viridis, hover_data=["Poliçe Yapısı", "Toplam Net Tazminat", "Verimlilik Skoru"], title="Poliçe Alternatifleri Maliyet-Risk Analizi")
            fig.update_layout(xaxis_title="Yıllık Toplam Prim", yaxis_title="Hasarda Şirketinizde Kalacak Risk", coloraxis_colorbar_title_text = 'Verimlilik')
            st.plotly_chart(fig, use_container_width=True)
            
    if st.session_state.errors:
        with st.sidebar.expander("⚠️ Geliştirici Hata Logları", expanded=False):
            for error in st.session_state.errors:
                st.code(error)

if __name__ == "__main__":
    main()
