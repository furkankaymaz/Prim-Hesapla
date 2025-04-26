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
    "risk_group_type": {"TR": "Risk Sınıfı Türü", "EN": "Risk Group Type"},
    "risk_group_type_help": {"TR": "A: Bina inşaatları, dekorasyon. B: Tünel, köprü, enerji santralleri gibi daha riskli projeler.", "EN": "A: Building construction, decoration. B: Tunnels, bridges, power plants, and other high-risk projects."},
    "currency": {"TR": "Para Birimi", "EN": "Currency"},
    "manual_fx": {"TR": "Kuru manuel güncelleyebilirsiniz", "EN": "You can manually update the exchange rate"},
    "pd": {"TR": "Yangın Sigorta Bedeli (PD)", "EN": "Property Damage Sum Insured (PD)"},
    "pd_help": {"TR": "Bina ve muhteviyat için yangın sigorta bedeli. Betonarme binalar için birim metrekare fiyatı min. 18,600 TL, diğerleri için 12,600 TL.", "EN": "Fire insurance sum for building and contents. Min. unit square meter price for concrete buildings: 18,600 TL; others: 12,600 TL."},
    "bi": {"TR": "Kar Kaybı Bedeli (BI)", "EN": "Business Interruption Sum Insured (BI)"},
    "bi_help": {"TR": "Deprem sonrası ticari faaliyetin durması sonucu ciro azalması ve maliyet artışından kaynaklanan brüt kâr kaybı.", "EN": "Gross profit loss due to reduced turnover and increased costs from business interruption after an earthquake."},
    "koas": {"TR": "Koasürans Oranı", "EN": "Coinsurance Share"},
    "koas_help": {"TR": "Sigortalının hasara iştirak oranı. Min. %20 sigortalı üzerinde kalır. %60’a kadar artırılabilir (max. %50 indirim).", "EN": "Insured's share in the loss. Min. 20% remains with the insured. Can be increased to 60% (max. 50% discount)."},
    "deduct": {"TR": "Muafiyet Oranı (%)", "EN": "Deductible (%)"},
    "deduct_help": {"TR": "Her hasarda bina sigorta bedeli üzerinden uygulanır. Min. %2, artırılabilir (max. %35 indirim).", "EN": "Applied per loss on the building sum insured. Min. 2%, can be increased (max. 35% discount)."},
    "btn_calc": {"TR": "Hesapla", "EN": "Calculate"},
    "min_premium": {"TR": "Minimum Deprem Primi", "EN": "Minimum Earthquake Premium"},
    "applied_rate": {"TR": "Uygulanan Oran (binde)", "EN": "Applied Rate (per mille)"},
    "risk_class": {"TR": "Deprem Risk Grubu (1=En Yüksek Risk)", "EN": "Earthquake Risk Zone (1=Highest)"},
    "risk_class_help": {"TR": "Deprem risk grupları, Doğal Afet Sigortaları Kurumu tarafından belirlenir. 1. Grup en yüksek risktir.", "EN": "Earthquake risk zones are determined by the Natural Disaster Insurance Institution. Zone 1 is the highest risk."},
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
    "car_premium": {"TR": "CAR Primi", "EN": "CAR Premium"},
    "cpm_premium": {"TR": "CPM Primi", "EN": "CPM Premium"},
    "cpe_premium": {"TR": "CPE Primi", "EN": "CPE Premium"},
    "limit_warning_fire": {"TR": "⚠️ Yangın Sigortası: Toplam sigorta bedeli 3.5 milyar TRY limitini aşıyor. Prim hesaplama bu limite göre yapılır.", "EN": "⚠️ Fire Insurance: Total sum insured exceeds the 3.5 billion TRY limit. Premium calculation will be based on this limit."},
    "limit_warning_car": {"TR": "⚠️ İnşaat & Montaj: Toplam sigorta bedeli 840 milyon TRY limitini aşıyor. Prim hesaplama bu limite göre yapılır.", "EN": "⚠️ Construction & Erection: Total sum insured exceeds the 840 million TRY limit. Premium calculation will be based on this limit."},
    "entered_value": {"TR": "Girilen Değer", "EN": "Entered Value"},
    "pd_premium": {"TR": "PD Primi", "EN": "PD Premium"},
    "bi_premium": {"TR": "BI Primi", "EN": "BI Premium"}
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
        return 1.0, ""
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
    return st.session_state[r_key], f"💱 1 {ccy} = {st.session_state[r_key]:,.4f} TL ({st.session_state[s_key]}, {st.session_state[d_key]})"

