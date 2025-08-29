# -*- coding: utf-8 -*-
#
# TariffEQ – Profesyonel ve AI Destekli PD & BI Hasar Analiz Aracı
# =======================================================================
# Bu Streamlit uygulaması, reasürans ve katastrofik modelleme metodolojilerinden
# esinlenerek geliştirilmiş parametreler ve tarifeye tam uyumlu hesaplama
# mantığı ile ticari/sınai rizikolar için profesyonel seviyede bir deprem
# hasar analizi sunar.
#
# GÜNCEL REVİZYON NOTLARI (Ağustos 2025 - v2.2):
# 1. BI Modeli Zenginleştirildi: İş Durması hesaplamasına 'Ekipman Tedarik Gecikmesi'
#    ve 'Bölgesel Altyapı Çöküşü' gibi ikincil risk faktörleri dahil edildi.
# 2. Uluslararası Vaka Entegrasyonu: Northridge (1994) depremi tecrübesi,
#    eski tip çelik yapılar için potansiyel bir zafiyet olarak modele eklendi.
# 3. AI Analist Rolü Keskinleştirildi: AI, artık tüm 'gizli zeka' kurallarını
#    raporunda doğrudan referans vererek açıklamak üzere yeniden eğitildi.
# 4. UI Düzeltmesi: Eksik bırakılan tüm girdi parametreleri arayüze eklendi.

