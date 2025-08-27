# -*- coding: utf-8 -*-
#
# TariffEQ – Profesyonel ve AI Destekli PD & BI Hasar Analiz Aracı
# =======================================================================
# Bu Streamlit uygulaması, reasürans ve katastrofik modelleme metodolojilerinden
# esinlenerek geliştirilmiş parametreler ve tarifeye tam uyumlu hesaplama
# mantığı ile ticari/sınai rizikolar için profesyonel seviyede bir deprem
# hasar analizi sunar.
#
# Kilit Özellikler:
# 1. AI Destekli Dinamik Parametre Ataması: AI, kullanıcının girdiği faaliyet
#    tanımını analiz ederek İçerik Hassasiyeti, FFE Riski gibi kritik risk
#    parametrelerini otomatik olarak belirler ve hesaplamalara dahil eder.
# 2. Gelişmiş Risk Parametreleri: Deprem Yönetmeliği Dönemi, Kat Sayısı,
#    Zemin Sınıfı, İş Sürekliliği Planı gibi profesyonel düzeyde risk
#    faktörleri analize dahil edilmiştir.
# 3. Ölçek Bazlı Dinamik Danışmanlık: AI, sigorta bedeline göre firmayı
#    (KOBİ, Ticari, Kurumsal) segmente eder ve tavsiyelerini bu ölçeğe göre özelleştirir.
# 4. Yeniden Tasarlanan Arayüz: Tüm girdiler, daha iyi bir kullanıcı deneyimi
#    için ana ekranda, mantıksal gruplar halinde üç sütunda toplanmıştır.

import streamlit as st
import pandas as pd
import plotly.express as px
from dataclasses import dataclass
from typing import Dict, List, Tuple
import json
import time

# --- AI İÇİN KORUMALI IMPORT VE GÜVENLİ KONFİGÜRASYON ---
_GEMINI_AVAILABLE = False
try:
    import google.generativeai as genai
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        _GEMINI_AVAILABLE = True
    else:
        _GEMINI_AVAILABLE = False
except (ImportError, Exception):
    _GEMINI_AVAILABLE = False

# --- TARİFE, ÇARPAN VERİLERİ VE SABİTLER ---
TARIFE_RATES = {"Betonarme": [3.13, 2.63, 2.38, 1.94, 1.38, 1.06, 0.75], "Diğer": [6.13, 5.56, 3.75, 2.00, 1.56, 1.24, 1.06]}
KOAS_FACTORS = {"80/20": 1.0, "75/25": 0.9375, "70/30": 0.875, "65/35": 0.8125, "60/40": 0.75, "55/45": 0.6875, "50/50": 0.625, "45/55": 0.5625, "40/60": 0.5, "90/10": 1.125, "100/0": 1.25}
MUAFIYET_FACTORS = {2.0: 1.0, 3.0: 0.94, 4.0: 0.87, 5.0: 0.81, 10.0: 0.65, 1.5: 1.03, 1.0: 1.06, 0.5: 1.09, 0.1: 1.12}
_DEPREM_ORAN = {1: 0.20, 2: 0.17, 3: 0.13, 4: 0.09, 5: 0.06, 6: 0.06, 7: 0.06}

