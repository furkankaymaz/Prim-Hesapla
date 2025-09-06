# -*- coding: utf-8 -*-
#
# TariffEQ – Hibrit Zekâ Destekli PD & BI Hasar Analiz Aracı (v6.4.1)
# =======================================================================
# Bu Streamlit uygulaması, reasürans ve katastrofik modelleme metodolojilerinden
# esinlenerek geliştirilmiş parametreler ve tarifeye tam uyumlu hesaplama
# mantığı ile ticari/sınai rizikolar için profesyonel seviyede bir deprem
# hasar analizi sunar.
#
# GÜNCEL REVİZYON NOTLARI (Eylül 2025 - v6.4.1 - Arama Entegrasyonu Güvenli)
# 1) Gemini Web Araştırması Güvenli Aç/Kapa:
#    - google-generativeai kütüphanesinde bazı versiyonlarda `google_search` / `google_search_retrieval`
#      tool isimleri desteklenmediğinde "Unknown field for FunctionDeclaration" hatası doğuyordu.
#    - Artık model, arama aracını DENE/GERİ DÖN yaklaşımıyla yükler: önce `google_search`, sonra
#      `google_search_retrieval`, ikisi de başarısızsa araçsız çalışıp heuristik üretir.
# 2) Araştırma Talimatları Prompt’a Gömülü:
#    - AI, aktif arama aracı bulursa web’den (AFAD, MTA, USGS, üretici bültenleri vb.) güncel kanıt toplar;
#      aksi halde aynı maddeleri heuristikle gerekçelendirir.
# 3) UI, metrikler ve tablo/grafik yapısı DEĞİŞMEDİ.

import streamlit as st
import pandas as pd
import plotly.express as px
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import json
import traceback
import os

# --- AI İÇİN KORUMALI IMPORT VE GÜVENLİ KONFİGÜRASYON ---
_GEMINI_AVAILABLE = False
try:
    import google.generativeai as genai
    _api_key = (st.secrets.get("GEMINI_API_KEY") if hasattr(st, "secrets") else None) or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if _api_key:
        genai.configure(api_key=_api_key)
        _GEMINI_AVAILABLE = True
    else:
        st.sidebar.warning("Gemini API anahtarı bulunamadı. AI özellikleri devre dışı.", icon="🔑")
        _GEMINI_AVAILABLE = False
except Exception:
    st.sidebar.error("Google AI kütüphanesi yüklenemedi. AI özellikleri devre dışı.", icon="🤖")
    _GEMINI_AVAILABLE = False


# --- AI PROMPTLARI ---

# ESKİ NİTEL RAPORLAMA PROMPTU (Tüm Tesis Tipleri İçin)
def get_qualitative_assessment_prompt(s: 'ScenarioInputs', triggered_rules: List[str]) -> str:
    if s.tesis_tipi == tr("endustriyel_tesis"):
        p = s.industrial_params
        return f"""
        Rolün: TariffEQ için çalışan uzman bir AI teknik underwriter'ı (Endüstriyel Tesisler).
        Görevin: Sana iletilen yapılandırılmış ve serbest metin girdilerini sentezleyerek, en önemli 2-3 risk faktörünü seçip görsel ve ikna edici bir "AI Teknik Risk Değerlendirmesi" oluşturmak.
        Kesin Kurallar: Başlık "### 🧠 AI Teknik Risk Değerlendirmesi (Endüstriyel Tesis)" olacak. Emoji kullan (🧱, 💧, 🏭, 🔧).
        Her faktörü "Tespit:" ve "Etki:" ile açıkla. Sonunda "Sonuçsal Beklenti:" başlığıyla kalitatif yorum yap. ASLA PML oranı verme.
        Gerekçelendirme Talimatı: 'Tespitlerini' yaparken, hem yapılandırılmış girdilerden (örn: 'Yönetmelik: 1998 öncesi') hem de serbest metindeki anahtar kelimelerden (örn: metindeki 'pres hattı' kelimesi) çıkarımlar yap.
        ---
        YAPILANDIRILMIŞ GİRDİLER: Yapı Türü: {p.yapi_turu}, Yönetmelik: {p.yonetmelik_donemi}, Zemin: {p.zemin_sinifi}, Yakın Çevre: {p.yakin_cevre}, Yumuşak Kat: {p.yumusak_kat_riski}
        SERBEST METİN (Ek Detaylar): "{p.faaliyet_tanimi}"
        SİSTEM TARAFINDAN TESPİT EDİLEN AKTİF RİSK FAKTÖRLERİ: {triggered_rules}
        ---
        Lütfen bu bilgilerle Teknik Risk Değerlendirmesini oluştur.
        """
    elif s.tesis_tipi == tr("res"):
        p = s.res_params
        return f"""
        Rolün: TariffEQ için çalışan uzman bir AI teknik underwriter'ı (Rüzgar Enerji Santralleri).
        Gerekçelendirme Talimatı: 'Tespitlerini' yaparken, hem yapılandırılmış girdilerden (örn: 'Türbin Yaşı: 10+ yıl') hem de serbest metindeki anahtar kelimelerden (örn: metindeki 'Nordex N90' ifadesi) çıkarımlar yap. 'YUMUSAK_ZEMIN' için 'salınım (rocking) etkisi' ve 'kule-temel birleşimi' risklerini vurgula. 'ESKI_TEKNOLOJI' için 'dişli kutusu (gearbox) hizalanması' ve 'metal yorgunluğu' risklerini vurgula. 'STANDART_SALT_SAHASI' için ise 'porselen izolatör' kırılganlığının BI için en zayıf halka olduğunu belirt.
        ---
        YAPILANDIRILMIŞ GİRDİLER: Türbin Yaşı: {p.turbin_yas}, Arazi Durumu: {p.arazi_jeoteknik}, Şalt Sahası: {p.salt_sahasi}, Risk Bölgesi: {s.rg}
        SERBEST METİN (Ek Detaylar): "{p.ek_detaylar}"
        SİSTEM TARAFINDAN TESPİT EDİLEN AKTİF RİSK FAKTÖRLERİ: {triggered_rules}
        ---
        Lütfen bu bilgilerle "### 🧠 AI Teknik Risk Değerlendirmesi (Rüzgar Enerji Santrali)" başlıklı, emojili (💨, 🏔️, ⚡️), "Tespit:", "Etki:", "Sonuçsal Beklenti:" içeren, PML oranı belirtmeyen bir Markdown raporu oluştur.
        """
    elif s.tesis_tipi == tr("ges"):
        p = s.ges_params
        return f"""
        Rolün: TariffEQ için çalışan uzman bir AI teknik underwriter'ı (Güneş Enerji Santralleri).
        Gerekçelendirme Talimatı: 'Tespitlerini' yaparken, girdilerden çıkarımlar yap. 'Tracker' için mekanik zafiyet, 'Eğimli Arazi' için şev stabilitesi/zincirleme hasar, 'Merkezi İnverter' için ise 'tek hata noktası' ve BI riskini vurgula.
        ---
        YAPILANDIRILMIŞ GİRDİLER: Panel Montaj Tipi: {p.panel_montaj_tipi}, Arazi Topoğrafyası: {p.arazi_topografyasi}, İnverter Mimarisi: {p.inverter_mimarisi}
        SERBEST METİN (Ek Detaylar): "{p.ek_detaylar}"
        SİSTEM TARAFINDAN TESPİT EDİLEN AKTİF RİSK FAKTÖRLERİ: {triggered_rules}
        ---
        Lütfen bu bilgilerle "### 🧠 AI Teknik Risk Değerlendirmesi (Güneş Enerji Santrali)" başlıklı, emojili (☀️, 🏞️, 🔌), "Tespit:", "Etki:", "Sonuçsal Beklenti:" içeren, PML oranı belirtmeyen bir Markdown raporu oluştur.
        """
    elif s.tesis_tipi == tr("hes"):
        p = s.hes_params
        return f"""
        Rolün: TariffEQ için çalışan uzman bir AI teknik underwriter'ı (Hidroelektrik Santraller).
        Gerekçelendirme Talimatı: 'Tespitlerini' yaparken, '1990 öncesi' için eski sismik tasarım kodlarına, 'Toprak/Kaya Dolgu' için içsel erozyon ve şev stabilitesi risklerine, 'Gövdeye Bitişik Santral' için ise türbin-jeneratör hizalanmasının bozulması riskine ve bunun BI'a olan kritik etkisine odaklan.
        ---
        YAPILANDIRILMIŞ GİRDİLER: Baraj Tipi: {p.baraj_tipi}, Tesis Yılı: {p.tesis_yili}, Santral Konumu: {p.santral_konumu}
        SERBEST METİN (Ek Detaylar): "{p.ek_detaylar}"
        SİSTEM TARAFINDAN TESPİT EDİLEN AKTİF RİSK FAKTÖRLERİ: {triggered_rules}
        ---
        Lütfen bu bilgilerle "### 🧠 AI Teknik Risk Değerlendirmesi (Hidroelektrik Santral)" başlıklı, emojili (🌊, 🏗️, ⚙️), "Tespit:", "Etki:", "Sonuçsal Beklenti:" içeren, PML oranı belirtmeyen bir Markdown raporu oluştur.
        """
    return "Seçilen tesis tipi için AI değerlendirmesi henüz aktif değil."


