import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# ------------------------------------------------------------
# Streamlit page config – MUST be first (no prior st.* calls)
# ------------------------------------------------------------
st.set_page_config(page_title="TarifeX", layout="centered")

###############################################################
# 0) Language selector (Türkçe / English)                     #
###############################################################
lang = st.sidebar.radio("Dil / Language", ["TR", "EN"], index=0)
T = {
    # UI text dictionary -----------------------------------------------------
    "title":       {"TR": "TarifeX – Akıllı Sigorta Prim Hesaplayıcı", "EN": "TarifeX – Smart Insurance Premium Calculator"},
    "subtitle":    {"TR": "Deprem ve Yanardağ Püskürmesi Teminatı", "EN": "Earthquake & Volcanic Eruption Cover"},
    "founder":     {"TR": "Kurucu", "EN": "Founder"},
    "select_calc": {"TR": "Hesaplama Türünü Seçin", "EN": "Select Calculation Type"},
    "calc_fire":   {"TR": "Yangın Sigortası - Ticari Sınai Rizikolar (PD & BI)", "EN": "Fire Insurance – Commercial / Industrial (PD & BI)"},
    "calc_car":    {"TR": "İnşaat & Montaj (CAR & EAR)", "EN": "Construction & Erection (CAR & EAR)"},
    "building_type": {"TR": "Yapı Tarzı", "EN": "Construction Type"},
    "risk_group":   {"TR": "Deprem Risk Grubu (1=En Yüksek Risk)", "EN": "Earthquake Risk Zone (1=Highest)"},
    "currency":     {"TR": "Para Birimi", "EN": "Currency"},
    "manual_fx":    {"TR": "Kuru manuel güncelleyebilirsiniz", "EN": "You can update the rate manually"},
    "pd":       {"TR": "Yangın Sigorta Bedeli (PD)", "EN": "Property Damage Sum Insured (PD)"},
    "bi":       {"TR": "Kar Kaybı Bedeli (BI)", "EN": "Business Interruption Sum Insured (BI)"},
    "ymm":     {"TR": "Yangın Mali Mesuliyet Bedeli (YMM)", "EN": "Third‑Party Liability Sum Insured"},
    "debris":   {"TR": "Enkaz Kaldırma Bedeli", "EN": "Debris Removal Sum Insured"},
    "koas":     {"TR": "Koasürans Oranı", "EN": "Coinsurance Share"},
    "deduct":   {"TR": "Muafiyet Oranı (%)", "EN": "Deductible (%)"},
    "btn_calc": {"TR": "Hesapla", "EN": "Calculate"},
    "min_premium": {"TR": "Minimum Deprem Primi", "EN": "Minimum EQ Premium"},
    "applied_rate": {"TR": "Uygulanan Oran %", "EN": "Applied Rate %"},
    # CAR / EAR
    "risk_class": {"TR": "Risk Sınıfı", "EN": "Risk Class"},
    "start": {"TR": "Poliçe Başlangıcı", "EN": "Policy Start"},
    "end": {"TR": "Poliçe Bitişi", "EN": "Policy End"},
    "duration": {"TR": "Süre", "EN": "Duration"},
    "months": {"TR": "ay", "EN": "months"},
    "coins": {"TR": "Koasürans", "EN": "Coinsurance"},
    "ded": {"TR": "Muafiyet (%)", "EN": "Deductible (%)"},
    "project": {"TR": "Proje Bedeli (CAR)", "EN": "Project Sum Insured (CAR)"},
    "cpm": {"TR": "İnşaat Makineleri (CPM)", "EN": "Construction Machinery (CPM)"},
    "cpe": {"TR": "Şantiye Tesisleri (CPE)", "EN": "Site Facilities (CPE)"},
    "total_premium": {"TR": "Toplam Minimum Prim", "EN": "Total Minimum Premium"},
}

def tr(key: str) -> str:
    """Translate helper using selected language."""
    return T[key][lang]

###############################################################
# 1) TCMB FX MODULE                                          #
###############################################################
@st.cache_data(ttl=60 * 60)
def get_tcmb_rate(ccy: str):
    """Return last available TCMB BanknoteSelling rate for code ccy."""
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
    """Show rate info + manual override, return rate."""
    if ccy == "TRY":
        return 1.0
    r_key = f"{key_prefix}_{ccy}_rate"
    s_key = f"{key_prefix}_{ccy}_src"
    d_key = f"{key_prefix}_{ccy}_dt"
    if r_key not in st.session_state:
        rate, dt = get_tcmb_rate(ccy)
        if rate is None:
            st.session_state.update({r_key: 0.0, s_key: "MANUEL", d_key: "-"})
        else:
            st.session_state.update({r_key: rate, s_key: "TCMB", d_key: dt})
    st.info(f"1 {ccy} = {st.session_state[r_key]:,.4f} TL ({st.session_state[s_key]}, {st.session_state[d_key]})")
    new_rate = st.number_input(tr("manual_fx"), value=float(st.session_state[r_key]), step=0.0001, format="%.4f", key=f"{key_prefix}_{ccy}_manual")
    st.session_state[r_key] = new_rate
    return new_rate

###############################################################
# 2) CONSTANT TABLES                                         #
###############################################################

tarife_oranlari = {
    "Betonarme": [3.13, 2.63, 2.38, 1.94, 1.38, 1.06, 0.75],
    "Diğer":     [6.13, 5.56, 3.75, 2.00, 1.56, 1.24, 1.06],
}
koasurans_indirimi = {"80/20":0.0,"75/25":0.0625,"70/30":0.125,"65/35":0.1875,"60/40":0.25,"55/45":0.3125,"50/50":0.375,"45/55":0.4375,"40/60":0.5,"30/70":0.125,"25/75":0.0625}
muafiyet_indirimi = {2:0.0,3:0.06,4:0.13,5:0.19,10:0.35}
# süre çarpanları 6‑36 ay, >36 +%3/ay
sure_carpani_tablosu = {m:0.70+0.05*(m-6) for m in range(6,13)}
sure_carpani_tablosu.update({m:1.00+0.05*(m-12) for m in range(13,25)})
sure_carpani_tablosu.update({m:1.60+0.05*(m-24) for m in range(25,37)})
sure_carpani_tablosu[6] = 0.70
car_tarife_oranlari = {
    "A": [1
