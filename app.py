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

# Language dictionary with updated English translations
T = {
    "title": {"TR": "TarifeX – Akıllı Sigorta Prim Hesaplama Uygulaması", "EN": "TarifeX – Smart Insurance Premium Calculator"},
    "subtitle": {"TR": "Deprem ve Yanardağ Püskürmesi Teminatı için Uygulanacak Güncel Tarife", "EN": "Current Tariff for Earthquake and Volcanic Eruption Coverage"},
    "fire_header": {"TR": "🔥 Yangın Sigortası Hesaplama", "EN": "🔥 Fire Insurance Calculation"},
    "car_header": {"TR": "🏗️ İnşaat & Montaj Hesaplama", "EN": "🏗️ Construction & Erection Calculation"},
    "select_calc": {"TR": "Hesaplama Türünü Seçin", "EN": "Select Calculation Type"},
    "calc_fire": {"TR": "Yangın Sigortası - Ticari Sınai Rizikolar (PD & BI)", "EN": "Fire Insurance – Commercial / Industrial (PD & BI)"},
    "calc_car": {"TR": "İnşaat & Montaj (CAR & EAR)", "EN": "Construction & Erection (CAR & EAR)"},
    "num_locations": {"TR": "Lokasyon Sayısı", "EN": "Number of Locations"},
    "num_locations_help": {"TR": "Hesaplama yapılacak lokasyon sayısını girin (1-10).", "EN": "Enter the number of locations to calculate (1-10)."},
    "location_group": {"TR": "Riziko Adresi Grubu", "EN": "Risk Address Group"},
    "location_group_help": {"TR": "Aynı riziko adresindeki lokasyonları aynı gruba atayın.", "EN": "Assign locations at the same risk address to the same group."},
    "building_type": {"TR": "Yapı Tarzı", "EN": "Construction Type"},
    "building_type_help": {"TR": "Betonarme: Çelik veya betonarme taşıyıcı karkas bulunan yapılar. Diğer: Bu gruba girmeyen yapılar.", "EN": "Concrete: Structures with steel or reinforced concrete framework. Other: Structures not in this group."},
    "risk_group": {"TR": "Deprem Risk Grubu (1=En Yüksek Risk)", "EN": "Earthquake Risk Zone (1=Highest)"},
    "risk_group_help": {"TR": "Deprem risk grupları, Doğal Afet Sigortaları Kurumu tarafından belirlenir. 1. Grup en yüksek risktir.", "EN": "Earthquake risk zones are determined by the Natural Disaster Insurance Institution. Zone 1 is the highest risk."},
    "risk_group_type": {"TR": "Risk Sınıfı Türü", "EN": "Risk Group Type"},
    "risk_group_type_help": {"TR": "A: Bina inşaatları, dekorasyon. B: Tünel, köprü, enerji santralleri gibi daha riskli projeler.", "EN": "A: Building construction, decoration. B: Tunnels, bridges, power plants, and other high-risk projects."},
    "currency": {"TR": "Para Birimi", "EN": "Currency"},
    "manual_fx": {"TR": "Kuru manuel güncelleyebilirsiniz", "EN": "You can manually update the exchange rate"},
    "building_sum": {"TR": "Bina Bedeli", "EN": "Building Sum Insured"},
    "building_sum_help": {"TR": "Bina için sigorta bedeli. Betonarme binalar için birim metrekare fiyatı min. 18,600 TL, diğerleri için 12,600 TL.", "EN": "Sum insured for the building. Min. unit square meter price for concrete buildings: 18,600 TL; others: 12,600 TL."},
    "fixture_sum": {"TR": "Demirbaş Bedeli", "EN": "Fixture Sum Insured"},
    "fixture_sum_help": {"TR": "Demirbaşlar için sigorta bedeli.", "EN": "Sum insured for fixtures."},
    "decoration_sum": {"TR": "Dekorasyon Bedeli", "EN": "Decoration Sum Insured"},
    "decoration_sum_help": {"TR": "Dekorasyon için sigorta bedeli.", "EN": "Sum insured for decoration."},
    "commodity_sum": {"TR": "Emtea Bedeli", "EN": "Commodity Sum Insured"},
    "commodity_sum_help": {"TR": "Emtea (ticari mallar) için sigorta bedeli.", "EN": "Sum insured for commodities (commercial goods)."},
    "safe_sum": {"TR": "Kasa Bedeli", "EN": "Safe Sum Insured"},
    "safe_sum_help": {"TR": "Kasa için sigorta bedeli.", "EN": "Sum insured for the safe."},
    "bi": {"TR": "Kar Kaybı Bedeli (BI)", "EN": "Business Interruption Sum Insured (BI)"},
    "bi_help": {"TR": "Deprem sonrası ticari faaliyetin durması sonucu ciro azalması ve maliyet artışından kaynaklanan brüt kâr kaybı.", "EN": "Gross profit loss due to reduced turnover and increased costs from business interruption after an earthquake."},
    "ec_fixed": {"TR": "Elektronik Cihaz Bedeli (Sabit)", "EN": "Electronic Device Sum Insured (Fixed)"},
    "ec_fixed_help": {"TR": "Sabit elektronik cihazlar için sigorta bedeli.", "EN": "Sum insured for fixed electronic devices."},
    "ec_mobile": {"TR": "Elektronik Cihaz Bedeli (Taşınabilir)", "EN": "Electronic Device Sum Insured (Mobile)"},
    "ec_mobile_help": {"TR": "Taşınabilir elektronik cihazlar için sigorta bedeli.", "EN": "Sum insured for mobile electronic devices."},
    "mk_fixed": {"TR": "Makine Kırılması Bedeli (Sabit)", "EN": "Machinery Breakdown Sum Insured (Fixed)"},
    "mk_fixed_help": {"TR": "Sabit makineler için sigorta bedeli.", "EN": "Sum insured for fixed machinery."},
    "mk_mobile": {"TR": "Makine Kırılması Bedeli (Taşınabilir)", "EN": "Machinery Breakdown Sum Insured (Mobile)"},
    "mk_mobile_help": {"TR": "Taşınabilir makineler için sigorta bedeli.", "EN": "Sum insured for mobile machinery."},
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
    "ec_premium": {"TR": "Elektronik Cihaz Primi", "EN": "Electronic Device Premium"},
    "mk_premium": {"TR": "Makine Kırılması Primi", "EN": "Machinery Breakdown Premium"},
    "group_premium": {"TR": "Grup Primi", "EN": "Group Premium"},
    "limit_warning_fire_pd": {"TR": "⚠️ Yangın Sigorta Bedeli: 3.5 milyar TRY limitini aşıyor. Prim hesaplama bu limite göre yapılır.", "EN": "⚠️ Property Damage: Sum insured exceeds the 3.5 billion TRY limit. Premium calculation will be based on this limit."},
    "limit_warning_fire_bi": {"TR": "⚠️ Kar Kaybı Bedeli: 3.5 milyar TRY limitini aşıyor. Prim hesaplama bu limite göre yapılır.", "EN": "⚠️ Business Interruption: Sum insured exceeds the 3.5 billion TRY limit. Premium calculation will be based on this limit."},
    "limit_warning_ec": {"TR": "⚠️ Elektronik Cihaz: Sigorta bedeli 840 milyon TRY limitini aşıyor. Prim hesaplama bu limite göre yapılır.", "EN": "⚠️ Electronic Device: Sum insured exceeds the 840 million TRY limit. Premium calculation will be based on this limit."},
    "limit_warning_mk": {"TR": "⚠️ Makine Kırılması: Sigorta bedeli 840 milyon TRY limitini aşıyor. Prim hesaplama bu limite göre yapılır.", "EN": "⚠️ Machinery Breakdown: Sum insured exceeds the 840 million TRY limit. Premium calculation will be based on this limit."},
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
    tcmb_rate_key = f"{key_prefix}_{ccy}_tcmb_rate"
    tcmb_date_key = f"{key_prefix}_{ccy}_tcmb_date"
    
    if tcmb_rate_key not in st.session_state:
        tcmb_rate, tcmb_date = get_tcmb_rate(ccy)
        if tcmb_rate is None:
            st.session_state.update({
                tcmb_rate_key: 0.0,
                tcmb_date_key: "-",
                r_key: 0.0,
                s_key: "MANUEL"
            })
        else:
            st.session_state.update({
                tcmb_rate_key: tcmb_rate,
                tcmb_date_key: tcmb_date,
                r_key: tcmb_rate,
                s_key: "TCMB"
            })
    
    default_rate = float(st.session_state[r_key])
    new_rate = st.number_input(tr("manual_fx"), value=default_rate, step=0.0001, format="%.4f", key=f"{key_prefix}_{ccy}_manual")
    
    if new_rate != st.session_state.get(tcmb_rate_key, 0.0):
        st.session_state[s_key] = "MANUEL"
    else:
        st.session_state[s_key] = "TCMB"
    
    st.session_state[r_key] = new_rate
    
    info_message = (
        f"💱 TCMB Kuru: 1 {ccy} = {st.session_state[tcmb_rate_key]:,.4f} TL (TCMB, {st.session_state[tcmb_date_key]}) | "
        f"Kullanılan Kur: 1 {ccy} = {st.session_state[r_key]:,.4f} TL ({st.session_state[s_key]})"
    )
    st.info(info_message)
    return st.session_state[r_key], info_message

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
    "40/60": 0.50,
    "30/70": 0.125, "25/75": 0.0625,
    "90/10": -0.125, "100/0": -0.25
}
koasurans_indirimi_car = {
    "80/20": 0.0, "75/25": 0.0625, "70/30": 0.125, "65/35": 0.1875,
    "60/40": 0.25, "55/45": 0.3125, "50/50": 0.375, "45/55": 0.4375,
    "40/60": 0.50
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
    return base + (0.03 * extra_months)

def calculate_months_difference(start_date, end_date):
    months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    total_days = (end_date - start_date).days
    year_diff = end_date.year - start_date.year
    month_diff = end_date.month - start_date.month
    estimated_days = (year_diff * 365) + (month_diff * 30)
    remaining_days = total_days - estimated_days
    if remaining_days >= 15:
        months += 1
    return months

def determine_group_params(locations_data):
    # Group locations by risk address group
    groups = {}
    for loc in locations_data:
        group = loc["group"]
        if group not in groups:
            groups[group] = []
        groups[group].append(loc)
    
    # Determine building type and risk group for each group
    for group, locs in groups.items():
        # Select building type with highest rate (Diğer > Betonarme)
        building_types = [loc["building_type"] for loc in locs]
        building_type = "Diğer" if "Diğer" in building_types else "Betonarme"
        
        # Select highest risk group (lowest number)
        risk_groups = [loc["risk_group"] for loc in locs]
        risk_group = min(risk_groups)
        
        # Sum insured values
        building = sum(loc["building"] for loc in locs)
        fixture = sum(loc["fixture"] for loc in locs)
        decoration = sum(loc["decoration"] for loc in locs)
        commodity = sum(loc["commodity"] for loc in locs)
        safe = sum(loc["safe"] for loc in locs)
        bi = sum(loc["bi"] for loc in locs)
        ec_fixed = sum(loc["ec_fixed"] for loc in locs)
        ec_mobile = sum(loc["ec_mobile"] for loc in locs)
        mk_fixed = sum(loc["mk_fixed"] for loc in locs)
        mk_mobile = sum(loc["mk_mobile"] for loc in locs)
        
        groups[group] = {
            "building_type": building_type,
            "risk_group": risk_group,
            "building": building,
            "fixture": fixture,
            "decoration": decoration,
            "commodity": commodity,
            "safe": safe,
            "bi": bi,
            "ec_fixed": ec_fixed,
            "ec_mobile": ec_mobile,
            "mk_fixed": mk_fixed,
            "mk_mobile": mk_mobile
        }
    return groups

def calculate_fire_premium(building_type, risk_group, currency, building, fixture, decoration, commodity, safe, bi, ec_fixed, ec_mobile, mk_fixed, mk_mobile, koas, deduct, fx_rate):
    pd_sum_insured = (building + fixture + decoration + commodity + safe) * fx_rate
    bi_sum_insured = bi * fx_rate
    ec_fixed_sum_insured = ec_fixed * fx_rate
    ec_mobile_sum_insured = ec_mobile * fx_rate
    mk_fixed_sum_insured = mk_fixed * fx_rate
    mk_mobile_sum_insured = mk_mobile * fx_rate
    
    rate = tarife_oranlari[building_type][risk_group - 1]
    
    LIMIT_FIRE = 3_500_000_000
    LIMIT_EC_MK = 840_000_000
    
    koas_discount = koasurans_indirimi[koas]
    deduct_discount = muafiyet_indirimi[deduct]
    adjusted_rate_pd = rate * (1 - koas_discount) * (1 - deduct_discount)
    if pd_sum_insured > LIMIT_FIRE:
        st.warning(tr("limit_warning_fire_pd"))
        adjusted_rate_pd = round(adjusted_rate_pd * (LIMIT_FIRE / pd_sum_insured), 6)
    pd_premium = (pd_sum_insured * adjusted_rate_pd) / 1000
    
    adjusted_rate_bi = rate
    if bi_sum_insured > LIMIT_FIRE:
        st.warning(tr("limit_warning_fire_bi"))
        adjusted_rate_bi = round(adjusted_rate_bi * (LIMIT_FIRE / bi_sum_insured), 6)
    bi_premium = (bi_sum_insured * adjusted_rate_bi) / 1000
    
    ec_premium = 0.0
    ec_fixed_premium = 0.0
    ec_mobile_premium = 0.0
    if ec_fixed > 0:
        ec_fixed_rate = rate * (1 - koas_discount) * (1 - deduct_discount)
        if ec_fixed_sum_insured > LIMIT_EC_MK:
            st.warning(tr("limit_warning_ec"))
            ec_fixed_rate = round(ec_fixed_rate * (LIMIT_EC_MK / ec_fixed_sum_insured), 6)
        ec_fixed_premium = (ec_fixed_sum_insured * ec_fixed_rate) / 1000
    if ec_mobile > 0:
        ec_mobile_rate = 2.00
        if ec_mobile_sum_insured > LIMIT_EC_MK:
            st.warning(tr("limit_warning_ec"))
            ec_mobile_rate = round(ec_mobile_rate * (LIMIT_EC_MK / ec_mobile_sum_insured), 6)
        ec_mobile_premium = (ec_mobile_sum_insured * ec_mobile_rate) / 1000
    ec_premium = ec_fixed_premium + ec_mobile_premium
    
    mk_premium = 0.0
    mk_fixed_premium = 0.0
    mk_mobile_premium = 0.0
    if mk_fixed > 0:
        mk_fixed_rate = rate * (1 - koas_discount) * (1 - deduct_discount)
        if mk_fixed_sum_insured > LIMIT_EC_MK:
            st.warning(tr("limit_warning_mk"))
            mk_fixed_rate = round(mk_fixed_rate * (LIMIT_EC_MK / mk_fixed_sum_insured), 6)
        mk_fixed_premium = (mk_fixed_sum_insured * mk_fixed_rate) / 1000
    if mk_mobile > 0:
        mk_mobile_rate = 2.00
        if mk_mobile_sum_insured > LIMIT_EC_MK:
            st.warning(tr("limit_warning_mk"))
            mk_mobile_rate = round(mk_mobile_rate * (LIMIT_EC_MK / mk_mobile_sum_insured), 6)
        mk_mobile_premium = (mk_mobile_sum_insured * mk_mobile_rate) / 1000
    mk_premium = mk_fixed_premium + mk_mobile_premium
    
    total_premium = pd_premium + bi_premium + ec_premium + mk_premium
    
    return pd_premium, bi_premium, ec_premium, mk_premium, total_premium, rate

def calculate_car_ear_premium(risk_group_type, risk_class, start_date, end_date, project, cpm, cpe, currency, koas, deduct, fx_rate):
    duration_months = calculate_months_difference(start_date, end_date)
    
    base_rate = tarife_oranlari[risk_group_type][risk_class - 1]
    duration_multiplier = calculate_duration_multiplier(duration_months)
    koas_discount = koasurans_indirimi_car[koas]
    deduct_discount = muafiyet_indirimi_car[deduct]
    
    LIMIT = 840_000_000
    
    project_sum_insured = project * fx_rate
    car_rate = base_rate * duration_multiplier * (1 - koas_discount) * (1 - deduct_discount)
    if project_sum_insured > LIMIT:
        st.warning(tr("limit_warning_car"))
        car_rate *= (LIMIT / project_sum_insured)
    car_premium = (project_sum_insured * car_rate) / 1000
    
    cpm_sum_insured = cpm * fx_rate
    cpm_rate = 1.25
    if cpm_sum_insured > LIMIT:
        st.warning(tr("limit_warning_car"))
        cpm_rate *= (LIMIT / cpm_sum_insured)
    cpm_premium = (cpm_sum_insured * cpm_rate / 1000) * duration_multiplier
    
    cpe_sum_insured = cpe * fx_rate
    cpe_rate = base_rate * duration_multiplier
    if cpe_sum_insured > LIMIT:
        st.warning(tr("limit_warning_car"))
        cpe_rate *= (LIMIT / cpe_sum_insured)
    cpe_premium = (cpe_sum_insured * cpe_rate) / 1000
    
    total_premium = car_premium + cpm_premium + cpe_premium
    
    return car_premium, cpm_premium, cpe_premium, total_premium, car_rate

# ------------------------------------------------------------
# 4) STREAMLIT UI
# ------------------------------------------------------------
# Header with Image
st.markdown(f'<h1 class="main-title">🏷️ {tr("title")}</h1>', unsafe_allow_html=True)
st.markdown(f'<h3 class="subtitle">{tr("subtitle")}</h3>', unsafe_allow_html=True)
st.markdown('<p class="founders">Founders: Ubeydullah Ayvaz & Furkan Kaymaz</p>', unsafe_allow_html=True)

st.image("https://i.imgur.com/iA8pLRD.jpg", caption=tr("title"))

# Main Content
st.markdown('<h2 class="section-header">📌 ' + ("Hesaplama Yap" if lang == "TR" else "Perform Calculation") + '</h2>', unsafe_allow_html=True)
calc_type = st.selectbox(tr("select_calc"), [tr("calc_fire"), tr("calc_car")], help="Hesaplama türünü seçerek başlayın." if lang == "TR" else "Start by selecting the calculation type.")

if calc_type == tr("calc_fire"):
    st.markdown(f'<h3 class="section-header">{tr("fire_header")}</h3>', unsafe_allow_html=True)
    
    # Number of Locations
    num_locations = st.number_input(tr("num_locations"), min_value=1, max_value=10, value=1, step=1, help=tr("num_locations_help"))
    
    # Risk Address Groups
    groups = [chr(65 + i) for i in range(num_locations)]  # A, B, C, ...
    locations_data = []
    for i in range(num_locations):
        with st.expander(f"Lokasyon {i + 1}" if lang == "TR" else f"Location {i + 1}"):
            col1, col2 = st.columns(2)
            with col1:
                building_type = st.selectbox(tr("building_type"), ["Betonarme", "Diğer"], key=f"building_type_{i}", help=tr("building_type_help"))
                risk_group = st.selectbox(tr("risk_group"), [1, 2, 3, 4, 5, 6, 7], key=f"risk_group_{i}", help=tr("risk_group_help"))
            with col2:
                group = st.selectbox(tr("location_group"), groups, key=f"group_{i}", help=tr("location_group_help"))
                if i == 0:
                    currency = st.selectbox(tr("currency"), ["TRY", "USD", "EUR"], key="fire_currency")
                    fx_rate, fx_info = fx_input(currency, "fire")
            
            st.markdown("#### SİGORTA BEDELLERİ")
            if currency != "TRY":
                st.info(fx_info)
            
            col3, col4, col5 = st.columns(3)
            with col3:
                building = st.number_input(tr("building_sum"), min_value=0.0, value=0.0, step=1000.0, key=f"building_{i}", help=tr("building_sum_help"))
                if building > 0:
                    st.write(f"{tr('entered_value')}: {format_number(building, currency)}")
                fixture = st.number_input(tr("fixture_sum"), min_value=0.0, value=0.0, step=1000.0, key=f"fixture_{i}", help=tr("fixture_sum_help"))
                if fixture > 0:
                    st.write(f"{tr('entered_value')}: {format_number(fixture, currency)}")
                decoration = st.number_input(tr("decoration_sum"), min_value=0.0, value=0.0, step=1000.0, key=f"decoration_{i}", help=tr("decoration_sum_help"))
                if decoration > 0:
                    st.write(f"{tr('entered_value')}: {format_number(decoration, currency)}")
            with col4:
                commodity = st.number_input(tr("commodity_sum"), min_value=0.0, value=0.0, step=1000.0, key=f"commodity_{i}", help=tr("commodity_sum_help"))
                if commodity > 0:
                    st.write(f"{tr('entered_value')}: {format_number(commodity, currency)}")
                safe = st.number_input(tr("safe_sum"), min_value=0.0, value=0.0, step=1000.0, key=f"safe_{i}", help=tr("safe_sum_help"))
                if safe > 0:
                    st.write(f"{tr('entered_value')}: {format_number(safe, currency)}")
                bi = st.number_input(tr("bi"), min_value=0.0, value=0.0, step=1000.0, key=f"bi_{i}", help=tr("bi_help"))
                if bi > 0:
                    st.write(f"{tr('entered_value')}: {format_number(bi, currency)}")
            with col5:
                ec_fixed = st.number_input(tr("ec_fixed"), min_value=0.0, value=0.0, step=1000.0, key=f"ec_fixed_{i}", help=tr("ec_fixed_help"))
                if ec_fixed > 0:
                    st.write(f"{tr('entered_value')}: {format_number(ec_fixed, currency)}")
                ec_mobile = st.number_input(tr("ec_mobile"), min_value=0.0, value=0.0, step=1000.0, key=f"ec_mobile_{i}", help=tr("ec_mobile_help"))
                if ec_mobile > 0:
                    st.write(f"{tr('entered_value')}: {format_number(ec_mobile, currency)}")
                mk_fixed = st.number_input(tr("mk_fixed"), min_value=0.0, value=0.0, step=1000.0, key=f"mk_fixed_{i}", help=tr("mk_fixed_help"))
                if mk_fixed > 0:
                    st.write(f"{tr('entered_value')}: {format_number(mk_fixed, currency)}")
                mk_mobile = st.number_input(tr("mk_mobile"), min_value=0.0, value=0.0, step=1000.0, key=f"mk_mobile_{i}", help=tr("mk_mobile_help"))
                if mk_mobile > 0:
                    st.write(f"{tr('entered_value')}: {format_number(mk_mobile, currency)}")
            
            locations_data.append({
                "group": group,
                "building_type": building_type,
                "risk_group": risk_group,
                "building": building,
                "fixture": fixture,
                "decoration": decoration,
                "commodity": commodity,
                "safe": safe,
                "bi": bi,
                "ec_fixed": ec_fixed,
                "ec_mobile": ec_mobile,
                "mk_fixed": mk_fixed,
                "mk_mobile": mk_mobile
            })
    
    st.markdown("### İNDIRIM ORANLARI")
    col5, col6 = st.columns(2)
    with col5:
        koas = st.selectbox(tr("koas"), list(koasurans_indirimi.keys()), help=tr("koas_help"))
    with col6:
        deduct = st.selectbox(tr("deduct"), sorted(list(muafiyet_indirimi.keys()), reverse=True), help=tr("deduct_help"))
    
    if st.button(tr("btn_calc"), key="fire_calc"):
        groups = determine_group_params(locations_data)
        total_premium = 0.0
        for group, data in groups.items():
            pd_premium, bi_premium, ec_premium, mk_premium, group_premium, applied_rate = calculate_fire_premium(
                data["building_type"], data["risk_group"], currency,
                data["building"], data["fixture"], data["decoration"], data["commodity"], data["safe"],
                data["bi"], data["ec_fixed"], data["ec_mobile"], data["mk_fixed"], data["mk_mobile"],
                koas, deduct, fx_rate
            )
            total_premium += group_premium
            if currency != "TRY":
                pd_premium_converted = pd_premium / fx_rate
                bi_premium_converted = bi_premium / fx_rate
                ec_premium_converted = ec_premium / fx_rate
                mk_premium_converted = mk_premium / fx_rate
                group_premium_converted = group_premium / fx_rate
                st.markdown(f'<div class="info-box">✅ <b>{tr("group_premium")} ({group}):</b> {format_number(group_premium_converted, currency)}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="info-box">✅ <b>{tr("pd_premium")} ({group}):</b> {format_number(pd_premium_converted, currency)}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="info-box">✅ <b>{tr("bi_premium")} ({group}):</b> {format_number(bi_premium_converted, currency)}</div>', unsafe_allow_html=True)
                if data["ec_fixed"] > 0 or data["ec_mobile"] > 0:
                    st.markdown(f'<div class="info-box">✅ <b>{tr("ec_premium")} ({group}):</b> {format_number(ec_premium_converted, currency)}</div>', unsafe_allow_html=True)
                if data["mk_fixed"] > 0 or data["mk_mobile"] > 0:
                    st.markdown(f'<div class="info-box">✅ <b>{tr("mk_premium")} ({group}):</b> {format_number(mk_premium_converted, currency)}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="info-box">📊 <b>{tr("applied_rate")} ({group}):</b> {applied_rate:.2f}‰</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="info-box">✅ <b>{tr("group_premium")} ({group}):</b> {format_number(group_premium, "TRY")}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="info-box">✅ <b>{tr("pd_premium")} ({group}):</b> {format_number(pd_premium, "TRY")}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="info-box">✅ <b>{tr("bi_premium")} ({group}):</b> {format_number(bi_premium, "TRY")}</div>', unsafe_allow_html=True)
                if data["ec_fixed"] > 0 or data["ec_mobile"] > 0:
                    st.markdown(f'<div class="info-box">✅ <b>{tr("ec_premium")} ({group}):</b> {format_number(ec_premium, "TRY")}</div>', unsafe_allow_html=True)
                if data["mk_fixed"] > 0 or data["mk_mobile"] > 0:
                    st.markdown(f'<div class="info-box">✅ <b>{tr("mk_premium")} ({group}):</b> {format_number(mk_premium, "TRY")}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="info-box">📊 <b>{tr("applied_rate")} ({group}):</b> {applied_rate:.2f}‰</div>', unsafe_allow_html=True)
        
        if currency != "TRY":
            total_premium_converted = total_premium / fx_rate
            st.markdown(f'<div class="info-box">✅ <b>{tr("total_premium")}:</b> {format_number(total_premium_converted, currency)}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="info-box">✅ <b>{tr("total_premium")}:</b> {format_number(total_premium, "TRY")}</div>', unsafe_allow_html=True)

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
        duration_months = calculate_months_difference(start_date, end_date)
        st.write(f"⏳ {tr('duration')}: {duration_months} {tr('months')}", help=tr("duration_help"))
        currency = st.selectbox(tr("currency"), ["TRY", "USD", "EUR"])
        fx_rate, fx_info = fx_input(currency, "car")
    
    st.markdown("### SİGORTA BEDELLERİ")
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
    
    st.markdown("### İNDIRIM ORANLARI")
    col6, col7 = st.columns(2)
    with col6:
        koas = st.selectbox(tr("coins"), list(koasurans_indirimi_car.keys()), help=tr("coins_help"))
    with col7:
        deduct = st.selectbox(tr("ded"), sorted(list(muafiyet_indirimi_car.keys()), reverse=True), help=tr("ded_help"))
    
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
