"""
Tekstil Lead Finder - Web Dashboard
Built with Streamlit
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

from database.models import get_session, Lead, EmailLog, EmailCampaign
from config.settings import TARGET_MARKETS, SEARCH_KEYWORDS, COMPANY_INFO

# Page config
st.set_page_config(
    page_title="Tekstil Lead Finder",
    page_icon="🧵",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    .stProgress > div > div > div > div {
        background-color: #1f77b4;
    }
</style>
""", unsafe_allow_html=True)


def get_lead_stats():
    """Get lead statistics from database"""
    session = get_session()

    stats = {
        "total": session.query(Lead).count(),
        "with_email": session.query(Lead).filter(Lead.email.isnot(None)).count(),
        "new": session.query(Lead).filter(Lead.status == "new").count(),
        "contacted": session.query(Lead).filter(Lead.status == "contacted").count(),
        "responded": session.query(Lead).filter(Lead.status == "responded").count(),
        "interested": session.query(Lead).filter(Lead.status == "interested").count(),
        "converted": session.query(Lead).filter(Lead.status == "converted").count(),
    }

    session.close()
    return stats


def get_leads_dataframe(filters=None):
    """Get leads as DataFrame"""
    session = get_session()
    query = session.query(Lead)

    if filters:
        if filters.get("status"):
            query = query.filter(Lead.status == filters["status"])
        if filters.get("country"):
            query = query.filter(Lead.country == filters["country"])
        if filters.get("has_email"):
            query = query.filter(Lead.email.isnot(None))

    leads = query.order_by(Lead.created_at.desc()).all()
    session.close()

    data = [lead.to_dict() for lead in leads]
    return pd.DataFrame(data)


def main():
    st.title("🧵 Tekstil Lead Finder")
    st.markdown("**Otomatik Müşteri Bulma Sistemi**")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Ayarlar")

        st.subheader("Firma Bilgileri")
        st.write(f"**Firma:** {COMPANY_INFO.get('name', 'N/A')}")
        st.write(f"**Kapasite:** {COMPANY_INFO.get('monthly_capacity', 'N/A')}")

        st.divider()

        page = st.radio(
            "Sayfa Seçin",
            ["📊 Dashboard", "🔍 Lead Arama", "📋 Lead Listesi", "📧 E-posta Kampanyası", "📈 Raporlar"]
        )

    # Main content based on page selection
    if page == "📊 Dashboard":
        show_dashboard()
    elif page == "🔍 Lead Arama":
        show_search_page()
    elif page == "📋 Lead Listesi":
        show_leads_page()
    elif page == "📧 E-posta Kampanyası":
        show_campaign_page()
    elif page == "📈 Raporlar":
        show_reports_page()


