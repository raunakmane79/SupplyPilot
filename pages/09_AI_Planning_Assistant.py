import streamlit as st
import pandas as pd
from src.database import load_dataframe_from_table
from src.styling import inject_custom_css
from src.ai_assistant import (
    create_weekly_action_plan_ai, 
    summarize_supplier_risk_ai, 
    explain_sku_risk_ai,
    create_procurement_note,
    explain_mrp_kit_constraints
)

# Page Setup
st.set_page_config(
    page_title="AI Planning Assistant - SupplyPilot AI",
    page_icon="🤖",
    layout="wide"
)

inject_custom_css()

# Sidebar
st.sidebar.image("https://img.icons8.com/nolan/96/airplane-take-off.png", width=60)
st.sidebar.title("SupplyPilot AI")
st.sidebar.subheader("AI Assistant")
st.sidebar.markdown("---")

api_key = st.sidebar.text_input("OpenAI API Key (Optional)", type="password", help="Input your key to enable GPT-4 powered briefings. Leaving it blank triggers template NLG fallbacks.")

st.title("AI Planning Assistant")
st.markdown("### Copilot Decision-Support Command Center")

# Load active data
df_recs = load_dataframe_from_table('recommendation_output')
df_sku = load_dataframe_from_table('sku_master')
df_supplier = load_dataframe_from_table('supplier_master')
df_po = load_dataframe_from_table('purchase_orders')
df_bom = load_dataframe_from_table('bom_or_kit_structure')

if df_recs.empty or df_sku.empty:
    st.warning("⚠️ Database is empty. Please initialize it on the **Data Upload & Templates** page.")
