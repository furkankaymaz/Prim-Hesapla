# -*- coding: utf-8 -*-
#
# TariffEQ – Profesyonel ve AI Destekli PD & BI Hasar Analiz Aracı
# =======================================================================
# Bu Streamlit uygulaması, reasürans ve katastrofik modelleme metodolojilerinden
# esinlenerek geliştirilmiş parametreler ve tarifeye tam uyumlu hesaplama
# mantığı ile ticari/sınai rizikolar için profesyonel seviyede bir deprem
# hasar analizi sunar.
#
# REVİZYON NOTLARI (Ağustos 2025):
# 1. AI Parametre Çıkarımı: Daha sağlam, deterministik ve tutarlı sonuçlar için
#    prompt mühendisliği, JSON şema zorlaması ve retry mekanizması eklendi.
# 2. AI Raporlama: Rapor, sayısal çıktılara doğrudan referans veren, aksiyon
#    odaklı ve müşteri yöneticisi tonunda olacak şekilde yeniden tasarlandı.
# 3. Kod Kalitesi: Okunabilirlik ve bakım kolaylığı için mapping dict'leri eklendi.
# 4. Analitik Derinlik: Poliçe alternatiflerini karşılaştırmak için "Verimlilik Skoru"
#    hesaplaması ve görselleştirmesi eklendi.
# 5. Performans: AI çağrıları, maliyet ve gecikmeyi azaltmak için cache'lendi.
# 6. UI/UX: Yardım metinleri sadeleştirildi, hata yönetimi iyileştirildi.

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

