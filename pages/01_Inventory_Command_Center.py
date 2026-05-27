import streamlit as st
import pandas as pd
from src.database import get_db_connection, load_dataframe_from_table
from src.styling import inject_custom_css
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
    "💡 **Operations Dashboard:** Displays aggregated KPI metrics, risk trends, "
    "and financial exposure for Meridian Retail Group. Select other pages from the sidebar to inspect items."
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
    
    # Merge SKU details into recommendations
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

    # 3. Display KPIs in Grid using native containers
    st.subheader("Core Health Metrics")
    
    row1_col1, row1_col2, row1_col3, row1_col4, row1_col5 = st.columns(5)
    with row1_col1:
        with st.container(border=True):
            st.metric(label="System Health Index", value=f"{health_score}%", help="Percentage of SKUs operating within healthy tolerances")
    with row1_col2:
        with st.container(border=True):
            st.metric(label="Stockout Exposure", value=f"${total_stockout_exposure:,.0f}", delta=f"{critical_skus + high_skus} SKUs at Risk", delta_color="inverse", help="Revenue at risk of lost sales due to near-term depletion")
    with row1_col3:
        with st.container(border=True):
            st.metric(label="Excess Capital Lockup", value=f"${total_excess_capital:,.0f}", help="Capital currently tied up in overstocked/non-moving items")
    with row1_col4:
        with st.container(border=True):
            st.metric(label="Open Replenishments", value=f"{actions_count} Actions", help="Number of purchase orders or expediting actions recommended immediately")
    with row1_col5:
        with st.container(border=True):
            st.metric(label="In-Transit PO Value", value=f"${open_po_value:,.0f}", delta=f"{len(df_po_open)} Open POs", help="Financial value of components and SKUs currently on-order")

    st.subheader("Operational Context")
    row2_col1, row2_col2, row2_col3, row2_col4 = st.columns(4)
    with row2_col1:
        with st.container(border=True):
            st.metric(label="Monitored SKUs", value=f"{total_skus}")
    with row2_col2:
        with st.container(border=True):
            st.metric(label="Critical Risk SKUs", value=f"{critical_skus}", delta="Immediate action", delta_color="inverse")
    with row2_col3:
        with st.container(border=True):
            st.metric(label="Avg Target Service Level", value=f"{avg_service_level:.1f}%")
    with row2_col4:
        with st.container(border=True):
            st.metric(label="Supplier Network Risk", value=f"{avg_supplier_risk:.1f}/100", help="Average risk score across active suppliers")

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
