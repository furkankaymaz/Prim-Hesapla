```python
import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# ------------------------------------------------------------
# STREAMLIT CONFIG (must be first)
# ------------------------------------------------------------
st.set_page_config(page_title="TarifeX", layout="centered")

# ------------------------------------------------------------
# CUSTOM CSS FOR STYLING
# ------------------------------------------------------------
st.markdown("""
<style>
    .main-title {
        font-size: 2.5em;
        color: #2E86C1;
        text-align: center;
        margin-bottom: 0.5em;
    }
    .subtitle {
        font-size: 1.2em;
        color: #5DADE2;
        text-align: center;
        margin-bottom: 0.5em;
    }
    .founders {
        font-size: 1em;
        color: #1A5276;
        text-align: center;
        margin-bottom: 1em;
    }
    .section-header {
        font-size: 1.5em;
        color: #1A5276;
        margin-top: 1em;
        margin-bottom: 0.5em;
    }
    .stButton>button {
        background-color: #2E86C1;
        color: white;
        border-radius: 10px;
        padding: 0.5em 1em;
    }
    .stButton>button:hover {
        background-color: #1A5276;
        color: white;
    }
    .lang-selector {
        position: fixed;
        top: 10px;
        right: 10px;
        z-index: 999;
    }
    .info-box {
        background-color: #F0F8FF;
        padding: 1em;
        border-radius: 10px;
        margin-bottom: 1em;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# 0) LANGUAGE SELECTOR (TR / EN) - Top Right
# ------------------------------------------------------------
with st.container():
    st.markdown('<div class="lang-selector">', unsafe_allow_html=True)
    lang = st.radio("🌐", ["TR", "EN"], index=0, horizontal=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------------------------
# LANGUAGE DICTIONARY
# ------------------------------------------------------------
T = {
    # ... (same as original for fire + common labels) ...
}

# Add entries for tarife_oranlari for CAR & EAR
# ------------------------------------------------------------
TARIFF = {
    "A": [1.56, 1.31, 1.19, 0.98, 0.69, 0.54, 0.38],
    "B": [3.06, 2.79, 1.88, 1.00, 0.79, 0.63, 0.54]
}

# ------------------------------------------------------------
# FX MODULE (same as original)
# ------------------------------------------------------------
@st.cache_data(ttl=3600)
def get_tcmb_rate(ccy: str):
    # ... unchanged ...
    return None, None

def fx_input(ccy: str, key_prefix: str) -> tuple:
    # ... unchanged ...
    return 1.0, ""

# ------------------------------------------------------------
# CONSTANT TABLES (fire and general)
# ------------------------------------------------------------
# ... original tarife_oranlari, koasurans_indirimi, muafiyet_indirimi, sure_carpani_tablosu ...

# ------------------------------------------------------------
# CALCULATION LOGIC
# ------------------------------------------------------------
def calculate_duration_multiplier(days: int, start: datetime, end: datetime) -> float:
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day >= 15:
        months += 1
    if months <= 36:
        return sure_carpani_tablosu.get(months, 1.0)
    extra = months - 36
    return sure_carpani_tablosu[36] * (1 + 0.03 * extra)

# Fire premium unchanged

def calculate_car_cpm_cpe(risk_type, region, start, end, project, cpm, cpe, koas, deduct, fx_rate):
    # Convert to TRY
    p_try = project * fx_rate
    cpm_try = cpm * fx_rate
    cpe_try = cpe * fx_rate
    
    # Duration factor
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day >= 15:
        months += 1
    duration_factor = calculate_duration_multiplier(months, start, end)

    # Discounts
    koas_d = koasurans_indirimi[koas]
    ded_d = muafiyet_indirimi[deduct]

    # Limits
    LIMIT = 840_000_000

    # CAR Rate and Premium
    base = TARIFF[risk_type][region-1]
    rate_car = base * duration_factor * (1-koas_d) * (1-ded_d)
    if p_try * duration_factor < LIMIT:
        pass
    else:
        rate_car *= LIMIT / (p_try * duration_factor)
    prem_car = p_try * rate_car / 1000

    # CPM Rate and Premium
    rate_cpm = 2.0
    if cpm_try * duration_factor < LIMIT:
        pass
    else:
        rate_cpm = 2 * LIMIT / (cpm_try * duration_factor)
    prem_cpm = cpm_try * rate_cpm / 1000 * ((end - start).days/365)

    # CPE Rate and Premium
    rate_cpe = base * duration_factor
    if cpe_try * duration_factor < LIMIT:
        pass
    else:
        rate_cpe *= LIMIT / (cpe_try * duration_factor)
    prem_cpe = cpe_try * rate_cpe / 1000

    # Total
    total = prem_car + prem_cpm + prem_cpe
    return prem_car, prem_cpm, prem_cpe, total, rate_car, rate_cpm, rate_cpe

# ------------------------------------------------------------
# UI LAYOUT
# ------------------------------------------------------------
# Header
st.markdown(f"<h1 class='main-title'>🏷️ {tr('title')}</h1>", unsafe_allow_html=True)
st.markdown(f"<h3 class='subtitle'>{tr('subtitle')}</h3>", unsafe_allow_html=True)
st.markdown('<p class="founders">Founders: Ubeydullah Ayvaz & Furkan Kaymaz</p>', unsafe_allow_html=True)

# Image
st.image("https://i.imgur.com/iA8pLRD.jpg", caption=tr('title'))

# Selection
st.markdown(f"<h2 class='section-header'>📌 {tr('select_calc')}</h2>", unsafe_allow_html=True)
choice = st.selectbox("", [tr('calc_fire'), tr('calc_car')])

# Fire Section (unchanged)
if choice == tr('calc_fire'):
    # ... original fire UI and calculation ...
    pass

# Car & Ear Section
else:
    st.markdown(f"<h3 class='section-header'>{tr('car_header')}</h3>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        risk_type = st.selectbox(tr('risk_class'), ['A','B'], help=tr('risk_class_help'))
        region = st.selectbox(tr('risk_group'), list(range(1,8)), help=tr('risk_group_help'))
        start = st.date_input(tr('start'), datetime.today())
        end = st.date_input(tr('end'), datetime.today()+timedelta(days=365))
    with col2:
        st.write(f"⏳ {tr('duration')}: { (end-start).days//30 } {tr('months')} ")
        currency = st.selectbox(tr('currency'), ['TRY','USD','EUR'])
        fx_rate, fx_info = fx_input(currency, 'car')
        if currency!='TRY': st.info(fx_info)

    st.markdown("### " + tr('project'))
    proj = st.number_input(tr('project'), 0.0, step=1000.0, help=tr('project_help'))
    st.markdown("### " + tr('cpm'))
    cpm = st.number_input(tr('cpm'), 0.0, step=1000.0, help=tr('cpm_help'))
    st.markdown("### " + tr('cpe'))
    cpe = st.number_input(tr('cpe'), 0.0, step=1000.0, help=tr('cpe_help'))

    st.markdown("### " + tr('coins'))
    koas = st.selectbox(tr('coins'), list(koasurans_indirimi.keys()), help=tr('coins_help'))
    st.markdown("### " + tr('ded'))
    deduct = st.selectbox(tr('ded'), list(muafiyet_indirimi.keys()), help=tr('ded_help'))

    if st.button(tr('btn_calc')):
        car_p, cpm_p, cpe_p, tot_p, rc, rcpm, rcpe = calculate_car_cpm_cpe(risk_type, region, start, end, proj, cpm, cpe, koas, deduct, fx_rate)
        # Display
        def disp(val, rate, label):
            if currency!='TRY':
                val_, rate_ = val/fx_rate, rate
                st.markdown(f"<div class='info-box'>✅ <b>{label}:</b> {format_number(val_,currency)} (@ {rate_:.2f}‰)</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='info-box'>✅ <b>{label}:</b> {format_number(val,'TRY')} (@ {rate:.2f}‰)</div>", unsafe_allow_html=True)
        disp(car_p, rc, tr('project') + ' Primi')
        disp(cpm_p, rcpm, tr('cpm') + ' Primi')
        disp(cpe_p, rcpe, tr('cpe') + ' Primi')
        # Total
        if currency!='TRY': tot_=tot_p/fx_rate; cur=currency
        else: tot_=tot_p; cur='TRY'
        st.markdown(f"<div class='info-box'>🎯 <b>{tr('total_premium')}:</b> {format_number(tot_,cur)}</div>", unsafe_allow_html=True)
```
