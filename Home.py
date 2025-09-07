# -*- coding: utf-8 -*-
#
# TariffEQ – Profesyonel ve AI Destekli PD & BI Hasar Analiz Aracı
# =======================================================================
# Bu Streamlit uygulaması, reasürans ve katastrofik modelleme metodolojilerinden
# esinlenerek geliştirilmiş parametreler ve tarifeye tam uyumlu hesaplama
# mantığı ile ticari/sınai rizikolar için profesyonel seviyde bir deprem
# hasar analizi sunar.
#
# GÜNCEL REVİZYON NOTLARI (Eylül 2025 - v3.2):
# 1. İki Aşamalı AI Raporlama: AI teknik değerlendirmesi, (1) Yapısal Riskler ve
#    (2) Faaliyete Özgü Sektörel Riskler olarak ikiye ayrıldı. Bu sayede çok
#    daha detaylı ve isabetli bir analiz sunulmaktadır.
# 2. Dinamik PD Modelleme: Bina/İçerik hasar oranı (örn: 40/60) artık sabit değil.
#    AI, faaliyet tanımına göre (AVM, Üretim, Lojistik vb.) en uygun sektörel
#    profili belirleyerek hasar dağılımını dinamik olarak atamaktadır.
# 3. Gelişmiş AI Promptları: AI'a "kıdemli hasar eksperi" rolü verilerek, faaliyet
#    tanımındaki spesifik riskleri (kırılabilir stok, otopark, FFE, altyapı
#    kesintileri) proaktif olarak tespit etmesi ve raporlaması sağlandı.

import streamlit as st
import pandas as pd
import plotly.express as px
from dataclasses import dataclass
from typing import Dict, List, Tuple
import json
import traceback

# --- AI İÇİN KORUMALI IMPORT VE GÜVENLİ KONFİGÜRASYON ---
_GEMINI_AVAILABLE = False
try:
    import google.generativeai as genai
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        _GEMINI_AVAILABLE = True
    else:
        st.sidebar.warning("Gemini API anahtarı bulunamadı. AI özellikleri devre dışı.", icon="🔑")
        _GEMINI_AVAILABLE = False
except (ImportError, Exception):
    st.sidebar.error("Google AI kütüphanesi yüklenemedi. AI özellikleri devre dışı.", icon="🤖")
    _GEMINI_AVAILABLE = False

# --- TARİFE, ÇARPAN VERİLERİ VE SABİTLER ---
TARIFE_RATES = {"Betonarme": [3.13, 2.63, 2.38, 1.94, 1.38, 1.06, 0.75], "Diğer": [6.13, 5.56, 3.75, 2.00, 1.56, 1.24, 1.06]}
KOAS_FACTORS = {"80/20": 1.0, "75/25": 0.9375, "70/30": 0.875, "65/35": 0.8125, "60/40": 0.75, "55/45": 0.6875, "50/50": 0.625, "45/55": 0.5625, "40/60": 0.5, "90/10": 1.125, "100/0": 1.25}
MUAFIYET_FACTORS = {2.0: 1.0, 3.0: 0.94, 4.0: 0.87, 5.0: 0.81, 10.0: 0.65, 1.5: 1.03, 1.0: 1.06, 0.5: 1.09, 0.1: 1.12}
_DEPREM_ORAN = {1: 0.20, 2: 0.17, 3: 0.13, 4: 0.09, 5: 0.06, 6: 0.06, 7: 0.06}
# YENİ (v3.2): Dinamik PD modellemesi için sektörel bina/içerik oranları
BINA_ICERIK_ORANLARI = {
    "Üretim Tesisi": (0.40, 0.60),
    "Lojistik Depo": (0.50, 0.50),
    "AVM / Otel / Ofis": (0.60, 0.40),
    "Diğer / Varsayılan": (0.50, 0.50)
}

