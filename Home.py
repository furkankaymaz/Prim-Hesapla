# home.py  —  TariffEQ Scenario + AI (single-file Streamlit app)
# Çalışma mantığı:
# - Google Gemini varsa (GEMINI_API_KEY) AI rapor üretir
# - Yoksa güvenli statik senaryo metnine otomatik düşer
# - Tek dosya: çeviri, hesap, UI hepsi burada

import os
import math
import streamlit as st
from dataclasses import dataclass
from typing import Dict

# --- AI İÇİN KORUMALI IMPORT (yoksa statik moda düşer) ---
_GEMINI_AVAILABLE = False
try:
    # Yeni SDK
    from google import genai as _genai_new  # type: ignore
    from google.genai import types as _genai_types  # type: ignore
    _GEMINI_AVAILABLE = True
except Exception:
    try:
        # Eski SDK (bazı ortamlarda bu kurulu)
        import google.generativeai as _genai_old  # type: ignore
        _GEMINI_AVAILABLE = True
    except Exception:
        _GEMINI_AVAILABLE = False

GEMINI_API_KEY = os.environ.get("AIzaSyAjbjgJDHqXpJK9euPWLkfgiMOSyOTOx1M")

# --- BASİT ÇEVİRİ SÖZLÜĞÜ (kullandığımız anahtarlarla sınırlı) ---
T = {
    "title": {"TR": "TariffEQ – Senaryo Analizi", "EN": "TariffEQ – Scenario Analysis"},
    "sidebar_language": {"TR": "Language / Dil", "EN": "Language / Dil"},
    "inputs_header": {"TR": "Girdiler", "EN": "Inputs"},
    "pd_ins": {"TR": "PD Sigorta Bedeli (₺)", "EN": "PD Sum Insured (TRY)"},
    "bi_ins": {"TR": "BI Sigorta Bedeli (₺)", "EN": "BI Sum Insured (TRY)"},
    "risk_zone": {"TR": "Deprem Risk Bölgesi (1=En Riskli)", "EN": "Earthquake Risk Zone (1=Highest)"},
    "btype": {"TR": "Yapı Türü", "EN": "Building Type"},
    "bage": {"TR": "Bina Yaşı", "EN": "Building Age"},
    "floors": {"TR": "Kat Sayısı", "EN": "Floors"},
    "activity": {"TR": "Faaliyet", "EN": "Activity"},
    "retrofit": {"TR": "Güçlendirme", "EN": "Retrofit"},
    "bi_wait": {"TR": "BI Bekleme Süresi (gün)", "EN": "BI Waiting Days"},
    "calc_header": {"TR": "Sonuçlar", "EN": "Results"},
    "pd_damage_amount": {"TR": "PD Hasar Tutarı", "EN": "PD Damage Amount"},
    "bi_damage_amount": {"TR": "BI Hasar Tutarı", "EN": "BI Damage Amount"},
    "ai_header": {"TR": "AI Senaryo Raporu", "EN": "AI Scenario Report"},
    "disclaimer": {
        "TR": "Bu çıktı demonstrasyon amaçlıdır; resmi sigorta teklifinin yerini almaz.",
        "EN": "This output is for demo purposes and does not replace a formal insurance quotation."
    },
    "btn_run": {"TR": "Senaryoyu Oluştur", "EN": "Generate Scenario"},
    "lang_TR": {"TR": "TR", "EN": "TR"},
    "lang_EN": {"TR": "EN", "EN": "EN"},
}

# --- YARDIMCI ---
def tr(key: str) -> str:
    lang = st.session_state.get("lang", "TR")
    return T.get(key, {}).get(lang, key)

def money(x: int) -> str:
    return f"₺{x:,}".replace(",", ".")

# --- GİRDİ MODELİ ---
@dataclass
class ScenarioInputs:
    si_pd: int = 250_000_000
    si_bi: int = 100_000_000
    rg: int = 3  # 1..5
    yapi_turu: str = "Betonarme"  # "Betonarme","Çelik","Yığma","Prefabrik"
    bina_yasi: str = "10-30 yıl"  # "0-5 yıl","5-10 yıl","10-30 yıl","30+ yıl"
    kat_sayisi: str = "4-7 kat"
    faaliyet: str = "İplik Fabrikası"
    guclendirme: str = "Yok"  # "Yok","Kısmi","Tam"
    bi_gun_muafiyeti: int = 14

