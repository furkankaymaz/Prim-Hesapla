# -*- coding: utf-8 -*-
#
# TariffEQ – v5.5 Final – "Hibrit Zeka" Motoru Entegreli Nihai Sürüm
# =======================================================================
# Bu sürüm, sağlanan "PROMPT PAKETİ v5.4.1" şartnamesine göre geliştirilmiştir.
# AI motoru, iki aşamalı, şema-kilitli ve Pydantic ile doğrulanmış bir
# yapıya kavuşturulmuştur. Tüm analizler dinamik, şeffaf ve tutarlıdır.

import streamlit as st
import pandas as pd
import plotly.express as px
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import json
import time
import traceback
import hashlib
from pydantic import BaseModel, Field, ValidationError, field_validator

# --- AI İÇİN KORUMALI IMPORT VE GÜVENLİ KONFİGÜRASYON ---
_GEMINI_AVAILABLE = False
try:
    import google.generativeai as genai
    # Bu bölümün çalışması için Streamlit Cloud'da veya yerelde secrets.toml dosyasına
    # GEMINI_API_KEY = "..." şeklinde anahtarınızı eklemeniz gerekmektedir.
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        _GEMINI_AVAILABLE = True
    else:
        st.sidebar.warning("Gemini API anahtarı bulunamadı. AI özellikleri devre dışı.", icon="🔑")
except (ImportError, Exception):
    st.sidebar.error("Google AI kütüphanesi yüklenemedi. AI özellikleri devre dışı.", icon="🤖")
    _GEMINI_AVAILABLE = False


# --- TARİFE, ÇARPAN VERİLERİ VE SABİTLER (Orijinal yapı korundu) ---
TARIFE_RATES = {"Betonarme": [3.13, 2.63, 2.38, 1.94, 1.38, 1.06, 0.75], "Çelik": [3.13, 2.63, 2.38, 1.94, 1.38, 1.06, 0.75], "Yığma": [6.13, 5.56, 3.75, 2.00, 1.56, 1.24, 1.06], "Diğer": [6.13, 5.56, 3.75, 2.00, 1.56, 1.24, 1.06]}
KOAS_FACTORS = {"80/20": 1.0, "75/25": 0.9375, "70/30": 0.875, "65/35": 0.8125, "60/40": 0.75, "55/45": 0.6875, "50/50": 0.625, "45/55": 0.5625, "40/60": 0.5, "90/10": 1.125, "100/0": 1.25}
MUAFIYET_FACTORS = {2.0: 1.0, 3.0: 0.94, 4.0: 0.87, 5.0: 0.81, 10.0: 0.65, 1.5: 1.03, 1.0: 1.06, 0.5: 1.09, 0.1: 1.12}
RISK_ZONE_TO_INDEX = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6}


# --- PYDANTIC DOĞRULAMA MODELLERİ (Şemanıza göre oluşturuldu) ---
class Citation(BaseModel):
    title: str
    publisher: str
    date: str
    url: str

class Preflight(BaseModel):
    mandatory_inputs_ok: bool; research_done_ok: bool; pd_bi_linkage_ok: bool
    bounds_ok: bool; citations_ok: bool; schema_ok: bool

class AnalystOutput(BaseModel):
    meta: Dict
    preflight: Preflight
    inputs_digest: Dict
    pd_factors: Dict
    pd_base_loss_ratio: Dict
    pd_loss_TL: Dict
    bi_factors: Dict
    bi_downtime_days: Dict
    bi_loss_TL: int
    risk_flags: List[str]
    key_findings_for_report: List[str]
    citations: List[Citation]
    notes: str
    validation: Dict

    @field_validator("pd_loss_TL")
    def pml_consistency(cls, v, info):
        if 'inputs_digest' in info.data:
            total = v.get("total", 0)
            pml = v.get("pml_ratio_total", 0.0)
            si = info.data["inputs_digest"]["si_pd_total_TL"]
            if si > 0:
                calc = round(total / si, 4)
                if abs(calc - round(pml, 4)) > 0.001:
                    raise ValueError(f"PML tutarsızlığı: Hesaplanan {calc}, raporda belirtilen {pml}")
        return v

# --- GİRDİ DATACLASS'İ ---
@dataclass
class UserInputs:
    tesis_tipi: str; acik_adres: str; faaliyet_tanimi: str; deprem_bolgesi: int
    si_bina: int; si_makine: int; si_elektronik: int; si_stok: int
    yillik_brut_kar: int; azami_tazminat_suresi: int; bi_gun_muafiyeti: int
    yapi_turu: str; yonetmelik_donemi: str; zemin_sinifi: str
    yangin_patlama_potensiyeli: str; altyapi_yedekliligi: str; yoke_sismik_korumasi: str

