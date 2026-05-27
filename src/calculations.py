import pandas as pd
import numpy as np

def get_z_score(service_level):
    """
    Returns the standard normal Z-score corresponding to target service levels.
    """
    # 90% = 1.28, 95% = 1.65, 98% = 2.05, 99% = 2.33
    if service_level >= 0.99:
        return 2.33
    elif service_level >= 0.98:
        return 2.05
    elif service_level >= 0.95:
        return 1.65
    elif service_level >= 0.90:
        return 1.28
    else:
        return 1.00 # default fallback for low service levels

def run_demand_classification(df_demand, df_sku):
    """
    Performs ABC and XYZ classification on the SKU dataset using demand history.
    Updates the df_sku dataframe in place with 'abc_class' and 'xyz_class'.
    """
    if df_demand.empty or df_sku.empty:
        return df_sku
        
    df_demand['date'] = pd.to_datetime(df_demand['date'])
    max_date = df_demand['date'].max()
    
    # 1. Calculate Average Daily Demand for ABC (based on last 90 days of active data)
    cutoff_90 = max_date - pd.Timedelta(days=90)
    df_90 = df_demand[df_demand['date'] >= cutoff_90]
    
    avg_demand_90 = df_90.groupby('sku_id')['demand_qty'].sum() / 90.0
    avg_demand_90 = avg_demand_90.reindex(df_sku['sku_id']).fillna(0.0)
    
    # Calculate annualized usage value: annual demand * unit cost
    # Annual demand = daily demand * 365
    annual_usage = avg_demand_90 * 365.0 * df_sku.set_index('sku_id')['unit_cost']
    annual_usage = annual_usage.reset_index(name='usage_value')
    
    # Sort descending for ABC
    annual_usage = annual_usage.sort_values(by='usage_value', ascending=False)
    annual_usage['cum_sum'] = annual_usage['usage_value'].cumsum()
    total_value = annual_usage['usage_value'].sum()
    
    if total_value > 0:
        annual_usage['cum_pct'] = annual_usage['cum_sum'] / total_value
    else:
        annual_usage['cum_pct'] = 0.0
        
    # ABC Rules: A = top 80%, B = next 15% (80-95%), C = remaining 5%
    def classify_abc(row):
        pct = row['cum_pct']
        if pct <= 0.80:
            return 'A'
        elif pct <= 0.95:
            return 'B'
        else:
            return 'C'
            
    annual_usage['abc_class'] = annual_usage.apply(classify_abc, axis=1)
    
    # 2. XYZ classification (demand variability)
    # Calculate weekly demand std dev / weekly demand mean
    # We aggregate weekly to avoid daily sparsity issues
    df_demand['week'] = df_demand['date'].dt.to_period('W')
    weekly_agg = df_demand.groupby(['sku_id', 'week'])['demand_qty'].sum().reset_index()
    
    weekly_stats = weekly_agg.groupby('sku_id')['demand_qty'].agg(['mean', 'std']).reset_index()
    weekly_stats['std'] = weekly_stats['std'].fillna(0.0)
    
    # Coefficient of Variation: CV = std / mean
    # Handle mean = 0
    weekly_stats['cv'] = np.where(weekly_stats['mean'] > 0, weekly_stats['std'] / weekly_stats['mean'], 9.9)
    
    # XYZ Rules: X = CV <= 0.20 (Stable), Y = 0.20 < CV <= 0.50 (Moderate), Z = CV > 0.50 (High/Volatile)
    def classify_xyz(row):
        cv = row['cv']
        if cv <= 0.20:
            return 'X'
        elif cv <= 0.50:
            return 'Y'
        else:
            return 'Z'
            
    weekly_stats['xyz_class'] = weekly_stats.apply(classify_xyz, axis=1)
    
    # Merge back to df_sku
    abc_map = annual_usage.set_index('sku_id')['abc_class'].to_dict()
    xyz_map = weekly_stats.set_index('sku_id')['xyz_class'].to_dict()
    
    df_sku['abc_class'] = df_sku['sku_id'].map(abc_map).fillna('C')
    df_sku['xyz_class'] = df_sku['sku_id'].map(xyz_map).fillna('Z')
    
    return df_sku

