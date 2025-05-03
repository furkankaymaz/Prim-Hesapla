import streamlit as st

# Sayfa yapılandırması
st.set_page_config(page_title="Tariffeq", layout="centered")

# CSS stilleri
st.markdown("""
<style>
    .main-title {
        font-size: 3em;
        color: #2E86C1;
        text-align: center;
        margin-top: 0.2em;
        margin-bottom: 0.2em;
    }
    .subtitle {
        font-size: 1.4em;
        color: #5DADE2;
        text-align: center;
        margin-bottom: 1em;
    }
    .info-box {
        background-color: #F0F8FF;
        padding: 1.5em;
        border-radius: 10px;
        margin: 1em 0;
    }
    .stButton>button {
        background-color: #2E86C1;
        color: white;
        border-radius: 8px;
        padding: 0.5em 1.2em;
        font-size: 1em;
    }
    .stButton>button:hover {
        background-color: #1A5276;
    }
</style>
""", unsafe_allow_html=True)

# Logo ve Başlıklar
st.image("https://i.ibb.co/PzWSdnQb/Logo.png", use_column_width=True)
st.markdown('<h1 class="main-title">Tariffeq</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Akıllı Sigorta Prim Hesaplama Çözümünüz</p>', unsafe_allow_html=True)

# Tanıtım Metni
st.markdown("""
<div class="info-box">
    <h3>📌 Tariffeq ile Neler Yapabilirsiniz?</h3>
    <ul>
        <li>✅ Deprem, inşaat ve montaj projeleri için prim hesaplayın</li>
        <li>✅ Güncel döviz kuru üzerinden anlık hesaplama</li>
        <li>✅ Gelişmiş kullanıcı arayüzü ile kolay kullanım</li>
    </ul>
</div>
""", unsafe_allow_html=True)

# Başlatma Butonu
st.markdown('<div style="text-align: center;">', unsafe_allow_html=True)
if st.button("🔍 Hesaplamaya Başla"):
    st.switch_page("pages/Hesaplama.py")
st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown('<p style="text-align: center; color: #888;">© 2025 Tariffeq. Developed by Furkan Kaymaz</p>', unsafe_allow_html=True)
