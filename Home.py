import streamlit as st

# Sayfa yapılandırması
st.set_page_config(page_title="Tariffeq - Akıllı Sigorta Hesaplama", page_icon="📊", layout="wide")

# CSS ile stil
st.markdown("""
    <style>
        .main-container {
            padding: 2rem;
        }
        .header {
            text-align: center;
            color: #2E86C1;
            font-size: 3em;
            margin-bottom: 0.1em;
        }
        .subheader {
            text-align: center;
            color: #5DADE2;
            font-size: 1.3em;
            margin-bottom: 1.5em;
        }
        .section {
            background-color: #f9f9f9;
            padding: 2rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        }
        .centered-button {
            display: flex;
            justify-content: center;
            margin-top: 1.5rem;
        }
        footer {
            text-align: center;
            color: #aaa;
            margin-top: 3rem;
            font-size: 0.9rem;
        }
    </style>
""", unsafe_allow_html=True)

# Başlıklar
st.markdown('<div class="main-container">', unsafe_allow_html=True)
st.markdown('<div class="header">Tariffeq</div>', unsafe_allow_html=True)
st.markdown('<div class="subheader">Akıllı Sigorta Prim Hesaplama Çözümünüz</div>', unsafe_allow_html=True)

# Logo (güncel parametre ile)
st.image("https://i.ibb.co/PzWSdnQb/Logo.png", use_container_width=True)

# Giriş bölümü
with st.container():
    st.markdown('<div class="section">', unsafe_allow_html=True)
    st.markdown("### Hoş Geldiniz!")
    st.write("Tariffeq, işletmenizin sigorta ihtiyaçlarını hızlı ve doğru bir şekilde hesaplamanıza olanak tanır. Deprem, inşaat ve daha birçok alanda prim hesaplamalarınızı kolayca yapın.")
    st.markdown('<div class="centered-button">', unsafe_allow_html=True)
    if st.button("Hesaplamaya Başla"):
        st.switch_page("pages/Hesaplama.py")  # sayfa yönlendirme
    st.markdown('</div></div>', unsafe_allow_html=True)

# Neden Tariffeq
with st.container():
    st.markdown('<div class="section">', unsafe_allow_html=True)
    st.markdown("### Neden Tariffeq?")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**🚀 Hızlı ve Güvenilir**")
        st.write("Prim hesaplamalarınızı saniyeler içinde yapın.")
    with col2:
        st.markdown("**📦 Kapsamlı Teminatlar**")
        st.write("Deprem, yangın, inşaat ve daha fazlası için destek.")
    with col3:
        st.markdown("**🖥️ Kullanıcı Dostu**")
        st.write("Basit arayüzle kolay kullanım.")
    st.markdown('</div>', unsafe_allow_html=True)

# İletişim
with st.container():
    st.markdown('<div class="section">', unsafe_allow_html=True)
    st.markdown("### Bizimle İletişime Geçin")
    st.write("Sorularınız mı var? Bize ulaşın: **info@tariffeq.com**")
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown('<footer>© 2025 Tariffeq. Tüm Hakları Saklıdır.</footer>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
