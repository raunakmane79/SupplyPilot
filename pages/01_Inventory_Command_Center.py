import streamlit as st
import pandas as pd
from src.database import get_db_connection, load_dataframe_from_table
from src.styling import inject_custom_css, create_kpi_card
from src.charts import (
    plot_inventory_health_donut, 
    plot_stockout_exposure_bar, 
    plot_excess_inventory_bar,
    plot_risk_trend
)

# Page Setup
st.set_page_config(
    page_title="Inventory Command Center - SupplyPilot AI",
    page_icon="📊",
    layout="wide"
)

inject_custom_css()

# Sidebar
st.sidebar.image("https://img.icons8.com/nolan/96/airplane-take-off.png", width=60)
st.sidebar.title("SupplyPilot AI")
st.sidebar.subheader("Inventory Command Center")
st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **Operations Dashboard:** This screen displays aggregated KPI metrics, risk trends, "
    "and financial exposure for Meridian Retail Group. Select other pages from the sidebar to dive deeper."
)

# Title
st.title("Inventory Command Center")
st.markdown("### Executive & Operations Overview")

# 1. Load active data
@st.cache_data(ttl=60)
def load_dashboard_data():
    df_recs = load_dataframe_from_table('recommendation_output')
    df_sku = load_dataframe_from_table('sku_master')
    df_supplier = load_dataframe_from_table('supplier_master')
    df_po = load_dataframe_from_table('purchase_orders')
    
    # Merge SKU cost and category details into recommendations
    if not df_recs.empty and not df_sku.empty:
        df_merged = df_recs.merge(
            df_sku[['sku_id', 'sku_name', 'category', 'unit_cost', 'selling_price', 'service_level_target']], 
            on='sku_id', 
            how='inner'
        )
        return df_merged, df_supplier, df_po
    return pd.DataFrame(), df_supplier, df_po

df_recs_merged, df_supplier, df_po = load_dashboard_data()

if df_recs_merged.empty:
    st.warning("⚠️ No planning data found in the local database. Please go to **Data Upload & Templates** to initialize the database.")
