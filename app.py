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

# ... (kodun devamı çok uzun olduğu için buraya tam yerleştiremiyoruz)