# --- ÇEVİRİ SÖZLÜĞÜ (Sadeleştirilmiş Yardım Metinleri ile) ---
T = {
    "title": {"TR": "TariffEQ – Profesyonel Risk Analizi", "EN": "TariffEQ – Professional Risk Analysis"},
    "inputs_header": {"TR": "📊 1. Senaryo Girdileri", "EN": "📊 1. Scenario Inputs"},
    "base_header": {"TR": "🏭 Temel Tesis Bilgileri", "EN": "🏭 Basic Facility Information"},
    "pd_header": {"TR": "🧱 PD Risk Parametreleri", "EN": "🧱 PD Risk Parameters"},
    "bi_header": {"TR": "📈 BI Risk Parametreleri", "EN": "📈 BI Risk Parameters"},
    "activity_desc": {"TR": "Tesisin Faaliyet Tanımı", "EN": "Facility Activity Description"},
    "activity_desc_help": {"TR": "AI'ın riskleri doğru analiz etmesi için faaliyetinizi kısaca açıklayın (örn: 'metal levha presleme ve otomotiv parça üretimi').", "EN": "Briefly describe your operations for accurate AI risk analysis (e.g., 'metal sheet pressing and automotive parts manufacturing')."},
    "si_pd": {"TR": "PD Toplam Sigorta Bedeli", "EN": "PD Total Sum Insured"},
    "si_pd_help": {"TR": "Bina, makine, emtia dahil tüm maddi varlıkların toplam güncel değeri.", "EN": "Total current value of all physical assets, including building, machinery, and stock."},
    "risk_zone": {"TR": "Deprem Risk Bölgesi", "EN": "Earthquake Risk Zone"},
    "risk_zone_help": {"TR": "Tesisin bulunduğu resmi deprem tehlike bölgesi (1 en riskli).", "EN": "The official seismic hazard zone of the facility (1 is the highest risk)."},
    "yonetmelik": {"TR": "Deprem Yönetmeliği Dönemi", "EN": "Seismic Code Era"},
    "yonetmelik_help": {"TR": "Binanın inşaat veya güçlendirme yılına göre ait olduğu yönetmelik. Bina dayanıklılığını belirler.", "EN": "The code corresponding to the building's construction/retrofit year. Determines structural resilience."},
    "btype": {"TR": "Yapı Türü", "EN": "Building Type"},
    "btype_help": {"TR": "Binanın ana taşıyıcı sistemi. Prim hesabında kullanılır.", "EN": "The main structural system of the building. Used in premium calculation."},
    "kat_sayisi": {"TR": "Kat Sayısı", "EN": "Number of Floors"},
    "kat_sayisi_help": {"TR": "Binanın toplam kat adedi.", "EN": "The total number of floors in the building."},
    "zemin": {"TR": "Zemin Sınıfı", "EN": "Soil Class"},
    "zemin_help": {"TR": "Tesisin zemin yapısı (ZA: Kaya, ZE: En Yumuşak). Bilinmiyorsa 'ZC' seçilebilir.", "EN": "The facility's soil type (ZA: Rock, ZE: Softest). If unknown, select 'ZC'."},
    "duzensizlik": {"TR": "Yapısal Düzensizlik Riski", "EN": "Structural Irregularity Risk"},
    "duzensizlik_help": {"TR": "'Yumuşak kat' veya 'kısa kolon' gibi bilinen bir yapısal zafiyet var mı?", "EN": "Are there known structural weaknesses like 'soft story' or 'short columns'?"},
    "sprinkler": {"TR": "Sprinkler Sistemi Varlığı", "EN": "Sprinkler System Presence"},
    "sprinkler_help": {"TR": "Otomatik yangın söndürme sistemi var mı? Yangın riskini azaltır.", "EN": "Is there an automatic fire sprinkler system? It reduces fire risk."},
    "gross_profit": {"TR": "Yıllık Brüt Kâr (GP)", "EN": "Annual Gross Profit (GP)"},
    "gross_profit_help": {"TR": "İş durması halinde kaybedilecek, sigortalanabilir yıllık brüt kâr.", "EN": "The insurable annual gross profit that would be lost during an interruption."},
    "azami_tazminat": {"TR": "Azami Tazminat Süresi", "EN": "Max. Indemnity Period"},
    "azami_tazminat_help": {"TR": "Hasar sonrası kar kaybınızın sigorta tarafından karşılanacağı maksimum süre.", "EN": "The maximum period for which loss of profit is covered by insurance post-loss."},
    "isp": {"TR": "İş Sürekliliği Planı (İSP)", "EN": "Business Continuity Plan (BCP)"},
    "isp_help": {"TR": "Kriz anında operasyonları sürdürmek için yazılı ve test edilmiş bir plan var mı?", "EN": "Is there a written, tested plan to continue operations during a crisis?"},
    "ramp_up": {"TR": "Üretimin Normale Dönme Hızı", "EN": "Production Ramp-up Speed"},
    "ramp_up_help": {"TR": "Onarım sonrası üretimin tekrar %100 kapasiteye ulaşma hızı.", "EN": "The speed at which production returns to 100% capacity after repairs."},
    "stok": {"TR": "Bitmiş Ürün Stoğu (Gün)", "EN": "Finished Goods Stock (Days)"},
    "stok_help": {"TR": "Üretim dursa bile, mevcut stokla kaç gün satış yapabilirsiniz?", "EN": "For how many days can you continue sales with existing stock if production stops?"},
    "bi_wait": {"TR": "BI Bekleme Süresi (Gün)", "EN": "BI Waiting Period (days)"},
    "bi_wait_help": {"TR": "Poliçedeki, kar kaybı tazminatı başlamadan önce geçmesi gereken gün sayısı.", "EN": "The policy's deductible period in days before loss of profit compensation starts."},
    "ai_analysis_header": {"TR": "🧠 2. AI Analiz Adımı", "EN": "🧠 2. AI Analysis Step"},
    "results_header": {"TR": "📝 3. Analiz Sonuçları ve Rapor", "EN": "📝 3. Analysis Results and Report"},
    "analysis_header": {"TR": "🔍 4. Poliçe Alternatifleri Analizi", "EN": "🔍 4. Policy Alternatives Analysis"},
    "btn_run": {"TR": "Analizi Çalıştır", "EN": "Run Analysis"},
    "table_analysis": {"TR": "📈 Tablo Analizi", "EN": "📈 Table Analysis"},
    "visual_analysis": {"TR": "📊 Görsel Analiz", "EN": "📊 Visual Analysis"},
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
    rg: int = 3
    faaliyet_tanimi: str = "Plastik enjeksiyon ve kalıp üretimi yapan bir fabrika."
    yapi_turu: str = "Betonarme"
    yonetmelik_donemi: str = "1998-2018 arası"
    kat_sayisi: str = "4-7 kat"
    zemin_sinifi: str = "ZC"
    yapısal_duzensizlik: str = "Yok"
    sprinkler_varligi: str = "Yok"
    azami_tazminat_suresi: int = 365
    isp_varligi: str = "Yok"
    ramp_up_hizi: str = "Orta"
    bitmis_urun_stogu: int = 15
    bi_gun_muafiyeti: int = 14
    icerik_hassasiyeti: str = "Orta"
    ffe_riski: str = "Orta"
    kritik_makine_bagimliligi: str = "Orta"

# --- TEKNİK HESAPLAMA ÇEKİRDEĞİ ---
def get_risk_segment(si_pd: int) -> str:
    if si_pd < 150_000_000: return "KOBİ / Yerel Üretici"
    if si_pd < 1_000_000_000: return "Ticari / Ulusal Ölçekli"
    return "Büyük Kurumsal / Global"

def calculate_pd_ratio(s: ScenarioInputs) -> float:
    # REVİZYON: Okunabilirlik için çarpanlar mapping dict'lerine dönüştürüldü.
    FACTORS = {
        "yapi_turu": {"Betonarme": 1.0, "Çelik": 0.85, "Yığma": 1.20, "Diğer": 1.1},
        "yonetmelik": {"1998 öncesi": 1.25, "1998-2018": 1.00, "2018 sonrası": 0.80},
        "kat_sayisi": {"1-3": 0.95, "4-7": 1.00, "8+": 1.10},
        "zemin": {"ZC": 1.00, "ZA/ZB": 0.85, "ZD": 1.20, "ZE": 1.50},
        "duzensizlik": {"Yok": 1.00, "Var": 1.40},
        "icerik_hassasiyeti": {"Düşük": 0.80, "Orta": 1.00, "Yüksek": 1.30},
        "ffe_riski": {"Düşük": 1.00, "Orta": 1.15, "Yüksek": 1.40}
    }
    
    base = _DEPREM_ORAN.get(s.rg, 0.13)
    factor = 1.0
    factor *= FACTORS["yapi_turu"].get(s.yapi_turu, 1.0)
    factor *= FACTORS["yonetmelik"].get(s.yonetmelik_donemi.split(' ')[0], 1.0)
    factor *= FACTORS["kat_sayisi"].get(s.kat_sayisi.split(' ')[0], 1.0)
    factor *= FACTORS["zemin"].get(s.zemin_sinifi.split(' ')[0], 1.0)
    factor *= FACTORS["duzensizlik"].get(s.yapısal_duzensizlik, 1.0)
    factor *= FACTORS["icerik_hassasiyeti"].get(s.icerik_hassasiyeti, 1.0)
    
    ffe_factor = FACTORS["ffe_riski"].get(s.ffe_riski, 1.0)
    if s.sprinkler_varligi == "Var":
        ffe_factor = (ffe_factor - 1) * 0.4 + 1 # Sprinkler FFE ağırlaştırıcı etkisini %60 azaltır
    factor *= ffe_factor
    
    return min(0.70, max(0.01, base * factor))

def calculate_bi_downtime(pd_ratio: float, s: ScenarioInputs) -> Tuple[int, int]:
    # REVİZYON: Okunabilirlik için çarpanlar mapping dict'lerine dönüştürüldü.
    FACTORS = {
        "isp": {"Yok": 1.00, "Var (Test Edilmemiş)": 0.85, "Var (Test Edilmiş)": 0.70},
        "ramp_up": {"Hızlı": 1.10, "Orta": 1.20, "Yavaş": 1.30},
        "makine_bagimliligi": {"Düşük": 1.00, "Orta": 1.25, "Yüksek": 1.60}
    }

    base_repair_days = 30 + (pd_ratio * 300)
    operational_factor = 1.0
    operational_factor *= FACTORS["isp"].get(s.isp_varligi, 1.0)
    operational_factor *= FACTORS["ramp_up"].get(s.ramp_up_hizi, 1.0)
    operational_factor *= FACTORS["makine_bagimliligi"].get(s.kritik_makine_bagimliligi, 1.0)
    
    # REVİZYON: Raporlama için brüt ve net kesinti ayrımı netleştirildi.
    gross_downtime = int(base_repair_days * operational_factor)
    
    # Stoklar ilk darbeyi emer, ancak azami tazminat süresi toplam kesintiyi sınırlar
    net_downtime_before_indemnity = gross_downtime - s.bitmis_urun_stogu
    final_downtime = min(s.azami_tazminat_suresi, net_downtime_before_indemnity)
    
    return max(0, gross_downtime), max(0, int(final_downtime))

def get_allowed_options(si_pd: int) -> Tuple[List[str], List[float]]:
    koas_opts = list(KOAS_FACTORS.keys())[:9]
    muaf_opts = list(MUAFIYET_FACTORS.keys())[:5]
    if si_pd > 3_500_000_000:
        koas_opts.extend(list(KOAS_FACTORS.keys())[9:])
        muaf_opts.extend(list(MUAFIYET_FACTORS.keys())[5:])
    return koas_opts, muaf_opts

def calculate_premium(si: float, yapi_turu: str, rg: int, koas: str, muaf: float, is_bi: bool = False) -> float:
    base_rate = TARIFE_RATES.get(yapi_turu, TARIFE_RATES["Diğer"])[rg - 1]
    prim_bedeli = min(si, 3_500_000_000) if not is_bi else si
    if is_bi: return (prim_bedeli * base_rate * 0.75) / 1000.0 # BI primi genellikle PD'nin %75'i civarıdır
    factor = KOAS_FACTORS.get(koas, 1.0) * MUAFIYET_FACTORS.get(muaf, 1.0)
    return (prim_bedeli * base_rate * factor) / 1000.0

def calculate_net_claim(si_pd: int, hasar_tutari: float, koas: str, muaf_pct: float) -> Dict[str, float]:
    muafiyet_tutari = si_pd * (muaf_pct / 100.0)
    muafiyet_sonrasi_hasar = max(0.0, hasar_tutari - muafiyet_tutari)
    sirket_pay_orani = float(koas.split('/')[0]) / 100.0
    net_tazminat = muafiyet_sonrasi_hasar * sirket_pay_orani
    sigortalida_kalan = hasar_tutari - net_tazminat
    return {"net_tazminat": net_tazminat, "sigortalida_kalan": sigortalida_kalan}

# --- AI FONKSİYONLARI ---
# REVİZYON: Performans için AI çağrıları cache'leniyor
@st.cache_data(show_spinner=False)
def get_ai_driven_parameters(faaliyet_tanimi: str) -> Dict[str, str]:
    default_params = {"icerik_hassasiyeti": "Orta", "ffe_riski": "Orta", "kritik_makine_bagimliligi": "Orta"}
    if not _GEMINI_AVAILABLE: return default_params

    # REVİZYON: Daha sağlam, yönlendirici ve deterministik prompt
    prompt = f"""
    Rolün: Sigorta sektöründe çalışan kıdemli bir deprem risk mühendisi.
    Görevin: Verilen tesis tanımını analiz edip, aşağıda tanımları ve ipuçları verilen üç risk parametresini skorlamak.
    Kısıtlar: Yanıtın SADECE ve SADECE aşağıda belirtilen JSON formatında olmalıdır. Başka hiçbir metin, açıklama veya selamlaşma ekleme. Değerler yalnızca "Düşük", "Orta" veya "Yüksek" olabilir.

    Tesis Tanımı: "{faaliyet_tanimi}"

    Skor Tanımları ve İpuçları:
    - icerik_hassasiyeti: Tesis içindeki makine, ekipman ve stokların sarsıntıya karşı kırılganlığı.
        - Düşük: Sağlam, dökme metal, büyük ve devrilmesi zor stok/makineler (örn: metal işleme atölyesi).
        - Orta: Standart makine parkuru, paketli ürünler (örn: tekstil, plastik enjeksiyon).
        - Yüksek: Hassas elektronikler, cam/seramik ürünler, özel kalibrasyon gerektiren makineler, dökülebilecek kimyasallar (örn: ilaç, laboratuvar, gıda, yarı iletken).
    - ffe_riski (Fire-Following-Earthquake): Deprem sonrası çıkabilecek yangın riski.
        - Düşük: Yanıcı/parlayıcı madde çok az (örn: montaj, depolama).
        - Orta: Standart elektrik ve makine parkuru, ambalaj malzemeleri (örn: gıda, otomotiv parçaları).
        - Yüksek: Yoğun solvent, kimyasal, yanıcı gaz/toz, plastik hammadde, ahşap (örn: kimya, boyahane, mobilya, petrokimya).
    - kritik_makine_bagimliligi: Üretimin, özel ve yeri zor dolacak tek bir makineye veya hatta bağımlılığı.
        - Düşük: Standart, kolayca bulunabilen makineler, yedekli üretim hatları.
        - Orta: Bazı özel makineler var ancak alternatif üreticiler veya yöntemler mevcut.
        - Yüksek: Sipariş üzerine yurt dışından aylar süren teslimatla gelen özel pres, fırın, reaktör veya CNC hattı (örn: otomotiv ana sanayi pres hattı, özel kimyasal reaktörü).

    SADECE ŞU JSON'u DÖNDÜR:
    {{
      "icerik_hassasiyeti": "Düşük|Orta|Yüksek",
      "ffe_riski": "Düşük|Orta|Yüksek",
      "kritik_makine_bagimliligi": "Düşük|Orta|Yüksek"
    }}
    """
    
    for attempt in range(2): # Hata durumunda bir kez daha dene
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            # REVİZYON: Deterministik cevap için generation_config eklendi
            generation_config = {
                "temperature": 0.1,
                "top_p": 0.8,
                "response_mime_type": "application/json",
            }
            response = model.generate_content(prompt, generation_config=generation_config)
            params = json.loads(response.text)
            
            # Gelen veriyi doğrula
            for key in default_params:
                if params.get(key) not in ['Düşük', 'Orta', 'Yüksek']:
                    params[key] = default_params[key]
            return params
        except Exception as e:
            if attempt == 0: continue # İlk hatada tekrar dene
            # REVİZYON: Gizli hata loglaması
            st.session_state.errors.append(f"AI Parametre Hatası: {str(e)}\n{traceback.format_exc()}")
            return default_params
    return default_params

# REVİZYON: Performans için AI çağrıları cache'leniyor
@st.cache_data(show_spinner=False)
def generate_report(s: ScenarioInputs, pd_ratio: float, gross_bi_days: int, net_bi_days: int, pd_damage: float, bi_damage: float) -> str:
    if not _GEMINI_AVAILABLE: return "AI servisi aktif değil. Lütfen API anahtarınızı kontrol edin."
    
    risk_segment = get_risk_segment(s.si_pd)

    # REVİZYON: Daha zengin, sayısal veri odaklı ve yönlendirici prompt
    prompt_template = f"""
    Rolün: Kıdemli bir risk mühendisi, hasar uzmanı ve müşteri yöneticisi karması bir AI danışmanı.
    Görevin: Aşağıdaki verileri kullanarak, sigortalı adayına yönelik profesyonel, anlaşılır ve aksiyon odaklı bir deprem risk raporu hazırlamak.
    Format: Cevabın 3 ana başlık ve her başlığın altında kısa maddeler (bullet points) içermelidir. En sona 3 maddelik bir "Özet Aksiyon Listesi" ekle. Sadece Türkçe cevap ver.

    ---
    **1. Tesis ve Risk Verileri:**
    - Faaliyet Tanımı: {s.faaliyet_tanimi}
    - Risk Segmenti: {risk_segment}
    - PD Sigorta Bedeli: {money(s.si_pd)} | Yıllık Brüt Kâr (GP): {money(s.yillik_brut_kar)}
    - Bina Yapısı: {s.yapi_turu}, {s.kat_sayisi}, {s.yonetmelik_donemi} yönetmeliği
    - Zemin ve Çevresel Riskler: {s.zemin_sinifi} sınıfı zemin, Yapısal Düzensizlik: {s.yapısal_duzensizlik}
    - Operasyonel Hazırlık: İş Sürekliliği Planı: {s.isp_varligi}, Bitmiş Ürün Stoğu: {s.bitmis_urun_stogu} gün

    **2. AI Tarafından Skorlanan Parametreler:**
    - İçerik Hassasiyeti: {s.icerik_hassasiyeti}
    - Deprem Sonrası Yangın (FFE) Riski: {s.ffe_riski}
    - Kritik Makine Bağımlılığı: {s.kritik_makine_bagimliligi}

    **3. Hasar Senaryosu Hesaplama Sonuçları:**
    - Beklenen Maddi Hasar (PD) Oranı: {pd_ratio:.1%} -> Beklenen PD Hasar Tutarı: {money(pd_damage)}
    - Brüt İş Durması Süresi: {gross_bi_days} gün (Onarım + normale dönüş süresi)
    - Net Tazmin Edilebilir İş Durması Süresi: {net_bi_days} gün (Stok ve poliçe bekleme süresi düşüldükten sonra)
    - Beklenen Kar Kaybı (BI) Hasar Tutarı: {money(bi_damage)}
    ---

    Lütfen Raporu Oluştur:
    """

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt_template, generation_config={"temperature": 0.5})
        
        # REVİZYON: Rapora teknik uyumluluk notu ekleniyor
        compliance_note = f"\n\n---\n*<small><b>Teknik Not:</b> Bu rapordaki prim ve tazminat senaryoları, Zorunlu Deprem Sigortası Tarife ve Talimatları Tebliği'nde yer alan yapı tarzı, deprem bölgesi, koasürans ve muafiyet çarpanları ile uyumlu olarak hesaplanmıştır.</small>*"
        return response.text + compliance_note
    except Exception as e:
        st.session_state.errors.append(f"AI Rapor Hatası: {str(e)}\n{traceback.format_exc()}")
        return "AI Raporu oluşturulurken bir hata oluştu. Lütfen daha sonra tekrar deneyin."

