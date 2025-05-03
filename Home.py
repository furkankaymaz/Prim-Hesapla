import streamlit as st

# Sayfa yapılandırması
st.set_page_config(page_title="Tariffeq - Smart Insurance Calculator", page_icon="📊", layout="wide")

# Dil seçimi
lang = st.sidebar.radio("Language / Dil", ["TR", "EN"], index=0, horizontal=True)

# Çeviri sözlüğü
T = {
    "title": {"TR": "Tariffeq", "EN": "Tariffeq"},
    "subtitle": {"TR": "Akıllı Sigorta Prim Hesaplama Çözümünüz", "EN": "Your Smart Insurance Premium Solution"},
    "welcome": {"TR": "### Hoş Geldiniz!", "EN": "### Welcome!"},
    "welcome_text": {
        "TR": "Tariffeq, işletmenizin sigorta ihtiyaçlarını hızlı ve doğru bir şekilde hesaplamanıza olanak tanır. Deprem, inşaat ve daha birçok alanda prim hesaplamalarınızı kolayca yapın!",
        "EN": "Tariffeq enables you to quickly and accurately calculate your business insurance needs. Easily compute premiums for earthquake, construction, and more!"
    },
    "start_button": {"TR": "Hesaplamaya Başla", "EN": "Start Calculation"},
    "start_message": {"TR": "Hesaplama sayfasına yönlendiriliyorsunuz...", "EN": "Redirecting to the calculation page..."},
    "why_title": {"TR": "### Neden Tariffeq?", "EN": "### Why Tariffeq?"},
    "feature1_title": {"TR": "**Hızlı ve Güvenilir**", "EN": "**Fast & Reliable**"},
    "feature1_text": {"TR": "Prim hesaplamalarınızı saniyeler içinde yapın.", "EN": "Perform premium calculations in seconds."},
    "feature2_title": {"TR": "**Kapsamlı Teminatlar**", "EN": "**Comprehensive Coverage**"},
    "feature2_text": {"TR": "Deprem, yangın, inşaat ve daha fazlası için destek.", "EN": "Support for earthquake, fire, construction, and more."},
    "feature3_title": {"TR": "**Kullanıcı Dostu**", "EN": "**User-Friendly**"},
    "feature3_text": {"TR": "Basit arayüzle kolay kullanım.", "EN": "Easy to use with a simple interface."},
    "contact_title": {"TR": "### Bizimle İletişime Geçin", "EN": "### Contact Us"},
    "contact_text": {"TR": "Sorularınız mı var? Bize ulaşın: **info@tariffeq.com**", "EN": "Have questions? Reach us at: **info@tariffeq.com**"},
    "founders_title": {"TR": "### Kurucularımız", "EN": "### Our Founders"},
    "footer": {"TR": "© 2025 Tariffeq. Tüm Hakları Saklıdır.", "EN": "© 2025 Tariffeq. All Rights Reserved."}
}

# CSS ile stil ekleme (geliştirilmiş profesyonel tasarım)
st.markdown("""
<style>
    .header {
        text-align: center;
        color: #1E3A8A;
        font-size: 3.5em;
        font-weight: 700;
        background: linear-gradient(90deg, #1E3A8A 0%, #3B82F6 100%);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        margin-bottom: 0.3em;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.1);
    }
    .subheader {
        text-align: center;
        color: #64748B;
        font-size: 1.8em;
        font-weight: 500;
        margin-bottom: 1.5em;
    }
    .section {
        background: linear-gradient(135deg, #F1F5F9 0%, #E0E7FF 100%);
        padding: 2.5em;
        border-radius: 15px;
        margin-bottom: 1.5em;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease;
    }
    .section:hover {
        transform: translateY(-5px);
    }
    .founder-section {
        background: linear-gradient(135deg, #E0E7FF 0%, #F1F5F9 100%);
        padding: 2em;
        border-radius: 15px;
        margin-bottom: 1.5em;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
    }
    .founder-card {
        display: inline-block;
        margin: 1em;
        padding: 1.5em;
        background: white;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease;
    }
    .founder-card:hover {
        transform: scale(1.05);
    }
    .founder-img {
        border-radius: 50%;
        width: 150px;
        height: 150px;
        object-fit: cover;
    }
    .button {
        display: flex;
        justify-content: center;
        margin-top: 1em;
    }
    .stButton > button {
        background-color: #3B82F6;
        color: white;
        border: none;
        padding: 0.75em 2em;
        border-radius: 10px;
        font-size: 1.1em;
        font-weight: 500;
        transition: background-color 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #1E40AF;
        color: white;
    }
    .footer {
        text-align: center;
        color: #64748B;
        font-size: 0.9em;
        margin-top: 2em;
        padding: 1em 0;
        border-top: 1px solid #E0E7FF;
    }
    a {
        color: #3B82F6;
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
    }
</style>
""", unsafe_allow_html=True)

