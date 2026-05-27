import streamlit as st
import pandas as pd
from src.database import get_db_connection, load_dataframe_from_table
from src.styling import inject_custom_css
from src.forecasting import generate_forecasts
from src.charts import plot_actual_vs_forecast

# Page Setup
st.set_page_config(
    page_title="Demand Forecasting Lab - SupplyPilot AI",
    page_icon="📈",
    layout="wide"
)

inject_custom_css()

# Sidebar
st.sidebar.image("https://img.icons8.com/nolan/96/airplane-take-off.png", width=60)
st.sidebar.title("SupplyPilot AI")
st.sidebar.subheader("Demand Forecasting Lab")
st.sidebar.markdown("---")
st.sidebar.info(
    "🔬 **Forecasting Lab:** Compare statistical forecasting models on historical SKU demand. "
    "Check fit errors (MAPE) and project future demand over a 12-week horizon."
)

st.title("Demand Forecasting Lab")
st.markdown("### Advanced Statistical SKU Forecasting Models")

# Alter sku_master schema if forecast_method_override doesn't exist
# Runs safely in SQLite
conn = get_db_connection()
try:
    conn.execute("ALTER TABLE sku_master ADD COLUMN forecast_method_override TEXT")
    conn.commit()
except Exception:
    # Column already exists
    pass
conn.close()

# 1. Load data
df_demand = load_dataframe_from_table('demand_history')
df_sku = load_dataframe_from_table('sku_master')

if df_demand.empty or df_sku.empty:
    st.warning("⚠️ No demand history or SKU records found. Initialize the database on the **Data Upload & Templates** page.")