def show_dashboard():
    """Dashboard overview"""
    st.header("Dashboard")

    # Get stats
    stats = get_lead_stats()

    # Metrics row
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Toplam Lead", stats["total"])
    with col2:
        st.metric("E-posta Var", stats["with_email"])
    with col3:
        st.metric("Yeni", stats["new"])
    with col4:
        st.metric("İletişim Kuruldu", stats["contacted"])
    with col5:
        st.metric("Dönüşüm", stats["converted"])

    st.divider()

    # Charts row
    col1, col2 = st.columns(2)

    with col1:
        # Status distribution
        status_data = {
            "Durum": ["Yeni", "İletişim", "Yanıt", "İlgili", "Dönüşüm"],
            "Sayı": [stats["new"], stats["contacted"], stats["responded"],
                     stats["interested"], stats["converted"]]
        }
        fig = px.pie(
            status_data,
            values="Sayı",
            names="Durum",
            title="Lead Durumu Dağılımı",
            hole=0.4
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Email coverage
        email_data = {
            "Kategori": ["E-posta Var", "E-posta Yok"],
            "Sayı": [stats["with_email"], stats["total"] - stats["with_email"]]
        }
        fig = px.pie(
            email_data,
            values="Sayı",
            names="Kategori",
            title="E-posta Kapsamı",
            hole=0.4,
            color_discrete_sequence=["#2ecc71", "#e74c3c"]
        )
        st.plotly_chart(fig, use_container_width=True)

    # Recent leads
    st.subheader("Son Eklenen Leadler")
    df = get_leads_dataframe()
    if not df.empty:
        st.dataframe(
            df[["company_name", "country", "email", "status", "source", "created_at"]].head(10),
            use_container_width=True
        )
    else:
        st.info("Henüz lead bulunmuyor. Arama yaparak başlayın!")


def show_search_page():
    """Lead search page"""
    st.header("🔍 Lead Arama")

    col1, col2 = st.columns(2)

    with col1:
        search_query = st.text_input(
            "Arama Terimi",
            value="textile importer",
            help="Örn: textile importer, clothing wholesaler"
        )

        market = st.selectbox(
            "Hedef Pazar",
            options=list(TARGET_MARKETS.keys()),
            format_func=lambda x: {
                "europe": "🇪🇺 Avrupa",
                "middle_east": "🇦🇪 Orta Doğu",
                "usa": "🇺🇸 ABD",
                "turkey": "🇹🇷 Türkiye"
            }.get(x, x)
        )

    with col2:
        countries = list(TARGET_MARKETS.get(market, {}).keys())
        selected_country = st.selectbox("Ülke", options=["Tümü"] + countries)

        source = st.selectbox(
            "Kaynak",
            options=["all", "google", "europages", "kompass"],
            format_func=lambda x: {
                "all": "Tüm Kaynaklar",
                "google": "Google/DuckDuckGo",
                "europages": "Europages",
                "kompass": "Kompass"
            }.get(x, x)
        )

    col1, col2 = st.columns(2)
    with col1:
        max_results = st.slider("Maksimum Sonuç", 10, 100, 30)
    with col2:
        enrich_emails = st.checkbox("E-posta Bul", value=True)

    if st.button("🔍 Aramayı Başlat", type="primary"):
        with st.spinner("Aranıyor..."):
            # Import and run search
            from scrapers import GoogleScraper, EuropagesScraper

            leads = []
            location = selected_country if selected_country != "Tümü" else ""

            progress_bar = st.progress(0)
            status_text = st.empty()

            # Google search
            if source in ["all", "google"]:
                status_text.text("Google'da aranıyor...")
                scraper = GoogleScraper()
                google_leads = scraper.search(search_query, location, max_results)
                leads.extend(google_leads)
                progress_bar.progress(33)

            # Europages search
            if source in ["all", "europages"]:
                status_text.text("Europages'de aranıyor...")
                scraper = EuropagesScraper()
                euro_leads = scraper.search(search_query, location)
                leads.extend(euro_leads)
                progress_bar.progress(66)

            # Enrich emails
            if enrich_emails and leads:
                status_text.text("E-postalar bulunuyor...")
                from email_tools import EmailEnricher
                enricher = EmailEnricher()
                for i, lead in enumerate(leads[:20]):  # Limit for speed
                    leads[i] = enricher.enrich_lead(lead)

            progress_bar.progress(100)
            status_text.text("Tamamlandı!")

            # Save to database
            session = get_session()
            saved = 0
            for lead_data in leads:
                existing = session.query(Lead).filter_by(
                    company_name=lead_data.get("company_name"),
                    website=lead_data.get("website")
                ).first()

                if not existing:
                    lead = Lead(
                        company_name=lead_data.get("company_name"),
                        website=lead_data.get("website"),
                        email=lead_data.get("email"),
                        country=selected_country if selected_country != "Tümü" else None,
                        source=lead_data.get("source"),
                        search_query=search_query
                    )
                    session.add(lead)
                    saved += 1

            session.commit()
            session.close()

            st.success(f"✅ {len(leads)} lead bulundu, {saved} yeni kaydedildi!")

            # Show results
            if leads:
                df = pd.DataFrame(leads)
                st.dataframe(df[["company_name", "website", "email", "source"]].head(20))


def show_leads_page():
    """Lead list and management"""
    st.header("📋 Lead Listesi")

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        status_filter = st.selectbox(
            "Durum",
            options=["Tümü", "new", "contacted", "responded", "interested", "converted"]
        )
    with col2:
        email_filter = st.checkbox("Sadece e-postası olanlar")
    with col3:
        pass

    # Build filters
    filters = {}
    if status_filter != "Tümü":
        filters["status"] = status_filter
    if email_filter:
        filters["has_email"] = True

    # Get data
    df = get_leads_dataframe(filters)

    if df.empty:
        st.info("Filtrelere uygun lead bulunamadı.")
        return

    st.write(f"**{len(df)} lead bulundu**")

    # Display with editing capability
    edited_df = st.data_editor(
        df[["id", "company_name", "website", "email", "country", "status", "score"]],
        use_container_width=True,
        num_rows="fixed",
        column_config={
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "status": st.column_config.SelectboxColumn(
                "Durum",
                options=["new", "contacted", "responded", "interested", "converted"]
            ),
            "score": st.column_config.NumberColumn("Skor", min_value=0, max_value=100)
        }
    )

    # Export button
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Excel'e Aktar"):
            from config.settings import EXPORTS_DIR
            filepath = EXPORTS_DIR / f"leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df.to_excel(filepath, index=False)
            st.success(f"✅ {filepath} dosyasına aktarıldı")


def show_campaign_page():
    """Email campaign management"""
    st.header("📧 E-posta Kampanyası")

    # Template selection
    templates = {
        "initial_contact_en": "🇬🇧 İlk İletişim (İngilizce)",
        "initial_contact_de": "🇩🇪 İlk İletişim (Almanca)",
        "initial_contact_tr": "🇹🇷 İlk İletişim (Türkçe)",
        "follow_up_1": "📩 Takip E-postası 1",
        "follow_up_2": "📩 Takip E-postası 2"
    }

    selected_template = st.selectbox(
        "E-posta Şablonu",
        options=list(templates.keys()),
        format_func=lambda x: templates.get(x, x)
    )

    # Preview template
    from outreach import EmailTemplateManager
    template_mgr = EmailTemplateManager(COMPANY_INFO)

    with st.expander("📝 Şablon Önizleme"):
        try:
            rendered = template_mgr.render_template(selected_template, {
                "contact_name": "John Doe",
                "their_company": "ABC Textiles Ltd.",
                "company_name": "ABC Textiles Ltd."
            })
            st.write(f"**Konu:** {rendered['subject']}")
            st.text_area("İçerik", rendered["body"], height=300, disabled=True)
        except Exception as e:
            st.error(f"Şablon hatası: {e}")

    st.divider()

    # Campaign settings
    col1, col2 = st.columns(2)

    with col1:
        target_status = st.selectbox(
            "Hedef Lead Durumu",
            options=["new", "contacted"]
        )
    with col2:
        send_limit = st.number_input("Gönderilecek E-posta Sayısı", 1, 50, 10)

    # Get eligible leads
    session = get_session()
    eligible = session.query(Lead).filter(
        Lead.email.isnot(None),
        Lead.status == target_status
    ).count()
    session.close()

    st.info(f"📊 {eligible} uygun lead mevcut")

    # Send buttons
    col1, col2 = st.columns(2)

    with col1:
        if st.button("👁️ Önizle (Test)"):
            st.warning("Bu bir test önizlemesidir. E-posta gönderilmedi.")

    with col2:
        if st.button("📤 Kampanyayı Başlat", type="primary"):
            st.error("⚠️ SMTP ayarlarını .env dosyasında yapılandırın!")
            st.code("""
# .env dosyası örneği:
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_NAME=Your Company
FROM_EMAIL=your-email@gmail.com
            """)


def show_reports_page():
    """Reports and analytics"""
    st.header("📈 Raporlar")

    # Date range
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Başlangıç", datetime.now() - timedelta(days=30))
    with col2:
        end_date = st.date_input("Bitiş", datetime.now())

    # Get data
    df = get_leads_dataframe()

    if df.empty:
        st.info("Rapor için yeterli veri yok.")
        return

    # Convert created_at to datetime
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"])
        df["date"] = df["created_at"].dt.date

    # Leads over time
    st.subheader("Zaman İçinde Lead Sayısı")
    daily_leads = df.groupby("date").size().reset_index(name="count")
    fig = px.line(daily_leads, x="date", y="count", title="Günlük Yeni Leadler")
    st.plotly_chart(fig, use_container_width=True)

    # By country
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Ülkelere Göre")
        if "country" in df.columns:
            country_stats = df["country"].value_counts().head(10)
            fig = px.bar(
                x=country_stats.index,
                y=country_stats.values,
                labels={"x": "Ülke", "y": "Lead Sayısı"}
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Kaynaklara Göre")
        if "source" in df.columns:
            source_stats = df["source"].value_counts()
            fig = px.pie(values=source_stats.values, names=source_stats.index)
            st.plotly_chart(fig, use_container_width=True)

    # Conversion funnel
    st.subheader("Dönüşüm Hunisi")
    stats = get_lead_stats()
    funnel_data = {
        "Aşama": ["Toplam Lead", "E-posta Var", "İletişim Kuruldu", "Yanıt Aldı", "İlgili", "Dönüşüm"],
        "Sayı": [
            stats["total"],
            stats["with_email"],
            stats["contacted"],
            stats["responded"],
            stats["interested"],
            stats["converted"]
        ]
    }
    fig = go.Figure(go.Funnel(
        y=funnel_data["Aşama"],
        x=funnel_data["Sayı"],
        textinfo="value+percent initial"
    ))
    st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
