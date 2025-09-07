# -*- coding: utf-8 -*-
#
# TariffEQ – Hibrit Zekâ Destekli PD & BI Hasar Analiz Aracı (v6.5)
# =======================================================================
# Bu Streamlit uygulaması, reasürans ve katastrofik modelleme metodolojilerinden
# esinlenerek geliştirilmiş parametreler ve tarifeye tam uyumlu hesaplama
# mantığı ile ticari/sınai rizikolar için profesyonel seviyede bir deprem
# hasar analizi sunar.
#
# GÜNCEL REVİZYON NOTLARI (Eylül 2025 - v6.5 - Denetlenebilir Araştırma Protokolü):
# 1. Odaklı AI Mimarisi: AI'ın çalışmadığı durumlar için geliştirilen tüm
#    heuristik/yedek fonksiyonlar kaldırıldı. Uygulama artık %100 AI gücüne
#    odaklanmıştır. Gemini çalışmazsa, analiz gerçekleşmez.
# 2. Gelişmiş AI Araştırma Protokolü: AI_ANALYST_SYSTEM_PROMPT, AI'ı adım adım
#    bir araştırma metodolojisi izlemeye zorlayan bir protokole dönüştürüldü.
#    AI artık kanıt sunmak, kaynak belirtmek ve varsayımlarını detaylıca
#    açıklamak zorundadır.
# 3. Akıllı YOKE Analizi ve Temiz Arayüz: Kullanıcıdan YOKE girdisi isteme kaldırıldı.
#    AI, bu riski faaliyet tanımından kendisi çıkarır. Arayüz sadeleştirildi ve
#    sonuçların şeffaflığı artırıldı.

import streamlit as st
import pandas as pd
import plotly.express as px
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import json
import traceback
import os

