import streamlit as st
import os
from src.database import init_db, is_db_empty
from src.data_generator import generate_all_demo_data
from src.recommendations import generate_recommendations
from src.styling import inject_custom_css

# Page Configuration
st.set_page_config(
    page_title="SupplyPilot AI - Enterprise Inventory Orchestration",
    page_icon="🛫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Startup DB Initialization
init_db()
if is_db_empty():
    with st.spinner("Initializing system database and generating demo data for Meridian Retail Group..."):
        generate_all_demo_data()
        generate_recommendations()

# Inject SaaS Styling
inject_custom_css()

# Sidebar Setup
st.sidebar.image("https://img.icons8.com/nolan/96/airplane-take-off.png", width=80)
st.sidebar.title("SupplyPilot AI")
st.sidebar.markdown(
    """
    **Platform Control Center**
    *Version 1.4.0 (Enterprise)*
    """
)
st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **Demo Mode Enabled:** Currently showing sample planning data for *Meridian Retail Group*. "
    "Go to the **Data Upload & Templates** page to upload your own files."
)

# Landing Page Content
st.markdown('<div class="hero-title">SupplyPilot <span class="hero-gradient-text">AI</span></div>', unsafe_allow_html=True)
st.markdown('<div class="hero-desc">Predict stockouts, reduce excess inventory, and turn ERP/MRP data into automated replenishment decisions.</div>', unsafe_allow_html=True)

# Call to Action Buttons
col_btn1, col_btn2, _ = st.columns([1.5, 1.5, 5])
with col_btn1:
    if st.button("🚀 Open Planning Workspace", use_container_width=True):
        st.switch_page("pages/01_Inventory_Command_Center.py")
with col_btn2:
    if st.button("📤 Upload Your Own Data", use_container_width=True):
        st.switch_page("pages/08_Data_Upload_Templates.py")

st.markdown("---")

# Feature Highlights / Value Propositions
st.subheader("Enterprise-Grade Supply Chain Capabilities")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        """
        <div class="saas-card" style="min-height: 250px;">
            <h4 style="color:#58a6ff; margin-bottom:12px;">📊 SKU Risk Intelligence</h4>
            <p style="color:#8b949e; font-size:0.95rem; line-height:1.5;">
                Analyze inventory health with multi-factor risk scoring (0-100). Balances days of cover, supplier delivery variance, 
                ABC/XYZ consumption value, and historical volatility to surface critical stockouts before they impact sales.
            </p>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    st.markdown(
        """
        <div class="saas-card" style="min-height: 250px;">
            <h4 style="color:#ffa657; margin-bottom:12px;">⚙️ E-Commerce MRP & BOM logic</h4>
            <p style="color:#8b949e; font-size:0.95rem; line-height:1.5;">
                Resolve bundle and kit constraints dynamically. Tracks component-level inventory limits, calculates 
                maximum buildable units for promotional kits, and generates precise subcomponent replenishment orders.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        """
        <div class="saas-card" style="min-height: 250px;">
            <h4 style="color:#56d364; margin-bottom:12px;">📈 Demand Forecasting Lab</h4>
            <p style="color:#8b949e; font-size:0.95rem; line-height:1.5;">
                Compare quantitative modeling algorithms: Simple Moving Average, Weighted Moving Average, and Exponential Smoothing. 
                Applies seasonal smoothing factors to generate 12-week projections and evaluates models using historical MAPE metrics.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown(
        """
        <div class="saas-card" style="min-height: 250px;">
            <h4 style="color:#bc8cff; margin-bottom:12px;">🎭 Scenario Planning Studio</h4>
            <p style="color:#8b949e; font-size:0.95rem; line-height:1.5;">
                Simulate supply chain shocks in a sandbox environment. Adjust demand surges, supplier transit delays, and target 
                service levels to instantly calculate the capital and stockout exposure impact across all 500 SKUs.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

with col3:
    st.markdown(
        """
        <div class="saas-card" style="min-height: 250px;">
            <h4 style="color:#ff7b72; margin-bottom:12px;">🚚 Supplier Reliability Scorecard</h4>
            <p style="color:#8b949e; font-size:0.95rem; line-height:1.5;">
                Evaluate vendor performance based on lead-time deviation, defect rates, and on-time delivery (OTD). 
                Safety stocks are dynamically scaled upwards for high-risk, single-source, or volatile suppliers.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown(
        """
        <div class="saas-card" style="min-height: 250px;">
            <h4 style="color:#bc8cff; margin-bottom:12px;">🤖 On-Demand AI Copilot</h4>
            <p style="color:#8b949e; font-size:0.95rem; line-height:1.5;">
                Run on-demand AI explanations for critical items. Generates action plans, summarizes vendor risks, drafts supplier 
                emails, and explains MRP constraints without expensive, auto-loading calls.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("---")
st.caption("SupplyPilot AI is a professional supply chain portfolio project demonstrating inventory science, database engineering, and product design principles.")