# --- YARDIMCI FONKSİYONLAR ---
def money_format(x: float) -> str:
    if pd.isna(x) or x is None: return ""
    return f"{x:,.0f} ₺".replace(",", ".")

def perform_web_search(inputs: UserInputs) -> str:
    """
    Bu fonksiyon, normalde Google Search API gibi bir araca bağlanarak
    dinamik araştırmayı yapar. Şimdilik, girdilere göre değişen
    bir metin döndüren bir simülasyon olarak çalışmaktadır.
    """
    st.toast("Dinamik araştırma yapılıyor...", icon="🔍")
    time.sleep(1) # Gerçek arama süresini simüle et
    sektor_anahtar_kelime = "endüstriyel tesis"
    if "otomotiv" in inputs.faaliyet_tanimi.lower(): sektor_anahtar_kelime = "otomotiv sanayi"
    if "gıda" in inputs.faaliyet_tanimi.lower(): sektor_anahtar_kelime = "gıda sanayi"

    return f"Simülasyon: {inputs.acik_adres} lokasyonu için AFAD İRAP raporu incelendi. Zemin büyütme riski orta seviyede. {sektor_anahtar_kelime} faaliyetine ilişkin global BI vaka analizlerinde, kritik ekipman tedarik sürelerinin ortalama 6-9 ay olduğu, 2023 Maraş depreminde ise lojistik aksamaların ek 3 ay gecikmeye yol açtığı belirtiliyor."

# --- HİBRİT ZEKA MOTORU ---
def run_ai_hybrid_analysis(inputs: UserInputs) -> Tuple[Dict, str]:
    if not _GEMINI_AVAILABLE:
        return {}, "AI servisi aktif değil. Lütfen Gemini API anahtarınızı kontrol edin."

    # Adım 1: Dinamik Araştırma
    search_results_summary = perform_web_search(inputs)

    # Adım 2: AI Analisti'ni Çalıştır
    st.toast("AI Analisti, sayısal parametreleri üretiyor...", icon="🔬")
    total_si_pd = inputs.si_bina + inputs.si_makine + inputs.si_elektronik + inputs.si_stok
    
    # Prompt için kullanıcı girdilerini JSON formatına çevir
    # Not: Dataclass'ı doğrudan json.dumps ile basmak yerine,
    # daha temiz bir sözlük oluşturmak daha güvenilirdir.
    user_inputs_for_prompt = {
        "tesis_tipi": inputs.tesis_tipi, "acik_adres": inputs.acik_adres,
        "faaliyet_tanimi": inputs.faaliyet_tanimi, "deprem_bolgesi": inputs.deprem_bolgesi,
        "yapi_turu": inputs.yapi_turu, "yonetmelik_donemi": inputs.yonetmelik_donemi
    }
    inputs_digest_for_prompt = {
        "si_pd_total_TL": total_si_pd,
        "pd_breakdown_TL": {"bina": inputs.si_bina, "makine": inputs.si_makine, "elektronik": inputs.si_elektronik, "stok": inputs.si_stok},
        "annual_gross_profit_TL": inputs.yillik_brut_kar,
        "rg": inputs.deprem_bolgesi,
        "bi_wait_days": inputs.bi_gun_muafiyeti,
        "max_indemnity_days": inputs.azami_tazminat_suresi
    }

    analyst_prompt = f"""
    PROMPT PAKETİ — TariffEQ v5.4.1 “Hibrit Zekâ”
    GÖREV: AŞAMA-1 — AI ANALİST (Araştırma → Sayısallaştırma → JSON)
    Kullanıcı Girdileri ve Araştırma Bulgularını, sağlanan JSON şemasına ve kurallara harfiyen uyarak doldur.
    
    KULLANICI GİRDİLERİ ÖZETİ:
    {json.dumps(user_inputs_for_prompt, indent=2, ensure_ascii=False)}

    ARAŞTIRMA BULGULARI:
    {search_results_summary}

    LÜTFEN SADECE İSTENEN JSON ŞEMASINI DOLDURARAK YANIT VER:
    {json.dumps(AnalystOutput.model_json_schema(), indent=2)}
    """
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(analyst_prompt, generation_config={"temperature": 0.2, "response_mime_type": "application/json"})
        ai_json_output = json.loads(response.text)
        
        # Adım 3: Pydantic ile Doğrulama
        st.toast("AI Analist çıktısı alındı, doğrulanıyor...", icon="✔️")
        validated_data = AnalystOutput.model_validate(ai_json_output)
        
        # Adım 4: AI Raporlayıcı'yı Çalıştır
        st.toast("AI Raporlayıcı, yönetici özetini hazırlıyor...", icon="✍️")
        reporter_prompt = f"""
        GÖREV: AŞAMA-2 — AI RAPORLAYICI (JSON → Yönetici Özeti). Sana iletilen doğrulanmış JSON verisinden, şartnamedeki kurallara uyarak bir yönetici özeti oluştur. Emoji kullanma.
        JSON GİRDİSİ: {validated_data.model_dump_json()}
        """
        report_response = model.generate_content(reporter_prompt, generation_config={"temperature": 0.3})
        final_report_text = report_response.text

        return validated_data.model_dump(), final_report_text

    except ValidationError as e:
        st.error(f"AI Çıktı Doğrulama Hatası: AI tarafından üretilen JSON, beklenen şemaya uymuyor. Lütfen tekrar deneyin. Detaylar: {e}")
        return {}, "AI çıktısı doğrulanamadı."
    except Exception as e:
        st.error(f"AI Analiz Motoru Hatası: {e}")
        return {}, f"AI analizi sırasında beklenmedik bir hata oluştu: {traceback.format_exc()}"

