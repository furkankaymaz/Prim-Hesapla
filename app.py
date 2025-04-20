import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# ------------------------------------------------------------
# Streamlit sayfa ayarı **ilk komut** olmak zorunda
# ------------------------------------------------------------
st.set_page_config(page_title="TarifeX", layout="centered")

"""
TarifeX – Akıllı Sigorta Prim Hesaplayıcı
------------------------------------------------
• Yangın (PD & BI) – Ticari/Sınai rizikolar
• İnşaat & Montaj (CAR/EAR)
• Deprem + Yanardağ Püskürmesi teminatı
• TCMB satış kurunu otomatik çeker; hafta sonu → son iş günü
"""
###############################################################
# TCMB KUR MODÜLÜ                                            #
###############################################################
@st.cache_data(ttl=60 * 60)
def get_tcmb_rate(ccy: str):
    """Son TCMB BanknoteSelling kuru; today.xml yoksa geriye 7 gün."""
    try:
        r = requests.get("https://www.tcmb.gov.tr/kurlar/today.xml", timeout=4)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        for cur in root.findall("Currency"):
            if cur.attrib.get("CurrencyCode") == ccy:
                txt = cur.findtext("BanknoteSelling") or cur.findtext("ForexSelling")
                return float(txt.replace(",", ".")), datetime.strptime(root.attrib["Date"], "%d.%m.%Y").strftime("%Y-%m-%d")
    except Exception:
        pass
    today = datetime.today()
    for i in range(1, 8):
        d = today - timedelta(days=i)
        url = f"https://www.tcmb.gov.tr/kurlar/{d:%Y%m}/{d:%d%m%Y}.xml"
        try:
            r = requests.get(url, timeout=4)
            if not r.ok:
                continue
            root = ET.fromstring(r.content)
            for cur in root.findall("Currency"):
                if cur.attrib.get("CurrencyCode") == ccy:
                    txt = cur.findtext("BanknoteSelling") or cur.findtext("ForexSelling")
                    return float(txt.replace(",", ".")), d.strftime("%Y-%m-%d")
        except Exception:
            continue
    return None, None

def fx_input(ccy: str, key_prefix: str) -> float:
    if ccy == "TRY":
        return 1.0
    r_key, s_key, d_key = f"{key_prefix}_rate", f"{key_prefix}_src", f"{key_prefix}_dt"
    if r_key not in st.session_state:
        rate, dt = get_tcmb_rate(ccy)
        if rate is None:
            st.session_state.update({r_key: 0.0, s_key: "MANUEL", d_key: "-"})
        else:
            st.session_state.update({r_key: rate, s_key: "TCMB", d_key: dt})
    st.info(f"1 {ccy} = {st.session_state[r_key]:,.4f} TL ({st.session_state[s_key]}, {st.session_state[d_key]})")
    new_rate = st.number_input("Kuru manuel güncelleyebilirsiniz", value=float(st.session_state[r_key]), step=0.0001, format="%.4f", key=f"{key_prefix}_manual")
    st.session_state[r_key] = new_rate
    return new_rate
###############################################################
# SABİT TABLOLAR                                             #
###############################################################

tarife_oranlari = {
    "Betonarme": [3.13, 2.63, 2.38, 1.94, 1.38, 1.06, 0.75],
    "Diğer":     [6.13, 5.56, 3.75, 2.00, 1.56, 1.24, 1.06],
}
koasurans_indirimi = {"80/20":0.0,"75/25":0.0625,"70/30":0.125,"65/35":0.1875,"60/40":0.25,"55/45":0.3125,"50/50":0.375,"45/55":0.4375,"40/60":0.5,"30/70":0.125,"25/75":0.0625}
muafiyet_indirimi = {2:0.0,3:0.06,4:0.13,5:0.19,10:0.35}
sure_carpani_tablosu = {**{m:0.70+0.05*(m-6) for m in range(6,13)},**{m:1.00+0.05*(m-12) for m in range(13,25)},**{m:1.60+0.05*(m-24) for m in range(25,37)}}
sure_carpani_tablosu[6]=0.70
car_tarife_oranlari = {
    "A": [1.56,1.31,1.19,0.98,0.69,0.54,0.38],
    "B": [3.06,2.79,1.88,1.00,0.79,0.63,0.54],
}
###############################################################
# SAYFA ÜST BAŞLIK                                           #
###############################################################

st.markdown(
    """
<style>body{background:#f9fbfc}.stApp{padding-top:2rem}h1{font-size:50px!important}</style>
<h1 style='text-align:center;color:#1F618D'>TarifeX</h1>
<p style='text-align:center'>Akıllı Sigorta Prim Hesaplama Uygulaması</p>
<p style='text-align:center;font-size:16px;color:#7f8c8d'>Deprem ve Yanardağ Püskürmesi Teminatı</p>
<p style='text-align:center;font-size:16px;color:#7f8c8d'>Founder: <b>Ubeydullah Ayvaz</b> & <b>Furkan Kaymaz</b></p>
""",
    unsafe_allow_html=True,
)

hesaplama_tipi = st.radio("Hesaplama Türünü Seçin", ["Yangın Sigortası - Ticari Sinai Rizikolar (PD & BI)", "İnşaat & Montaj (CAR & EAR)"])

########################################
# YANGIN – TİCARİ/SINAİ
########################################
if hesaplama_tipi.startswith("Yangın"):
    bina_tipi = st.selectbox("Yapı Tarzı", ["Betonarme", "Diğer"])
    deprem_bolgesi = st.selectbox("Deprem Risk Grubu (1=En Yüksek Risk)", list(range(1,8)))
    para_birimi = st.selectbox("Para Birimi", ["TRY", "USD", "EUR"], key="ybim")
    kur = fx_input(para_birimi, "yangin")
    damage = st.number_input("Yangın Sigorta Bedeli (PD)", min_value=0, step=1000)
    bi     = st.number_input("Kar Kaybı Bedeli (BI)",  min_value=0, step=1000)
    ymm    = st.number_input("Yangın Mali Mesuliyet Bedeli (YMM)", min_value=0, step=1000)
    enkaz  = st.number_input("Enkaz Kaldırma Bedeli", min_value=0, step=1000)
    total_bed = (damage+bi+ymm+enkaz)*kur
    koas = st.selectbox("Koasürans Oranı", list(koasurans_indirimi.keys()))
    mua  = st.selectbox("Muafiyet Oranı (%)", list(muafiyet_indirimi.keys()))
    if st.button("Hesapla", key="yangin_calc"):
        oran = tarife_oranlari[bina_tipi][deprem_bolgesi-1]/1000
        k_ind = koasurans_indirimi[koas]
        m_ind = muafiyet_indirimi[mua]
        nih_oran = oran*(1-k_ind)*(1-m_ind)
        prim = total_bed*nih_oran
        st.success(f"Minimum Deprem Primi: {prim:,.2f} TL")
        st.markdown(f"*Uygulanan Oran %:* {nih_oran*100:.4f}")

########################################
# CAR / EAR
########################################
elif hesaplama_tipi.startswith("İnşaat"):
    risk = st.selectbox("Risk Sınıfı", ["A","B"])
    deprem_bolgesi = st.selectbox("Deprem Risk Grubu", list(range(1,8)), key="dep_c")
    bas = st.date