# Helper function to format numbers with thousand separators
def format_number(value: float, currency: str) -> str:
    formatted_value = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{formatted_value} {currency}"

# ------------------------------------------------------------
# 2) CONSTANT TABLES
# ------------------------------------------------------------
tarife_oranlari = {
    "Betonarme": [3.13, 2.63, 2.38, 1.94, 1.38, 1.06, 0.75],
    "Diğer": [6.13, 5.56, 3.75, 2.00, 1.56, 1.24, 1.06],
    "RiskGrubuA": [1.56, 1.31, 1.19, 0.98, 0.69, 0.54, 0.38],
    "RiskGrubuB": [3.06, 2.79, 1.88, 1.00, 0.79, 0.63, 0.54]
}
koasurans_indirimi = {
    "80/20": 0.0, "75/25": 0.0625, "70/30": 0.125, "65/35": 0.1875,
    "60/40": 0.25, "55/45": 0.3125, "50/50": 0.375, "45/55": 0.4375,
    "40/60": 0.25, "30/70": 0.125, "25/75": 0.0625,
    "90/10": -0.125, "100/0": -0.25
}
koasurans_indirimi_car = {
    "80/20": 0.0, "75/25": 0.0625, "70/30": 0.125, "65/35": 0.1875,
    "60/40": 0.25, "55/45": 0.3125, "50/50": 0.375, "45/55": 0.4375,
    "40/60": 0.25
}
muafiyet_indirimi = {
    2: 0.0, 3: 0.06, 4: 0.13, 5: 0.19, 10: 0.35,
    0.1: -0.12, 0.5: -0.09, 1: -0.06, 1.5: -0.03
}
muafiyet_indirimi_car = {
    2: 0.0, 3: 0.06, 4: 0.13, 5: 0.19, 10: 0.35
}
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

def calculate_fire_premium(building_type, risk_group, currency, pd, bi, koas, deduct, fx_rate):
    # Convert sums to TRY
    pd_sum_insured = pd * fx_rate
    bi_sum_insured = bi * fx_rate
    
    # Get base tariff rate (per mille)
    rate = tarife_oranlari[building_type][risk_group - 1]
    
    # Limit for premium calculation
    LIMIT = 3_500_000_000  # 3.5 billion TRY
    
    # Calculate adjusted rate for PD (apply discounts first, then limit adjustment)
    koas_discount = koasurans_indirimi[koas]
    deduct_discount = muafiyet_indirimi[deduct]
    adjusted_rate_pd = rate * (1 - koas_discount) * (1 - deduct_discount)
    
    if pd_sum_insured > LIMIT:
        st.warning(tr("limit_warning_fire"))
        adjusted_rate_pd = round(adjusted_rate_pd * (LIMIT / pd_sum_insured), 6)
    
    # Calculate PD premium
    pd_premium = (pd_sum_insured * adjusted_rate_pd) / 1000  # Per mille
    
    # Calculate adjusted rate for BI (no discounts, only limit adjustment)
    adjusted_rate_bi = rate  # No koasürans or muafiyet for BI
    if bi_sum_insured > LIMIT:
        st.warning(tr("limit_warning_fire"))
        adjusted_rate_bi = round(adjusted_rate_bi * (LIMIT / bi_sum_insured), 6)
    
    # Calculate BI premium
    bi_premium = (bi_sum_insured * adjusted_rate_bi) / 1000  # Per mille
    
    # Total premium
    total_premium = pd_premium + bi_premium
    
    return pd_premium, bi_premium, total_premium, rate