import streamlit as st
import pandas as pd
import plotly.express as px
from dataclasses import dataclass
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
    "inputs_header": {"TR": "📊 1. Senaryo Girdileri", "EN": "📊 1. Scenario Inputs"},
    "base_header": {"TR": "🏭 Temel Tesis Bilgileri", "EN": "🏭 Basic Facility Information"},
    "pd_header": {"TR": "🧱 PD Risk Parametreleri", "EN": "🧱 PD Risk Parameters"},
    "bi_header": {"TR": "📈 BI Risk Parametreleri", "EN": "📈 BI Risk Parameters"},
    "activity_desc": {"TR": "Tesisin Faaliyet Tanımı", "EN": "Facility Activity Description"},
    "activity_desc_help": {"TR": "AI'ın riskleri doğru analiz etmesi için faaliyetinizi kısaca açıklayın (örn: 'metal levha presleme ve otomotiv parça üretimi').", "EN": "Briefly describe your operations for accurate AI risk analysis (e.g., 'metal sheet pressing and automotive parts manufacturing')."},
    "si_pd": {"TR": "PD Toplam Sigorta Bedeli", "EN": "PD Total Sum Insured"},
    "si_pd_help": {"TR": "Bina, makine, emtia dahil tüm maddi varlıkların toplam güncel değeri.", "EN": "Total current value of all physical assets, including building, machinery, and stock."},
    "risk_zone": {"TR": "Deprem Risk Bölgesi", "EN": "Earthquake Risk Zone"},
    "risk_zone_help": {"TR": "Tesisin bulunduğu resmi deprem tehlike bölgesi (1 en riskli).", "EN": "The official seismic hazard zone of the facility (1 is the highest risk)."},
    "yonetmelik": {"TR": "Deprem Yönetmeliği Dönemi", "EN": "Seismic Code Era"},
    "yonetmelik_help": {"TR": "Binanın inşaat veya güçlendirme yılına göre ait olduğu yönetmelik. Bina dayanıklılığını belirler.", "EN": "The code corresponding to the building's construction/retrofit year. Determines structural resilience."},
    "btype": {"TR": "Yapı Türü", "EN": "Building Type"},
    "btype_help": {"TR": "Binanın ana taşıyıcı sistemi. Prim hesabında kullanılır.", "EN": "The main structural system of the building. Used in premium calculation."},
    "kat_sayisi": {"TR": "Kat Sayısı", "EN": "Number of Floors"},
    "kat_sayisi_help": {"TR": "Binanın toplam kat adedi.", "EN": "The total number of floors in the building."},
    "zemin": {"TR": "Zemin Sınıfı", "EN": "Soil Class"},
    "zemin_help": {"TR": "Tesisin zemin yapısı (ZA: Kaya, ZE: En Yumuşak). Bilinmiyorsa 'ZC' seçilebilir.", "EN": "The facility's soil type (ZA: Rock, ZE: Softest). If unknown, select 'ZC'."},
    "duzensizlik": {"TR": "Yapısal Düzensizlik Riski", "EN": "Structural Irregularity Risk"},
    "duzensizlik_help": {"TR": "'Yumuşak kat', 'bitişik farklı bina' veya 'kısa kolon' gibi bilinen bir yapısal zafiyet var mı?", "EN": "Are there known structural weaknesses like 'soft story', 'adjacent different building' or 'short columns'?"},
    "sprinkler": {"TR": "Sprinkler Sistemi Varlığı", "EN": "Sprinkler System Presence"},
    "sprinkler_help": {"TR": "Otomatik yangın söndürme sistemi var mı? Yangın riskini azaltır.", "EN": "Is there an automatic fire sprinkler system? It reduces fire risk."},
    "gross_profit": {"TR": "Yıllık Brüt Kâr (GP)", "EN": "Annual Gross Profit (GP)"},
    "gross_profit_help": {"TR": "İş durması halinde kaybedilecek, sigortalanabilir yıllık brüt kâr.", "EN": "The insurable annual gross profit that would be lost during an interruption."},
    "azami_tazminat": {"TR": "Azami Tazminat Süresi", "EN": "Max. Indemnity Period"},
    "azami_tazminat_help": {"TR": "Hasar sonrası kar kaybınızın sigorta tarafından karşılanacağı maksimum süre.", "EN": "The maximum period for which loss of profit is covered by insurance post-loss."},
    "isp": {"TR": "İş Sürekliliği Planı (İSP)", "EN": "Business Continuity Plan (BCP)"},
    "isp_help": {"TR": "Kriz anında operasyonları sürdürmek için yazılı ve test edilmiş bir plan var mı?", "EN": "Is there a written, tested plan to continue operations during a crisis?"},
    "ramp_up": {"TR": "Üretimin Normale Dönme Hızı", "EN": "Production Ramp-up Speed"},
    "ramp_up_help": {"TR": "Onarım sonrası üretimin tekrar %100 kapasiteye ulaşma hızı.", "EN": "The speed at which production returns to 100% capacity after repairs."},
    "stok": {"TR": "Bitmiş Ürün Stoğu (Gün)", "EN": "Finished Goods Stock (Days)"},
    "stok_help": {"TR": "Üretim dursa bile, mevcut stokla kaç gün satış yapabilirsiniz?", "EN": "For how many days can you continue sales with existing stock if production stops?"},
    "bi_wait": {"TR": "BI Bekleme Süresi (Gün)", "EN": "BI Waiting Period (days)"},
    "bi_wait_help": {"TR": "Poliçedeki, kar kaybı tazminatı başlamadan önce geçmesi gereken gün sayısı.", "EN": "The policy's deductible period in days before loss of profit compensation starts."},
    "ai_analysis_header": {"TR": "🧠 2. AI Analiz Adımı ve Gerekçelendirme", "EN": "🧠 2. AI Analysis Step & Justification"},
    "results_header": {"TR": "📝 3. Analiz Sonuçları", "EN": "📝 3. Analysis Results"},
    "analysis_header": {"TR": "🔍 4. Poliçe Alternatifleri Analizi", "EN": "🔍 4. Policy Alternatives Analysis"},
    "btn_run": {"TR": "Analizi Çalıştır", "EN": "Run Analysis"},
    "table_analysis": {"TR": "📈 Tablo Analizi", "EN": "📈 Table Analysis"},
    "visual_analysis": {"TR": "📊 Görsel Analiz", "EN": "📊 Visual Analysis"},
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
    rg: int = 1
    faaliyet_tanimi: str = "Adapazarı'nda kurulu, 1995 yapımı, ilaç ve hassas kimyasallar üreten betonarme bir tesis."
    yapi_turu: str = "Betonarme"
    yonetmelik_donemi: str = "1998 öncesi (Eski Yönetmelik)"
    kat_sayisi: str = "1-3 kat"
    zemin_sinifi: str = "ZE"
    yapısal_duzensizlik: str = "Var"
    sprinkler_varligi: str = "Var"
    azami_tazminat_suresi: int = 365
    isp_varligi: str = "Var (Test Edilmiş)"
    ramp_up_hizi: str = "Orta"
    bitmis_urun_stogu: int = 30
    bi_gun_muafiyeti: int = 21
    icerik_hassasiyeti: str = "Orta"
    ffe_riski: str = "Orta"
    kritik_makine_bagimliligi: str = "Orta"

