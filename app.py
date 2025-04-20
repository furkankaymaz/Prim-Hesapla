import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# ================================================================
# FX UTILITIES – otomatik kur çekme (exchangerate.host  → TCMB)
# ================================================================
@st.cache_data(ttl=60 * 30)  # 30 dakikada bir yenile
def fetch_fx(currency: str):
    """Returns (rate, source, date_iso) or (None, None, None)"""
    # --- 1) exchangerate.host -------------------------------------------------
    try:
        url = f"https://api.exchangerate.host/latest?base={currency}&symbols=TRY"
        r = requests.get(url, timeout=4)
        if r.ok and r.json().get("success"):
            rate = r.json()["rates"]["TRY"]
            date_iso = r.json()["date"]  # yyyy-mm-dd
            return rate, "exchangerate.host", date_iso
    except Exception:
        pass

    # --- 2) TCMB fallback -----------------------------------------------------
    try:
        r = requests.get("https://www.tcmb.gov.tr/kurlar/today.xml", timeout=4)
        root = ET.fromstring(r.content)
        for cur in root.findall("Currency"):
            if cur.attrib.get("CurrencyCode") == currency:
                text = (cur.findtext("BanknoteSelling") or cur.findtext("ForexSelling")).replace(",", ".")
                rate = float(text)
                date_iso = root.attrib.get("Date")  # g.g.yyyy
                date_iso = datetime.strptime(date_iso, "%d.%m.%Y").strftime("%Y-%m-%d")
                return rate, "TCMB", date_iso
    except Exception:
        pass

    return None, None, None


def fx_input(para_birimi: str, key_prefix: str = "fx") -> float:
    """Para birimi TRY değilse otomatik kuru getirir, kullanıcıya manuel güncelle opsiyonu tanır."""
    if para_birimi == "TRY":
        return 1.0

    rate_key = f"{key_prefix}_{para_birimi}_rate"
    src_key = f"{key_prefix}_{para_birimi}_src"
    dt_key = f"{key_prefix}_{para_birimi}_dt"

    if rate_key not in st.session_state:
        rate, src, dt = fetch_fx(para_birimi)
        if rate:
            st.session_state[rate_key] = rate
            st.session_state[src_key] = src
            st.session_state[dt_key] = dt
        else:
            # fallback manuel başlangıç
            st.session_state[rate_key] = 30.0
            st.session_state[src_key] = "MANUEL"
            st.session_state[dt_key] = "-"

    st.info(
        f"1 {para_birimi} = {st.session_state[rate_key]:,.4f} TL "
        f"({st.session_state[src_key]}, {st.session_state[dt_key]})"
    )

    return st.number_input(
        "Kuru manuel güncelleyebilirsiniz",
        value=float(st.session_state[rate_key]),
        step=0.01,
        key=f"{key_prefix}_kur_input",
    )

# ================================================================
# TARİFE SABİT TABLOLARI
# ================================================================

# Tarife oran tablosu (Deprem Bölgesi x Bina Tipi)
tarife_oranlari = {
    "Betonarme": [3.13, 2.63, 2.38, 1.94, 1.38, 1.06, 0.75],
    "Diğer": [6.13, 5.56, 3.75, 2.00, 1.56, 1.24, 1.06],
}

koasurans_indirimi = {
    "80/20": 0.00,
    "75/25": 0.0625,
    "70/30": 0.1250,
    "65/35": 0.1875,
    "60/40": 0.2500,
    "55/45": 0.3125,
    "50/50": 0.3750,
    "45/55": 0.4375,
    "40/60": 0.50,
    "30/70": 0.1250,
    "25/75": 0.0625,
}

muafiyet_indirimi = {2: 0.00, 3: 0.06, 4: 0.13, 5: 0.19, 10: 0.35}

sure_carpani_tablosu = {
    6: 0.70,
    7: 0.75,
    8: 0.80,
    9: 0.85,
    10: 0.90,
    11: 0.95,
    12: 1.00,
    13: 1.05,
    14: 1.10,
    15: 1.15,
    16: 1.20,
    17: 1.25,
    18: 1.30,
    19: 1.35,
    20: 1.40,
    21: 1.45,
    22: 1.50,
    23: 1.55,
    24: 1.60,
    25: 1.65,
    26: 1.70,
    27: 1.74,
    28: 1.78,
    29: 1.82,
    30: 1.86,
    31: 1.90,
    32: 1.94,
    33: 1.98,
    34: 2.02,
    35: 2.06,
    36: 2.10,
}