# --- STREAMLIT UYGULAMASI ---
def main():
    st.set_page_config(page_title=tr("title"), layout="wide", page_icon="🏗️")
    
    if 'run_clicked' not in st.session_state:
        st.session_state.run_clicked = False
    if 'errors' not in st.session_state:
        st.session_state.errors = []

    st.title(f"🏗️ {tr('title')}")

    s_inputs = ScenarioInputs()

    st.header(tr("inputs_header"))
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader(tr("base_header"))
        s_inputs.faaliyet_tanimi = st.text_area(tr("activity_desc"), s_inputs.faaliyet_tanimi, height=150, help=tr("activity_desc_help"))
        s_inputs.si_pd = st.number_input(tr("si_pd"), min_value=1_000_000, value=s_inputs.si_pd, step=10_000_000, format="%d", help=tr("si_pd_help"))
        s_inputs.yillik_brut_kar = st.number_input(tr("gross_profit"), min_value=0, value=s_inputs.yillik_brut_kar, step=10_000_000, format="%d", help=tr("gross_profit_help"))
        s_inputs.rg = st.select_slider(tr("risk_zone"), options=[1,2,3,4,5,6,7], value=s_inputs.rg, help=tr("risk_zone_help"))
        s_inputs.yapi_turu = st.selectbox(tr("btype"), ["Betonarme", "Çelik", "Yığma", "Diğer"], help=tr("btype_help"))

    with col2:
        st.subheader(tr("pd_header"))
        s_inputs.yonetmelik_donemi = st.selectbox(tr("yonetmelik"), ["1998-2018 arası (Varsayılan)", "2018 sonrası (Yeni Yönetmelik)", "1998 öncesi (Eski Yönetmelik)"], help=tr("yonetmelik_help"))
        s_inputs.kat_sayisi = st.selectbox(tr("kat_sayisi"), ["4-7 kat (Varsayılan)", "1-3 kat", "8+ kat"], help=tr("kat_sayisi_help"))
        s_inputs.zemin_sinifi = st.selectbox(tr("zemin"), ["ZC (Varsayılan)", "ZA/ZB (Kaya/Sıkı Zemin)", "ZD (Orta Gevşek)", "ZE (Yumuşak/Gevşek)"], help=tr("zemin_help"))
        s_inputs.yapısal_duzensizlik = st.selectbox(tr("duzensizlik"), ["Yok", "Var"], help=tr("duzensizlik_help"))
        s_inputs.sprinkler_varligi = st.radio(tr("sprinkler"), ["Yok", "Var"], index=0, horizontal=True, help=tr("sprinkler_help"))

    with col3:
        st.subheader(tr("bi_header"))
        s_inputs.azami_tazminat_suresi = st.selectbox(tr("azami_tazminat"), [365, 540, 730], format_func=lambda x: f"{int(x/30)} Ay", help=tr("azami_tazminat_help"))
        s_inputs.isp_varligi = st.selectbox(tr("isp"), ["Yok (Varsayılan)", "Var (Test Edilmemiş)", "Var (Test Edilmiş)"], help=tr("isp_help"))
        s_inputs.ramp_up_hizi = st.selectbox(tr("ramp_up"), ["Orta (Varsayılan)", "Hızlı", "Yavaş"], help=tr("ramp_up_help"))
        s_inputs.bitmis_urun_stogu = st.number_input(tr("stok"), value=s_inputs.bitmis_urun_stogu, min_value=0, help=tr("stok_help"))
        s_inputs.bi_gun_muafiyeti = st.number_input(tr("bi_wait"), min_value=0, value=s_inputs.bi_gun_muafiyeti, step=1, help=tr("bi_wait_help"))
    
    st.markdown("---")
    if st.button(f"🚀 {tr('btn_run')}", use_container_width=True, type="primary"):
        st.session_state.run_clicked = True
        st.session_state.s_inputs = s_inputs
        st.session_state.errors = [] # Analiz her çalıştığında hataları temizle

    if st.session_state.run_clicked:
        s_inputs = st.session_state.s_inputs
        
        with st.spinner("AI, tesisinizi analiz ediyor ve risk parametrelerini atıyor..."):
            ai_params = get_ai_driven_parameters(s_inputs.faaliyet_tanimi)
            s_inputs.icerik_hassasiyeti = ai_params["icerik_hassasiyeti"]
            s_inputs.ffe_riski = ai_params["ffe_riski"]
            s_inputs.kritik_makine_bagimliligi = ai_params["kritik_makine_bagimliligi"]

        st.header(tr("ai_analysis_header"))
        risk_segment = get_risk_segment(s_inputs.si_pd)
        st.info(f"**AI Analiz Özeti:** Tesisiniz, girilen sigorta bedeline göre **'{risk_segment}'** segmentinde değerlendirilmiştir. Faaliyet tanımınız analiz edilerek aşağıdaki parametreler hesaplamaya otomatik olarak dahil edilmiştir:", icon="💡")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("İçerik Hassasiyeti", s_inputs.icerik_hassasiyeti, help="AI, varlıkların (makine, emtia) hasara karşı hassasiyetini bu şekilde skorladı.")
        c2.metric("Deprem Sonrası Yangın Riski", s_inputs.ffe_riski, help="AI, faaliyetinizdeki yanıcı madde yoğunluğuna göre ikincil yangın riskini bu şekilde skorladı.")
        c3.metric("Kritik Makine Bağımlılığı", s_inputs.kritik_makine_bagimliligi, help="AI, üretiminizin ne kadar özel ve yeri zor dolacak makinelere bağlı olduğunu bu şekilde skorladı.")
        
        pd_ratio = calculate_pd_ratio(s_inputs)
        gross_bi_days, net_bi_days_raw = calculate_bi_downtime(pd_ratio, s_inputs)
        pd_damage_amount = s_inputs.si_pd * pd_ratio
        
        # Kar kaybı tazminatı, poliçe bekleme süresinden sonra başlar
        net_bi_days_final = max(0, net_bi_days_raw - s_inputs.bi_gun_muafiyeti)
        bi_damage_amount = (s_inputs.yillik_brut_kar / 365.0) * net_bi_days_final if s_inputs.yillik_brut_kar > 0 else 0

        st.header(tr("results_header"))
        with st.spinner("AI Deprem Hasar Uzmanı, nihai raporu ve tavsiyeleri hazırlıyor..."):
            report = generate_report(s_inputs, pd_ratio, gross_bi_days, net_bi_days_final, pd_damage_amount, bi_damage_amount)
            st.markdown(report, unsafe_allow_html=True)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Beklenen PD Hasar Tutarı", money(pd_damage_amount), f"PD Oranı: {pd_ratio:.2%}")
        m2.metric("Brüt / Net İş Kesintisi", f"{gross_bi_days} / {net_bi_days_final} gün", "Onarım / Tazmin edilebilir")
        m3.metric("Beklenen BI Hasar Tutarı", money(bi_damage_amount))
        
        st.markdown("---")
        st.header(tr("analysis_header"))
        
        # REVİZYON: Tarife varyantları hakkında bilgilendirme notu
        if s_inputs.si_pd > 3_500_000_000:
            st.info("ℹ️ Sigorta bedeliniz 3.5 Milyar TL'yi aştığı için, tarife dışı daha esnek koasürans ve muafiyet seçenekleri de analize dahil edilmiştir.", icon="ℹ️")

        koas_opts, muaf_opts = get_allowed_options(s_inputs.si_pd)
        results = []
        for koas in koas_opts:
            for muaf in muaf_opts:
                prim_pd = calculate_premium(s_inputs.si_pd, s_inputs.yapi_turu, s_inputs.rg, koas, muaf)
                prim_bi = calculate_premium(s_inputs.yillik_brut_kar, s_inputs.yapi_turu, s_inputs.rg, koas, muaf, is_bi=True)
                toplam_prim = prim_pd + prim_bi
                
                pd_claim = calculate_net_claim(s_inputs.si_pd, pd_damage_amount, koas, muaf)
                total_damage = pd_damage_amount + bi_damage_amount
                total_payout = pd_claim["net_tazminat"] + bi_damage_amount
                retained_risk = total_damage - total_payout
                
                # REVİZYON: Verimlilik Skoru hesaplaması eklendi
                verimlilik_skoru = (total_payout / toplam_prim if toplam_prim > 0 else 0) - (retained_risk / s_inputs.si_pd if s_inputs.si_pd > 0 else 0)

                results.append({
                    "Poliçe Yapısı": f"{koas} / {muaf}%", "Yıllık Toplam Prim": toplam_prim,
                    "Toplam Net Tazminat": total_payout, "Sigortalıda Kalan Risk": retained_risk,
                    "Verimlilik Skoru": verimlilik_skoru
                })
        df = pd.DataFrame(results).sort_values("Verimlilik Skoru", ascending=False).reset_index(drop=True)

        tab1, tab2 = st.tabs([tr("table_analysis"), tr("visual_analysis")])
        with tab1:
            st.markdown("Aşağıdaki tabloda, tüm olası poliçe yapıları için **maliyet (prim)** ve hasar sonrası **net durumunuzu** karşılaştırabilirsiniz. En verimli seçenekler üste sıralanmıştır.")
            st.dataframe(df.style.format({
                "Yıllık Toplam Prim": money, 
                "Toplam Net Tazminat": money, 
                "Sigortalıda Kalan Risk": money,
                "Verimlilik Skoru": "{:.2f}"
            }), use_container_width=True)
        
        with tab2:
            st.markdown("Bu grafik, en verimli poliçe alternatifini bulmanıza yardımcı olur. **Amaç, sol alt köşeye en yakın noktayı bulmaktır.** Bu noktalar, hem **düşük prim** ödeyeceğiniz hem de hasar anında **şirketinizde en az riskin kalacağı** en verimli seçenekleri temsil eder.")
            
            # REVİZYON: Hover'a Verimlilik Skoru eklendi
            fig = px.scatter(
                df, x="Yıllık Toplam Prim", y="Sigortalıda Kalan Risk",
                color="Verimlilik Skoru", color_continuous_scale=px.colors.sequential.Viridis,
                hover_data=["Poliçe Yapısı", "Toplam Net Tazminat", "Verimlilik Skoru"], 
                title="Poliçe Alternatifleri Maliyet-Risk Analizi"
            )
            fig.update_traces(marker=dict(size=10, line=dict(width=1, color='DarkSlateGrey')))
            fig.update_layout(
                xaxis_title="Yıllık Toplam Prim (Düşük olması hedeflenir)", 
                yaxis_title="Hasarda Şirketinizde Kalacak Risk (Düşük olması hedeflenir)",
                coloraxis_colorbar_title_text = 'Verimlilik'
            )
            st.plotly_chart(fig, use_container_width=True)

    # REVİZYON: Gizli hata loglaması için sidebar expander'ı
    if st.session_state.errors:
        with st.sidebar.expander("⚠️ Geliştirici Hata Logları", expanded=False):
            for error in st.session_state.errors:
                st.code(error)

if __name__ == "__main__":
    main()
