import datetime
import pandas as pd
import numpy as np
from src.database import get_db_connection, load_dataframe_from_table
from src.calculations import compute_inventory_parameters
from src.risk_scoring import calculate_stockout_risk_score, classify_risk_level, compute_excess_inventory

def generate_recommendations():
    """
    Runs calculations on current database state, generates planning recommendations,
    and inserts them into the `recommendation_output` table in SQLite.
    """
    # 1. Load active dataframes
    conn = get_db_connection()
    
    df_sku = load_dataframe_from_table('sku_master')
    df_inventory = load_dataframe_from_table('inventory_status')
    df_demand = load_dataframe_from_table('demand_history')
    df_po = load_dataframe_from_table('purchase_orders')
    df_supplier = load_dataframe_from_table('supplier_master')
    
    if df_sku.empty or df_inventory.empty or df_demand.empty:
        conn.close()
        return False
        
    # 2. Compute basic parameters
    df_master = compute_inventory_parameters(df_sku, df_inventory, df_demand, df_po, df_supplier)
    
    # 3. Calculate Risk Score and Classification
    df_master['risk_score_calc'] = df_master.apply(calculate_stockout_risk_score, axis=1)
    df_master['risk_level'] = df_master['risk_score_calc'].apply(classify_risk_level)
    
    # 4. Calculate Excess Inventory
    excess_results = df_master.apply(compute_excess_inventory, axis=1)
    df_master['excess_qty'] = [r[0] for r in excess_results]
    df_master['excess_inventory_value'] = [r[1] for r in excess_results]
    
    # 5. Calculate Stockout Value Exposure
    # If Days of Cover is less than the lead time, we will stockout before replenishment arrives.
    # Exposure = Days Short * Avg Daily Demand * Selling Price
    def compute_stockout_exposure(row):
        lt = row['lead_time_adjusted']
        doc = row['days_of_cover']
        if doc < lt and row['add_90'] > 0:
            days_short = max(lt - max(doc, 0.0), 0.0)
            return round(days_short * row['add_90'] * row['selling_price'], 2)
        return 0.0
        
    df_master['estimated_stockout_value'] = df_master.apply(compute_stockout_exposure, axis=1)
    
    # 6. Apply Actions and Reason Codes
    def assign_action_and_reason(row):
        risk = row['risk_level']
        doc = row['days_of_cover']
        on_order = row['on_order_qty']
        rop = row['reorder_point']
        ip = row['inventory_position']
        suggested_qty = row['suggested_order_qty']
        excess_val = row['excess_inventory_value']
        
        action = "Monitor"
        reason = "Healthy Stock"
        
        # Checking excess first
        if excess_val > 0 and doc > 90.0:
            action = "Redistribute Stock" if row['on_hand_qty'] > 100 else "Liquidate/Promote"
            reason = "EXCESS_STOCK"
            return action, reason
            
        # Checking stockouts/replenishment
        if risk in ['Critical', 'High']:
            if doc <= 0:
                if on_order > 0:
                    action = "Expedite PO"
                    reason = "STOCKOUT_ACTIVE_PO"
                else:
                    action = "Place Order"
                    reason = "STOCKOUT_NO_PO"
            else:
                if on_order > 0:
                    action = "Expedite PO"
                    reason = "CRITICAL_LEAD_TIME_BREACH"
                else:
                    action = "Place Order"
                    reason = "REORDER_TRIGGERED"
        elif ip < rop and suggested_qty > 0:
            action = "Place Order"
            reason = "REORDER_TRIGGERED"
            
        return action, reason
        
    action_reason = df_master.apply(assign_action_and_reason, axis=1)
    df_master['suggested_action'] = [ar[0] for ar in action_reason]
    df_master['reason_code'] = [ar[1] for ar in action_reason]
    
    # Created timestamp
    created_at = datetime.datetime.now().isoformat()
    
    # 7. Write to SQLite
    cursor = conn.cursor()
    cursor.execute("DELETE FROM recommendation_output")
    
    rec_records = []
    for _, row in df_master.iterrows():
        rec_records.append((
            row['sku_id'],
            row['warehouse_id'],
            row['risk_level'],
            int(row['inventory_position']),
            float(row['days_of_cover']),
            float(row['reorder_point']),
            float(row['safety_stock']),
            int(row['suggested_order_qty']),
            row['suggested_order_date'],
            row['suggested_action'],
            row['reason_code'],
            float(row['estimated_stockout_value']),
            float(row['excess_inventory_value']),
            created_at
        ))
        
    cursor.executemany("""
    INSERT OR REPLACE INTO recommendation_output
    (sku_id, warehouse_id, risk_level, inventory_position, days_of_cover, reorder_point,
     safety_stock, suggested_order_qty, suggested_order_date, suggested_action, reason_code,
     estimated_stockout_value, excess_inventory_value, created_at)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rec_records)
    
    conn.commit()
    conn.close()
    return True