# --- HASAR VE PRİM HESAPLAMA MOTORLARI ---
def calculate_damages_from_ai_output(s: UserInputs, ai_output: Dict) -> Dict:
    if not ai_output: return {}
    pd_loss = ai_output.get("pd_loss_TL", {})
    bi_downtime = ai_output.get("bi_downtime_days", {})
    
    net_bi_days = bi_downtime.get("net_after_wait", 0)
    bi_damage = (s.yillik_brut_kar / 365) * net_bi_days if s.yillik_brut_kar > 0 else 0
    
    return {
        "pd_hasar": pd_loss.get("total", 0),
        "bi_hasar": bi_damage,
        "pml_orani": pd_loss.get("pml_ratio_total", 0),
        "brut_bi_suresi_gun": bi_downtime.get("gross", 0)
    }

def get_allowed_options(si_pd: int) -> Tuple[List[str], List[float]]:
    koas_opts = list(KOAS_FACTORS.keys())[:9]
    muaf_opts = list(MUAFIYET_FACTORS.keys())[:5]
    if si_pd > 350_000_000:
        koas_opts.extend(list(KOAS_FACTORS.keys())[9:])
        muaf_opts.extend(list(MUAFIYET_FACTORS.keys())[5:])
    return koas_opts, muaf_opts

def calculate_premium(si: float, tarife_yapi_turu: str, rg: int, koas: str, muaf: float, is_bi: bool = False) -> float:
    rg_index = RISK_ZONE_TO_INDEX.get(rg, 0)
    base_rate = TARIFE_RATES.get(tarife_yapi_turu, TARIFE_RATES["Diğer"])[rg_index]
    prim_bedeli = si
    if is_bi: return (prim_bedeli * base_rate * 0.75) / 1000.0
    factor = KOAS_FACTORS.get(koas, 1.0) * MUAFIYET_FACTORS.get(muaf, 1.0)
    return (prim_bedeli * base_rate * factor) / 1000.0

def calculate_net_claim(si_pd: int, hasar_tutari: float, koas: str, muaf_pct: float) -> Dict[str, float]:
    muafiyet_tutari = si_pd * (muaf_pct / 100.0)
    muafiyet_sonrasi_hasar = max(0.0, hasar_tutari - muafiyet_tutari)
    sirket_pay_orani = float(koas.split('/')[0]) / 100.0
    net_tazminat = muafiyet_sonrasi_hasar * sirket_pay_orani
    sigortalida_kalan = hasar_tutari - net_tazminat
    return {"net_tazminat": net_tazminat, "sigortalida_kalan": sigortalida_kalan}