def calculate_car_ear_premium(risk_group_type, risk_class, start_date, end_date, project, cpm, cpe, currency, koas, deduct, fx_rate):
    # Calculate duration in months (Excel-style: MONTH(B5)-MONTH(B4)+(YEAR(B5)-YEAR(B4))*12+(DAY(B5)>=15))
    duration_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    if end_date.day >= 15:
        duration_months += 1
    
    # Calculate days for CPM duration factor
    days = (end_date - start_date).days
    duration_factor = days / 365
    
    # Base rate and duration multiplier
    base_rate = tarife_oranlari[risk_group_type][risk_class - 1]
    duration_multiplier = calculate_duration_multiplier(duration_months)
    koas_discount = koasurans_indirimi_car[koas]
    deduct_discount = muafiyet_indirimi_car[deduct]
    
    # Limit for premium calculation
    LIMIT = 840_000_000  # 840 million TRY
    
    # CAR Premium
    project_sum_insured = project * fx_rate
    car_rate = base_rate * duration_multiplier * (1 - koas_discount) * (1 - deduct_discount)
    if project_sum_insured > LIMIT:
        st.warning(tr("limit_warning_car"))
        car_rate *= (LIMIT / project_sum_insured)
    car_premium = (project_sum_insured * car_rate) / 1000
    
    # CPM Premium
    cpm_sum_insured = cpm * fx_rate
    cpm_rate = 2.0  # Default rate is 2 ‰
    if cpm_sum_insured > LIMIT:
        st.warning(tr("limit_warning_car"))
        cpm_rate *= (LIMIT / cpm_sum_insured)
    cpm_premium = (cpm_sum_insured * cpm_rate / 1000) * duration_factor
    
    # CPE Premium
    cpe_sum_insured = cpe * fx_rate
    cpe_rate = base_rate * duration_multiplier  # No koas or deduct discount for CPE
    if cpe_sum_insured > LIMIT:
        st.warning(tr("limit_warning_car"))
        cpe_rate *= (LIMIT / cpe_sum_insured)
    cpe_premium = (cpe_sum_insured * cpe_rate) / 1000
    
    # Total Premium
    total_premium = car_premium + cpm_premium + cpe_premium
    
    return car_premium, cpm_premium, cpe_premium, total_premium, car_rate

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
        fx_rate, fx_info = fx_input(currency, "fire")
    
    st.markdown("### " + ("Sigorta Bedelleri" if lang == "TR" else "Sums Insured"))
    if currency != "TRY":
        st.info(fx_info)
    
    pd = st.number_input(tr("pd"), min_value=0.0, value=0.0, step=1000.0, help=tr("pd_help"))
    if pd > 0:
        st.write(f"{tr('entered_value')}: {format_number(pd, currency)}")
    
    bi = st.number_input(tr("bi"), min_value=0.0, value=0.0, step=1000.0, help=tr("bi_help"))
    if bi > 0:
        st.write(f"{tr('entered_value')}: {format_number(bi, currency)}")
    
    st.markdown("### " + ("İndirim Oranları" if lang == "TR" else "Discount Rates"))
    col5, col6 = st.columns(2)
    with col5:
        koas = st.selectbox(tr("koas"), list(koasurans_indirimi.keys()), help=tr("koas_help"))
    with col6:
        deduct = st.selectbox(tr("deduct"), list(muafiyet_indirimi.keys()), help=tr("deduct_help"))
    
    if st.button(tr("btn_calc"), key="fire_calc"):
        pd_premium, bi_premium, total_premium, applied_rate = calculate_fire_premium(building_type, risk_group, currency, pd, bi, koas, deduct, fx_rate)
        if currency != "TRY":
            pd_premium_converted = pd_premium / fx_rate
            bi_premium_converted = bi_premium / fx_rate
            total_premium_converted = total_premium / fx_rate
            st.markdown(f'<div class="info-box">✅ <b>{tr("pd_premium")}:</b> {format_number(pd_premium_converted, currency)}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="info-box">✅ <b>{tr("bi_premium")}:</b> {format_number(bi_premium_converted, currency)}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="info-box">✅ <b>{tr("total_premium")}:</b> {format_number(total_premium_converted, currency)}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="info-box">✅ <b>{tr("pd_premium")}:</b> {format_number(pd_premium, "TRY")}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="info-box">✅ <b>{tr("bi_premium")}:</b> {format_number(bi_premium, "TRY")}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="info-box">✅ <b>{tr("total_premium")}:</b> {format_number(total_premium, "TRY")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="info-box">📊 <b>{tr("applied_rate")}:</b> {applied_rate:.2f}‰</div>', unsafe_allow_html=True)

