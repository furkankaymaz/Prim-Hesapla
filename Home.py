# -*- coding: utf-8 -*-
# home.py — TariffEQ Scenario + AI (single-file Streamlit app)
#
# Bu uygulama, kullanıcının girdiği bilgilere dayanarak AI destekli,
# detaylı bir Maddi Hasar (PD) ve İş Durması (BI) senaryosu oluşturur.
# Ardından, tüm olası koasürans ve muafiyet alternatifleri için net
# hasar ve tazminat hesaplamalarını yaparak, en uygun poliçe yapısının
# görsel olarak analiz edilmesini sağlar.
#
# Çalışma Mantığı:
# - Google Gemini API anahtarı varsa (AIzaSyAjbjgJDHqXpJK9euPWLkfgiMOSyOTOx1M), AI raporu üretir.
# - Yoksa, güvenli ve bilgilendirici bir statik metne otomatik olarak düşer.
# - Tüm mantık (çeviri, hesaplama, UI) bu tek dosyada toplanmıştır.

import os
import math
import streamlit as st
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Tuple

# --- AI İÇİN KORUMALI IMPORT (yoksa statik moda düşer) ---
_GEMINI_AVAILABLE = False
try:
    # google-generativeai kütüphanesini import etmeye çalış
    import google.generativeai as genai
    _GEMINI_AVAILABLE = True
except ImportError:
    # Kütüphane yoksa, AI fonksiyonları çalışmaz
    _GEMINI_AVAILABLE = False

# Ortam değişkenlerinden Gemini API anahtarını al
AIzaSyAjbjgJDHqXpJK9euPWLkfgiMOSyOTOx1M = os.environ.get("AIzaSyAjbjgJDHqXpJK9euPWLkfgiMOSyOTOx1M")
if _GEMINI_AVAILABLE and AIzaSyAjbjgJDHqXpJK9euPWLkfgiMOSyOTOx1M:
    try:
        genai.configure(api_key=AIzaSyAjbjgJDHqXpJK9euPWLkfgiMOSyOTOx1M)
    except Exception as e:
        # API anahtarı geçersizse veya başka bir konfigürasyon hatası olursa
        _GEMINI_AVAILABLE = False
        st.sidebar.warning("Gemini API anahtarı geçersiz veya bir hata oluştu. AI özellikleri devre dışı.", icon="⚠️")