else:
    # Merge SKU details into recommendations for copilot context
    df_merged = df_recs.merge(
        df_sku[['sku_id', 'sku_name', 'category', 'unit_cost', 'selling_price', 'moq', 'case_pack_qty', 'service_level_target', 'default_lead_time_days', 'criticality', 'lifecycle_status']], 
        on='sku_id', 
        how='inner'
    )
    df_merged = df_merged.merge(
        df_supplier[['supplier_id', 'supplier_name', 'avg_lead_time_days', 'lead_time_std_days', 'on_time_delivery_rate', 'fill_rate', 'risk_score']], 
        on='supplier_id', 
        how='left'
    )
    # Calculate Lead Time Adjusted (default fallback for prompt)
    df_merged['lead_time_adjusted'] = df_merged['default_lead_time_days']
    
    # Calculate on-order (default fallback for prompt)
    df_po_open = df_po[df_po['status'].isin(['Open', 'In Transit'])]
    df_po_agg = df_po_open.groupby(['sku_id', 'warehouse_id'])['order_qty'].sum().reset_index()
    df_po_agg.rename(columns={'order_qty': 'on_order_qty'}, inplace=True)
    df_merged = df_merged.merge(df_po_agg, on=['sku_id', 'warehouse_id'], how='left')
    df_merged['on_order_qty'] = df_merged['on_order_qty'].fillna(0).astype(int)
    
    # Aggregated lists for prompt
    df_po_active = df_po[df_po['status'].isin(['Open', 'In Transit'])]

    st.write(
        "Use structured shortcuts to run AI planning actions on the active database. "
        "The system generates context-aware briefs based on calculations."
    )

    # 1. Weekly Executive Action Plan Command
    st.markdown("#### 📅 Strategic Operations Briefs")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(
            """
            <div class="saas-card" style="min-height: 180px;">
                <h5>📈 Weekly Executive Action Plan</h5>
                <p style="color:#8b949e; font-size:0.9rem;">
                    Generates a high-level operational review detailing replenishment capital needs, expedites, 
                    and working capital recovery actions.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        btn_plan = st.button("📊 Generate Weekly Planning Summary", use_container_width=True)
        if btn_plan:
            with st.spinner("Compiling database parameters and running CSCO planner model..."):
                plan_text = create_weekly_action_plan_ai(df_merged, df_supplier, api_key=api_key)
                st.markdown("---")
                st.markdown(
                    f"""
                    <div class="saas-card" style="border-left: 4px solid #1f6feb;">
                        {plan_text}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
    with col2:
        st.markdown(
            """
            <div class="saas-card" style="min-height: 180px;">
                <h5>🚚 Supplier Vulnerability Audit</h5>
                <p style="color:#8b949e; font-size:0.9rem;">
                    Summarizes systemic supplier network risks, delayed transits, and single-source bottlenecks 
                    in the supply chain.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        btn_sup = st.button("🚚 Summarize Network Supplier Risk", use_container_width=True)
        if btn_sup:
            with st.spinner("Analyzing supplier scorecards and logistics pipelines..."):
                sup_text = summarize_supplier_risk_ai(df_supplier, df_sku, df_po, api_key=api_key)
                st.markdown("---")
                st.markdown(
                    f"""
                    <div class="saas-card" style="border-left: 4px solid #bc8cff;">
                        {sup_text}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    st.markdown("---")

    # 2. SKU and MRP Constraint Commands
    st.markdown("#### 🔍 Item & BOM Assembly Audits")
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown(
            """
            <div class="saas-card" style="min-height: 180px;">
                <h5>⚡ SKU Risk Briefings & Draft Notes</h5>
                <p style="color:#8b949e; font-size:0.9rem;">
                    Select a critical SKU to generate an explanation of safety stock breaches, 
                    lost revenue values, and a draft vendor email.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        # Selectbox of top critical SKUs
        df_crit = df_merged[df_merged['risk_level'].isin(['Critical', 'High'])]
        if df_crit.empty:
            df_crit = df_merged
            
        sku_options = df_crit.apply(lambda r: f"{r['sku_id']} | {r['sku_name']} ({r['warehouse_id']})", axis=1).tolist()
        sel_sku_opt = st.selectbox("Select Target Critical SKU", sku_options)
        
        btn_sku = st.button("🔍 Explain Selected SKU Risk", use_container_width=True)
        if btn_sku:
            idx = sku_options.index(sel_sku_opt)
            sku_row = df_crit.iloc[idx]
            
            # Find open POs
            df_po_item = df_po_active[
                (df_po_active['sku_id'] == sku_row['sku_id']) & 
                (df_po_active['warehouse_id'] == sku_row['warehouse_id'])
            ]
            
            with st.spinner("Running SKU diagnostic model..."):
                sku_brief = explain_sku_risk_ai(sku_row, df_po_item, api_key=api_key)
                email_note = create_procurement_note(sku_row)
                
                st.markdown("---")
                st.markdown(
                    f"""
                    <div class="saas-card" style="border-left: 4px solid #ffa657;">
                        <h4>SKU Risk Brief</h4>
                        {sku_brief}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                st.text_area("Auto-Draft Procurement Email Note", email_note, height=250)

    with col4:
        st.markdown(
            """
            <div class="saas-card" style="min-height: 180px;">
                <h5>⚙️ BOM Kit Constraints Auditor</h5>
                <p style="color:#8b949e; font-size:0.9rem;">
                    Select a parent kit to evaluate assembly capacity. Pinpoints bottleneck components and 
                    generates order requirements.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Load unique BOM parent kits
        parent_ids = df_bom['parent_sku_id'].unique().tolist()
        parent_skus = df_sku[df_sku['sku_id'].isin(parent_ids)]
        
        if parent_skus.empty:
            st.info("No kits/BOM structures found in the database.")
        else:
            kit_options = parent_skus.apply(lambda r: f"{r['sku_id']} | {r['sku_name']}", axis=1).tolist()
            sel_kit_opt = st.selectbox("Select Target Parent Kit to Audit", kit_options)
            
            btn_mrp = st.button("⚙️ Explain MRP Kit Constraints", use_container_width=True)
            if btn_mrp:
                kit_id = sel_kit_opt.split(" | ")[0]
                kit_row = parent_skus[parent_skus['sku_id'] == kit_id].iloc[0]
                
                # Fetch components
                df_kit_bom = df_bom[df_bom['parent_sku_id'] == kit_id].copy()
                df_kit_bom = df_kit_bom.merge(
                    df_sku[['sku_id', 'sku_name', 'unit_cost']], 
                    left_on='component_sku_id', 
                    right_on='sku_id', 
                    how='inner'
                )
                df_inv_agg = df_po_open.merge(df_sku[['sku_id', 'unit_cost']], on='sku_id', how='right') # placeholder
                
                # Aggregate component stocks
                df_inv = load_dataframe_from_table('inventory_status')
                df_inv_agg = df_inv.groupby('sku_id')['on_hand_qty'].sum().reset_index()
                df_kit_bom = df_kit_bom.merge(df_inv_agg, on='sku_id', how='left')
                df_kit_bom['on_hand_qty'] = df_kit_bom['on_hand_qty'].fillna(0).astype(int)
                
                df_kit_bom['max_buildable'] = (df_kit_bom['on_hand_qty'] / df_kit_bom['component_qty']).apply(np.floor).astype(int)
                max_kits = df_kit_bom['max_buildable'].min()
                
                with st.spinner("Analyzing material requirements planning constraints..."):
                    mrp_report = explain_mrp_kit_constraints(
                        kit_id, 
                        kit_row['sku_name'], 
                        max_kits, 
                        df_kit_bom
                    )
                    st.markdown("---")
                    st.markdown(
                        f"""
                        <div class="saas-card" style="border-left: 4px solid #56d364;">
                            {mrp_report}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
