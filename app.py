import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# ------------------------------------------------------------
# STREAMLIT CONFIG (must be first)
# ------------------------------------------------------------
st.set_page_config(page_title="TarifeX", layout="centered")

# Custom CSS for styling
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

# Language dictionary with full English translation
T = {
    "title": {"TR": "TarifeX – Akıllı Sigorta Prim Hesaplama Uygulaması", "EN": "TarifeX – Smart Insurance Premium Calculator"},
    "subtitle": {"TR": "Deprem ve Yanardağ Püskürmesi Teminatı için Uygulanacak Güncel Tarife", "EN": "Current Tariff for Earthquake and Volcanic Eruption Coverage"},
    "fire_header": {"TR": "🔥 Yangın Sigortası Hesaplama", "EN": "🔥 Fire Insurance Calculation"},
    "car_header": {"TR": "🏗️ İnşaat & Montaj Hesaplama", "EN": "🏗️ Construction & Erection Calculation"},
    "select_calc": {"TR": "Hesaplama Türünü Seçin", "EN": "Select Calculation Type"},
    "calc_fire": {"TR": "Yangın Sigortası - Ticari Sınai Rizikolar (PD & BI)", "EN": "Fire Insurance – Commercial / Industrial (PD & BI)"},
    "calc_car": {"TR": "İnşaat & Montaj (CAR & EAR)", "EN": "Construction & Erection (CAR & EAR)"},
    "building_type": {"TR": "Yapı Tarzı", "EN": "Construction Type"},
    "building_type_help": {"TR": "Betonarme: Çelik veya betonarme taşıyıcı karkas bulunan yapılar. Diğer: Bu gruba girmeyen yapılar.", "EN": "Concrete: Structures with steel or reinforced concrete framework. Other: Structures not in this group."},
    "risk_group": {"TR": "Deprem Risk Grubu (1=En Yüksek Risk)", "EN": "Earthquake Risk Zone (1=Highest)"},
    "risk_group_help": {"TR": "Deprem risk grupları, Doğal Afet Sigortaları Kurumu tarafından belirlenir. 1. Grup en yüksek risktir.", "EN": "Earthquake risk zones are determined by the Natural Disaster Insurance Institution. Zone 1 is the highest risk."},
    "currency": {"TR": "Para Birimi", "EN": "Currency"},
    "manual_fx": {"TR": "Kuru manuel güncelleyebilirsiniz", "EN": "You can manually update the exchange rate"},
    "pd": {"TR": "Yangın Sigorta Bedeli (PD)", "EN": "Property Damage Sum Insured (PD)"},
    "pd_help": {"TR": "Bina ve muhteviyat için yangın sigorta bedeli. Betonarme binalar için birim metrekare fiyatı min. 18,600 TL, diğerleri için 12,600 TL.", "EN": "Fire insurance sum for building and contents. Min. unit square meter price for concrete buildings: 18,600 TL; others: 12,600 TL."},
    "bi": {"TR": "Kar Kaybı Bedeli (BI)", "EN": "Business Interruption Sum Insured (BI)"},
    "bi_help": {"TR": "Deprem sonrası ticari faaliyetin durması sonucu ciro azalması ve maliyet artışından kaynaklanan brüt kâr kaybı.", "EN": "Gross profit loss due to reduced turnover and increased costs from business interruption after an earthquake."},
    "ymm": {"TR": "Yangın Mali Mesuliyet Bedeli (YMM)", "EN": "Third‑Party Liability Sum Insured"},
    "ymm_help": {"TR": "Üçüncü şahıslara karşı mali sorumluluk teminatı bedeli.", "EN": "Sum insured for third-party liability coverage."},
    "debris": {"TR": "Enkaz Kaldırma Bedeli", "EN": "Debris Removal Sum Insured"},
    "debris_help": {"TR": "Deprem sonrası enkaz kaldırma masrafları için teminat bedeli.", "EN": "Sum insured for debris removal costs after an earthquake."},
    "koas": {"TR": "Koasürans Oranı", "EN": "Coinsurance Share"},
    "koas_help": {"TR": "Sigortalının hasara iştirak oranı. Min. %20 sigortalı üzerinde kalır. %60’a kadar artırılabilir (max. %50 indirim).", "EN": "Insured's share in the loss. Min. 20% remains with the insured. Can be increased to 60% (max. 50% discount)."},
    "deduct": {"TR": "Muafiyet Oranı (%)", "EN": "Deductible (%)"},
    "deduct_help": {"TR": "Her hasarda bina sigorta bedeli üzerinden uygulanır. Min. %2, artırılabilir (max. %35 indirim).", "EN": "Applied per loss on the building sum insured. Min. 2%, can be increased (max. 35% discount)."},
    "btn_calc": {"TR": "Hesapla", "EN": "Calculate"},
    "min_premium": {"TR": "Minimum Deprem Primi", "EN": "Minimum Earthquake Premium"},
    "applied_rate": {"TR": "Uygulanan Oran %", "EN": "Applied Rate %"},
    "risk_class": {"TR": "Risk Sınıfı", "EN": "Risk Class"},
    "risk_class_help": {"TR": "A: Bina inşaatları, dekorasyon. B: Tünel, köprü, enerji santralleri gibi daha riskli projeler.", "EN": "A: Building construction, decoration. B: Tunnels, bridges, power plants, and other high-risk projects."},
    "start": {"TR": "Poliçe Başlangıcı", "EN": "Policy Start"},
    "end": {"TR": "Poliçe Bitişi", "EN": "Policy End"},
    "duration": {"TR": "Süre", "EN": "Duration"},
    "months": {"TR": "ay", "EN": "months"},
    "duration_help": {"TR": "Sigorta süresi. 36 aydan uzun projelerde her ay için %3 eklenir.", "EN": "Policy duration. For projects over 36 months, 3% is added per month."},
    "coins": {"TR": "Koasürans", "EN": "Coinsurance"},
    "coins_help": {"TR": "Sigortalının hasara iştirak oranı. Min. %20 sigortalı üzerinde kalır. %60’a kadar artırılabilir (max. %50 indirim).", "EN": "Insured's share in the loss. Min. 20% remains with the insured. Can be increased to 60% (max. 50% discount)."},
    "ded": {"TR": "Muafiyet (%)", "EN": "Deductible (%)"},
    "ded_help": {"TR": "Her hasarda sigorta bedeli üzerinden uygulanır. Min. %2, artırılabilir (max. %35 indirim).", "EN": "Applied per loss on the sum insured. Min. 2%, can be increased (max. 35% discount)."},
    "project": {"TR": "Proje Bedeli (CAR)", "EN": "Project Sum Insured (CAR)"},
    "project_help": {"TR": "Proje nihai değeri (gümrük, vergi, nakliye ve işçilik dahil). Min. sözleşme bedeli kadar olmalı.", "EN": "Final project value (including customs, taxes, transport, and labor). Must be at least the contract value."},
    "cpm": {"TR": "İnşaat Makineleri (CPM)", "EN": "Construction Machinery (CPM)"},
    "cpm_help": {"TR": "İnşaat makineleri için teminat bedeli. Aynı riziko adresinde kullanılmalı.", "EN": "Sum insured for construction machinery. Must be used at the same risk address."},
    "cpe": {"TR": "Şantiye Tesisleri (CPE)", "EN": "Site Facilities (CPE)"},
    "cpe_help": {"TR": "Şantiye tesisleri için teminat bedeli. Aynı riziko adresinde bulunmalı.", "EN": "Sum insured for site facilities. Must be at the same risk address."},
    "total_premium": {"TR": "Toplam Minimum Prim", "EN": "Total Minimum Premium"},
    "limit_warning": {"TR": "⚠️ Toplam sigorta bedeli 850 milyon TRY limitini aşıyor. Prim hesaplama bu limite göre yapılır.", "EN": "⚠️ Total sum insured exceeds the 850 million TRY limit. Premium calculation will be based on this limit."}
}