# --- ÇEVİRİ SÖZLÜĞÜ ---
T = {
    "title": {"TR": "TariffEQ – Profesyonel Risk Analizi", "EN": "TariffEQ – Professional Risk Analysis"},
    "inputs_header": {"TR": "📊 1. Senaryo Girdileri", "EN": "📊 1. Scenario Inputs"},
    "base_header": {"TR": "🏭 Temel Tesis Bilgileri", "EN": "🏭 Basic Facility Information"},
    "pd_header": {"TR": "🧱 PD Risk Parametreleri", "EN": "🧱 PD Risk Parameters"},
    "bi_header": {"TR": "📈 BI Risk Parametreleri", "EN": "📈 BI Risk Parameters"},
    "activity_desc": {"TR": "Tesisin Faaliyet Tanımı", "EN": "Facility Activity Description"},
    "activity_desc_help": {"TR": "AI'ın tesisinize özel riskleri (içerik hassasiyeti, yangın riski vb.) doğru analiz edebilmesi için lütfen faaliyetinizi kısaca açıklayın.", "EN": "Please briefly describe your operations so the AI can accurately analyze facility-specific risks (e.g., content vulnerability, fire risk)."},
    "si_pd": {"TR": "PD Toplam Sigorta Bedeli", "EN": "PD Total Sum Insured"},
    "si_pd_help": {"TR": "Bina, makine, demirbaş ve emtia gibi tüm maddi varlıklarınızın toplam yeniden yapım veya yerine koyma bedeli.", "EN": "The total replacement cost of all your physical assets like buildings, machinery, fixtures, and stock."},
    "risk_zone": {"TR": "Deprem Risk Bölgesi", "EN": "Earthquake Risk Zone"},
    "risk_zone_help": {"TR": "Tesisinizin bulunduğu, resmi deprem tehlike haritasındaki risk bölgesi (1. Bölge en riskli).", "EN": "The official seismic hazard zone of your facility's location (Zone 1 is the highest risk)."},
    "yonetmelik": {"TR": "Deprem Yönetmeliği Dönemi", "EN": "Seismic Code Era"},
    "yonetmelik_help": {"TR": "Binanızın inşa edildiği veya en son güçlendirildiği tarihteki geçerli deprem yönetmeliği. Bu, binanızın hasara karşı direncini belirleyen en önemli faktördür.", "EN": "The seismic code in effect at the time your building was constructed or last retrofitted. This is the most critical factor determining its resilience."},
    "btype": {"TR": "Yapı Türü", "EN": "Building Type"},
    "btype_help": {"TR": "Binanın ana taşıyıcı sisteminin türü (Betonarme, Çelik vb.). Prim hesabı için zorunludur.", "EN": "The type of the main structural system of the building (e.g., Reinforced Concrete, Steel). Required for premium calculation."},
    "kat_sayisi": {"TR": "Kat Sayısı", "EN": "Number of Floors"},
    "kat_sayisi_help": {"TR": "Binanın toplam kat adedi. Yüksek binalar, depremde farklı salınım özellikleri gösterir.", "EN": "The total number of floors. Taller buildings exhibit different oscillation characteristics during an earthquake."},
    "zemin": {"TR": "Zemin Sınıfı", "EN": "Soil Class"},
    "zemin_help": {"TR": "Tesisinizin üzerine kurulu olduğu zeminin jeolojik yapısı. Bilmiyorsanız, 'ZC' varsayılan olarak kabul edilir. (ZA: Kaya, ZE: En Yumuşak Zemin)", "EN": "The geological type of the ground beneath your facility. If unknown, 'ZC' is assumed as the default. (ZA: Rock, ZE: Softest Soil)"},
    "duzensizlik": {"TR": "Yapısal Düzensizlik Riski", "EN": "Structural Irregularity Risk"},
    "duzensizlik_help": {"TR": "Binanızda 'yumuşak kat' (örn: alt katı tamamen camlı lobi/dükkan) veya 'kısa kolon' gibi yapısal zafiyetler var mı?", "EN": "Does your building have structural weaknesses like a 'soft story' (e.g., a ground floor with extensive glass windows) or 'short columns'?"},
    "sprinkler": {"TR": "Sprinkler Sistemi Varlığı", "EN": "Sprinkler System Presence"},
    "sprinkler_help": {"TR": "Tesisinizde otomatik yangın söndürme (sprinkler) sistemi bulunuyor mu? Bu, hem yangın riskini azaltır hem de potansiyel bir su hasarı riski oluşturur.", "EN": "Is there an automatic fire sprinkler system in your facility? This both reduces fire risk and creates a potential water damage risk."},
    "gross_profit": {"TR": "Yıllık Brüt Kâr (Gross Profit)", "EN": "Annual Gross Profit"},
    "gross_profit_help": {"TR": "İş durması sonucu kaybedilecek olan, sigortalanabilir brüt kârınızın yıllık tutarı.", "EN": "The annual amount of your insurable gross profit that would be lost in case of a business interruption."},
    "azami_tazminat": {"TR": "Azami Tazminat Süresi", "EN": "Max. Indemnity Period"},
    "azami_tazminat_help": {"TR": "Bir hasar sonrası, kar kaybınızın sigorta tarafından karşılanacağı maksimum süre (genellikle 12, 18 veya 24 ay).", "EN": "The maximum period for which your loss of profit will be covered by insurance after a loss (typically 12, 18, or 24 months)."},
    "isp": {"TR": "İş Sürekliliği Planı (İSP) Varlığı", "EN": "Business Continuity Plan (BCP) Presence"},
    "isp_help": {"TR": "Kriz anında operasyonları devam ettirmek veya hızla yeniden başlatmak için yazılı ve test edilmiş bir planınız var mı?", "EN": "Do you have a written and tested plan to continue or quickly restart operations in a crisis?"},
    "ramp_up": {"TR": "Üretimin Normale Dönme Hızı (Ramp-up)", "EN": "Production Ramp-up Speed"},
    "ramp_up_help": {"TR": "Fiziksel onarım bittikten sonra, üretiminizin tekrar %100 kapasiteye ulaşması ne kadar sürer? (Kalibrasyon, personel, tedarik zinciri vb. faktörler)", "EN": "After physical repairs are complete, how long does it take for your production to reach 100% capacity? (Considering factors like calibration, personnel, supply chain, etc.)"},
    "stok": {"TR": "Bitmiş Ürün Stoğu (Gün)", "EN": "Finished Goods Stock (Days)"},
    "stok_help": {"TR": "Üretim tamamen dursa bile, mevcut stoklarınızla kaç gün boyunca satış yapmaya devam edebilirsiniz?", "EN": "Even if production completely stops, for how many days can you continue making sales from your existing stock?"},
    "bi_wait": {"TR": "BI Bekleme Süresi (gün)", "EN": "BI Waiting Period (days)"},
    "bi_wait_help": {"TR": "Kar kaybı tazminatının ödenmeye başlamasından önce geçmesi gereken, poliçenizdeki gün cinsinden muafiyet süresi.", "EN": "The deductible period in days, as specified in your policy, that must pass before loss of profit compensation begins."},
    "ai_analysis_header": {"TR": "🧠 2. AI Analiz Adımı", "EN": "🧠 2. AI Analysis Step"},
    "ai_analysis_desc": {"TR": "AI, girdiğiniz faaliyet tanımını analiz ederek hesaplama için gerekli olan teknik risk parametrelerini otomatik olarak belirledi.", "EN": "The AI has analyzed your activity description to automatically determine technical risk parameters for the calculation."},
    "results_header": {"TR": "📝 3. Analiz Sonuçları ve Rapor", "EN": "📝 3. Analysis Results and Report"},
    "analysis_header": {"TR": "🔍 4. Poliçe Alternatifleri Analizi", "EN": "🔍 4. Policy Alternatives Analysis"},
    "btn_run": {"TR": "Analizi Çalıştır", "EN": "Run Analysis"},
}

