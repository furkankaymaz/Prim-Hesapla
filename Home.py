# app.py
# -*- coding: utf-8 -*-
"""
TariffEQ v6.3 – Hibrit Zekâ Motoru (Endüstriyel) • Tek Dosya Çalışan Uygulama
Koşullar:
- Python 3.9+ (3.12 uyumlu)
- pip install streamlit google-generativeai pandas

Çalıştırma:
  streamlit run app.py

API Anahtarı:
- st.secrets["GEMINI_API_KEY"] veya ortam değişkeni GEMINI_API_KEY/GOOGLE_API_KEY
- Gerekirse sol kenar çubuktan geçici olarak girebilirsiniz.
"""

from __future__ import annotations
import os, json
from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional

import streamlit as st
import pandas as pd

# --- Yardımcı sabitler --------------------------------------------------------
_DEF_ENUM = ["Düşük", "Orta", "Yüksek"]
_DEF_SPLIT_INDUSTRIAL = {"bina": 0.40, "makine": 0.40, "elektronik": 0.06, "stok": 0.14}

def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(x)))

def _enum(v: str) -> str:
    return v if v in _DEF_ENUM else "Orta"

def _get_gemini_api_key() -> Optional[str]:
    key = None
    try:
        key = st.secrets.get("GEMINI_API_KEY")  # type: ignore[attr-defined]
    except Exception:
        pass
    key = key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        ui_key = st.session_state.get("_ui_key")
        if ui_key:
            key = ui_key
    return key

# --- Prompt (AI Analist) ------------------------------------------------------
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

# --- Veri modelleri -----------------------------------------------------------
@dataclass
class IndustrialParams:
    faaliyet_tanimi: str = ""
    bi_gun_muafiyeti: int = 21
    zemin_sinifi: Optional[str] = None
    yapi_turu: Optional[str] = None
    yonetmelik_donemi: Optional[str] = None
    kat_sayisi: Optional[int] = None
    yakin_cevre: Optional[str] = None
    yumusak_kat_riski: Optional[str] = None
    YOKE_durumu: Optional[str] = None
    isp_varligi: Optional[str] = None
    alternatif_tesis: Optional[str] = None
    bitmis_urun_stogu: Optional[int] = 0
    # Granüler SI (opsiyonel)
    pd_bina_sum: Optional[int] = 0
    pd_makine_sum: Optional[int] = 0
    pd_elektronik_sum: Optional[int] = 0
    pd_stok_sum: Optional[int] = 0

@dataclass
class SessionInputs:
    facility_type: str = "Endüstriyel"
    rg: int = 4
    si_pd: int = 0
    yillik_brut_kar: int = 0
    azami_tazminat_suresi: int = 365
    industrial_params: IndustrialParams = field(default_factory=IndustrialParams)  # <-- düzeltme

# --- AI Çağrısı ---------------------------------------------------------------
def _build_user_payload_from_session(s: SessionInputs) -> Dict:
    p = s.industrial_params
    return {
        "facility_type": s.facility_type,
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
        "YOKE_durumu": p.YOKE_durumu,
        "ISP": p.isp_varligi,
        "alternatif_tesis": p.alternatif_tesis,
        "bitmis_urun_stogu_gun": int(p.bitmis_urun_stogu or 0),
        "faaliyet_tanimi": p.faaliyet_tanimi or "",
    }

