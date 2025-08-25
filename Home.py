# -*- coding: utf-8 -*-
"""
TariffEQ – AI Destekli Ticari Deprem Hasar & Prim Analiz Modülü
================================================================================

Bu sürüm, kullanıcının girdiği bilgilere dayanarak AI destekli ve gerçekçi bir
hasar senaryosu oluşturur. Ardından, tüm olası koasürans ve muafiyet
alternatifleri için prim ve net tazminat hesaplamalarını yaparak, kullanıcının
en uygun poliçe yapısını kolayca bulmasını sağlar.

Öne Çıkanlar
------------
- **AI Hasar Uzmanı:** Faaliyet koluna özel, teknik detaylar içeren dinamik bir
  Maddi Hasar (PD) ve İş Durması (BI) senaryosu üretir.
- **Teknik Olarak Doğru Hesaplama:** Tazminat hesaplaması, sigortacılık
  tekniğine uygun olarak (muafiyetin sigorta bedelinden düşülmesi vb.)
  doğru bir şekilde yapılır.
- **Basit ve Karar Odaklı Arayüz:** Tüm girdiler kenar çubuğundadır. Ana ekran
  net sonuçları, tabloyu ve karar vermeyi kolaylaştıran interaktif bir
  grafiği sekmeler halinde sunar.
- **Tüm Alternatiflerin Analizi:** Mevzuata uygun tüm koasürans ve muafiyet
  kombinasyonları için prim, net tazminat ve sigortalıda kalan riski
  hesaplayarak karşılaştırma imkanı sunar.

Kullanım
--------
# Gerekli kütüphaneler:
# pip install streamlit pandas numpy plotly

# Uygulamayı çalıştırmak için:
streamlit run app.py
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple
import sys
import numpy as np
import pandas as pd

try:
    import streamlit as st
    import plotly.express as px
    STREAMLIT_AVAILABLE = True
except ImportError:
    st.error("Bu uygulama için gerekli kütüphaneler (streamlit, pandas, plotly) eksik. Lütfen `pip install streamlit pandas plotly` komutu ile yükleyin.")
    sys.exit(1)

# -------------------------------
# GÖRSEL/FORMAT YARDIMCILARI
# -------------------------------
fmt_money = lambda x: f"{x:,.0f}".replace(",", ".")

# -------------------------------
# TEMEL TARİFE VE HASAR VERİLERİ
# -------------------------------
DEPREM_BOLGESI_ORANLARI: Dict[int, Dict[str, float]] = {
    1: {"hafif": 0.07, "beklenen": 0.20, "agir": 0.45},
    2: {"hafif": 0.06, "beklenen": 0.17, "agir": 0.40},
    3: {"hafif": 0.05, "beklenen": 0.13, "agir": 0.32},
    4: {"hafif": 0.04, "beklenen": 0.09, "agir": 0.24},
    5: {"hafif": 0.03, "beklenen": 0.06, "agir": 0.15},
    6: {"hafif": 0.03, "beklenen": 0.06, "agir": 0.15},
    7: {"hafif": 0.03, "beklenen": 0.06, "agir": 0.15},
}
TARIFE_PD_BI: Dict[str, List[float]] = {
    "Betonarme": [3.13, 2.63, 2.38, 1.94, 1.38, 1.06, 0.75],
    "Diğer":     [6.13, 5.56, 3.75, 2.00, 1.56, 1.24, 1.06],
}
KOAS_FACTOR: Dict[str, float] = {
    "80/20": 1.00, "75/25": 1 - 0.0625, "70/30": 1 - 0.1250, "65/35": 1 - 0.1875,
    "60/40": 1 - 0.2500, "55/45": 1 - 0.3125, "50/50": 1 - 0.3750, "45/55": 1 - 0.4375,
    "40/60": 1 - 0.5000, "90/10": 1 + 0.1250, "100/0": 1 + 0.2500,
}
MUAFF_FACTOR: Dict[float, float] = {
    0.1: 1 + 0.12, 0.5: 1 + 0.09, 1.0: 1 + 0.06, 1.5: 1 + 0.03,
    2.0: 1.00, 3.0: 1 - 0.06, 4.0: 1 - 0.13, 5.0: 1 - 0.19, 10.0: 1 - 0.35,
}
CAP_PD_BI = 3_500_000_000

# -------------------------------
# HESAPLAMA MANTIĞI
# -------------------------------

@dataclass
class ScenarioInputs:
    si_pd: int = 250_000_000
    si_bi: int = 100_000_000
    rg: int = 3
    yapi_turu: str = "Betonarme"
    bina_yasi: str = "10-30 yaş"
    kat_sayisi: str = "4-7 kat"
    faaliyet: str = "İplik Fabrikası"
    guclendirme: str = "Yok"
    bi_gun_muafiyeti: int = 14

def calculate_damage_ratios(s: ScenarioInputs) -> Dict[str, float]:
    base_oranlar = DEPREM_BOLGESI_ORANLARI[s.rg]
    carpani = 1.0
    if s.yapi_turu == "Yığma": carpani *= 1.15
    elif s.yapi_turu == "Çelik": carpani *= 0.85
    if s.bina_yasi == "> 30 yaş": carpani *= 1.20
    elif s.bina_yasi == "< 10 yaş": carpani *= 0.90
    if s.kat_sayisi == "8+ kat": carpani *= 1.10
    elif s.kat_sayisi == "1-3 kat": carpani *= 0.95
    if "Depo" in s.faaliyet: carpani *= 1.15
    elif "Ofis" in s.faaliyet: carpani *= 0.90
    elif "Fabrika" in s.faaliyet or "Üretim" in s.faaliyet: carpani *= 1.05
    if s.guclendirme == "Var": carpani *= 0.85
    return {k: min(v * carpani, 0.70) for k, v in base_oranlar.items()}

def calculate_downtime_days(pd_damage_ratio: float) -> int:
    m = pd_damage_ratio * 100
    if m < 2: return 10
    if m < 5: return 30
    if m < 10: return 75
    if m < 20: return 135
    return 200

def calculate_premium(si: float, yapi_turu: str, rg: int, koas: str, muaf_pct: float) -> float:
    yapi_tarife = "Betonarme" if yapi_turu == "Çelik" else yapi_turu
    base_rate = TARIFE_PD_BI[yapi_tarife][rg-1]
    factor = KOAS_FACTOR[koas] * MUAFF_FACTOR[muaf_pct]
    prim_bedeli = min(si, CAP_PD_BI)
    return (prim_bedeli * base_rate / 1000.0) * factor

def calculate_pd_claim(si_pd: int, hasar_tutari: float, koas: str, muaf_pct: float) -> Dict[str, float]:
    muafiyet_tutari = si_pd * (muaf_pct / 100.0)
    muafiyet_sonrasi_hasar = max(0.0, hasar_tutari - muafiyet_tutari)
    sirket_pay_orani = float(koas.split('/')[0]) / 100.0
    net_tazminat = muafiyet_sonrasi_hasar * sirket_pay_orani
    sigortalida_kalan = hasar_tutari - net_tazminat
    return {"net_tazminat": net_tazminat, "sigortalida_kalan": sigortalida_kalan}

def calculate_bi_claim(si_bi: int, kesinti_gunu: int, bi_gun_muafiyeti: int) -> Dict[str, float]:
    gunluk_kar_kaybi = si_bi / 365.0
    odenecek_gun = max(0, kesinti_gunu - bi_gun_muafiyeti)
    hasar_tutari = odenecek_gun * gunluk_kar_kaybi
    # BI'da koasürans ve % muafiyet genellikle uygulanmaz, hasar direkt ödenir.
    return {"net_tazminat": hasar_tutari, "hasar_tutari": hasar_tutari}

def generate_ai_scenario(s: ScenarioInputs, pd_hasar_orani: float, bi_kesinti_gunu: int) -> str:
    scenario_text = f"**Deprem Hasar Uzmanı Raporu (Beklenen Senaryo)**\n\n"
    scenario_text += f"**Tesis:** {s.faaliyet} ({s.yapi_turu}, {s.bina_yasi})\n"
    scenario_text += f"**Konum:** {s.rg}. Derece Deprem Bölgesi\n\n"
    scenario_text += f"**Maddi Hasar (PD) Değerlendirmesi:**\n"
    scenario_text += f"Bölgede meydana gelen deprem, tesisin yapısal olmayan elemanlarında ve içerisindeki kıymetlerde **{pd_hasar_orani:.2%}** oranında bir hasar meydana getirmiştir. "

    if "Fabrika" in s.faaliyet or "Üretim" in s.faaliyet:
        scenario_text += "Özellikle üretim hattındaki **yüksek hassasiyetli makine ve teçhizatın bir kısmı devrilerek veya sarsıntıdan ötürü kalibrasyonları bozularak ağır hasar almıştır.** "
        if "İplik" in s.faaliyet:
            scenario_text += "Dokuma tezgahları ve iplik makinelerinin hassas elektronik bileşenleri zarar görmüştür. "
        scenario_text += "Ayrıca, depolanan hammadde ve mamul ürünlerin bir kısmı raflardan düşerek kullanılamaz hale gelmiştir."
    elif "Depo" in s.faaliyet:
        scenario_text += "Özellikle **yüksek istifleme yapılan raf sistemlerinde yaşanan çökme** nedeniyle stoklanan emtianın önemli bir bölümü zarar görmüştür. Forklift gibi mobil ekipmanlarda da hasar tespit edilmiştir."
    elif "Ofis" in s.faaliyet:
        scenario_text += "İç bölme duvarlarında, asma tavanlarda ve zemin kaplamalarında çatlaklar ve dökülmeler meydana gelmiştir. **Bilgisayarlar, sunucular ve diğer elektronik cihazlar** sarsıntı nedeniyle devrilerek hasarlanmıştır."
    else:
        scenario_text += "Tesis içerisindeki demirbaşlar, emtialar ve makine parkurunda çeşitli seviyelerde hasarlar gözlemlenmiştir."

    scenario_text += f"\n\n**İş Durması (BI) Değerlendirmesi:**\n"
    scenario_text += f"Meydana gelen maddi hasarlar ve artçı sarsıntı riskleri nedeniyle tesisin faaliyetleri durdurulmuştur. Yapılan ilk incelemelere göre, hasar tespiti, temizlik, onarım ve yeniden devreye alma süreçleri göz önüne alındığında, **üretimin yaklaşık {bi_kesinti_gunu} gün durması beklenmektedir.** Bu süre, kritik makinelerin yedek parça temin süreçlerine göre değişiklik gösterebilir."
    return scenario_text

def get_allowed_options(si_pd: int) -> Tuple[List[str], List[float]]:
    koas_base = ["80/20","75/25","70/30","65/35","60/40","55/45","50/50","45/55","40/60"]
    muaf_base = [2.0,3.0,4.0,5.0,10.0]
    if si_pd > 3_500_000_000:
        koas_ext = ["90/10","100/0"]
        muaf_ext = [0.1,0.5,1.0,1.5]
        return koas_base + koas_ext, muaf_base + muaf_ext
    return koas_base, muaf_base

# -------------------------------
# STREAMLIT ARAYÜZÜ
# -------------------------------
def run_app():
    st.set_page_config(page_title="AI Destekli Deprem Risk Analizi", page_icon=" Richter ölçeği", layout="wide")
    st.markdown("## 🏢 AI Destekli Ticari Deprem Risk ve Prim Analizi")

    # --- GİRDİ ALANI (KENAR ÇUBUĞU) ---
    with st.sidebar:
        st.image("https://i.imgur.com/mDKW3A2.png", width=250)
        st.header("1. Tesis Bilgilerini Girin")
        s_inputs = ScenarioInputs()
        s_inputs.faaliyet = st.text_input("Faaliyet Kolu (Örn: İplik Fabrikası, Lojistik Depo)", "İplik Fabrikası")
        s_inputs.si_pd = st.number_input("Maddi Hasar (PD) Sigorta Bedeli (TRY)", min_value=1_000_000, value=250_000_000, step=1_000_000)
        s_inputs.si_bi = st.number_input("Yıllık Kar Kaybı (BI) Bedeli (TRY)", min_value=0, value=100_000_000, step=1_000_000)
        s_inputs.rg = st.select_slider("Deprem Risk Bölgesi", options=[1,2,3,4,5,6,7], value=3)
        s_inputs.yapi_turu = st.selectbox("Yapı Türü", ["Betonarme", "Çelik", "Yığma", "Diğer"])
        s_inputs.bina_yasi = st.selectbox("Bina Yaşı", ["< 10 yaş", "10-30 yaş", "> 30 yaş"], index=1)
        s_inputs.kat_sayisi = st.selectbox("Kat Sayısı", ["1-3 kat", "4-7 kat", "8+ kat"], index=1)
        s_inputs.guclendirme = st.radio("Güçlendirme Yapıldı mı?", ["Yok", "Var"], index=0, horizontal=True)
        s_inputs.bi_gun_muafiyeti = st.number_input("Kar Kaybı Bekleme Süresi (Gün)", min_value=0, value=14, step=1)

    # --- HESAPLAMALAR ---
    damage_ratios = calculate_damage_ratios(s_inputs)
    beklenen_pd_hasar_orani = damage_ratios["beklenen"]
    pd_hasar_tutari = s_inputs.si_pd * beklenen_pd_hasar_orani
    
    beklenen_bi_kesinti_gunu = calculate_downtime_days(beklenen_pd_hasar_orani)
    bi_sonuclari = calculate_bi_claim(s_inputs.si_bi, beklenen_bi_kesinti_gunu, s_inputs.bi_gun_muafiyeti)
    bi_hasar_tutari = bi_sonuclari["hasar_tutari"]
    net_bi_tazminat = bi_sonuclari["net_tazminat"]

    # --- ANA EKRAN ---
    st.header("2. Analiz Sonuçları")

    # AI Hasar Senaryosu
    with st.container(border=True):
        ai_scenario = generate_ai_scenario(s_inputs, beklenen_pd_hasar_orani, beklenen_bi_kesinti_gunu)
        st.markdown(ai_scenario)

    # Beklenen Hasar Metrikleri
    st.subheader("Beklenen Hasar Senaryosu Sonuçları")
    col1, col2, col3 = st.columns(3)
    col1.metric("Maddi Hasar (PD) Tutarı", f"{fmt_money(pd_hasar_tutari)} TRY", f"{beklenen_pd_hasar_orani:.2%} Oranında")
    col2.metric("İş Durması (BI) Süresi", f"{beklenen_bi_kesinti_gunu} Gün", "Tahmini")
    col3.metric("İş Durması (BI) Hasar Tutarı", f"{fmt_money(bi_hasar_tutari)} TRY", f"{s_inputs.bi_gun_muafiyeti} gün muafiyet sonrası")

    st.markdown("---")
    st.header("3. Poliçe Alternatifleri ve Optimizasyon")

    # Tüm alternatifleri hesapla
    koas_opts, muaf_opts = get_allowed_options(s_inputs.si_pd)
    results = []
    for koas in koas_opts:
        for muaf in muaf_opts:
            prim_pd = calculate_premium(s_inputs.si_pd, s_inputs.yapi_turu, s_inputs.rg, koas, muaf)
            prim_bi = calculate_premium(s_inputs.si_bi, s_inputs.yapi_turu, s_inputs.rg, "80/20", 2.0) # BI primi standarttır
            toplam_prim = prim_pd + prim_bi
            
            pd_claim_res = calculate_pd_claim(s_inputs.si_pd, pd_hasar_tutari, koas, muaf)
            net_pd_tazminat = pd_claim_res["net_tazminat"]
            
            toplam_net_tazminat = net_pd_tazminat + net_bi_tazminat
            toplam_hasar = pd_hasar_tutari + bi_hasar_tutari
            sigortalida_kalan_risk = toplam_hasar - toplam_net_tazminat
            
            results.append({
                "Poliçe Yapısı": f"{koas} Koas. / {muaf}% Muaf.",
                "Yıllık Toplam Prim": toplam_prim,
                "Net PD Tazminatı": net_pd_tazminat,
                "Net BI Tazminatı": net_bi_tazminat,
                "Toplam Net Tazminat": toplam_net_tazminat,
                "Hasarda Şirketinizde Kalan Risk": sigortalida_kalan_risk
            })
    df = pd.DataFrame(results)

    # Sonuçları Sekmelerde Göster
    tab1, tab2 = st.tabs(["📊 Tablo Analizi", "📈 Görsel Analiz"])

    with tab1:
        st.markdown("Aşağıdaki tabloda tüm olası poliçe yapıları için prim ve hasar sonrası net durumunuzu karşılaştırabilirsiniz. En düşük **Toplam Prim** ve en düşük **Şirketinizde Kalan Risk** değerlerini bularak sizin için en verimli seçeneği belirleyebilirsiniz.")
        st.dataframe(
            df.sort_values("Yıllık Toplam Prim").style.format({
                "Yıllık Toplam Prim": "{:,.0f} TRY",
                "Net PD Tazminatı": "{:,.0f} TRY",
                "Net BI Tazminatı": "{:,.0f} TRY",
                "Toplam Net Tazminat": "{:,.0f} TRY",
                "Hasarda Şirketinizde Kalan Risk": "{:,.0f} TRY",
            }),
            use_container_width=True,
            height=500
        )

    with tab2:
        st.markdown("Bu grafik, en verimli poliçe alternatifini bulmanıza yardımcı olur. **Amacınız, sol alt köşeye en yakın noktayı bulmaktır.** Bu noktalar, hem **düşük prim** ödeyeceğiniz hem de hasar anında **şirketinizde en az riskin kalacağı** en verimli seçenekleri temsil eder.")
        fig = px.scatter(
            df,
            x="Yıllık Toplam Prim",
            y="Hasarda Şirketinizde Kalan Risk",
            color="Yıllık Toplam Prim",
            color_continuous_scale=px.colors.sequential.Tealgrn,
            hover_data=["Poliçe Yapısı", "Toplam Net Tazminat"],
            title="Poliçe Alternatifleri Optimizasyon Grafiği"
        )
        fig.update_traces(marker=dict(size=12, line=dict(width=1, color='DarkSlateGrey')), selector=dict(mode='markers'))
        fig.update_layout(
            xaxis_title="Ödenecek Yıllık Prim (Ne kadar düşükse o kadar iyi)",
            yaxis_title="Hasarda Şirketinizde Kalacak Risk (Ne kadar düşükse o kadar iyi)"
        )
        st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    run_app()