# HİBRİT ZEKA ANALİST PROMPTU (Araştırma talimatları eklendi)
AI_ANALYST_SYSTEM_PROMPT = r"""
SİSTEM MESAJI — TariffEQ v6.4 • Şeffaf AI ANALİST (Deprem Hasar Kalibrasyonu)
AMAÇ VE SINIRLAR
- Görevin: Kullanıcı girdileri ve serbest metin açıklamasından (faaliyet_tanimi) hareketle deprem kaynaklı PD ve BI hasar kalibrasyon parametrelerini üretmek.
- Çıktın tek parça JSON (aşağıdaki şemaya birebir uy). JSON dışında tek karakter bile yazma.
- Deterministik çalış: temperature ≤ 0.2.
- Türkiye önceliği: TBDY-2018, HAZUS, FEMA P-58, yerel zemin ve YOKE pratikleri.

WEB ARAŞTIRMASI (aktifse):
- Google Search aracı etkinse şu öncelikle aramaları yap, kanıtları meta.notes’a ekle:
  1) AFAD/MTA/TR gov — “deprem tehlike haritası {il}/{ilçe} PGA”, “mikrobölgeleme {ilçe} zemin sınıfı ZC/ZD/ZE sıvılaşma”
  2) TBDY-2018 spektral ivme parametreleri (2018+)
  3) Sektör ekipmanı — “{kritik_ekipman} lead time 2024..2025”, “transformer lead time 2024..2025”
  4) Global endüstriyel deprem etkileri — EERI/USGS/JRC vaka özetleri
- Her kanıtta: iddia + sayı/birim + tarih + yayıncı + URL’yi özetle. Çelişki varsa en güncel ve resmî/akademik olana daha çok ağırlık ver.
- Araca erişimin yoksa aynı başlıkları heuristikle değerlendir, meta.assumptions ve confidence ile belirt.

KALİBRASYON KURALLARI
- pd_base_loss_ratio.* ∈ [0.01, 0.60]
- pd_factor_suggestion.zemin_carpani ∈ [0.85, 1.50]
- pd_factor_suggestion.yoke_carpani ∈ [1.00, 1.60]
- pd_factor_suggestion.ffeq_potansiyel_carpani ∈ [1.00, 2.00]
- pd_factor_suggestion.stok_devrilme_carpani ∈ [1.00, 2.50]
- bi_calibration.kritik_ekipman_durus_carpani ∈ [1.00, 3.00]
- bi_calibration.altyapi_gecikme_ay ∈ [0, 3]
- bi_calibration.tedarik_zinciri_gecikme_ay ∈ [0, 12]
- buffer_bitmis_urun_stogu_gun ∈ [0, 120]
- Sınır dışı değerleri kırp (clamp) ve gerekçeyi meta.notes’a yaz.

YOKE ÇIKARIMI:
- “yüksek raf”, “askılı hat”, “tank”, “boru hattı”, “hassas cihaz”, “merkezi inverter” vb. sinyallerde yoke_carpani ≥ 1.20 yönünde değerlendir; gerekçeyi meta.assumptions’a yaz.

ÇIKTI — ZORUNLU JSON ŞEMASI
{
  "icerik_hassasiyeti": "Düşük|Orta|Yüksek",
  "kritik_makine_bagimliligi": "Düşük|Orta|Yüksek",
  "ffe_riski": "Düşük|Orta|Yüksek",
  "pd_base_loss_ratio_suggestion": {"bina": 0.00, "makine": 0.00, "elektronik": 0.00, "stok": 0.00},
  "pd_factor_suggestion": {"zemin_carpani": 1.00, "yoke_carpani": 1.00, "ffeq_potansiyel_carpani": 1.00, "stok_devrilme_carpani": 1.00},
  "bi_calibration": {"kritik_ekipman_durus_carpani": 1.00, "altyapi_gecikme_ay": 0, "tedarik_zinciri_gecikme_ay": 0, "buffer_bitmis_urun_stogu_gun": 0},
  "risk_flags": ["YUMUSAK_KAT_RISKI","SIVILASMA_RISKI","ESKI_TASARIM_KODU","ALTYAPI_RISKI","MERKEZI_INVERTER_RISKI","TRACKER_RISKI"],
  "meta": {
      "confidence_0to1": 0.00,
      "assumptions": [],
      "notes": "Kanıt/varsayım özetleri; 'Kanıt: ... — Kaynak: ... — Tarih: ... — URL: ...'"
  }
}
"""

# --- TARİFE, ÇARPAN VERİLERİ VE SABİTLER ---
TARIFE_RATES = {
    "Betonarme": [3.13, 2.63, 2.38, 1.94, 1.38, 1.06, 0.75],
    "Çelik":      [3.13, 2.63, 2.38, 1.94, 1.38, 1.06, 0.75],
    "Yığma":      [6.13, 5.56, 3.75, 2.00, 1.56, 1.24, 1.06],
    "Diğer":      [6.13, 5.56, 3.75, 2.00, 1.56, 1.24, 1.06]
}
KOAS_FACTORS = {"80/20": 1.0, "75/25": 0.9375, "70/30": 0.875, "65/35": 0.8125, "60/40": 0.75, "55/45": 0.6875, "50/50": 0.625, "45/55": 0.5625, "40/60": 0.5, "90/10": 1.125, "100/0": 1.25}
MUAFIYET_FACTORS = {2.0: 1.0, 3.0: 0.94, 4.0: 0.87, 5.0: 0.81, 10.0: 0.65, 1.5: 1.03, 1.0: 1.06, 0.5: 1.09, 0.1: 1.12}
_DEPREM_ORAN = {1: 0.20, 2: 0.17, 3: 0.13, 4: 0.09, 5: 0.06, 6: 0.06, 7: 0.06}
_DEF_SPLIT_INDUSTRIAL = {"bina": 0.40, "makine": 0.40, "elektronik": 0.06, "stok": 0.14}