# ================================================================
# STREAMLIT UI
# ================================================================

st.set_page_config(page_title="TarifeX", layout="centered")

st.markdown(
    """
    <style>
    body { background-color: #f9fbfc; }
    .stApp { padding-top: 2rem; }
    h1 { font-size: 50px !important; }
    p { font-size: 18px; }
    </style>
    <h1 style='text-align: center; color: #1F618D;'>TarifeX</h1>
    <p style='text-align: center;'>Akıllı Sigorta Prim Hesaplama Uygulaması</p>
    <p style='text-align: center; font-size: 16px; color: #7f8c8d;'>Deprem ve Yanardağ Püskürmesi Teminatı için Uygulanacak Güncel Tarife</p>
    <p style='text-align: center; font-size: 16px; color: #7f8c8d;'>Founder: <b>Ubeydullah Ayvaz</b> & <b>Furkan Kaymaz</b></p>
    """,
    unsafe_allow_html=True,
)

hesaplama_tipi = st.radio(
    "Hesaplama Türünü Seçin",
    [
        "Yangın Sigortası - Ticari Sinai Rizikolar (PD & BI)",
        "İnşaat & Montaj (CAR & EAR)",
    ],
)

# -----------------------------------------------------------------
# 1) YANGIN ‑ TİCARİ/SINAİ PRİM HESAPLAMA
# -----------------------------------------------------------------
if hesaplama_tipi == "Yangın Sigortası - Ticari Sinai Rizikolar (PD & BI)":
    st.subheader("🌊 Deprem Primi Hesaplayıcı")

    bina_tipi = st.selectbox("Yapı Tarzı", ["Betonarme", "Diğer"])
    deprem_bolgesi = st.selectbox("Deprem Risk Grubu (1=En Yüksek Risk)", list(range(1, 8)))
    para_birimi = st.selectbox("Para Birimi", ["TRY", "USD", "EUR"])
    kur_karsilik = fx_input(para_birimi, key_prefix="yangin")

    damage = st.number_input("Yangın Sigorta Bedeli (PD)", min_value=0, step=1000)
    bi = st.number_input("Kar Kaybı Bedeli (BI)", min_value=0, step=1000)
    ymm = st.number_input("Yangın Mali Mesuliyet Bedeli (YMM)", min_value=0, step=1000)
    enkaz = st.number_input("Enkaz Kaldırma Bedeli", min_value=0, step=1000)

    toplam_bedel = (damage + bi + ymm + enkaz) * kur_karsilik

    koasurans = st.selectbox("Koasürans Oranı", list(koasurans_indirimi.keys()))
    muafiyet = st.selectbox("Muafiyet Oranı (%)", list(muafiyet_indirimi.keys()))

    if st.button("Hesapla", key="deprem"):
        oran = tarife_oranlari[bina_tipi][deprem_bolgesi - 1] / 1000
        koasurans_ind = koasurans_indirimi[koasurans]
        muafiyet_ind = muafiyet_indirimi[muafiyet]
        nihai_oran = oran * (1 - koasurans_ind) * (1 - muafiyet_ind)
        prim = toplam_bedel * nihai_oran

        st.subheader("📋 Hesaplama Sonucu")
        st.markdown(f"*Tarife Oranı:* {oran*1000:.2f} ‰")
        st.markdown(f"*Koasürans İndirimi:* %{koasurans_ind*100:.2f}")
        st.markdown(f"*Muafiyet İndirimi:* %{muafiyet_ind*100:.2f}")
        st.markdown(f"*Uygulanan Oran:* %{nihai_oran*100:.4f}")
        st.markdown(f"*Toplam Sigorta Bedeli (TL):* {toplam_bedel:,.2f}")
        st.success(f"📈 Minimum Deprem Primi: {prim:,.2f} TL")