# --- BASİT ÇEVİRİ SÖZLÜĞÜ ---
T = {
    "title": {"TR": "TariffEQ – AI Destekli Hasar Analizi", "EN": "TariffEQ – AI-Powered Damage Analysis"},
    "sidebar_language": {"TR": "Language / Dil", "EN": "Language / Dil"},
    "inputs_header": {"TR": "1. Senaryo Girdileri", "EN": "1. Scenario Inputs"},
    "pd_header": {"TR": "Maddi Hasar (PD) Bilgileri", "EN": "Property Damage (PD) Information"},
    "bi_header": {"TR": "İş Durması (BI) Bilgileri", "EN": "Business Interruption (BI) Information"},
    "si_pd": {"TR": "PD Sigorta Bedeli (₺)", "EN": "PD Sum Insured (TRY)"},
    "si_bi": {"TR": "Yıllık BI Bedeli (₺)", "EN": "Annual BI Sum Insured (TRY)"},
    "risk_zone": {"TR": "Deprem Risk Bölgesi (1=En Riskli)", "EN": "Earthquake Risk Zone (1=Highest)"},
    "btype": {"TR": "Yapı Türü", "EN": "Building Type"},
    "bage": {"TR": "Bina Yaşı", "EN": "Building Age"},
    "floors": {"TR": "Kat Sayısı", "EN": "Number of Floors"},
    "activity": {"TR": "Faaliyet Kolu", "EN": "Line of Business"},
    "retrofit": {"TR": "Güçlendirme", "EN": "Retrofitting"},
    "bi_wait": {"TR": "BI Bekleme Süresi (gün)", "EN": "BI Waiting Period (days)"},
    "supplier_dep": {"TR": "Tedarikçi Bağımlılığı", "EN": "Supplier Dependency"},
    "alt_site": {"TR": "Alternatif Tesis Durumu", "EN": "Alternate Site Availability"},
    "results_header": {"TR": "2. Analiz Sonuçları", "EN": "2. Analysis Results"},
    "pd_damage_amount": {"TR": "Beklenen PD Hasar Tutarı", "EN": "Expected PD Damage Amount"},
    "bi_downtime": {"TR": "Beklenen Kesinti Süresi", "EN": "Expected Downtime"},
    "bi_damage_amount": {"TR": "Beklenen BI Hasar Tutarı", "EN": "Expected BI Damage Amount"},
    "ai_header": {"TR": "AI Deprem Hasar Uzmanı Raporu", "EN": "AI Earthquake Damage Expert Report"},
    "analysis_header": {"TR": "3. Poliçe Alternatifleri Analizi", "EN": "3. Policy Alternatives Analysis"},
    "table_analysis": {"TR": "📊 Tablo Analizi", "EN": "📊 Table Analysis"},
    "visual_analysis": {"TR": "📈 Görsel Analiz", "EN": "📈 Visual Analysis"},
    "disclaimer": {
        "TR": "Bu çıktı yalnızca demonstrasyon amaçlıdır ve resmi bir hasar tespiti veya sigorta teklifinin yerini almaz.",
        "EN": "This output is for demonstration purposes only and does not replace a formal damage assessment or insurance quotation."
    },
    "btn_run": {"TR": "Analizi Çalıştır", "EN": "Run Analysis"},
}

# --- YARDIMCI FONKSİYONLAR ---
def tr(key: str) -> str:
    lang = st.session_state.get("lang", "TR")
    return T.get(key, {}).get(lang, key)

def money(x: float) -> str:
    return f"₺{x:,.0f}".replace(",", ".")

# --- GİRDİ VE HESAPLAMA MODELLERİ ---
@dataclass
class ScenarioInputs:
    si_pd: int = 250_000_000
    si_bi: int = 100_000_000
    rg: int = 3
    yapi_turu: str = "Betonarme"
    bina_yasi: str = "10-30 yıl"
    kat_sayisi: str = "4-7 kat"
    faaliyet: str = "İplik Fabrikası"
    guclendirme: str = "Yok"
    bi_gun_muafiyeti: int = 14
    tedarikci_bagimliligi: str = "Orta"
    alternatif_tesis: str = "Yok"

_DEPREM_ORAN = {
    1: 0.20, 2: 0.17, 3: 0.13, 4: 0.09, 5: 0.06, 6: 0.06, 7: 0.06
}

def calculate_pd_ratio(s: ScenarioInputs) -> float:
    base = _DEPREM_ORAN.get(s.rg, 0.13)
    factor = 1.0
    factor *= {"Betonarme": 1.0, "Çelik": 0.85, "Yığma": 1.20, "Diğer": 1.1}.get(s.yapi_turu, 1.0)
    factor *= {"< 10 yaş": 0.90, "10-30 yaş": 1.0, "> 30 yaş": 1.15}.get(s.bina_yasi, 1.0)
    factor *= {"1-3 kat": 0.95, "4-7 kat": 1.0, "8+ kat": 1.1}.get(s.kat_sayisi, 1.0)
    factor *= {"Yok": 1.0, "Var": 0.85}.get(s.guclendirme, 1.0)
    return min(0.70, max(0.01, base * factor))