# --- ÇEVİRİ SÖZLÜĞÜ ---
T = {
    "title": {"TR": "TariffEQ – Hibrit Zekâ Destekli Risk Analizi", "EN": "TariffEQ – Hybrid AI-Powered Risk Analysis"},
    "tesis_tipi_secimi": {"TR": "1. Lütfen Analiz Etmek İstediğiniz Tesis Tipini Seçiniz", "EN": "1. Please Select the Facility Type to Analyze"},
    "endustriyel_tesis": {"TR": "Endüstriyel Tesis (Fabrika, Depo vb.)", "EN": "Industrial Facility (Factory, Warehouse etc.)"},
    "res": {"TR": "Enerji Santrali - Rüzgar (RES)", "EN": "Power Plant - Wind (WPP)"},
    "ges": {"TR": "Enerji Santrali - Güneş (GES)", "EN": "Power Plant - Solar (SPP)"},
    "hes": {"TR": "Enerji Santrali - Hidroelektrik (HES)", "EN": "Power Plant - Hydroelectric (HPP)"},
    "inputs_header": {"TR": "📊 2. Senaryo Girdileri", "EN": "📊 2. Scenario Inputs"},
    "base_header": {"TR": "🏭 Temel Bilgiler", "EN": "🏭 Basic Information"},
    "pd_header": {"TR": "🧱 Yapısal & Çevresel Riskler", "EN": "🧱 Structural & Environmental Risks"},
    "bi_header": {"TR": "📈 Operasyonel & BI Riskleri", "EN": "📈 Operational & BI Risks"},
    "res_header": {"TR": "💨 RES'e Özgü Riskler", "EN": "💨 WPP-Specific Risks"},
    "ges_header": {"TR": "☀️ GES'e Özgü Riskler", "EN": "☀️ SPP-Specific Risks"},
    "hes_header": {"TR": "🌊 HES'e Özgü Riskler", "EN": "🌊 HPP-Specific Risks"},
    "activity_desc_industrial": {"TR": "Süreç, Ekipman ve Stoklara Dair Ek Detaylar", "EN": "Additional Details on Processes, Equipment, and Stock"},
    "activity_desc_res": {"TR": "Türbin, Saha ve Ekipmanlara Dair Ek Detaylar", "EN": "Additional Details on Turbines, Site, and Equipment"},
    "activity_desc_ges": {"TR": "Panel, Arazi ve İnverterlere Dair Ek Detaylar", "EN": "Additional Details on Panels, Land, and Inverters"},
    "activity_desc_hes": {"TR": "Baraj, Tünel ve Santral Binasına Dair Ek Detaylar", "EN": "Additional Details on Dam, Tunnels, and Powerhouse"},
    "si_pd": {"TR": "Toplam Sigorta Bedeli (PD)", "EN": "Total Sum Insured (PD)"},
    "risk_zone": {"TR": "Deprem Risk Bölgesi", "EN": "Earthquake Risk Zone"},
    "gross_profit": {"TR": "Yıllık Brüt Kâr (GP)", "EN": "Annual Gross Profit (GP)"},
    "baraj_tipi": {"TR": "Baraj Tipi", "EN": "Dam Type"},
    "tesis_yili": {"TR": "Tesisin İnşa Yılı", "EN": "Facility Construction Year"},
    "santral_konumu": {"TR": "Santral Binasının Konumu", "EN": "Powerhouse Location"},
    "panel_montaj": {"TR": "Panel Montaj Tipi", "EN": "Panel Mounting Type"},
    "arazi_topo": {"TR": "Arazinin Topoğrafyası", "EN": "Land Topography"},
    "inverter_mimari": {"TR": "İnverter Mimarisi", "EN": "Inverter Architecture"},
    "turbin_yas": {"TR": "Türbin Teknolojisi ve Ortalama Yaşı", "EN": "Turbine Technology and Average Age"},
    "arazi_jeoteknik": {"TR": "Arazinin Jeo-Teknik Durumu", "EN": "Geo-Technical Condition of the Site"},
    "salt_sahasi": {"TR": "Şalt Sahasının Sismik Performansı", "EN": "Seismic Performance of the Substation"},
    "azami_tazminat": {"TR": "Azami Tazminat Süresi", "EN": "Max. Indemnity Period"},
    "bi_wait": {"TR": "BI Bekleme Süresi (Muafiyet)", "EN": "BI Waiting Period (Deductible)"},
    "yumusak_kat": {"TR": "Zemin Katta Geniş Vitrin/Cephe (Yumuşak Kat Riski)", "EN": "Large Ground Floor Facade/Windows (Soft Story Risk)"},
    "yumusak_kat_help": {"TR": "Binanızın zemin katı, üst katlara göre daha az perde duvara sahip ve büyük oranda cam cephe/vitrin/garaj kapısı gibi açıklıklardan mı oluşuyor?", "EN": "Does your building's ground floor have significantly fewer shear walls than the upper floors, consisting mostly of open spaces like glass facades, storefronts, or garage doors?"},
    "ai_pre_analysis_header": {"TR": "🧠 AI Teknik Risk Değerlendirmesi", "EN": "🧠 AI Technical Risk Assessment"},
    "results_header": {"TR": "📝 Sayısal Hasar Analizi", "EN": "📝 Numerical Damage Analysis"},
    "analysis_header": {"TR": "🔍 Poliçe Alternatifleri Analizi", "EN": "🔍 Policy Alternatives Analysis"},
    "btn_run": {"TR": "Analizi Çalıştır", "EN": "Run Analysis"},
}

# --- YARDIMCI FONKSİYONLAR ---
def tr(key: str) -> str:
    lang = st.session_state.get("lang", "TR")
    return T.get(key, {}).get(lang, key)

def money(x: float) -> str:
    try:
        return f"{x:,.0f} ₺".replace(",", ".")
    except Exception:
        return f"{x} ₺"

def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(x)))

# === Gemini yardımcıları: arama aracını güvenli şekilde dene/geri dön =========
def _mk_model(system_prompt: str, want_search: bool = True):
    """
    google-generativeai bazı sürümlerde arama araç isimlerini farklı bekler.
    Burada sırayla deneriz: 'google_search' → 'google_search_retrieval' → araçsız.
    Instantiation ya da generate_content sırasında hata çıkarsa araçsız moda geri döneriz.
    """
    if not _GEMINI_AVAILABLE:
        return None, None
    # Önce araçsız temel model (en güvenli)
    base_kwargs = dict(model_name="gemini-1.5-flash", system_instruction=system_prompt)
    # Ardından araçlı denemeler için tuple listesi:
    tool_variants = []
    if want_search:
        tool_variants = [
            [{"google_search": {}}],            # bazı sürümler
            [{"google_search_retrieval": {}}],  # bazı sürümler
        ]
    # Deneme dizisi: önce araçlı varyantlar, olmazsa araçsız
    tried = []
    if want_search:
        for tv in tool_variants:
            try:
                m = genai.GenerativeModel(**base_kwargs, tools=tv)  # type: ignore
                return m, tv
            except Exception as e:
                tried.append(str(e))
    # Araçsız
    try:
        m = genai.GenerativeModel(**base_kwargs)
        return m, None
    except Exception as e:
        # En kötü durumda None dön
        st.session_state.errors.append(f"Gemini model yüklenemedi: {e}\nDenemeler: {tried}")
        return None, None

