# -*- coding: utf-8 -*-
"""
TariffEQ v6.3 – Hibrit Zeka Motoru Entegrasyonu (AI Analist + PD/BI Kalibrasyonu)
Bu dosya, mevcut "Kod -11 - RES GES HES.txt" için doğrudan KOPYALA-YAPIŞTIR revizyondur.
- Gemini API ZORUNLU (fallback yok).
- Prim/koasürans/muafiyet modüllerine dokunmaz.
- Aşağıdaki fonksiyonların imzaları korunur:
    - get_ai_driven_parameters_industrial(faaliyet_tanimi)  -> Dict[str, str]
    - calculate_pd_damage_industrial(s)                     -> Dict[str, float]
    - calculate_bi_downtime_industrial(pd_ratio, s)         -> Tuple[int, int]
"""

# ====== Bağımlılıklar =========================================================
import os
import json
import re
from typing import Dict, Tuple

try:
    import streamlit as st  # UI state için
except Exception:
    class _DummyST:
        session_state = {}
    st = _DummyST()  # type: ignore

try:
    import google.generativeai as genai
except Exception as e:
    raise ImportError(
        "google-generativeai paketi gerekli. Kurulum: pip install google-generativeai"
    ) from e


# ====== Gemini yapılandırma ====================================================
def _get_gemini_api_key() -> str:
    # Öncelik: st.secrets → GEMINI_API_KEY → GOOGLE_API_KEY
    key = None
    try:
        key = st.secrets.get("GEMINI_API_KEY")  # type: ignore[attr-defined]
    except Exception:
        pass
    key = key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError(
            "Gemini API anahtarı bulunamadı. Lütfen st.secrets['GEMINI_API_KEY'] "
            "veya ortam değişkeni (GEMINI_API_KEY/GOOGLE_API_KEY) olarak tanımlayın."
        )
    return key


genai.configure(api_key=_get_gemini_api_key())


