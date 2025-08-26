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
# 1. Gelişmiş Risk Parametreleri: Zemin Sınıfı, İçerik Kırılganlığı,
#    Deprem Sonrası Yangın Riski, Tedarikçi Yoğunlaşması gibi profesyonel
#    düzeyde risk faktörleri analize dahil edilmiştir.
# 2. Teknik Olarak Doğrulanmış Hesaplama: Prim ve tazminat hesaplamaları,
#    01/01/2025 tarihli İhtiyari Deprem Tarifesi'ne tam uyumludur.
# 3. Gelişmiş AI Raporu: Gemini API, girilen tüm gelişmiş parametreleri
#    dikkate alarak çok daha derinlikli ve teknik bir hasar raporu oluşturur.
# 4. Yeniden Tasarlanan Arayüz: Tüm girdiler, daha iyi bir kullanıcı deneyimi
#    için ana ekranda, mantıksal gruplar halinde üç sütunda toplanmıştır.

import streamlit as st
import pandas as pd
import plotly.express as px
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

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
    "inputs_header": {"TR": "1. Senaryo Girdileri", "EN": "1. Scenario Inputs"},
    "results_header": {"TR": "2. Analiz Sonuçları", "EN": "2. Analysis Results"},
    "analysis_header": {"TR": "3. Poliçe Alternatifleri Analizi", "EN": "3. Policy Alternatives Analysis"},
    "base_header": {"TR": "Temel Tesis ve Hasar Bilgileri", "EN": "Basic Facility and Damage Information"},
    "pd_header": {"TR": "Gelişmiş Maddi Hasar (PD) Parametreleri", "EN": "Advanced Property Damage (PD) Parameters"},
    "bi_header": {"TR": "Gelişmiş İş Durması (BI) Parametreleri", "EN": "Advanced Business Interruption (BI) Parameters"},
    "activity": {"TR": "Faaliyet Kolu", "EN": "Line of Business"},
    "si_pd": {"TR": "PD Toplam Sigorta Bedeli (₺)", "EN": "PD Total Sum Insured (TRY)"},
    "risk_zone": {"TR": "Deprem Risk Bölgesi", "EN": "Earthquake Risk Zone"},
    "btype": {"TR": "Yapı Türü", "EN": "Building Type"},
    "bage": {"TR": "Bina Yaşı", "EN": "Building Age"},
    "zemin": {"TR": "Zemin Sınıfı", "EN": "Soil Class"},
    "icerik": {"TR": "İçerik (Muhteviyat) Kırılganlığı", "EN": "Contents Vulnerability"},
    "ffe": {"TR": "Deprem Sonrası Yangın Riski", "EN": "Fire Following Earthquake (FFE) Risk"},
    "duzensizlik": {"TR": "Yapısal Düzensizlik (Yumuşak Kat)", "EN": "Structural Irregularity (Soft Story)"},
    "si_bi": {"TR": "Yıllık BI Bedeli (₺)", "EN": "Annual BI Sum Insured (TRY)"},
    "azami_tazminat": {"TR": "Azami Tazminat Süresi", "EN": "Max. Indemnity Period"},
    "makine": {"TR": "Kritik Makine Bağımlılığı", "EN": "Critical Machinery Dependency"},
    "tedarikci": {"TR": "Tedarikçi Yoğunlaşma Riski", "EN": "Supplier Concentration Risk"},
    "altyapi": {"TR": "Altyapı Kesinti Riski (Gün)", "EN": "Infrastructure Outage Risk (Days)"},
    "stok": {"TR": "Bitmiş Ürün Stoğu (Gün)", "EN": "Finished Goods Stock (Days)"},
    "bi_wait": {"TR": "BI Bekleme Süresi (gün)", "EN": "BI Waiting Period (days)"},
    "pd_damage_amount": {"TR": "Beklenen PD Hasar Tutarı", "EN": "Expected PD Damage Amount"},
    "bi_downtime": {"TR": "Beklenen Kesinti Süresi", "EN": "Expected Downtime"},
    "bi_damage_amount": {"TR": "Beklenen BI Hasar Tutarı", "EN": "Expected BI Damage Amount"},
    "ai_header": {"TR": "AI Deprem Hasar Uzmanı Raporu", "EN": "AI Earthquake Damage Expert Report"},
    "table_analysis": {"TR": "📊 Tablo Analizi", "EN": "📊 Table Analysis"},
    "visual_analysis": {"TR": "📈 Maliyet-Risk Analizi", "EN": "📈 Cost-Risk Analysis"},
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
    faaliyet: str = "Plastik Enjeksiyon Üretim Fabrikası"
    zemin_sinifi: str = "ZC - Orta Sıkı Zemin (Varsayılan)"
    icerik_kirilganligi: str = "Orta (Standart Makine/Emtia - Varsayılan)"
    ffe_riski: str = "Orta (Tekstil/Plastik Enjeksiyon)"
    yapısal_duzensizlik: str = "Yok / Bilinmiyor (Varsayılan)"
    azami_tazminat_suresi: int = 365 # Gün olarak
    kritik_makine_bagimliligi: str = "Orta (Kısmen İthal/Özelleştirilmiş)"
    tedarikci_yogunlasma_riski: str = "Orta (Bazı tedarikçiler aynı bölgede)"
    altyapi_kesinti_riski: int = 15
    bitmis_urun_stogu: int = 15
    bi_gun_muafiyeti: int = 14

