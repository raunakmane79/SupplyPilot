import streamlit as st
import pandas as pd
from src.database import get_db_connection, load_dataframe_from_table
from src.styling import inject_custom_css
from src.calculations import compute_inventory_parameters
from src.risk_scoring import calculate_stockout_risk_score, classify_risk_level
from src.charts import plot_historical_demand, plot_actual_vs_forecast
from src.forecasting import generate_forecasts
from src.ai_assistant import explain_sku_risk_ai
from src.recommendations import generate_recommendations

# Page Setup
st.set_page_config(
    page_title="SKU Risk Intelligence - SupplyPilot AI",
    page_icon="🔍",
    layout="wide"
)

inject_custom_css()

# Sidebar
st.sidebar.image("https://img.icons8.com/nolan/96/airplane-take-off.png", width=60)
st.sidebar.title("SupplyPilot AI")
st.sidebar.subheader("SKU Risk Intelligence")
st.sidebar.markdown("---")

# Optional API Key input
api_key = st.sidebar.text_input("OpenAI API Key (Optional)", type="password", help="Input your key to enable GPT-4 powered risk explanations. Leaving it blank triggers template NLG fallbacks.")

# Load active data
@st.cache_data(ttl=60)
def load_sku_intelligence_data():
    df_recs = load_dataframe_from_table('recommendation_output')
    df_sku = load_dataframe_from_table('sku_master')
    df_supplier = load_dataframe_from_table('supplier_master')
    df_po = load_dataframe_from_table('purchase_orders')
    df_inventory = load_dataframe_from_table('inventory_status')
    
    if df_recs.empty or df_sku.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
    df_merged = df_recs.merge(
        df_sku[['sku_id', 'sku_name', 'category', 'product_family', 'unit_cost', 'selling_price', 'moq', 'case_pack_qty', 'service_level_target', 'default_lead_time_days', 'criticality', 'lifecycle_status', 'seasonal_flag']], 
        on='sku_id', 
        how='inner'
    )
    df_merged = df_merged.merge(
        df_supplier[['supplier_id', 'supplier_name', 'avg_lead_time_days', 'lead_time_std_days', 'on_time_delivery_rate', 'fill_rate', 'risk_score', 'single_source_flag', 'payment_terms']], 
        on='supplier_id', 
        how='left'
    )
    
    df_inventory_details = df_inventory.merge(df_merged, on=['sku_id', 'warehouse_id'], how='inner')
    
    return df_inventory_details, df_supplier, df_po, df_recs

df_sku_details, df_supplier, df_po, df_recs_raw = load_sku_intelligence_data()

st.title("SKU Risk Intelligence")
st.markdown("### Interactive SKU Risk Audit & Inspection Workbench")

if df_sku_details.empty:
    st.warning("⚠️ No active planning data found. Initialize the database first on the **Data Upload & Templates** page.")
