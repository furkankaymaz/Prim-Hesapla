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
    except Exception:
        return None, None
    return None, None

@st.cache_data(ttl=3600)
def fx_input(ccy: str, key_prefix: str):
    if ccy == "TRY":
        return 1.0, ""
    r, s, d = f"{key_prefix}_{ccy}_rate", f"{key_prefix}_{ccy}_src", f"{key_prefix}_{ccy}_dt"
    if r not in st.session_state:
        rate, dt = get_tcmb_rate(ccy)
        if rate:
            st.session_state[r] = rate; st.session_state[s] = "TCMB"; st.session_state[d] = dt
        else:
            st.session_state[r] = 0.0; st.session_state[s] = "MANUEL"; st.session_state[d] = "-"
    fx_rate = st.number_input(tr("manual_fx"), value=float(st.session_state[r]), step=0.0001, format="%.4f", key=r)
    fx_info = f"💱 1 {ccy} = {fx_rate:.4f} TL ({st.session_state[s]}, {st.session_state[d]})"
    st.info(fx_info)
    return fx_rate, fx_info

# ------------------------------------------------------------
# CONSTANT TABLES
# ------------------------------------------------------------
tarife_oranlari = {
    "Betonarme": [3.13,2.63,2.38,1.94,1.38,1.06,0.75],
    "Diğer":     [6.13,5.56,3.75,2.00,1.56,1.24,1.06]
}
car_tarife = {
    "A": [1.56,1.31,1.19,0.98,0.69,0.54,0.38],
    "B": [3.06,2.79,1.88,1.00,0.79,0.63,0.54]
}
sure_carpani = {i: sure_carpani_tablosu[i] for i in sure_carpani_tablosu}
koasurans_indirimi = {k:v for k,v in koasurans_indirimi.items() if k in ["80/20","75/25","70/30","65/35","60/40"]}
muafiyet_indirimi = {2:0,3:0.06,4:0.13,5:0.19,10:0.35}

# ------------------------------------------------------------
# CALCULATION FUNCTIONS
# ------------------------------------------------------------
def calculate_duration(months):
    if months <= 36:
        return sure_carpani.get(months,1.0)
    return sure_carpani[36]*(1+0.03*(months-36))

def calculate_fire_premium(building_type,risk,pd,bi,fx_rate):
    pd_tl,bi_tl = pd*fx_rate, bi*fx_rate
    rate=tarife_oranlari[building_type][risk-1];LIMIT=3_500_000_000
    if pd_tl>LIMIT: pd_tl=LIMIT; st.warning(tr("limit_warning_fire"))
    if bi_tl>LIMIT: bi_tl=LIMIT; st.warning(tr("limit_warning_fire"))
    pd_pr,bi_pr = pd_tl*rate/1000, bi_tl*rate/1000
    return pd_pr,bi_pr,pd_pr+bi_pr,rate

def calculate_car_prem(rc,rz,sd,ed,prj,cpm,cpe,ko,de,fx_rate):
    # Duration
    mo=(ed.year-sd.year)*12+(ed.month-sd.month)+(1 if ed.day>=15 else 0)
    dm=calculate_duration(mo)
    # Base rate
    br=car_tarife[rc][rz-1]
    # Rate after discounts
    rr=br*dm*(1-koasurans_indirimi[ko])*(1-muafiyet_indirimi[de])
    LIMIT=840_000_000
    # CAR
    car_tl=min(prj*fx_rate,LIMIT); car_pr=car_tl*rr/1000
    # CPE
    cpe_tl=min(cpe*fx_rate,LIMIT); cpe_pr=cpe_tl*(br*dm)/1000
    # CPM
    cpm_tl=min(cpm*fx_rate,LIMIT)
    cp_rate=2 if cpm_tl<=LIMIT else 2*LIMIT/cpm_tl
    days=(ed-sd).days; cpm_pr=cpm_tl*cp_rate/1000*days/365
    return car_pr,cpe_pr,cpm_pr,car_pr+cpe_pr+cpm_pr,rr