# --- ÇEVİRİ SÖZLÜĞÜ ---
T = {
    "title": {"TR": "TariffEQ – AI Destekli Risk Analizi", "EN": "TariffEQ – AI-Powered Risk Analysis"},
    "inputs_header": {"TR": "📊 1. Senaryo Girdileri", "EN": "📊 1. Scenario Inputs"},
    "base_header": {"TR": "🏭 Temel Tesis Bilgileri", "EN": "🏭 Basic Facility Information"},
    "pd_header": {"TR": "🧱 Yapısal & Çevresel Riskler", "EN": "🧱 Structural & Environmental Risks"},
    "bi_header": {"TR": "📈 Operasyonel & BI Riskleri", "EN": "📈 Operational & BI Risks"},
    "activity_desc": {"TR": "Tesisin Faaliyetini ve İçeriğini Tanımlayın", "EN": "Describe the Facility's Operations and Contents"},
    "si_pd": {"TR": "Toplam Sigorta Bedeli (PD)", "EN": "Total Sum Insured (PD)"},
    "risk_zone": {"TR": "Deprem Risk Bölgesi", "EN": "Earthquake Risk Zone"},
    "yonetmelik": {"TR": "Deprem Yönetmeliği Dönemi", "EN": "Seismic Code Era"},
    "btype": {"TR": "Yapı Türü", "EN": "Building Type"},
    "kat_sayisi": {"TR": "Kat Sayısı", "EN": "Number of Floors"},
    "zemin": {"TR": "Zemin Sınıfı", "EN": "Soil Class"},
    "yakın_cevre": {"TR": "Tesisin Yakın Çevresi", "EN": "Facility's Immediate Surroundings"},
    "yumusak_kat": {"TR": "Zemin Katta Geniş Vitrin/Cephe (Yumuşak Kat Riski)", "EN": "Large Ground Floor Facade/Windows (Soft Story Risk)"},
    "yumusak_kat_help": {"TR": "Binanızın zemin katı, üst katlara göre daha az perde duvara sahip ve büyük oranda cam cephe/vitrin/garaj kapısı gibi açıklıklardan mı oluşuyor?", "EN": "Does your building's ground floor have significantly fewer shear walls than the upper floors, consisting mostly of open spaces like glass facades, storefronts, or garage doors?"},
    "gross_profit": {"TR": "Yıllık Sigortalanabilir Brüt Kâr (GP)", "EN": "Annual Insurable Gross Profit (GP)"},
    "isp": {"TR": "İş Sürekliliği Planı (İSP)", "EN": "Business Continuity Plan (BCP)"},
    "alternatif_tesis": {"TR": "Alternatif Üretim Tesisi İmkanı", "EN": "Alternative Production Facility"},
    "bi_wait": {"TR": "BI Bekleme Süresi (Muafiyet)", "EN": "BI Waiting Period (Deductible)"},
    "ai_pre_analysis_header": {"TR": "🧠 2. AI Teknik Risk Değerlendirmesi", "EN": "🧠 2. AI Technical Risk Assessment"},
    "results_header": {"TR": "📝 3. Sayısal Hasar Analizi", "EN": "📝 3. Numerical Damage Analysis"},
    "analysis_header": {"TR": "🔍 4. Poliçe Alternatifleri Analizi", "EN": "🔍 4. Policy Alternatives Analysis"},
    "btn_run": {"TR": "Analizi Çalıştır", "EN": "Run Analysis"},
}

# --- YARDIMCI FONKSİYONLAR ---
def tr(key: str) -> str:
    lang = st.session_state.get("lang", "TR")
    return T.get(key, {}).get(lang, key)

def money(x: float) -> str:
    return f"{x:,.0f} ₺".replace(",", ".")

# --- GİRDİ VE HESAPLAMA MODELLERİ ---
@dataclass
class ScenarioInputs:
    si_pd: int = 250_000_000
    yillik_brut_kar: int = 100_000_000
    rg: int = 1
    faaliyet_tanimi: str = "Lüks bir AVM. Alt katlarda otopark, orta katlarda çeşitli (giyim, mücevherat, ev tekstili, elektronik) mağazalar, en üst katta ise yemek alanları (restoranlar) ve çok salonlu bir sinema kompleksi bulunuyor. Geniş cam cephelere sahip."
    yapi_turu: str = "Betonarme"
    yonetmelik_donemi: str = "1998-2018 arası (Varsayılan)"
    kat_sayisi: str = "4-7 kat"
    zemin_sinifi: str = "ZE"
    yakin_cevre: str = "Ana Karada / Düz Ova"
    yumusak_kat_riski: str = "Evet"
    azami_tazminat_suresi: int = 365
    isp_varligi: str = "Var (Test Edilmiş)"
    alternatif_tesis: str = "Yok"
    bitmis_urun_stogu: int = 0
    bi_gun_muafiyeti: int = 30
    # YENİ (v3.2): Bu parametreler artık AI tarafından atanacak
    icerik_hassasiyeti: str = "Orta"
    ffe_riski: str = "Orta"
    kritik_makine_bagimliligi: str = "Orta"
    bina_icerik_profili: str = "Diğer / Varsayılan"