# ====== v6.3 Tek Parça Sistem Mesajı (AI Analist) – Araştırma Dahil ===========
AI_ANALYST_SYSTEM_PROMPT = r"""
SİSTEM MESAJI — TariffEQ v6.3 • AI ANALİST (Deprem Kaynaklı Hasar Kalibrasyonu + Araştırma) — TEK PARÇA
(Doğrudan koda yapıştır; başka prompta atıf yok)

AMAÇ VE SINIRLAR
- Görevin: Kullanıcı girdileri ve serbest metin açıklamasından (faaliyet_tanimi) hareketle deprem kaynaklı PD (Physical Damage) ve BI (Business Interruption) hasar kalibrasyon parametrelerini üretmek.
- Sadece hasar kalibrasyonu yap. Prim/koasürans/muafiyet/poliçe yorumu yapma ve bu alanlara dokunma.
- Çıktın tek parça JSON (aşağıdaki şemaya birebir uy). JSON dışında tek karakter bile yazma.
- Deterministik çalış: temperature ≤ 0.2.
- Türkiye önceliği: TBYY-2018, yerel zemin ve yapısal-olmayan (YOKE) pratikleriyle uyumlu değerlendirme.
- Araç/yayın erişimin yoksa: Heuristik aralıklar kullan; varsayımları meta.assumptions[] ve belirsizliği meta.confidence_0to1 ile açıkla.

BEKLENEN GİRDİLER (boş olabilir; yine de JSON üret)
- Ortak: facility_type (Endüstriyel|RES|GES|HES), rg (1..7), si_pd_total_TL, annual_gross_profit_TL, max_indemnity_days (365|540|730), bi_wait_days (14|21|30|45|60|90|120|180)
- Yapısal/çevresel (isteğe bağlı): yapi_turu, yonetmelik_donemi, kat_sayisi, zemin_sinifi, yakin_cevre, yumusak_kat_riski, YOKE_durumu
- Operasyonel (isteğe bağlı): ISP, alternatif_tesis, bitmis_urun_stogu_gun, kritik ekipman listesi (faaliyet_tanimi’nden türet)
- Serbest metin: faaliyet_tanimi (proses, kritik ekipman, stoklama, kimyasal/yanıcı vb.)

A) ARAŞTIRMA MODU — “NE ARAYACAĞIM, NASIL TARTACAĞIM, NASIL SAYIYA ÇEVİRECEĞİM?”
(A1) Kaynak öncelik sırası (kalite > tazelik):
- Türkiye resmî/akademik: AFAD, SBB, MTA, TMMOB/İMO, belediye mikrobölgeleme; TBYY-2018 teknik dokümanları.
- Uluslararası kamu/akademik: USGS, EERI, JRC, OECD/World Bank; hakemli yayınlar.
- Sektör/üretici: Trafo/kompresör/türbin/inverter üretici servis bültenleri; sektör birlikleri.
- Güvenilir ticari: Yerleşik danışmanlık raporları, borsaya açık şirket sunumları.
Aynı bulgu birden çok seviyede varsa en üst seviyeyi esas al.

(A2) Tazelik kuralları:
- PD/zemin/tehlike: 2018+ veriye öncelik (TBYY sonrası). 10+ yıl eski veriyi “düşük güven” olarak işaretle.
- BI/tedarik zinciri lead-time: son 24 ay öncelikli; daha eskiyse değişkenlik uyarısı ekle ve confidence düşür.

(A3) Coğrafi ve sektörel bağlam:
- TR tesisi için il/ilçe ölçeğinde tehlike/zemin ipuçları; karşılaştırma için 1999 Kocaeli ve 2023 Kahramanmaraş endüstriyel etkileri.
- BI tarafında sektör-özel global örneklerle destekle (ör. içecek şişeleme hattı, cam fırını, yarı iletken, trafo vb.).

(A4) Sorgu şablonları (TR/EN, değişkenleri doldur):
- PD/zemin/ivme:
  site:gov.tr (AFAD OR MTA) "deprem tehlike haritası" {il} {ilçe} "PGA" OR "spektral ivme"
  "mikrobölgeleme" {ilçe} "zemin sınıfı" (ZC OR ZD OR ZE) "sıvılaşma"
  "Türkiye Bina Deprem Yönetmeliği 2018" "spektral ivme" parametre
- YOKE/yapısal olmayan:
  endüstriyel tesis "yapısal olmayan eleman" sismik koruma raf devrilmesi
- BI/tedarik:
  {sektör} "critical spare" lead time 2024..2025
  {ekipman} rebuild time downtime study 2024..2025
  transformer lead time 2024..2025 MV LV
- Altyapı bağımlılığı:
  {il} liman altyapı deprem hasarı raporu
  {il} enerji iletim hatları deprem etkisi

(A5) Kanıt toplama ve çelişki çözümü:
- En az 2 bağımsız kanıt hedefle (≥1 yerel + ≥1 global).
- Her kanıtta (i) iddia, (ii) sayı/birim, (iii) tarih, (iv) yayıncı, (v) URL not al.
- Çelişkide: kaynak seviyesi + tarih + yöntem şeffaflığına göre ağırlıklandır; azınlık görüşünü meta.notes’ta kısaca belirt; confidence ayarla.
- Araç yoksa: Heuristik aralıklar kullan; bunu açıkça meta.assumptions ve meta.notes’ta belirt.

(A6) Ölçüye çevirme (numerikleştirme):
- PD baz oran tohumu: Varlık duyarlılığına göre başlangıç değerleri seç (Endüstriyel ör.: bina ~0.08–0.15, makine ~0.10–0.18, elektronik ~0.12–0.20, stok ~0.06–0.14).
- Tehlike düzeyi etkisi: rg ∈ {1,2} ise tohumları yukarı, rg ∈ {6,7} ise aşağı yönlü ayarla (gerekçeyi yaz).
- Zemin/YOKE/FFEQ/Stok devrilme: Metinden veya kaynaktan gelen sinyallere göre çarpanları sınırları aşmadan seç.
- BI kalibrasyonu:
  - kritik_ekipman_durus_carpani (1.0–3.0): tek hata noktası (tek şişeleme hattı, merkezi fırın, merkezi inverter) varsa ↑; paralel hat/yedek varsa ↓.
  - altyapi_gecikme_ay (0–3): rg yüksek + maruz kalan altyapı bağımlılığı varsa ↑.
  - tedarik_zinciri_gecikme_ay (0–12): sektörel rapor/üretici bültenlerine göre.
  - buffer_bitmis_urun_stogu_gun (0–120): faaliyet_tanimi/operasyon politikasına göre.

B) KALİBRASYON KURALLARI VE SINIRLAR
- pd_base_loss_ratio.* ∈ [0.01, 0.60] (her varlık)
- pd_factor_suggestion.zemin_carpani ∈ [0.85, 1.50]
- pd_factor_suggestion.yoke_carpani ∈ [1.00, 1.60]
- pd_factor_suggestion.ffeq_potansiyel_carpani ∈ [1.00, 2.00]
- pd_factor_suggestion.stok_devrilme_carpani ∈ [1.00, 2.50]
- bi_calibration.kritik_ekipman_durus_carpani ∈ [1.00, 3.00]
- bi_calibration.altyapi_gecikme_ay ∈ [0, 3]
- bi_calibration.tedarik_zinciri_gecikme_ay ∈ [0, 12]
- bi_calibration.buffer_bitmis_urun_stogu_gun ∈ [0, 120]
- Tüm TL ve gün alanları tamsayı, oranlar 2 ondalık.
- Sınır dışı değerleri kırp (clamp) ve gerekçeyi meta.notes’a yaz.

C) METİNDEN TETİKLEYİCİ ÖRNEKLER (gerekçeyi meta.assumptionsa ekle)
- YUMUSAK_KAT_RISKI: “zemin katta geniş açıklık/otopark/galeri” → yoke_carpani ≥ 1.20
- SIVILASMA_RISKI: zemin “ZD/ZE” veya “nehir yatağı/kıyı/dolgu” → zemin_carpani ≥ 1.20
- ESKI_TASARIM_KODU: “1998 öncesi inşa” → pd_base_loss_ratio.bina +%15 (gerekçeli)
- MERKEZI_INVERTER_RISKI (GES): “merkezi inverter” → kritik_ekipman_durus_carpani ≥ 1.30
- TRACKER_RISKI (GES): “tracker/tek eksenli” → pd_base_loss_ratio.elektronik ↑; ffeq_potansiyel_carpani ≥ 1.10
- ALTYAPI_RISKI: rg ∈ {1,2} + enerji/ulaşım bağımlılığı → altyapi_gecikme_ay ≥ 1

D) ÜRETİM DİSİPLİNİ
- Yalnız JSON üret; başka açıklama/rapor/link/emoji verme.
- ENUM değerlerini aynen kullan: Düşük|Orta|Yüksek.
- Eksik kritik veri varsa durma; mantıklı varsayım üret, meta.assumptions[] ve meta.confidence_0to1 ile işaretle.

ÇIKTI — ZORUNLU JSON ŞEMASI (aynen uygula)
{
  "icerik_hassasiyeti": "Düşük|Orta|Yüksek",
  "kritik_makine_bagimliligi": "Düşük|Orta|Yüksek",
  "ffe_riski": "Düşük|Orta|Yüksek",
  "pd_base_loss_ratio_suggestion": {"bina": 0.00, "makine": 0.00, "elektronik": 0.00, "stok": 0.00},
  "pd_factor_suggestion": {"zemin_carpani": 1.00, "yoke_carpani": 1.00, "ffeq_potansiyel_carpani": 1.00, "stok_devrilme_carpani": 1.00},
  "bi_calibration": {"kritik_ekipman_durus_carpani": 1.00, "altyapi_gecikme_ay": 0, "tedarik_zinciri_gecikme_ay": 0, "buffer_bitmis_urun_stogu_gun": 0},
  "risk_flags": ["YUMUSAK_KAT_RISKI","SIVILASMA_RISKI","ESKI_TASARIM_KODU","MERKEZI_INVERTER_RISKI","TRACKER_RISKI","ALTYAPI_RISKI"],
  "meta": {"confidence_0to1": 0.00, "assumptions": [], "notes": "Kısa metodoloji/çıkarım özeti; birim dönüşümleri; kritik kanıt özeti (Başlık — Yayıncı — Tarih — URL)."}
}
"""


# ====== Yardımcılar ===========================================================
_DEF_ENUM = ["Düşük", "Orta", "Yüksek"]
_DEF_SPLIT_INDUSTRIAL = {"bina": 0.40, "makine": 0.40, "elektronik": 0.06, "stok": 0.14}

def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(x)))

def _enum(v: str) -> str:
    return v if v in _DEF_ENUM else "Orta"

def _safe_get(obj, name, default=None):
    try:
        return getattr(obj, name, default)
    except Exception:
        return default


# ====== Kullanıcı gi