# --- TEKNİK HESAPLAMA ÇEKİRDEĞİ ---
def calculate_pd_ratio(s: ScenarioInputs) -> float:
    base = _DEPREM_ORAN.get(s.rg, 0.13)
    factor = 1.0
    # Temel Faktörler
    factor *= {"Betonarme": 1.0, "Çelik": 0.85, "Yığma": 1.20, "Diğer": 1.1}.get(s.yapi_turu, 1.0)
    factor *= {"< 10 yaş": 0.90, "10-30 yaş": 1.0, "> 30 yaş": 1.15}.get(s.bina_yasi, 1.0)
    # Gelişmiş PD Faktörleri
    factor *= {"ZA/ZB": 0.85, "ZC": 1.00, "ZD": 1.20, "ZE": 1.50}.get(s.zemin_sinifi.split(' ')[0], 1.0)
    factor *= {"Düşük": 0.80, "Orta": 1.00, "Yüksek": 1.30}.get(s.icerik_kirilganligi.split(' ')[0], 1.0)
    factor *= {"Düşük": 1.00, "Orta": 1.15, "Yüksek": 1.40}.get(s.ffe_riski.split(' ')[0], 1.0)
    factor *= {"Yok": 1.00, "Var": 1.40}.get(s.yapısal_duzensizlik.split(' ')[0], 1.0)
    return min(0.70, max(0.01, base * factor))

