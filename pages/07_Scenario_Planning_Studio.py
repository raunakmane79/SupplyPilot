import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from src.database import load_dataframe_from_table
from src.styling import inject_custom_css
from src.calculations import compute_inventory_parameters
from src.risk_scoring import calculate_stockout_risk_score, classify_risk_level, compute_excess_inventory
from src.charts import apply_chart_theme

# Page Setup
st.set_page_config(
    page_title="Scenario Planning Studio - SupplyPilot AI",
    page_icon="🎭",
    layout="wide"
)

inject_custom_css()

# Sidebar Setup
st.sidebar.image("https://img.icons8.com/nolan/96/airplane-take-off.png", width=60)
st.sidebar.title("SupplyPilot AI")
st.sidebar.subheader("Scenario Controls")
st.sidebar.markdown("---")

# Sliders for Simulation
sim_demand_increase = st.sidebar.slider(
    "Demand Increase / Spike (%)", 
    min_value=-50, 
    max_value=100, 
    value=0, 
    step=5,
    help="Simulates a uniform demand surge or drop across all sales channels."
)

sim_supplier_delay = st.sidebar.slider(
    "Supplier Lead-Time Delays (Days)", 
    min_value=0, 
    max_value=30, 
    value=0, 
    step=1,
    help="Adds delay days to default supplier transit lead times due to logistics constraints."
)

sim_service_level = st.sidebar.selectbox(
    "Target Service Level Overrides", 
    ["No Override", "90%", "95%", "98%", "99%"],
    help="Overrides SKU target service levels, recalculating required safety stocks."
)

# Convert service level string to float
service_level_map = {
    "90%": 0.90,
    "95%": 0.95,
    "98%": 0.98,
    "99%": 0.99
}
target_sl_override = service_level_map.get(sim_service_level, None)

st.title("Scenario Planning Studio")
st.markdown("### Interactive 'What-If' Supply Chain Sandbox")

# 1. Load active data
@st.cache_data(ttl=60)
def load_scenario_data():
    df_recs = load_dataframe_from_table('recommendation_output')
    df_sku = load_dataframe_from_table('sku_master')
    df_supplier = load_dataframe_from_table('supplier_master')
    df_po = load_dataframe_from_table('purchase_orders')
    df_inventory = load_dataframe_from_table('inventory_status')
    df_demand = load_dataframe_from_table('demand_history')
    return df_recs, df_sku, df_supplier, df_po, df_inventory, df_demand

df_recs, df_sku, df_supplier, df_po, df_inventory, df_demand = load_scenario_data()

if df_recs.empty or df_sku.empty:
    st.warning("⚠️ Database is empty. Please initialize it on the **Data Upload & Templates** page.")
