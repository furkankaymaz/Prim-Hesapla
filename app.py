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
    "start_date": {"TR": "Başlangıç Tarihi", "EN": "Start Date"},
    "end_date": {"TR": "Bitiş Tarihi", "EN": "End Date"},
    "duration": {"TR": "Poliçe Süresi (Ay)", "EN": "Policy Duration (Months)"},
    "duration_help": {"TR": "Poliçe süresi 6-36 ay arasında olmalıdır. Daha uzun süreler için ek çarpan uygulanır.", "EN": "Policy duration should be between 6-36 months. Additional multiplier applies for longer durations."},
    "project": {"TR": "Proje Bedeli (CAR)", "EN": "Project Sum Insured (CAR)"},
    "project_help": {"TR": "İnşaat veya montaj projesinin toplam bedeli.", "EN": "Total sum insured for the construction or erection project."},
    "cpm": {"TR": "Makine ve Ekipman Bedeli (CPM)", "EN": "Machinery and Equipment Sum Insured (CPM)"},
    "cpm_help": {"TR": "İnşaat sırasında kullanılan makine ve ekipmanların bedeli.", "EN": "Sum insured for machinery and equipment used during construction."},
    "cpe": {"TR": "Mevcut Yapı Bedeli (CPE)", "EN": "Existing Structure Sum Insured (CPE)"},
    "cpe_help": {"TR": "İnşaat alanında bulunan mevcut yapıların sigorta bedeli.", "EN": "Sum insured for existing structures at the construction site."},
    "limit_warning_fire": {"TR": "Toplam sigorta bedeli 3,500,000,000 TRY limitini aşıyor. Limit üzerinden hesaplama yapıldı.", "EN": "Total sum insured exceeds the 3,500,000,000 TRY limit. Calculation is based on the limit."},
    "limit_warning_car": {"TR": "Toplam sigorta bedeli 850,000,000 TRY limitini aşıyor. Limit üzerinden hesaplama yapıldı.", "EN": "Total sum insured exceeds the 850,000,000 TRY limit. Calculation is based on the limit."},
    "results": {"TR": "Sonuçlar", "EN": "Results"},
    "car_premium": {"TR": "CAR Primi", "EN": "CAR Premium"},
    "cpm_premium": {"TR": "CPM Primi", "EN": "CPM Premium"},
    "cpe_premium": {"TR": "CPE Primi", "EN": "CPE Premium"},
    "total_premium": {"TR": "Toplam Prim", "EN": "Total Premium"},
    "min_premium_info": {"TR": "Not: Minimum prim uygulanabilir.", "EN": "Note: Minimum premium may apply."},
}

def tr(key):
    return T[key][lang]

# ------------------------------------------------------------
# 1) HEADER
# ------------------------------------------------------------
st.markdown(f'<div class="main-title">{tr("title")}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="subtitle">{tr("subtitle")}</div>', unsafe_allow_html=True)

# ------------------------------------------------------------
# 2) TARIFF TABLES AND CONSTANTS
# ------------------------------------------------------------
# Tariff rates for Fire (unchanged)
tarife_oranlari = {
    "Betonarme": [3.13, 2.63, 2.38, 1.94, 1.38, 1.06, 0.75],
    "Diğer": [6.13, 5.56, 3.75, 2.00, 1.56, 1.24, 1.06],
    "RiskGrubuA": [1.56, 1.31, 1.19, 0.98, 0.69, 0.54, 0.38],  # CAR/EAR Group A
    "RiskGrubuB": [3.06, 2.79, 1.88, 1.00, 0.79, 0.63, 0.54]   # CAR/EAR Group B
}

# Duration multiplier table (unchanged)
sure_carpani_tablosu = {
    6: 0.70, 7: 0.75, 8: 0.80, 9: 0.85, 10: 0.90, 11: 0.95, 12: 1.00,
    13: 1.05, 14: 1.10, 15: 1.15, 16: 1.20, 17: 1.25, 18: 1.30,
    19: 1.35, 20: 1.40, 21: 1.45, 22: 1.50, 23: 1.55, 24: 1.60,
    25: 1.65, 26: 1.70, 27: 1.74, 28: 1.78, 29: 1.82, 30: 1.86,
    31: 1.90, 32: 1.94, 33: 1.98, 34: 2.02, 35: 2.06, 36: 2.10
}

# Coinsurance discounts (Fire - unchanged)
koasurans_indirimi = {
    "80/20": 0.0, "75/25": 0.0625, "70/30": 0.125, "65/35": 0.1875,
    "60/40": 0.25, "55/45": 0.3125, "50/50": 0.375, "45/55": 0.4375,
    "40/60": 0.5, "30/70": 0.125, "25/75": 0.0625,
    "90/10": -0.125, "100/0": -0.25
}

