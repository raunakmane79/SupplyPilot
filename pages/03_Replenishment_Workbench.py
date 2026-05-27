import streamlit as st
import pandas as pd
import datetime
import random
from src.database import get_db_connection, load_dataframe_from_table
from src.styling import inject_custom_css, create_kpi_card
from src.recommendations import generate_recommendations
from src.ai_assistant import create_procurement_note

# Page Setup
st.set_page_config(
    page_title="Replenishment Workbench - SupplyPilot AI",
    page_icon="📥",
    layout="wide"
)

inject_custom_css()

# Sidebar
st.sidebar.image("https://img.icons8.com/nolan/96/airplane-take-off.png", width=60)
st.sidebar.title("SupplyPilot AI")
st.sidebar.subheader("Replenishment Workbench")
st.sidebar.markdown("---")
st.sidebar.info(
    "📥 **Procurement Workbench:** Planners review suggested replenishment and expedite recommendations here. "
    "Check elements to approve, then click 'Commit Checked Orders' to record them as purchase orders in SQLite."
)

st.title("Replenishment Workbench")
st.markdown("### Interactive Order Authorization & Procurement Workspace")

# 1. Load active data
def load_workbench_data():
    df_recs = load_dataframe_from_table('recommendation_output')
    df_sku = load_dataframe_from_table('sku_master')
    df_supplier = load_dataframe_from_table('supplier_master')
    
    if df_recs.empty or df_sku.empty:
        return pd.DataFrame()
        
    df_merged = df_recs.merge(
        df_sku[['sku_id', 'sku_name', 'category', 'unit_cost', 'selling_price', 'moq', 'case_pack_qty', 'default_lead_time_days']], 
        on='sku_id', 
        how='inner'
    )
    df_merged = df_merged.merge(
        df_supplier[['supplier_id', 'supplier_name', 'payment_terms', 'minimum_order_value']], 
        on='supplier_id', 
        how='left'
    )
    
    # Calculate financial impact (Unit Cost * Suggested Qty)
    df_merged['financial_impact'] = df_merged['suggested_order_qty'] * df_merged['unit_cost']
    
    # Filter for SKUs that need action (Order or Expedite)
    df_actions = df_merged[df_merged['suggested_action'].isin(['Place Order', 'Expedite PO'])].copy()
    
    # Sort by risk level priority (Critical -> High -> Medium)
    priority_map = {'Critical': 1, 'High': 2, 'Medium': 3, 'Low': 4, 'Healthy': 5}
    df_actions['priority_num'] = df_actions['risk_level'].map(priority_map).fillna(5)
    df_actions = df_actions.sort_values(by=['priority_num', 'financial_impact'], ascending=[True, False])
    
    # Assign row number priority
    df_actions.insert(0, 'priority', range(1, len(df_actions) + 1))
    
    return df_actions

df_workbench = load_workbench_data()

if df_workbench.empty:
    st.success("🎉 All SKUs are currently healthy! No replenishment actions are recommended at this time.")