def calculate_policy_alternatives(s: UserInputs, damage_results: Dict) -> pd.DataFrame:
    toplam_si_pd = s.si_bina + s.si_makine + s.si_elektronik + s.si_stok
    if toplam_si_pd == 0: return pd.DataFrame()
    
    koas_opts, muaf_opts = get_allowed_options(toplam_si_pd)
    results_data = []
    
    for koas in koas_opts:
        for muaf in muaf_opts:
            prim_pd = calculate_premium(toplam_si_pd, s.yapi_turu, s.deprem_bolgesi, koas, muaf)
            prim_bi = calculate_premium(s.yillik_brut_kar, s.yapi_turu, s.deprem_bolgesi, koas, muaf, is_bi=True)
            toplam_prim = prim_pd + prim_bi
            pd_claim = calculate_net_claim(toplam_si_pd, damage_results.get('pd_hasar', 0), koas, muaf)
            total_payout = pd_claim["net_tazminat"] + damage_results.get('bi_hasar', 0)
            total_damage = damage_results.get('pd_hasar', 0) + damage_results.get('bi_hasar', 0)
            retained_risk = total_damage - total_payout
            verimlilik_skoru = (total_payout / toplam_prim if toplam_prim > 0 else 0) - (retained_risk / toplam_si_pd if toplam_si_pd > 0 else 0) * 5
            results_data.append({
                "Poliçe Yapısı": f"{koas} / {muaf}%", "Yıllık Toplam Prim": toplam_prim, 
                "Toplam Net Tazminat": total_payout, "Sigortalıda Kalan Risk": retained_risk, 
                "Verimlilik Skoru": verimlilik_skoru
            })
    return pd.DataFrame(results_data).sort_values("Verimlilik Skoru", ascending=False).reset_index(drop=True)

