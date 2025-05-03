import streamlit as st

# Sayfa ayarı
st.set_page_config(page_title="Tariffeq - Smart Insurance Calculator", layout="wide")

# Dil seçimi
lang = st.sidebar.radio("Language / Dil", ["TR", "EN"], index=0, horizontal=True)

# Çeviri sözlüğü
T = {
    "title": {"TR": "Tariffeq", "EN": "Tariffeq"},
    "subtitle": {
        "TR": "Akıllı Sigorta Prim Hesaplama Platformu",
        "EN": "Smart Insurance Premium Calculation Platform"
    },
    "start": {"TR": "Hesaplamaya Başla", "EN": "Start Calculation"},
    "desc": {
        "TR": "Tariffeq, deprem, inşaat ve ticari rizikolar için minimum prim hesaplamalarını saniyeler içinde yapmanızı sağlar.",
        "EN": "Tariffeq enables you to calculate minimum insurance premiums for earthquake, construction, and commercial risks within seconds."
    },
    "why": {"TR": "Neden Tariffeq?", "EN": "Why Tariffeq?"},
    "feature1": {"TR": "✨ Kolay ve Hızlı Kullanım", "EN": "✨ Easy & Fast Use"},
    "feature2": {"TR": "⚖️ Teknik Doğruluk", "EN": "⚖️ Technical Accuracy"},
    "feature3": {"TR": "🤝 Reasürör ve Broker Dostu", "EN": "🤝 Reinsurer & Broker Friendly"},
    "founders": {"TR": "Kurucular", "EN": "Founders"},
    "contact": {
        "TR": "Sorularınız için bize info@tariffeq.com adresinden ulaşabilirsiniz.",
        "EN": "For inquiries, contact us at info@tariffeq.com"
    },
    "footer": {
        "TR": "© 2025 Tariffeq. Tüm Hakları Saklıdır.",
        "EN": "© 2025 Tariffeq. All rights reserved."
    }
}

# CSS (geliştirilmiş profesyonel tasarım)
st.markdown("""
    <style>
    .main-title {
        font-size: 3.5em;
        font-weight: 700;
        background: linear-gradient(90deg, #1E3A8A 0%, #3B82F6 100%);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        text-align: center;
        margin-bottom: 0.2em;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .subtitle {
        font-size: 1.8em;
        color: #64748B;
        font-weight: 500;
        text-align: center;
        margin-bottom: 1.5em;
    }
    .section {
        background: linear-gradient(135deg, #F1F5F9 0%, #E0E7FF 100%);
        border-radius: 15px;
        padding: 2em;
        margin: 1em 0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        transition: transform 0.3s ease;
    }
    .section:hover {
        transform: translateY(-5px);
    }
    .founder-section {
        background: linear-gradient(135deg, #E0E7FF 0%, #F1F5F9 100%);
        border-radius: 15px;
        padding: 2em;
        margin: 1em 0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        text-align: center;
    }
    .founder-card {
        display: inline-block;
        margin: 1em;
        padding: 1.5em;
        background: white;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
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
        border: 3px solid #2E86C1;
        margin-bottom: 0.5em;
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
        font-size: 0.9em;
        color: #64748B;
        margin-top: 2em;
        padding-top: 1em;
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

# Header
st.markdown(f"<div class='main-title'>{T['title'][lang]}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='subtitle'>{T['subtitle'][lang]}</div>", unsafe_allow_html=True)

# Logo
try:
    st.image("https://i.ibb.co/PzWSdnQb/Logo.png", use_container_width=True)
except Exception:
    st.warning("Logo yüklenemedi. Lütfen URL'yi kontrol edin.")

# Description
with st.container():
    st.markdown(f"<div class='section'>", unsafe_allow_html=True)
    st.write(f"### {T['desc'][lang]}")
    if st.button(T['start'][lang]):
        st.success(T['desc'][lang])  # Yönlendirme yerine başarı mesajı
    st.markdown("</div>", unsafe_allow_html=True)

# Features
with st.container():
    st.markdown(f"<div class='section'>", unsafe_allow_html=True)
    st.write(f"### {T['why'][lang]}")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(T['feature1'][lang])
    with col2:
        st.info(T['feature2'][lang])
    with col3:
        st.info(T['feature3'][lang])
    st.markdown("</div>", unsafe_allow_html=True)

# Founders
with st.container():
    st.markdown(f"<div class='founder-section'>", unsafe_allow_html=True)
    st.write(f"### {T['founders'][lang]}")
    col1, col2 = st.columns(2)
    with col1:
        try:
            st.markdown('<div class="founder-card">', unsafe_allow_html=True)
            st.image("https://i.ibb.co/99NWxnxH/furkan.jpg", caption="Furkan Kaymaz", use_container_width=False, width=150)
            st.markdown(f'<a href="https://www.linkedin.com/in/furkan-kaymaz-97736718b/" target="_blank">Furkan Kaymaz</a>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        except Exception:
            st.warning("Furkan Kaymaz'ın fotoğrafı yüklenemedi. Lütfen URL'yi kontrol edin.")
    with col2:
        try:
            st.image("https://i.ibb.co/K3ysQ1x/ubeydullah.jpg", caption="Ubeydullah Ayvaz", use_container_width=False, width=150)
            st.markdown(f'<a href="https://www.linkedin.com/in/ubeydullah-ayvaz-762269143/" target="_blank">Ubeydullah Ayvaz</a>', unsafe_allow_html=True)
        except Exception:
            st.warning("Ubeydullah Ayvaz'ın fotoğrafı yüklenemedi. Lütfen URL'yi kontrol edin.")
    st.markdown("</div>", unsafe_allow_html=True)

# Contact
with st.container():
    st.markdown(f"<div class='section'>", unsafe_allow_html=True)
    st.write(f"### Contact")
    st.write(T['contact'][lang])
    st.markdown("</div>", unsafe_allow_html=True)

# Footer
st.markdown(f"<div class='footer'>{T['footer'][lang]}</div>", unsafe_allow_html=True)
