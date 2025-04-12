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

st.set_page_config(page_title="TarifeX", layout="centered")
st.markdown("""
    <style>
    body { background-color: #f9fbfc; }
    .stApp { padding-top: 2rem; }
    h1 { font-size: 50px !important; }
    p { font-size: 18px; }
    </style>
    <h1 style='text-align: center; color: #1F618D;'>TarifeX</h1>
    <p style='text-align: center;'>Akıllı Sigorta Prim Hesaplama Uygulaması</p>
    <p style='text-align: center; font-size: 16px; color: #7f8c8d;'>Founder: <b>Ubeydullah Ayvaz</b> & <b>Furkan Kaymaz</b></p>
""", unsafe_allow_html=True)


hesaplama_tipi = st.radio("Hesaplama Türünü Seçin", ["Deprem Teminatı (PD & BI)", "İnşaat & Montaj (CAR & EAR)"])

if hesaplama_tipi == "Deprem Teminatı (PD & BI)":
    st.subheader("🌊 Deprem Primi Hesaplayıcı")
    bina_tipi = st.selectbox("Bina Tipi", ["Betonarme", "Diğer"])
    deprem_bolgesi = st.selectbox("Deprem Risk Bölgesi (1=En Yüksek Risk)", list(range(1, 8)))
    para_birimi = st.selectbox("Para Birimi", ["TRY", "USD", "EUR"])
    kur_karsilik = 1.0
    if para_birimi != "TRY":
        kur_karsilik = st.number_input(f"1 {para_birimi} = ... TL", min_value=0.1, step=0.1, value=30.0)

    damage = st.number_input("PD - Fiziki Hasar Bedeli", min_value=0, step=1000)
    bi = st.number_input("BI - Kar Kaybı Bedeli", min_value=0, step=1000)
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