# ------------------------------------------------------------
# UI RENDERING
# ------------------------------------------------------------
st.markdown(f'<h1 class="main-title">🏷️ {tr("title")}</h1>',unsafe_allow_html=True)
st.markdown(f'<h3 class="subtitle">{tr("subtitle")}</h3>',unsafe_allow_html=True)
st.markdown('<p class="founders">Founders: Ubeydullah Ayvaz & Furkan Kaymaz</p>',unsafe_allow_html=True)

type_sel = st.selectbox(tr("select_calc"),[tr("calc_fire"),tr("calc_car")])

if type_sel==tr("calc_fire"):
    st.markdown(f'<h3 class="section-header">{tr("fire_header")}</h3>',unsafe_allow_html=True)
    col1,col2=st.columns(2)
    with col1:
        bld=st.selectbox(tr("building_type"),["Betonarme","Diğer"]) ; rg=st.selectbox(tr("risk_group"),range(1,8))
        cur=st.selectbox(tr("currency"),["TRY","USD","EUR"])
    with col2:
        fx,info=fx_input(cur,"fire")
        st.info(info)
    pd=st.number_input(tr("pd"),min_value=0.0) ; bi=st.number_input(tr("bi"),min_value=0.0)
    st.columns(2)[0].selectbox(tr("koas"),list(koasurans_indirimi.keys()))
    st.columns(2)[1].selectbox(tr("deduct"),list(muafiyet_indirimi.keys()))
    if st.button(tr("btn_calc")):
        pd_pr,bi_pr,tot_pr,ar=calculate_fire_premium(bld,rg,pd,bi,fx)
        if cur!="TRY":
            st.info(f"{tr('pd_premium')}: {pd_pr/fx:.2f} {cur}")
            st.info(f"{tr('bi_premium')}: {bi_pr/fx:.2f} {cur}")
            st.info(f"{tr('total_premium')}: {tot_pr/fx:.2f} {cur}")
        else:
            st.info(f"{tr('pd_premium')}: {pd_pr:,.2f} TL")
            st.info(f"{tr('bi_premium')}: {bi_pr:,.2f} TL")
            st.info(f"{tr('total_premium')}: {tot_pr:,.2f} TL")
        st.info(f"📊 {tr('applied_rate')}: {ar:.2f}‰")
else:
    st.markdown(f'<h3 class="section-header">{tr("car_header")}</h3>',unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        rc=st.selectbox(tr("risk_class"),["A","B"]) ; rz=st.selectbox(tr("risk_group"),range(1,8))
        sd=st.date_input(tr("start")) ; ed=st.date_input(tr("end"))
    with c2:
        cur=st.selectbox(tr("currency"),["TRY","USD","EUR"])
        fx,info=fx_input(cur,"car") ; st.info(info)
    prj=st.number_input(tr("project"),min_value=0.0) ; cpm=st.number_input(tr("cpm"),min_value=0.0) ; cpe=st.number_input(tr("cpe"),min_value=0.0)
    ko=st.selectbox(tr("coins"),list(koasurans_indirimi.keys()))
    de=st.selectbox(tr("ded"),list(muafiyet_indirimi.keys()))
    if st.button(tr("btn_calc")):
        car_pr,cpe_pr,cpm_pr,tot_pr,ar=calculate_car_prem(rc,rz,sd,ed,prj,cpm,cpe,ko,de,fx)
        if cur!="TRY":
            st.info(f"{tr('car_premium')}: {car_pr/fx:.2f} {cur}")
            st.info(f"{tr('cpe_premium')}: {cpe_pr/fx:.2f} {cur}")
            st.info(f"{tr('cpm_premium')}: {cpm_pr/fx:.2f} {cur}")
            st.info(f"{tr('total_premium')}: {tot_pr/fx:.2f} {cur}")
        else:
            st.info(f"{tr('car_premium')}: {car_pr:,.2f} TL")
            st.info(f"{tr('cpe_premium')}: {cpe_pr:,.2f} TL")
            st.info(f"{tr('cpm_premium')}: {cpm_pr:,.2f} TL")
            st.info(f"{tr('total_premium')}: {tot_pr:,.2f} TL")
        st.info(f"📊 {tr('applied_rate')}: {ar:.2f}‰")