else:
    # 2. Calculate KPI Metrics
    total_skus = df_recs_merged['sku_id'].nunique()
    critical_skus = len(df_recs_merged[df_recs_merged['risk_level'] == 'Critical'])
    high_skus = len(df_recs_merged[df_recs_merged['risk_level'] == 'High'])
    
    total_stockout_exposure = df_recs_merged['estimated_stockout_value'].sum()
    total_excess_capital = df_recs_merged['excess_inventory_value'].sum()
    
    # Health score = % of SKUs not in Critical/High risk
    health_score = int(100 - ((critical_skus + high_skus) / total_skus * 100))
    health_score = min(max(health_score, 0), 100)
    
    avg_service_level = df_recs_merged['service_level_target'].mean() * 100.0
    
    # Open PO value calculation (open/in transit orders * sku unit cost)
    df_po_open = df_po[df_po['status'].isin(['Open', 'In Transit'])]
    df_po_open_merged = df_po_open.merge(df_recs_merged[['sku_id', 'unit_cost']], on='sku_id', how='inner')
    open_po_value = (df_po_open_merged['order_qty'] * df_po_open_merged['unit_cost']).sum()
    
    avg_supplier_risk = df_supplier['risk_score'].mean()
    
    actions_count = len(df_recs_merged[df_recs_merged['suggested_action'].isin(['Place Order', 'Expedite PO'])])

    # 3. Display KPIs in Grid (Two rows of cards)
    st.markdown("#### Primary Health Indicators")
    row1_col1, row1_col2, row1_col3, row1_col4, row1_col5 = st.columns(5)
    
    with row1_col1:
        st.markdown(create_kpi_card("System Health Index", f"{health_score}%", "Normal", "neutral", "Percentage of SKUs operating within healthy tolerances"), unsafe_allow_html=True)
    with row1_col2:
        st.markdown(create_kpi_card("Active Stockout Exposure", f"${total_stockout_exposure:,.2f}", f"{critical_skus + high_skus} SKUs at Risk", "down", "Revenue at risk of lost sales due to near-term depletion"), unsafe_allow_html=True)
    with row1_col3:
        st.markdown(create_kpi_card("Excess Inventory Value", f"${total_excess_capital:,.2f}", "Working Capital Lock", "neutral", "Capital currently tied up in overstocked/non-moving items"), unsafe_allow_html=True)
    with row1_col4:
        st.markdown(create_kpi_card("Active Replenishments", f"{actions_count} Actions", "Due This Week", "up", "Number of purchase orders or expediting actions recommended immediately"), unsafe_allow_html=True)
    with row1_col5:
        st.markdown(create_kpi_card("In-Transit PO Capital", f"${open_po_value:,.2f}", f"{len(df_po_open)} Open Orders", "neutral", "Financial value of components and SKUs currently on-order"), unsafe_allow_html=True)

    st.markdown("#### Operational Diagnostics")
    row2_col1, row2_col2, row2_col3, row2_col4 = st.columns(4)
    with row2_col1:
        st.markdown(create_kpi_card("Total Monitored SKUs", f"{total_skus}", "Active Portfolio", "neutral", "Total unique items tracked across warehouses"), unsafe_allow_html=True)
    with row2_col2:
        st.markdown(create_kpi_card("Critical Risk SKU Count", f"{critical_skus}", "Requires Action", "down", "SKUs that will stockout before replenishment can arrive"), unsafe_allow_html=True)
    with row2_col3:
        st.markdown(create_kpi_card("Average Target Service Level", f"{avg_service_level:.1f}%", "Target Compliance", "neutral", "Weighted service level commitment to customers"), unsafe_allow_html=True)
    with row2_col4:
        st.markdown(create_kpi_card("Supplier Network Risk Score", f"{avg_supplier_risk:.1f}/100", "Moderate", "neutral", "Average risk score across active suppliers"), unsafe_allow_html=True)

    st.markdown("---")

    # 4. Charts Section
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        fig_donut = plot_inventory_health_donut(df_recs_merged)
        st.plotly_chart(fig_donut, use_container_width=True)
        
    with col_chart2:
        fig_exposure = plot_stockout_exposure_bar(df_recs_merged)
        st.plotly_chart(fig_exposure, use_container_width=True)
        
    col_chart3, col_chart4 = st.columns(2)
    
    with col_chart3:
        fig_excess = plot_excess_inventory_bar(df_recs_merged)
        st.plotly_chart(fig_excess, use_container_width=True)
        
    with col_chart4:
        fig_trend = plot_risk_trend()
        st.plotly_chart(fig_trend, use_container_width=True)

    st.markdown("---")

    # 5. Top 10 lists
    col_table1, col_table2 = st.columns(2)
    
    with col_table1:
        st.subheader("Top 10 Stockout Exposures")
        risky_table = df_recs_merged[df_recs_merged['estimated_stockout_value'] > 0].sort_values(
            by='estimated_stockout_value', ascending=False
        ).head(10)[['sku_id', 'sku_name', 'category', 'warehouse_id', 'days_of_cover', 'estimated_stockout_value']]
        
        st.dataframe(
            risky_table.style.format({'days_of_cover': '{:.1f}', 'estimated_stockout_value': '${:,.2f}'}),
            use_container_width=True,
            hide_index=True
        )
        
    with col_table2:
        st.subheader("Top 10 Overstocked Inventory Capital")
        excess_table = df_recs_merged[df_recs_merged['excess_inventory_value'] > 0].sort_values(
            by='excess_inventory_value', ascending=False
        ).head(10)[['sku_id', 'sku_name', 'category', 'warehouse_id', 'days_of_cover', 'excess_inventory_value']]
        
        st.dataframe(
            excess_table.style.format({'days_of_cover': '{:.1f}', 'excess_inventory_value': '${:,.2f}'}),
            use_container_width=True,
            hide_index=True
        )