# --- TEKNİK HESAPLAMA ÇEKİRDEĞİ (REVİZE EDİLDİ v3.2) ---
def calculate_pd_damage(s: ScenarioInputs) -> Dict[str, float]:
    FACTORS = {
        "yonetmelik": {"1998 öncesi": 1.25, "1998-2018": 1.00, "2018 sonrası": 0.80},
        "kat_sayisi": {"1-3": 0.95, "4-7": 1.00, "8+": 1.10},
        "zemin": {"ZC": 1.00, "ZA/ZB": 0.85, "ZD": 1.20, "ZE": 1.50},
        "yumusak_kat": {"Hayır": 1.00, "Evet": 1.40},
    }
    base_bina_oran = _DEPREM_ORAN.get(s.rg, 0.13)
    bina_factor = 1.0
    bina_factor *= FACTORS["yonetmelik"].get(s.yonetmelik_donemi.split(' ')[0], 1.0)
    bina_factor *= FACTORS["kat_sayisi"].get(s.kat_sayisi.split(' ')[0], 1.0)
    bina_factor *= FACTORS["zemin"].get(s.zemin_sinifi, 1.0)
    bina_factor *= FACTORS["yumusak_kat"].get(s.yumusak_kat_riski, 1.0)
    
    if s.yapi_turu == "Betonarme" and "1998 öncesi" in s.yonetmelik_donemi: bina_factor *= 1.20
    if s.yapi_turu == "Çelik" and "1998 öncesi" in s.yonetmelik_donemi: bina_factor *= 1.15
    if s.zemin_sinifi in ["ZD", "ZE"] and s.yakin_cevre != "Ana Karada / Düz Ova": bina_factor *= 1.40

    bina_pd_ratio = min(0.60, max(0.01, base_bina_oran * bina_factor))
    
    # REVİZE EDİLDİ (v3.2): Bina/İçerik oranı artık AI tarafından belirlenen profile göre dinamik.
    bina_oran, icerik_oran = BINA_ICERIK_ORANLARI.get(s.bina_icerik_profili, BINA_ICERIK_ORANLARI["Diğer / Varsayılan"])
    si_bina_varsayim = s.si_pd * bina_oran
    si_icerik_varsayim = s.si_pd * icerik_oran
    
    icerik_hassasiyet_carpan = {"Düşük": 0.6, "Orta": 0.8, "Yüksek": 1.0}.get(s.icerik_hassasiyeti, 0.8)
    icerik_pd_ratio = bina_pd_ratio * icerik_hassasiyet_carpan

    bina_hasar = si_bina_varsayim * bina_pd_ratio
    icerik_hasar = si_icerik_varsayim * icerik_pd_ratio
    toplam_pd_hasar = bina_hasar + icerik_hasar
    ortalama_pd_ratio = toplam_pd_hasar / s.si_pd if s.si_pd > 0 else 0
    
    return {"damage_amount": toplam_pd_hasar, "pml_ratio": ortalama_pd_ratio}

def calculate_bi_downtime(pd_ratio: float, s: ScenarioInputs) -> Tuple[int, int]:
    FACTORS = {
        "isp": {"Yok": 1.00, "Var (Test Edilmemiş)": 0.85, "Var (Test Edilmiş)": 0.70},
        "makine_bagimliligi": {"Düşük": 1.00, "Orta": 1.25, "Yüksek": 1.70},
        "alternatif_tesis": {"Yok": 1.0, "Var (kısmi kapasite)": 0.6, "Var (tam kapasite)": 0.2}
    }
    base_repair_days = 30 + (pd_ratio * 300)
    operational_factor = 1.0
    operational_factor *= FACTORS["isp"].get(s.isp_varligi, 1.0)
    operational_factor *= FACTORS["makine_bagimliligi"].get(s.kritik_makine_bagimliligi, 1.0)
    operational_factor *= FACTORS["alternatif_tesis"].get(s.alternatif_tesis, 1.0)
    gross_downtime = int(base_repair_days * operational_factor)
    
    # Yüksek riskli bölgelerde altyapı gecikmesi eklenir
    if s.rg in [1, 2]: gross_downtime += 30

    net_downtime_before_indemnity = gross_downtime - s.bitmis_urun_stogu
    final_downtime = min(s.azami_tazminat_suresi, net_downtime_before_indemnity)
    return max(0, gross_downtime), max(0, int(final_downtime))

