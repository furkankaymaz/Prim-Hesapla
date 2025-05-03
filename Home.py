import streamlit as st

# Sayfa yapılandırması
st.set_page_config(page_title="Tariffeq - Akıllı Sigorta Hesaplama", page_icon="📊", layout="wide")

# CSS ile stil ekleme
st.markdown("""
<style>
    .header {
        text-align: center;
        color: #2E86C1;
        font-size: 3em;
        margin-bottom: 0.2em;
    }
    .subheader {
        text-align: center;
        color: #5DADE2;
        font-size: 1.5em;
        margin-bottom: 1em;
    }
    .section {
        background-color: #F0F8FF;
        padding: 2em;
        border-radius: 10px;
        margin-bottom: 1em;
    }
    .button {
        display: flex;
        justify-content: center;
    }
</style>
""", unsafe_allow_html=True)

# Başlık ve Alt Başlık
st.markdown('<h1 class="header">Tariffeq</h1>', unsafe_allow_html=True)
st.markdown('<p class="subheader">Akıllı Sigorta Prim Hesaplama Çözümünüz</p>', unsafe_allow_html=True)

# Logo veya Görsel
st.image("https://i.ibb.co/PzWSdnQb/Logo.png", use_column_width=True)

# Giriş Bölümü
with st.container():
    st.markdown('<div class="section">', unsafe_allow_html=True)
    st.write("### Hoş Geldiniz!")
    st.write("Tariffeq, işletmenizin sigorta ihtiyaçlarını hızlı ve doğru bir şekilde hesaplamanıza olanak tanır. Deprem, inşaat ve daha birçok alanda prim hesaplamalarınızı kolayca yapın!")
    st.markdown('<div class="button">', unsafe_allow_html=True)
    if st.button("Hesaplamaya Başla"):
        st.write("Hesaplama sayfasına yönlendiriliyorsunuz...")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Özellikler Bölümü
with st.container():
    st.markdown('<div class="section">', unsafe_allow_html=True)
    st.write("### Neden Tariffeq?")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write("**Hızlı ve Güvenilir**")
        st.write("Prim hesaplamalarınızı saniyeler içinde yapın.")
    with col2:
        st.write("**Kapsamlı Teminatlar**")
        st.write("Deprem, yangın, inşaat ve daha fazlası için destek.")
    with col3:
        st.write("**Kullanıcı Dostu**")
        st.write("Basit arayüzle kolay kullanım.")
    st.markdown('</div>', unsafe_allow_html=True)

# İletişim Bölümü
with st.container():
    st.markdown('<div class="section">', unsafe_allow_html=True)
    st.write("### Bizimle İletişime Geçin")
    st.write("Sorularınız mı var? Bize ulaşın: **info@tariffeq.com**")
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown('<p style="text-align: center; color: #888;">© 2025 Tariffeq. Tüm Hakları Saklıdır.</p>', unsafe_allow_html=True)