def get_ai_calibration_full_industrial(s: SessionInputs) -> Dict:
    key = _get_gemini_api_key()
    if not key:
        raise RuntimeError("Gemini API anahtarı bulunamadı. Soldaki 'API Anahtarı' alanına girin veya ortam/secrets ayarlayın.")
    # Import'u burada yapıyoruz ki paket yoksa okunaklı uyarı gösterelim
    try:
        import google.generativeai as genai  # type: ignore
    except ModuleNotFoundError:
        raise RuntimeError("google-generativeai paketi kurulu değil. Kurulum: pip install google-generativeai")
    genai.configure(api_key=key)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=AI_ANALYST_SYSTEM_PROMPT,
    )
    generation_config = {"temperature": 0.1, "top_p": 0.8, "response_mime_type": "application/json"}
    payload = _build_user_payload_from_session(s)
    prompt_user = "KULLANICI GİRDİLERİ (JSON):\n" + json.dumps(payload, ensure_ascii=False)
    resp = model.generate_content(prompt_user, generation_config=generation_config)
    if not resp or not getattr(resp, "text", None):
        raise ValueError("Gemini yanıtı boş veya beklenmedik.")
    try:
        calib = json.loads(resp.text)
    except Exception as e:
        raise ValueError(f"Gemini JSON ayrıştırılamadı: {e}\nYanıt: {resp.text[:500]}")

    # Şema & band kısıtları
    r = calib.get("pd_base_loss_ratio_suggestion", {}) or {}
    f = calib.get("pd_factor_suggestion", {}) or {}
    b = calib.get("bi_calibration", {}) or {}
    calib["icerik_hassasiyeti"] = _enum(calib.get("icerik_hassasiyeti", "Orta"))
    calib["ffe_riski"] = _enum(calib.get("ffe_riski", "Orta"))
    calib["kritik_makine_bagimliligi"] = _enum(calib.get("kritik_makine_bagimliligi", "Orta"))
    def _rz(v, lo=0.01, hi=0.60): return round(_clamp(float(v), lo, hi), 2)
    for k in ("bina","makine","elektronik","stok"):
        r[k] = _rz(r.get(k, 0.12))
    f["zemin_carpani"] = round(_clamp(float(f.get("zemin_carpani", 1.00)), 0.85, 1.50), 2)
    f["yoke_carpani"] = round(_clamp(float(f.get("yoke_carpani", 1.00)), 1.00, 1.60), 2)
    f["ffeq_potansiyel_carpani"] = round(_clamp(float(f.get("ffeq_potansiyel_carpani", 1.00)), 1.00, 2.00), 2)
    f["stok_devrilme_carpani"] = round(_clamp(float(f.get("stok_devrilme_carpani", 1.00)), 1.00, 2.50), 2)
    b["kritik_ekipman_durus_carpani"] = round(_clamp(float(b.get("kritik_ekipman_durus_carpani", 1.20)), 1.00, 3.00), 2)
    b["altyapi_gecikme_ay"] = int(_clamp(int(b.get("altyapi_gecikme_ay", 0)), 0, 3))
    b["tedarik_zinciri_gecikme_ay"] = int(_clamp(int(b.get("tedarik_zinciri_gecikme_ay", 1)), 0, 12))
    b["buffer_bitmis_urun_stogu_gun"] = int(_clamp(int(b.get("buffer_bitmis_urun_stogu_gun", 0)), 0, 120))
    calib["pd_base_loss_ratio_suggestion"] = r
    calib["pd_factor_suggestion"] = f
    calib["bi_calibration"] = b

    st.session_state["_v63_calib_industrial"] = calib
    st.session_state["_v63_payload"] = payload
    return calib

# --- PD Hesaplama -------------------------------------------------------------
def calculate_pd_damage_industrial(s: SessionInputs) -> Dict[str, float]:
    calib = st.session_state.get("_v63_calib_industrial") or get_ai_calibration_full_industrial(s)
    r = calib["pd_base_loss_ratio_suggestion"]
    f = calib["pd_factor_suggestion"]
    si_total = int(s.si_pd or 0)
    if si_total <= 0:
        return {"damage_amount": 0, "pml_ratio": 0.0, "_details": {"ratios": {}, "pd_breakdown": {}}}
    p = s.industrial_params
    si_bina = int(p.pd_bina_sum or 0)
    si_makine = int(p.pd_makine_sum or 0)
    si_elektronik = int(p.pd_elektronik_sum or 0)
    si_stok = int(p.pd_stok_sum or 0)
    if (si_bina + si_makine + si_elektronik + si_stok) > 0:
        si = {"bina": si_bina, "makine": si_makine, "elektronik": si_elektronik, "stok": si_stok}
    else:
        splits = _DEF_SPLIT_INDUSTRIAL
        si = {k: int(si_total * v) for k, v in splits.items()}
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
                "bina": round(bina_ratio, 2),
                "makine": round(makine_ratio, 2),
                "elektronik": round(elektronik_ratio, 2),
                "stok": round(stok_ratio, 2),
            },
            "pd_breakdown": {
                "bina": int(pd_bina),
                "makine": int(pd_makine),
                "elektronik": int(pd_elektronik),
                "stok": int(pd_stok),
            },
        },
    }

# --- BI Hesaplama -------------------------------------------------------------
def calculate_bi_downtime_industrial(pd_ratio: float, s: SessionInputs) -> Tuple[int, int, int]:
    calib = st.session_state.get("_v63_calib_industrial") or get_ai_calibration_full_industrial(s)
    b = calib["bi_calibration"]
    base_repair = 30 + (float(pd_ratio) * 300.0)
    internal = int(base_repair * float(b["kritik_ekipman_durus_carpani"]))
    external = int((int(b["altyapi_gecikme_ay"]) + int(b["tedarik_zinciri_gecikme_ay"])) * 30)
    gross = max(internal, external)
    buffer_days = int(b.get("buffer_bitmis_urun_stogu_gun", 0) or 0)
    wait = int(s.industrial_params.bi_gun_muafiyeti or 21)
    max_days = int(s.azami_tazminat_suresi or 365)
    net_before_wait = max(0, gross - buffer_days)
    net_after_wait = min(max_days, max(0, net_before_wait - wait))
    return int(gross), int(net_after_wait), int(buffer_days)