# --- TEKNİK HESAPLAMA ÇEKİRDEĞİ ---
def get_risk_segment(si_pd: int) -> str:
    if si_pd < 150_000_000: return "KOBİ / Yerel Üretici"
    if si_pd < 1_000_000_000: return "Ticari / Ulusal Ölçekli"
    return "Büyük Kurumsal / Global"

def calculate_pd_ratio(s: ScenarioInputs) -> float:
    FACTORS = {
        "yapi_turu": {"Betonarme": 1.0, "Çelik": 0.85, "Yığma": 1.20, "Diğer": 1.1},
        "yonetmelik": {"1998 öncesi": 1.25, "1998-2018": 1.00, "2018 sonrası": 0.80},
        "kat_sayisi": {"1-3": 0.95, "4-7": 1.00, "8+": 1.10},
        "zemin": {"ZC": 1.00, "ZA/ZB": 0.85, "ZD": 1.20, "ZE": 1.50},
        "duzensizlik": {"Yok": 1.00, "Var": 1.40},
        "icerik_hassasiyeti": {"Düşük": 0.80, "Orta": 1.00, "Yüksek": 1.30},
        "ffe_riski": {"Düşük": 1.00, "Orta": 1.15, "Yüksek": 1.40}
    }
    base = _DEPREM_ORAN.get(s.rg, 0.13)
    factor = 1.0
    factor *= FACTORS["yapi_turu"].get(s.yapi_turu, 1.0)
    factor *= FACTORS["yonetmelik"].get(s.yonetmelik_donemi.split(' ')[0], 1.0)
    factor *= FACTORS["kat_sayisi"].get(s.kat_sayisi.split(' ')[0], 1.0)
    factor *= FACTORS["zemin"].get(s.zemin_sinifi.split(' ')[0], 1.0)
    factor *= FACTORS["duzensizlik"].get(s.yapısal_duzensizlik, 1.0)
    factor *= FACTORS["icerik_hassasiyeti"].get(s.icerik_hassasiyeti, 1.0)
    
    ffe_factor = FACTORS["ffe_riski"].get(s.ffe_riski, 1.0)
    if s.sprinkler_varligi == "Var":
        ffe_factor = (ffe_factor - 1) * 0.4 + 1
    factor *= ffe_factor
    
    # VAKA #1 (Türkiye): Eski tip prefabrik zafiyeti (Referans: PEER 2000-03 Raporu)
    if s.yapi_turu == "Betonarme" and "1998 öncesi" in s.yonetmelik_donemi:
        factor *= 1.20
        
    # VAKA #4 (Uluslararası): Northridge Kırılgan Kaynak Zafiyeti (Referans: FEMA/SAC Raporları, 1995)
    if s.yapi_turu == "Çelik" and "1998 öncesi" in s.yonetmelik_donemi:
        factor *= 1.15

    # Zemin Sıvılaşması Riski (Referans: Adapazarı 1999 Vaka Analizleri)
    if s.zemin_sinifi in ["ZD", "ZE"]:
        factor *= 1.30

    return min(0.70, max(0.01, base * factor))

def calculate_bi_downtime(pd_ratio: float, s: ScenarioInputs) -> Tuple[int, int]:
    FACTORS = {
        "isp": {"Yok": 1.00, "Var (Test Edilmemiş)": 0.85, "Var (Test Edilmiş)": 0.70},
        "ramp_up": {"Hızlı": 1.10, "Orta": 1.20, "Yavaş": 1.30},
        "makine_bagimliligi": {"Düşük": 1.00, "Orta": 1.25, "Yüksek": 1.70}
    }
    base_repair_days = 30 + (pd_ratio * 300)
    operational_factor = 1.0
    operational_factor *= FACTORS["isp"].get(s.isp_varligi, 1.0)
    operational_factor *= FACTORS["ramp_up"].get(s.ramp_up_hizi, 1.0)
    operational_factor *= FACTORS["makine_bagimliligi"].get(s.kritik_makine_bagimliligi, 1.0)
    gross_downtime = int(base_repair_days * operational_factor)
    
    if s.rg in [1, 2]:
        gross_downtime = int(gross_downtime * 1.15)

    net_downtime_before_indemnity = gross_downtime - s.bitmis_urun_stogu
    final_downtime = min(s.azami_tazminat_suresi, net_downtime_before_indemnity)
    return max(0, gross_downtime), max(0, int(final_downtime))