# Coinsurance discounts (CAR/EAR - updated)
koasurans_indirimi_car = {
    "80/20": 0.0, "75/25": 0.0625, "70/30": 0.125, "65/35": 0.1875,
    "60/40": 0.25, "55/45": 0.3125, "50/50": 0.375, "45/55": 0.4375,
    "40/60": 0.5
}

# Deductible discounts (Fire - unchanged)
muafiyet_indirimi = {
    2: 0.0, 3: 0.06, 4: 0.13, 5: 0.19, 10: 0.35,
    0.1: -0.12, 0.5: -0.09, 1: -0.06, 1.5: -0.03
}

# Deductible discounts (CAR/EAR - updated)
muafiyet_indirimi_car = {2: 0.0, 3: 0.06, 4: 0.13, 5: 0.19, 10: 0.35}

# Limits
LIMIT_FIRE = 3_500_000_000  # 3.5 billion TRY for Fire
LIMIT_CAR = 850_000_000     # 850 million TRY for CAR/EAR

# Minimum premiums (unchanged)
MIN_PREMIUM_FIRE = 5000  # TRY
MIN_PREMIUM_CAR = 5000   # TRY

# ------------------------------------------------------------
# 3) HELPER FUNCTIONS
# ------------------------------------------------------------
def get_exchange_rate(currency: str) -> float:
    # Since network calls are not allowed in Pyodide, we'll return default values
    # In a real environment, this would fetch from TCMB
    rates = {"TRY": 1.0, "USD": 34.0, "EUR": 36.0}  # Approximate rates as of April 2025
    return rates.get(currency, 1.0)

def calculate_duration_multiplier(months: int) -> float:
    if months <= 36:
        return sure_carpani_tablosu.get(months, 1.0)
    base = sure_carpani_tablosu[36]
    extra_months = months - 36
    return base * (1 + 0.03 * extra_months)

def calculate_fire_premium(pd: float, bi: float, fx_rate: float, building_type: str, risk_group: int, duration_months: int, koas: str, deduct: float) -> tuple[float, float]:
    total_sum_insured = (pd + bi) * fx_rate
    if total_sum_insured > LIMIT_FIRE:
        st.warning(tr("limit_warning_fire"))
        total_sum_insured = LIMIT_FIRE
    
    base_rate = tarife_oranlari[building_type][risk_group - 1]
    duration_multiplier = calculate_duration_multiplier(duration_months)
    koas_discount = koasurans_indirimi[koas]
    deduct_discount = muafiyet_indirimi[deduct]
    
    final_rate = base_rate * duration_multiplier * (1 - koas_discount) * (1 - deduct_discount)
    premium = (total_sum_insured * final_rate) / 100
    
    if premium < MIN_PREMIUM_FIRE:
        premium = MIN_PREMIUM_FIRE
    return premium, final_rate

def calculate_car_ear_premium(project: float, cpm: float, cpe: float, fx_rate: float, risk_group_type: str, risk_class: int, start_date: datetime, end_date: datetime, koas: str, deduct: float) -> tuple[float, float, float, float, float]:
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
    
    # CAR Premium
    project_sum_insured = project * fx_rate
    car_rate = base_rate * duration_multiplier * (1 - koas_discount) * (1 - deduct_discount)
    if project_sum_insured > LIMIT_CAR:
        car_rate *= (LIMIT_CAR / project_sum_insured)
    car_premium = (project_sum_insured * car_rate) / 1000
    
    # CPM Premium
    cpm_sum_insured = cpm * fx_rate
    cpm_rate = 2.0  # Default rate is 2 ‰
    if cpm_sum_insured > LIMIT_CAR:
        cpm_rate *= (LIMIT_CAR / cpm_sum_insured)
    cpm_premium = (cpm_sum_insured * cpm_rate / 1000) * duration_factor
    
    # CPE Premium
    cpe_sum_insured = cpe * fx_rate
    cpe_rate = base_rate * duration_multiplier  # No koas or deduct discount for CPE
    if cpe_sum_insured > LIMIT_CAR:
        cpe_rate *= (LIMIT_CAR / cpe_sum_insured)
    cpe_premium = (cpe_sum_insured * cpe_rate) / 1000
    
    # Total Premium
    total_premium = car_premium + cpm_premium + cpe_premium
    if total_premium < MIN_PREMIUM_CAR:
        total_premium = MIN_PREMIUM_CAR
    
    return car_premium, cpm_premium, cpe_premium, total_premium, car_rate

# ------------------------------------------------------------
# 4) INPUT FORM
# ------------------------------------------------------------
# Currency selection (moved back to the top)
currencies = ["TRY", "USD", "EUR"]
currency = st.selectbox(tr("currency"), currencies)
fx_rate = get_exchange_rate(currency)
fx_rate = st.number_input(tr("manual_fx"), value=fx_rate, min_value=0.0, step=0.01)