# --- UI -----------------------------------------------------------------------
st.set_page_config(page_title="TariffEQ v6.3 – Hibrit Zeka Motoru (Endüstriyel)", layout="wide")

with st.sidebar:
    st.markdown("### Ayarlar")
    st.text_input("API Anahtarı (opsiyonel – eğer ortam/secrets yoksa)", type="password", key="_ui_key")
    st.markdown("---")
    st.caption("Girdi alanlarını doldurun ve **Analizi Çalıştır** butonuna basın.")

st.title("TariffEQ v6.3 – Endüstriyel Tesis Deprem PD/BI Kalibrasyonu (Gemini)")

colA, colB, colC = st.columns([1,1,1])
with colA:
    rg = st.selectbox("Deprem Risk Bölgesi (rg)", [1,2,3,4,5,6,7], index=3)
    si_pd = st.number_input("Toplam PD Sigorta Bedeli (TL)", min_value=0, step=100_000, value=5_000_000)
    yillik_brut_kar = st.number_input("Yıllık Brüt Kâr (TL)", min_value=0, step=100_000, value=12_000_000)
with colB:
    azami_tazminat_suresi = st.selectbox("Azami Tazminat Süresi (gün)", [365, 540, 730], index=0)
    bi_wait = st.selectbox("BI Gün Muafiyeti (gün)", [14,21,30,45,60,90,120,180], index=1)
    zemin_sinifi = st.selectbox("Zemin Sınıfı", ["Bilmiyorum", "ZA","ZB","ZC","ZD","ZE"], index=3)
with colC:
    pd_bina_sum = st.number_input("Bina SI (opsiyonel, TL)", min_value=0, step=100_000, value=0)
    pd_makine_sum = st.number_input("Makine SI (opsiyonel, TL)", min_value=0, step=100_000, value=0)
    pd_elektronik_sum = st.number_input("Elektronik SI (opsiyonel, TL)", min_value=0, step=50_000, value=0)
    pd_stok_sum = st.number_input("Stok SI (opsiyonel, TL)", min_value=0, step=50_000, value=0)

faaliyet_tanimi = st.text_area(
    "Faaliyet Tanımı (proses, kritik ekipman, stoklama, kimyasal/yanıcı vb.)",
    placeholder="Üretim sürecinizi, kritik ekipman(lar)ı, stoklama yöntemini (yüksek raf vb.) ve özel koşulları (soğuk zincir, ithal hammadde vb.) yazınız.",
    height=140,
)

colR1, colR2, colR3 = st.columns(3)
with colR1:
    yumusak_kat_riski = st.selectbox("Yumuşak Kat Riski", ["Bilinmiyor", "Evet", "Hayır"], index=0)
with colR2:
    YOKE_durumu = st.selectbox("Yapısal Olmayan Elemanların Koruması (YOKE)", ["Bilinmiyor","Koruma Yok","Kısmi","Tam"], index=0)
with colR3:
    bitmis_urun_stogu = st.number_input("Bitmiş Ürün Stoku (gün)", min_value=0, max_value=120, value=0)

analyze = st.button("Analizi Çalıştır", type="primary")

def _build_session_from_ui() -> SessionInputs:
    ip = IndustrialParams(
        faaliyet_tanimi=faaliyet_tanimi,
        bi_gun_muafiyeti=int(bi_wait),
        zemin_sinifi=None if zemin_sinifi=="Bilmiyorum" else zemin_sinifi,
        yumusak_kat_riski="Evet" if yumusak_kat_riski=="Evet" else ("Hayır" if yumusak_kat_riski=="Hayır" else None),
        YOKE_durumu=None if YOKE_durumu=="Bilinmiyor" else YOKE_durumu,
        bitmis_urun_stogu=int(bitmis_urun_stogu),
        pd_bina_sum=int(pd_bina_sum),
        pd_makine_sum=int(pd_makine_sum),
        pd_elektronik_sum=int(pd_elektronik_sum),
        pd_stok_sum=int(pd_stok_sum),
    )
    s = SessionInputs(
        facility_type="Endüstriyel",
        rg=int(rg),
        si_pd=int(si_pd),
        yillik_brut_kar=int(yillik_brut_kar),
        azami_tazminat_suresi=int(azami_tazminat_suresi),
        industrial_params=ip,
    )
    st.session_state["s_inputs"] = s
    return s