# --- YARDIMCI FONKSİYONLAR ---
def tr(key: str) -> str:
    lang = st.session_state.get("lang", "TR")
    return T.get(key, {}).get(lang, key)

def money(x: float) -> str:
    return f"{x:,.0f} ₺".replace(",", ".")

# --- GİRDİ VE HESAPLAMA MODELLERİ ---
@dataclass
class ScenarioInputs:
    si_pd: int = 250_000_000
    yillik_brut_kar: int = 100_000_000
    rg: int = 3
    faaliyet_tanimi: str = "Plastik enjeksiyon ve kalıp üretimi yapan bir fabrika."
    yapi_turu: str = "Betonarme"
    yonetmelik_donemi: str = "1998-2018 arası"
    kat_sayisi: str = "4-7 kat"
    zemin_sinifi: str = "ZC"
    yapısal_duzensizlik: str = "Yok"
    sprinkler_varligi: str = "Yok"
    azami_tazminat_suresi: int = 365
    isp_varligi: str = "Yok"
    ramp_up_hizi: str = "Orta"
    bitmis_urun_stogu: int = 15
    bi_gun_muafiyeti: int = 14
    icerik_hassasiyeti: str = "Orta"
    ffe_riski: str = "Orta"
    kritik_makine_bagimliligi: str = "Orta"