def tr(key: str) -> str:
    return T[key][lang]

# ------------------------------------------------------------
# 1) TCMB FX MODULE
# ------------------------------------------------------------
@st.cache_data(ttl=3600)
def get_tcmb_rate(ccy: str):
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
    r_key = f"{key_prefix}_{ccy}_rate"
    s_key = f"{key_prefix}_{ccy}_src"
    d_key = f"{key_prefix}_{ccy}_dt"
    if r_key not in st.session_state:
        rate, dt = get_tcmb_rate(ccy)
        if rate is None:
            st.session_state.update({r_key: 0.0, s_key: "MANUEL", d_key: "-"})
        else:
            st.session_state.update({r_key: rate, s_key: "TCMB", d_key: dt})
    st.info(f"💱 1 {ccy} = {st.session_state[r_key]:,.4f} TL ({st.session_state[s_key]}, {st.session_state[d_key]})")
    st.session_state[r_key] = st.number_input(tr("manual_fx"), value=float(st.session_state[r_key]), step=0.0001, format="%.4f", key=f"{key_prefix}_{ccy}_manual")
    return st.session_state[r_key]

# ------------------------------------------------------------
# 2) CONSTANT TABLES
# ------------------------------------------------------------
tarife_oranlari = {
    "Betonarme": [3.13, 2.63, 2.38, 1.94, 1.38, 1.06, 0.75],
    "Diğer": [6.13, 5.56, 3.75, 2.00, 1.56, 1.24, 1.06]
}
koasurans_indirimi = {
    "80/20": 0.0, "75/25": 0.0625, "70/30": 0.125, "65/35": 0.1875, 
    "60/40": 0.25, "55/45": 0.3125, "50/50": 0.375, "45/55": 0.4375, 
    "40/60": 0.5, "30/70": 0.125, "25/75": 0.0625
}
muafiyet_indirimi = {2: 0.0, 3: 0.06, 4: 0.13, 5: 0.19, 10: 0.35}
sure_carpani_tablosu = {
    6: 0.70, 7: 0.75, 8: 0.80, 9: 0.85, 10: 0.90, 11: 0.95, 12: 1.00, 
    13: 1.05, 14: 1.10, 15: 1.15, 16: 1.20, 17: 1.25, 18: 1.30, 
    19: 1.35, 20: 1.40, 21: 1.45, 22: 1.50, 23: 1.55, 24: 1.60, 
    25: 1.65, 26: 1.70, 27: 1.74, 28: 1.78, 29: 1.82, 30: 1.86, 
    31: 1.90, 32: 1.94, 33: 1.98, 34: 2.02, 35: 2.06, 36: 2.10
}