def _normalize_calib_json(calib: Dict) -> Dict:
    # ENUM’lar
    def_enum = {"Düşük", "Orta", "Yüksek"}
    for k in ("icerik_hassasiyeti", "kritik_makine_bagimliligi", "ffe_riski"):
        v = calib.get(k, "Orta")
        calib[k] = v if v in def_enum else "Orta"
    # PD oranları
    r = calib.get("pd_base_loss_ratio_suggestion", {}) or {}
    for k in ("bina", "makine", "elektronik", "stok"):
        r[k] = round(_clamp(float(r.get(k, 0.12)), 0.01, 0.60), 2)
    calib["pd_base_loss_ratio_suggestion"] = r
    # PD çarpanları
    f = calib.get("pd_factor_suggestion", {}) or {}
    f["zemin_carpani"] = round(_clamp(float(f.get("zemin_carpani", 1.00)), 0.85, 1.50), 2)
    f["yoke_carpani"] = round(_clamp(float(f.get("yoke_carpani", 1.10)), 1.00, 1.60), 2)
    f["ffeq_potansiyel_carpani"] = round(_clamp(float(f.get("ffeq_potansiyel_carpani", 1.00)), 1.00, 2.00), 2)
    f["stok_devrilme_carpani"] = round(_clamp(float(f.get("stok_devrilme_carpani", 1.00)), 1.00, 2.50), 2)
    calib["pd_factor_suggestion"] = f
    # BI kalibrasyonu
    b = calib.get("bi_calibration", {}) or {}
    b["kritik_ekipman_durus_carpani"] = round(_clamp(float(b.get("kritik_ekipman_durus_carpani", 1.20)), 1.00, 3.00), 2)
    b["altyapi_gecikme_ay"] = int(_clamp(int(b.get("altyapi_gecikme_ay", 0)), 0, 3))
    b["tedarik_zinciri_gecikme_ay"] = int(_clamp(int(b.get("tedarik_zinciri_gecikme_ay", 1)), 0, 12))
    b["buffer_bitmis_urun_stogu_gun"] = int(_clamp(int(b.get("buffer_bitmis_urun_stogu_gun", 0)), 0, 120))
    calib["bi_calibration"] = b
    # Risk bayrakları
    flags = calib.get("risk_flags", [])
    if not isinstance(flags, list):
        flags = []
    calib["risk_flags"] = flags
    # Meta
    meta = calib.get("meta", {}) or {}
    meta["confidence_0to1"] = float(_clamp(float(meta.get("confidence_0to1", 0.6)), 0.0, 1.0))
    if "assumptions" not in meta or not isinstance(meta.get("assumptions"), list):
        meta["assumptions"] = []
    if "notes" not in meta or not isinstance(meta.get("notes"), str):
        meta["notes"] = "Heuristik dayanaklar kullanıldı."
    calib["meta"] = meta
    return calib


# --- GİRDİ VE HESAPLAMA MODELLERİ ---
@dataclass
class IndustrialInputs:
    faaliyet_tanimi: str = "Otomotiv ana sanayiye metal şasi parçaları üreten bir tesis. Tesiste 5 adet 1000 tonluk hidrolik pres, CNC makineleri ve robotik kaynak hatları bulunmaktadır. Yüksek raflarda rulo sac malzeme stoklanmaktadır."
    yapi_turu: str = "Çelik"; yonetmelik_donemi: str = "2018 sonrası (Yeni Yönetmelik)"; kat_sayisi: str = "1-3 kat"
    yumusak_kat_riski: str = "Hayır"; yakin_cevre: str = "Ana Karada / Düz Ova"; zemin_sinifi: str = "ZC (Varsayılan)"
    isp_varligi: str = "Var (Test Edilmiş)"; alternatif_tesis: str = "Var (kısmi kapasite)"; bitmis_urun_stogu: int = 15; bi_gun_muafiyeti: int = 21
    pd_bina_sum: int = 0; pd_makine_sum: int = 0; pd_elektronik_sum: int = 0; pd_stok_sum: int = 0

@dataclass
class RESInputs:
    ek_detaylar: str = "Manisa'da, temel iyileştirmesi yapılmış bir yamaçta kurulu 25 adet 8 yıllık Nordex N90 türbini. Şalt sahası standart tipte ve tesise 1km uzakta."
    turbin_yas: str = "5-10 yıl arası (Olgun Teknoloji)"; arazi_jeoteknik: str = "Yumuşak Zeminli / Toprak Tepe veya Ova"; salt_sahasi: str = "Standart Ekipman (Özel bir önlem yok)"; bi_gun_muafiyeti: int = 30

@dataclass
class GESInputs:
    ek_detaylar: str = "Konya Karapınar'da düz bir ova üzerine kurulu, tek eksenli tracker sistemli bir GES. Sahada 4 adet merkezi inverter bulunmaktadır."
    panel_montaj_tipi: str = "Tek Eksenli Takipçi Sistem (Tracker)"; arazi_topografyasi: str = "Düz Ova / Düşük Eğimli Arazi"; inverter_mimarisi: str = "Merkezi İnverter"; bi_gun_muafiyeti: int = 30

@dataclass
class HESInputs:
    ek_detaylar: str = "Artvin'de, 1985 yılında inşa edilmiş, gövdeye bitişik santral binası olan bir baraj."
    baraj_tipi: str = "Toprak / Kaya Dolgu"; tesis_yili: str = "1990 öncesi"; santral_konumu: str = "Baraj Gövdesine Bitişik / İçinde"; bi_gun_muafiyeti: int = 60

@dataclass
class ScenarioInputs:
    tesis_tipi: str = tr("endustriyel_tesis")
    si_pd: int = 500_000_000; yillik_brut_kar: int = 200_000_000; rg: int = 1; azami_tazminat_suresi: int = 365
    industrial_params: IndustrialInputs = field(default_factory=IndustrialInputs)
    res_params: RESInputs = field(default_factory=RESInputs)
    ges_params: GESInputs = field(default_factory=GESInputs)
    hes_params: HESInputs = field(default_factory=HESInputs)


# --- TEKNİK HESAPLAMA ÇEKİRDEĞİ ---
def calculate_pd_damage_industrial(s: ScenarioInputs) -> Dict:
    calib = st.session_state.get("ai_calibration_results")
    if not calib:
        raise ValueError("AI Kalibrasyon verisi bulunamadı. Lütfen analizi tekrar çalıştırın.")
    r = calib["pd_base_loss_ratio_suggestion"]; f = calib["pd_factor_suggestion"]
    si_total = int(s.si_pd or 0)
    if si_total <= 0:
        return {"damage_amount": 0, "pml_ratio": 0.0, "_details": {"ratios": {}, "pd_breakdown": {}}}

    p = s.industrial_params
    si_bina = int(p.pd_bina_sum or 0); si_makine = int(p.pd_makine_sum or 0)
    si_elektronik = int(p.pd_elektronik_sum or 0); si_stok = int(p.pd_stok_sum or 0)

    if (si_bina + si_makine + si_elektronik + si_stok) == 0:
        si = {k: int(si_total * v) for k, v in _DEF_SPLIT_INDUSTRIAL.items()}
    else:
        si = {"bina": si_bina, "makine": si_makine, "elektronik": si_elektronik, "stok": si_stok}

    bina_ratio = _clamp(r["bina"] * f["zemin_carpani"] * f["yoke_carpani"], 0.01, 0.60)
    makine_ratio = _clamp(r["makine"] * f["zemin_carpani"] * f["yoke_carpani"] * f["ffeq_potansiyel_carpani"], 0.01, 0.60)
    elektronik_ratio = _clamp(r["elektronik"] * f["zemin_carpani"] * f["yoke_carpani"] * f["ffeq_potansiyel_carpani"], 0.01, 0.60)
    stok_ratio = _clamp(r["stok"] * f["zemin_carpani"] * f["yoke_carpani"] * f["stok_devrilme_carpani"], 0.01, 0.60)

    pd_bina = si["bina"] * bina_ratio
    pd_makine = si["makine"] * makine_ratio
    pd_elektronik = si["elektronik"] * elektronik_ratio
    pd_stok = si["stok"] * stok_ratio

    total = pd_bina + pd_makine + pd_elektronik + pd_stok
    pml_ratio = _clamp(total / max(1, sum(si.values())), 0.00, 0.80)

    return {
        "damage_amount": int(total),
        "pml_ratio": float(round(pml_ratio, 3)),
        "_details": {
            "ratios": {
                "Bina": round(bina_ratio, 2), "Makine": round(makine_ratio, 2),
                "Elektronik": round(elektronik_ratio, 2), "Stok": round(stok_ratio, 2),
            },
            "pd_breakdown": {
                "Bina": int(pd_bina), "Makine": int(pd_makine),
                "Elektronik": int(pd_elektronik), "Stok": int(pd_stok),
            },
        },
    }