else:
    st.markdown(f'<h3 class="section-header">{tr("car_header")}</h3>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        risk_group_type = st.selectbox(
            tr("risk_group_type"),
            ["RiskGrubuA", "RiskGrubuB"],
            format_func=lambda x: "A" if x == "RiskGrubuA" else "B",
            help=tr("risk_group_type_help")
        )
        risk_class = st.selectbox(tr("risk_class"), [1, 2, 3, 4, 5, 6, 7], help=tr("risk_class_help"))
        start_date = st.date_input(tr("start"), value=datetime.today())
        end_date = st.date_input(tr("end"), value=datetime.today() + timedelta(days=365))
    with col2:
        duration_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
        if end_date.day >= 15:
            duration_months += 1
        st.write(f"⏳ {tr('duration')}: {duration_months} {tr('months')}", help=tr("duration_help"))
        currency = st.selectbox(tr("currency"), ["TRY", "USD", "EUR"])
        fx_rate, fx_info = fx_input(currency, "car")
    
    st.markdown("### " + ("Sigorta Bedelleri" if lang == "TR" else "Sums Insured"))
    if currency != "TRY":
        st.info(fx_info)
    
    col3, col4, col5 = st.columns(3)
    with col3:
        project = st.number_input(tr("project"), min_value=0.0, value=0.0, step=1000.0, help=tr("project_help"))
        if project > 0:
            st.write(f"{tr('entered_value')}: {format_number(project, currency)}")
    with col4:
        cpm = st.number_input(tr("cpm"), min_value=0.0, value=0.0, step=1000.0, help=tr("cpm_help"))
        if cpm > 0:
            st.write(f"{tr('entered_value')}: {format_number(cpm, currency)}")
    with col5:
        cpe = st.number_input(tr("cpe"), min_value=0.0, value=0.0, step=1000.0, help=tr("cpe_help"))
        if cpe > 0:
            st.write(f"{tr('entered_value')}: {format_number(cpe, currency)}")
    
    st.markdown("### " + ("İndirim Oranları" if lang == "TR" else "Discount Rates"))
    col6, col7 = st.columns(2)
    with col6:
        koas = st.selectbox(tr("coins"), list(koasurans_indirimi_car.keys()), help=tr("coins_help"))
    with col7:
        deduct = st.selectbox(tr("ded"), list(muafiyet_indirimi_car.keys()), help=tr("ded_help"))
    
    if st.button(tr("btn_calc"), key="car_calc"):
        car_premium, cpm_premium, cpe_premium, total_premium, applied_rate = calculate_car_ear_premium(
            risk_group_type, risk_class, start_date, end_date, project, cpm, cpe, currency, koas, deduct, fx_rate
        )
        if currency != "TRY":
            car_premium_converted = car_premium / fx_rate
            cpm_premium_converted = cpm_premium / fx_rate
            cpe_premium_converted = cpe_premium / fx_rate
            total_premium_converted = total_premium / fx_rate
            st.markdown(f'<div class="info-box">✅ <b>{tr("car_premium")}:</b> {format_number(car_premium_converted, currency)}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="info-box">✅ <b>{tr("cpm_premium")}:</b> {format_number(cpm_premium_converted, currency)}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="info-box">✅ <b>{tr("cpe_premium")}:</b> {format_number(cpe_premium_converted, currency)}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="info-box">✅ <b>{tr("total_premium")}:</b> {format_number(total_premium_converted, currency)}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="info-box">✅ <b>{tr("car_premium")}:</b> {format_number(car_premium, "TRY")}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="info-box">✅ <b>{tr("cpm_premium")}:</b> {format_number(cpm_premium, "TRY")}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="info-box">✅ <b>{tr("cpe_premium")}:</b> {format_number(cpe_premium, "TRY")}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="info-box">✅ <b>{tr("total_premium")}:</b> {format_number(total_premium, "TRY")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="info-box">📊 <b>{tr("applied_rate")} (CAR):</b> {applied_rate:.2f}‰</div>', unsafe_allow_html=True)
        total_rate = (total_premium / (project + cpm + cpe)) * 1000 if (project + cpm + cpe) > 0 else 0
        st.markdown(f'<div class="info-box">📊 <b>{tr("applied_rate")} (Toplam):</b> {total_rate:.2f}‰</div>', unsafe_allow_html=True)
