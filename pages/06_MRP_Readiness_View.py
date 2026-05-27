import streamlit as st
import pandas as pd
import numpy as np
from src.database import load_dataframe_from_table
from src.styling import inject_custom_css
from src.ai_assistant import explain_mrp_kit_constraints

# Page Setup
st.set_page_config(
    page_title="MRP Readiness View - SupplyPilot AI",
    page_icon="⚙️",
    layout="wide"
)

inject_custom_css()

# Sidebar
st.sidebar.image("https://img.icons8.com/nolan/96/airplane-take-off.png", width=60)
st.sidebar.title("SupplyPilot AI")
st.sidebar.subheader("MRP Readiness View")
st.sidebar.markdown("---")
st.sidebar.info(
    "⚙️ **MRP Readiness:** Analyze e-commerce bundles and kits. "
    "Identify component shortages, calculate maximum buildable kits, and generate replenishment targets."
)

st.title("MRP Readiness View")
st.markdown("### Bill of Materials (BOM) & Kit Assembly Planner")

# 1. Load active data
df_bom = load_dataframe_from_table('bom_or_kit_structure')
df_sku = load_dataframe_from_table('sku_master')
df_inventory = load_dataframe_from_table('inventory_status')

if df_bom.empty or df_sku.empty or df_inventory.empty:
    st.warning("⚠️ No BOM/Kit structures or inventory data found. Initialize the database on the **Data Upload & Templates** page.")
else:
    # Get parent kits list
    parent_ids = df_bom['parent_sku_id'].unique().tolist()
    parent_skus = df_sku[df_sku['sku_id'].isin(parent_ids)]
    
    if parent_skus.empty:
        st.info("No parent kits or bundles currently active in sku_master.")
    else:
        # 2. Select parent SKU
        kit_options = parent_skus.apply(lambda r: f"{r['sku_id']} | {r['sku_name']}", axis=1).tolist()
        selected_kit_option = st.selectbox("Select Parent Kit / Bundle to Audit", kit_options)
        
        selected_parent_id = selected_kit_option.split(" | ")[0]
        parent_row = parent_skus[parent_skus['sku_id'] == selected_parent_id].iloc[0]
        
        # 3. Load components for this parent
        kit_name = df_bom[df_bom['parent_sku_id'] == selected_parent_id]['kit_name'].iloc[0]
        
        df_kit_bom = df_bom[df_bom['parent_sku_id'] == selected_parent_id].copy()
        
        # Get component SKU details (names)
        df_kit_bom = df_kit_bom.merge(
            df_sku[['sku_id', 'sku_name', 'unit_cost', 'supplier_id']], 
            left_on='component_sku_id', 
            right_on='sku_id', 
            how='inner'
        )
        
        # Aggregate on-hand stock for components across all warehouses
        df_inv_agg = df_inventory.groupby('sku_id')['on_hand_qty'].sum().reset_index()
        df_kit_bom = df_kit_bom.merge(df_inv_agg, on='sku_id', how='left')
        df_kit_bom['on_hand_qty'] = df_kit_bom['on_hand_qty'].fillna(0).astype(int)
        
        # Calculate maximum buildable kits from each component: on_hand / required
        df_kit_bom['max_buildable'] = (df_kit_bom['on_hand_qty'] / df_kit_bom['component_qty']).apply(np.floor).astype(int)
        
        # 4. Compute overall kit statistics
        max_kits_buildable = df_kit_bom['max_buildable'].min()
        
        # Find bottleneck component
        bottleneck_row = df_kit_bom.sort_values('max_buildable').iloc[0]
        bottleneck_id = bottleneck_row['component_sku_id']
        bottleneck_name = bottleneck_row['sku_name']
        
        # Total cost to assemble one kit
        kit_unit_cost = (df_kit_bom['component_qty'] * df_kit_bom['unit_cost']).sum()
        
        # Display Kit KPI Summary Card
        st.markdown(f"#### Kit Profile: **{kit_name}**")
        
        col_k1, col_k2, col_k3, col_k4 = st.columns(4)
        with col_k1:
            st.metric(label="Total Buildable Units", value=f"{max_kits_buildable} Kits", delta="Based on components on-hand")
        with col_k2:
            st.metric(label="Primary Bottleneck Component", value=f"{bottleneck_id}", delta=bottleneck_name[:25])
        with col_k3:
            st.metric(label="Total Bill-of-Materials Cost", value=f"${kit_unit_cost:,.2f} / Kit", delta="Sum of components")
        with col_k4:
            st.metric(label="Active Components", value=f"{len(df_kit_bom)} items", delta="BOM lines")
            
        st.markdown("---")
        
        # 5. Dynamic BOM Planner Widget
        st.subheader("🛠️ Assembly Production Simulator")
        target_build_qty = st.number_input(
            "Enter Target Kit Run (Assembly Volume)", 
            min_value=1, 
            value=100, 
            step=10, 
            help="Simulates component shortages and replenishment orders required to assemble this quantity of kits."
        )
        
        # Calculate shortages
        df_kit_bom['qty_needed_for_run'] = df_kit_bom['component_qty'] * target_build_qty
        df_kit_bom['shortage'] = (df_kit_bom['qty_needed_for_run'] - df_kit_bom['on_hand_qty']).clip(lower=0)
        df_kit_bom['shortage_cost'] = df_kit_bom['shortage'] * df_kit_bom['unit_cost']
        
        total_shortage_cost = df_kit_bom['shortage_cost'].sum()
        
        # 6. Component breakdown table
        st.subheader("📋 Component Inventory Breakdown")
        
        # Format columns for display
        df_mrp_table = df_kit_bom[[
            'component_sku_id', 'sku_name', 'component_qty', 'on_hand_qty', 
            'max_buildable', 'qty_needed_for_run', 'shortage', 'shortage_cost'
        ]].copy()
        
        df_mrp_table.columns = [
            'Component SKU', 'Description', 'Qty Per Kit', 'On Hand Stock', 
            'Buildable Limit', 'Needed for Run', 'Shortage', 'Shortage Cost'
        ]
        
        # Add highlighted styling to bottleneck row
        def highlight_bottleneck(val):
            # We want to highlight the row matching the bottleneck SKU
            pass
            
        st.dataframe(
            df_mrp_table.style.format({
                'Qty Per Kit': '{:,}',
                'On Hand Stock': '{:,}',
                'Buildable Limit': '{:,}',
                'Needed for Run': '{:,}',
                'Shortage': '{:,}',
                'Shortage Cost': '${:,.2f}'
            }),
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown(f"**Total Capital Required for Shortages:** `${total_shortage_cost:,.2f}`")
        
        st.markdown("---")
        
        # 7. AI MRP Readiness Briefing
        st.subheader("🤖 MRP Readiness Analysis")
        st.write("Generate an on-demand material requirements planning analysis of this kit run, identifying critical paths and PO recommendations.")
        
        btn_mrp_ai = st.button("📋 Generate Kit Readiness Audit")
        if btn_mrp_ai:
            with st.spinner("Calculating material requirements planning logic..."):
                report = explain_mrp_kit_constraints(
                    selected_parent_id, 
                    parent_row['sku_name'], 
                    max_kits_buildable, 
                    df_kit_bom
                )
                st.markdown(
                    f"""
                    <div class="saas-card" style="border-left: 4px solid #ffa657; background-color: rgba(240, 136, 62, 0.05);">
                        {report}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