# --- HASAR ORAN HESABI (basit, açıklanabilir heuristik) ---
_DEPREM_ORAN = {
    1: {"hafif": 0.07, "beklenen": 0.20, "agir": 0.45},
    2: {"hafif": 0.06, "beklenen": 0.17, "agir": 0.40},
    3: {"hafif": 0.05, "beklenen": 0.13, "agir": 0.32},
    4: {"hafif": 0.04, "beklenen": 0.09, "agir": 0.24},
    5: {"hafif": 0.03, "beklenen": 0.06, "agir": 0.15},
}

def calculate_damage_ratios(s: ScenarioInputs) -> Dict[str, float]:
    base = _DEPREM_ORAN.get(int(s.rg), _DEPREM_ORAN[3])["beklenen"]
    factor = 1.0

    # Yapı türü
    factor *= {"Betonarme": 1.0, "Çelik": 0.9, "Prefabrik": 1.05, "Yığma": 1.25}.get(s.yapi_turu, 1.0)
    # Bina yaşı
    factor *= {"0-5 yıl": 0.85, "5-10 yıl": 0.95, "10-30 yıl": 1.0, "30+ yıl": 1.2}.get(s.bina_yasi, 1.0)
    # Kat sayısı
    factor *= {"1-3 kat": 0.9, "4-7 kat": 1.0, "8+ kat": 1.1}.get(s.kat_sayisi, 1.0)
    # Güçlendirme
    factor *= {"Yok": 1.0, "Kısmi": 0.95, "Tam": 0.9}.get(s.guclendirme, 1.0)

    pd_ratio = min(0.95, max(0.01, base * factor))  # 1%–95% güvenli sınır
    # BI gün kestirimi (çok kaba): PD oranı ve yapısal/operasyonel faktörlere bağlı
    bi_days = int(round( (60 * pd_ratio) * {"Betonarme":1.0,"Çelik":0.9,"Prefabrik":1.1,"Yığma":1.2}[s.yapi_turu] ))
    bi_days = max(0, min(365, bi_days))
    return {"pd_ratio": pd_ratio, "bi_days": bi_days}

# --- AI RAPOR (Gemini varsa), STATİK RAPOR (fallback) ---
def _static_report(s: ScenarioInputs, pd_ratio: float, bi_days: int, lang: str) -> str:
    pd_pct = round(pd_ratio * 100, 1)
    if lang.lower().startswith("tr"):
        return f"""**Deprem Hasar Değerlendirmesi (Beklenen Senaryo)**

**Tesis:** {s.faaliyet} ({s.yapi_turu}, {s.bina_yasi}, {s.kat_sayisi})
**Bölge:** {s.rg}. Bölge | **Güçlendirme:** {s.guclendirme}

**PD (Mal) Hasar:** Yaklaşık **%{pd_pct}** seviyesinde hasar beklenmektedir. Kritik ekipmanlar ve raf sistemlerinde devrilme/çarpma kaynaklı ikincil zararlar öngörülür. İnce kaplama ve hat sonu üniteleri daha yüksek hasar potansiyeline sahiptir.

**BI (Kar Kaybı):** Ortalama **{bi_days} gün** üretim/operasyon kesintisi riski mevcuttur. Tedarik gecikmeleri, yedek parça temini ve artçı sarsıntılar yeniden devreye alma süresini uzatabilir.

> Bu metin, AI anahtarı olmadığında üretilen statik rapordur."""
    else:
        return f"""**Earthquake Damage Assessment (Expected Scenario)**

**Facility:** {s.faaliyet} ({s.yapi_turu}, {s.bina_yasi}, {s.kat_sayisi})
**Zone:** {s.rg} | **Retrofit:** {s.guclendirme}

**PD (Property) Damage:** Expected around **{pd_pct}%**. Secondary damages from tipping/impact on racks and sensitive machinery are likely. End-of-line units have higher susceptibility.

**BI (Business Interruption):** Approximately **{bi_days} days** of downtime risk. Spare-part delivery, suppliers’ delays and aftershocks may extend restart times.

> This text is a static report used when no AI key is provided."""