def calculate_bi_downtime(pd_ratio: float, s: ScenarioInputs) -> int:
    # Maddi hasar ne kadar büyükse, temel kesinti o kadar uzun olur.
    base_days = 30 + (pd_ratio * 300)
    
    # Operasyonel faktörler bu süreyi artırır veya azaltır.
    factor = 1.0
    factor *= {"Düşük": 0.9, "Orta": 1.0, "Yüksek": 1.2}.get(s.tedarikci_bagimliligi, 1.0)
    factor *= {"Var": 0.7, "Yok": 1.0}.get(s.alternatif_tesis, 1.0)
    
    return min(365, int(base_days * factor))

def get_allowed_options(si_pd: int) -> Tuple[List[str], List[float]]:
    koas_base = ["80/20", "75/25", "70/30", "65/35", "60/40", "55/45", "50/50", "45/55", "40/60"]
    muaf_base = [2.0, 3.0, 4.0, 5.0, 10.0]
    if si_pd > 3_500_000_000:
        koas_ext = ["90/10", "100/0"]
        muaf_ext = [0.1, 0.5, 1.0, 1.5]
        return koas_base + koas_ext, muaf_base + muaf_ext
    return koas_base, muaf_base

def calculate_net_claim(si_pd: int, hasar_tutari: float, koas: str, muaf_pct: float) -> Dict[str, float]:
    muafiyet_tutari = si_pd * (muaf_pct / 100.0)
    muafiyet_sonrasi_hasar = max(0.0, hasar_tutari - muafiyet_tutari)
    sirket_pay_orani = float(koas.split('/')[0]) / 100.0
    net_tazminat = muafiyet_sonrasi_hasar * sirket_pay_orani
    sigortalida_kalan = hasar_tutari - net_tazminat
    return {"net_tazminat": net_tazminat, "sigortalida_kalan": sigortalida_kalan}

# --- AI RAPOR ÜRETİMİ ---
def generate_report(s: ScenarioInputs, pd_ratio: float, bi_days: int) -> str:
    lang = st.session_state.get("lang", "TR")
    use_tr = lang.startswith("TR")

    # Statik Rapor (Fallback)
    def static_report():
        pd_pct = f"{pd_ratio:.1%}"
        if use_tr:
            return f"""**Deprem Hasar Değerlendirmesi (Beklenen Senaryo)**

**Tesis:** {s.faaliyet} ({s.yapi_turu}, {s.bina_yasi}) | **Bölge:** {s.rg}. Derece

**Maddi Hasar (PD):** Yapısal ve operasyonel özellikler göz önüne alındığında, tesiste yaklaşık **{pd_pct}** oranında bir maddi hasar beklenmektedir. Bu oran, özellikle faaliyetinize özel makine ve teçhizatta önemli hasarlar anlamına gelebilir.

**İş Durması (BI):** Maddi hasarın onarımı ve operasyonların yeniden stabil hale gelmesi için tahmini kesinti süresi **{bi_days} gündür**. Bu süre, tedarik zinciri ve alternatif tesis imkanlarına göre değişiklik gösterebilir.

> *Bu rapor, AI servisinin aktif olmaması nedeniyle standart şablon kullanılarak oluşturulmuştur.*"""
        else:
            return f"""**Earthquake Damage Assessment (Expected Scenario)**

**Facility:** {s.faaliyet} ({s.yapi_turu}, {s.bina_yasi}) | **Zone:** {s.rg}

**Property Damage (PD):** Considering the structural and operational characteristics, an estimated property damage of **{pd_pct}** is expected. This could imply significant damage to specialized machinery and equipment.

**Business Interruption (BI):** The estimated downtime to repair damages and stabilize operations is **{bi_days} days**. This period may vary depending on supply chain and alternate site availability.

> *This is a static report generated because the AI service is not active.*"""

    if not _GEMINI_AVAILABLE or not AIzaSyAjbjgJDHqXpJK9euPWLkfgiMOSyOTOx1M:
        return static_report()

    # Gemini AI Raporu
    prompt_template = """
Sen bir deprem risk mühendisi ve sigorta hasar uzmanısın. Aşağıdaki bilgilere sahip bir tesis için teknik, profesyonel ve gerçekçi bir dille, beklenen deprem hasar senaryosu raporu hazırla. Raporu "Maddi Hasar (PD) Değerlendirmesi" ve "İş Durması (BI) Değerlendirmesi" olmak üzere iki ana başlık altında sun. Faaliyet koluna özel detaylar ekle.

**Tesis Bilgileri:**
- **Faaliyet Kolu:** {faaliyet}
- **Yapı Türü / Yaşı:** {yapi_turu} / {bina_yasi}
- **Deprem Risk Bölgesi:** {rg}. Derece
- **Güçlendirme Durumu:** {guclendirme}
- **Tedarikçi Bağımlılığı:** {tedarikci_bagimliligi}
- **Alternatif Tesis:** {alternatif_tesis}

**Hesaplanan Senaryo Değerleri:**
- **Beklenen Maddi Hasar Oranı:** {pd_ratio:.1%}
- **Tahmini Toplam Kesinti Süresi:** {bi_days} gün
- **BI Poliçesi Bekleme Süresi:** {bi_gun_muafiyeti} gün

Raporu {lang} dilinde oluştur.
"""
    prompt = prompt_template.format(lang="Türkçe" if use_tr else "English", pd_ratio=pd_ratio, bi_days=bi_days, **s.__dict__)

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.sidebar.error(f"AI Raporu oluşturulamadı: {e}", icon="🤖")
        return static_report()