else:
    # 2. Select SKU and Warehouse
    sku_options = df_sku.apply(lambda r: f"{r['sku_id']} | {r['sku_name']}", axis=1).tolist()
    
    col1, col2 = st.columns(2)
    with col1:
        selected_sku_option = st.selectbox("Select Target SKU to Model", sku_options)
        selected_sku_id = selected_sku_option.split(" | ")[0]
        sku_row = df_sku[df_sku['sku_id'] == selected_sku_id].iloc[0]
        
    with col2:
        wh_options = ["All Warehouses"] + sorted(df_demand[df_demand['sku_id'] == selected_sku_id]['warehouse_id'].dropna().unique().tolist())
        selected_wh_option = st.selectbox("Select Warehouse Aggregation", wh_options)
        selected_wh_id = None if selected_wh_option == "All Warehouses" else selected_wh_option

    st.markdown("---")

    # 3. Generate Forecast
    wh_filter = selected_wh_id if selected_wh_id else None
    df_hist, df_fc, metrics = generate_forecasts(df_demand, selected_sku_id, wh_filter)
    
    if df_hist.empty or len(df_hist) < 8:
        st.error("❌ Insufficient demand history for this SKU to run forecasting algorithms. A minimum of 8 weeks of history is required.")
    else:
        # Display Forecasting accuracy
        st.subheader("📊 Model Performance Scorecard")
        st.caption("Lower Mean Absolute Percentage Error (MAPE) indicates a more accurate historical fit.")
        
        m_col1, m_col2, m_col3 = st.columns(3)
        
        with m_col1:
            with st.container(border=True):
                st.metric(label="Simple Moving Average (4-Week)", value=f"{metrics['moving_average']:.1f}% MAPE")
        with m_col2:
            with st.container(border=True):
                st.metric(label="Weighted Moving Average (4-Week)", value=f"{metrics['weighted_moving_average']:.1f}% MAPE")
        with m_col3:
            with st.container(border=True):
                st.metric(label="Exponential Smoothing (α=0.3)", value=f"{metrics['exponential_smoothing']:.1f}% MAPE")
            
        # Model selector and optimizer actions
        st.markdown("#### Model Optimization Control")
        col_ctrl1, col_ctrl2 = st.columns(2)
        
        # Check current model override from DB
        current_override = sku_row.get('forecast_method_override', 'exponential_smoothing')
        current_override = current_override if current_override else 'exponential_smoothing'
        
        model_names_map = {
            'moving_average': 'Simple Moving Average',
            'weighted_moving_average': 'Weighted Moving Average',
            'exponential_smoothing': 'Exponential Smoothing'
        }
        
        # Display current active plan model
        st.write(f"**Current Active Planning Model:** `{model_names_map.get(current_override, 'Exponential Smoothing')}`")
        
        with col_ctrl1:
            model_options = list(model_names_map.keys())
            model_display_names = list(model_names_map.values())
            
            selected_model = st.selectbox(
                "Manual Model Select Override", 
                model_display_names, 
                index=model_options.index(current_override) if current_override in model_options else 2
            )
            
            # Save manually selected model
            manual_model_key = [k for k, v in model_names_map.items() if v == selected_model][0]
            btn_save_model = st.button("🎯 Set Selected Model as Active")
            
            if btn_save_model:
                conn = get_db_connection()
                conn.execute("UPDATE sku_master SET forecast_method_override = ? WHERE sku_id = ?", (manual_model_key, selected_sku_id))
                conn.commit()
                conn.close()
                st.success(f"Active planning model updated to {selected_model} in SQLite!")
                st.rerun()
                
        with col_ctrl2:
            st.write("Let the system select the best performing forecasting model based on the lowest historical fitting error (MAPE).")
            btn_optimize = st.button("⚡ Run Algorithmic Model Optimizer", type="primary")
            
            if btn_optimize:
                # Find model with lowest MAPE value
                best_model_key = min(metrics, key=metrics.get)
                best_model_name = model_names_map[best_model_key]
                best_mape = metrics[best_model_key]
                
                conn = get_db_connection()
                conn.execute("UPDATE sku_master SET forecast_method_override = ? WHERE sku_id = ?", (best_model_key, selected_sku_id))
                conn.commit()
                conn.close()
                
                st.success(f"Optimized! `{best_model_name}` selected as active planning model (Lowest MAPE: {best_mape:.1f}%). Committed to SQLite database.")
                st.rerun()
                
        st.markdown("---")
        
        # 4. Chart Display
        fig = plot_actual_vs_forecast(df_hist, df_fc, selected_sku_id)
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # 5. Table of projected values & export
        col_t1, col_t2 = st.columns([1, 1])
        
        with col_t1:
            st.subheader("📋 12-Week Forecast Projections")
            df_fc_display = df_fc.copy()
            df_fc_display['date'] = df_fc_display['date'].dt.strftime('%Y-%m-%d')
            df_fc_display.columns = ['Week Date', 'Moving Average (Units)', 'Weighted MA (Units)', 'Exponential Smoothing (Units)']
            
            st.dataframe(df_fc_display, use_container_width=True, hide_index=True)
            
        with col_t2:
            st.subheader("🔬 Model Explanations")
            st.markdown(
                """
                - **Simple Moving Average (SMA):**
                  Averages demand over a sliding window of 4 weeks. Ideal for stable, mature product classes (XYZ: X). 
                  Fails to capture short-term trends or seasonal spikes.
                  
                - **Weighted Moving Average (WMA):**
                  Applies weights `[0.4, 0.3, 0.2, 0.1]` prioritizing recent periods. Captures quick demand shifts faster than SMA, 
                  making it well-suited for fast-moving launch stages.
                  
                - **Exponential Smoothing (SES):**
                  Computes a weighted average of past demands with exponentially decaying weights controlled by smoothing parameter $\\alpha=0.3$. 
                  Balances stability and responsiveness.
                  
                - **Seasonality Indexing (SupplyPilot Enhancement):**
                  If the SKU belongs to a seasonal category (e.g. Outdoor or Apparel), SupplyPilot applies historical seasonal index modifiers 
                  based on the week of year, allowing future projections to reflect realistic cyclic surges.
                """
            )
            
            # Download forecast button
            csv_data = df_fc.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Projections to CSV",
                data=csv_data,
                file_name=f"SupplyPilot_12W_Forecast_{selected_sku_id}_{selected_wh_option}.csv",
                mime="text/csv",
                use_container_width=True
            )
