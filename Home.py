import streamlit as st

# Sayfa Ayarları
st.set_page_config(
    page_title="TariffEQ – Smart Insurance Calculator",
    layout="wide",
    page_icon="📊"
)

# Dil seçimi
lang = st.sidebar.radio("Language / Dil", ["TR", "EN"], index=0, horizontal=True)
st.sidebar.page_link("/Tariffeq_Calculation", label="🚀 Hemen Hesapla / Calculate Now !")

# Çeviri sözlüğü
T = {
    "title": {"TR": "TariffEQ", "EN": "TariffEQ"},
    "subtitle": {
        "TR": "Akıllı Sigorta Prim Hesaplama Platformu",
        "EN": "Smart Insurance Premium Calculation Platform"
    },
    "start": {"TR": "Hesaplamaya Başla", "EN": "Start Calculation"},
    "desc": {
        "TR": "TariffEQ, deprem, inşaat ve ticari rizikolar için minimum prim hesaplamalarını saniyeler içinde yapmanızı sağlar.",
        "EN": "TariffEQ enables you to calculate minimum insurance premiums for earthquake, construction, and commercial risks within seconds."
    },
    "why": {"TR": "Neden TariffEQ?", "EN": "Why TariffEQ?"},
    "feature1": {"TR": "⚡ Kolay ve Hızlı Kullanım", "EN": "⚡ Easy & Fast Use"},
    "feature2": {"TR": "📐 Teknik Doğruluk", "EN": "📐 Technical Accuracy"},
    "feature3": {"TR": "🤝 Reasürör ve Broker Dostu", "EN": "🤝 Reinsurer & Broker Friendly"},
    "founders": {"TR": "Kurucular", "EN": "Founders"},
    "contact": {
        "TR": "Sorularınız için bize info@tariffeq.com adresinden ulaşabirsiniz.",
        "EN": "For inquiries, contact us at info@tariffeq.com"
    },
    "footer": {
        "TR": "© 2025 TariffEQ. Tüm Hakları Saklıdır.",
        "EN": "© 2025 TariffEQ. All rights reserved."
    },
    "comment": {"TR": "Yorum Bırak", "EN": "Leave a Comment"},
    "comment_placeholder": {"TR": "Yorumunuzu buraya yazın...", "EN": "Write your comment here..."},
    "submit": {"TR": "Gönder", "EN": "Submit"}
}

# Özel CSS
st.markdown("""
<style>
    .header {
        background-color: #E8F4FD;
        padding: 2em;
        text-align: center;
        border-radius: 12px;
        margin-bottom: 1.5em;
    }
    .header img {
        height: 280px;
        margin-bottom: 1em;
    }
    .header h1 {
        font-size: 3.2em;
        color: #2E86C1;
        margin-bottom: 0.2em;
    }
    .header h3 {
        color: #5DADE2;
        font-weight: 400;
    }
    .card {
        background-color: #F0F4FA;
        padding: 1.5em;
        border-radius: 12px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.05);
        text-align: center;
        margin-bottom: 1em;
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

# Başlık
st.markdown("""
<div class="header">
    <img src="https://i.ibb.co/PzWSdnQb/Logo.png" alt="TariffEQ Logo" />
    <h1>TariffEQ</h1>
    <h3>{}</h3>
</div>
""".format(T["subtitle"][lang]), unsafe_allow_html=True)

# Açıklama ve Başlat Butonu
st.markdown(f"#### {T['desc'][lang]}")
if st.button(T['start'][lang]):
    st.switch_page("/Tariffeq_Calculation")

# Neden TariffEQ
st.markdown(f"### {T['why'][lang]}")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"<div class='card'>{T['feature1'][lang]}</div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div class='card'>{T['feature2'][lang]}</div>", unsafe_allow_html=True)
with col3:
    st.markdown(f"<div class='card'>{T['feature3'][lang]}</div>", unsafe_allow_html=True)

# Kurucular
st.markdown(f"### {T['founders'][lang]}")
f1, f2 = st.columns(2)
with f1:
    st.image("https://i.ibb.co/99NWxnxH/furkan.jpg", width=150)
    st.markdown("**Osman Furkan Kaymaz**")
    st.markdown("[LinkedIn](https://www.linkedin.com/in/furkan-kaymaz-97736718b/)")
with f2:
    st.image("https://i.ibb.co/K3ysQ1x/ubeydullah.jpg", width=150)
    st.markdown("**Ubeydullah Ayvaz**")
    st.markdown("[LinkedIn](https://www.linkedin.com/in/ubeydullah-ayvaz-762269143/)")

# İletişim
st.markdown(f"### Contact")
st.info(T['contact'][lang])

# Yorum Kutusu
st.markdown(f"### {T['comment'][lang]}")
comment = st.text_area(label="", placeholder=T['comment_placeholder'][lang])
if st.button(T['submit'][lang]):
    if comment.strip():
        st.success("Teşekkürler, yorumunuz alınmıştır.")
    else:
        st.warning("Lütfen boş yorum göndermeyiniz.")

# Footer
st.markdown(f"<div class='footer'>{T['footer'][lang]}</div>", unsafe_allow_html=True)