def calculate_on_order_qty(df_po):
    """
    Returns a dataframe of SKU-warehouse combinations and their total open on-order quantity.
    """
    if df_po.empty:
        return pd.DataFrame(columns=['sku_id', 'warehouse_id', 'on_order_qty'])
        
    open_pos = df_po[df_po['status'].isin(['Open', 'In Transit'])]
    grouped = open_pos.groupby(['sku_id', 'warehouse_id'])['order_qty'].sum().reset_index()
    grouped.rename(columns={'order_qty': 'on_order_qty'}, inplace=True)
    return grouped

def compute_inventory_parameters(df_sku, df_inventory, df_demand, df_po, df_supplier, demand_increase_pct=0.0, supplier_delay_days=0.0, target_sl_override=None):
    """
    Runs core supply chain logic for safety stock, ROP, days of cover, and suggested replenishment.
    Accepts scenario factors (demand_increase_pct, supplier_delay_days, target_sl_override) for dynamic sandbox calculations.
    """
    # 1. Extract demand stats
    df_demand['date'] = pd.to_datetime(df_demand['date'])
    max_date = df_demand['date'].max()
    
    # Average Daily Demand for last 30, 60, and 90 days
    add_30 = df_demand[df_demand['date'] >= (max_date - pd.Timedelta(days=30))].groupby(['sku_id', 'warehouse_id'])['demand_qty'].sum() / 30.0
    add_60 = df_demand[df_demand['date'] >= (max_date - pd.Timedelta(days=60))].groupby(['sku_id', 'warehouse_id'])['demand_qty'].sum() / 60.0
    add_90 = df_demand[df_demand['date'] >= (max_date - pd.Timedelta(days=90))].groupby(['sku_id', 'warehouse_id'])['demand_qty'].sum() / 90.0
    
    # We will use add_90 as our base daily demand for long-term calculations, but allow adjustments
    add_90 = add_90 * (1.0 + (demand_increase_pct / 100.0))
    
    # Calculate weekly standard deviation to derive daily demand standard deviation
    df_demand['week'] = df_demand['date'].dt.to_period('W')
    weekly_demand = df_demand.groupby(['sku_id', 'warehouse_id', 'week'])['demand_qty'].sum().reset_index()
    weekly_std = weekly_demand.groupby(['sku_id', 'warehouse_id'])['demand_qty'].std().fillna(0.0)
    
    # Daily std dev = weekly std dev / sqrt(7)
    daily_std = weekly_std / np.sqrt(7.0)
    
    # 2. Extract on-order details
    df_on_order = calculate_on_order_qty(df_po)
    
    # 3. Join all details together
    df_master = df_inventory.copy()
    
    # Merge SKU cost, lead time, category details
    sku_details = df_sku[['sku_id', 'sku_name', 'category', 'unit_cost', 'selling_price', 'moq', 
                          'case_pack_qty', 'service_level_target', 'supplier_id', 'default_lead_time_days', 
                          'criticality', 'lifecycle_status', 'abc_class', 'xyz_class']]
    df_master = df_master.merge(sku_details, on='sku_id', how='inner')
    
    # Merge supplier risk parameters
    sup_details = df_supplier[['supplier_id', 'risk_score', 'on_time_delivery_rate']]
    df_master = df_master.merge(sup_details, on='supplier_id', how='left')
    
    # Merge daily demand averages
    df_master = df_master.merge(add_30.reset_index(name='add_30'), on=['sku_id', 'warehouse_id'], how='left')
    df_master = df_master.merge(add_60.reset_index(name='add_60'), on=['sku_id', 'warehouse_id'], how='left')
    df_master = df_master.merge(add_90.reset_index(name='add_90'), on=['sku_id', 'warehouse_id'], how='left')
    df_master = df_master.merge(daily_std.reset_index(name='daily_std'), on=['sku_id', 'warehouse_id'], how='left')
    
    # Fill missing demand with zero
    for col in ['add_30', 'add_60', 'add_90', 'daily_std']:
        df_master[col] = df_master[col].fillna(0.0)
        
    # Merge on-order
    df_master = df_master.merge(df_on_order, on=['sku_id', 'warehouse_id'], how='left')
    df_master['on_order_qty'] = df_master['on_order_qty'].fillna(0).astype(int)
    
    # Calculate active Inventory Position
    # IP = on_hand + on_order - allocated - backorder
    df_master['inventory_position'] = (
        df_master['on_hand_qty'] + 
        df_master['on_order_qty'] - 
        df_master['allocated_qty'] - 
        df_master['backorder_qty']
    )
    
    # Calculate Days of Cover
    # Days cover = inventory_position / avg_daily_demand (use add_90)
    df_master['days_of_cover'] = np.where(
        df_master['add_90'] > 0.0, 
        df_master['inventory_position'] / df_master['add_90'], 
        999.0
    )
    df_master['days_of_cover'] = np.clip(df_master['days_of_cover'], -99.0, 999.0)
    
    # Calculate Safety Stock
    # Formula: safety_stock = z_score * demand_std_dev * sqrt(lead_time_days)
    # Target service level override can be applied for what-if scenarios
    def compute_ss(row):
        if row['safety_stock_override'] is not None and not np.isnan(row['safety_stock_override']):
            return float(row['safety_stock_override'])
            
        sl = target_sl_override if target_sl_override is not None else row['service_level_target']
        z = get_z_score(sl)
        
        # Adjust lead time by supplier delays if specified in scenario studio
        lt_days = max(row['default_lead_time_days'] + supplier_delay_days, 1.0)
        
        # Increase safety stock if supplier risk is high
        # Multiplier scales from 1.0 (0 risk) to 1.5 (100 risk)
        risk_multiplier = 1.0 + (row['risk_score'] / 200.0)
        
        ss = z * row['daily_std'] * np.sqrt(lt_days) * risk_multiplier
        return round(ss, 1)
        
    df_master['safety_stock'] = df_master.apply(compute_ss, axis=1)
    
    # Calculate Reorder Point (ROP)
    # ROP = (daily_demand * lead_time_days) + safety_stock
    df_master['lead_time_adjusted'] = df_master['default_lead_time_days'] + supplier_delay_days
    df_master['lead_time_adjusted'] = np.clip(df_master['lead_time_adjusted'], 1.0, 365.0)
    
    df_master['reorder_point'] = (df_master['add_90'] * df_master['lead_time_adjusted']) + df_master['safety_stock']
    df_master['reorder_point'] = np.round(df_master['reorder_point'], 1)
    
    # Suggested Order Quantity
    # Target stock = ROP + Cycle Stock (cycle stock can be based on 30 days of average demand)
    # Suggested qty = max(target_stock - inventory_position, MOQ) rounded to case pack
    cycle_stock = df_master['add_90'] * 30.0
    df_master['target_stock'] = df_master['reorder_point'] + cycle_stock
    
    def compute_suggested_order(row):
        # We only replenishment if Inventory Position is below ROP
        if row['inventory_position'] >= row['reorder_point']:
            return 0
            
        needed = row['target_stock'] - row['inventory_position']
        suggested = max(needed, row['moq'])
        
        # Round to case pack quantity if available
        cp = row['case_pack_qty']
        if cp and cp > 0:
            suggested = int(np.ceil(suggested / cp) * cp)
        else:
            suggested = int(np.ceil(suggested))
            
        return suggested
        
    df_master['suggested_order_qty'] = df_master.apply(compute_suggested_order, axis=1)
    
    # Suggested Order Date
    # If inventory position is below ROP, the order is needed immediately
    # Otherwise, project when the inventory position will fall to ROP:
    # Days until ROP = (Inventory Position - ROP) / ADD
    # Order date = Today + Days until ROP
    today = pd.Timestamp.now().date()
    def compute_suggested_date(row):
        if row['inventory_position'] < row['reorder_point']:
            return today.isoformat()
            
        if row['add_90'] <= 0.0:
            return (today + pd.Timedelta(days=90)).isoformat() # default future buffer
            
        days_until_rop = (row['inventory_position'] - row['reorder_point']) / row['add_90']
        days_until_rop = max(0, int(days_until_rop))
        return (today + pd.Timedelta(days=min(days_until_rop, 180))).isoformat()
        
    df_master['suggested_order_date'] = df_master.apply(compute_suggested_date, axis=1)
    
    return df_master
