import streamlit as st

st.set_page_config(page_title="TariffEQ", layout="centered")

st.markdown("<h1 style='text-align: center;'>TariffEQ</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align: center; color: gray;'>Smart Insurance Premium Calculator</h4>", unsafe_allow_html=True)

st.write("""
TariffEQ, sigorta prim hesaplamalarını kolaylaştırmak için geliştirilmiş akıllı bir hesaplama aracıdır. 
Deprem, inşaat ve mühendislik sigortalarında doğru ve güncel prim tahminleri sunar.
""")

if st.button("Prim Hesapla"):
    st.switch_page("pages/Hesaplama.py")

st.markdown("---")
st.markdown("<small>© 2025 TariffEQ | Tüm hakları saklıdır.</small>", unsafe_allow_html=True)
