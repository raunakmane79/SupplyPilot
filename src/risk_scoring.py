import numpy as np
import pandas as pd

def calculate_stockout_risk_score(row):
    """
    Computes a stockout risk score from 0 to 100 for a SKU-warehouse record.
    """
    # 1. Days Cover vs Lead Time (30%)
    lt = max(row['lead_time_adjusted'], 1.0)
    doc = row['days_of_cover']
    
    if doc < 0:
        doc_score = 100.0
    elif doc == 0:
        doc_score = 100.0
    elif doc < lt:
        # Scale between 30 and 100 based on coverage ratio
        doc_score = 100.0 * (1.0 - (doc / lt))
    else:
        doc_score = 0.0
        
    # 2. Inventory Position vs Reorder Point (25%)
    rop = max(row['reorder_point'], 1.0)
    ip = row['inventory_position']
    
    if ip <= 0:
        ip_score = 100.0
    elif ip < rop:
        ip_score = 100.0 * (1.0 - (ip / rop))
    else:
        ip_score = 0.0
        
    # 3. Demand Trend and Volatility (15%)
    # XYZ Class weight: Z=100, Y=60, X=20
    xyz = row.get('xyz_class', 'Z')
    xyz_weight = {'Z': 100.0, 'Y': 60.0, 'X': 20.0}.get(xyz, 50.0)
    
    # Trend weight: ratio of short-term (30d) vs long-term (90d) average daily demand
    add30 = row.get('add_30', 0.0)
    add90 = row.get('add_90', 0.0)
    if add90 > 0:
        trend_ratio = add30 / add90
        trend_score = min(max((trend_ratio - 1.0) * 100.0, 0.0), 100.0)
    else:
        trend_score = 50.0
        
    demand_score = (0.5 * xyz_weight) + (0.5 * trend_score)
    
    # 4. Supplier Reliability (15%)
    # Uses supplier risk score (already 0-100)
    supplier_score = float(row.get('risk_score', 50.0))
    
    # 5. ABC/Criticality (10%)
    abc = row.get('abc_class', 'C')
    abc_val = {'A': 100.0, 'B': 60.0, 'C': 20.0}.get(abc, 20.0)
    
    crit = row.get('criticality', 'Medium')
    crit_val = {'Critical': 100.0, 'High': 80.0, 'Medium': 50.0, 'Low': 20.0}.get(crit, 50.0)
    
    criticality_score = (0.5 * abc_val) + (0.5 * crit_val)
    
    # 6. Open PO Delay Risk (5%)
    # If inventory position is below reorder point and we have no open POs
    on_hand = row['on_hand_qty']
    on_order = row['on_order_qty']
    
    if on_hand < rop and on_order == 0:
        po_risk = 90.0 # High risk since no replenishment in transit
    elif on_hand < rop and on_order > 0:
        # Check if there is an overdue in-transit PO
        # Simulated based on OTD rates
        otd = row.get('on_time_delivery_rate', 0.9)
        po_risk = 100.0 * (1.0 - otd) # delay probability
    else:
        po_risk = 10.0
        
    # Calculate weighted score
    final_score = (
        (0.30 * doc_score) + 
        (0.25 * ip_score) + 
        (0.15 * demand_score) + 
        (0.15 * supplier_score) + 
        (0.10 * criticality_score) + 
        (0.05 * po_risk)
    )
    
    return int(np.clip(final_score, 0, 100))

def classify_risk_level(score):
    """
    Categorizes the risk score into standard risk levels.
    """
    if score >= 80:
        return "Critical"
    elif score >= 60:
        return "High"
    elif score >= 40:
        return "Medium"
    elif score >= 20:
        return "Low"
    else:
        return "Healthy"

def compute_excess_inventory(row):
    """
    Determines if the SKU-warehouse combination is at risk of excess inventory.
    Returns the estimated excess quantity and value in dollars.
    """
    on_hand = row['on_hand_qty']
    rop = row['reorder_point']
    unit_cost = row['unit_cost']
    doc = row['days_of_cover']
    status = row['lifecycle_status']
    
    # Excess inventory conditions:
    # 1. Days of cover exceeds 90 days (standard e-commerce threshold)
    # 2. On-hand inventory is significantly greater than ROP + 30 days demand
    # 3. Demands are declining or SKU is phase-out/discontinued
    
    # Target maximum stock we want to hold: ROP + 30 days of cycle stock
    max_target_stock = rop + (row['add_90'] * 30.0)
    
    excess_qty = 0
    if doc > 90.0 or (on_hand > max_target_stock and on_hand > 50):
        # Quantity exceeding the max target stock
        excess_qty = max(0, int(on_hand - max_target_stock))
        
    # If the product is phased-out or discontinued, all on-hand stock is potentially excess
    if status in ['Phase-out', 'Discontinued']:
        excess_qty = max(excess_qty, on_hand)
        
    excess_val = round(excess_qty * unit_cost, 2)
    return excess_qty, excess_val
