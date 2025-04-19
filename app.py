import streamlit as st
import requests

# Tarife oran tablosu (Deprem Bölgesi x Bina Tipi)
tarife_oranlari = {
    "Betonarme": [3.13, 2.63, 2.38, 1.94, 1.38, 1.06, 0.75],
    "Diğer": [6.13, 5.56, 3.75, 2.00, 1.56, 1.24, 1.06]
}

koasurans_indirimi = {
    "80/20": 0.00, "75/25": 0.0625, "70/30": 0.1250, "65/35": 0.1875,
    "60/40": 0.2500, "55/45": 0.3125, "50/50": 0.3750, "45/55": 0.4375, "40/60": 0.50,
    "30/70": 0.1250, "25/75": 0.0625
}

muafiyet_indirimi = {
    2: 0.00, 3: 0.06, 4: 0.13, 5: 0.19, 10: 0.35
}

sure_carpani_tablosu = {
    6: 0.70, 7: 0.75, 8: 0.80, 9: 0.85, 10: 0.90, 11: 0.95, 12: 1.00,
    13: 1.05, 14: 1.10, 15: 1.15, 16: 1.20, 17: 1.25, 18: 1.30, 19: 1.35, 20: 1.40,
    21: 1.45, 22: 1.50, 23: 1.55, 24: 1.60, 25: 1.65, 26: 1.70, 27: 1.74, 28: 1.78,
    29: 1.82, 30: 1.86, 31: 1.90, 32: 1.94, 33: 1.98, 34: 2.02, 35: 2.06, 36: 2.10
}

st.set_page_config(page_title="TarifeX", layout="centered")
st.markdown("""
    <style>
    body { background-color: #f9fbfc; }
    .stApp { padding-top: 2rem; }
    h1 { font-size: 50px !important; }
    p { font-size: 18px; }
    </style>
    <h1 style='text-align: center; color: #1F618D;'>TarifeX</h1>
    <p style='text-align: center;'>Akıllı Sigorta Prim Hesaplama Uygulaması</p><p style='text-align: center; font-size: 16px; color: #7f8c8d;'>Deprem ve Yanardağ Püskürmesi Teminatı için Uygulanacak Güncel Tarife</p>
    <p style='text-align: center; font-size: 16px; color: #7f8c8d;'>Founder: <b>Ubeydullah Ayvaz</b> & <b>Furkan Kaymaz</b></p>
""", unsafe_allow_html=True)

hesaplama_tipi = st.radio("Hesaplama Türünü Seçin", ["Yangın Sigortası - Ticari Sinai Rizikolar (PD & BI)", "İnşaat & Montaj (CAR & EAR)"])

if hesaplama_tipi == "Yangın Sigortası - Ticari Sinai Rizikolar (PD & BI)":
    st.subheader("🌊 Deprem Primi Hesaplayıcı")
    bina_tipi = st.selectbox("Yapı Tarzı", ["Betonarme", "Diğer"])
    deprem_bolgesi = st.selectbox("Deprem Risk Grubu (1=En Yüksek Risk)", list(range(1, 8)))
    para_birimi = st.selectbox("Para Birimi", ["TRY", "USD", "EUR"])
    kur_karsilik = 1.0
    if para_birimi != "TRY":
        kur_karsilik = st.number_input(f"1 {para_birimi} = ... TL", min_value=0.1, step=0.1, value=30.0)

    damage = st.number_input("Yangın Sigorta Bedeli (PD)", min_value=0, step=1000)
    bi = st.number_input("Kar Kaybı Bedeli (BI)", min_value=0, step=1000)
    ymm = st.number_input("Yangın Mali Mesuliyet Bedeli (YMM)", min_value=0, step=1000)
    enkaz = st.number_input("Enkaz Kaldırma Bedeli", min_value=0, step=1000)

    toplam_bedel = (damage + bi + ymm + enkaz) * kur_karsilik

    koasurans = st.selectbox("Koasürans Oranı", list(koasurans_indirimi.keys()))
    muafiyet = st.selectbox("Muafiyet Oranı (%)", list(muafiyet_indirimi.keys()))

    if st.button("Hesapla", key="deprem"):
        oran = tarife_oranlari[bina_tipi][deprem_bolgesi - 1] / 1000
        koasurans_ind = koasurans_indirimi[koasurans]
        muafiyet_ind = muafiyet_indirimi[muafiyet]
        nihai_oran = oran * (1 - koasurans_ind) * (1 - muafiyet_ind)
        prim = toplam_bedel * nihai_oran

        st.subheader("📋 Hesaplama Sonucu")
        st.markdown(f"**Tarife Oranı:** {oran*1000:.2f} ‰")
        st.markdown(f"**Koasürans İndirimi:** %{koasurans_ind*100:.2f}")
        st.markdown(f"**Muafiyet İndirimi:** %{muafiyet_ind*100:.2f}")
        st.markdown(f"**Uygulanan Oran:** %{nihai_oran*100:.4f}")
        st.markdown(f"**Toplam Sigorta Bedeli (TL):** {toplam_bedel:,.2f}")
        st.success(f"📈 Minimum Deprem Primi: {prim:,.2f} TL")

    with st.expander("💱 Merkez Bankası Güncel Döviz Satış Kuru"):
        try:
            response = requests.get("https://api.exchangerate.host/latest?base=TRY")
            data = response.json()
            usd_try = 1 / data['rates']['USD']
            eur_try = 1 / data['rates']['EUR']

            st.metric(label="USD / TRY Satış Kuru", value=f"{usd_try:.2f} TL")
            st.metric(label="EUR / TRY Satış Kuru", value=f"{eur_try:.2f} TL")

        except Exception as e:
            st.error("Döviz kurları çekilemedi. Lütfen daha sonra tekrar deneyiniz.")

elif hesaplama_tipi == "İnşaat & Montaj (CAR & EAR)":
    # mevcut kod değişmedi