def calculate_bi_downtime_industrial(pd_ratio: float, s: ScenarioInputs) -> Tuple[int, int]:
    calib = st.session_state.get("ai_calibration_results")
    if not calib:
        raise ValueError("AI Kalibrasyon verisi bulunamadı. Lütfen analizi tekrar çalıştırın.")
    b = calib["bi_calibration"]; p = s.industrial_params
    base_repair = 30 + (float(pd_ratio) * 300.0)
    internal_downtime = int(base_repair * float(b["kritik_ekipman_durus_carpani"]))
    external_downtime = int((int(b["altyapi_gecikme_ay"]) + int(b["tedarik_zinciri_gecikme_ay"])) * 30)
    gross = max(internal_downtime, external_downtime)
    net_after_stock = max(0, gross - int(b.get("buffer_bitmis_urun_stogu_gun", p.bitmis_urun_stogu)))
    net_after_wait = max(0, net_after_stock - p.bi_gun_muafiyeti)
    final = min(s.azami_tazminat_suresi, net_after_wait)
    return max(0, gross), max(0, int(final))

def calculate_pd_damage_res(s: ScenarioInputs) -> Dict[str, float]:
    p = s.res_params
    FACTORS = {
        "turbin_yas": {"5 yıldan yeni (Modern Teknoloji)": 0.9, "5-10 yıl arası (Olgun Teknoloji)": 1.0, "10+ yıl (Eski Teknoloji)": 1.25},
        "arazi_jeoteknik": {"Kayalık ve Sağlam Zeminli Tepe": 0.85, "Yumuşak Zeminli / Toprak Tepe veya Ova": 1.35}
    }
    base_oran = _DEPREM_ORAN.get(s.rg, 0.13) * 0.5
    factor = FACTORS["turbin_yas"].get(p.turbin_yas, 1.0) * FACTORS["arazi_jeoteknik"].get(p.arazi_jeoteknik, 1.0)
    pml_ratio = min(0.40, max(0.01, base_oran * factor))
    return {"damage_amount": s.si_pd * pml_ratio, "pml_ratio": pml_ratio}

def calculate_bi_downtime_res(pd_ratio: float, s: ScenarioInputs) -> Tuple[int, int]:
    p = s.res_params
    base_repair_days = 45 + (pd_ratio * 400); operational_factor = 1.0
    if p.salt_sahasi == "Standart Ekipman (Özel bir önlem yok)": operational_factor *= 1.5
    if "10+" in p.turbin_yas: operational_factor *= 1.1
    gross = int(base_repair_days * operational_factor)
    if s.rg in [1, 2]: gross += 45
    net_raw = max(0, gross - p.bi_gun_muafiyeti); final = min(s.azami_tazminat_suresi, net_raw)
    return max(0, gross), max(0, int(final))

def calculate_pd_damage_ges(s: ScenarioInputs) -> Dict[str, float]:
    p = s.ges_params
    FACTORS = {
        "panel_montaj": {"Sabit Eğimli Konstrüksiyon": 1.0, "Tek Eksenli Takipçi Sistem (Tracker)": 1.2},
        "arazi_topo": {"Düz Ova / Düşük Eğimli Arazi": 1.0, "Orta / Yüksek Eğimli Arazi (Yamaç)": 1.3}
    }
    base_oran = _DEPREM_ORAN.get(s.rg, 0.13) * 0.4
    factor = FACTORS["panel_montaj"].get(p.panel_montaj_tipi, 1.0) * FACTORS["arazi_topo"].get(p.arazi_topografyasi, 1.0)
    pml_ratio = min(0.50, max(0.01, base_oran * factor))
    return {"damage_amount": s.si_pd * pml_ratio, "pml_ratio": pml_ratio}

def calculate_bi_downtime_ges(pd_ratio: float, s: ScenarioInputs) -> Tuple[int, int]:
    p = s.ges_params
    base_repair_days = 25 + (pd_ratio * 350); operational_factor = 1.0
    if p.inverter_mimarisi == "Merkezi İnverter": operational_factor *= 1.4
    gross = int(base_repair_days * operational_factor)
    if s.rg in [1, 2]: gross += 30
    net_raw = max(0, gross - p.bi_gun_muafiyeti); final = min(s.azami_tazminat_suresi, net_raw)
    return max(0, gross), max(0, int(final))

def calculate_pd_damage_hes(s: ScenarioInputs) -> Dict[str, float]:
    p = s.hes_params
    FACTORS = {
        "baraj_tipi": {"Beton Ağırlık / Kemer": 1.0, "Toprak / Kaya Dolgu": 1.4, "Nehir Tipi (Barajsız / Regülatör)": 0.5},
        "tesis_yili": {"1990 öncesi": 1.5, "1990-2010 arası": 1.1, "2010 sonrası": 0.9}
    }
    base_oran = _DEPREM_ORAN.get(s.rg, 0.13) * 0.8
    factor = FACTORS["baraj_tipi"].get(p.baraj_tipi, 1.0) * FACTORS["tesis_yili"].get(p.tesis_yili, 1.0)
    pml_ratio = min(0.80, max(0.02, base_oran * factor))
    return {"damage_amount": s.si_pd * pml_ratio, "pml_ratio": pml_ratio}

def calculate_bi_downtime_hes(pd_ratio: float, s: ScenarioInputs) -> Tuple[int, int]:
    p = s.hes_params
    base_repair_days = 90 + (pd_ratio * 500); operational_factor = 1.0
    if p.santral_konumu == "Baraj Gövdesine Bitişik / İçinde": operational_factor *= 1.3
    gross = int(base_repair_days * operational_factor)
    if s.rg in [1, 2]: gross += 60
    net_raw = max(0, gross - p.bi_gun_muafiyeti); final = min(s.azami_tazminat_suresi, net_raw)
    return max(0, gross), max(0, int(final))

def get_allowed_options(si_pd: int) -> Tuple[List[str], List[float]]:
    koas_opts = list(KOAS_FACTORS.keys())[:9]; muaf_opts = list(MUAFIYET_FACTORS.keys())[:5]
    if si_pd > 3_500_000_000:
        koas_opts.extend(list(KOAS_FACTORS.keys())[9:]); muaf_opts.extend(list(MUAFIYET_FACTORS.keys())[5:])
    return koas_opts, muaf_opts

def calculate_premium(si: float, tarife_yapi_turu: str, rg: int, koas: str, muaf: float, is_bi: bool = False) -> float:
    base_rate = TARIFE_RATES.get(tarife_yapi_turu, TARIFE_RATES["Diğer"])[rg - 1]
    prim_bedeli = min(si, 3_500_000_000) if not is_bi else si
    if is_bi:
        return (prim_bedeli * base_rate * 0.75) / 1000.0
    factor = KOAS_FACTORS.get(koas, 1.0) * MUAFIYET_FACTORS.get(muaf, 1.0)
    return (prim_bedeli * base_rate * factor) / 1000.0

def calculate_net_claim(si_pd: int, hasar_tutari: float, koas: str, muaf_pct: float) -> Dict[str, float]:
    muafiyet_tutari = si_pd * (muaf_pct / 100.0)
    muafiyet_sonrasi_hasar = max(0.0, hasar_tutari - muafiyet_tutari)
    sirket_pay_orani = float(koas.split('/')[0]) / 100.0
    net_tazminat = muafiyet_sonrasi_hasar * sirket_pay_orani
    sigortalida_kalan = hasar_tutari - net_tazminat
    return {"net_tazminat": net_tazminat, "sigortalida_kalan": sigortalida_kalan}