# --- STREAMLIT UYGULAMASI ---
def main():
    st.set_page_config(page_title=tr("title"), layout="wide", page_icon="📉")
    st.title(tr("title"))

    # --- GİRDİLER (KENAR ÇUBUĞU) ---
    with st.sidebar:
        c1, c2 = st.columns(2)
        c1.selectbox(tr("sidebar_language"), ["TR", "EN"], key="lang", index=["TR", "EN"].index(st.session_state.get("lang", "TR")))
        
        st.header(tr("inputs_header"))
        
        st.subheader(tr("pd_header"))
        s_inputs = ScenarioInputs()
        s_inputs.faaliyet = st.text_input(tr("activity"), "İplik Fabrikası")
        s_inputs.si_pd = st.number_input(tr("si_pd"), min_value=1_000_000, value=250_000_000, step=1_000_000)
        s_inputs.rg = st.select_slider(tr("risk_zone"), options=[1,2,3,4,5,6,7], value=3)
        s_inputs.yapi_turu = st.selectbox(tr("btype"), ["Betonarme", "Çelik", "Yığma", "Diğer"])
        s_inputs.bina_yasi = st.selectbox(tr("bage"), ["< 10 yaş", "10-30 yaş", "> 30 yaş"], index=1)
        s_inputs.kat_sayisi = st.selectbox(tr("floors"), ["1-3 kat", "4-7 kat", "8+ kat"], index=1)
        s_inputs.guclendirme = st.radio(tr("retrofit"), ["Yok", "Var"], index=0, horizontal=True)

        st.subheader(tr("bi_header"))
        s_inputs.si_bi = st.number_input(tr("si_bi"), min_value=0, value=100_000_000, step=1_000_000)
        s_inputs.bi_gun_muafiyeti = st.number_input(tr("bi_wait"), min_value=0, value=14, step=1)
        s_inputs.tedarikci_bagimliligi = st.select_slider(tr("supplier_dep"), ["Düşük", "Orta", "Yüksek"], value="Orta")
        s_inputs.alternatif_tesis = st.radio(tr("alt_site"), ["Var", "Yok"], index=1, horizontal=True)

        run_button = st.button(tr("btn_run"), use_container_width=True, type="primary")

    # --- ANA EKRAN ---
    if run_button:
        # 1. Hasar Oranlarını ve Sürelerini Hesapla
        pd_ratio = calculate_pd_ratio(s_inputs)
        bi_days = calculate_bi_downtime(pd_ratio, s_inputs)
        pd_damage_amount = s_inputs.si_pd * pd_ratio
        net_bi_days = max(0, bi_days - s_inputs.bi_gun_muafiyeti)
        bi_damage_amount = (s_inputs.si_bi / 365.0) * net_bi_days if s_inputs.si_bi > 0 else 0

        st.header(tr("results_header"))

        # 2. AI Raporunu Göster
        with st.expander(tr("ai_header"), expanded=True):
            with st.spinner("AI Deprem Hasar Uzmanı raporu hazırlıyor..."):
                report = generate_report(s_inputs, pd_ratio, bi_days)
                st.markdown(report)
        
        # 3. Ana Metrikleri Göster
        m1, m2, m3 = st.columns(3)
        m1.metric(tr("pd_damage_amount"), money(pd_damage_amount), f"{pd_ratio:.2%}")
        m2.metric(tr("bi_downtime"), f"{bi_days} gün", "Brüt")
        m3.metric(tr("bi_damage_amount"), money(bi_damage_amount), f"{net_bi_days} gün net")
        
        st.markdown("---")
        st.header(tr("analysis_header"))
        
        # 4. Tüm Alternatifleri Hesapla
        koas_opts, muaf_opts = get_allowed_options(s_inputs.si_pd)
        results = []
        for koas in koas_opts:
            for muaf in muaf_opts:
                pd_claim = calculate_net_claim(s_inputs.si_pd, pd_damage_amount, koas, muaf)
                total_damage = pd_damage_amount + bi_damage_amount
                total_payout = pd_claim["net_tazminat"] + bi_damage_amount # BI hasarı tam ödenir varsayımı
                retained_risk = total_damage - total_payout
                
                results.append({
                    "Poliçe Yapısı": f"{koas} / {muaf}%",
                    "Net PD Tazminatı": pd_claim["net_tazminat"],
                    "Net BI Tazminatı": bi_damage_amount,
                    "Toplam Net Tazminat": total_payout,
                    "Sigortalıda Kalan Risk": retained_risk,
                })
        df = pd.DataFrame(results)

        # 5. Sonuçları Sekmelerde Sun
        tab1, tab2 = st.tabs([tr("table_analysis"), tr("visual_analysis")])
        with tab1:
            st.markdown("Aşağıdaki tabloda, tüm olası poliçe yapıları için hasar sonrası alacağınız net tazminatı ve şirketinizde kalacak riski karşılaştırabilirsiniz.")
            st.dataframe(df.style.format("{:,.0f}", subset=["Net PD Tazminatı", "Net BI Tazminatı", "Toplam Net Tazminat", "Sigortalıda Kalan Risk"]), use_container_width=True)
        
        with tab2:
            st.markdown("Bu grafik, en verimli poliçe alternatifini bulmanıza yardımcı olur. **Amaç, sağ üst köşeye en yakın noktayı bulmaktır.** Bu noktalar, hem **alacağınız tazminatı maksimize eden** hem de **şirketinizde kalacak riski minimize eden** en verimli seçenekleri temsil eder.")
            fig = px.scatter(
                df,
                x="Sigortalıda Kalan Risk",
                y="Toplam Net Tazminat",
                color="Toplam Net Tazminat",
                color_continuous_scale=px.colors.sequential.Viridis,
                hover_data=["Poliçe Yapısı"],
                title="Poliçe Alternatifleri Risk-Tazminat Analizi"
            )
            fig.update_traces(marker=dict(size=10, line=dict(width=1, color='DarkSlateGrey')))
            fig.update_layout(
                xaxis_title="Hasarda Şirketinizde Kalacak Risk (Düşük olması hedeflenir)",
                yaxis_title="Alınacak Toplam Net Tazminat (Yüksek olması hedeflenir)"
            )
            st.plotly_chart(fig, use_container_width=True)
            
    st.info(tr("disclaimer"))

if __name__ == "__main__":
    main()