# ... (Diğer yardımcı fonksiyonlar aynı kalır)
def get_allowed_options(si_pd: int) -> Tuple[List[str], List[float]]:
    koas_opts = list(KOAS_FACTORS.keys())[:9]; muaf_opts = list(MUAFIYET_FACTORS.keys())[:5]
    if si_pd > 3_500_000_000: koas_opts.extend(list(KOAS_FACTORS.keys())[9:]); muaf_opts.extend(list(MUAFIYET_FACTORS.keys())[5:])
    return koas_opts, muaf_opts
def calculate_premium(si: float, yapi_turu: str, rg: int, koas: str, muaf: float, is_bi: bool = False) -> float:
    base_rate = TARIFE_RATES.get(yapi_turu, TARIFE_RATES["Diğer"])[rg - 1]; prim_bedeli = min(si, 3_500_000_000) if not is_bi else si
    if is_bi: return (prim_bedeli * base_rate * 0.75) / 1000.0
    factor = KOAS_FACTORS.get(koas, 1.0) * MUAFIYET_FACTORS.get(muaf, 1.0)
    return (prim_bedeli * base_rate * factor) / 1000.0
def calculate_net_claim(si_pd: int, hasar_tutari: float, koas: str, muaf_pct: float) -> Dict[str, float]:
    muafiyet_tutari = si_pd * (muaf_pct / 100.0); muafiyet_sonrasi_hasar = max(0.0, hasar_tutari - muafiyet_tutari)
    sirket_pay_orani = float(koas.split('/')[0]) / 100.0; net_tazminat = muafiyet_sonrasi_hasar * sirket_pay_orani
    sigortalida_kalan = hasar_tutari - net_tazminat
    return {"net_tazminat": net_tazminat, "sigortalida_kalan": sigortalida_kalan}