# --- AI İÇİN KORUMALI IMPORT VE GÜVENLİ KONFİGÜRASYON ---
_GEMINI_AVAILABLE = False
try:
    import google.generativeai as genai
    if st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        genai.configure(api_key=(st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")))
        _GEMINI_AVAILABLE = True
    else:
        st.sidebar.warning("Gemini API anahtarı bulunamadı. AI özellikleri devre dışı.", icon="🔑")
        _GEMINI_AVAILABLE = False
except (ImportError, Exception):
    st.sidebar.error("Google AI kütüphanesi yüklenemedi. AI özellikleri devre dışı.", icon="🤖")
    _GEMINI_AVAILABLE = False


# --- AI PROMPTLARI ---

def get_qualitative_assessment_prompt(s: 'ScenarioInputs', triggered_rules: List[str]) -> str:
    # Bu fonksiyon nitel rapor üretir ve değişmemiştir.
    if s.tesis_tipi == tr("endustriyel_tesis"):
        p = s.industrial_params
        return f"""
        Rolün: TariffEQ için çalışan uzman bir AI teknik underwriter'ı (Endüstriyel Tesisler)...
        ---
        YAPILANDIRILMIŞ GİRDİLER: Yapı Türü: {p.yapi_turu}, Yönetmelik: {p.yonetmelik_donemi}, Zemin: {p.zemin_sinifi}...
        SERBEST METİN (Ek Detaylar): "{p.faaliyet_tanimi}"
        ---
        Lütfen bu bilgilerle Teknik Risk Değerlendirmesini oluştur.
        """
    # Diğer tesis tipleri için prompt'lar burada devam eder...
    return "Seçilen tesis tipi için AI değerlendirmesi henüz aktif değil."


AI_ANALYST_SYSTEM_PROMPT = r"""
SİSTEM MESAJI — TariffEQ v6.5 • AI Araştırma Analisti (Denetlenebilir Araştırma Protokolü)

ROL VE AMAÇ
Sen, TariffEQ uygulaması için çalışan uzman bir 'AI Araştırma Analisti'sin. Birincil görevin, sana sunulan bir endüstriyel tesis senaryosunu analiz etmek ve bu analizi, en yüksek standartlardaki (TBDY-2018, AFAD, HAZUS, FEMA P-58, akademik yayınlar, güvenilir endüstri raporları) kaynaklardan elde edilen bilgilerle destekleyerek denetlenebilir, savunulabilir ve şeffaf sayısal kalibrasyon parametreleri üretmektir. Senin çıktın bir "kara kutu" olamaz; her sayısal değerin bir gerekçesi ve kaynağı olmalıdır.

ZORUNLU ARAŞTIRMA PROTOKOLÜ (Her analizde bu adımları izle)

Adım 1: Girdileri Ayrıştırma ve Araştırma Soruları Oluşturma
- Kullanıcının girdiği tüm verileri (risk bölgesi, zemin sınıfı, faaliyet tanımı vb.) dikkatle incele.
- Bu girdilerden yola çıkarak cevaplaman gereken spesifik teknik sorular oluştur. Örnekler:
    - "1. Derece deprem bölgesinde, ZD zemin sınıfı üzerindeki çelik bir yapı için TBDY-2018'e göre beklenen zemin büyütme etkisi nedir?"
    - "Faaliyet tanımında belirtilen 'yüksek raflarda rulo sac stoklama', yapısal olmayan eleman (YOKE) hasar potansiyelini (HAZUS metodolojisine göre) ne ölçüde artırır?"
    - "Otomotiv ana sanayi için kritik bir hidrolik presin global tedarik zinciri kesintisi durumunda ortalama bekleme süresi nedir?"

Adım 2: Bilgiyi Sentezleme (Simüle Edilmiş Araştırma)
- Oluşturduğun soruları cevaplamak için geniş bilgi havuzunu kullan. Türkiye ile ilgili konularda TBDY-2018 ve AFAD verilerini mutlak öncelik olarak al.
- Uluslararası standartlar ve sektörel veriler için HAZUS, FEMA ve güvenilir endüstri raporlarını referans al.
- Çelişkili bilgi bulursan, en güncel ve en resmi kaynağı (örneğin, bir blog yazısı yerine resmi yönetmelik) esas al ve bu durumu `meta.notes` içinde belirt.

Adım 3: Sayısallaştırma ve Kalibrasyon
- Araştırma bulgularını, istenen JSON şemasındaki sayısal parametrelere dönüştür.
- Her parametre atamasını, Adım 2'de elde ettiğin kanıtlara dayandır. Örneğin, TBDY-2018'de ZD sınıfı için belirtilen bir katsayıyı doğrudan `zemin_carpani` olarak ata.

Adım 4: Gerekçelendirme ve Dokümantasyon (EN KRİTİK ADIM)
- JSON çıktısındaki `meta.assumptions` ve `meta.notes` alanlarını eksiksiz ve detaylı doldurmak zorundasın. Bu, senin temel performans göstergendir.
- `meta.assumptions`: Özellikle `faaliyet_tanimi`ndan yaptığın çıkarımları (örn. YOKE riski) buraya yaz. Bu, kullanıcının doğrudan vermediği ama senin analizle ürettiğin bilgilerdir.
- `meta.notes`: Sayısal atamalarının arkasındaki "Neden?" sorusunu cevaplayan kanıtları buraya ekle. Her kanıt için şu formatı kullan: "Kanıt: [Bulgu Özeti] - Kaynak: [Yayıncı/Kurum Adı] - Tarih: [Yayın Tarihi]".

ÖRNEK BİR GEREKÇELENDİRME:
"meta": {
  "confidence_0to1": 0.90,
  "assumptions": [
    "Faaliyet tanımındaki 'yüksek raflarda rulo sac' ve 'robotik kaynak hatları' ifadeleri, sismik koruması olmayan, devrilmeye ve kaymaya müsait ciddi yapısal olmayan eleman (YOKE) riski olarak yorumlanmış ve 'yoke_carpani' buna göre artırılmıştır."
  ],
  "notes": "Kanıt: ZD zemin sınıfı için kısa periyot zemin büyütme katsayısı (F_s) 1.2-1.5 aralığındadır; senaryo için ortalama 1.3 değeri 'zemin_carpani' olarak atanmıştır. - Kaynak: TBDY-2018, Tablo 2.1 - Tarih: 2018. Kanıt: Ağır sanayide kullanılan büyük ölçekli CNC ve pres makinelerinin özel sipariş ve kurulum süreleri, tedarik zinciri krizlerinde ortalama 9 ayı bulabilmektedir. 'tedarik_zinciri_gecikme_ay' buna göre kalibre edilmiştir. - Kaynak: Global Industrial Machinery Report - Tarih: 2024."
}

ÇIKTI — ZORUNLU JSON ŞEMASI
{
  "icerik_hassasiyeti": "Düşük|Orta|Yüksek",
  "kritik_makine_bagimliligi": "Düşük|Orta|Yüksek",
  "ffe_riski": "Düşük|Orta|Yüksek",
  "pd_base_loss_ratio_suggestion": {"bina": 0.00, "makine": 0.00, "elektronik": 0.00, "stok": 0.00},
  "pd_factor_suggestion": {"zemin_carpani": 1.00, "yoke_carpani": 1.00, "ffeq_potansiyel_carpani": 1.00, "stok_devrilme_carpani": 1.00},
  "bi_calibration": {"kritik_ekipman_durus_carpani": 1.00, "altyapi_gecikme_ay": 0, "tedarik_zinciri_gecikme_ay": 0, "buffer_bitmis_urun_stogu_gun": 0},
  "risk_flags": ["YUMUSAK_KAT_RISKI","SIVILASMA_RISKI","ESKI_TASARIM_KODU"],
  "meta": {
      "confidence_0to1": 0.00,
      "assumptions": ["List of assumptions made, especially regarding YOKE risk inferred from the activity description."],
      "notes": "List of evidence supporting numerical parameters. Use format: 'Evidence: [Summary] - Source: [Publisher] - Date: [Year]'."
  }
}
"""

# --- Sabitler, Çeviriler ve Veri Modelleri ---
# (Bu bölümler önceki versiyon ile aynıdır, YOKE girdisi dataclass'tan kaldırılmıştır)
TARIFE_RATES = {"Betonarme": [3.13, 2.63, 2.38, 1.94, 1.38, 1.06, 0.75], "Çelik": [3.13, 2.63, 2.38, 1.94, 1.38, 1.06, 0.75], "Yığma": [6.13, 5.56, 3.75, 2.00, 1.56, 1.24, 1.06], "Diğer": [6.13, 5.56, 3.75, 2.00, 1.56, 1.24, 1.06]}
KOAS_FACTORS = {"80/20": 1.0, "75/25": 0.9375, "70/30": 0.875, "65/35": 0.8125, "60/40": 0.75, "55/45": 0.6875, "50/50": 0.625, "45/55": 0.5625, "40/60": 0.5, "90/10": 1.125, "100/0": 1.25}
MUAFIYET_FACTORS = {2.0: 1.0, 3.0: 0.94, 4.0: 0.87, 5.0: 0.81, 10.0: 0.65, 1.5: 1.03, 1.0: 1.06, 0.5: 1.09, 0.1: 1.12}
_DEF_SPLIT_INDUSTRIAL = {"bina": 0.40, "makine": 0.40, "elektronik": 0.06, "stok": 0.14}
def tr(key: str) -> str: return T.get(key, {}).get(st.session_state.get("lang", "TR"), key)
def money(x: float) -> str: return f"{x:,.0f} ₺".replace(",", ".")
def _clamp(x: float, lo: float, hi: float) -> float: return max(lo, min(hi, float(x)))
T = { "title": {"TR": "TariffEQ – Hibrit Zekâ Destekli Risk Analizi", "EN": "TariffEQ – Hybrid AI-Powered Risk Analysis"}, "tesis_tipi_secimi": {"TR": "1. Lütfen Analiz Etmek İstediğiniz Tesis Tipini Seçiniz", "EN": "1. Please Select the Facility Type to Analyze"}, "endustriyel_tesis": {"TR": "Endüstriyel Tesis (Fabrika, Depo vb.)", "EN": "Industrial Facility (Factory, Warehouse etc.)"}, "res": {"TR": "Enerji Santrali - Rüzgar (RES)", "EN": "Power Plant - Wind (WPP)"}, "ges": {"TR": "Enerji Santrali - Güneş (GES)", "EN": "Power Plant - Solar (SPP)"}, "hes": {"TR": "Enerji Santrali - Hidroelektrik (HES)", "EN": "Power Plant - Hydroelectric (HPP)"}, "inputs_header": {"TR": "📊 2. Senaryo Girdileri", "EN": "📊 2. Scenario Inputs"}, "base_header": {"TR": "🏭 Temel Bilgiler", "EN": "🏭 Basic Information"}, "pd_header": {"TR": "🧱 Yapısal & Çevresel Riskler", "EN": "🧱 Structural & Environmental Risks"}, "bi_header": {"TR": "📈 Operasyonel & BI Riskleri", "EN": "📈 Operational & BI Risks"}, "activity_desc_industrial": {"TR": "Süreç, Ekipman ve Stoklara Dair Ek Detaylar", "EN": "Additional Details on Processes, Equipment, and Stock"}, "si_pd": {"TR": "Toplam Sigorta Bedeli (PD)", "EN": "Total Sum Insured (PD)"}, "risk_zone": {"TR": "Deprem Risk Bölgesi", "EN": "Earthquake Risk Zone"}, "gross_profit": {"TR": "Yıllık Brüt Kâr (GP)", "EN": "Annual Gross Profit (GP)"}, "azami_tazminat": {"TR": "Azami Tazminat Süresi", "EN": "Max. Indemnity Period"}, "bi_wait": {"TR": "BI Bekleme Süresi (Muafiyet)", "EN": "BI Waiting Period (Deductible)"}, "yumusak_kat": {"TR": "Zemin Katta Geniş Vitrin/Cephe (Yumuşak Kat Riski)", "EN": "Large Ground Floor Facade/Windows (Soft Story Risk)"}, "yumusak_kat_help": {"TR": "Binanızın zemin katı..."}, "ai_pre_analysis_header": {"TR": "🧠 AI Teknik Risk Değerlendirmesi", "EN": "🧠 AI Technical Risk Assessment"}, "results_header": {"TR": "📝 Sayısal Hasar Analizi", "EN": "📝 Numerical Damage Analysis"}, "analysis_header": {"TR": "🔍 Poliçe Alternatifleri Analizi", "EN": "🔍 Policy Alternatives Analysis"}, "btn_run": {"TR": "Analizi Çalıştır", "EN": "Run Analysis"},}

@dataclass
class IndustrialInputs:
    faaliyet_tanimi: str = "Otomotiv ana sanayiye metal şasi parçaları üreten bir tesis. Tesiste 5 adet 1000 tonluk hidrolik pres, CNC makineleri ve robotik kaynak hatları bulunmaktadır. Yüksek raflarda rulo sac malzeme stoklanmaktadır."
    yapi_turu: str = "Çelik"; yonetmelik_donemi: str = "2018 sonrası (Yeni Yönetmelik)"; kat_sayisi: str = "1-3 kat"
    yumusak_kat_riski: str = "Hayır"; yakin_cevre: str = "Ana Karada / Düz Ova"; zemin_sinifi: str = "ZC (Varsayılan)"
    isp_varligi: str = "Var (Test Edilmiş)"; alternatif_tesis: str = "Var (kısmi kapasite)"; bitmis_urun_stogu: int = 15; bi_gun_muafiyeti: int = 21
    pd_bina_sum: int = 0; pd_makine_sum: int = 0; pd_elektronik_sum: int = 0; pd_stok_sum: int = 0

@dataclass
class ScenarioInputs:
    tesis_tipi: str = tr("endustriyel_tesis"); si_pd: int = 500_000_000; yillik_brut_kar: int = 200_000_000; rg: int = 1; azami_tazminat_suresi: int = 365
    industrial_params: IndustrialInputs = field(default_factory=IndustrialInputs)


# --- Hesaplama Fonksiyonları ---
def calculate_pd_damage_industrial(s: ScenarioInputs) -> Dict:
    calib = st.session_state.get("ai_calibration_results")
    if not calib: raise ValueError("AI Kalibrasyon verisi bulunamadı. Lütfen analizi tekrar çalıştırın.")
    r = calib["pd_base_loss_ratio_suggestion"]; f = calib["pd_factor_suggestion"]; si_total = int(s.si_pd or 0)
    if si_total <= 0: return {"damage_amount": 0, "pml_ratio": 0.0, "_details": {"ratios": {}, "pd_breakdown": {}}}
    p = s.industrial_params
    si_bina = int(p.pd_bina_sum or 0); si_makine = int(p.pd_makine_sum or 0); si_elektronik = int(p.pd_elektronik_sum or 0); si_stok = int(p.pd_stok_sum or 0)
    if (si_bina + si_makine + si_elektronik + si_stok) == 0: si = {k: int(si_total * v) for k, v in _DEF_SPLIT_INDUSTRIAL.items()}
    else: si = {"bina": si_bina, "makine": si_makine, "elektronik": si_elektronik, "stok": si_stok}
    bina_ratio = _clamp(r["bina"] * f["zemin_carpani"] * f["yoke_carpani"], 0.01, 0.60); makine_ratio = _clamp(r["makine"] * f["zemin_carpani"] * f["yoke_carpani"] * f["ffeq_potansiyel_carpani"], 0.01, 0.60); elektronik_ratio = _clamp(r["elektronik"] * f["zemin_carpani"] * f["yoke_carpani"] * f["ffeq_potansiyel_carpani"], 0.01, 0.60); stok_ratio = _clamp(r["stok"] * f["zemin_carpani"] * f["yoke_carpani"] * f["stok_devrilme_carpani"], 0.01, 0.60)
    pd_bina = si["bina"] * bina_ratio; pd_makine = si["makine"] * makine_ratio; pd_elektronik = si["elektronik"] * elektronik_ratio; pd_stok = si["stok"] * stok_ratio
    total = pd_bina + pd_makine + pd_elektronik + pd_stok; pml_ratio = _clamp(total / max(1, sum(si.values())), 0.00, 0.80)
    return {"damage_amount": int(total), "pml_ratio": float(round(pml_ratio, 3)), "_details": {"ratios": {"Bina": round(bina_ratio, 2), "Makine": round(makine_ratio, 2), "Elektronik": round(elektronik_ratio, 2), "Stok": round(stok_ratio, 2)}, "pd_breakdown": {"Bina": int(pd_bina), "Makine": int(pd_makine), "Elektronik": int(pd_elektronik), "Stok": int(pd_stok)}}}

def calculate_bi_downtime_industrial(pd_ratio: float, s: ScenarioInputs) -> Tuple[int, int]:
    calib = st.session_state.get("ai_calibration_results")
    if not calib: raise ValueError("AI Kalibrasyon verisi bulunamadı.")
    b = calib["bi_calibration"]; p = s.industrial_params; base_repair = 30 + (float(pd_ratio) * 300.0); internal_downtime = int(base_repair * float(b["kritik_ekipman_durus_carpani"])); external_downtime = int((int(b["altyapi_gecikme_ay"]) + int(b["tedarik_zinciri_gecikme_ay"])) * 30); gross_downtime = max(internal_downtime, external_downtime); net_downtime_after_stock = max(0, gross_downtime - int(b.get("buffer_bitmis_urun_stogu_gun", p.bitmis_urun_stogu))); net_downtime_after_wait = max(0, net_downtime_after_stock - p.bi_gun_muafiyeti); final_downtime = min(s.azami_tazminat_suresi, net_downtime_after_wait); return max(0, gross_downtime), max(0, int(final_downtime))

# --- AI Fonksiyonları ---
@st.cache_data(show_spinner="AI Araştırma Analisti çalışıyor...")
def get_ai_calibration_industrial(s: ScenarioInputs) -> Dict:
    if not _GEMINI_AVAILABLE: raise ConnectionError("Gemini API anahtarı bulunamadı veya geçersiz. Lütfen ayarları kontrol edin.")
    p = s.industrial_params
    payload = {
        "facility_type": "Endüstriyel", "rg": int(s.rg), "si_pd_total_TL": int(s.si_pd),
        "annual_gross_profit_TL": int(s.yillik_brut_kar), "max_indemnity_days": int(s.azami_tazminat_suresi),
        "bi_wait_days": int(p.bi_gun_muafiyeti), "yapi_turu": p.yapi_turu, "yonetmelik_donemi": p.yonetmelik_donemi,
        "kat_sayisi": p.kat_sayisi, "zemin_sinifi": p.zemin_sinifi, "yakin_cevre": p.yakin_cevre,
        "yumusak_kat_riski": p.yumusak_kat_riski, "ISP": p.isp_varligi, "alternatif_tesis": p.alternatif_tesis,
        "bitmis_urun_stogu_gun": int(p.bitmis_urun_stogu or 0), "faaliyet_tanimi": p.faaliyet_tanimi or "",
    }
    try:
        model = genai.GenerativeModel(model_name="gemini-1.5-flash-latest", system_instruction=AI_ANALYST_SYSTEM_PROMPT)
        generation_config = {"temperature": 0.1, "top_p": 0.8, "response_mime_type": "application/json"}
        prompt_user = "KULLANICI GİRDİLERİ (JSON):\n" + json.dumps(payload, ensure_ascii=False)
        response = model.generate_content(prompt_user, generation_config=generation_config)
        return json.loads(response.text)
    except Exception as e:
        st.session_state.errors.append(f"AI Parametre Hatası: {str(e)}\n{traceback.format_exc()}")
        raise RuntimeError(f"AI Analisti'nden geçerli bir yanıt alınamadı: {e}")

# --- STREAMLIT UYGULAMASI ---
def main():
    st.set_page_config(page_title="TariffEQ v6.5", layout="wide", page_icon="🏗️")
    if 'run_clicked' not in st.session_state: st.session_state.run_clicked = False
    if 'errors' not in st.session_state: st.session_state.errors = []
    if 's_inputs' not in st.session_state: st.session_state.s_inputs = ScenarioInputs()

    st.title(tr('title'))
    
    # Tesis Tipi Seçimi (Sadece Endüstriyel aktif)
    selected_tesis_tipi = st.selectbox(
        tr("tesis_tipi_secimi"),
        [tr("endustriyel_tesis")], # Şimdilik sadece endüstriyel
        index=0
    )
    s_inputs = st.session_state.s_inputs
    s_inputs.tesis_tipi = selected_tesis_tipi
    
    st.header(tr("inputs_header"))
    
    p_ind = s_inputs.industrial_params
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader(tr("base_header"))
        s_inputs.si_pd = st.number_input(tr("si_pd"), min_value=1_000_000, value=s_inputs.si_pd, step=10_000_000)
        p_ind.faaliyet_tanimi = st.text_area(tr("activity_desc_industrial"), p_ind.faaliyet_tanimi, height=200, placeholder="Örn: ...hidrolik presler, CNC makineleri...")
        with st.expander("Opsiyonel: Varlık Bazında Sigorta Bedeli"):
             p_ind.pd_bina_sum = st.number_input("Bina SI (TL)", min_value=0, step=100_000, value=p_ind.pd_bina_sum)
             p_ind.pd_makine_sum = st.number_input("Makine SI (TL)", min_value=0, step=100_000, value=p_ind.pd_makine_sum)
             p_ind.pd_elektronik_sum = st.number_input("Elektronik SI (TL)", min_value=0, step=50_000, value=p_ind.pd_elektronik_sum)
             p_ind.pd_stok_sum = st.number_input("Stok SI (TL)", min_value=0, step=50_000, value=p_ind.pd_stok_sum)
    with col2:
        st.subheader(tr("pd_header"))
        s_inputs.rg = st.select_slider(tr("risk_zone"), options=list(range(1, 8)), value=s_inputs.rg)
        p_ind.yapi_turu = st.selectbox("Yapı Türü", ["Betonarme", "Çelik", "Yığma", "Diğer"])
        p_ind.yonetmelik_donemi = st.selectbox("Yönetmelik Dönemi", ["1998 öncesi (Eski Yönetmelik)", "1998-2018 arası (Varsayılan)", "2018 sonrası (Yeni Yönetmelik)"])
        p_ind.kat_sayisi = st.selectbox("Kat Sayısı", ["1-3 kat", "4-7 kat", "8+ kat"])
        p_ind.zemin_sinifi = st.selectbox("Zemin Sınıfı", ["ZE", "ZD", "ZC (Varsayılan)", "ZA/ZB (Kaya/Sıkı Zemin)"])
        p_ind.yakin_cevre = st.selectbox("Tesisin Yakın Çevresi", ["Nehir Yatağı / Göl Kenarı / Kıyı Şeridi", "Ana Karada / Düz Ova", "Dolgu Zemin Üzerinde"])
        p_ind.yumusak_kat_riski = st.selectbox(tr("yumusak_kat"), ["Hayır", "Evet"], help=tr("yumusak_kat_help"))
    with col3:
        st.subheader(tr("bi_header"))
        s_inputs.yillik_brut_kar = st.number_input(tr("gross_profit"), min_value=0, value=s_inputs.yillik_brut_kar, step=10_000_000)
        p_ind.bi_gun_muafiyeti = st.selectbox(tr("bi_wait"), [14, 21, 30, 45, 60])
        s_inputs.azami_tazminat_suresi = st.selectbox(tr("azami_tazminat"), [365, 540, 730], format_func=lambda x: f"{int(x/30)} Ay")
        p_ind.isp_varligi = st.selectbox("İş Sürekliliği Planı", ["Yok (Varsayılan)", "Var (Test Edilmemiş)", "Var (Test Edilmiş)"])
        p_ind.alternatif_tesis = st.selectbox("Alternatif Tesis", ["Yok", "Var (kısmi kapasite)", "Var (tam kapasite)"])
        p_ind.bitmis_urun_stogu = st.number_input("Bitmiş Ürün Stoğu (gün)", value=p_ind.bitmis_urun_stogu, min_value=0, max_value=120)

    st.markdown("---")
    if st.button(f"🚀 {tr('btn_run')}", use_container_width=True, type="primary"):
        st.session_state.run_clicked = True
        st.session_state.s_inputs = s_inputs
        st.session_state.errors = []
        st.session_state.ai_calibration_results = {}
    
    if st.session_state.run_clicked:
        s_inputs = st.session_state.s_inputs
        try:
            # 1. AI'dan kalibrasyon al
            ai_calib = get_ai_calibration_industrial(s_inputs)
            st.session_state.ai_calibration_results = ai_calib
            
            # 2. Nitel raporu oluştur
            triggered_rules = ai_calib.get("risk_flags", [])
            assessment_report = get_qualitative_assessment_prompt(s_inputs, triggered_rules) # Basit metin olarak al
            
            # 3. Sayısal hesaplamaları yap
            pd_results = calculate_pd_damage_industrial(s_inputs)
            gross_bi_days, net_bi_days_final = calculate_bi_downtime_industrial(pd_results["pml_ratio"], s_inputs)

            # --- SONUÇLARI GÖSTERME ---
            st.header(tr("ai_pre_analysis_header"))
            # st.markdown(assessment_report, unsafe_allow_html=True) # Nitel rapor şimdilik gösterilmiyor.
            
            pd_damage_amount = pd_results["damage_amount"]; pd_ratio = pd_results["pml_ratio"]
            bi_damage_amount = (s_inputs.yillik_brut_kar / 365.0) * net_bi_days_final if s_inputs.yillik_brut_kar > 0 else 0
            
            st.header(tr("results_header"))
            m1, m2, m3 = st.columns(3)
            m1.metric("Beklenen PD Hasar Tutarı", money(pd_damage_amount), f"PML: {pd_ratio:.2%}")
            m2.metric("Brüt / Net İş Kesintisi", f"{gross_bi_days} / {net_bi_days_final} gün", "Onarım / Tazmin edilebilir")
            m3.metric("Beklenen BI Hasar Tutarı", money(bi_damage_amount))

            if "_details" in pd_results:
                st.subheader("Varlık Bazlı PD Hasar Kırılımı")
                details = pd_results["_details"]
                df_det = pd.DataFrame(list(details["pd_breakdown"].items()), columns=["Varlık Grubu", "PD Hasarı (₺)"])
                df_det["Hasar Oranı"] = [f"{v:.2%}" for v in details["ratios"].values()]
                st.dataframe(df_det.style.format({"PD Hasarı (₺)": money}), use_container_width=True)

            st.markdown("---")
            st.subheader("🧠 AI Kalibrasyon Gerekçeleri ve Parametreler")
            meta = ai_calib.get("meta", {})
            st.markdown("##### AI Tarafından Yapılan Ana Varsayımlar"); assumptions = meta.get("assumptions", ["Varsayım bulunamadı."])
            for assumption in assumptions: st.info(f"ℹ️ {assumption}")
            st.markdown("##### Analizde Kullanılan Dayanak ve Referanslar"); notes = meta.get("notes", "Referans bulunamadı."); st.caption(f"📜 {notes}")
            st.markdown("##### Atanan Sayısal Kalibrasyon Parametreleri"); params_data = []
            for group_key, group_dict in ai_calib.items():
                if isinstance(group_dict, dict):
                    group_name = {"pd_factor_suggestion": "PD Çarpanları", "bi_calibration": "BI Kalibrasyonu"}.get(group_key, "Diğer")
                    for key, value in group_dict.items():
                        params_data.append({"Grup": group_name, "Parametre": key, "Değer": value})
            if params_data: df_params = pd.DataFrame(params_data); st.table(df_params.style.format({"Değer": "{:.2f}"}))
            else: st.warning("Sayısal parametreler AI tarafından üretilemedi.")
            
        except (RuntimeError, ConnectionError, Exception) as e:
            st.error(f"❌ Analiz Başarısız Oldu: {e}")
            st.session_state.errors.append(f"Analiz Hatası: {str(e)}\n{traceback.format_exc()}")

    if st.session_state.errors:
        with st.sidebar.expander("⚠️ Geliştirici Hata Logları", expanded=False):
            for error in st.session_state.errors:
                st.code(error)

if __name__ == "__main__":
    main()
