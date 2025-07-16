"""
Multi-Standard Accounting Analysis Platform - Home Dashboard
"""

import streamlit as st

# Configure page
st.set_page_config(
    page_title="Technical Accounting AI Platform",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for branding and styling
def load_css():
    """Load custom CSS for brand consistency"""
    css = """
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Lato:wght@400;700&family=Poppins:wght@600;700&display=swap');

    /* Brand Color Variables */
    :root {
        --primary-color: #0A2B4C;
        --secondary-color: #C5A565;
        --bg-color: #F8F9FA;
        --text-color: #212529;
        --heading-font: 'Poppins', sans-serif;
        --body-font: 'Lato', sans-serif;
        --border-color: #e0e0e0;
    }

    /* Global Styling */
    html, body, [class*="st-"] {
        font-family: var(--body-font);
        color: var(--text-color);
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: var(--heading-font);
        color: var(--primary-color);
        font-weight: 700;
    }

    /* Main Container */
    .main .block-container {
        padding: 2rem;
        max-width: 1200px;
    }

    /* Expertise Cards */
    .expertise-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 1.5rem;
        margin: 2rem 0;
    }

    .expertise-card {
        background: white;
        border: 2px solid var(--secondary-color);
        border-radius: 12px;
        padding: 1.5rem;
        transition: all 0.3s ease;
        cursor: pointer;
    }

    .expertise-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        border-color: var(--primary-color);
    }

    .expertise-card h3 {
        color: var(--primary-color);
        margin-bottom: 1rem;
        font-size: 1.3rem;
    }

    .expertise-card p {
        color: #666;
        line-height: 1.6;
        margin-bottom: 1rem;
    }

    .expertise-card-disabled {
        background: #f8f9fa;
        border: 2px solid #e0e0e0;
        border-radius: 12px;
        padding: 1.5rem;
        opacity: 0.7;
    }

    .expertise-card-disabled h3 {
        color: #666;
        margin-bottom: 1rem;
        font-size: 1.3rem;
    }

    .expertise-card-disabled p {
        color: #999;
        line-height: 1.6;
    }

    /* Status Badges */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-top: 1rem;
    }

    .status-available {
        background: #d4edda;
        color: #155724;
    }

    .status-coming-soon {
        background: #fff3cd;
        color: #856404;
    }

    /* Header Styling */
    .hero-header {
        text-align: center;
        margin: 2rem 0 3rem 0;
    }

    .hero-title {
        font-family: var(--heading-font);
        font-size: 3rem;
        font-weight: 700;
        color: var(--primary-color);
        margin-bottom: 1rem;
    }

    .hero-subtitle {
        font-size: 1.3rem;
        color: #666;
        margin-bottom: 2rem;
    }
    """
    st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)

# Load styling
load_css()

# Header Section
st.markdown("""
<div class="hero-header">
    <h1 class="hero-title">Controller.cpa</h1>
    <p class="hero-subtitle">AI-Powered Technical Accounting Analysis Platform</p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# Available Standards
standards = {
    'ASC 606': {
        'name': 'Revenue from Contracts with Customers',
        'description': 'Analyze complex contracts for performance obligations, variable consideration, and proper recognition timing using the 5-step model.',
        'status': 'available',
        'page': 'pages/1_ASC_606_Revenue.py'
    },
    'ASC 842': {
        'name': 'Leases',
        'description': 'Classify leases as operating or finance and generate amortization schedules and journal entries automatically.',
        'status': 'coming_soon',
        'page': 'pages/2_ASC_842_Leases.py'
    },
    'ASC 815': {
        'name': 'Derivatives and Hedging',
        'description': 'Analyze derivative instruments and hedging activities for proper classification and measurement.',
        'status': 'coming_soon',
        'page': 'pages/3_ASC_815_Derivatives.py'
    },
    'ASC 326': {
        'name': 'Credit Losses',
        'description': 'Implement current expected credit loss (CECL) model for financial instruments.',
        'status': 'coming_soon',
        'page': 'pages/4_ASC_326_Credit_Losses.py'
    }
}

# Generate cards HTML
cards_html = '<div class="expertise-grid">'

for code, info in standards.items():
    if info['status'] == 'available':
        cards_html += f"""
        <div class="expertise-card" onclick="window.open('/{info['page'].replace('pages/', '').replace('.py', '')}', '_self')">
            <h3>{info['name']} ({code})</h3>
            <p>{info['description']}</p>
            <span class="status-badge status-available">Available Now</span>
        </div>
        """
    else:
        cards_html += f"""
        <div class="expertise-card-disabled">
            <h3>{info['name']} ({code})</h3>
            <p>{info['description']}</p>
            <span class="status-badge status-coming-soon">Coming Soon</span>
        </div>
        """

cards_html += '</div>'

st.markdown(cards_html, unsafe_allow_html=True)

# Quick Stats Section
st.markdown("---")
st.markdown("### Platform Statistics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Active Standards", "1", "ASC 606")

with col2:
    st.metric("Analysis Quality", "Big 4", "Professional Grade")

with col3:
    st.metric("Knowledge Base", "1,510", "Authoritative Chunks")

with col4:
    st.metric("Response Time", "~30s", "Average Analysis")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; margin-top: 2rem;">
    <p>Built with advanced AI and authoritative accounting guidance</p>
    <p><strong>Version 2.0.0</strong> | Multi-Standard Platform</p>
</div>
""", unsafe_allow_html=True)