# -----------------------------------------------------------------
# 2) İNŞAAT & MONTAJ (CAR & EAR)
# -----------------------------------------------------------------
elif hesaplama_tipi == "İnşaat & Montaj (CAR & EAR)":
    st.subheader("🧱 CAR & EAR Primi Hesaplayıcı")
    st.markdown("Bu bölüm inşaat ve montaj işleri için teknik prim hesaplamasına yöneliktir.")

    risk_sinifi = st.selectbox("Risk Sınıfı", ["A", "B"])
    deprem_bolgesi = st.selectbox("Deprem Risk Grubu", list(range(1, 8)))
    baslangic_tarihi = st.date_input("Poliçe Başlangıç Tarihi")
    bitis_tarihi = st.date_input("Poliçe Bitiş Tarihi")

    def hesapla_sure_ay(bas, bit):
        ay = (bit.year - bas.year) * 12 + (bit.month - bas.month)
        if bit.day >= 15:
            ay += 1
        return ay

    sigorta_suresi = hesapla_sure_ay(baslangic_tarihi, bitis_tarihi)
    st.markdown(f"📅 Süre: {sigorta_suresi} ay")

    koasurans = st.selectbox(
        "Müşterek Sigorta (Koasürans Oranı)", list(koasurans_indirimi.keys()), key="car"
    )
    muafiyet = st.selectbox(
        "Muafiyet Oranı (%)", list(muafiyet_indirimi.keys()), key="carmuaf"
    )

    kur = st.selectbox("Para Birimi", ["TRY", "USD", "EUR"], key="carkur")
    kur_karsilik = fx_input(kur, key_prefix="car")

    st.markdown("---")
    st.markdown("*Teminat Bedelleri*")
    car_bedel = st.number_input("🏗️ Proje Bedeli (İnşaat - Montaj Bedeli)", min_value=0, step=1_000_000)
    cpm_bedel = st.number_input("🛠️ İnşaat Makineleri (CPM)", min_value=0, step=1_000_000)
    cpe_bedel = st.number_input("⚙️ Şantiye Tesisleri (CPE)", min_value=0, step=1_000_000)

    car_tarife_oranlari = {
        "A": [1.56, 1.31, 1.19, 0.98, 0.69, 0.54, 0.38],
        "B": [3.06, 2.79, 1.88, 1.00, 0.79, 0.63, 0.54],
    }

    if st.button("Hesapla", key="carcalc"):
        koasurans_ind = koasurans_indirimi[koasurans]
        muafiyet_ind = muafiyet_indirimi[muafiyet]

        def get_sure_carpani(sure):
            if sure <= 6:
                return sure_carpani_tablosu[6]
            elif sure in sure_carpani_tablosu:
                return sure_carpani_tablosu[sure]
            else:
                return sure_carpani_tablosu[36] + (sure - 36) * 0.03

        def hesapla_car(bedel):
            tl_bedel = bedel * kur_karsilik
            sure_carpani = get_sure_carpani(sigorta_suresi)
            oran = (car_tarife_oranlari[risk_sinifi][deprem_bolgesi - 1] / 1000) * sure_carpani
            if tl_bedel < 850_000_000:
                return bedel * oran * (1 - koasurans_ind) * (1 - muafiyet_ind)
            else:
                return (oran * 850_000_000 * (1 - koasurans_ind) * (1 - muafiyet_ind)) / kur_karsilik

        def hesapla_cpm(bedel):
            tl_bedel = bedel * kur_karsilik
            if tl_bedel < 850_000_000:
                oran = 0.002
            else:
                oran = (0.002 * 850_000_000) / tl_bedel
            return bedel * oran

        def hesapla_cpe(bedel):
            tl_bedel = bedel * kur_karsilik
            oran = 0.0012495
            if tl_bedel < 850_000_000:
                return bedel * oran
            else:
                return 850_000_000 * oran / kur_karsilik

        car_prim = hesapla_car(car_bedel)
        cpm_prim = hesapla_cpm(cpm_bedel)
        cpe_prim = hesapla_cpe(cpe_bedel)

        toplam_prim = car_prim + cpm_prim + cpe_prim
        toplam_bedel = (car_bedel + cpm_bedel + cpe_bedel) * kur_karsilik

        st.subheader("📋 Hesaplama Sonucu")
        st.markdown(f"*Toplam Sigorta Bedeli (TL):* {toplam_bedel:,.2f}")
        st.markdown(f"*Koasürans İndirimi:* %{koasurans_ind*100:.2f}")
        st.markdown(f"*Muafiyet İndirimi:* %{muafiyet_ind*100:.2f}")
        st.success(f"🏗️ Toplam Minimum Prim: {toplam_prim:,.2f} TL")
