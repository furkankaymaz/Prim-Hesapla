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
        "TR": "Sorularınız için bize info@tariffeq.com adresinden ulaşabirsiniz.",
        "EN": "For inquiries, contact us at info@tariffeq.com"
    },
    "footer": {
        "TR": "© 2025 Tariffeq. Tüm Hakları Saklıdır.",
        "EN": "© 2025 Tariffeq. All rights reserved."
    }
}

# CSS
st.markdown("""
    <style>
    .main-title {
        font-size: 3.2em;
        font-weight: bold;
        color: #2E86C1;
        text-align: center;
        margin-bottom: 0.1em;
    }
    .subtitle {
        font-size: 1.5em;
        color: #5DADE2;
        text-align: center;
        margin-bottom: 1.5em;
    }
    .section {
        background-color: #f8f9fa;
        border-radius: 12px;
        padding: 2em;
        margin: 1em 0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .founder-img {
        border-radius: 50%;
        height: 150px;
        width: 150px;
        object-fit: cover;
        border: 3px solid #2E86C1;
        margin-bottom: 0.5em;
    }
    .footer {
        text-align: center;
        font-size: 0.9em;
        color: gray;
        margin-top: 2em;
        padding-top: 1em;
        border-top: 1px solid #dee2e6;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown(f"<div class='main-title'>{T['title'][lang]}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='subtitle'>{T['subtitle'][lang]}</div>", unsafe_allow_html=True)

st.image("https://i.ibb.co/PzWSdnQb/Logo.png", use_column_width=True)

# Description
with st.container():
    st.markdown(f"<div class='section'>", unsafe_allow_html=True)
    st.write(f"### {T['desc'][lang]}")
    if st.button(T['start'][lang]):
        st.success("Hesaplama sayfasına yönlendiriliyorsunuz...")
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
    st.markdown(f"<div class='section'>", unsafe_allow_html=True)
    st.write(f"### {T['founders'][lang]}")
    col1, col2 = st.columns(2)
    with col1:
        st.image("https://i.ibb.co/99NWxnx/furkan.jpg", caption="Furkan Kaymaz", use_column_width=False, width=150)
        st.markdown("[LinkedIn](https://www.linkedin.com/in/furkan-kaymaz-97736718b/)")
    with col2:
        st.image("https://i.ibb.co/K3ysQ1x/ubeydullah.jpg", caption="Ubeydullah Ayvaz", use_column_width=False, width=150)
        st.markdown("[LinkedIn](https://www.linkedin.com/in/ubeydullah-ayvaz-762269143/)")
    st.markdown("</div>", unsafe_allow_html=True)

# Contact
with st.container():
    st.markdown(f"<div class='section'>", unsafe_allow_html=True)
    st.write(f"### Contact")
    st.write(T['contact'][lang])
    st.markdown("</div>", unsafe_allow_html=True)

# Footer
st.markdown(f"<div class='footer'>{T['footer'][lang]}</div>", unsafe_allow_html=True)