def calculate_bi_downtime(pd_ratio: float, s: ScenarioInputs) -> int:
    # PD hasarına dayalı temel onarım süresi
    base_repair_days = 30 + (pd_ratio * 300)
    # Operasyonel faktörler bu süreyi uzatır
    operational_factor = 1.0
    operational_factor *= {"Düşük": 1.00, "Orta": 1.25, "Yüksek": 1.60}.get(s.kritik_makine_bagimliligi.split(' ')[0], 1.0)
    operational_factor *= {"Düşük": 1.00, "Orta": 1.20, "Yüksek": 1.50}.get(s.tedarikci_yogunlasma_riski.split(' ')[0], 1.0)
    # Brüt kesinti süresi
    gross_downtime = base_repair_days * operational_factor
    # Altyapı ve stok etkileri
    # Altyapı kesintisi, onarım süresinden uzunsa, kesinti süresini belirler.
    gross_downtime = max(gross_downtime, s.altyapi_kesinti_riski)
    # Stok, kar kaybının başlamasını geciktirir
    net_downtime_before_indemnity = gross_downtime - s.bitmis_urun_stogu
    # Sonuç, azami tazminat süresi ile sınırlandırılır
    final_downtime = min(s.azami_tazminat_suresi, net_downtime_before_indemnity)
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
    if is_bi:
        return (prim_bedeli * base_rate) / 1000.0
    factor = KOAS_FACTORS.get(koas, 1.0) * MUAFIYET_FACTORS.get(muaf, 1.0)
    return (prim_bedeli * base_rate * factor) / 1000.0

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

    def static_report():
        pd_pct = f"{pd_ratio:.1%}"
        if use_tr:
            return f"**Deprem Hasar Değerlendirmesi (Standart Rapor)**\n\n**Maddi Hasar (PD):** Tesis özelliklerine göre beklenen hasar oranı yaklaşık **{pd_pct}**'dir.\n\n**İş Durması (BI):** Tahmini kesinti süresi **{bi_days} gündür**.\n\n> *Bu rapor, AI servisinin aktif olmaması nedeniyle standart şablon kullanılarak oluşturulmuştur.*"
        else:
            return f"**Earthquake Damage Assessment (Standard Report)**\n\n**Property Damage (PD):** Based on facility specs, the expected damage ratio is approx. **{pd_pct}**.\n\n**Business Interruption (BI):** Estimated downtime is **{bi_days} days**.\n\n> *This is a static report generated because the AI service is not active.*"

    if not _GEMINI_AVAILABLE:
        return static_report()

    prompt_template = """
Sen, sigorta şirketleri için çalışan kıdemli bir deprem risk mühendisi ve hasar uzmanısın. Görevin, aşağıda bilgileri verilen endüstriyel tesis için beklenen bir deprem sonrası oluşacak hasarları, teknik ve profesyonel bir dille raporlamaktır. Raporu "Maddi Hasar (PD) Değerlendirmesi" ve "İş Durması (BI) Değerlendirmesi" olmak üzere iki ana başlık altında, madde işaretleri kullanarak sun. Faaliyet koluna ve girilen tüm gelişmiş risk parametrelerine özel, somut ve gerçekçi hasar örnekleri ver.

**Tesis Bilgileri:**
- **Faaliyet Kolu:** {faaliyet}
- **Yapı Türü / Yaşı:** {yapi_turu} / {bina_yasi}
- **Deprem Risk Bölgesi:** {rg}. Derece
- **Zemin Sınıfı:** {zemin_sinifi}
- **İçerik Kırılganlığı:** {icerik_kirilganligi}
- **Deprem Sonrası Yangın Riski:** {ffe_riski}
- **Yapısal Düzensizlik:** {yapısal_duzensizlik}
- **Kritik Makine Bağımlılığı:** {kritik_makine_bagimliligi}
- **Tedarikçi Yoğunlaşma Riski:** {tedarikci_yogunlasma_riski}

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

    s_inputs = ScenarioInputs()

    st.header(tr("inputs_header"))
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader(tr("base_header"))
        s_inputs.faaliyet = st.text_input(tr("activity"), "Plastik Enjeksiyon Üretim Fabrikası")
        s_inputs.si_pd = st.number_input(tr("si_pd"), min_value=1_000_000, value=250_000_000, step=10_000_000)
        s_inputs.rg = st.select_slider(tr("risk_zone"), options=[1,2,3,4,5,6,7], value=3)
        s_inputs.yapi_turu = st.selectbox(tr("btype"), ["Betonarme", "Çelik", "Yığma", "Diğer"])
        s_inputs.bina_yasi = st.selectbox(tr("bage"), ["< 10 yaş", "10-30 yaş", "> 30 yaş"], index=1)

    with col2:
        st.subheader(tr("pd_header"))
        s_inputs.zemin_sinifi = st.selectbox(tr("zemin"), ["ZC - Orta Sıkı Zemin (Varsayılan)", "ZA/ZB - Kaya/Sıkı Zemin", "ZD - Orta Gevşek Zemin", "ZE - Yumuşak/Gevşek Zemin"])
        s_inputs.icerik_kirilganligi = st.selectbox(tr("icerik"), ["Orta (Standart Makine/Emtia - Varsayılan)", "Düşük (Dayanıklı/Dökme Mallar)", "Yüksek (Hassas Elektronik/Cam/Kimyasal)"])
        s_inputs.ffe_riski = st.selectbox(tr("ffe"), ["Düşük (Ofis/Depo - Varsayılan)", "Orta (Tekstil/Plastik Enjeksiyon)", "Yüksek (Kimya/Petrokimya/Rafineri)"])
        s_inputs.yapısal_duzensizlik = st.selectbox(tr("duzensizlik"), ["Yok / Bilinmiyor (Varsayılan)", "Var"])

    with col3:
        st.subheader(tr("bi_header"))
        s_inputs.si_bi = st.number_input(tr("si_bi"), min_value=0, value=100_000_000, step=10_000_000)
        s_inputs.azami_tazminat_suresi = st.selectbox(tr("azami_tazminat"), [365, 540, 730], format_func=lambda x: f"{int(x/30)} Ay")
        s_inputs.kritik_makine_bagimliligi = st.selectbox(tr("makine"), ["Düşük (Yerli/Standart Ekipman - Varsayılan)", "Orta (Kısmen İthal/Özelleştirilmiş)", "Yüksek (Tamamen İthal/Özel Üretim)"])
        s_inputs.tedarikci_yogunlasma_riski = st.selectbox(tr("tedarikci"), ["Düşük / Farklı Bölgelerde (Varsayılan)", "Orta (Bazı tedarikçiler aynı bölgede)", "Yüksek (Kritik tedarikçiler aynı bölgede)"])
        s_inputs.altyapi_kesinti_riski = st.number_input(tr("altyapi"), value=15)
        s_inputs.bitmis_urun_stogu = st.number_input(tr("stok"), value=15)
        s_inputs.bi_gun_muafiyeti = st.number_input(tr("bi_wait"), min_value=0, value=14, step=1)
    
    st.markdown("---")
    run_button = st.button(tr("btn_run"), use_container_width=True, type="primary")

    if run_button:
        pd_ratio = calculate_pd_ratio(s_inputs)
        bi_days = calculate_bi_downtime(pd_ratio, s_inputs)
        pd_damage_amount = s_inputs.si_pd * pd_ratio
        net_bi_days = max(0, bi_days - s_inputs.bi_gun_muafiyeti)
        bi_damage_amount = (s_inputs.si_bi / 365.0) * net_bi_days if s_inputs.si_bi > 0 else 0

        st.header(tr("results_header"))
        with st.spinner("AI Deprem Hasar Uzmanı raporu hazırlıyor..."):
            report = generate_report(s_inputs, pd_ratio, bi_days)
            st.markdown(report, unsafe_allow_html=True)
        
        m1, m2, m3 = st.columns(3)
        m1.metric(tr("pd_damage_amount"), money(pd_damage_amount), f"{pd_ratio:.2%}")
        m2.metric(tr("bi_downtime"), f"{bi_days} gün", "Net Kesinti")
        m3.metric(tr("bi_damage_amount"), money(bi_damage_amount), f"{net_bi_days} gün tazmin edilebilir")
        
        st.markdown("---")
        st.header(tr("analysis_header"))
        
        koas_opts, muaf_opts = get_allowed_options(s_inputs.si_pd)
        results = []
        for koas in koas_opts:
            for muaf in muaf_opts:
                prim_pd = calculate_premium(s_inputs.si_pd, s_inputs.yapi_turu, s_inputs.rg, koas, muaf)
                prim_bi = calculate_premium(s_inputs.si_bi, s_inputs.yapi_turu, s_inputs.rg, koas, muaf, is_bi=True)
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
            st.dataframe(df.style.format("{:,.0f}", subset=df.columns[1:]), use_container_width=True)
        
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