# Başlık ve Alt Başlık
st.markdown(f'<h1 class="header">{T["title"][lang]}</h1>', unsafe_allow_html=True)
st.markdown(f'<p class="subheader">{T["subtitle"][lang]}</p>', unsafe_allow_html=True)

# Logo veya Görsel
try:
    st.image("https://i.ibb.co/PzWSdnQb/Logo.png", use_column_width=True)
except Exception:
    st.warning("Logo yüklenemedi. Lütfen resim URL'sini kontrol edin.")

# Giriş Bölümü
with st.container():
    st.markdown('<div class="section">', unsafe_allow_html=True)
    st.markdown(f'{T["welcome"][lang]}', unsafe_allow_html=True)
    st.write(f'{T["welcome_text"][lang]}')
    st.markdown('<div class="button">', unsafe_allow_html=True)
    if st.button(T["start_button"][lang]):
        st.write(T["start_message"][lang])
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Özellikler Bölümü
with st.container():
    st.markdown('<div class="section">', unsafe_allow_html=True)
    st.markdown(f'{T["why_title"][lang]}', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'{T["feature1_title"][lang]}', unsafe_allow_html=True)
        st.write(f'{T["feature1_text"][lang]}')
    with col2:
        st.markdown(f'{T["feature2_title"][lang]}', unsafe_allow_html=True)
        st.write(f'{T["feature2_text"][lang]}')
    with col3:
        st.markdown(f'{T["feature3_title"][lang]}', unsafe_allow_html=True)
        st.write(f'{T["feature3_text"][lang]}')
    st.markdown('</div>', unsafe_allow_html=True)

# Kurucular Bölümü
with st.container():
    st.markdown('<div class="founder-section">', unsafe_allow_html=True)
    st.markdown(f'{T["founders_title"][lang]}', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        try:
            st.markdown('<div class="founder-card">', unsafe_allow_html=True)
            st.image("https://ibb.co/99NWxnxH", caption="Osman Furkan Kaymaz", use_column_width=False, output_format="auto", width=150, clamp=True)
            st.markdown(f'<a href="https://www.linkedin.com/in/furkan-kaymaz-97736718b/" target="_blank">Osman Furkan Kaymaz</a>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        except Exception:
            st.warning("Osman Furkan Kaymaz'ın fotoğrafı yüklenemedi.")
    with col2:
        try:
            st.markdown('<div class="founder-card">', unsafe_allow_html=True)
            st.image("https://ibb.co/K3ysQ1x", caption="Ubeydullah Ayvaz", use_column_width=False, output_format="auto", width=150, clamp=True)
            st.markdown(f'<a href="https://www.linkedin.com/in/ubeydullah-ayvaz-762269143/" target="_blank">Ubeydullah Ayvaz</a>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        except Exception:
            st.warning("Ubeydullah Ayvaz'ın fotoğrafı yüklenemedi.")
    st.markdown('</div>', unsafe_allow_html=True)

# İletişim Bölümü
with st.container():
    st.markdown('<div class="section">', unsafe_allow_html=True)
    st.markdown(f'{T["contact_title"][lang]}', unsafe_allow_html=True)
    st.write(f'{T["contact_text"][lang]}')
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown(f'<div class="footer">{T["footer"][lang]}</div>', unsafe_allow_html=True)