else:
    # 2. Display summary metric cards
    total_actions = len(df_workbench)
    order_actions = df_workbench[df_workbench['suggested_action'] == 'Place Order']
    expedite_actions = df_workbench[df_workbench['suggested_action'] == 'Expedite PO']
    
    total_capital_needed = order_actions['financial_impact'].sum()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(create_kpi_card("Replenishment Actions", f"{total_actions}", "Action Items", "neutral"), unsafe_allow_html=True)
    with col2:
        st.markdown(create_kpi_card("New Orders Suggested", f"{len(order_actions)} SKUs", "Replenishments", "up"), unsafe_allow_html=True)
    with col3:
        st.markdown(create_kpi_card("Expedite Requests", f"{len(expedite_actions)} Open POs", "Lead-Time Breaches", "down"), unsafe_allow_html=True)
    with col4:
        st.markdown(create_kpi_card("Capital Requirement", f"${total_capital_needed:,.2f}", "MOQ & Case Rounded", "neutral"), unsafe_allow_html=True)

    st.markdown("---")

    # 3. Interactive Data Editor for approvals
    st.subheader("📋 Replenishment Proposals Queue")
    st.caption("Double click checkboxes under 'Approve' and 'Reviewed' to select records. Click 'Commit Approved Orders' below to submit them.")

    # Add default checkboxes in dataframe
    df_workbench['Approve'] = False
    df_workbench['Reviewed'] = False
    
    # Select columns to display
    display_cols = [
        'Approve', 'Reviewed', 'priority', 'sku_id', 'sku_name', 'warehouse_id', 
        'supplier_name', 'inventory_position', 'reorder_point', 'suggested_order_qty', 
        'suggested_order_date', 'suggested_action', 'reason_code', 'financial_impact'
    ]
    
    # Render with Streamlit Data Editor
    edited_df = st.data_editor(
        df_workbench[display_cols],
        column_config={
            'Approve': st.column_config.CheckboxColumn('Approve', help="Select to place purchase order", default=False),
            'Reviewed': st.column_config.CheckboxColumn('Reviewed', help="Mark this recommendation as reviewed", default=False),
            'priority': st.column_config.NumberColumn('Priority', disabled=True),
            'sku_id': st.column_config.TextColumn('SKU', disabled=True),
            'sku_name': st.column_config.TextColumn('Description', disabled=True),
            'warehouse_id': st.column_config.TextColumn('WH', disabled=True),
            'supplier_name': st.column_config.TextColumn('Supplier', disabled=True),
            'inventory_position': st.column_config.NumberColumn('Position', disabled=True),
            'reorder_point': st.column_config.NumberColumn('ROP', disabled=True),
            'suggested_order_qty': st.column_config.NumberColumn('Suggested Qty', disabled=True),
            'suggested_order_date': st.column_config.TextColumn('Target Date', disabled=True),
            'suggested_action': st.column_config.TextColumn('Action', disabled=True),
            'reason_code': st.column_config.TextColumn('Reason Code', disabled=True),
            'financial_impact': st.column_config.NumberColumn('Est Cost', format="$%.2f", disabled=True),
        },
        use_container_width=True,
        hide_index=True
    )

    # 4. Action execution: Commit Approved Orders
    col_act1, col_act2, _ = st.columns([2, 2, 6])
    
    with col_act1:
        commit_btn = st.button("✔️ Commit Checked Orders", type="primary", use_container_width=True)
        if commit_btn:
            approved_rows = edited_df[edited_df['Approve'] == True]
            if approved_rows.empty:
                st.warning("No orders checked for approval. Select the checkboxes under 'Approve'.")
            else:
                # Commit to purchase_orders table in SQLite
                conn = get_db_connection()
                cursor = conn.cursor()
                
                success_count = 0
                today_str = datetime.date.today().isoformat()
                
                for _, row in approved_rows.iterrows():
                    sku_id = row['sku_id']
                    wh_id = row['warehouse_id']
                    qty = int(row['suggested_order_qty'])
                    
                    # Find supplier ID for SKU
                    cursor.execute("SELECT supplier_id, default_lead_time_days FROM sku_master WHERE sku_id = ?", (sku_id,))
                    sku_res = cursor.fetchone()
                    if sku_res:
                        supplier_id = sku_res['supplier_id']
                        lt_days = sku_res['default_lead_time_days']
                    else:
                        supplier_id = "SUP-101"
                        lt_days = 14
                        
                    po_id = f"PO-APP-{random.randint(10000, 99999)}"
                    exp_date = (datetime.date.today() + datetime.timedelta(days=lt_days)).isoformat()
                    
                    # 1. Insert new purchase order
                    cursor.execute("""
                        INSERT INTO purchase_orders 
                        (po_id, sku_id, supplier_id, warehouse_id, order_date, expected_arrival_date, actual_arrival_date, order_qty, received_qty, status)
                        VALUES (?, ?, ?, ?, ?, ?, NULL, ?, 0, 'Open')
                    """, (po_id, sku_id, supplier_id, wh_id, today_str, exp_date, qty))
                    
                    # 2. Update stock status - add quantity to on_order_qty in local memory / update the database directly?
                    # The ROP calculations dynamically pull open POs, so we don't need to manually update inventory_status.
                    
                    success_count += 1
                
                conn.commit()
                conn.close()
                
                # Regenerate recommendations
                generate_recommendations()
                
                st.success(f"Successfully recorded {success_count} new Purchase Orders in SQLite database! Recommendations updated.")
                st.rerun()

    with col_act2:
        # Export recommendations as CSV
        csv_data = df_workbench.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Queue to CSV",
            data=csv_data,
            file_name=f"SupplyPilot_Replenishment_Proposals_{datetime.date.today().isoformat()}.csv",
            mime="text/csv",
            use_container_width=True
        )

    st.markdown("---")

    # 5. Procurement Communications Section
    st.subheader("✉️ Auto-Draft Supplier Communications")
    st.write("Select a recommendation below to generate a pre-formatted email draft for procurement buyers.")
    
    sku_list = df_workbench.apply(lambda r: f"{r['sku_id']} | {r['sku_name']} ({r['warehouse_id']})", axis=1).tolist()
    selected_comm_sku = st.selectbox("Select SKU for Communication", sku_list)
    
    # Get matching row
    comm_idx = sku_list.index(selected_comm_sku)
    comm_row = df_workbench.iloc[comm_idx]
    
    email_text = create_procurement_note(comm_row)
    
    st.text_area("Generated Draft Email", email_text, height=350)
    st.caption("💡 Copy this email draft to send directly to your vendor account representative.")
