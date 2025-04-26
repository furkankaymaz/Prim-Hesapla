import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# ------------------------------------------------------------
# STREAMLIT CONFIG (must be first)
# ------------------------------------------------------------
st.set_page_config(page_title="TarifeX – Akıllı Sigorta Prim Hesaplama", layout="centered")

# ------------------------------------------------------------
# CUSTOM CSS STYLING
# ------------------------------------------------------------
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
# LANGUAGE SELECTOR (Top Right)
# ------------------------------------------------------------
with st.container():
    st.markdown('<div class="lang-selector">', unsafe_allow_html=True)
    lang = st.radio("🌐", ["TR", "EN"], index=0, horizontal=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------------------------
# TRANSLATIONS
# ------------------------------------------------------------
T = {
    "title": {"TR": "TarifeX – Akıllı Sigorta Prim Hesaplama", "EN": "TarifeX – Smart Insurance Premium Calculator"},
    "subtitle": {"TR": "Deprem ve Yanardağ Püskürmesi Teminatı", "EN": "Earthquake & Volcanic Eruption Coverage"},
    "select_calc": {"TR": "Hesaplama Türünü Seçin", "EN": "Select Calculation Type"},
    "calc_fire": {"TR": "Yangın Sigortası (PD & BI)", "EN": "Fire Insurance (PD & BI)"},
    "calc_car": {"TR": "İnşaat & Montaj (CAR & EAR)", "EN": "Construction & Erection (CAR & EAR)"},
    "currency": {"TR": "Para Birimi", "EN": "Currency"},
    "manual_fx": {"TR": "Kuru manuel güncelleyebilirsiniz", "EN": "You can manually update the exchange rate"},
    "btn_calc": {"TR": "Hesapla", "EN": "Calculate"},
    "pd_premium": {"TR": "PD Primi", "EN": "PD Premium"},
    "bi_premium": {"TR": "BI Primi", "EN": "BI Premium"},
    "car_premium": {"TR": "CAR Primi", "EN": "CAR Premium"},
    "cpm_premium": {"TR": "CPM Primi", "EN": "CPM Premium"},
    "cpe_premium": {"TR": "CPE Primi", "EN": "CPE Premium"},
    "total_premium": {"TR": "Toplam Prim", "EN": "Total Premium"},
    "limit_warning_fire": {"TR": "⚠️ Yangın: 3.5 milyar TL limit var.", "EN": "⚠️ Fire: 3.5 billion TRY limit."},
    "limit_warning_car": {"TR": "⚠️ Montaj: 840 milyon TL limit var.", "EN": "⚠️ Construction: 840 million TRY limit."}
}

def tr(key):
    return T[key][lang]

# ------------------------------------------------------------
# FX RATE MODULE
# ------------------------------------------------------------
@st.cache_data(ttl=3600)
def get_tcmb_rate(ccy: str):
    try:
        r = requests.get("https://www.tcmb.gov.tr/kurlar/today.xml", timeout=5)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        for cur in root.findall("Currency"):
            if cur.attrib.get("CurrencyCode") == ccy:
                txt = cur.findtext("BanknoteSelling") or cur.findtext("ForexSelling")
                return float(txt.replace(",", ".")), root.attrib.get("Date")
    except:
        return None, None
    return None, None

@st.cache_data(ttl=3600)
def fx_input(ccy: str, key_prefix: str):
    if ccy == "TRY":
        return 1.0, ""
    r_key = f"{key_prefix}_{ccy}_rate"
    s_key = f"{key_prefix}_{ccy}_src"
    d_key = f"{key_prefix}_{ccy}_dt"
    if r_key not in st.session_state:
        rate, dt = get_tcmb_rate(ccy)
        if rate:
            st.session_state[r_key] = rate; st.session_state[s_key] = "TCMB"; st.session_state[d_key] = dt
        else:
            st.session_state[r_key] = 0.0; st.session_state[s_key] = "MANUEL"; st.session_state[d_key] = "-"
    fx_rate = st.number_input(tr("manual_fx"), value=float(st.session_state[r_key]), step=0.0001, format="%.4f", key=r_key)
    fx_info = f"💱 1 {ccy} = {fx_rate:.4f} TL ({st.session_state[s_key]}, {st.session_state[d_key]})"
    st.info(fx_info)
    return fx_rate, fx_info

# ------------------------------------------------------------
# CONSTANT TABLES
# ------------------------------------------------------------
tarife_oranlari = {"Betonarme":[3.13,2.63,2.38,1.94,1.38,1.06,0.75],"Diğer":[6.13,5.56,3.75,2.00,1.56,1.24,1.06]}
car_tarife = {"A":[1.56,1.31,1.19,0.98,0.69,0.54,0.38],"B":[3.06,2.79,1.88,1.00,0.79,0.63,0.54]}
sure_carpani_tablosu = {6:0.70,7:0.75,8:0.80,9:0.85,10:0.90,11:0.95,12:1.00,13:1.05,14:1.10,15:1.15,16:1.20,17:1.25,18:1.30,19:1.35,20:1.40,21:1.45,22:1.50,23:1.55,24:1.60,25:1.65,26:1.70,27:1.74,28:1.78,29:1.82,30:1.86,31:1.90,32:1.94,33:1.98,34:2.02,35:2.06,36:2.10}
koasurans_indirimi={"80/20":0.0,"75/25":0.0625,"70/30":0.125,"65/35":0.1875,"60/40":0.25}
muafiyet_indirimi={2:0.0,3:0.06,4:0.13,5:0.19,10:0.35}

# ------------------------------------------------------------
# CALCULATION FUNCTIONS
# ------------------------------------------------------------
def calculate_duration(months):
    if months<=36: return sure_carpani_tablosu.get(months,1.0)
    return sure_carpani_tablosu[36]*(1+0.03*(months-36))

def calculate_fire_premium(building_type,risk,pd,bi,fx):
    pd_tl,bi_tl=pd*fx,bi*fx;rate=tarife_oranlari[building_type][risk-1];LIMIT=3_500_000_000
    if pd_tl>LIMIT: pd_tl=LIMIT; st.warning(tr("limit_warning_fire"))
    if bi_tl>LIMIT: bi_tl=LIMIT; st.warning(tr("limit_warning_fire"))
    pd_pr,bi_pr=pd_tl*rate/1000,bi_tl*rate/1000
    return pd_pr,bi_pr,pd_pr+bi_pr,rate

def calculate_car_ear_premium(risk_class, risk_group, start, end, project, cpm, cpe, currency, koas, deduct, fx_rate):
    mo=(end.year-start.year)*12+(end.month-start.month)+(1 if end.day>=15 else 0)
    dm=calculate_duration(mo)
    br=car_tarife[risk_class][risk_group-1]
    rr=br*dm*(1-koasurans_indirimi[koas])*(1-muafiyet_indirimi[deduct])
    LIMIT=840_000_000
    # CAR
    car_tl=min(project*fx_rate,LIMIT);car_pr=car_tl*rr/1000
    # CPM
    cpm_tl=min(cpm*fx_rate,LIMIT)
    cpm_rate=2 if cpm_tl<=LIMIT else 2*LIMIT/cpm_tl
    days=(end-start).days;cpm_pr=cpm_tl*cpm_rate/1000*days/365
    # CPE
    cpe_tl=min(cpe*fx_rate,LIMIT);cpe_pr=cpe_tl*(br*dm)/1000
    total=car_pr+cpm_pr+cpe_pr
    return car_pr,cpm_pr,cpe_pr,total,rr

# ------------------------------------------------------------
# UI RENDERING
# ------------------------------------------------------------
st.markdown(f'<h1 class="main-title">🏷️ {tr("title")}</h1>', unsafe_allow_html=True)
st.markdown(f'<h3 class="subtitle">{tr("subtitle")}</h3>', unsafe_allow_html=True)
st.markdown('<p class="founders">Founders: Ubeydullah Ayvaz & Furkan Kaymaz</p>', unsafe_allow_html=True)

calc_type=st.selectbox(tr("select_calc"),[tr("calc_fire"),tr("calc_car")])

if calc_type==tr("calc_fire"):
    st.markdown(f'<h3 class="section-header">{tr("fire_header")}</h3>', unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        bld=st.selectbox(tr("building_type"),["Betonarme","Diğer"])
        rg=st.selectbox(tr("risk_group"),range(1,8))
        cur=st.selectbox(tr("currency"),["TRY","USD","EUR"] )
    with c2:
        fx,info=fx_input(cur,"fire");st.info(info)
    pd=st.number_input(tr("pd"),min_value=0.0);bi=st.number_input(tr("bi"),min_value=0.0)
    ko=st.selectbox(tr("koas"),list(koasurans_indirimi.keys()));ded=st.selectbox(tr("deduct"),list(muafiyet_indirimi.keys()))
    if st.button(tr("btn_calc")):
        pd_pr,bi_pr,tot_pr,ar=calculate_fire_premium(bld,rg,pd,bi,fx)
        if cur!="TRY":
            st.info(f": {pd_pr/fx:.2f} {cur}");st.info(f": {bi_pr/fx:.2f} {cur}");st.info(f": {tot_pr/fx:.2f} {cur}")
        else:
            st.info(f": {pd_pr:,.2f} TL");st.info(f": {bi_pr:,.2f} TL");st.info(f": {tot_pr:,.2f} TL")
        st.info(f"📊 {tr('applied_rate')}: {ar:.2f}‰")
else:
    st.markdown(f'<h3 class="section-header">{tr("car_header")}</h3>', unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        risk_type=st.selectbox(tr("risk_class"),["A","B"],help=tr("risk_class_help"))
        deprem_zone=st.selectbox(tr("risk_group"),range(1,8),help=tr("risk_group_help"))
        start_date=st.date_input(tr("start"));end_date=st.date_input(tr("end"))
    with c2:
        cur=st.selectbox(tr("currency"),["TRY","USD","EUR"]);fx,info=fx_input(cur,"car");st.info(info)
    project=st.number_input(tr("project"),min_value=0.0)
    cpm=st.number_input(tr("cpm"),min_value=0.0)
    cpe=st.number_input(tr("cpe"),min_value=0.0)
    ko=st.selectbox(tr("coins"),list(koasurans_indirimi.keys()))
    de=st.selectbox(tr("ded"),list(muafiyet_indirimi.keys()))
    if st.button(tr("btn_calc")):
        car_pr,cpm_pr,cpe_pr,tot_pr,ar=calculate_car_ear_premium(risk_type,deprem_zone,start_date,end_date,project,cpm,cpe,cur,ko,de,fx)
        if cur!="TRY":
            st.info(f"✅ {tr('car_premium')}: {car_pr/fx:.2f} {cur}")
            st.info(f"✅ {tr('cpm_premium')}: {cpm_pr/fx:.2f} {cur}")
            st.info(f"✅ {tr('cpe_premium')}: {cpe_pr/fx:.2f} {cur}")
            st.info(f"✅ {tr('total_premium')}: {tot_pr/fx:.2f} {cur}")
        else:
            st.info(f"✅ {tr('car_premium')}: {car_pr:,.2f} TL")
            st.info(f"✅ {tr('cpm_premium')}: {cpm_pr:,.2f} TL")
            st.info(f"✅ {tr('cpe_premium')}: {cpe_pr:,.2f} TL")
            st.info(f"✅ {tr('total_premium')}: {tot_pr:,.2f} TL")
        st.info(f"📊 {tr('applied_rate')}: {ar:.2f}‰")