def get_allowed_options(si_pd: int) -> Tuple[List[str], List[float]]:
    koas_opts = list(KOAS_FACTORS.keys())[:9]; muaf_opts = list(MUAFIYET_FACTORS.keys())[:5]
    if si_pd > 3_500_000_000:
        koas_opts.extend(list(KOAS_FACTORS.keys())[9:]); muaf_opts.extend(list(MUAFIYET_FACTORS.keys())[5:])
    return koas_opts, muaf_opts

def calculate_premium(si: float, yapi_turu: str, rg: int, koas: str, muaf: float, is_bi: bool = False) -> float:
    base_rate = TARIFE_RATES.get(yapi_turu, TARIFE_RATES["Diğer"])[rg - 1]
    prim_bedeli = min(si, 3_500_000_000) if not is_bi else si
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

# --- AI FONKSİYONLARI ---
@st.cache_data(show_spinner=False)
def get_ai_driven_parameters(faaliyet_tanimi: str) -> Dict[str, str]:
    default_params = {"icerik_hassasiyeti": "Orta", "ffe_riski": "Orta", "kritik_makine_bagimliligi": "Orta"}
    if not _GEMINI_AVAILABLE: return default_params
    prompt = f"""
    Rolün: Kıdemli bir deprem risk mühendisi.
    Görevin: Tesis tanımını analiz edip, 3 risk parametresini skorlamak.
    Kısıtlar: Yanıtın SADECE JSON formatında olmalı.
    Tesis Tanımı: "{faaliyet_tanimi}"
    Önemli Notlar:
    1. Modern bir yapı bile olsa, faaliyet türü (örn: lojistik, üretim) içindeki ekipman ve raf sistemleri nedeniyle 'içerik hassasiyeti' ve 'kritik makine bağımlılığı' yüksek olabilir. (Referans: Kahramanmaraş Depremleri Gözlemleri)
    2. Eğer faaliyet "yarı iletken", "elektronik", "ilaç", "laboratuvar", "hassas optik" gibi ifadeler içeriyorsa, bu tesislerdeki en büyük riskin operasyonel hassasiyet olduğunu bil. Bu durumda 'İçerik Hassasiyeti' ve 'Kritik Makine Bağımlılığı' parametrelerini tereddütsüz 'Yüksek' olarak ata. (Referans: Tayvan 1999, Japonya 2011 Depremleri)
    Skor Tanımları:
    - icerik_hassasiyeti: (Yüksek: Hassas elektronik, ilaç, kimyasallar, devrilebilecek yüksek raf sistemleri).
    - ffe_riski: (Yüksek: Yoğun solvent, kimyasal, yanıcı gaz/toz, plastik hammadde).
    - kritik_makine_bagimliligi: (Yüksek: Özel sipariş pres, fırın, reaktör, otomasyon hattı).
    SADECE ŞU JSON'u DÖNDÜR: {{"icerik_hassasiyeti": "...", "ffe_riski": "...", "kritik_makine_bagimliligi": "..."}}
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        generation_config = {"temperature": 0.1, "top_p": 0.8, "response_mime_type": "application/json"}
        response = model.generate_content(prompt, generation_config=generation_config)
        params = json.loads(response.text)
        for key in default_params:
            if params.get(key) not in ['Düşük', 'Orta', 'Yüksek']: params[key] = default_params[key]
        return params
    except Exception as e:
        st.session_state.errors.append(f"AI Parametre Hatası: {str(e)}\n{traceback.format_exc()}")
        return default_params

@st.cache_data(show_spinner=False)
def generate_report(s: ScenarioInputs, pd_ratio: float, gross_bi_days: int) -> str:
    if not _GEMINI_AVAILABLE: return "AI servisi aktif değil."
    prompt_template = f"""
    Rolün: Uzman bir risk analisti.
    Görevin: Sağlanan verileri kullanarak, teknik bir hasar analizi raporu oluşturmak.
    Kesin Kural: ASLA tavsiye, öneri veya aksiyon listesi sunma. Sadece mevcut durum tespitini ve bu tespite yol açan gerekçeleri, sağlanan referansları kullanarak açıkla.
    Gerekçelendirme Talimatı: Aşağıdaki her bir madde için, eğer ilgili koşul sağlanıyorsa, raporunda bu durumu ve referansını AÇIKÇA belirtmek zorundasın.
    - `1998 öncesi Betonarme` ise: Kocaeli Depremi tecrübesiyle bilinen çatı sistemi zafiyetine atıfta bulun.
    - `1998 öncesi Çelik` ise: Northridge (1994) depreminde görülen kırılgan kaynak birleşimi riskine atıfta bulun.
    - `Zemin Sınıfı ZD veya ZE` ise: Adapazarı (1999) örneğindeki gibi zemin sıvılaşması potansiyeline atıfta bulun.
    - `İçerik Hassasiyeti/Kritik Makine Bağımlılığı Yüksek` ise: Faaliyet tanımına (örn: lojistik, yüksek teknoloji) bağlayarak Kahramanmaraş, Tayvan veya Japonya depremi tecrübelerine atıfta bulun.
    - `BI Süresi Hesabı` için: Yüksek riskli bölgedeki altyapı çöküşü (İskenderun Limanı örneği) ve uzun termin süreli ekipman bekleme risklerini gerekçe olarak sun.
    ---
    **ANALİZ EDİLECEK VERİLER:**
    - Girdi Verileri: Faaliyet: {s.faaliyet_tanimi}, Yapı: {s.yapi_turu}, Yönetmelik: {s.yonetmelik_donemi}, Zemin: {s.zemin_sinifi}, Düzensizlik: {s.yapısal_duzensizlik}, Risk Bölgesi: {s.rg}
    - AI Parametreleri: İçerik Hassasiyeti: {s.icerik_hassasiyeti}, Kritik Makine Bağımlılığı: {s.kritik_makine_bagimliligi}
    - Hesaplanan Sonuçlar: Beklenen PD Oranı (PML): {pd_ratio:.1%}, Brüt İş Durması Süresi: {gross_bi_days} gün
    ---
    LÜTFEN RAPORU OLUŞTUR:
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt_template, generation_config={"temperature": 0.3})
        return response.text
    except Exception as e:
        st.session_state.errors.append(f"AI Rapor Hatası: {str(e)}\n{traceback.format_exc()}")
        return "AI Analiz Raporu oluşturulurken bir hata oluştu."