# --- TEKNİK HESAPLAMA ÇEKİRDEĞİ ---
def get_risk_segment(si_pd: int) -> str:
    if si_pd < 150_000_000: return "KOBİ / Yerel Üretici"
    if si_pd < 1_000_000_000: return "Ticari / Ulusal Ölçekli"
    return "Büyük Kurumsal / Global"

def calculate_pd_ratio(s: ScenarioInputs) -> float:
    base = _DEPREM_ORAN.get(s.rg, 0.13)
    factor = 1.0
    factor *= {"Betonarme": 1.0, "Çelik": 0.85, "Yığma": 1.20, "Diğer": 1.1}.get(s.yapi_turu, 1.0)
    factor *= {"1998 öncesi": 1.25, "1998-2018": 1.00, "2018 sonrası": 0.80}.get(s.yonetmelik_donemi.split(' ')[0], 1.0)
    factor *= {"1-3": 0.95, "4-7": 1.00, "8+": 1.10}.get(s.kat_sayisi.split(' ')[0], 1.0)
    factor *= {"ZC": 1.00, "ZA/ZB": 0.85, "ZD": 1.20, "ZE": 1.50}.get(s.zemin_sinifi.split(' ')[0], 1.0)
    factor *= {"Yok": 1.00, "Var": 1.40}.get(s.yapısal_duzensizlik.split(' ')[0], 1.0)
    factor *= {"Düşük": 0.80, "Orta": 1.00, "Yüksek": 1.30}.get(s.icerik_hassasiyeti, 1.0)
    ffe_factor = {"Düşük": 1.00, "Orta": 1.15, "Yüksek": 1.40}.get(s.ffe_riski, 1.0)
    if s.sprinkler_varligi == "Var": ffe_factor = (ffe_factor - 1) * 0.4 + 1
    factor *= ffe_factor
    return min(0.70, max(0.01, base * factor))

def calculate_bi_downtime(pd_ratio: float, s: ScenarioInputs) -> int:
    base_repair_days = 30 + (pd_ratio * 300)
    operational_factor = 1.0
    operational_factor *= {"Yok": 1.00, "Var": 0.75}.get(s.isp_varligi.split(' ')[0], 1.0)
    operational_factor *= {"Hızlı": 1.10, "Orta": 1.20, "Yavaş": 1.30}.get(s.ramp_up_hizi.split(' ')[0], 1.0)
    operational_factor *= {"Düşük": 1.00, "Orta": 1.25, "Yüksek": 1.60}.get(s.kritik_makine_bagimliligi, 1.0)
    gross_downtime = base_repair_days * operational_factor
    net_downtime = gross_downtime - s.bitmis_urun_stogu
    final_downtime = min(s.azami_tazminat_suresi, net_downtime)
    return max(0, int(final_downtime))

def get_allowed_options(si_pd: int) -> Tuple[List[str], List[float]]:
    koas_opts = list(KOAS_FACTORS.keys())[:9]
    muaf_opts = list(MUAFIYET_FACTORS.keys())[:5]
    if si_pd > 3_500_000_000:
        koas_opts.extend(list(KOAS_FACTORS.keys())[9:])
        muaf_opts.extend(list(MUAFIYET_FACTORS.keys())[5:])
    return koas_opts, muaf_opts