else:
    # 2. Compute Baseline Stats
    baseline_critical = len(df_recs[df_recs['risk_level'] == 'Critical'])
    baseline_high = len(df_recs[df_recs['risk_level'] == 'High'])
    baseline_stockout_val = df_recs['estimated_stockout_value'].sum()
    
    # Calculate baseline capital needed by category
    df_sku_costs = df_sku[['sku_id', 'unit_cost', 'category']]
    df_recs_cost = df_recs.merge(df_sku_costs, on='sku_id', how='left')
    df_recs_cost['baseline_cost'] = df_recs_cost['suggested_order_qty'] * df_recs_cost['unit_cost']
    baseline_capital = df_recs_cost['baseline_cost'].sum()
    baseline_excess = df_recs['excess_inventory_value'].sum()

    # 3. Compute Simulated Scenario in Memory
    with st.spinner("Simulating scenario parameters across 500 SKUs..."):
        df_sim = compute_inventory_parameters(
            df_sku, df_inventory, df_demand, df_po, df_supplier,
            demand_increase_pct=sim_demand_increase,
            supplier_delay_days=sim_supplier_delay,
            target_sl_override=target_sl_override
        )
        
        # Calculate Risk and Excess
        df_sim['risk_score_calc'] = df_sim.apply(calculate_stockout_risk_score, axis=1)
        df_sim['risk_level'] = df_sim['risk_score_calc'].apply(classify_risk_level)
        
        excess_results = df_sim.apply(compute_excess_inventory, axis=1)
        df_sim['excess_qty'] = [r[0] for r in excess_results]
        df_sim['excess_inventory_value'] = [r[1] for r in excess_results]
        
        # Stockout exposure
        def compute_stockout_exposure_sim(row):
            lt = row['lead_time_adjusted']
            doc = row['days_of_cover']
            if doc < lt and row['add_90'] > 0:
                days_short = max(lt - max(doc, 0.0), 0.0)
                return round(days_short * row['add_90'] * row['selling_price'], 2)
            return 0.0
            
        df_sim['estimated_stockout_value'] = df_sim.apply(compute_stockout_exposure_sim, axis=1)
        df_sim['financial_impact'] = df_sim['suggested_order_qty'] * df_sim['unit_cost']
        
        # Scenario stats
        sim_critical = len(df_sim[df_sim['risk_level'] == 'Critical'])
        sim_high = len(df_sim[df_sim['risk_level'] == 'High'])
        sim_stockout_val = df_sim['estimated_stockout_value'].sum()
        sim_capital = df_sim['financial_impact'].sum()
        sim_excess = df_sim['excess_inventory_value'].sum()

    # 4. Show KPI Deltas using native elements
    crit_delta = sim_critical - baseline_critical
    stockout_delta = sim_stockout_val - baseline_stockout_val
    capital_delta = sim_capital - baseline_capital
    excess_delta = sim_excess - baseline_excess
    
    st.subheader("Scenario Delta Scorecard")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        with st.container(border=True):
            st.metric(
                label="Simulated Critical SKUs", 
                value=f"{sim_critical} SKUs", 
                delta=f"{crit_delta} vs Baseline", 
                delta_color="inverse"
            )
    with col2:
        with st.container(border=True):
            st.metric(
                label="Simulated Stockout Exposure", 
                value=f"${sim_stockout_val:,.0f}", 
                delta=f"${stockout_delta:,.0f} vs Baseline", 
                delta_color="inverse"
            )
    with col3:
        with st.container(border=True):
            st.metric(
                label="Required Order Capital", 
                value=f"${sim_capital:,.0f}", 
                delta=f"${capital_delta:,.0f} vs Baseline"
            )
    with col4:
        with st.container(border=True):
            st.metric(
                label="Simulated Excess Capital", 
                value=f"${sim_excess:,.0f}", 
                delta=f"${excess_delta:,.0f} vs Baseline", 
                delta_color="inverse"
            )

    st.markdown("---")

    # 5. Narrative Explanation of what happened
    st.subheader("📝 Scenario Analysis Report")
    narrative = ""
    if sim_demand_increase > 0:
        narrative += f"- **Demand Surge:** A **{sim_demand_increase}%** demand surge has increased consumption rates across the portfolio. "
    elif sim_demand_increase < 0:
        narrative += f"- **Demand Drop:** A **{abs(sim_demand_increase)}%** demand drop has slowed consumption rates across the portfolio. "
        
    if sim_supplier_delay > 0:
        narrative += f"Combined with **{sim_supplier_delay} days** of logistics transit delays, "
        
    narrative += f"this scenario shifts **{sim_critical + sim_high} SKUs** into Critical/High risk categories. "
    
    if stockout_delta > 0:
        narrative += f"Projected revenue exposure increases by **${stockout_delta:,.2f}**, representing potential missed omnichannel sales. "
    elif stockout_delta < 0:
        narrative += f"Projected revenue exposure decreases by **${abs(stockout_delta):,.2f}** due to slower sales velocity. "
        
    if capital_delta > 0:
        narrative += f"To maintain the service levels, procurement must allocate an additional **${capital_delta:,.2f}** in order capital to satisfy supplier MOQs and rounded case packs."
    elif capital_delta < 0:
        narrative += f"Reflecting the demand drop, immediate order commitments can be reduced by **${abs(capital_delta):,.2f}**."

    st.info(narrative if narrative else "Adjust sliders in the sidebar to simulate market forces and supplier shocks.")

    st.markdown("---")

    # 6. Side-by-Side Comparative Graph
    st.subheader("📊 Capital Requirements by Category: Baseline vs. Scenario")
    
    # Aggregate baseline and simulated capital by category
    df_base_cat = df_recs_cost.groupby('category')['baseline_cost'].sum().reset_index()
    df_sim_cat = df_sim.groupby('category')['financial_impact'].sum().reset_index()
    
    df_chart_data = df_base_cat.merge(df_sim_cat, on='category', how='outer').fillna(0.0)
    df_chart_data.columns = ['Category', 'Baseline Capital ($)', 'Scenario Capital ($)']
    
    # Melt for side-by-side grouping
    df_melted = pd.melt(df_chart_data, id_vars=['Category'], value_vars=['Baseline Capital ($)', 'Scenario Capital ($)'],
                        var_name='Scenario Type', value_name='Capital ($)')
    
    fig_comp = px.bar(
        df_melted,
        x='Category',
        y='Capital ($)',
        color='Scenario Type',
        barmode='group',
        color_discrete_sequence=['#475569', '#2563eb'], # gray and blue
        title="BOM Purchase Capital Comparison by Product Category"
    )
    apply_chart_theme(fig_comp)
    st.plotly_chart(fig_comp, use_container_width=True)

    st.markdown("---")

    # 7. Top 10 Most Affected SKUs Table
    st.subheader("📋 Top 10 SKUs Most Affected by This Scenario")
    st.caption("Shows SKUs with the largest change in Suggested Order Quantity under the active simulation.")
    
    df_baseline_suggested = df_recs[['sku_id', 'warehouse_id', 'suggested_order_qty']].rename(
        columns={'suggested_order_qty': 'baseline_suggested'}
    )
    df_compare = df_sim.merge(df_baseline_suggested, on=['sku_id', 'warehouse_id'], how='inner')
    df_compare['qty_change'] = df_compare['suggested_order_qty'] - df_compare['baseline_suggested']
    df_compare['qty_change_abs'] = df_compare['qty_change'].abs()
    
    df_affected = df_compare.sort_values(by='qty_change_abs', ascending=False).head(10)
    
    if df_affected.empty:
        st.info("No changes in order quantities detected under this scenario.")
    else:
        df_affected_display = df_affected[[
            'sku_id', 'sku_name', 'warehouse_id', 'category', 'baseline_suggested', 
            'suggested_order_qty', 'qty_change', 'financial_impact'
        ]].copy()
        
        df_affected_display.columns = [
            'SKU', 'Description', 'WH', 'Category', 'Baseline Order (Qty)', 
            'Scenario Order (Qty)', 'Order Qty Change', 'Simulated Cost'
        ]
        
        st.dataframe(
            df_affected_display.style.format({
                'Baseline Order (Qty)': '{:,}',
                'Scenario Order (Qty)': '{:,}',
                'Order Qty Change': '{:+,}',
                'Simulated Cost': '${:,.2f}'
            }),
            use_container_width=True,
            hide_index=True
        )