else:
    # 1. Multi-factor Filtering Panel
    with st.expander("🔍 Filter SKU Intelligence Matrix", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        
        categories = ["All"] + sorted(df_sku_details['category'].dropna().unique().tolist())
        warehouses = ["All"] + sorted(df_sku_details['warehouse_id'].dropna().unique().tolist())
        suppliers = ["All"] + sorted(df_sku_details['supplier_name'].dropna().unique().tolist())
        risk_levels = ["All", "Critical", "High", "Medium", "Low", "Healthy"]
        
        with col1:
            sel_cat = st.selectbox("Category", categories)
            sel_wh = st.selectbox("Fulfillment Center", warehouses)
        with col2:
            sel_sup = st.selectbox("Primary Supplier", suppliers)
            sel_risk = st.selectbox("Risk Level Threshold", risk_levels)
        with col3:
            abc_classes = ["All"] + sorted(df_sku_details['abc_class'].dropna().unique().tolist())
            xyz_classes = ["All"] + sorted(df_sku_details['xyz_class'].dropna().unique().tolist())
            sel_abc = st.selectbox("ABC Classification", abc_classes)
            sel_xyz = st.selectbox("XYZ Classification (Variability)", xyz_classes)
        with col4:
            lifecycles = ["All"] + sorted(df_sku_details['lifecycle_status'].dropna().unique().tolist())
            seasonal = st.selectbox("Seasonal SKU Profile", ["All", "Seasonal Only", "Non-Seasonal Only"])
            sel_life = st.selectbox("Product Lifecycle Status", lifecycles)

    # Filter operations
    df_filtered = df_sku_details.copy()
    if sel_cat != "All":
        df_filtered = df_filtered[df_filtered['category'] == sel_cat]
    if sel_wh != "All":
        df_filtered = df_filtered[df_filtered['warehouse_id'] == sel_wh]
    if sel_sup != "All":
        df_filtered = df_filtered[df_filtered['supplier_name'] == sel_sup]
    if sel_risk != "All":
        df_filtered = df_filtered[df_filtered['risk_level'] == sel_risk]
    if sel_abc != "All":
        df_filtered = df_filtered[df_filtered['abc_class'] == sel_abc]
    if sel_xyz != "All":
        df_filtered = df_filtered[df_filtered['xyz_class'] == sel_xyz]
    if sel_life != "All":
        df_filtered = df_filtered[df_filtered['lifecycle_status'] == sel_life]
    if seasonal == "Seasonal Only":
        df_filtered = df_filtered[df_filtered['seasonal_flag'] == 1]
    elif seasonal == "Non-Seasonal Only":
        df_filtered = df_filtered[df_filtered['seasonal_flag'] == 0]

    # Search Bar
    search_query = st.text_input("🔍 Quick Search by SKU ID or SKU Name", "").strip()
    if search_query:
        df_filtered = df_filtered[
            df_filtered['sku_id'].str.contains(search_query, case=False) | 
            df_filtered['sku_name'].str.contains(search_query, case=False)
        ]

    # Display SKU Matrix
    st.markdown(f"**Filtered Results:** Showing `{len(df_filtered)}` SKU-Warehouse intersections.")
    
    df_table = df_filtered[[
        'sku_id', 'sku_name', 'warehouse_id', 'supplier_name', 'on_hand_qty', 
        'inventory_position', 'days_of_cover', 'reorder_point', 'suggested_order_qty', 
        'risk_level', 'estimated_stockout_value', 'suggested_action'
    ]].copy()
    
    st.dataframe(
        df_table.style.format({
            'on_hand_qty': '{:,}',
            'inventory_position': '{:,}',
            'days_of_cover': '{:.1f}',
            'reorder_point': '{:,.1f}',
            'suggested_order_qty': '{:,}',
            'estimated_stockout_value': '${:,.2f}'
        }),
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    # 2. SKU Detailed Inspector
    st.subheader("🕵️ Single SKU Deep-Dive Inspector")
    
    if df_filtered.empty:
        st.info("No SKUs match the current filters. Adjust your filters to inspect a SKU.")
    else:
        sku_options = df_filtered.apply(lambda r: f"{r['sku_id']} | {r['sku_name']} ({r['warehouse_id']})", axis=1).tolist()
        selected_option = st.selectbox("Select SKU-Warehouse to Inspect", sku_options)
        
        selected_idx = sku_options.index(selected_option)
        sku_record = df_filtered.iloc[selected_idx]
        
        selected_sku_id = sku_record['sku_id']
        selected_wh_id = sku_record['warehouse_id']
        
        st.markdown(f"### Inspecting: **{sku_record['sku_name']}**")
        st.markdown(f"**SKU ID:** `{selected_sku_id}` | **Category:** `{sku_record['category']}` | **Fulfillment Center:** `{selected_wh_id}`")
        
        # Details layout (Tabs)
        tab_inv, tab_reorder, tab_supplier, tab_forecast, tab_ai, tab_edit = st.tabs([
            "📦 Stock & PO Summary", "⚙️ Reorder Logic", "🚚 Supplier Scorecard", "📈 Demand & Forecast Lab", "🤖 AI Risk Assistant", "✏️ Edit SKU Parameters"
        ])
        
        with tab_inv:
            col_inv1, col_inv2 = st.columns([2, 3])
            with col_inv1:
                st.markdown("#### Inventory Balance Sheet")
                st.write(f"**On Hand Quantity:** {sku_record['on_hand_qty']} units")
                st.write(f"**Allocated to Orders:** {sku_record['allocated_qty']} units")
                st.write(f"**Backorders outstanding:** {sku_record['backorder_qty']} units")
                st.write(f"**Active On-Order Quantity:** {sku_record['on_order_qty']} units")
                st.write(f"**Net Inventory Position:** {sku_record['inventory_position']} units")
                st.write(f"**Days of Cover:** {sku_record['days_of_cover']:.1f} days")
                st.write(f"**Last Sync Updated:** `{sku_record['last_updated']}`")
                
            with col_inv2:
                st.markdown("#### Active Purchase Orders")
                df_po_sku = df_po[
                    (df_po['sku_id'] == selected_sku_id) & 
                    (df_po['warehouse_id'] == selected_wh_id) & 
                    (df_po['status'].isin(['Open', 'In Transit']))
                ]
                if df_po_sku.empty:
                    st.info("No open or in-transit purchase orders are currently scheduled for this warehouse.")
                else:
                    st.dataframe(
                        df_po_sku[['po_id', 'order_date', 'expected_arrival_date', 'order_qty', 'status']],
                        use_container_width=True,
                        hide_index=True
                    )
                    
        with tab_reorder:
            col_re1, col_re2 = st.columns(2)
            with col_re1:
                st.markdown("#### Replenishment Thresholds")
                st.write(f"**Target Service Level:** {sku_record['service_level_target']*100:.0f}%")
                st.write(f"**Safety Stock Threshold:** {sku_record['safety_stock']:.1f} units")
                st.write(f"**Reorder Point (ROP):** {sku_record['reorder_point']:.1f} units")
                st.write(f"**Suggested Order Qty:** {sku_record['suggested_order_qty']} units")
                st.write(f"**Suggested Order Date:** `{sku_record['suggested_order_date']}`")
            with col_re2:
                st.markdown("#### Formula Constraints")
                st.write(f"**Supplier MOQ:** {sku_record['moq']} units")
                st.write(f"**Standard Case Pack Qty:** {sku_record['case_pack_qty']} units")
                st.write(f"**ABC Classification:** `{sku_record['abc_class']}`")
                st.write(f"**XYZ Demand Profile:** `{sku_record['xyz_class']}`")
                st.write(f"**Default Lead Time:** {sku_record['default_lead_time_days']} days")
                
        with tab_supplier:
            col_sup1, col_sup2 = st.columns(2)
            with col_sup1:
                st.markdown("#### Supplier Profile")
                st.write(f"**Partner Name:** {sku_record['supplier_name']}")
                st.write(f"**Specialization:** {sku_record['product_specialty']}")
                st.write(f"**Geographical Location:** {sku_record['state']} ({sku_record['region']})")
                st.write(f"**Single-Source Vendor:** {'⚠️ YES' if sku_record['single_source_flag'] == 1 else 'No'}")
            with col_sup2:
                st.markdown("#### Vendor Scorecard")
                st.write(f"**Average Lead Time:** {sku_record['avg_lead_time_days']:.1f} days")
                st.write(f"**Lead Time Std Dev (Volatility):** {sku_record['lead_time_std_days']:.1f} days")
                st.write(f"**On-Time Delivery (OTD) Rate:** {sku_record['on_time_delivery_rate']*100:.1f}%")
                st.write(f"**Fill Rate Average:** {sku_record['fill_rate']*100:.1f}%")
                st.write(f"**Defect Rate:** {sku_record['defect_rate']*100:.3f}%")
                st.write(f"**Reliability Score:** {sku_record['risk_score']}/100")
                
        with tab_forecast:
            df_demand_db = load_dataframe_from_table('demand_history')
            df_hist, df_fc, metrics = generate_forecasts(df_demand_db, selected_sku_id, selected_wh_id)
            
            if df_hist.empty:
                st.warning("No demand history found for this SKU in the database.")
            else:
                col_f1, col_f2 = st.columns([2, 1])
                with col_f1:
                    fig_fc = plot_actual_vs_forecast(df_hist, df_fc, selected_sku_id)
                    st.plotly_chart(fig_fc, use_container_width=True)
                with col_f2:
                    st.markdown("#### Forecast Models Accuracy")
                    if metrics:
                        st.markdown("**Historical Fitting Error (MAPE):**")
                        st.metric("Simple Moving Average", f"{metrics['moving_average']:.1f}% MAPE")
                        st.metric("Weighted Moving Average", f"{metrics['weighted_moving_average']:.1f}% MAPE")
                        st.metric("Exponential Smoothing", f"{metrics['exponential_smoothing']:.1f}% MAPE")
                    else:
                        st.info("Insufficient demand history to compute forecast accuracy metrics.")

        with tab_ai:
            st.markdown("#### SupplyPilot AI Risk Analysis")
            st.write("Calculates a natural language explanation of risk status, supplier safety buffers, and PO scheduling gap delays.")
            
            btn_ai = st.button("🤖 Generate AI SKU Risk Analysis")
            if btn_ai:
                with st.spinner("Analyzing parameters and generating SKU-level briefing..."):
                    df_po_active = df_po[
                        (df_po['sku_id'] == selected_sku_id) & 
                        (df_po['warehouse_id'] == selected_wh_id) & 
                        (df_po['status'].isin(['Open', 'In Transit']))
                    ]
                    analysis_text = explain_sku_risk_ai(sku_record, df_po_active, api_key=api_key)
                    
                    st.markdown(
                        f"""
                        <div style="border-left: 4px solid #3b82f6; background-color: #111827; padding: 18px; border-radius: 6px;">
                            {analysis_text}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    
        with tab_edit:
            st.markdown("#### Edit SKU Master Parameters")
            st.write("Modify planning constraints for this SKU. Saving will update the database and recalculate recommendations.")
            
            # Form to prevent multiple updates on single changes
            with st.form("edit_sku_form"):
                col_e1, col_e2 = st.columns(2)
                
                with col_e1:
                    edit_service_level = st.slider(
                        "Target Service Level Target", 
                        min_value=0.80, 
                        max_value=0.99, 
                        value=float(sku_record['service_level_target']), 
                        step=0.01,
                        format="%.2f"
                    )
                    edit_lead_time = st.number_input(
                        "Default Lead Time (Days)", 
                        min_value=1, 
                        max_value=180, 
                        value=int(sku_record['default_lead_time_days'])
                    )
                    edit_moq = st.number_input(
                        "Minimum Order Quantity (MOQ)", 
                        min_value=1, 
                        value=int(sku_record['moq'])
                    )
                    edit_case_pack = st.number_input(
                        "Case Pack Qty", 
                        min_value=1, 
                        value=int(sku_record['case_pack_qty']) if sku_record['case_pack_qty'] else 12
                    )
                    
                with col_e2:
                    edit_cost = st.number_input(
                        "Unit Cost ($)", 
                        min_value=0.1, 
                        value=float(sku_record['unit_cost']), 
                        format="%.2f"
                    )
                    edit_price = st.number_input(
                        "Selling Price ($)", 
                        min_value=0.1, 
                        value=float(sku_record['selling_price']), 
                        format="%.2f"
                    )
                    
                    status_list = ["Active", "Phase-out", "Discontinued", "Launch"]
                    current_status_idx = status_list.index(sku_record['lifecycle_status']) if sku_record['lifecycle_status'] in status_list else 0
                    edit_status = st.selectbox(
                        "Product Lifecycle Status", 
                        status_list, 
                        index=current_status_idx
                    )
                
                submit_edit = st.form_submit_button("💾 Save Parameters & Recalculate")
                
                if submit_edit:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE sku_master 
                        SET service_level_target = ?, default_lead_time_days = ?, moq = ?, 
                            case_pack_qty = ?, unit_cost = ?, selling_price = ?, lifecycle_status = ? 
                        WHERE sku_id = ?
                    """, (edit_service_level, edit_lead_time, edit_moq, edit_case_pack, edit_cost, edit_price, edit_status, selected_sku_id))
                    conn.commit()
                    conn.close()
                    
                    # Recalculate
                    generate_recommendations()
                    
                    # Reset cache
                    st.cache_data.clear()
                    st.success("SKU parameters updated and planning thresholds recalculated successfully!")
                    st.rerun()
