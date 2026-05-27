import streamlit as st
import pandas as pd
from src.database import load_dataframe_from_table
from src.styling import inject_custom_css
from src.charts import plot_supplier_risk_matrix, plot_supplier_otd_bar
from src.ai_assistant import summarize_supplier_risk_ai

# Page Setup
st.set_page_config(
    page_title="Supplier Reliability Center - SupplyPilot AI",
    page_icon="🚚",
    layout="wide"
)

inject_custom_css()

# Sidebar
st.sidebar.image("https://img.icons8.com/nolan/96/airplane-take-off.png", width=60)
st.sidebar.title("SupplyPilot AI")
st.sidebar.subheader("Supplier Reliability Center")
st.sidebar.markdown("---")

api_key = st.sidebar.text_input("OpenAI API Key (Optional)", type="password", help="Input your key to enable GPT-4 powered supplier briefings. Leaving it blank triggers template NLG fallbacks.")

# 1. Load active data
@st.cache_data(ttl=60)
def load_supplier_dashboard_data():
    df_supplier = load_dataframe_from_table('supplier_master')
    df_sku = load_dataframe_from_table('sku_master')
    df_po = load_dataframe_from_table('purchase_orders')
    return df_supplier, df_sku, df_po

df_supplier, df_sku, df_po = load_supplier_dashboard_data()

st.title("Supplier Reliability Center")
st.markdown("### Supplier Network Risk & Logistics Scorecards")

if df_supplier.empty:
    st.warning("⚠️ No supplier records found in database. Initialize the database on the **Data Upload & Templates** page.")
else:
    # 2. Calculate KPIs
    avg_risk = df_supplier['risk_score'].mean()
    otd_breaches = len(df_supplier[df_supplier['on_time_delivery_rate'] < 0.95])
    
    today_str = pd.Timestamp.now().strftime('%Y-%m-%d')
    delayed_pos = df_po[(df_po['status'].isin(['Open', 'In Transit'])) & (df_po['expected_arrival_date'] < today_str)]
    delayed_po_count = len(delayed_pos)
    
    single_source_sups = df_supplier[df_supplier['single_source_flag'] == 1]['supplier_id'].tolist()
    single_source_skus_count = len(df_sku[df_sku['supplier_id'].isin(single_source_sups)])
    
    high_risk_sups = df_supplier[df_supplier['risk_score'] > 60]['supplier_id'].tolist()
    risky_skus_count = len(df_sku[df_sku['supplier_id'].isin(high_risk_sups)])

    # Display KPI Cards using native components
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        with st.container(border=True):
            st.metric(label="Avg Supplier Risk", value=f"{avg_risk:.1f}/100", help="Average risk score across active suppliers")
    with col2:
        with st.container(border=True):
            st.metric(label="OTD Breaches (<95%)", value=f"{otd_breaches} Vendors", delta_color="inverse")
    with col3:
        with st.container(border=True):
            st.metric(label="Delayed PO Count", value=f"{delayed_po_count} Orders", delta_color="inverse")
    with col4:
        with st.container(border=True):
            st.metric(label="Single-Source SKUs", value=f"{single_source_skus_count} SKUs")
    with col5:
        with st.container(border=True):
            st.metric(label="High Risk Tied SKUs", value=f"{risky_skus_count} SKUs", delta_color="inverse")

    st.markdown("---")

    # 3. Visual Charts
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        fig_matrix = plot_supplier_risk_matrix(df_supplier)
        st.plotly_chart(fig_matrix, use_container_width=True)
    with col_c2:
        fig_otd = plot_supplier_otd_bar(df_supplier)
        st.plotly_chart(fig_otd, use_container_width=True)

    st.markdown("---")

    # 4. Supplier Matrix Table
    st.subheader("📋 Supplier Master Assessment Matrix")
    
    df_supplier_display = df_supplier.copy()
    df_supplier_display['single_source_flag'] = df_supplier_display['single_source_flag'].map({1: '⚠️ Yes', 0: 'No'})
    
    st.dataframe(
        df_supplier_display[[
            'supplier_id', 'supplier_name', 'state', 'region', 'product_specialty', 
            'avg_lead_time_days', 'lead_time_std_days', 'on_time_delivery_rate', 
            'fill_rate', 'defect_rate', 'risk_score', 'single_source_flag', 'payment_terms'
        ]].style.format({
            'avg_lead_time_days': '{:.1f}d',
            'lead_time_std_days': '±{:.1f}d',
            'on_time_delivery_rate': '{:.1%}',
            'fill_rate': '{:.1%}',
            'defect_rate': '{:.3%}',
            'risk_score': '{:.0f}'
        }),
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    # 5. AI Supplier Risk Auditor
    st.subheader("🤖 AI Supplier Risk Auditor")
    st.write("Generate a brief strategic evaluation of lead-time delays, quality rates, and bottlenecks across the supplier network.")
    
    btn_sup_ai = st.button("📊 Run Supplier Network Risk Audit")
    if btn_sup_ai:
        with st.spinner("Analyzing supplier scorecards and delivery patterns..."):
            summary_text = summarize_supplier_risk_ai(df_supplier, df_sku, df_po, api_key=api_key)
            st.markdown(
                f"""
                <div style="border-left: 4px solid #8b5cf6; background-color: #111827; padding: 18px; border-radius: 6px;">
                    {summary_text}
                </div>
                """,
                unsafe_allow_html=True
            )