# --- AI FONKSİYONLARI (Araştırma aracı güvenli) ---
@st.cache_data(show_spinner=False)
def get_ai_calibration_industrial(s: ScenarioInputs) -> Dict:
    if not _GEMINI_AVAILABLE:
        return {}
    p = s.industrial_params
    payload = {
        "facility_type": "Endüstriyel",
        "rg": int(s.rg),
        "si_pd_total_TL": int(s.si_pd),
        "annual_gross_profit_TL": int(s.yillik_brut_kar),
        "max_indemnity_days": int(s.azami_tazminat_suresi),
        "bi_wait_days": int(p.bi_gun_muafiyeti),
        "yapi_turu": p.yapi_turu,
        "yonetmelik_donemi": p.yonetmelik_donemi,
        "kat_sayisi": p.kat_sayisi,
        "zemin_sinifi": p.zemin_sinifi,
        "yakin_cevre": p.yakin_cevre,
        "yumusak_kat_riski": p.yumusak_kat_riski,
        "ISP": p.isp_varligi,
        "alternatif_tesis": p.alternatif_tesis,
        "bitmis_urun_stogu_gun": int(p.bitmis_urun_stogu or 0),
        "faaliyet_tanimi": p.faaliyet_tanimi or "",
    }
    # Kullanıcıya şeffaf: arama aracı denendi mi?
    model, tools_used = _mk_model(AI_ANALYST_SYSTEM_PROMPT, want_search=True)
    if model is None:
        return {}

    prompt_user = (
        "KULLANICI GİRDİLERİ (JSON):\n"
        + json.dumps(payload, ensure_ascii=False)
        + "\n---\n"
        + "ARAŞTIRMA TALEBİ:\n"
        + "- Eğer arama aracı etkinse, öncelikli sorgular: AFAD/MTA PGA & mikrobölgeleme; TBDY-2018 spektral ivme; "
          "kritik ekipman lead-time (2024..2025); trafo lead-time; EERI/USGS endüstriyel etki örnekleri.\n"
        + "- Arama aracı yoksa heuristik üret ve meta.assumptions'a ekle."
    )

    generation_config = {"temperature": 0.1, "top_p": 0.8, "response_mime_type": "application/json"}

    # generate_content: araçlı model bazı sürümlerde çağrıda patlayabilir → araçsıza geri dön
    def _call_model(mdl):
        return mdl.generate_content(prompt_user, generation_config=generation_config)

    try:
        resp = _call_model(model)
    except Exception as e:
        # araçlı kullanım hatasıysa araçsız tekrar dene
        try:
            model_no_tools, _ = _mk_model(AI_ANALYST_SYSTEM_PROMPT, want_search=False)
            resp = _call_model(model_no_tools)
            st.session_state.errors.append(f"Arama aracı devre dışı bırakıldı (fallback): {e}")
        except Exception as e2:
            st.session_state.errors.append(f"AI Parametre Hatası (araçsız deneme başarısız): {e2}\n{traceback.format_exc()}")
            return {}

    if not resp or not getattr(resp, "text", None):
        st.session_state.errors.append("Gemini yanıtı boş döndü.")
        return {}

    try:
        raw = json.loads(resp.text)
    except Exception as e:
        st.session_state.errors.append(f"Gemini JSON ayrıştırılamadı: {e}\nYanıt: {resp.text[:400]}")
        return {}

    calib = _normalize_calib_json(raw)
    # Meta’ya arama aracı bilgisi ekleyelim (şeffaflık)
    try:
        meta = calib.get("meta", {}) or {}
        meta["search_tool"] = "enabled" if tools_used else "disabled"
        calib["meta"] = meta
    except Exception:
        pass
    return calib

@st.cache_data(show_spinner=False)
def generate_technical_assessment(s: ScenarioInputs, triggered_rules: List[str]) -> str:
    if not _GEMINI_AVAILABLE:
        return "AI servisi aktif değil."
    prompt = get_qualitative_assessment_prompt(s, triggered_rules)
    if not prompt:
        return "Seçilen tesis tipi için AI değerlendirmesi henüz aktif değil."
    try:
        # Raporlayıcı kısım için arama gerekli değil → araçsız model
        model, _ = _mk_model(system_prompt="", want_search=False)
        response = model.generate_content(prompt, generation_config={"temperature": 0.2})
        return response.text
    except Exception as e:
        st.session_state.errors.append(f"AI Rapor Hatası: {str(e)}\n{traceback.format_exc()}")
        return "AI Teknik Değerlendirme raporu oluşturulamadı."