# --- AI FONKSİYONLARI (REVİZE EDİLDİ v3.2) ---
@st.cache_data(show_spinner=False)
def get_ai_driven_parameters(faaliyet_tanimi: str) -> Dict[str, str]:
    default_params = {
        "icerik_hassasiyeti": "Orta",
        "ffe_riski": "Orta",
        "kritik_makine_bagimliligi": "Orta",
        "bina_icerik_profili": "Diğer / Varsayılan"
    }
    if not _GEMINI_AVAILABLE: return default_params
    
    prompt = f"""
    Rolün: Kıdemli bir risk mühendisi ve underwriter.
    Görevin: Tesis tanımını analiz edip, 4 adet risk parametresini en uygun şekilde skorlamak.
    Kısıtlar: Yanıtın SADECE JSON formatında olmalı. Başka hiçbir metin ekleme.

    Tesis Tanımı: "{faaliyet_tanimi}"

    PARAMETRE TANIMLARI VE SEÇİM KRİTERLERİ:

    1.  "icerik_hassasiyeti": Tesis içindeki mal ve ekipmanların sarsıntıya karşı ne kadar hassas olduğu.
        - "Yüksek": İlaç, kimya, yarı iletken, laboratuvar. AVM içindeki mücevherat, elektronik, cam/porselen ürünler. Yüksek ve devrilmeye müsait raf sistemleri.
        - "Orta": Genel imalat, tekstil, metal işleme, mobilya. AVM içindeki giyim mağazaları.
        - "Düşük": Kaba inşaat malzemeleri, hurda metal, blok mermer.

    2.  "ffe_riski": Deprem Sonrası Yangın (Fire Following Earthquake) riski.
        - "Yüksek": Yoğun solvent, yanıcı kimyasallar, gaz hatları, plastik hammaddeler, toz patlaması riski olan (un, şeker) tesisler. AVM'deki restoran mutfakları, gaz hatları.
        - "Orta": Ahşap işleme, kağıt/karton depolama, genel elektrik ve makine parkı.
        - "Düşük": Yanıcı malzeme içermeyen depolar (örn: metal, taş).

    3.  "kritik_makine_bagimliligi": Üretimin/faaliyetin, hasarlanması durumunda yerine konması zor, özel ekipmanlara bağımlılığı.
        - "Yüksek": Özel sipariş üretim hattı (otomotiv), büyük presler, fırınlar, reaktörler. AVM'deki sinema projeksiyon/ses sistemleri, yürüyen merdivenler, merkezi iklimlendirme.
        - "Orta": Standart CNC makineleri, tekstil makineleri, paketleme hatları.
        - "Düşük": Jenerik ekipmanların kullanıldığı, makineye az bağımlı montaj veya depolama faaliyetleri.

    4.  "bina_icerik_profili": Toplam sigorta bedelinin bina ve içerik arasında nasıl dağıldığına dair sektörel profil.
        - "AVM / Otel / Ofis": Bina değeri genellikle içerikten yüksektir. (örn: 60/40)
        - "Üretim Tesisi": Makine/ekipman değeri genellikle bina değerinden yüksektir. (örn: 40/60)
        - "Lojistik Depo": Bina ve içindeki stok değeri genellikle yakındır. (örn: 50/50)
        - "Diğer / Varsayılan": Tanım belirsiz ise kullanılır.

    SADECE ŞU JSON FORMATINDA ÇIKTI ÜRET:
    {{"icerik_hassasiyeti": "...", "ffe_riski": "...", "kritik_makine_bagimliligi": "...", "bina_icerik_profili": "..."}}
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        generation_config = {"temperature": 0.1, "top_p": 0.8, "response_mime_type": "application/json"}
        response = model.generate_content(prompt, generation_config=generation_config)
        params = json.loads(response.text)
        # Gelen veriyi doğrula ve varsayılan değerleri ata
        for key, valid_options in {
            "icerik_hassasiyeti": ['Düşük', 'Orta', 'Yüksek'],
            "ffe_riski": ['Düşük', 'Orta', 'Yüksek'],
            "kritik_makine_bagimliligi": ['Düşük', 'Orta', 'Yüksek'],
            "bina_icerik_profili": list(BINA_ICERIK_ORANLARI.keys())
        }.items():
            if params.get(key) not in valid_options:
                params[key] = default_params[key]
        return params
    except Exception as e:
        st.session_state.errors.append(f"AI Parametre Hatası: {str(e)}\n{traceback.format_exc()}")
        return default_params

@st.cache_data(show_spinner=False)
def generate_comprehensive_assessment(s: ScenarioInputs, triggered_rules: List[str]) -> str: # YENİ FONKSİYON (v3.2)
    if not _GEMINI_AVAILABLE: return "AI servisi aktif değil."
    
    prompt = f"""
    Rolün: Dünya standartlarında bir deprem risk mühendisi ve kıdemli hasar eksperi. TariffEQ platformu için teknik bir rapor hazırlıyorsun.
    Görevin: Sana verilen kullanıcı girdileri ve sistem tarafından tetiklenen risk faktörlerini kullanarak, iki ana bölümden oluşan detaylı bir risk değerlendirmesi yazmak.
    
    Kesin Kurallar:
    1. Çıktın SADECE Markdown formatında olacak.
    2. Raporun iki ana başlığı olacak: "### 🏛️ 1. Yapısal ve Çevresel Risk Değerlendirmesi" ve "### 🏭 2. Faaliyete Özgü Sektörel Risk Değerlendirmesi".
    3. Her başlık altında, en önemli 2-3 risk faktörünü emoji kullanarak vurgula.
    4. Her faktörü "Tespit:" ve "Etki:" alt başlıklarıyla, kısa ve net cümlelerle açıkla.
    5. "Tespit:" bölümünde, bu riski hangi kullanıcı girdisinden çıkardığını belirt. (örn: Zemin Sınıfı: 'ZE', Faaliyet Tanımı: 'AVM' vb.)
    6. "Etki:" bölümünde, bu riskin hasarı nasıl artıracağını ve potansiyel sonuçlarını (fiziksel, operasyonel) belirt. Varsa bilinen bir deprem referansı (Kocaeli 1999 vb.) ekle.
    7. **Sektörel Değerlendirme Bölümünde (En Önemli Kısım):** Faaliyet tanımının içine dal.
        - "AVM/Otel" görürsen: Geniş cam cephelerin kırılması, yürüyen merdivenlerin hasarı, lüks/kırılabilir stokların (mücevher, elektronik) devrilmesi, otoparktaki araçların üzerine düşebilecek tesisat (sprinkler boruları), sinema ekipmanlarının (projeksiyon, ses sistemi) hassasiyeti ve restoranlardaki gaz hatlarından kaynaklı FFE riskine odaklan.
        - "Üretim" görürsen: Kritik makinelerin (pres, CNC) hassasiyetine, devrilebilecek yüksek raf sistemlerindeki stoklara, kimyasal sızıntı ve FFE riskine odaklan.
        - "Lojistik" görürsen: Yüksek raf sistemlerinin devrilmesi (Pancaking etkisi), sprinkler patlaması sonucu stokların ıslanması ve yangın yüküne odaklan.
    8. Raporun sonunda "###  sonuçsal Beklenti" başlığı altında genel bir değerlendirme ve PML (Potansiyel Maksimum Hasar) beklentisi hakkında kalitatif bir yorum yap (ASLA sayısal oran verme).

    KULLANICI GİRDİLERİ:
    - Faaliyet Tanımı: {s.faaliyet_tanimi}
    - Yapı Türü: {s.yapi_turu}, Yönetmelik: {s.yonetmelik_donemi}, Kat Sayısı: {s.kat_sayisi}
    - Zemin Sınıfı: {s.zemin_sinifi}, Yakın Çevre: {s.yakin_cevre}
    - Yumuşak Kat Riski: {s.yumusak_kat_riski}

    SİSTEM TARAFINDAN TESPİT EDİLEN AKTİF RİSK FAKTÖRLERİ: {triggered_rules}

    Lütfen bu bilgilerle İki Aşamalı Teknik Risk Değerlendirmesini oluştur.
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt, generation_config={"temperature": 0.25})
        return response.text
    except Exception as e:
        st.session_state.errors.append(f"AI Rapor Hatası: {str(e)}\n{traceback.format_exc()}")
        return "AI Teknik Değerlendirme raporu oluşturulamadı."


