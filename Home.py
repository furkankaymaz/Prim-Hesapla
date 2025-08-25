# -*- coding: utf-8 -*-
"""
TariffEQ – Ticari & Sınai Deprem: İnteraktif Prim & Limit Optimizasyon + AI Rapor (Tek Dosya)
==============================================================================================

• Esasları:
  - Tüm koasürans ve muafiyet kombinasyonları için PD (ve opsiyonel BI) net tazminat ve kalan risk hesaplanır.
  - Optimizasyon hedefi seçilebilir (Kalan Risk Min / Dengeli / Net Ödeme Max).
  - Görselleştirme: Scatter (Prim vs Net Ödeme) + Isı Haritası (Kalan Risk matrisi).
  - Limit kaydırıcısı ile anlık PD ödeme/kalan etkisi.
  - AI (Gemini) varsa parametreleri özetleyen rapor üretir; yoksa otomatik statik metne düşer.

• Çalıştırma:
  pip install streamlit pandas numpy plotly
  streamlit run home.py

• Hugging Face Spaces:
  README.md başına aşağıdaki YAML:
  ---
  sdk: streamlit
  app_file: home.py
  ---

• AI:
  - Ortam değişkeni GEMINI_API_KEY tanımlanırsa AI kullanılmaya çalışılır.
  - Sağ panelden "API Key (opsiyonel)" girişi ile de anahtar verilebilir.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple
import os, sys, numpy as np, pandas as pd

# Görsel/format yardımcıları
fmt_money = lambda x: f"{x:,.0f}".replace(",", ".")

# -------------------------------
# Opsiyonel AI (Gemini) entegrasyonu – güvenli koruma
# -------------------------------
_GEMINI_AVAILABLE = False
try:
    # Yeni SDK (google-genai)
    from google import genai as _genai_new          # type: ignore
    from google.genai import types as _genai_types  # type: ignore
    _GEMINI_AVAILABLE = True
except Exception:
    try:
        # Eski SDK (google-generativeai)
        import google.generativeai as _genai_old    # type: ignore
        _GENAI_OLD = True
        _GEMINI_AVAILABLE = True
    except Exception:
        _GEMINI_AVAILABLE = False

# -------------------------------
# Streamlit & Plotly
# -------------------------------
try:
    import streamlit as st
    import plotly.express as px
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

# -------------------------------
# TEMEL TARİFE & HASAR MODELİ
# -------------------------------
# Risk Bölgelerine göre temel PD hasar oranları
DEPREM_BOLGESI_ORANLARI: Dict[int, Dict[str, float]] = {
    1: {"hafif": 0.07, "beklenen": 0.20, "agir": 0.45},
    2: {"hafif": 0.06, "beklenen": 0.17, "agir": 0.40},
    3: {"hafif": 0.05, "beklenen": 0.13, "agir": 0.32},
    4: {"hafif": 0.04, "beklenen": 0.09, "agir": 0.24},
    5: {"hafif": 0.03, "beklenen": 0.06, "agir": 0.15},
    6: {"hafif": 0.03, "beklenen": 0.06, "agir": 0.15},
    7: {"hafif": 0.03, "beklenen": 0.06, "agir": 0.15},
}

# Tarife Oranları (Tablo-2) – ‰ (binde)
TARIFE_PD: Dict[str, List[float]] = {
    "Betonarme": [3.13, 2.63, 2.38, 1.94, 1.38, 1.06, 0.75],
    "Diğer":     [6.13, 5.56, 3.75, 2.00, 1.56, 1.24, 1.06],
}

# Koasürans & Muafiyet faktörleri (eski kodla uyumlu)
KOAS_FACTOR: Dict[str, float] = {
    "80/20": 1.00, "75/25": 1 - 0.0625, "70/30": 1 - 0.1250, "65/35": 1 - 0.1875,
    "60/40": 1 - 0.2500, "55/45": 1 - 0.3125, "50/50": 1 - 0.3750, "45/55": 1 - 0.4375,
    "40/60": 1 - 0.5000, "90/10": 1 + 0.1250, "100/0": 1 + 0.2500,
}
MUAFF_FACTOR: Dict[float, float] = {
    0.1: 1 + 0.12, 0.5: 1 + 0.09, 1.0: 1 + 0.06, 1.5: 1 + 0.03,
    2.0: 1.00, 3.0: 1 - 0.06, 4.0: 1 - 0.13, 5.0: 1 - 0.19, 10.0: 1 - 0.35,
}

CAP_PD = 3_500_000_000  # TRY üstü için farklı kombinasyonlar devreye girer

# -------------------------------
# Yardımcı fonksiyonlar
# -------------------------------
def insurer_share_from_koas(koas: str) -> float:
    left, _ = koas.split("/")
    return float(left) / 100.0

def allowed_sets(pd_total_try: float) -> Tuple[List[str], List[float]]:
    base_koas = ["80/20","75/25","70/30","65/35","60/40","55/45","50/50","45/55","40/60"]
    ext_koas  = ["90/10","100/0"]
    base_muaf = [2.0,3.0,4.0,5.0,10.0]
    ext_muaf  = [0.1,0.5,1.0,1.5]
    if pd_total_try <= CAP_PD:
        return base_koas, base_muaf
    return base_koas + ext_koas, base_muaf + ext_muaf

def calculate_damage_ratios(
    bolge: int, yapi_tipi: str, bina_yasi: str, kat_sayisi: str, faaliyet: str, guclendirme: str
) -> Dict[str, float]:
    """
    Eski modelle uyumlu; bina özelliklerine göre PD oranlarını modifiye eder.
    Maksimum %70 sınırlaması ile döner.
    """
    base = DEPREM_BOLGESI_ORANLARI.get(bolge, DEPREM_BOLGESI_ORANLARI[1]).copy()
    carpani = 1.0

    # Yapı Tipi
    if yapi_tipi == "Yığma": carpani *= 1.15
    elif yapi_tipi == "Çelik": carpani *= 0.85
    elif yapi_tipi == "Diğer": carpani *= 1.05

    # Bina Yaşı
    if bina_yasi == "> 30 yaş": carpani *= 1.20
    elif bina_yasi == "< 10 yaş": carpani *= 0.90
    elif bina_yasi == "10-30 yaş": carpani *= 1.05

    # Kat
    if kat_sayisi == "8+ kat": carpani *= 1.10
    elif kat_sayisi == "1-3 kat": carpani *= 0.95

    # Faaliyet
    if faaliyet == "Depolama": carpani *= 1.15
    elif faaliyet == "Ofis": carpani *= 0.90
    elif faaliyet == "Üretim": carpani *= 1.05

    # Güçlendirme
    if guclendirme == "Var": carpani *= 0.85

    return {k: min(round(v * carpani, 4), 0.70) for k, v in base.items()}

def premium_pd(si_pd: float, yapi_turu: str, rg: int, enfl: float, koas: str, muaf_pct: float) -> float:
    # Tarife tablosu: Çelik için Betonarme ile hizalı kullanılmıştı
    yapi_tarife = "Betonarme" if yapi_turu == "Çelik" else yapi_turu
    base_rate_prmille = TARIFE_PD.get(yapi_tarife, TARIFE_PD["Diğer"])[rg-1]
    base_rate_prmille *= (1.0 + (enfl/100.0)/2.0)  # enflasyon etkisi
    factor = KOAS_FACTOR[koas] * MUAFF_FACTOR[muaf_pct]
    matrah = min(si_pd, CAP_PD)
    prim = (matrah * base_rate_prmille / 1000.0) * factor
    return prim

def pd_claim(si_pd: float, limit_pd: float, damage_ratio: float, muaf_pct: float, insurer_share: float) -> Dict[str, float]:
    brut = si_pd * damage_ratio
    muaf = si_pd * (muaf_pct / 100.0)
    muaf_sonrasi = max(0.0, brut - muaf)
    sirket_payi = muaf_sonrasi * insurer_share
    odeme = min(sirket_payi, limit_pd)
    kalan = brut - odeme
    return {"brut_hasar": brut, "odenecek_tazminat": odeme, "sigortali_payi": kalan}

# --- BI (opsiyonel) ---
def estimate_bi_days_from_pd_ratio(pd_ratio: float, severity: str, yapi_turu: str) -> int:
    # Basit heuristik: hafif/beklenen/ağır için 20/60/120 gün * yapı çarpanı
    base = {"hafif": 20, "beklenen": 60, "agir": 120}[severity]
    yapi = {"Betonarme":1.0, "Çelik":0.9, "Diğer":1.05, "Yığma":1.15}[yapi_turu]
    days = int(round(base * (0.6 + 0.8 * pd_ratio) * yapi))
    return max(0, min(365, days))

def bi_claim(si_bi: float, bi_days: int, time_deductible: int) -> Dict[str, float]:
    net_days = max(0, bi_days - time_deductible)
    gunluk = si_bi / 365.0
    tutar = gunluk * net_days
    return {"net_tazminat": tutar, "net_gun": net_days}

# -------------------------------
# SENARYO & IZGARA HESABI
# -------------------------------
@dataclass
class ScenarioInputs:
    si_pd: int = 250_000_000
    si_bi: int = 100_000_000
    rg: int = 3
    yapi_turu: str = "Betonarme"
    bina_yasi: str = "10-30 yaş"
    kat_sayisi: str = "4-7 kat"
    faaliyet: str = "Üretim"
    guclendirme: str = "Yok"
    enfl: float = 0.0
    bi_wait_days: int = 14
    include_bi: bool = True

def compute_all_alternatives(s: ScenarioInputs) -> Tuple[pd.DataFrame, Dict[str, float], Dict[str, int], Dict[str, float]]:
    dr = calculate_damage_ratios(s.rg, s.yapi_turu, s.bina_yasi, s.kat_sayisi, s.faaliyet, s.guclendirme)
    koas_opts, muaf_opts = allowed_sets(s.si_pd)

    # BI tahmin günleri ve tutarları (koasüranstan bağımsız)
    bi_days = {
        "hafif": estimate_bi_days_from_pd_ratio(dr["hafif"], "hafif", s.yapi_turu),
        "beklenen": estimate_bi_days_from_pd_ratio(dr["beklenen"], "beklenen", s.yapi_turu),
        "agir": estimate_bi_days_from_pd_ratio(dr["agir"], "agir", s.yapi_turu),
    }
    bi_amounts = {
        k: bi_claim(s.si_bi, v, s.bi_wait_days)["net_tazminat"] if s.include_bi and s.si_bi > 0 else 0.0
        for k, v in bi_days.items()
    }

    rows = []
    for koas in koas_opts:
        insurer_share = insurer_share_from_koas(koas)
        for muaf in muaf_opts:
            prim = premium_pd(s.si_pd, s.yapi_turu, s.rg, s.enfl, koas, muaf)

            # PD claim – limit = SI (referans ızgara)
            claim_h = pd_claim(s.si_pd, s.si_pd, dr["hafif"], muaf, insurer_share)
            claim_b = pd_claim(s.si_pd, s.si_pd, dr["beklenen"], muaf, insurer_share)
            claim_a = pd_claim(s.si_pd, s.si_pd, dr["agir"], muaf, insurer_share)

            # Toplam net ödeme (PD + opsiyonel BI)
            tot_h = claim_h["odenecek_tazminat"] + bi_amounts["hafif"]
            tot_b = claim_b["odenecek_tazminat"] + bi_amounts["beklenen"]
            tot_a = claim_a["odenecek_tazminat"] + bi_amounts["agir"]

            # Kalan risk (brüt PD + opsiyonel BI brüt - toplam net ödeme)
            # BI brüt ~ net ile eşit kabul edildi (koasürans yok); hassasiyet gerekiyorsa ayrıca verilebilir.
            kalan_h = (claim_h["brut_hasar"] + bi_amounts["hafif"]) - tot_h
            kalan_b = (claim_b["brut_hasar"] + bi_amounts["beklenen"]) - tot_b
            kalan_a = (claim_a["brut_hasar"] + bi_amounts["agir"]) - tot_a

            rows.append({
                "Koasürans": koas, "PD Muafiyet %": muaf, "Toplam Prim": prim,
                "Hafif Net Ödeme": tot_h, "Beklenen Net Ödeme": tot_b, "Ağır Net Ödeme": tot_a,
                "Hafif Kalan Risk": kalan_h, "Beklenen Kalan Risk": kalan_b, "Ağır Kalan Risk": kalan_a,
                "Hafif PD Brüt": claim_h["brut_hasar"], "Beklenen PD Brüt": claim_b["brut_hasar"], "Ağır PD Brüt": claim_a["brut_hasar"],
            })
    df = pd.DataFrame(rows)
    return df, dr, bi_days, bi_amounts

# -------------------------------
# AI raporlayıcı
# -------------------------------
def ai_report(s: ScenarioInputs, dr: Dict[str, float], bi_days: Dict[str, int], best_row: pd.Series, api_key: str | None) -> str:
    # Geminide başarısızlık veya anahtar yoksa statik rapor döner
    pd_pct = round(dr["beklenen"] * 100, 1)
    if not (api_key and _GEMINI_AVAILABLE):
        return (
            f"**Deprem Hasar Değerlendirmesi (Özet)**\n\n"
            f"- Bölge: {s.rg} | Yapı: {s.yapi_turu}, {s.bina_yasi}, {s.kat_sayisi} | Faaliyet: {s.faaliyet} | Güçlendirme: {s.guclendirme}\n"
            f"- Beklenen PD oranı: **%{pd_pct}** | Tahmini BI kesinti: **{bi_days['beklenen']} gün** (muafiyet: {s.bi_wait_days} gün)\n"
            f"- Önerilen yapı: **Koasürans {best_row['Koasürans']} / Muafiyet %{best_row['PD Muafiyet %']}**\n"
            f"- Gerekçe: Kalan riskin düşüklüğü ve makul prim dengesi.\n\n"
            f"_Not: AI anahtarı bulunamadı; statik rapor gösterilmektedir._"
        )

    prompt = f"""
