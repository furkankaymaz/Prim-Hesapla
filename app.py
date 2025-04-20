import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# ================================================================
# DÖVİZ KURU YARDIMCI FONKSİYONLARI (sadece TCMB; elle güncelle ops.)
# ================================================================
@st.cache_data(ttl=60 * 60)  # 1 saatte bir yeniler
def get_tcmb_rate(ccy: str):
    """TCMB bugün.xml’den satış kuru döner → (rate, date_iso) / (None, None)"""
    try:
        r = requests.get("https://www.tcmb.gov.tr/kurlar/today.xml", timeout=4)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        for cur in root.findall("Currency"):
            if cur.attrib.get("CurrencyCode") == ccy:
                text = (cur.findtext("BanknoteSelling") or cur.findtext("ForexSelling"))
                rate = float(text.replace(",", "."))
                date_iso = datetime.strptime(root.attrib["Date"], "%d.%m.%Y").strftime("%Y-%m-%d")
                return rate, date_iso
    except Exception:
        pass
    return None, None


def fx_input(ccy: str, key_prefix: str) -> float:
    """TRY dışındaki para birimleri için TCMB satış kuru + manuel güncelleme alanı."""
    if ccy == "TRY":
        return 1.0

    rate_key = f"{key_prefix}_rate"
    src_key = f"{key_prefix}_src"
    date_key = f"{key_prefix}_date"

    # İlk seferde otomatik kur çek
    if rate_key not in st.session_state:
        rate, date_iso = get_tcmb_rate(ccy)
        if rate is None:
            rate, src, date_iso = 0.0, "MANUEL", "-"
        else:
            src = "TCMB"
        st.session_state.update({rate_key: rate, src_key: src, date_key: date_iso})

    # Bilgi şeridi
    st.info(
        f"1 {ccy} = {st.session_state[rate_key]:,.4f} TL "
        f"({st.session_state[src_key]}, {st.session_state[date_key]})"
    )

    # Manuel güncelleme
    new_rate = st.number_input(
        "Kuru manuel güncelleyebilirsiniz",
        value=float(st.session_state[rate_key]),
        min_value=0.0,
        step=0.0001,
        format="%.4f",
        key=f"{key_prefix}_manual",
    )
    st.session_state[rate_key] = new_rate
    return new_rate

# ================================================================
# SABİT TABLOLAR
# ================================================================

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
    6: 0.70, 7: 0.75, 8: 0.80, 9: 0.85, 10: 0.90, 11: 0.95, 12: 1.00,
    13: 1.05, 14: 1.10, 15: 1.15, 16: 1.20, 17: 1.25, 18: 1.30, 19: 1.35, 20: 1.40,
    21: 1.45, 22: 1.50, 23: 1.55, 24: 1.60, 25: 1.65, 26: 1.70, 27: 1.74, 28: 1.78,
    29: 1.82, 30: 1.86, 31: 1.90, 32: 1.94, 33: 1.98, 34: 2.02, 35: 2.06, 36: 2.10,
}

car_tarife_oranlari = {
    "A": [1.56, 1.31, 1.19, 0.98, 0.69, 0.54, 0.38],
    "B": [3.06, 2.79, 1.88, 1.00, 0.79, 0.63, 0.54],
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

# ---------------------------------------------------------------
# 1) YANGIN – TİCARİ/SINAİ
# ---------------------------------------------------------------
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
        prim = toplam