# --- STREAMLIT UYGULAMASI ---
def main():
    st.set_page_config(page_title=tr("title"), layout="wide", page_icon="🏗️")
    if 'run_clicked' not in st.session_state: st.session_state.run_clicked = False
    if 'errors' not in st.session_state: st.session_state.errors = []
    st.title(f"🏗️ {tr('title')}")

    s_inputs = st.session_state.get('s_inputs', ScenarioInputs())

    st.header(tr("inputs_header"))
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader(tr("base_header"))
        s_inputs.si_pd = st.number_input(tr("si_pd"), min_value=1_000_000, value=s_inputs.si_pd, step=10_000_000, format="%d")
        s_inputs.faaliyet_tanimi = st.text_area(tr("activity_desc"), s_inputs.faaliyet_tanimi, height=200, 
            placeholder="Örn: Otomotiv ana sanayiye metal şasi parçaları üreten bir tesis. Tesiste büyük hidrolik presler, CNC makineleri ve robotik kaynak hatları bulunmaktadır. Yüksek raflarda metal rulo stokları depolanmaktadır.")
        
    with col2:
        st.subheader(tr("pd_header"))
        s_inputs.rg = st.select_slider(tr("risk_zone"), options=list(range(1, 8)), value=s_inputs.rg)
        s_inputs.yapi_turu = st.selectbox(tr("btype"), ["Betonarme", "Çelik", "Yığma", "Diğer"], index=["Betonarme", "Çelik", "Yığma", "Diğer"].index(s_inputs.yapi_turu))
        s_inputs.yonetmelik_donemi = st.selectbox(tr("yonetmelik"), ["1998 öncesi (Eski Yönetmelik)", "1998-2018 arası (Varsayılan)", "2018 sonrası (Yeni Yönetmelik)"], index=["1998 öncesi (Eski Yönetmelik)", "1998-2018 arası (Varsayılan)", "2018 sonrası (Yeni Yönetmelik)"].index(s_inputs.yonetmelik_donemi))
        s_inputs.kat_sayisi = st.selectbox(tr("kat_sayisi"), ["1-3 kat", "4-7 kat", "8+ kat"], index=["1-3 kat", "4-7 kat", "8+ kat"].index(s_inputs.kat_sayisi))
        s_inputs.zemin_sinifi = st.selectbox(tr("zemin"), ["ZE", "ZD", "ZC (Varsayılan)", "ZA/ZB (Kaya/Sıkı Zemin)"], index=["ZE", "ZD", "ZC (Varsayılan)", "ZA/ZB (Kaya/Sıkı Zemin)"].index(s_inputs.zemin_sinifi))
        s_inputs.yakin_cevre = st.selectbox(tr("yakın_cevre"), ["Nehir Yatağı / Göl Kenarı / Kıyı Şeridi", "Ana Karada / Düz Ova", "Dolgu Zemin Üzerinde"], index=["Nehir Yatağı / Göl Kenarı / Kıyı Şeridi", "Ana Karada / Düz Ova", "Dolgu Zemin Üzerinde"].index(s_inputs.yakin_cevre))
        s_inputs.yumusak_kat_riski = st.selectbox(tr("yumusak_kat"), ["Hayır", "Evet"], index=["Hayır", "Evet"].index(s_inputs.yumusak_kat_riski), help=tr("yumusak_kat_help"))
        
    with col3:
        st.subheader(tr("bi_header"))
        s_inputs.yillik_brut_kar = st.number_input(tr("gross_profit"), min_value=0, value=s_inputs.yillik_brut_kar, step=10_000_000, format="%d")
        s_inputs.bi_gun_muafiyeti = st.selectbox(tr("bi_wait"), [14, 21, 30, 45, 60], index=[14, 21, 30, 45, 60].index(s_inputs.bi_gun_muafiyeti))
        s_inputs.isp_varligi = st.selectbox(tr("isp"), ["Yok (Varsayılan)", "Var (Test Edilmemiş)", "Var (Test Edilmiş)"], index=["Yok (Varsayılan)", "Var (Test Edilmemiş)", "Var (Test Edilmiş)"].index(s_inputs.isp_varligi))
        s_inputs.alternatif_tesis = st.selectbox(tr("alternatif_tesis"), ["Yok", "Var (kısmi kapasite)", "Var (tam kapasite)"], index=["Yok", "Var (kısmi kapasite)", "Var (tam kapasite)"].index(s_inputs.alternatif_tesis))
        s_inputs.bitmis_urun_stogu = st.number_input("Bitmiş Ürün Stoğu (gün)", value=s_inputs.bitmis_urun_stogu, min_value=0)
        s_inputs.azami_tazminat_suresi = st.number_input("Azami Tazminat Süresi (gün)", value=s_inputs.azami_tazminat_suresi, min_value=0)

    st.markdown("---")
    if st.button(f"🚀 {tr('btn_run')}", use_container_width=True, type="primary"):
        st.session_state.run_clicked = True
        st.session_state.s_inputs = s_inputs
        st.session_state.errors = []

    if st.session_state.run_clicked:
        s_inputs = st.session_state.s_inputs
        
        with st.spinner("AI, tesisinizi analiz ediyor ve risk parametrelerini atıyor..."):
            ai_params = get_ai_driven_parameters(s_inputs.faaliyet_tanimi)
            s_inputs.icerik_hassasiyeti = ai_params["icerik_hassasiyeti"]
            s_inputs.ffe_riski = ai_params["ffe_riski"]
            s_inputs.kritik_makine_bagimliligi = ai_params["kritik_makine_bagimliligi"]
            s_inputs.bina_icerik_profili = ai_params["bina_icerik_profili"]
        
        triggered_rules = []
        if s_inputs.yapi_turu == "Betonarme" and "1998 öncesi" in s_inputs.yonetmelik_donemi: triggered_rules.append("ESKI_YONETMELIK_BETONARME")
        if s_inputs.yapi_turu == "Çelik" and "1998 öncesi" in s_inputs.yonetmelik_donemi: triggered_rules.append("ESKI_YONETMELIK_CELIK")
        if s_inputs.zemin_sinifi in ["ZD", "ZE"] and s_inputs.yakin_cevre != "Ana Karada / Düz Ova": triggered_rules.append("SIVILASMA_RISKI")
        if s_inputs.yumusak_kat_riski == "Evet": triggered_rules.append("YUMUSAK_KAT_RISKI")
        if s_inputs.icerik_hassasiyeti == 'Yüksek' or s_inputs.kritik_makine_bagimliligi == 'Yüksek': triggered_rules.append("SEKTOREL_HASSASIYET")
        if s_inputs.rg in [1, 2]: triggered_rules.append("ALTYAPI_KESINTI_RISKI")

        st.header(tr("ai_pre_analysis_header"))
        with st.spinner("AI Teknik Underwriter'ı iki aşamalı senaryo değerlendirmesi yapıyor..."):
            assessment_report = generate_comprehensive_assessment(s_inputs, triggered_rules)
            st.markdown(assessment_report, unsafe_allow_html=True)
            
        pd_results = calculate_pd_damage(s_inputs)
        pd_damage_amount = pd_results["damage_amount"]
        pd_ratio = pd_results["pml_ratio"]
        gross_bi_days, net_bi_days_raw = calculate_bi_downtime(pd_ratio, s_inputs)
        net_bi_days_final = max(0, net_bi_days_raw - s_inputs.bi_gun_muafiyeti)
        bi_damage_amount = (s_inputs.yillik_brut_kar / 365.0) * net_bi_days_final if s_inputs.yillik_brut_kar > 0 else 0
        
        st.header(tr("results_header"))
        m1, m2, m3 = st.columns(3)
        m1.metric("Beklenen PD Hasar Tutarı", money(pd_damage_amount), f"PML: {pd_ratio:.2%}")
        m2.metric("Brüt / Net İş Kesintisi", f"{gross_bi_days} / {net_bi_days_final} gün", "Onarım / Tazmin edilebilir")
        m3.metric("Beklenen BI Hasar Tutarı", money(bi_damage_amount))
        
        st.markdown("---")
        st.header(tr("analysis_header"))
        koas_opts, muaf_opts = get_allowed_options(s_inputs.si_pd)
        results = []
        for koas in koas_opts:
            for muaf in muaf_opts:
                prim_pd = calculate_premium(s_inputs.si_pd, s_inputs.yapi_turu, s_inputs.rg, koas, muaf)
                prim_bi = calculate_premium(s_inputs.yillik_brut_kar, s_inputs.yapi_turu, s_inputs.rg, koas, muaf, is_bi=True)
                toplam_prim = prim_pd + prim_bi
                pd_claim = calculate_net_claim(s_inputs.si_pd, pd_damage_amount, koas, muaf)
                total_payout = pd_claim["net_tazminat"] + bi_damage_amount
                retained_risk = (pd_damage_amount + bi_damage_amount) - total_payout
                verimlilik_skoru = (total_payout / toplam_prim if toplam_prim > 0 else 0) - (retained_risk / s_inputs.si_pd if s_inputs.si_pd > 0 else 0)
                results.append({"Poliçe Yapısı": f"{koas} / {muaf}%", "Yıllık Toplam Prim": toplam_prim, "Toplam Net Tazminat": total_payout, "Sigortalıda Kalan Risk": retained_risk, "Verimlilik Skoru": verimlilik_skoru})
        df = pd.DataFrame(results).sort_values("Verimlilik Skoru", ascending=False).reset_index(drop=True)
        
        tab1, tab2 = st.tabs(["📈 Tablo Analizi", "📊 Görsel Analiz"])
        with tab1:
            st.dataframe(df.style.format({"Yıllık Toplam Prim": money, "Toplam Net Tazminat": money, "Sigortalıda Kalan Risk": money, "Verimlilik Skoru": "{:.2f}"}), use_container_width=True)
        with tab2:
            fig = px.scatter(df, x="Yıllık Toplam Prim", y="Sigortalıda Kalan Risk", color="Verimlilik Skoru", color_continuous_scale=px.colors.sequential.Viridis, hover_data=["Poliçe Yapısı", "Toplam Net Tazminat", "Verimlilik Skoru"], title="Poliçe Alternatifleri Maliyet-Risk Analizi")
            fig.update_layout(xaxis_title="Yıllık Toplam Prim", yaxis_title="Hasarda Şirketinizde Kalacak Risk", coloraxis_colorbar_title_text = 'Verimlilik')
            st.plotly_chart(fig, use_container_width=True)
            
    if st.session_state.errors:
        with st.sidebar.expander("⚠️ Geliştirici Hata Logları", expanded=False):
            for error in st.session_state.errors:
                st.code(error)

if __name__ == "__main__":
    main()