def calculate_premium(si: float, yapi_turu: str, rg: int, koas: str, muaf: float, is_bi: bool = False) -> float:
    base_rate = TARIFE_RATES.get(yapi_turu, TARIFE_RATES["Diğer"])[rg - 1]
    prim_bedeli = min(si, 3_500_000_000)
    if is_bi: return (prim_bedeli * base_rate) / 1000.0
    factor = KOAS_FACTORS.get(koas, 1.0) * MUAFIYET_FACTORS.get(muaf, 1.0)
    return (prim_bedeli * base_rate * factor) / 1000.0

def calculate_net_claim(si_pd: int, hasar_tutari: float, koas: str, muaf_pct: float) -> Dict[str, float]:
    muafiyet_tutari = si_pd * (muaf_pct / 100.0)
    muafiyet_sonrasi_hasar = max(0.0, hasar_tutari - muafiyet_tutari)
    sirket_pay_orani = float(koas.split('/')[0]) / 100.0
    net_tazminat = muafiyet_sonrasi_hasar * sirket_pay_orani
    sigortalida_kalan = hasar_tutari - net_tazminat
    return {"net_tazminat": net_tazminat, "sigortalida_kalan": sigortalida_kalan}

# --- AI FONKSİYONLARI ---
def get_ai_driven_parameters(faaliyet_tanimi: str) -> Dict[str, str]:
    default_params = {"icerik_hassasiyeti": "Orta", "ffe_riski": "Orta", "kritik_makine_bagimliligi": "Orta"}
    if not _GEMINI_AVAILABLE: return default_params
    prompt = f"""Bir risk analisti olarak, aşağıdaki endüstriyel tesis tanımını analiz et ve şu üç risk parametresini 'Düşük', 'Orta' veya 'Yüksek' olarak skorla. Sadece JSON formatında cevap ver. Tesis Tanımı: "{faaliyet_tanimi}"\n\nJSON Formatı:\n{{\n  "icerik_hassasiyeti": "...",\n  "ffe_riski": "...",\n  "kritik_makine_bagimliligi": "..."\n}}"""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        params = json.loads(response.text)
        for key in default_params:
            if params.get(key) not in ['Düşük', 'Orta', 'Yüksek']: params[key] = default_params[key]
        return params
    except Exception: return default_params

