import streamlit as st
import pandas as pd
import io
from src.database import get_db_connection, clear_all_tables, init_db, is_db_empty
from src.data_generator import generate_all_demo_data
from src.recommendations import generate_recommendations
from src.styling import inject_custom_css
from src.upload_validator import validate_dataframe, get_template_csv, SCHEMAS

# Page Setup
st.set_page_config(
    page_title="Data Upload & Templates - SupplyPilot AI",
    page_icon="📤",
    layout="wide"
)

inject_custom_css()

# Sidebar
st.sidebar.image("https://img.icons8.com/nolan/96/airplane-take-off.png", width=60)
st.sidebar.title("SupplyPilot AI")
st.sidebar.subheader("Data Upload Center")
st.sidebar.markdown("---")

st.title("Data Upload & Templates")
st.markdown("### Platform Integration & Data Mapping Portal")

# 1. Mode Control and Reset Actions
col_m1, col_m2 = st.columns([3, 1])

with col_m1:
    st.markdown(
        "SupplyPilot AI can run in **Demo Mode** using simulated retail datasets for *Meridian Retail Group*, "
        "or in **User Data Mode** by importing your own inventory and procurement files. "
        "Upload files matching the required schemas below, then click **Commit Custom Data**."
    )
    
with col_m2:
    btn_reset = st.button("⚠️ Reset to Demo Mode", use_container_width=True)
    if btn_reset:
        with st.spinner("Clearing custom datasets and reloading Meridian Retail Group demo data..."):
            clear_all_tables()
            generate_all_demo_data()
            generate_recommendations()
            st.success("Successfully reset SQLite database to Demo Mode!")
            st.rerun()

st.markdown("---")

# 2. Template Downloads Section
st.subheader("📥 Download CSV Integration Templates")
st.write("Download these schema-conforming CSV files to map your own ERP/MRP data into SupplyPilot AI.")

# Display templates download buttons in a grid
g_col1, g_col2, g_col3 = st.columns(3)
g_col4, g_col5, g_col6 = st.columns(3)

with g_col1:
    st.download_button(
        label="📄 Download SKU Master Template",
        data=get_template_csv('sku_master'),
        file_name="SupplyPilot_SKU_Master_Template.csv",
        mime="text/csv",
        use_container_width=True
    )
with g_col2:
    st.download_button(
        label="📄 Download Inventory Status Template",
        data=get_template_csv('inventory_status'),
        file_name="SupplyPilot_Inventory_Status_Template.csv",
        mime="text/csv",
        use_container_width=True
    )
with g_col3:
    st.download_button(
        label="📄 Download Demand History Template",
        data=get_template_csv('demand_history'),
        file_name="SupplyPilot_Demand_History_Template.csv",
        mime="text/csv",
        use_container_width=True
    )
with g_col4:
    st.download_button(
        label="📄 Download Supplier Master Template",
        data=get_template_csv('supplier_master'),
        file_name="SupplyPilot_Supplier_Master_Template.csv",
        mime="text/csv",
        use_container_width=True
    )
with g_col5:
    st.download_button(
        label="📄 Download Purchase Orders Template",
        data=get_template_csv('purchase_orders'),
        file_name="SupplyPilot_Purchase_Orders_Template.csv",
        mime="text/csv",
        use_container_width=True
    )
with g_col6:
    st.download_button(
        label="📄 Download BOM/Kit Structure Template",
        data=get_template_csv('bom_or_kit_structure'),
        file_name="SupplyPilot_BOM_Structure_Template.csv",
        mime="text/csv",
        use_container_width=True
    )

st.markdown("---")

# 3. File Upload and Validation Section
st.subheader("📤 Import Custom Datasets")
st.write("Upload your CSV or Excel files. The validator will audit files for column schema conformance on-the-fly.")

# Keep uploaded dataframes in session state until committed
if 'custom_dfs' not in st.session_state:
    st.session_state['custom_dfs'] = {}