Sen bir endüstriyel deprem sigortası uzmanısın. Aşağıdaki girdilere göre kısa, teknik ve net bir değerlendirme yaz.
- Bölge: {s.rg}, Yapı: {s.yapi_turu}, Yaş: {s.bina_yasi}, Kat: {s.kat_sayisi}, Faaliyet: {s.faaliyet}, Güçlendirme: {s.guclendirme}
- PD Oranları: Hafif %{round(dr['hafif']*100,1)}, Beklenen %{round(dr['beklenen']*100,1)}, Ağır %{round(dr['agir']*100,1)}
- BI (Beklenen) Gün: {bi_days['beklenen']}, BI Muafiyet: {s.bi_wait_days} gün
- Önerilen: Koasürans {best_row['Koasürans']} / Muafiyet %{best_row['PD Muafiyet %']}
- Gerekçe: Kalan risk minimizasyonu ve prim dengesi
Çıktıyı madde işaretli, yalın teknik Türkçe ile ver.
"""
    try:
        if 'genai' in globals() and isinstance(globals().get('_genai_new'), object):
            client = _genai_new.Client(api_key=api_key)
            content = client.models.generate_content(
                model="gemini-1.5-pro",
                contents=_genai_types.Content(role="user", parts=[_genai_types.Part.from_text(prompt)])
            )
            return getattr(content, "text", None) or "AI yanıtı alınamadı; statik rapora düşünüz."
        # Eski SDK
        _genai_old.configure(api_key=api_key)
        model = _genai_old.GenerativeModel("gemini-1.5-pro")
        resp = model.generate_content(prompt)
        return getattr(resp, "text", None) or "AI yanıtı alınamadı; statik rapora düşünüz."
    except Exception:
        return "AI çağrısı başarısız oldu; statik rapora geçiniz."

# -------------------------------
# UI – Streamlit
# -------------------------------
def run_streamlit_app():
    st.set_page_config(page_title="TariffEQ – Deprem Optimizasyon + AI", page_icon="📈", layout="wide")
    st.markdown("## 📈 Ticari & Sınai Deprem – Prim & Limit Optimizasyonu + AI Rapor")
    st.caption("Koasürans–muafiyet ızgarası üzerinden PD (ve opsiyonel BI) analizini yapın, en iyi yapıyı seçin, isterseniz AI yorumuyla raporlayın.")

    # Sağ panel: Girdiler / AI / Hedef
    st.sidebar.header("1) Senaryo Girdileri")
    s_inputs = ScenarioInputs()
    s_inputs.si_pd = st.sidebar.number_input("Maddi Hasar (PD) Sigorta Bedeli (TRY)", min_value=1_000_000, value=250_000_000, step=1_000_000)
    s_inputs.si_bi = st.sidebar.number_input("Kar Kaybı (BI) Sigorta Bedeli (TRY)", min_value=0, value=100_000_000, step=1_000_000)
    s_inputs.include_bi = st.sidebar.checkbox("BI dahil", value=True)
    s_inputs.bi_wait_days = st.sidebar.number_input("BI Bekleme (gün)", min_value=0, value=14, step=1)
    s_inputs.rg = st.sidebar.select_slider("Deprem Risk Grubu", options=[1,2,3,4,5,6,7], value=3)
    s_inputs.yapi_turu = st.sidebar.selectbox("Yapı Türü", ["Betonarme", "Çelik", "Yığma", "Diğer"])
    s_inputs.bina_yasi = st.sidebar.selectbox("Bina Yaşı", ["< 10 yaş", "10-30 yaş", "> 30 yaş"], index=1)
    s_inputs.kat_sayisi = st.sidebar.selectbox("Kat Sayısı", ["1-3 kat", "4-7 kat", "8+ kat"], index=1)
    s_inputs.faaliyet = st.sidebar.selectbox("Faaliyet Türü", ["Üretim", "Depolama", "Perakende", "Ofis"], index=0)
    s_inputs.guclendirme = st.sidebar.radio("Güçlendirme", ["Yok", "Var"], index=0, horizontal=True)
    s_inputs.enfl = st.sidebar.slider("Enflasyon (%) – Tarife Artışı", min_value=0, max_value=100, value=0)

    st.sidebar.markdown("---")
    st.sidebar.header("2) Optimizasyon Hedefi")
    objective = st.sidebar.radio(
        "Hedef seçiniz",
        ["Kalan Risk Min", "Dengeli Skor", "Net Ödeme Max"],
        index=0
    )
    if objective == "Dengeli Skor":
        w_risk = st.sidebar.slider("Ağırlık: Kalan Risk (↓ iyi)", 0.0, 1.0, 0.6, 0.05)
        w_muaf = st.sidebar.slider("Ağırlık: Muafiyet Düşüklüğü (↓ iyi)", 0.0, 1.0, 0.2, 0.05)
        w_share = st.sidebar.slider("Ağırlık: Sigortacı Payı Yüksekliği (↑ iyi)", 0.0, 1.0, 0.2, 0.05)
    else:
        w_risk, w_muaf, w_share = 1.0, 0.0, 0.0

    st.sidebar.markdown("---")
    st.sidebar.header("3) AI (opsiyonel)")
    env_key = os.environ.get("GEMINI_API_KEY")
    ui_key = st.sidebar.text_input("API Key (opsiyonel)", value="", type="password")
    use_key = ui_key.strip() or env_key or None
    if use_key and _GEMINI_AVAILABLE:
        st.sidebar.success("AI kullanılabilir.")
    elif use_key and not _GEMINI_AVAILABLE:
        st.sidebar.warning("Anahtar var ama AI kitaplığı kurulu değil. (google-genai / google-generativeai)")
    else:
        st.sidebar.info("AI anahtarı yok; statik rapor kullanılacak.")

    # Hesapla
    df, dr, bi_days, bi_amounts = compute_all_alternatives(s_inputs)

    # Üst metrikler – PD brüt hasar (3 senaryo) ve BI günleri
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Hafif PD Oranı", f"{dr['hafif']:.2%}", f"Brüt: {fmt_money(s_inputs.si_pd * dr['hafif'])}")
    col2.metric("Beklenen PD Oranı", f"{dr['beklenen']:.2%}", f"Brüt: {fmt_money(s_inputs.si_pd * dr['beklenen'])}")
    col3.metric("Ağır PD Oranı", f"{dr['agir']:.2%}", f"Brüt: {fmt_money(s_inputs.si_pd * dr['agir'])}")
    if s_inputs.include_bi:
        col4.metric("Beklenen BI Gün", f"{bi_days['beklenen']} gün", f"Muafiyet: {s_inputs.bi_wait_days} gün")

    st.markdown("---")

    # Sekmeler: Optimizasyon | Görselleştirme | Tüm Alternatifler | AI Rapor
    tab_opt, tab_vis, tab_table, tab_ai = st.tabs(["🔎 Optimizasyon", "📊 Görselleştirme", "📋 Tüm Alternatifler", "🤖 AI Rapor"])

    # --- OPTİMİZASYON ---
    with tab_opt:
        scenario_col = st.selectbox(
            "Hangi senaryoya göre optimize edelim?",
            options=["Beklenen", "Ağır", "Hafif"],
            index=0
        )
        # Hedef değişkenler
        if scenario_col == "Beklenen":
            target_net = "Beklenen Net Ödeme"; target_left = "Beklenen Kalan Risk"
        elif scenario_col == "Ağır":
            target_net = "Ağır Net Ödeme"; target_left = "Ağır Kalan Risk"
        else:
            target_net = "Hafif Net Ödeme"; target_left = "Hafif Kalan Risk"

        df_eval = df.copy()
        # Dengeli skor için normalizasyon
        if objective == "Dengeli Skor":
            # daha düşük kalan risk iyi -> min-max terslenmiş skor
            rk = df_eval[target_left].values
            rk_norm = (rk - rk.min()) / (rk.max() - rk.min() + 1e-9)
            rk_score = 1.0 - rk_norm

            muaf = df_eval["PD Muafiyet %"].values
            muaf_norm = (muaf - muaf.min()) / (muaf.max() - muaf.min() + 1e-9)
            muaf_score = 1.0 - muaf_norm

            share = df_eval["Koasürans"].apply(lambda s: insurer_share_from_koas(s)).values
            share_norm = (share - share.min()) / (share.max() - share.min() + 1e-9)

            df_eval["Skor"] = w_risk * rk_score + w_muaf * muaf_score + w_share * share_norm
            best = df_eval.sort_values("Skor", ascending=False).head(1).iloc[0]
        elif objective == "Net Ödeme Max":
            best = df_eval.sort_values(target_net, ascending=False).head(1).iloc[0]
        else:  # Kalan Risk Min
            best = df_eval.sort_values(target_left, ascending=True).head(1).iloc[0]

        st.success(
            f"**Önerilen Yapı:** Koasürans `{best['Koasürans']}`, Muafiyet `%{best['PD Muafiyet %']}`  |  "
            f"Prim: **{fmt_money(best['Toplam Prim'])}**  |  "
            f"{scenario_col} Net Ödeme: **{fmt_money(best[target_net])}**  |  "
            f"{scenario_col} Kalan Risk: **{fmt_money(best[target_left])}**"
        )

        # Limit kaydırıcısı – referans olarak önerilen yapıyla gösterim
        st.subheader("İnteraktif PD Limit Analizi (Önerilen Yapıya Göre)")
        insurer_share = insurer_share_from_koas(best["Koasürans"])
        muaf = float(best["PD Muafiyet %"])
        max_limit = int(s_inputs.si_pd * 1.05)
        default_limit = int(s_inputs.si_pd * dr["beklenen"])
        selected_limit = st.slider("PD Limit (TRY)", min_value=0, max_value=max_limit, value=default_limit, step=int(max_limit/200))

        cl_h = pd_claim(s_inputs.si_pd, selected_limit, dr["hafif"], muaf, insurer_share)
        cl_b = pd_claim(s_inputs.si_pd, selected_limit, dr["beklenen"], muaf, insurer_share)
        cl_a = pd_claim(s_inputs.si_pd, selected_limit, dr["agir"], muaf, insurer_share)
        c1, c2, c3 = st.columns(3)
        c1.metric("Hafif – PD Net Ödeme", fmt_money(cl_h["odenecek_tazminat"]), f"Kalan: {fmt_money(cl_h['sigortali_payi'])}")
        c2.metric("Beklenen – PD Net Ödeme", fmt_money(cl_b["odenecek_tazminat"]), f"Kalan: {fmt_money(cl_b['sigortali_payi'])}")
        c3.metric("Ağır – PD Net Ödeme", fmt_money(cl_a["odenecek_tazminat"]), f"Kalan: {fmt_money(cl_a['sigortali_payi'])}")

    # --- GÖRSELLEŞTİRME ---
    with tab_vis:
        st.subheader("Prim – Net Ödeme Alanı (Scatter)")
        which_net = st.selectbox(
            "Grafikteki Net Ödeme:", ["Beklenen Net Ödeme", "Ağır Net Ödeme", "Hafif Net Ödeme"], index=0
        )
        fig = px.scatter(
            df, x="Toplam Prim", y=which_net, color="Koasürans",
            size=df["PD Muafiyet %"].pow(1.4),
            hover_data=["Koasürans", "PD Muafiyet %"],
            labels={"Toplam Prim": "Toplam Prim (TRY)", which_net: "Net Ödeme (TRY)"},
            title=f"Prim vs {which_net}"
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Isı Haritası – Kalan Risk Matrisi")
        which_left = st.selectbox(
            "Isı haritasında:", ["Beklenen Kalan Risk", "Ağır Kalan Risk", "Hafif Kalan Risk"], index=0
        )
        pivot = df.pivot_table(index="PD Muafiyet %", columns="Koasürans", values=which_left, aggfunc="mean")
        heat = px.imshow(
            pivot.sort_index(ascending=True),
            aspect="auto", origin="lower",
            labels=dict(x="Koasürans", y="Muafiyet %", color="Kalan Risk (TRY)"),
            title=f"{which_left} – Isı Haritası"
        )
        st.plotly_chart(heat, use_container_width=True)

    # --- TABLO ---
    with tab_table:
        st.subheader("Tüm Alternatifler")
        st.dataframe(
            df.sort_values(["Toplam Prim","Beklenen Kalan Risk"]).style.format({
                "Toplam Prim": "{:,.0f}",
                "Hafif Net Ödeme": "{:,.0f}", "Beklenen Net Ödeme": "{:,.0f}", "Ağır Net Ödeme": "{:,.0f}",
                "Hafif Kalan Risk": "{:,.0f}", "Beklenen Kalan Risk": "{:,.0f}", "Ağır Kalan Risk": "{:,.0f}",
                "Hafif PD Brüt": "{:,.0f}", "Beklenen PD Brüt": "{:,.0f}", "Ağır PD Brüt": "{:,.0f}",
            }),
            use_container_width=True, height=520
        )

    # --- AI RAPOR ---
    with tab_ai:
        st.subheader("AI Senaryo Raporu")
        # Optimizasyon sekmesinde seçilenle tutarlı bir "en iyi"yi tekrar hesapla (varsayılan: Beklenen/Kalan Risk Min)
        df_eval = df.copy()
        df_eval = df_eval.sort_values("Beklenen Kalan Risk", ascending=True)
        best = df_eval.iloc[0]
        report = ai_report(s_inputs, dr, bi_days, best, use_key)
        st.markdown(report)

# -------------------------------
# GİRİŞ
# -------------------------------
if __name__ == "__main__":
    if not STREAMLIT_AVAILABLE:
        print("Bu uygulama için Streamlit gereklidir. Lütfen `pip install streamlit pandas numpy plotly` yükleyip tekrar deneyin.")
        sys.exit(1)
    run_streamlit_app()