def generate_report(s: ScenarioInputs, pd_ratio: float, bi_days: int, bi_damage: float) -> str:
    if not _GEMINI_AVAILABLE: return "AI servisi aktif değil. Lütfen API anahtarınızı kontrol edin."
    
    risk_segment = get_risk_segment(s.si_pd)
    icow_limit_suggestion = money(bi_damage * 0.25)
    cbi_limit_suggestion = money(s.yillik_brut_kar * 0.15)
    genisletilmis_bi_suggestion = money(s.yillik_brut_kar * 0.20)
    
    prompt_template = f"""
Sen, sigorta şirketleri için çalışan kıdemli bir deprem risk mühendisi ve hasar uzmanısın. Görevin, aşağıda bilgileri verilen endüstriyel tesis için beklenen bir deprem sonrası oluşacak hasarları, teknik ve profesyonel bir dille raporlamaktır. Raporu "Maddi Hasar (PD) Değerlendirmesi", "İş Durması (BI) Değerlendirmesi" ve "Risk Danışmanlığı ve Aksiyon Önerileri" olmak üzere üç ana başlık altında, madde işaretleri kullanarak sun. Faaliyet koluna ve girilen tüm gelişmiş risk parametrelerine özel, somut ve gerçekçi hasar örnekleri ver.
"Risk Danışmanlığı" bölümünde, analiz edilen firmanın risk segmentine ({risk_segment}) göre özel ve nicel tavsiyelerde bulun.

**Tesis Bilgileri ve Birincil Risk Faktörleri:**
- **Faaliyet Tanımı:** {s.faaliyet_tanimi}
- **Deprem Yönetmeliği Dönemi:** {s.yonetmelik_donemi}
- **Zemin Sınıfı:** {s.zemin_sinifi}
- **Yapısal Düzensizlik:** {s.yapısal_duzensizlik}
- **İş Sürekliliği Planı:** {s.isp_varligi}
- **Sprinkler Sistemi:** {s.sprinkler_varligi}

**AI Tarafından Skorlanan Parametreler:**
- **İçerik Hassasiyeti:** {s.icerik_hassasiyeti}
- **Deprem Sonrası Yangın (FFE) Riski:** {s.ffe_riski}
- **Kritik Makine Bağımlılığı:** {s.kritik_makine_bagimliligi}

**Hesaplanan Senaryo Değerleri:**
- **Beklenen Maddi Hasar Oranı:** {pd_ratio:.1%}
- **Tahmini Toplam Kesinti Süresi:** {bi_days} gün
"""
    if risk_segment == "KOBİ / Yerel Üretici":
        prompt_template += f"\n**Danışmanlık Notu:** Bu segmentteki bir firma için, Artan Çalışma Masrafları (ICOW) teminatı kritiktir. Yaklaşık **{icow_limit_suggestion}** limitli bir ICOW teminatı önerisi yap."
    elif risk_segment == "Ticari / Ulusal Ölçekli":
        prompt_template += f"\n**Danışmanlık Notu:** Bu segmentteki bir firma için, Tedarikçi Riski (CBI) önemlidir. Yaklaşık **{cbi_limit_suggestion}** limitli bir CBI teminatı önerisi yap ve 420 Milyon TL üzeri riskler için 'Tazminat Limitli Deprem Teminatı' seçeneğini açıkla."
    else: # Büyük Kurumsal / Global
        prompt_template += f"\n**Danışmanlık Notu:** Bu segmentteki bir firma için, sistemik riskler ön plandadır. Tedarikçi/Müşteri (CBI), Kamu Hizmetleri ve Ulaşım Engeli gibi teminatların önemini vurgula. Yaklaşık **{genisletilmis_bi_suggestion}** limitli bir 'Genişletilmiş Kar Kaybı Teminatları' paketi öner."

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt_template)
        return response.text
    except Exception as e:
        st.sidebar.error(f"AI Raporu oluşturulamadı: {e}", icon="🤖")
        return "AI Raporu oluşturulurken bir hata oluştu."