upload_configs = [
    ('sku_master', 'SKU Master File (Required)'),
    ('inventory_status', 'Inventory Status File (Required)'),
    ('demand_history', 'Demand History File (Required)'),
    ('supplier_master', 'Supplier Master File (Required)'),
    ('purchase_orders', 'Purchase Orders File (Required)'),
    ('bom_or_kit_structure', 'BOM or Kit Structure (Optional)')
]

for table_name, label in upload_configs:
    uploaded_file = st.file_uploader(f"Upload {label}", type=['csv', 'xlsx'], key=f"upload_{table_name}")
    
    if uploaded_file is not None:
        try:
            # Parse file type
            if uploaded_file.name.endswith('.csv'):
                df_raw = pd.read_csv(uploaded_file)
            else:
                df_raw = pd.read_excel(uploaded_file)
                
            # Run validation
            is_valid, err_msg, df_cleaned = validate_dataframe(df_raw, table_name)
            
            if is_valid:
                st.success(f"✅ **{uploaded_file.name}** validated successfully! Found {len(df_cleaned)} rows.")
                st.session_state['custom_dfs'][table_name] = df_cleaned
            else:
                st.error(f"❌ **{uploaded_file.name}** validation failed: {err_msg}")
                # Show columns found
                st.info(f"Columns found in file: {list(df_raw.columns)}. Required columns are: {SCHEMAS[table_name]['required']}")
                # Delete from state
                st.session_state['custom_dfs'].pop(table_name, None)
        except Exception as e:
            st.error(f"Error parsing file: {e}")
            st.session_state['custom_dfs'].pop(table_name, None)

st.markdown("---")

# 4. Commit Uploaded Data to SQL
st.subheader("💾 Commit Custom Data to Platform")
st.write(
    "Click the button below to overwrite the SQLite database with your validated files. "
    "This will clear the demo dataset and run replenishment calculations for your items."
)

required_loaded = all(k in st.session_state['custom_dfs'] for k in ['sku_master', 'inventory_status', 'demand_history', 'supplier_master', 'purchase_orders'])

if required_loaded:
    st.markdown('<p style="color:#56d364; font-weight:600;">✅ All required files uploaded and validated. Ready to commit.</p>', unsafe_allow_html=True)
    
    btn_commit = st.button("💾 Commit Custom Data & Run Calculations", type="primary", use_container_width=True)
    if btn_commit:
        with st.spinner("Clearing database tables and loading custom files..."):
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Clear all tables
            clear_all_tables()
            init_db() # ensure tables exist
            
            # Write uploaded tables
            for table_name, df_data in st.session_state['custom_dfs'].items():
                # Write to sqlite using pandas to_sql (simpler for direct dataframe dump)
                # Since we standardized column names, we can append/replace. 
                # Note: to_sql might drop PK indexes, so we insert/executemany, or we can use to_sql with if_exists='append'
                df_data.to_sql(table_name, conn, if_exists='append', index=False)
                
            # If BOM was not uploaded, ensure empty table or proceed
            if 'bom_or_kit_structure' not in st.session_state['custom_dfs']:
                # empty insert or do nothing
                pass
                
            conn.commit()
            conn.close()
            
            # Run replenishment recommendations
            success = generate_recommendations()
            if success:
                st.success("🎉 Custom data committed and planning recommendations calculated successfully!")
                # Reset cache
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Calculations failed. Check that SKU IDs in SKU master match SKU IDs in Demand history and Inventory tables.")
else:
    # List which required files are still missing
    missing_reqs = []
    for k in ['sku_master', 'inventory_status', 'demand_history', 'supplier_master', 'purchase_orders']:
        if k not in st.session_state.get('custom_dfs', {}):
            missing_reqs.append(k.replace('_', ' ').title())
            
    st.warning(f"⚠️ **Incomplete Dataset:** Please upload and validate the following required files: {', '.join(missing_reqs)}")
    st.button("💾 Commit Custom Data & Run Calculations", disabled=True, use_container_width=True)