# --- STREAMLIT UYGULAMASI ---
def main():
    st.set_page_config(page_title=tr("title"), layout="wide", page_icon="🏗️")
    if 'run_clicked' not in st.session_state: st.session_state.run_clicked = False
    if 'errors' not in st.session_state: st.session_state.errors = []
    st.title(f"🏗️ {tr('title')}")
    s_inputs = ScenarioInputs()
    st.header(tr("inputs_header"))
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader(tr("base_header"))
        s_inputs.faaliyet_tanimi = st.text_area(tr("activity_desc"), s_inputs.faaliyet_tanimi, height=150, help=tr("activity_desc_help"))
        s_inputs.si_pd = st.number_input(tr("si_pd"), min_value=1_000_000, value=s_inputs.si_pd, step=10_000_000, format="%d", help=tr("si_pd_help"))
        s_inputs.yillik_brut_kar = st.number_input(tr("gross_profit"), min_value=0, value=s_inputs.yillik_brut_kar, step=10_000_000, format="%d", help=tr("gross_profit_help"))
        s_inputs.rg = st.select_slider(tr("risk_zone"), options=list(range(1, 8)), value=s_inputs.rg, help=tr("risk_zone_help"))
        s_inputs.yapi_turu = st.selectbox(tr("btype"), ["Betonarme", "Çelik", "Yığma", "Diğer"], help=tr("btype_help"))

    with col2:
        st.subheader(tr("pd_header"))
        s_inputs.yonetmelik_donemi = st.selectbox(tr("yonetmelik"), ["1998 öncesi (Eski Yönetmelik)", "1998-2018 arası (Varsayılan)", "2018 sonrası (Yeni Yönetmelik)"], help=tr("yonetmelik_help"))
        s_inputs.kat_sayisi = st.selectbox(tr("kat_sayisi"), ["1-3 kat", "4-7 kat (Varsayılan)", "8+ kat"], help=tr("kat_sayisi_help"))
        s_inputs.zemin_sinifi = st.selectbox(tr("zemin"), ["ZE", "ZD", "ZC (Varsayılan)", "ZA/ZB (Kaya/Sıkı Zemin)"], help=tr("zemin_help"))
        s_inputs.yapısal_duzensizlik = st.selectbox(tr("duzensizlik"), ["Var", "Yok"], help=tr("duzensizlik_help"))
        s_inputs.sprinkler_varligi = st.radio(tr("sprinkler"), ["Yok", "Var"], index=1, horizontal=True, help=tr("sprinkler_help"))

    with col3:
        st.subheader(tr("bi_header"))
        s_inputs.azami_tazminat_suresi = st.selectbox(tr("azami_tazminat"), [365, 540, 730], index=0, format_func=lambda x: f"{int(x/30)} Ay", help=tr("azami_tazminat_help"))
        s_inputs.isp_varligi = st.selectbox(tr("isp"), ["Yok (Varsayılan)", "Var (Test Edilmemiş)", "Var (Test Edilmiş)"], index=2, help=tr("isp_help"))
        s_inputs.ramp_up_hizi = st.selectbox(tr("ramp_up"), ["Orta (Varsayılan)", "Hızlı", "Yavaş"], help=tr("ramp_up_help"))
        s_inputs.bitmis_urun_stogu = st.number_input(tr("stok"), value=s_inputs.bitmis_urun_stogu, min_value=0, help=tr("stok_help"))
        s_inputs.bi_gun_muafiyeti = st.number_input(tr("bi_wait"), min_value=0, value=s_inputs.bi_gun_muafiyeti, step=1, help=tr("bi_wait_help"))

    st.markdown("---")
    if st.button(f"🚀 {tr('btn_run')}", use_container_width=True, type="primary"):
        st.session_state.run_clicked = True
        st.session_state.s_inputs = s_inputs
        st.session_state.errors = []

    if st.session_state.run_clicked:
        s_inputs = st.session_state.s_inputs
        with st.spinner("AI, tesisinizi analiz ediyor ve risk parametrelerini atıyor..."):
            ai_params = get_ai_driven_parameters(s_inputs.faaliyet_tanimi)
            s_inputs.icerik_hassasiyeti, s_inputs.ffe_riski, s_inputs.kritik_makine_bagimliligi = ai_params["icerik_hassasiyeti"], ai_params["ffe_riski"], ai_params["kritik_makine_bagimliligi"]
        
        pd_ratio = calculate_pd_ratio(s_inputs)
        gross_bi_days, net_bi_days_raw = calculate_bi_downtime(pd_ratio, s_inputs)
        pd_damage_amount = s_inputs.si_pd * pd_ratio
        net_bi_days_final = max(0, net_bi_days_raw - s_inputs.bi_gun_muafiyeti)
        bi_damage_amount = (s_inputs.yillik_brut_kar / 365.0) * net_bi_days_final if s_inputs.yillik_brut_kar > 0 else 0
        
        st.header(tr("ai_analysis_header"))
        with st.spinner("AI Uzman Analisti, raporu hazırlıyor..."):
            report = generate_report(s_inputs, pd_ratio, gross_bi_days)
            st.markdown(report, unsafe_allow_html=True)
            
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
                prim_pd = calculate_premium(s_inputs.si_pd, s_inputs.yapi_turu, s_inputs.rg, koas, muaf)
                prim_bi = calculate_premium(s_inputs.yillik_brut_kar, s_inputs.yapi_turu, s_inputs.rg, koas, muaf, is_bi=True)
                toplam_prim = prim_pd + prim_bi
                pd_claim = calculate_net_claim(s_inputs.si_pd, pd_damage_amount, koas, muaf)
                total_payout = pd_claim["net_tazminat"] + bi_damage_amount
                retained_risk = (pd_damage_amount + bi_damage_amount) - total_payout
                verimlilik_skoru = (total_payout / toplam_prim if toplam_prim > 0 else 0) - (retained_risk / s_inputs.si_pd if s_inputs.si_pd > 0 else 0)
                results.append({"Poliçe Yapısı": f"{koas} / {muaf}%", "Yıllık Toplam Prim": toplam_prim, "Toplam Net Tazminat": total_payout, "Sigortalıda Kalan Risk": retained_risk, "Verimlilik Skoru": verimlilik_skoru})
        df = pd.DataFrame(results).sort_values("Verimlilik Skoru", ascending=False).reset_index(drop=True)
        
        tab1, tab2 = st.tabs([tr("table_analysis"), tr("visual_analysis")])
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