# --- STREAMLIT UYGULAMASI ---
def main():
    st.set_page_config(page_title=tr("title"), layout="wide", page_icon="🏗️")
    st.title(f"🏗️ {tr('title')}")

    s_inputs = ScenarioInputs()

    st.header(tr("inputs_header"))
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader(tr("base_header"))
        s_inputs.faaliyet_tanimi = st.text_area(tr("activity_desc"), s_inputs.faaliyet_tanimi, placeholder=tr("activity_placeholder"), height=150, help=tr("activity_desc_help"))
        s_inputs.si_pd = st.number_input(tr("si_pd"), min_value=1_000_000, value=s_inputs.si_pd, step=10_000_000, format="%d", help=tr("si_pd_help"))
        s_inputs.yillik_brut_kar = st.number_input(tr("gross_profit"), min_value=0, value=s_inputs.yillik_brut_kar, step=10_000_000, format="%d", help=tr("gross_profit_help"))
        s_inputs.rg = st.select_slider(tr("risk_zone"), options=[1,2,3,4,5,6,7], value=s_inputs.rg, help=tr("risk_zone_help"))
        s_inputs.yapi_turu = st.selectbox(tr("btype"), ["Betonarme", "Çelik", "Yığma", "Diğer"], help=tr("btype_help"))

    with col2:
        st.subheader(tr("pd_header"))
        s_inputs.yonetmelik_donemi = st.selectbox(tr("yonetmelik"), ["1998-2018 arası (Varsayılan)", "2018 sonrası (Yeni Yönetmelik)", "1998 öncesi (Eski Yönetmelik)"], help=tr("yonetmelik_help"))
        s_inputs.kat_sayisi = st.selectbox(tr("kat_sayisi"), ["4-7 kat (Varsayılan)", "1-3 kat", "8+ kat"], help=tr("kat_sayisi_help"))
        s_inputs.zemin_sinifi = st.selectbox(tr("zemin"), ["ZC (Varsayılan)", "ZA/ZB (Kaya/Sıkı Zemin)", "ZD (Orta Gevşek)", "ZE (Yumuşak/Gevşek)"], help=tr("zemin_help"))
        s_inputs.yapısal_duzensizlik = st.selectbox(tr("duzensizlik"), ["Yok (Varsayılan)", "Var"], help=tr("duzensizlik_help"))
        s_inputs.sprinkler_varligi = st.radio(tr("sprinkler"), ["Yok", "Var"], index=0, horizontal=True, help=tr("sprinkler_help"))

    with col3:
        st.subheader(tr("bi_header"))
        s_inputs.azami_tazminat_suresi = st.selectbox(tr("azami_tazminat"), [365, 540, 730], format_func=lambda x: f"{int(x/30)} Ay", help=tr("azami_tazminat_help"))
        s_inputs.isp_varligi = st.selectbox(tr("isp"), ["Yok (Varsayılan)", "Var (Test Edilmemiş)", "Var (Test Edilmiş)"], help=tr("isp_help"))
        s_inputs.ramp_up_hizi = st.selectbox(tr("ramp_up"), ["Orta (Varsayılan)", "Hızlı", "Yavaş"], help=tr("ramp_up_help"))
        s_inputs.bitmis_urun_stogu = st.number_input(tr("stok"), value=s_inputs.bitmis_urun_stogu, min_value=0, help=tr("stok_help"))
        s_inputs.bi_gun_muafiyeti = st.number_input(tr("bi_wait"), min_value=0, value=s_inputs.bi_gun_muafiyeti, step=1, help=tr("bi_wait_help"))
    
    st.markdown("---")
    run_button = st.button(f"🚀 {tr('btn_run')}", use_container_width=True, type="primary")

    if 'run_clicked' not in st.session_state:
        st.session_state.run_clicked = False

    if run_button:
        st.session_state.run_clicked = True
        st.session_state.s_inputs = s_inputs

    if st.session_state.run_clicked:
        s_inputs = st.session_state.s_inputs
        
        with st.spinner("AI, tesisinizi analiz ediyor ve risk parametrelerini atıyor..."):
            ai_params = get_ai_driven_parameters(s_inputs.faaliyet_tanimi)
            s_inputs.icerik_hassasiyeti = ai_params["icerik_hassasiyeti"]
            s_inputs.ffe_riski = ai_params["ffe_riski"]
            s_inputs.kritik_makine_bagimliligi = ai_params["kritik_makine_bagimliligi"]

        st.header(tr("ai_analysis_header"))
        risk_segment = get_risk_segment(s_inputs.si_pd)
        st.info(f"**AI Analiz Özeti:** Tesisiniz, girilen sigorta bedeline göre **'{risk_segment}'** segmentinde değerlendirilmiştir. Faaliyet tanımınız analiz edilerek aşağıdaki parametreler hesaplamaya otomatik olarak dahil edilmiştir:", icon="💡")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("İçerik Hassasiyeti", s_inputs.icerik_hassasiyeti, help="AI, faaliyet tanımınıza göre tesis içindeki varlıkların (makine, emtia) hasara karşı hassasiyetini bu şekilde skorladı.")
        c2.metric("Deprem Sonrası Yangın Riski", s_inputs.ffe_riski, help="AI, faaliyetinizdeki yanıcı madde yoğunluğuna göre deprem sonrası ikincil bir yangın çıkma riskini bu şekilde skorladı.")
        c3.metric("Kritik Makine Bağımlılığı", s_inputs.kritik_makine_bagimliligi, help="AI, üretiminizin ne kadar özel ve yeri zor dolacak makinelere bağlı olduğunu bu şekilde skorladı.")
        
        with st.expander("🤖 AI'a Gönderilen Komutu Gör"):
            st.code(f"""Bir risk analisti olarak, aşağıdaki endüstriyel tesis tanımını analiz et ve şu üç risk parametresini 'Düşük', 'Orta' veya 'Yüksek' olarak skorla. Sadece JSON formatında cevap ver. Tesis Tanımı: "{s_inputs.faaliyet_tanimi}"...""", language="text")

        pd_ratio = calculate_pd_ratio(s_inputs)
        bi_days = calculate_bi_downtime(pd_ratio, s_inputs)
        pd_damage_amount = s_inputs.si_pd * pd_ratio
        net_bi_days = max(0, bi_days - s_inputs.bi_gun_muafiyeti)
        bi_damage_amount = (s_inputs.yillik_brut_kar / 365.0) * net_bi_days if s_inputs.yillik_brut_kar > 0 else 0

        st.header(tr("results_header"))
        with st.spinner("AI Deprem Hasar Uzmanı, nihai raporu ve tavsiyeleri hazırlıyor..."):
            report = generate_report(s_inputs, pd_ratio, bi_days, bi_damage_amount)
            st.markdown(report, unsafe_allow_html=True)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Beklenen PD Hasar Tutarı", money(pd_damage_amount), f"{pd_ratio:.2%}")
        m2.metric("Beklenen Net Kesinti Süresi", f"{bi_days} gün")
        m3.metric("Beklenen BI Hasar Tutarı", money(bi_damage_amount), f"{net_bi_days} gün tazmin edilebilir")
        
        st.markdown("---")
        st.header(tr("analysis_header"))
        
        koas_opts, muaf_opts = get_allowed_options(s_inputs.si_pd)
        results = []
        for koas in koas_opts:
            for muaf in muaf_opts:
                prim_pd = calculate_premium(s_inputs.si_pd, s_inputs.yapi_turu, s_inputs.rg, koas, muaf)
                prim_bi = calculate_premium(s_inputs.yillik_brut_kar, s_inputs.yapi_turu, s_inputs.rg, koas, muaf, is_bi=True)
                toplam_prim = prim_pd + prim_bi
                pd_claim = calculate_net_claim(s_inputs.si_pd, pd_damage_amount, koas, muaf)
                total_damage = pd_damage_amount + bi_damage_amount
                total_payout = pd_claim["net_tazminat"] + bi_damage_amount
                retained_risk = total_damage - total_payout
                
                results.append({
                    "Poliçe Yapısı": f"{koas} / {muaf}%", "Yıllık Toplam Prim": toplam_prim,
                    "Toplam Net Tazminat": total_payout, "Sigortalıda Kalan Risk": retained_risk,
                })
        df = pd.DataFrame(results)

        tab1, tab2 = st.tabs([tr("table_analysis"), tr("visual_analysis")])
        with tab1:
            st.markdown("Aşağıdaki tabloda, tüm olası poliçe yapıları için **maliyet (prim)** ve hasar sonrası **net durumunuzu** karşılaştırabilirsiniz.")
            st.dataframe(df.style.format(money, subset=["Yıllık Toplam Prim", "Toplam Net Tazminat", "Sigortalıda Kalan Risk"]), use_container_width=True)
        
        with tab2:
            st.markdown("Bu grafik, en verimli poliçe alternatifini bulmanıza yardımcı olur. **Amaç, sol alt köşeye en yakın noktayı bulmaktır.** Bu noktalar, hem **düşük prim** ödeyeceğiniz hem de hasar anında **şirketinizde en az riskin kalacağı** en verimli seçenekleri temsil eder.")
            fig = px.scatter(
                df, x="Yıllık Toplam Prim", y="Sigortalıda Kalan Risk",
                color="Sigortalıda Kalan Risk", color_continuous_scale=px.colors.sequential.Reds_r,
                hover_data=["Poliçe Yapısı", "Toplam Net Tazminat"], title="Poliçe Alternatifleri Maliyet-Risk Analizi"
            )
            fig.update_traces(marker=dict(size=10, line=dict(width=1, color='DarkSlateGrey')))
            fig.update_layout(xaxis_title="Yıllık Toplam Prim (Düşük olması hedeflenir)", yaxis_title="Hasarda Şirketinizde Kalacak Risk (Düşük olması hedeflenir)")
            st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