# ------------------------------------------------------------
# 3) CALCULATION LOGIC
# ------------------------------------------------------------
def calculate_duration_multiplier(months: int) -> float:
    if months <= 36:
        return sure_carpani_tablosu.get(months, 1.0)
    base = sure_carpani_tablosu[36]
    extra_months = months - 36
    return base * (1 + 0.03 * extra_months)

def calculate_fire_premium(building_type, risk_group, currency, pd, bi, ymm, debris, koas, deduct, fx_rate):
    total_sum_insured = (pd + bi + ymm + debris) * fx_rate
    if total_sum_insured > 850_000_000:
        st.warning(tr("limit_warning"))
        total_sum_insured = 850_000_000
    
    rate = tarife_oranlari[building_type][risk_group - 1]
    koas_discount = koasurans_indirimi[koas]
    deduct_discount = muafiyet_indirimi[deduct]
    
    final_rate = rate * (1 - koas_discount) * (1 - deduct_discount)
    premium = (total_sum_insured * final_rate) / 100
    
    return premium, final_rate

def calculate_car_ear_premium(risk_class, duration_months, project, cpm, cpe, currency, koas, deduct, fx_rate):
    total_sum_insured = (project + cpm + cpe) * fx_rate
    if total_sum_insured > 850_000_000:
        st.warning(tr("limit_warning"))
        total_sum_insured = 850_000_000
    
    base_rate = tarife_oranlari["Betonarme"][risk_class - 1]
    duration_multiplier = calculate_duration_multiplier(duration_months)
    koas_discount = koasurans_indirimi[koas]
    deduct_discount = muafiyet_indirimi[deduct]
    
    final_rate = base_rate * duration_multiplier * (1 - koas_discount) * (1 - deduct_discount)
    premium = (total_sum_insured * final_rate) / 100
    
    return premium, final_rate

# ------------------------------------------------------------
# 4) STREAMLIT UI
# ------------------------------------------------------------
# Header with Image
st.markdown(f'<h1 class="main-title">🏷️ {tr("title")}</h1>', unsafe_allow_html=True)
st.markdown(f'<h3 class="subtitle">{tr("subtitle")}</h3>', unsafe_allow_html=True)
st.markdown('<p class="founders">Founders: Ubeydullah Ayvaz & Furkan Kaymaz</p>', unsafe_allow_html=True)

# Imgur'dan alınan yeni doğrudan resim URL'si
st.image("https://i.imgur.com/iA8pLRD.jpg", caption=tr("title"))

# Main Content
st.markdown('<h2 class="section-header">📌 ' + ("Hesaplama Yap" if lang == "TR" else "Perform Calculation") + '</h2>', unsafe_allow_html=True)
calc_type = st.selectbox(tr("select_calc"), [tr("calc_fire"), tr("calc_car")], help="Hesaplama türünü seçerek başlayın." if lang == "TR" else "Start by selecting the calculation type.")

