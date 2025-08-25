# -*- coding: utf-8 -*-
"""
TariffEQ – Ticari & Sınai Deprem: Prim + Hasar (PD+BI) Senaryo Modülü
========================================================================

Bu sürüm **Streamlit olmadan da** çalışır. Ortamda `streamlit` yüklüyse
arayüzü başlatır; değilse **CLI/Jupyter** çıktıları üretir ve **birim testleri**
ile doğrulama yapar. Böylece "ModuleNotFoundError: streamlit" hatası ortadan
kalkar ve fonksiyonellik korunur.

Öne Çıkanlar
------------
- Minimum deprem primi (PD+BI) – Tarife Tablosu-2 + 3,5 milyar TRY cap
- Bedel bandına göre **geçerli koasürans & muafiyet kombinasyonları**
- **MDR tabanlı PD hasar** ve **BI (iş durması) tazmin** hesabı
- Basit grafik üretimi (matplotlib mevcutsa PNG kaydı)
- CSV çıktısı
- **Birim testleri** (değiştirmeyin; gerekirse ek test ekleyin)

Kullanım
--------
```
# Ortamda streamlit yoksa:
python app.py            # CLI modunda örnek senaryo + testler

# Ortamda streamlit varsa (opsiyonel GUI):
streamlit run app.py
```

Notlar
------
- PDF/Excel üretimi, streamlit dışı ortamda harici paket riskine yol açtığı için
  bu minimal sürümde **CSV** ile sınırlandırılmıştır. İsterseniz açıkça ekleriz.
- Çelik yapı için tarife oranı, mevzuattaki Betonarme/Diğer ayrımı nedeniyle
  **prim hesabında Betonarme altında** ele alınır (yakın kabul). MDR ise yapı tipine
  özgü çarpanlarla hesaplanır.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

import sys
import numpy as np
import pandas as pd

# Matplotlib opsiyonel (grafik kaydı için)
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except Exception:
    MATPLOTLIB_AVAILABLE = False

# Streamlit opsiyonel (GUI için)
try:
    import streamlit as st  # type: ignore
    STREAMLIT_AVAILABLE = True
except Exception:
    STREAMLIT_AVAILABLE = False

# -------------------------------
# Görsel/format yardımcıları
# -------------------------------
fmt_money = lambda x: f"{x:,.0f}".replace(",", ".")

# -------------------------------
# Tarife Oranları (Tablo-2) – PD & BI
# -------------------------------
# Risk Grubu I→VII indeks (1 tabanlı giriş)
TARIFE_PD: Dict[str, List[float]] = {
    "Betonarme": [3.13, 2.63, 2.38, 1.94, 1.38, 1.06, 0.75],
    "Diğer":     [6.13, 5.56, 3.75, 2.00, 1.56, 1.24, 1.06],
}
# Basit yaklaşım: BI oranı = PD oranı (aynı RG & yapı grubu)
TARIFE_BI = TARIFE_PD

# Koasürans indirim/artırım faktörleri
KOAS_FACTOR: Dict[str, float] = {
    "80/20": 1.00, "75/25": 1 - 0.0625, "70/30": 1 - 0.1250, "65/35": 1 - 0.1875,
    "60/40": 1 - 0.2500, "55/45": 1 - 0.3125, "50/50": 1 - 0.3750, "45/55": 1 - 0.4375,
    "40/60": 1 - 0.5000,
    # 3.5–7 milyar bandı
    "90/10": 1 + 0.1250, "100/0": 1 + 0.2500,
}

# Muafiyet indirim/artırım faktörleri (PD)
MUAFF_FACTOR: Dict[float, float] = {
    0.1: 1 + 0.12,
    0.5: 1 + 0.09,
    1.0: 1 + 0.06,
    1.5: 1 + 0.03,
    2.0: 1.00,
    3.0: 1 - 0.06,
    4.0: 1 - 0.13,
    5.0: 1 - 0.19,
    10.0: 1 - 0.35,
}

# -------------------------------
# MDR (PD) – baz tablo ve çarpanlar
# -------------------------------
MDR_BASE: Dict[str, Dict[str, float]] = {
    ">=0.50":    {"RC": 0.065, "Steel": 0.050, "Masonry": 0.100},
    "0.40-0.50": {"RC": 0.050, "Steel": 0.040, "Masonry": 0.080},
    "0.30-0.40": {"RC": 0.035, "Steel": 0.028, "Masonry": 0.055},
    "0.20-0.30": {"RC": 0.020, "Steel": 0.016, "Masonry": 0.030},
    "0.15-0.20": {"RC": 0.010, "Steel": 0.008, "Masonry": 0.015},
    "<0.15":     {"RC": 0.005, "Steel": 0.004, "Masonry": 0.008},
}

FACTOR_ZEMIN = {"ZA":1.00, "ZB":1.10, "ZC":1.30, "ZD":1.60, "ZE":2.00}
FACTOR_YAS   = {"≤1998":1.30, "1999–2018":1.10, "2019+":0.85}
FACTOR_KAT   = {"1–3":0.90, "4–7":1.00, ">=8":1.10}
FACTOR_GUCL  = {"Yok":1.00, "Var":0.85}

MDR_CAP = 0.70  # güvenlik tavanı

# RG → temsilî PGA (g) — MDR için yaklaşık; premium için RG zorunlu
RG_TO_PGA = {1:0.45, 2:0.375, 3:0.325, 4:0.275, 5:0.225, 6:0.175, 7:0.125}

FAAL_FACTOR = {"Üretim":1.00, "Depolama":1.15, "Perakende":1.00, "Ofis":0.70}
LIFE_FACTOR = {"Düşük":0.95, "Orta":1.00, "Yüksek":1.15}
BI_WAIT_OPTIONS = [14, 30]

CAP_PD_BI = 3_500_000_000  # TRY

# -------------------------------
# Yardımcı fonksiyonlar (MDR & BI)
# -------------------------------

def pga_to_band(pga: float) -> str:
    if pga >= 0.50: return ">=0.50"
    if pga >= 0.40: return "0.40-0.50"
    if pga >= 0.30: return "0.30-0.40"
    if pga >= 0.20: return "0.20-0.30"
    if pga >= 0.15: return "0.15-0.20"
    return "<0.15"


def mdr_baseline(pga: float, yapi_turu: str) -> float:
    band = pga_to_band(pga)
    key = {"Betonarme":"RC", "Çelik":"Steel", "Yığma":"Masonry"}[yapi_turu]
    return MDR_BASE[band][key]


def mdr_final(pga: float, yapi_turu: str, zemin: str, yas_band: str, kat_band: str, gucl: str) -> float:
    m = mdr_baseline(pga, yapi_turu)
    m *= FACTOR_ZEMIN[zemin]
    m *= FACTOR_YAS[yas_band]
    m *= FACTOR_KAT[kat_band]
    m *= FACTOR_GUCL[gucl]
    return min(MDR_CAP, m)


def downtime_base_days(mdr: float) -> float:
    m = mdr * 100
    if m < 2: return 10
    if m < 5: return 30
    if m < 10: return 75
    if m < 20: return 135
    return 200


def downtime_effective_days(mdr: float, faaliyet: str, lifeline: str, stok_gun: int, alt_gun: int) -> float:
    d0 = downtime_base_days(mdr)
    db = d0 * FAAL_FACTOR[faaliyet] * LIFE_FACTOR[lifeline]
    de = max(0.0, db - stok_gun - alt_gun)
    return de

# -------------------------------
# Prim hesapları
# -------------------------------

def tarife_oran(yapi_turu: str, rg: int, enflasyon_yuzde: float, which: str = "PD") -> float:
    base = (TARIFE_PD if which == "PD" else TARIFE_BI)[yapi_turu][rg-1]
    # Enflasyon girişi varsa yarısı kadar arttır (mevcut yaklaşım)
    return base * (1.0 + (enflasyon_yuzde/100.0)/2.0)


def effective_rate_with_cap(rate: float, si: float, cap: float) -> Tuple[float, float]:
    if si <= 0: return 0.0, 0.0
    if si <= cap: return rate, si
    eff_rate = rate * (cap/si)
    return eff_rate, si


def premium_pd(si_pd: float, yapi_turu: str, rg: int, enfl: float, koas: str, muaf_pct: float) -> Tuple[float, float, float]:
    # Çelik → prim tarafında Betonarme kabulü (tarife sınırlaması)
    yapi_tarife = yapi_turu if yapi_turu != "Çelik" else "Betonarme"
    base_rate = tarife_oran(yapi_tarife, rg, enfl, which="PD")
    eff_rate, _ = effective_rate_with_cap(base_rate, si_pd, CAP_PD_BI)
    factor = KOAS_FACTOR[koas] * MUAFF_FACTOR[muaf_pct]
    prim = (min(si_pd, CAP_PD_BI) * base_rate / 1000.0) * factor if si_pd > CAP_PD_BI else (si_pd * base_rate / 1000.0) * factor
    return prim, base_rate, eff_rate


def premium_bi(si_bi: float, yapi_turu: str, rg: int, enfl: float) -> Tuple[float, float, float]:
    yapi_tarife = yapi_turu if yapi_turu != "Çelik" else "Betonarme"
    base_rate = tarife_oran(yapi_tarife, rg, enfl, which="BI")
    eff_rate, _ = effective_rate_with_cap(base_rate, si_bi, CAP_PD_BI)
    prim = (min(si_bi, CAP_PD_BI) * base_rate / 1000.0)
    return prim, base_rate, eff_rate

# -------------------------------
# Tazminat (PD & BI)
# -------------------------------

def insurer_share_from_koas(koas: str) -> float:
    left, _ = koas.split("/")
    return float(left) / 100.0


def pd_claim(si_pd: float, limit_pd: float, mdr: float, muaf_pct: float, insurer_share: float) -> Dict[str, float]:
    brut = si_pd * mdr
    muaf = si_pd * (muaf_pct/100.0)
    od_bas = max(0.0, brut - muaf)
    od_cos = od_bas * insurer_share
    od_lim = min(od_cos, limit_pd) if limit_pd > 0 else od_cos
    return {"PD_Brut": brut, "PD_Muaf": muaf, "PD_Odenecek": od_lim}


def bi_claim(daily_gp: float, wait_days: int, faaliyet: str, lifeline: str, stok_gun: int,
             alt_gun: int, mdr: float, insurer_share: float, limit_bi: float) -> Dict[str, float]:
    de = downtime_effective_days(mdr, faaliyet, lifeline, stok_gun, alt_gun)
    pay_days = max(0.0, min(365.0, de - wait_days))
    brut = daily_gp * pay_days
    od_cos = brut * insurer_share
    od_lim = min(od_cos, limit_bi) if limit_bi > 0 else od_cos
    return {
        "BI_EtkinGun": de,
        "BI_OdenecekGun": pay_days,
        "BI_Brut": brut,
        "BI_Odenecek": od_lim,
    }

# -------------------------------
# Geçerli kombinasyonlar
# -------------------------------
KOAS_LIST_BASE = ["80/20","75/25","70/30","65/35","60/40","55/45","50/50","45/55","40/60"]
KOAS_LIST_EXT  = ["90/10","100/0"]
MUAFF_LIST_BASE = [2.0,3.0,4.0,5.0,10.0]
MUAFF_LIST_EXT  = [0.1,0.5,1.0,1.5]


def allowed_sets(pd_total_try: float) -> Tuple[List[str], List[float]]:
    if pd_total_try <= 3_500_000_000:
        return KOAS_LIST_BASE, MUAFF_LIST_BASE
    elif pd_total_try <= 7_000_000_000:
        return KOAS_LIST_BASE + KOAS_LIST_EXT, MUAFF_LIST_BASE + MUAFF_LIST_EXT
    else:
        return KOAS_LIST_BASE + KOAS_LIST_EXT, MUAFF_LIST_BASE + MUAFF_LIST_EXT

# -------------------------------
# Senaryo çalıştırma (çekirdek)
# -------------------------------
@dataclass
class Scenario:
    # Tehlike & yapı
    hazard_mode: str = "RG"  # "RG" or "PGA"
    rg: int = 3
    pga_val: float = RG_TO_PGA[3]
    yapi_turu: str = "Betonarme"  # Betonarme/Çelik/Yığma
    zemin: str = "ZC"
    yas_band: str = "1999–2018"
    kat_band: str = "4–7"
    gucl: str = "Yok"

    # PD/BI SI & limit & ekonomi
    si_pd: int = 1_000_000_000
    limit_pd: int = 1_000_000_000
    daily_gp: int = 1_000_000
    limit_bi: int = 365_000_000
    enfl: float = 0.0

    # BI işletim
    faaliyet: str = "Üretim"
    lifeline: str = "Orta"
    stok_gun: int = 0
    alt_gun: int = 0
    bi_waits: Tuple[int, ...] = tuple(BI_WAIT_OPTIONS)

    # Referans (grafik düşündüğünüzde)
    ref_koas: str = "80/20"
    ref_muaf: float = 2.0
    ref_wait: int = 14


def compute_alternatives(s: Scenario) -> Tuple[pd.DataFrame, Dict[str, float]]:
    # Premium tarafı RG ister; MDR tarafı PGA ile de hesaplanabilir
    pga = s.pga_val if s.hazard_mode == "PGA" else RG_TO_PGA[s.rg]
    mdr = mdr_final(pga, s.yapi_turu, s.zemin, s.yas_band, s.kat_band, s.gucl)

    koas_opts, muaf_opts = allowed_sets(s.si_pd)
    rows = []
    for koas in koas_opts:
        insurer_share = insurer_share_from_koas(koas)
        for muaf in muaf_opts:
            prim_pd, pd_base_rate, pd_eff_rate = premium_pd(s.si_pd, s.yapi_turu, s.rg, s.enfl, koas, muaf)
            prim_bi, bi_base_rate, bi_eff_rate = premium_bi(s.daily_gp*365, s.yapi_turu, s.rg, s.enfl)
            for wait in (s.bi_waits or (s.ref_wait,)):
                pd_res = pd_claim(s.si_pd, s.limit_pd, mdr, muaf, insurer_share)
                bi_res = bi_claim(s.daily_gp, wait, s.faaliyet, s.lifeline, s.stok_gun, s.alt_gun, mdr, insurer_share, s.limit_bi)
                total_claim = pd_res["PD_Odenecek"] + bi_res["BI_Odenecek"]
                total_premium = prim_pd + prim_bi
                loss_ratio = (total_claim/total_premium) if total_premium>0 else np.nan
                rows.append({
                    "Koasürans": koas,
                    "PD Muafiyet %": muaf,
                    "BI Bekleme (gün)": wait,
                    "MDR %": round(mdr*100,2),
                    "PD Brüt Hasar": pd_res["PD_Brut"],
                    "PD Muafiyet Tutar": pd_res["PD_Muaf"],
                    "PD Net Ödeme": pd_res["PD_Odenecek"],
                    "BI Etkin Gün": bi_res["BI_EtkinGun"],
                    "BI Ödenecek Gün": bi_res["BI_Odenecek"],
                    "BI Brüt Hasar": bi_res["BI_Brut"],
                    "BI Net Ödeme": bi_res["BI_Odenecek"],
                    "Toplam Net Ödeme": total_claim,
                    "PD Prim": prim_pd,
                    "BI Prim": prim_bi,
                    "Toplam Prim": total_premium,
                    "Loss Ratio": loss_ratio,
                    "PD Oran (baz)": pd_base_rate,
                    "BI Oran (baz)": bi_base_rate,
                })

    df = pd.DataFrame(rows)

    # Referans kartlar
    ref_share = insurer_share_from_koas(s.ref_koas)
    ref_pd = pd_claim(s.si_pd, s.limit_pd, mdr, s.ref_muaf, ref_share)
    ref_bi = bi_claim(s.daily_gp, s.ref_wait, s.faaliyet, s.lifeline, s.stok_gun, s.alt_gun, mdr, ref_share, s.limit_bi)
    ref_pdprim, _, _ = premium_pd(s.si_pd, s.yapi_turu, s.rg, s.enfl, s.ref_koas, s.ref_muaf)
    ref_biprim, _, _ = premium_bi(s.daily_gp*365, s.yapi_turu, s.rg, s.enfl)

    cards = {
        "MDR %": ref_pd["PD_Brut"]/s.si_pd*100 if s.si_pd>0 else 0.0,
        "PD Net Ödeme (Ref)": ref_pd["PD_Odenecek"],
        "BI Ödenecek Gün (Ref)": ref_bi["BI_Odenecek"],
        "Toplam Prim (Ref)": ref_pdprim + ref_biprim,
    }
    return df, cards

# -------------------------------
# CSV ve Grafik Kayıt (opsiyonel)
# -------------------------------

def save_csv(df: pd.DataFrame, path: str = "tariffeq_deprem_alternatifler.csv") -> str:
    df.to_csv(path, index=False)
    return path


def plot_pd_limit_curve(si_pd: float, mdr: float, muaf: float, share: float, path: str = "pd_limit_curve.png") -> str:
    if not MATPLOTLIB_AVAILABLE:
        return ""
    lims = np.linspace(0.1, 1.2, 15) * si_pd
    y = []
    for L in lims:
        res = pd_claim(si_pd, L, mdr, muaf, share)
        y.append(res["PD_Odenecek"])
    fig, ax = plt.subplots(figsize=(8,4))
    ax.plot(lims, y, marker="o")
    ax.set_xlabel("PD Limit (TRY)")
    ax.set_ylabel("PD Net Ödeme (TRY)")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_bi_downtime_bars(mdr: float, faaliyet: str, lifeline: str, stok_gun: int, alt_gun: int,
                           ref_wait: int, path: str = "bi_downtime.png") -> str:
    if not MATPLOTLIB_AVAILABLE:
        return ""
    d0 = downtime_base_days(mdr)
    db = d0 * FAAL_FACTOR[faaliyet] * LIFE_FACTOR[lifeline]
    de = max(0.0, db - stok_gun - alt_gun)
    pay = max(0.0, min(365.0, de - ref_wait))
    names = ["Baz Duruş D₀","Çarpanlı Duruş D_b","Etkin Duruş D_e","Ödenecek Gün"]
    vals = [d0, db, de, pay]
    fig, ax = plt.subplots(figsize=(7,3.5))
    ax.bar(names, vals)
    ax.set_ylabel("Gün")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path

# -------------------------------
# Basit CLI
# -------------------------------

def main_cli() -> None:
    print("TariffEQ – CLI modu (Streamlit bulunamadı).\n")
    s = Scenario()
    df, cards = compute_alternatives(s)

    # Özet
    print("Özet (Referans):")
    print(f"  MDR %                : {cards['MDR %']:.2f}")
    print(f"  PD Net Ödeme (Ref)   : {fmt_money(cards['PD Net Ödeme (Ref)'])}")
    print(f"  BI Ödenecek Gün (Ref): {cards['BI Ödenecek Gün (Ref)']:.0f}")
    print(f"  Toplam Prim (Ref)    : {fmt_money(cards['Toplam Prim (Ref)'])}")

    # Tablo (ilk 12 satır)
    show_cols = [
        "Koasürans","PD Muafiyet %","BI Bekleme (gün)",
        "MDR %","PD Brüt Hasar","PD Muafiyet Tutar","PD Net Ödeme",
        "BI Etkin Gün","BI Ödenecek Gün","BI Brüt Hasar","BI Net Ödeme",
        "Toplam Net Ödeme","PD Prim","BI Prim","Toplam Prim","Loss Ratio"
    ]
    print("\nAlternatifler (ilk 12):")
    print(
        df[show_cols]
        .sort_values(["Toplam Prim","Toplam Net Ödeme"])[:12]
        .to_string(index=False, formatters={
            k:(lambda v: f"{v:,.0f}".replace(",","."))
            for k in ["PD Brüt Hasar","PD Muafiyet Tutar","PD Net Ödeme","BI Brüt Hasar","BI Net Ödeme","Toplam Net Ödeme","PD Prim","BI Prim","Toplam Prim"]
        })
    )

    # Kayıtlar
    path_csv = save_csv(df)
    print(f"\nCSV kaydedildi: {path_csv}")

    # Grafikler
    pga = s.pga_val if s.hazard_mode == "PGA" else RG_TO_PGA[s.rg]
    mdr = mdr_final(pga, s.yapi_turu, s.zemin, s.yas_band, s.kat_band, s.gucl)
    share = insurer_share_from_koas(s.ref_koas)
    if MATPLOTLIB_AVAILABLE:
        p1 = plot_pd_limit_curve(s.si_pd, mdr, s.ref_muaf, share)
        p2 = plot_bi_downtime_bars(mdr, s.faaliyet, s.lifeline, s.stok_gun, s.alt_gun, s.ref_wait)
        print(f"Grafikler: {p1 or 'yok'}, {p2 or 'yok'}")
    else:
        print("Matplotlib yok – grafik üretilmedi.")

# -------------------------------
# Birim Testleri (değiştirmeyin; yeni test ekleyin)
# -------------------------------

def run_tests() -> None:
    # 1) Cap etkisi
    eff, si_eff = effective_rate_with_cap(rate=2.38, si=5_000_000_000, cap=3_500_000_000)
    assert abs(eff - (2.38*(3_500_000_000/5_000_000_000))) < 1e-9

    # 2) PD prim basit
    prim, base, eff = premium_pd(100_000_000, "Betonarme", 3, 0.0, "80/20", 2.0)
    # 100m * 2.38 / 1000 = 238,000
    assert round(prim) == 238000, f"PD prim beklenen 238000, got {prim}"

    # 3) PD prim cap
    prim2, _, _ = premium_pd(5_000_000_000, "Betonarme", 3, 0.0, "80/20", 2.0)
    # 3.5bn * 2.38 / 1000 = 8,330,000
    assert round(prim2) == 8330000, f"cap sonrası beklenen 8,330,000, got {prim2}"

    # 4) PD claim muafiyet/limit
    pd_res = pd_claim(si_pd=100_000_000, limit_pd=2_000_000, mdr=0.05, muaf_pct=2.0, insurer_share=0.80)
    # brut=5m, muaf=2m -> baz=3m, koas=2.4m, limit=2m
    assert round(pd_res["PD_Odenecek"]) == 2_000_000

    # 5) BI claim bekleme etkisi
    bi_res = bi_claim(daily_gp=1_000_000, wait_days=14, faaliyet="Üretim", lifeline="Orta",
                      stok_gun=0, alt_gun=0, mdr=0.05, insurer_share=0.80, limit_bi=10_000_000_000)
    # mdr=5% -> base 75g (Üretim/Orta çarpan =1) -> ödenecek gün 61 -> 61m * 0.8
    assert round(bi_res["BI_Odenecek"]) == 48_800_000

    # 6) allowed sets
    k1, m1 = allowed_sets(3_000_000_000)
    assert "80/20" in k1 and 2.0 in m1
    k2, m2 = allowed_sets(4_000_000_000)
    assert "90/10" in k2 and 0.5 in m2

    # 7) MDR bileşik çarpan kontrol
    mdr_val = mdr_final(0.325, "Betonarme", "ZC", "1999–2018", "4–7", "Yok")
    expected = 0.035 * 1.30 * 1.10 * 1.00 * 1.00
    assert abs(mdr_val - expected) < 1e-9

    print("TÜM TESTLER BAŞARILI ✅")

# -------------------------------
# Streamlit UI (opsiyonel)
# -------------------------------

def run_streamlit_app() -> None:
    st.set_page_config(page_title="TariffEQ – Deprem Prim & Hasar", page_icon="📊", layout="wide")
    st.markdown("## Ticari & Sınai Deprem – Prim + Hasar Senaryosu")
    st.caption("Tarife kuralları + senaryo hasarı (PD & BI). Grafikler ve CSV hazır.")

    colA, colB, colC = st.columns([1.2,1.2,1.2])
    with colA:
        hazard_mode = st.selectbox("Tehlike girişi", ["Risk Grubu (I–VII)", "PGA (g)"])
        if hazard_mode == "Risk Grubu (I–VII)":
            rg = st.select_slider("Deprem Risk Grubu", options=[1,2,3,4,5,6,7], value=3)
            pga_val = st.number_input("Temsilî PGA (g)", value=RG_TO_PGA[rg], format="%.3f")
        else:
            pga_val = st.number_input("PGA (g)", min_value=0.05, max_value=1.0, value=0.325, step=0.005)
            rg = st.select_slider("Deprem Risk Grubu (premium için)", options=[1,2,3,4,5,6,7], value=3)
        yapi_turu = st.selectbox("Yapı Türü", ["Betonarme","Çelik","Yığma"])
        zemin = st.selectbox("Zemin Sınıfı", ["ZA","ZB","ZC","ZD","ZE"], index=2)
        yas_band = st.selectbox("Yapı Yaşı", ["≤1998","1999–2018","2019+"], index=1)
        kat_band = st.selectbox("Kat Adedi", ["1–3","4–7", ">=8"], index=1)
        gucl = st.selectbox("Güçlendirme", ["Yok","Var"], index=0)

    with colB:
        si_pd = st.number_input("PD Sigorta Bedeli", min_value=1_000_000, value=1_000_000_000, step=500_000)
        limit_pd = st.number_input("PD Limit", min_value=0, value=1_000_000_000, step=500_000)
        daily_gp = st.number_input("Günlük Brüt Kâr (BI)", min_value=0, value=1_000_000, step=50_000)
        limit_bi = st.number_input("BI Limit", min_value=0, value=int(daily_gp*365), step=500_000)
        enfl = st.slider("Enflasyon (%) – tarife artışı (½)", min_value=0, max_value=100, value=0)

    with colC:
        faaliyet = st.selectbox("Faaliyet Türü", list(FAAL_FACTOR.keys()))
        lifeline = st.selectbox("Altyapı/Lifeline Düzeyi", list(LIFE_FACTOR.keys()), index=1)
        stok_gun = st.number_input("Stok Tamponu (gün)", min_value=0, max_value=60, value=0, step=1)
        alt_sev = st.selectbox("Alternatif Tesis/Outsourcing", ["Yok","Kısmi","Tam"], index=0)
        alt_gun = 0 if alt_sev=="Yok" else (7 if alt_sev=="Kısmi" else 14)
        bi_waits = st.multiselect("BI Bekleme (gün)", BI_WAIT_OPTIONS, default=BI_WAIT_OPTIONS)

    s = Scenario(
        hazard_mode=("RG" if hazard_mode.startswith("Risk") else "PGA"), rg=rg, pga_val=pga_val,
        yapi_turu=yapi_turu, zemin=zemin, yas_band=yas_band, kat_band=kat_band, gucl=gucl,
        si_pd=si_pd, limit_pd=limit_pd, daily_gp=daily_gp, limit_bi=limit_bi, enfl=float(enfl),
        faaliyet=faaliyet, lifeline=lifeline, stok_gun=int(stok_gun), alt_gun=int(alt_gun), bi_waits=tuple(bi_waits),
    )

    df, cards = compute_alternatives(s)
    st.markdown("---")
    st.subheader("🔹 Alternatifler Matrisi (Prim + Hasar)")
    if not df.empty:
        show_cols = [
            "Koasürans","PD Muafiyet %","BI Bekleme (gün)",
            "MDR %","PD Brüt Hasar","PD Muafiyet Tutar","PD Net Ödeme",
            "BI Etkin Gün","BI Ödenecek Gün","BI Brüt Hasar","BI Net Ödeme",
            "Toplam Net Ödeme","PD Prim","BI Prim","Toplam Prim","Loss Ratio"
        ]
        st.dataframe(
            df[show_cols]
            .sort_values(["Toplam Prim","Toplam Net Ödeme"]).reset_index(drop=True)
        , use_container_width=True)
        st.download_button("📥 CSV İndir", data=df.to_csv(index=False).encode("utf-8"), file_name="tariffeq_deprem_alternatifler.csv", mime="text/csv")
    else:
        st.info("Girdi bulunamadı.")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("MDR (PD Hasar Oranı)", f"{cards['MDR %']:.2f}%")
    with c2:
        st.metric("PD Net Ödeme (Ref)", fmt_money(cards['PD Net Ödeme (Ref)']))
    with c3:
        st.metric("BI Ödenecek Gün (Ref)", f"{cards['BI Ödenecek Gün (Ref)']:.0f} gün")
    with c4:
        st.metric("Toplam Prim (Ref)", fmt_money(cards['Toplam Prim (Ref)']))

    st.caption("© TariffEQ – Teknik bilgilendirme; hesaplamalar bağlayıcı teklif değildir.")

# -------------------------------
# Giriş noktası
# -------------------------------
if __name__ == "__main__":
    # Testleri önce çalıştır (geliştirici güveni)
    try:
        run_tests()
    except AssertionError as e:
        print("TEST HATASI:", e)
        sys.exit(1)

    if STREAMLIT_AVAILABLE:
        run_streamlit_app()
    else:
        main_cli()