# --- STREAMLIT UYGULAMASI ---
def main():
    st.set_page_config(page_title=T["title"]["TR"], layout="wide", page_icon="🏗️")
    if 'run_clicked' not in st.session_state: st.session_state.run_clicked = False
    if 'errors' not in st.session_state: st.session_state.errors = []

    st.title(tr('title'))

    if 's_inputs' not in st.session_state: st.session_state.s_inputs = ScenarioInputs()

    tesis_tipi_secenekleri = [tr("endustriyel_tesis"), tr("res"), tr("ges"), tr("hes")]
    try:
        current_index = tesis_tipi_secenekleri.index(st.session_state.s_inputs.tesis_tipi)
    except ValueError:
        current_index = 0

    def on_tesis_tipi_change():
        st.session_state.run_clicked = False
        st.session_state.s_inputs = ScenarioInputs(tesis_tipi=st.session_state.tesis_tipi_selector)

    selected_tesis_tipi = st.selectbox(tr("tesis_tipi_secimi"), tesis_tipi_secenekleri, index=current_index, on_change=on_tesis_tipi_change, key="tesis_tipi_selector")

    s_inputs = st.session_state.s_inputs
    s_inputs.tesis_tipi = selected_tesis_tipi

    st.header(tr("inputs_header"))

    if s_inputs.tesis_tipi == tr("endustriyel_tesis"):
        p_ind = s_inputs.industrial_params
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader(tr("base_header"))
            s_inputs.si_pd = st.number_input(tr("si_pd"), min_value=1_000_000, value=s_inputs.si_pd, step=10_000_000)
            p_ind.faaliyet_tanimi = st.text_area(tr("activity_desc_industrial"), p_ind.faaliyet_tanimi, height=200, placeholder="Örn: ...hidrolik presler, CNC makineleri...")
            with st.expander("Opsiyonel: Varlık Bazında Sigorta Bedeli"):
                 p_ind.pd_bina_sum = st.number_input("Bina SI (TL)", min_value=0, step=100_000, value=p_ind.pd_bina_sum)
                 p_ind.pd_makine_sum = st.number_input("Makine SI (TL)", min_value=0, step=100_000, value=p_ind.pd_makine_sum)
                 p_ind.pd_elektronik_sum = st.number_input("Elektronik SI (TL)", min_value=0, step=50_000, value=p_ind.pd_elektronik_sum)
                 p_ind.pd_stok_sum = st.number_input("Stok SI (TL)", min_value=0, step=50_000, value=p_ind.pd_stok_sum)

        with col2:
            st.subheader(tr("pd_header"))
            s_inputs.rg = st.select_slider(tr("risk_zone"), options=list(range(1, 8)), value=s_inputs.rg)
            p_ind.yapi_turu = st.selectbox("Yapı Türü", ["Betonarme", "Çelik", "Yığma", "Diğer"])
            p_ind.yonetmelik_donemi = st.selectbox("Yönetmelik Dönemi", ["1998 öncesi (Eski Yönetmelik)", "1998-2018 arası (Varsayılan)", "2018 sonrası (Yeni Yönetmelik)"])
            p_ind.kat_sayisi = st.selectbox("Kat Sayısı", ["1-3 kat", "4-7 kat", "8+ kat"])
            p_ind.zemin_sinifi = st.selectbox("Zemin Sınıfı", ["ZE", "ZD", "ZC (Varsayılan)", "ZA/ZB (Kaya/Sıkı Zemin)"])
            p_ind.yakin_cevre = st.selectbox("Tesisin Yakın Çevresi", ["Nehir Yatağı / Göl Kenarı / Kıyı Şeridi", "Ana Karada / Düz Ova", "Dolgu Zemin Üzerinde"])
            p_ind.yumusak_kat_riski = st.selectbox(tr("yumusak_kat"), ["Hayır", "Evet"], help=tr("yumusak_kat_help"))

        with col3:
            st.subheader(tr("bi_header"))
            s_inputs.yillik_brut_kar = st.number_input(tr("gross_profit"), min_value=0, value=s_inputs.yillik_brut_kar, step=10_000_000)
            p_ind.bi_gun_muafiyeti = st.selectbox(tr("bi_wait"), [14, 21, 30, 45, 60])
            s_inputs.azami_tazminat_suresi = st.selectbox(tr("azami_tazminat"), [365, 540, 730], format_func=lambda x: f"{int(x/30)} Ay")
            p_ind.isp_varligi = st.selectbox("İş Sürekliliği Planı", ["Yok (Varsayılan)", "Var (Test Edilmemiş)", "Var (Test Edilmiş)"])
            p_ind.alternatif_tesis = st.selectbox("Alternatif Tesis", ["Yok", "Var (kısmi kapasite)", "Var (tam kapasite)"])
            p_ind.bitmis_urun_stogu = st.number_input("Bitmiş Ürün Stoğu (gün)", value=p_ind.bitmis_urun_stogu, min_value=0, max_value=120)

    elif s_inputs.tesis_tipi == tr("res"):
        p_res = s_inputs.res_params
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader(tr("base_header"))
            s_inputs.si_pd = st.number_input(tr("si_pd"), min_value=1_000_000, value=s_inputs.si_pd, step=10_000_000)
            s_inputs.yillik_brut_kar = st.number_input(tr("gross_profit"), min_value=0, value=s_inputs.yillik_brut_kar, step=10_000_000)
            p_res.ek_detaylar = st.text_area(tr("activity_desc_res"), p_res.ek_detaylar, height=125)
        with col2:
            st.subheader(tr("res_header"))
            s_inputs.rg = st.select_slider(tr("risk_zone"), options=list(range(1, 8)), value=s_inputs.rg)
            p_res.turbin_yas = st.selectbox(tr("turbin_yas"), ["5 yıldan yeni (Modern Teknoloji)", "5-10 yıl arası (Olgun Teknoloji)", "10+ yıl (Eski Teknoloji)"])
            p_res.arazi_jeoteknik = st.selectbox(tr("arazi_jeoteknik"), ["Kayalık ve Sağlam Zeminli Tepe", "Yumuşak Zeminli / Toprak Tepe veya Ova"])
            p_res.salt_sahasi = st.selectbox(tr("salt_sahasi"), ["Standart Ekipman (Özel bir önlem yok)", "Sismik Izolatörlü veya Güçlendirilmiş Ekipman"])
        with col3:
            st.subheader(tr("bi_header"))
            s_inputs.azami_tazminat_suresi = st.selectbox(tr("azami_tazminat"), [365, 540, 730], format_func=lambda x: f"{int(x/30)} Ay")
            p_res.bi_gun_muafiyeti = st.selectbox(tr("bi_wait"), [30, 45, 60, 90])

    elif s_inputs.tesis_tipi == tr("ges"):
        p_ges = s_inputs.ges_params
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader(tr("base_header"))
            s_inputs.si_pd = st.number_input(tr("si_pd"), min_value=1_000_000, value=s_inputs.si_pd, step=10_000_000)
            s_inputs.yillik_brut_kar = st.number_input(tr("gross_profit"), min_value=0, value=s_inputs.yillik_brut_kar, step=10_000_000)
            p_ges.ek_detaylar = st.text_area(tr("activity_desc_ges"), p_ges.ek_detaylar, height=125)
        with col2:
            st.subheader(tr("ges_header"))
            s_inputs.rg = st.select_slider(tr("risk_zone"), options=list(range(1, 8)), value=s_inputs.rg)
            p_ges.panel_montaj_tipi = st.selectbox(tr("panel_montaj"), ["Sabit Eğimli Konstrüksiyon", "Tek Eksenli Takipçi Sistem (Tracker)"])
            p_ges.arazi_topografyasi = st.selectbox(tr("arazi_topo"), ["Düz Ova / Düşük Eğimli Arazi", "Orta / Yüksek Eğimli Arazi (Yamaç)"])
            p_ges.inverter_mimarisi = st.selectbox(tr("inverter_mimari"), ["Merkezi İnverter", "Dizi (String) İnverter"])
        with col3:
            st.subheader(tr("bi_header"))
            s_inputs.azami_tazminat_suresi = st.selectbox(tr("azami_tazminat"), [365, 540, 730], format_func=lambda x: f"{int(x/30)} Ay")
            p_ges.bi_gun_muafiyeti = st.selectbox(tr("bi_wait"), [30, 45, 60, 90])

    elif s_inputs.tesis_tipi == tr("hes"):
        p_hes = s_inputs.hes_params
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader(tr("base_header"))
            s_inputs.si_pd = st.number_input(tr("si_pd"), min_value=1_000_000, value=s_inputs.si_pd, step=10_000_000)
            s_inputs.yillik_brut_kar = st.number_input(tr("gross_profit"), min_value=0, value=s_inputs.yillik_brut_kar, step=10_000_000)
            p_hes.ek_detaylar = st.text_area(tr("activity_desc_hes"), p_hes.ek_detaylar, height=125)
        with col2:
            st.subheader(tr("hes_header"))
            s_inputs.rg = st.select_slider(tr("risk_zone"), options=list(range(1, 8)), value=s_inputs.rg)
            p_hes.baraj_tipi = st.selectbox(tr("baraj_tipi"), ["Beton Ağırlık / Kemer", "Toprak / Kaya Dolgu", "Nehir Tipi (Barajsız / Regülatör)"])
            p_hes.tesis_yili = st.selectbox(tr("tesis_yili"), ["1990 öncesi", "1990-2010 arası", "2010 sonrası"])
            p_hes.santral_konumu = st.selectbox(tr("santral_konumu"), ["Baraj Gövdesine Bitişik / İçinde", "Yeraltı (Kavern)", "Barajdan Ayrı / Uzak"])
        with col3:
            st.subheader(tr("bi_header"))
            s_inputs.azami_tazminat_suresi = st.selectbox(tr("azami_tazminat"), [365, 540, 730], format_func=lambda x: f"{int(x/30)} Ay")
            p_hes.bi_gun_muafiyeti = st.selectbox(tr("bi_wait"), [60, 90, 120, 180])

    st.markdown("---")
    if st.button(f"🚀 {tr('btn_run')}", use_container_width=True, type="primary"):
        st.session_state.run_clicked = True
        st.session_state.s_inputs = s_inputs
        st.session_state.errors = []
        st.session_state.ai_calibration_results = {}

    if st.session_state.run_clicked:
        s_inputs = st.session_state.s_inputs
        triggered_rules: List[str] = []

        try:
            if s_inputs.tesis_tipi == tr("endustriyel_tesis"):
                with st.spinner("AI Hibrit Zekâ Motoru endüstriyel tesisinizi kalibre ediyor..."):
                    ai_calib = get_ai_calibration_industrial(s_inputs)
                    st.session_state.ai_calibration_results = ai_calib
                    triggered_rules = ai_calib.get("risk_flags", []) if ai_calib else []
                pd_results = calculate_pd_damage_industrial(s_inputs)
                gross_bi_days, net_bi_days_final = calculate_bi_downtime_industrial(pd_results["pml_ratio"], s_inputs)
                tarife_yapi_turu = s_inputs.industrial_params.yapi_turu

            elif s_inputs.tesis_tipi == tr("res"):
                p_res = s_inputs.res_params
                if "10+" in p_res.turbin_yas: triggered_rules.append("ESKI_TEKNOLOJI")
                if "Yumuşak Zeminli" in p_res.arazi_jeoteknik: triggered_rules.append("YUMUSAK_ZEMIN")
                if "Standart Ekipman" in p_res.salt_sahasi: triggered_rules.append("STANDART_SALT_SAHASI")
                pd_results = calculate_pd_damage_res(s_inputs)
                gross_bi_days, net_bi_days_final = calculate_bi_downtime_res(pd_results["pml_ratio"], s_inputs)
                tarife_yapi_turu = "Diğer"

            elif s_inputs.tesis_tipi == tr("ges"):
                p_ges = s_inputs.ges_params
                if "Tracker" in p_ges.panel_montaj_tipi: triggered_rules.append("TRACKER_RISKI")
                if "Eğimli Arazi" in p_ges.arazi_topografyasi: triggered_rules.append("EGIM_RISKI")
                if "Merkezi İnverter" in p_ges.inverter_mimarisi: triggered_rules.append("MERKEZI_INVERTER_RISKI")
                pd_results = calculate_pd_damage_ges(s_inputs)
                gross_bi_days, net_bi_days_final = calculate_bi_downtime_ges(pd_results["pml_ratio"], s_inputs)
                tarife_yapi_turu = "Diğer"

            elif s_inputs.tesis_tipi == tr("hes"):
                p_hes = s_inputs.hes_params
                if "1990 öncesi" in p_hes.tesis_yili: triggered_rules.append("ESKI_TASARIM_KODU")
                if "Toprak / Kaya Dolgu" in p_hes.baraj_tipi: triggered_rules.append("DOLGU_BARAJ_RISKI")
                if "Bitişik" in p_hes.santral_konumu: triggered_rules.append("HIZALANMA_RISKI")
                pd_results = calculate_pd_damage_hes(s_inputs)
                gross_bi_days, net_bi_days_final = calculate_bi_downtime_hes(pd_results["pml_ratio"], s_inputs)
                tarife_yapi_turu = "Diğer"

            st.header(tr("ai_pre_analysis_header"))
            with st.spinner("AI Teknik Underwriter'ı senaryoyu değerlendiriyor..."):
                assessment_report = generate_technical_assessment(s_inputs, triggered_rules)
                st.markdown(assessment_report, unsafe_allow_html=True)

            pd_damage_amount = pd_results["damage_amount"]
            pd_ratio = pd_results["pml_ratio"]
            bi_damage_amount = (s_inputs.yillik_brut_kar / 365.0) * net_bi_days_final if s_inputs.yillik_brut_kar > 0 else 0

            st.header(tr("results_header"))
            m1, m2, m3 = st.columns(3)
            m1.metric("Beklenen PD Hasar Tutarı", money(pd_damage_amount), f"PML: {pd_ratio:.2%}")
            m2.metric("Brüt / Net İş Kesintisi", f"{gross_bi_days} / {net_bi_days_final} gün", "Onarım / Tazmin edilebilir")
            m3.metric("Beklenen BI Hasar Tutarı", money(bi_damage_amount))

            if s_inputs.tesis_tipi == tr("endustriyel_tesis") and "_details" in pd_results:
                st.subheader("Varlık Bazlı PD Hasar Kırılımı")
                details = pd_results["_details"]
                df_det = pd.DataFrame(list(details["pd_breakdown"].items()), columns=["Varlık Grubu", "PD Hasarı (₺)"])
                df_det["Hasar Oranı"] = [f"{v:.2%}" for v in details["ratios"].values()]
                st.dataframe(df_det.style.format({"PD Hasarı (₺)": money}), use_container_width=True)

            # ŞEFFAFLIK BÖLÜMÜ
            if s_inputs.tesis_tipi == tr("endustriyel_tesis") and st.session_state.ai_calibration_results:
                st.markdown("---")
                st.subheader("🧠 AI Kalibrasyon Gerekçeleri ve Parametreler")
                calib = st.session_state.ai_calibration_results
                meta = calib.get("meta", {})

                st.markdown("##### AI Tarafından Yapılan Ana Varsayımlar")
                assumptions = meta.get("assumptions", ["Varsayım bulunamadı."])
                for assumption in assumptions:
                    st.info(f"ℹ️ {assumption}")

                st.markdown("##### Analizde Kullanılan Dayanak ve Referanslar")
                notes = meta.get("notes", "Referans bulunamadı.")
                st.caption(f"📜 {notes}")
                if meta.get("search_tool") == "enabled":
                    st.caption("🔎 Web araştırması: **AKTİF**")
                else:
                    st.caption("🔎 Web araştırması: **PASİF (heuristik)**")

                st.markdown("##### Atanan Sayısal Kalibrasyon Parametreleri")
                params_data = []
                pd_factors = calib.get("pd_factor_suggestion", {})
                bi_calib = calib.get("bi_calibration", {})

                for key, value in pd_factors.items():
                    params_data.append({"Grup": "PD Çarpanları", "Parametre": key, "Değer": value})
                for key, value in bi_calib.items():
                    params_data.append({"Grup": "BI Kalibrasyonu", "Parametre": key, "Değer": value})

                if params_data:
                    df_params = pd.DataFrame(params_data)
                    st.table(df_params.style.format({"Değer": "{:.2f}"}))
                else:
                    st.warning("Sayısal parametreler AI tarafından üretilemedi.")

            st.markdown("---")
            st.header(tr("analysis_header"))

            koas_opts, muaf_opts = get_allowed_options(s_inputs.si_pd)
            results = []
            for koas in koas_opts:
                for muaf in muaf_opts:
                    prim_pd = calculate_premium(s_inputs.si_pd, tarife_yapi_turu, s_inputs.rg, koas, muaf)
                    prim_bi = calculate_premium(s_inputs.yillik_brut_kar, tarife_yapi_turu, s_inputs.rg, koas, muaf, is_bi=True)
                    toplam_prim = prim_pd + prim_bi

                    pd_claim = calculate_net_claim(s_inputs.si_pd, pd_damage_amount, koas, muaf)
                    total_payout = pd_claim["net_tazminat"] + bi_damage_amount
                    retained_risk = (pd_damage_amount + bi_damage_amount) - total_payout
                    verimlilik_skoru = (total_payout / toplam_prim if toplam_prim > 0 else 0) - (retained_risk / s_inputs.si_pd if s_inputs.si_pd > 0 else 0)

                    results.append({
                        "Poliçe Yapısı": f"{koas} / {muaf}%",
                        "Yıllık Toplam Prim": toplam_prim,
                        "Toplam Net Tazminat": total_payout,
                        "Sigortalıda Kalan Risk": retained_risk,
                        "Verimlilik Skoru": verimlilik_skoru
                    })

            df = pd.DataFrame(results).sort_values("Verimlilik Skoru", ascending=False).reset_index(drop=True)
            tab1, tab2 = st.tabs(["📈 Tablo Analizi", "📊 Görsel Analiz"])
            with tab1:
                st.dataframe(
                    df.style.format({
                        "Yıllık Toplam Prim": money,
                        "Toplam Net Tazminat": money,
                        "Sigortalıda Kalan Risk": money,
                        "Verimlilik Skoru": "{:.2f}"
                    }),
                    use_container_width=True
                )
            with tab2:
                fig = px.scatter(
                    df, x="Yıllık Toplam Prim", y="Sigortalıda Kalan Risk",
                    color="Verimlilik Skoru", color_continuous_scale=px.colors.sequential.Viridis,
                    hover_data=["Poliçe Yapısı", "Toplam Net Tazminat", "Verimlilik Skoru"],
                    title="Poliçe Alternatifleri Maliyet-Risk Analizi"
                )
                fig.update_layout(xaxis_title="Yıllık Toplam Prim", yaxis_title="Hasarda Şirketinizde Kalacak Risk", coloraxis_colorbar_title_text='Verimlilik')
                st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"Analiz sırasında bir hata oluştu: {e}")
            st.session_state.errors.append(f"Analiz Hatası: {str(e)}\n{traceback.format_exc()}")

    if st.session_state.errors:
        with st.sidebar.expander("⚠️ Geliştirici Hata Logları", expanded=False):
            for error in st.session_state.errors:
                st.code(error)

if __name__ == "__main__":
    main()