if calc_type == tr("calc_fire"):
    st.markdown(f'<h3 class="section-header">{tr("fire_header")}</h3>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        building_type = st.selectbox(tr("building_type"), ["Betonarme", "Diğer"], help=tr("building_type_help"))
        risk_group = st.selectbox(tr("risk_group"), [1, 2, 3, 4, 5, 6, 7], help=tr("risk_group_help"))
        currency = st.selectbox(tr("currency"), ["TRY", "USD", "EUR"])
    with col2:
        fx_rate = fx_input(currency, "fire")
    
    st.markdown("### " + ("Sigorta Bedelleri" if lang == "TR" else "Sums Insured"))
    col3, col4 = st.columns(2)
    with col3:
        pd = st.number_input(tr("pd"), min_value=0.0, value=0.0, step=1000.0, help=tr("pd_help"))
        bi = st.number_input(tr("bi"), min_value=0.0, value=0.0, step=1000.0, help=tr("bi_help"))
    with col4:
        ymm = st.number_input(tr("ymm"), min_value=0.0, value=0.0, step=1000.0, help=tr("ymm_help"))
        debris = st.number_input(tr("debris"), min_value=0.0, value=0.0, step=1000.0, help=tr("debris_help"))
    
    st.markdown("### " + ("İndirim Oranları" if lang == "TR" else "Discount Rates"))
    col5, col6 = st.columns(2)
    with col5:
        koas = st.selectbox(tr("koas"), list(koasurans_indirimi.keys()), help=tr("koas_help"))
    with col6:
        deduct = st.selectbox(tr("deduct"), list(muafiyet_indirimi.keys()), help=tr("deduct_help"))
    
    if st.button(tr("btn_calc"), key="fire_calc"):
        premium, applied_rate = calculate_fire_premium(building_type, risk_group, currency, pd, bi, ymm, debris, koas, deduct, fx_rate)
        st.markdown(f'<div class="info-box">✅ <b>{tr("min_premium")}:</b> {premium:,.2f} TRY</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="info-box">📊 <b>{tr("applied_rate")}:</b> {applied_rate:.2f}%</div>', unsafe_allow_html=True)

else:
    st.markdown(f'<h3 class="section-header">{tr("car_header")}</h3>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        risk_class = st.selectbox(tr("risk_class"), [1, 2, 3, 4, 5, 6, 7], help=tr("risk_class_help"))
        start_date = st.date_input(tr("start"), value=datetime.today())
        end_date = st.date_input(tr("end"), value=datetime.today() + timedelta(days=365))
    with col2:
        duration_months = max(1, (end_date.year - start_date.year) * 12 + end_date.month - start_date.month)
        st.write(f"⏳ {tr('duration')}: {duration_months} {tr('months')}", help=tr("duration_help"))
        currency = st.selectbox(tr("currency"), ["TRY", "USD", "EUR"])
        fx_rate = fx_input(currency, "car")
    
    st.markdown("### " + ("Sigorta Bedelleri" if lang == "TR" else "Sums Insured"))
    col3, col4, col5 = st.columns(3)
    with col3:
        project = st.number_input(tr("project"), min_value=0.0, value=0.0, step=1000.0, help=tr("project_help"))
    with col4:
        cpm = st.number_input(tr("cpm"), min_value=0.0, value=0.0, step=1000.0, help=tr("cpm_help"))
    with col5:
        cpe = st.number_input(tr("cpe"), min_value=0.0, value=0.0, step=1000.0, help=tr("cpe_help"))
    
    st.markdown("### " + ("İndirim Oranları" if lang == "TR" else "Discount Rates"))
    col6, col7 = st.columns(2)
    with col6:
        koas = st.selectbox(tr("coins"), list(koasurans_indirimi.keys()), help=tr("coins_help"))
    with col7:
        deduct = st.selectbox(tr("ded"), list(muafiyet_indirimi.keys()), help=tr("ded_help"))
    
    if st.button(tr("btn_calc"), key="car_calc"):
        premium, applied_rate = calculate_car_ear_premium(risk_class, duration_months, project, cpm, cpe, currency, koas, deduct, fx_rate)
        st.markdown(f'<div class="info-box">✅ <b>{tr("total_premium")}:</b> {premium:,.2f} TRY</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="info-box">📊 <b>{tr("applied_rate")}:</b> {applied_rate:.2f}%</div>', unsafe_allow_html=True)

# Footer removed as per previous request
