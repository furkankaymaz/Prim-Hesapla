
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

st.title("📌 Prim Hesaplama Uygulaması")
hesaplama_tipi = st.radio("Hesaplama Türünü Seçin", ["Deprem Teminatı (PD & BI)", "İnşaat & Montaj (CAR & EAR)"])

if hesaplama_tipi == "Deprem Teminatı (PD & BI)":
    st.warning("PD & BI hesaplama modülü bu sürümde devre dışı bırakıldı.")

elif hesaplama_tipi == "İnşaat & Montaj (CAR & EAR)":
    st.subheader("🧱 CAR & EAR Primi Hesaplayıcı")
    st.markdown("Bu bölüm inşaat ve montaj işleri için teknik prim hesaplamasına yöneliktir.")

    risk_sinifi = st.selectbox("Risk Sınıfı", ["A", "B"])
    deprem_bolgesi = st.selectbox("Deprem Risk Bölgesi", list(range(1, 8)))
    baslangic_tarihi = st.date_input("Başlangıç Tarihi")
    bitis_tarihi = st.date_input("Bitiş Tarihi")

    def hesapla_sure_ay(bas, bit):
        ay = (bit.year - bas.year) * 12 + (bit.month - bas.month)
        if bit.day >= 15:
            ay += 1
        return ay

    sigorta_suresi = hesapla_sure_ay(baslangic_tarihi, bitis_tarihi)
    st.markdown(f"📅 Süre: {sigorta_suresi} ay")

    koasurans = st.selectbox("Koasürans Oranı", list(koasurans_indirimi.keys()), key="car")
    muafiyet = st.selectbox("Muafiyet Oranı (%)", list(muafiyet_indirimi.keys()), key="carmuaf")
    kur = st.selectbox("Para Birimi", ["TRY", "USD", "EUR"], key="carkur")
    kur_karsilik = 1.0
    if kur != "TRY":
        kur_karsilik = st.number_input(f"1 {kur} = ... TL", min_value=0.1, step=0.1, value=30.0, key="car_kur")

    st.markdown("---")
    st.markdown("**Teminat Bedelleri**")
    car_bedel = st.number_input("🏗️ CAR Bedeli", min_value=0, step=1000000)
    cpm_bedel = st.number_input("🛠️ CPM Bedeli", min_value=0, step=1000000)
    cpe_bedel = st.number_input("⚙️ CPE Bedeli", min_value=0, step=1000000)

    if st.button("Hesapla", key="carcalc"):
        koasurans_ind = koasurans_indirimi[koasurans]
        muafiyet_ind = muafiyet_indirimi[muafiyet]

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

        sure_carpani = get_sure_carpani(sigorta_suresi)
        oran = (car_tarife_oranlari[risk_sinifi][deprem_bolgesi - 1] / 1000) * sure_carpani

        def hesapla_car(bedel):
            tl_bedel = bedel * kur_karsilik
            if tl_bedel < 850_000_000:
                return bedel * oran * (1 - koasurans_ind) * (1 - muafiyet_ind)
            else:
                return (oran * 850_000_000 * (1 - koasurans_ind) * (1 - muafiyet_ind)) / kur_karsilik

        def hesapla_cpm(bedel):
            tl_bedel = bedel * kur_karsilik
            if tl_bedel < 850_000_000:
                oran_cpm = 0.002
            else:
                oran_cpm = (0.002 * 850_000_000) / (tl_bedel)
            return bedel * oran_cpm

        def hesapla_cpe(bedel):
            tl_bedel = bedel * kur_karsilik
            oran = 0.0012495
            if tl_bedel < 850_000_000:
                return bedel * oran
            else:
                return 850_000_000 * oran / kur_karsilik

        car_prim = hesapla_car(car_bedel)
        cpm_prim = hesapla_cpm(cpm_bedel)
        cpe_prim = hesapla_cpe(cpe_bedel)

        toplam_prim = (car_prim + cpm_prim + cpe_prim)
        toplam_bedel = (car_bedel + cpm_bedel + cpe_bedel) * kur_karsilik

        st.subheader("📋 Hesaplama Sonucu")
        st.markdown(f"**Toplam Sigorta Bedeli (TL):** {toplam_bedel:,.2f}")
        st.markdown(f"**Koasürans İndirimi:** %{koasurans_ind*100:.2f}")
        st.markdown(f"**Muafiyet İndirimi:** %{muafiyet_ind*100:.2f}")
        st.success(f"🏗️ Toplam Minimum Prim: {toplam_prim:,.2f} TL")