# --- STREAMLIT ANA UYGULAMA AKIŞI ---
def main():
    st.set_page_config(page_title="TariffEQ v5.5 Final", layout="wide", page_icon="🏗️")
    st.title("TariffEQ v5.5 – Hibrit Zeka Motoru")

    # Tesis tipi seçimi
    tesis_tipi_secenekleri = ["Endüstriyel Tesis", "Enerji Santrali - Rüzgar (RES)", "Enerji Santrali - Güneş (GES)", "Enerji Santrali - Hidroelektrik (HES)"]
    selected_tesis_tipi = st.selectbox("1. Lütfen Analiz Etmek İstediğiniz Tesis Tipini Seçiniz", tesis_tipi_secenekleri)

    with st.form(key="analysis_form"):
        st.header(f"2. {selected_tesis_tipi} Bilgilerini Giriniz")
        
        # Sadece Endüstriyel Tesis için detaylı form
        if selected_tesis_tipi == "Endüstriyel Tesis":
            c1, c2, c3 = st.columns(3)
            with c1:
                st.subheader("🏭 Temel ve Finansal Bilgiler")
                acik_adres = st.text_input("Açık Adres", "Gebze Organize Sanayi Bölgesi, Kocaeli")
                faaliyet_tanimi = st.text_area("Faaliyet Tanımı (En Kritik Bilgi)", "Otomotiv ana sanayiye metal şasi parçaları üreten, pres ve robotik kaynak hatları olan tesis.", height=150, placeholder="Üretim süreci, kritik ekipmanlar, stoklama yöntemi...")
                st.markdown("---")
                si_bina = st.number_input("Bina Sigorta Bedeli", 0, 10_000_000_000, 150_000_000, 1_000_000, format="%d")
                si_makine = st.number_input("Makine-Ekipman Bedeli", 0, 10_000_000_000, 250_000_000, 1_000_000, format="%d")
                si_elektronik = st.number_input("Elektronik Cihaz Bedeli", 0, 10_000_000_000, 50_000_000, 1_000_000, format="%d")
                si_stok = st.number_input("Stok (Emtia) Bedeli", 0, 10_000_000_000, 50_000_000, 1_000_000, format="%d")
                yillik_brut_kar = st.number_input("Yıllık Brüt Kâr (GP)", 0, 10_000_000_000, 200_000_000, 10_000_000, format="%d")
            with c2:
                st.subheader("🧱 Yapısal & PD Riskleri")
                deprem_bolgesi = st.select_slider("Deprem Risk Bölgesi", options=[1, 2, 3, 4, 5, 6, 7], value=1)
                yapi_turu = st.selectbox("Yapı Taşıyıcı Sistemi", ["Çelik", "Betonarme", "Prefabrik Betonarme"])
                yonetmelik_donemi = st.selectbox("İnşa Yönetmeliği", ["2018 sonrası (Yeni)", "1998-2018 arası", "1998 öncesi (Eski)"], index=1)
                zemin_sinifi = st.selectbox("Zemin Sınıfı (Biliyorsanız)", ["Bilmiyorum / AI Belirlesin", "ZA/ZB", "ZC", "ZD", "ZE"])
                yoke_sismik_korumasi = st.selectbox("YOKE Koruması", ["Koruma Yok", "Kısmi Koruma", "Tam Koruma"], index=1)
                yangin_patlama_potensiyeli = st.selectbox("Yangın Potansiyeli", ["Düşük", "Orta", "Yüksek", "Çok Yüksek"], index=1)
            with c3:
                st.subheader("📈 Operasyonel & BI Riskleri")
                azami_tazminat_suresi = st.selectbox("Azami Tazminat Süresi", [12, 18, 24], format_func=lambda x: f"{x} Ay") * 30
                bi_gun_muafiyeti = st.selectbox("BI Bekleme Süresi", [14, 21, 30, 45, 60], format_func=lambda x: f"{x} gün")
                altyapi_yedekliligi = st.selectbox("Kritik Altyapı Yedekliliği", ["Yedeksiz", "Kısmi Yedekli", "Tam Yedekli"], index=1)
        else:
            st.warning(f"{selected_tesis_tipi} için gelişmiş AI motoru bu versiyonda henüz aktif değildir. Lütfen Endüstriyel Tesis seçeneği ile devam ediniz.")
        
        form_submit_button = st.form_submit_button("🚀 Analizi Çalıştır", use_container_width=True, type="primary")

    if form_submit_button:
        st.session_state.analysis_run = False # Yeni analiz için eski sonuçları temizle
        if selected_tesis_tipi == "Endüstriyel Tesis":
            user_inputs = UserInputs(
                tesis_tipi=selected_tesis_tipi, acik_adres=acik_adres, faaliyet_tanimi=faaliyet_tanimi,
                deprem_bolgesi=deprem_bolgesi, si_bina=si_bina, si_makine=si_makine, si_elektronik=si_elektronik,
                si_stok=si_stok, yillik_brut_kar=yillik_brut_kar, azami_tazminat_suresi=azami_tazminat_suresi,
                bi_gun_muafiyeti=bi_gun_muafiyeti, yapi_turu=yapi_turu, yonetmelik_donemi=yonetmelik_donemi,
                zemin_sinifi=zemin_sinifi, yangin_patlama_potensiyeli=yangin_patlama_potensiyeli,
                altyapi_yedekliligi=altyapi_yedekliligi, yoke_sismik_korumasi=yoke_sismik_korumasi
            )
            
            with st.spinner("AI Hibrit Zeka Motoru çalıştırılıyor... Bu işlem 1-2 dakika sürebilir."):
                ai_output, final_report_text = run_ai_hybrid_analysis(user_inputs)
            
            if ai_output:
                damage_results = calculate_damages_from_ai_output(user_inputs, ai_output)
                policy_df = calculate_policy_alternatives(user_inputs, damage_results)
                
                st.session_state.damage_results = damage_results
                st.session_state.final_report_text = final_report_text
                st.session_state.policy_df = policy_df
                st.session_state.analysis_run = True
        else:
            st.error(f"{selected_tesis_tipi} modülü için analiz motoru bu versiyonda aktif değildir.")

    if st.session_state.get('analysis_run', False):
        st.markdown("---"); st.header("2. Analiz Sonuçları")
        st.markdown(st.session_state.final_report_text, unsafe_allow_html=True)
        st.markdown("---")
        
        dr = st.session_state.damage_results
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Beklenen PD Hasar", money_format(dr.get('pd_hasar')), f"PML Oranı: {dr.get('pml_orani', 0):.2%}")
        m2.metric("Brüt BI Süresi", f"{dr.get('brut_bi_suresi_gun', 0)} gün")
        m3.metric("Beklenen BI Hasar", money_format(dr.get('bi_hasar')))
        m4.metric("Toplam Risk", money_format(dr.get('pd_hasar', 0) + dr.get('bi_hasar', 0)))
        
        st.markdown("---"); st.header("3. Poliçe Optimizasyon Motoru")
        df = st.session_state.policy_df
        tab1, tab2 = st.tabs(["📈 Tablo Analizi", "📊 Görsel Analiz"])
        with tab1:
            st.dataframe(df.style.format(formatter={"Yıllık Toplam Prim": money_format, "Toplam Net Tazminat": money_format, "Sigortalıda Kalan Risk": money_format, "Verimlilik Skoru": "{:.2f}"}), use_container_width=True)
        with tab2:
            fig = px.scatter(df, x="Yıllık Toplam Prim", y="Sigortalıda Kalan Risk", color="Verimlilik Skoru", hover_data=["Poliçe Yapısı"])
            fig.update_traces(hovertemplate='<b>%{customdata[0]}</b><br>Prim: %{x:,.0f} ₺<br>Kalan Risk: %{y:,.0f} ₺')
            st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