calc_type = st.selectbox(tr("select_calc"), [tr("calc_fire"), tr("calc_car")])

# Fire Insurance Form (unchanged)
if calc_type == tr("calc_fire"):
    st.markdown(f'<div class="section-header">{tr("fire_header")}</div>', unsafe_allow_html=True)
    
    building_type = st.selectbox(tr("building_type"), ["Betonarme", "Diğer"], help=tr("building_type_help"))
    risk_group = st.selectbox(tr("risk_group"), [1, 2, 3, 4, 5, 6, 7], help=tr("risk_group_help"))
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(tr("start_date"), value=datetime.today())
    with col2:
        end_date = st.date_input(tr("end_date"), value=datetime.today() + timedelta(days=365))
    
    duration_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    st.number_input(tr("duration"), value=duration_months, disabled=True, help=tr("duration_help"))
    
    col3, col4 = st.columns(2)
    with col3:
        pd = st.number_input(tr("pd"), min_value=0.0, value=1000000.0, step=10000.0, help=tr("pd_help"))
    with col4:
        bi = st.number_input(tr("bi"), min_value=0.0, value=0.0, step=10000.0, help=tr("bi_help"))
    
    koas = st.selectbox(tr("koas"), list(koasurans_indirimi.keys()), help=tr("koas_help"))
    deduct = st.selectbox(tr("deduct"), list(muafiyet_indirimi.keys()), help=tr("deduct_help"))
    
    if st.button(tr("btn_calc")):
        premium, applied_rate = calculate_fire_premium(pd, bi, fx_rate, building_type, risk_group, duration_months, koas, deduct)
        st.markdown(f"### {tr('results')}")
        st.markdown(f"- **{tr('total_premium')}**: {premium:,.2f} TRY")
        st.markdown(f"- **{tr('applied_rate')}**: {applied_rate:.2f} ‰")
        st.markdown(f"*{tr('min_premium_info')}*")

# CAR/EAR Insurance Form (only risk group type is ensured)
else:
    st.markdown(f'<div class="section-header">{tr("car_header")}</div>', unsafe_allow_html=True)
    
    # Risk Group Type (A or B)
    risk_group_type = st.selectbox(
        tr("risk_group_type"),
        ["RiskGrubuA", "RiskGrubuB"],
        format_func=lambda x: "A" if x == "RiskGrubuA" else "B",
        help=tr("risk_group_type_help")
    )
    
    # Earthquake Risk Zone (1-7)
    risk_class = st.selectbox(tr("risk_class"), [1, 2, 3, 4, 5, 6, 7], help=tr("risk_class_help"))
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(tr("start_date"), value=datetime.today())
    with col2:
        end_date = st.date_input(tr("end_date"), value=datetime.today() + timedelta(days=365))
    
    duration_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    if end_date.day >= 15:
        duration_months += 1
    st.number_input(tr("duration"), value=duration_months, disabled=True, help=tr("duration_help"))
    
    col3, col4, col5 = st.columns(3)
    with col3:
        project = st.number_input(tr("project"), min_value=0.0, value=1000000.0, step=10000.0, help=tr("project_help"))
    with col4:
        cpm = st.number_input(tr("cpm"), min_value=0.0, value=0.0, step=10000.0, help=tr("cpm_help"))
    with col5:
        cpe = st.number_input(tr("cpe"), min_value=0.0, value=0.0, step=10000.0, help=tr("cpe_help"))
    
    koas = st.selectbox(tr("koas"), list(koasurans_indirimi_car.keys()), help=tr("koas_help"))
    deduct = st.selectbox(tr("deduct"), list(muafiyet_indirimi_car.keys()), help=tr("deduct_help"))
    
    if st.button(tr("btn_calc")):
        car_premium, cpm_premium, cpe_premium, total_premium, applied_rate = calculate_car_ear_premium(
            project, cpm, cpe, fx_rate, risk_group_type, risk_class, start_date, end_date, koas, deduct
        )
        st.markdown(f"### {tr('results')}")
        st.markdown(f"- **{tr('car_premium')}**: {car_premium:,.2f} TRY")
        st.markdown(f"- **{tr('cpm_premium')}**: {cpm_premium:,.2f} TRY")
        st.markdown(f"- **{tr('cpe_premium')}**: {cpe_premium:,.2f} TRY")
        st.markdown(f"- **{tr('total_premium')}**: {total_premium:,.2f} TRY")
        st.markdown(f"- **{tr('applied_rate')} (CAR)**: {applied_rate:.2f} ‰")
        st.markdown(f"*{tr('min_premium_info')}*")
