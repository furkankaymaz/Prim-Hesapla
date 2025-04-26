import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# ------------------------------------------------------------
# STREAMLIT CONFIG
st.set_page_config(page_title="TarifeX – Akıllı Sigorta Prim Hesaplama", layout="centered")

# ------------------------------------------------------------
# STYLING
st.markdown("""
<style>
    .main-title { font-size: 2.5em; color: #2E86C1; text-align: center; margin-bottom: 0.5em; }
    .subtitle { font-size: 1.2em; color: #5DADE2; text-align: center; margin-bottom: 0.5em; }
    .founders { font-size: 1em; color: #1A5276; text-align: center; margin-bottom: 1em; }
    .section-header { font-size: 1.5em; color: #1A5276; margin-top: 1em; margin-bottom: 0.5em; }
    .stButton>button { background-color: #2E86C1; color: white; border-radius: 10px; padding: 0.5em 1em; }
    .stButton>button:hover { background-color: #1A5276; color: white; }
    .lang-selector { position: fixed; top: 10px; right: 10px; z-index: 999; }
    .info-box { background-color: #F0F8FF; padding: 1em; border-radius: 10px; margin-bottom: 1em; }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# LANGUAGE SELECTOR
with st.container():
    st.markdown('<div class="lang-selector">', unsafe_allow_html=True)
    lang = st.radio("🌐", ["TR", "EN"], index=0, horizontal=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------------------------
# TRANSLATIONS
def tr(key):
    return translations[key][lang]

translations = {
    "title": {"TR": "TarifeX – Akıllı Sigorta Prim Hesaplama", "EN": "TarifeX – Smart Insurance Premium Calculator"},
    "subtitle": {"TR": "Deprem ve Yanardağ Teminatı Hesaplama", "EN": "Earthquake & Volcanic Coverage Calculator"},
    "select_calc": {"TR": "Hesaplama Türünü Seçin", "EN": "Select Calculation Type"},
    "calc_fire": {"TR": "Yangın Sigortası (PD & BI)", "EN": "Fire Insurance (PD & BI)"},
    "calc_car": {"TR": "İnşaat & Montaj (CAR & EAR)", "EN": "Construction & Erection (CAR & EAR)"},
    "currency": {"TR": "Para Birimi", "EN": "Currency"},
    "manual_fx": {"TR": "Kuru manuel girin", "EN": "Manual FX Rate"},
    "btn_calc": {"TR": "Hesapla", "EN": "Calculate"},
    "pd": {"TR": "Yangın Sigorta Bedeli (PD)", "EN": "Property Damage (PD)"},
    "bi": {"TR": "Kar Kaybı Bedeli (BI)", "EN": "Business Interruption (BI)"},
    "koas": {"TR": "Koasürans Oranı", "EN": "Coinsurance"},
    "deduct": {"TR": "Muafiyet (%)", "EN": "Deductible (%)"},
    "building_type": {"TR": "Yapı Tarzı", "EN": "Building Type"},
    "building_type_help": {"TR": "Betonarme veya Diğer", "EN": "Concrete or Other"},
    "risk_group": {"TR": "Deprem Risk Grubu", "EN": "Risk Zone (1=Highest)"},
    "risk_group_help": {"TR": "1=En yüksek risk", "EN": "1=Highest risk"},
    "risk_class": {"TR": "Risk Sınıfı", "EN": "Risk Class"},
    "risk_class_help": {"TR": "A veya B tercihi", "EN": "Choose A or B"},
    "start": {"TR": "Poliçe Başlangıcı", "EN": "Policy Start"},
    "end": {"TR": "Poliçe Bitişi", "EN": "Policy End"},
    "project": {"TR": "Proje Bedeli (CAR)", "EN": "Project CAR"},
    "cpm": {"TR": "İnşaat Makineleri (CPM)", "EN": "Construction Machinery (CPM)"},
    "cpe": {"TR": "Şantiye Tesisleri (CPE)", "EN": "Site Facilities (CPE)"},
    "pd_premium": {"TR": "PD Primi", "EN": "PD Premium"},
    "bi_premium": {"TR": "BI Primi", "EN": "BI Premium"},
    "car_premium": {"TR": "CAR Primi", "EN": "CAR Premium"},
    "cpm_premium": {"TR": "CPM Primi", "EN": "CPM Premium"},
    "cpe_premium": {"TR": "CPE Primi", "EN": "CPE Premium"},
    "total_premium": {"TR": "Toplam Prim", "EN": "Total Premium"},
    "applied_rate": {"TR": "Uygulanan Oran (‰)", "EN": "Applied Rate (‰)"},
    "limit_warning_fire": {"TR": "⚠️ Yangın: 3.5 milyar TL limit aşımı", "EN": "⚠️ Fire: 3.5 bn TRY limit"},
    "limit_warning_car": {"TR": "⚠️ Montaj: 840 milyon TL limit aşımı", "EN": "⚠️ CAR: 840 mn TRY limit"}
}

# ------------------------------------------------------------
# FX MODULE
def get_tcmb_rate(ccy):
    try:
        r = requests.get("https://www.tcmb.gov.tr/kurlar/today.xml", timeout=5)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        for cur in root.findall("Currency"):
            if cur.attrib.get("CurrencyCode") == ccy:
                txt = cur.findtext("BanknoteSelling") or cur.findtext("ForexSelling")
                date = root.attrib.get("Date", "-")
                return float(txt.replace(',', '.')), date
    except:
        pass
    return None, None

@st.cache_data(ttl=3600)
def fx_input(ccy, prefix):
    if ccy == 'TRY': return 1.0, ''
    rate_key = f"{prefix}_{ccy}_rate"
    src_key = f"{prefix}_{ccy}_src"
    dt_key = f"{prefix}_{ccy}_dt"
    if rate_key not in st.session_state:
        rate, date = get_tcmb_rate(ccy)
        st.session_state[rate_key] = rate or 0
        st.session_state[src_key] = 'TCMB' if rate else 'MANUEL'
        st.session_state[dt_key] = date or '-'
    fx = st.number_input(tr('manual_fx'), value=st.session_state[rate_key], step=0.0001, format="%.4f", key=rate_key)
    info = f"💱1 {ccy} = {fx:.4f} TL ({st.session_state[src_key]}, {st.session_state[dt_key]})"
    st.info(info)
    return fx, info

# ------------------------------------------------------------
# CONSTANTS
tarife_fire = {'Betonarme': [3.13,2.63,2.38,1.94,1.38,1.06,0.75], 'Diğer': [6.13,5.56,3.75,2.00,1.56,1.24,1.06]}
car_rates = {'A': [1.56,1.31,1.19,0.98,0.69,0.54,0.38], 'B': [3.06,2.79,1.88,1.00,0.79,0.63,0.54]}
sure_tab = {i: v for i,v in {
    **{i:0.70+0.05*(i-6) for i in range(6,12)},
    12:1.00,13:1.05,14:1.10,15:1.15,16:1.20,17:1.25,18:1.30,19:1.35,20:1.40,
    21:1.45,22:1.50,23:1.55,24:1.60,25:1.65,26:1.70,27:1.74,28:1.78,29:1.82,30:1.86,
    31:1.90,32:1.94,33:1.98,34:2.02,35:2.06,36:2.10}.items()}
koas_tab = {'80/20':0, '75/25':0.0625, '70/30':0.125, '65/35':0.1875, '60/40':0.25}
ded_tab = {2:0,3:0.06,4:0.13,5:0.19,10:0.35}

# ------------------------------------------------------------
# HELPERS
def calc_duration(mo):
    if mo <= 36:
        return sure_tab.get(mo, 1)
    return sure_tab[36] + 0.03 * (mo - 36)

# ------------------------------------------------------------
# FIRE CALCULATION
def calculate_fire(bld, rg, pd, bi, fx):
    pd_tl, bi_tl = pd * fx, bi * fx
    rate = tarife_fire[bld][rg - 1]
    L = 3_500_000_000
    if pd_tl > L: pd_tl = L; st.warning(tr('limit_warning_fire'))
    if bi_tl > L: bi_tl = L; st.warning(tr('limit_warning_fire'))
    pd_pr = pd_tl * rate / 1000
    bi_pr = bi_tl * rate / 1000
    return pd_pr, bi_pr, pd_pr + bi_pr, rate

# ------------------------------------------------------------
# CAR & EAR CALCULATION
def calculate_car_ear(rc, rz, sd, ed, prj, cpm, cpe, ko, de, fx):
    # Duration months
    mo = (ed.year - sd.year) * 12 + (ed.month - sd.month) + (1 if ed.day >= 15 else 0)
    dm = calc_duration(mo)
    br = car_rates[rc][rz - 1]
    disc = (1 - koas_tab[ko]) * (1 - ded_tab[de])
    L = 840_000_000
    # CAR
    vol_car = prj * fx * dm
    if vol_car <= L:
        car_pr = prj * br * dm * disc * fx / 1000
    else:
        st.warning(tr('limit_warning_car'))
        car_pr = L * br * disc / 1000
    # CPM
    vol_cpm = cpm * fx
    cp_rate = 2 if vol_cpm <= L else 2 * L / (vol_cpm * dm)
    days = (ed - sd).days
    cpm_pr = vol_cpm * cp_rate / 1000 * (days / 365)
    # CPE
    vol_cpe = cpe * fx * dm
    if vol_cpe <= L:
        cpe_pr = cpe * br * dm * fx / 1000
    else:
        st.warning(tr('limit_warning_car'))
        cpe_pr = L * br / 1000
    total = car_pr + cpm_pr + cpe_pr
    return car_pr, cpm_pr, cpe_pr, total, br * disc * dm

# ------------------------------------------------------------
# UI RENDER
st.markdown(f'<h1 class="main-title">🏷️ {tr("title")}</h1>', unsafe_allow_html=True)
st.markdown(f'<h3 class="subtitle">{tr("subtitle")}</h3>', unsafe_allow_html=True)
st.markdown('<p class="founders">Founders: Ubeydullah Ayvaz & Furkan Kaymaz</p>', unsafe_allow_html=True)

choice = st.selectbox(tr('select_calc'), [tr('calc_fire'), tr('calc_car')])

if choice == tr('calc_fire'):
    c1, c2 = st.columns(2)
    with c1:
        bld = st.selectbox(tr('building_type'), ['Betonarme', 'Diğer'], help=tr('building_type_help'))
        rg = st.selectbox(tr('risk_group'), list(range(1, 8)), help=tr('risk_group_help'))
        cur = st.selectbox(tr('currency'), ['TRY', 'USD', 'EUR'])
    with c2:
        fx, info = fx_input(cur, 'fire')
    pd = st.number_input(tr('pd'), min_value=0.0)
    bi = st.number_input(tr('bi'), min_value=0.0)
    ko = st.selectbox(tr('koas'), list(koas_tab.keys()))
    de = st.selectbox(tr('deduct'), list(ded_tab.keys()))
    if st.button(tr('btn_calc')):
        pd_pr, bi_pr, tot_pr, ar = calculate_fire(bld, rg, pd, bi, fx)
        if cur != 'TRY':
            st.info(f"✅ {tr('pd_premium')}: {pd_pr/fx:,.2f} {cur}")
            st.info(f"✅ {tr('bi_premium')}: {bi_pr/fx:,.2f} {cur}")
            st.info(f"✅ {tr('total_premium')}: {tot_pr/fx:,.2f} {cur}")
        else:
            st.info(f"✅ {tr('pd_premium')}: {pd_pr:,.2f} TL")
            st.info(f"✅ {tr('bi_premium')}: {bi_pr:,.2f} TL")
            st.info(f"✅ {tr('total_premium')}: {tot_pr:,.2f} TL")
        st.info(f"📊 {tr('applied_rate')}: {ar:.2f} ‰")
else:
    c1, c2 = st.columns(2)
    with c1:
        rc = st.selectbox(tr('risk_class'), ['A', 'B'], help=tr('risk_class_help'))
        rz = st.selectbox(tr('risk_group'), list(range(1, 8)), help=tr('risk_group_help'))
        sd = st.date_input(tr('start'), value=datetime.today())
        ed = st.date_input(tr('end'), value=datetime.today() + timedelta(days=365))
    with c2:
        cur = st.selectbox(tr('currency'), ['TRY', 'USD', 'EUR'])
        fx, info = fx_input(cur, 'car')
    prj = st.number_input(tr('project'), min_value=0.0)
    cpm_v = st.number_input(tr('cpm'), min_value=0.0)
    cpe_v = st.number_input(tr('cpe'), min_value=0.0)
    ko = st.selectbox(tr('coins'), list(koas_tab.keys()))
    de = st.selectbox(tr('ded'), list(ded_tab.keys()))
    if st.button(tr('btn_calc')):
        car_pr, cpm_pr, cpe_pr, tot_pr, ar = calculate_car_ear(rc, rz, sd, ed, prj, cpm_v, cpe_v, ko, de, fx)
        if cur != 'TRY':
            st.info(f"✅ {tr('car_premium')}: {car_pr/fx:,.2f} {cur}")
            st.info(f"✅ {tr('cpm_premium')}: {cpm_pr/fx:,.2f} {cur}")
            st.info(f"✅ {tr('cpe_premium')}: {cpe_pr/fx:,.2f} {cur}")
            st.info(f"✅ {tr('total_premium')}: {tot_pr/fx:,.2f} {cur}")
        else:
            st.info(f"✅ {tr('car_premium')}: {car_pr:,.2f} TL")
            st.info(f"✅ {tr('cpm_premium')}: {cpm_pr:,.2f} TL")
            st.info(f"✅ {tr('cpe_premium')}: {cpe_pr:,.2f} TL")
            st.info(f"✅ {tr('total_premium')}: {tot_pr:,.2f} TL")
        st.info(f"📊 {tr('applied_rate')}: {ar:.2f} ‰")