def _coinsurance_table(pd_tl: int, bi_net_days: int, daily_gp: float) -> pd.DataFrame:
    coins = [1.00, 0.90, 0.80, 0.70]
    pd_deduct_pcts = [0.00, 0.01, 0.02, 0.05]
    rows = []
    gross_bi_tl = daily_gp * bi_net_days
    gross_loss = pd_tl + gross_bi_tl
    for c in coins:
        for d in pd_deduct_pcts:
            pd_ded_tl = pd_tl * d
            net_pay = max(gross_loss - pd_ded_tl, 0) * c
            insured_retention = gross_loss - net_pay
            eff_score = net_pay / max(1, insured_retention) if insured_retention>0 else float("inf")
            rows.append({
                "Koasürans (Sigortacı Payı)": c,
                "PD Muafiyet (%)": d,
                "PD Muafiyet (TL)": int(pd_ded_tl),
                "Brüt Kayıp (TL)": int(gross_loss),
                "Net Ödenecek Tazminat (TL)": int(net_pay),
                "Sigortalı Katlanacağı Risk (TL)": int(insured_retention),
                "Verimlilik Skoru": round(eff_score, 3) if eff_score!=float("inf") else 999.0,
            })
    df = pd.DataFrame(rows).sort_values(["Verimlilik Skoru","Net Ödenecek Tazminat (TL)"], ascending=[False, False])
    return df

if analyze:
    try:
        s = _build_session_from_ui()
        calib = get_ai_calibration_full_industrial(s)
        with st.expander("AI Kalibrasyon JSON (v6.3)"):
            st.json(calib)

        pd_res = calculate_pd_damage_industrial(s)
        pd_tl = pd_res["damage_amount"]
        pml_ratio = pd_res["pml_ratio"]
        gross_days, bi_net_days, buffer_days = calculate_bi_downtime_industrial(pml_ratio, s)
        daily_gp = (s.yillik_brut_kar or 0) / 365.0
        bi_loss_tl = int(daily_gp * bi_net_days)

        st.subheader("Özet Sonuçlar")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("PD Tahmini (TL)", f"{pd_tl:,.0f}".replace(",", "."))
        m2.metric("PML Oranı", f"{pml_ratio:.2%}")
        m3.metric("BI Brüt/Net (gün)", f"{gross_days} / {bi_net_days}")
        m4.metric("BI Net Kayıp (TL)", f"{bi_loss_tl:,.0f}".replace(",", "."))

        st.markdown("#### Varlık Bazlı PD Kırılımı")
        det = pd_res["_details"]["pd_breakdown"]
        df_det = pd.DataFrame([
            ["Bina", det["bina"], pd_res["_details"]["ratios"]["bina"]],
            ["Makine", det["makine"], pd_res["_details"]["ratios"]["makine"]],
            ["Elektronik", det["elektronik"], pd_res["_details"]["ratios"]["elektronik"]],
            ["Stok", det["stok"], pd_res["_details"]["ratios"]["stok"]],
        ], columns=["Varlık", "PD (TL)", "Oran"])
        st.dataframe(df_det, use_container_width=True)

        st.markdown("#### Koasürans & Muafiyet Senaryoları – Net Ödenecek Tazminat")
        df_opts = _coinsurance_table(pd_tl, bi_net_days, daily_gp)
        st.dataframe(df_opts, use_container_width=True)

        st.markdown("#### Muafiyet (TL) – Net Ödenecek Tazminat (TL) Dağılımı")
        st.scatter_chart(df_opts, x="PD Muafiyet (TL)", y="Net Ödenecek Tazminat (TL)")

        st.markdown("#### Yorum (Otomatik)")
        st.write(
            f"- İçerik hassasiyeti: **{calib.get('icerik_hassasiyeti','Orta')}** | "
            f"FFE riski: **{calib.get('ffe_riski','Orta')}** | "
            f"Kritik makine bağımlılığı: **{calib.get('kritik_makine_bagimliligi','Orta')}**"
        )
        st.write(
            f"- BI kalibrasyonu: kritik ekipman çarpanı **{calib['bi_calibration']['kritik_ekipman_durus_carpani']}**, "
            f"altyapı gecikme **{calib['bi_calibration']['altyapi_gecikme_ay']} ay**, "
            f"tedarik gecikme **{calib['bi_calibration']['tedarik_zinciri_gecikme_ay']} ay**, "
            f"stok tamponu **{calib['bi_calibration']['buffer_bitmis_urun_stogu_gun']} gün**."
        )
        st.caption("Not: Prim hesaplama bu uygulamaya dahil değildir; mevcut tarifeye entegre edilebilir.")

    except Exception as e:
        st.error(f"Hata: {e}")

else:
    st.info("Parametreleri girin ve **Analizi Çalıştır** butonuna basın.")