def _ai_report(s: ScenarioInputs, pd_ratio: float, bi_days: int, lang: str) -> str:
    if not (_GEMINI_AVAILABLE and GEMINI_API_KEY):
        return _static_report(s, pd_ratio, bi_days, lang)

    prompt_tr = f"""
Aşağıdaki girdilerle bir deprem hasar senaryosu hazırla. Sonuç teknik ve net olsun; PD ve BI etkilerini ayrı başlıklarda yaz.
- Faaliyet: {s.faaliyet}
- Yapı Türü: {s.yapi_turu} | Bina Yaşı: {s.bina_yasi} | Kat: {s.kat_sayisi}
- Bölge: {s.rg} | Güçlendirme: {s.guclendirme}
- PD Oranı: {round(pd_ratio*100,1)}%
- BI Beklenen Kesinti: {bi_days} gün
- BI Bekleme (muafiyet): {s.bi_gun_muafiyeti} gün
Türkçe yaz.
"""
    prompt_en = f"""
Write a concise, technical earthquake damage scenario with separate PD and BI sections:
- Activity: {s.faaliyet}
- Building: {s.yapi_turu} | Age: {s.bina_yasi} | Floors: {s.kat_sayisi}
- Zone: {s.rg} | Retrofit: {s.guclendirme}
- PD Ratio: {round(pd_ratio*100,1)}%
- BI Expected Downtime: {bi_days} days
- BI Time Deductible: {s.bi_gun_muafiyeti} days
English output.
"""
    use_tr = lang.lower().startswith("tr")
    try:
        # Yeni SDK varsa:
        if 'genai' in globals() and isinstance(globals().get('_genai_new'), object):
            client = _genai_new.Client(api_key=GEMINI_API_KEY)
            content = client.models.generate_content(
                model="gemini-1.5-pro",
                contents=_genai_types.Content(role="user", parts=[_genai_types.Part.from_text(prompt_tr if use_tr else prompt_en)])
            )
            return content.text.strip() if getattr(content, "text", None) else _static_report(s, pd_ratio, bi_days, lang)
        # Eski SDK’ya düş:
        _genai_old.configure(api_key=GEMINI_API_KEY)
        model = _genai_old.GenerativeModel("gemini-1.5-pro")
        resp = model.generate_content(prompt_tr if use_tr else prompt_en)
        return getattr(resp, "text", None) or _static_report(s, pd_ratio, bi_days, lang)
    except Exception:
        return _static_report(s, pd_ratio, bi_days, lang)

# --- UI ---
st.set_page_config(page_title=tr("title"), layout="wide", page_icon="📉")

# Dil seçimi (üstte, basit)
if "lang" not in st.session_state:
    st.session_state["lang"] = "TR"
c1, c2 = st.columns([1, 4])
with c1:
    st.selectbox(tr("sidebar_language"), ["TR", "EN"], index=0 if st.session_state["lang"]=="TR" else 1,
                 key="lang")

st.title(tr("title"))

st.subheader(tr("inputs_header"))
col1, col2, col3 = st.columns(3)
with col1:
    si_pd = st.number_input(tr("pd_ins"), min_value=1_000_000, value=250_000_000, step=1_000_000)
    rg = st.selectbox(tr("risk_zone"), options=[1,2,3,4,5], index=2)
    floors = st.selectbox(tr("floors"), ["1-3 kat", "4-7 kat", "8+ kat"], index=1)
with col2:
    si_bi = st.number_input(tr("bi_ins"), min_value=0, value=100_000_000, step=1_000_000)
    btype = st.selectbox(tr("btype"), ["Betonarme","Çelik","Prefabrik","Yığma"], index=0)
    bage = st.selectbox(tr("bage"), ["0-5 yıl","5-10 yıl","10-30 yıl","30+ yıl"], index=2)
with col3:
    activity = st.text_input(tr("activity"), value="İplik Fabrikası")
    retrofit = st.selectbox(tr("retrofit"), ["Yok","Kısmi","Tam"], index=0)
    bi_wait = st.number_input(tr("bi_wait"), min_value=0, value=14, step=1)

run = st.button(tr("btn_run"))

if run:
    s = ScenarioInputs(
        si_pd=int(si_pd), si_bi=int(si_bi), rg=int(rg),
        yapi_turu=btype, bina_yasi=bage, kat_sayisi=floors,
        faaliyet=activity, guclendirme=retrofit, bi_gun_muafiyeti=int(bi_wait)
    )
    ratios = calculate_damage_ratios(s)
    pd_ratio = ratios["pd_ratio"]
    bi_days = ratios["bi_days"]

    pd_damage = int(round(s.si_pd * pd_ratio))
    # BI basit yaklaşım: BI SI yıllık; gün düşümü = min(bi_days, 365 - muafiyet)
    net_bi_days = max(0, min(365, bi_days) - s.bi_gun_muafiyeti)
    bi_damage = int(round((s.si_bi / 365.0) * net_bi_days)) if s.si_bi else 0

    st.subheader(tr("calc_header"))
    m1, m2 = st.columns(2)
    m1.metric(tr("pd_damage_amount"), money(pd_damage))
    m2.metric(tr("bi_damage_amount"), money(bi_damage))

    with st.expander(tr("ai_header"), expanded=True):
        report = _ai_report(s, pd_ratio, bi_days, st.session_state["lang"])
        st.markdown(report)

st.info(tr("disclaimer"))
