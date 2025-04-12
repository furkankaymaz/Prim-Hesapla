import streamlit as st

# Tarife oran tablosu (Deprem Bölgesi x Bina Tipi)
tarife_oranlari = {
    "Betonarme": [2.50, 2.22, 1.89, 1.77, 1.33, 0.94, 0.64],
    "Diğer": [4.40, 3.77, 3.30, 3.09, 2.48, 1.65, 0.97]
}

koasurans_indirimi = {
    "80/20": 0.00, "75/25": 0.0625, "70/30": 0.1250, "65/35": 0.1875,
    "60/40": 0.2500, "55/45": 0.3125, "50/50": 0.3750, "45/55": 0.4375, "40/60": 0.50,
    "30/70": 0.1250, "25/75": 0.0625
}

muafiyet_indirimi = {
    2: 0.00, 3: 0.06, 4: 0.13, 5: 0.19, 10: 0.35
}

car_tarife_oranlari = {
    "A": [1.56, 1.31, 1.19, 0.98, 0.69, 0.54, 0.38],
    "B": [3.06, 2.79, 1.88, 1.00, 0.79, 0.63, 0.54]
}

sure_carpani_tablosu = {i: 0.80 + 0.01 * (i - 6) for i in range(6, 37)}

def get_sure_carpani(sure):
    if sure <= 6:
        return 0.80
    elif sure >= 36:
        return sure_carpani_tablosu[36] + (sure - 36) * 0.03
    else:
        return sure_carpani_tablosu.get(sure, 1.00)

def hesapla_car(bedel):
    tl_bedel = bedel * kur_karsilik
    sure_carpani = get_sure_carpani(sigorta_suresi)
    oran = (car_tarife_oranlari[risk_sinifi][deprem_bolgesi - 1] / 1000) * sure_carpani
    if tl_bedel < 850_000_000:
        return bedel * oran * (1 - koasurans_ind) * (1 - muafiyet_ind)
    else:
        return (oran * 850_000_000 * (1 - koasurans_ind) * (1 - muafiyet_ind)) / kur_karsilik

def hesapla_cpm(bedel):
    tl_bedel = bedel * kur_karsilik
    if tl_bedel < 850_000_000:
        oran = 0.002
    else:
        oran = (0.002 * 850_000_000) / tl_bedel
    return bedel * oran

def hesapla_cpe(bedel):
    tl_bedel = bedel * kur_karsilik
    oran = 0.0012495
    if tl_bedel < 850_000_000:
        return bedel * oran
    else:
        return 850_000_000 * oran / kur_karsilik
