import random
import datetime
import pandas as pd
import numpy as np
from src.database import get_db_connection

# Seed for reproducibility
random.seed(42)
np.random.seed(42)

# List of 30 fictional U.S. state/city-inspired suppliers
SUPPLIER_NAMES = [
    ("Texas Cotton Co.", "TX", "South", "Apparel"),
    ("Detroit Motor Goods", "MI", "Midwest", "Office & Lifestyle"),
    ("California Solar Supply", "CA", "West", "Electronics Accessories"),
    ("Pennsylvania Steel Works", "PA", "Northeast", "Home Goods"),
    ("Georgia Home Textiles", "GA", "South", "Home Goods"),
    ("Florida Wellness Imports", "FL", "South", "Wellness"),
    ("Ohio Packaging Group", "OH", "Midwest", "Office & Lifestyle"),
    ("New York Urban Goods", "NY", "Northeast", "Apparel"),
    ("North Carolina Furniture Supply", "NC", "South", "Home Goods"),
    ("Arizona Outdoor Gear", "AZ", "West", "Outdoor & Seasonal"),
    ("Illinois Retail Components", "IL", "Midwest", "Electronics Accessories"),
    ("Tennessee Distribution Partners", "TN", "South", "Office & Lifestyle"),
    ("Washington Tech Accessories", "WA", "West", "Electronics Accessories"),
    ("Colorado Mountain Goods", "CO", "West", "Outdoor & Seasonal"),
    ("New Jersey Port Supply", "NJ", "Northeast", "Office & Lifestyle"),
    ("Michigan Mobility Parts", "MI", "Midwest", "Electronics Accessories"),
    ("Oregon Eco Packaging", "OR", "West", "Office & Lifestyle"),
    ("Nevada Event Merchandise", "NV", "West", "Apparel"),
    ("Virginia Home Essentials", "VA", "South", "Home Goods"),
    ("Minnesota Cold Weather Goods", "MN", "Midwest", "Outdoor & Seasonal"),
    ("Wisconsin Dairy Pack", "WI", "Midwest", "Wellness"),
    ("Missouri Fulfillment Supply", "MO", "Midwest", "Office & Lifestyle"),
    ("Indiana Industrial Goods", "IN", "Midwest", "Home Goods"),
    ("Louisiana Gulf Imports", "LA", "South", "Wellness"),
    ("South Carolina Apparel Works", "SC", "South", "Apparel"),
    ("Massachusetts Smart Home Supply", "MA", "Northeast", "Electronics Accessories"),
    ("Utah Activewear Supply", "UT", "West", "Apparel"),
    ("Kentucky Storage Solutions", "KY", "South", "Home Goods"),
    ("Alabama Textile Partners", "AL", "South", "Apparel"),
    ("Kansas Farm & Home Supply", "KS", "Midwest", "Outdoor & Seasonal")
]

CATEGORIES = {
    "Apparel": ["Activewear", "Footwear", "Outerwear", "Basics"],
    "Home Goods": ["Bedding", "Bath", "Kitchenware", "Decor", "Lighting"],
    "Electronics Accessories": ["Chargers", "Cables", "Cases", "Mounts", "Smart Home"],
    "Wellness": ["Supplements", "Skincare", "Aromatherapy", "Fitness Equipment"],
    "Outdoor & Seasonal": ["Camping", "Hiking", "Patio & Garden", "Cold Weather Gear"],
    "Office & Lifestyle": ["Stationery", "Storage", "Organizers", "Travel Gear"]
}

WAREHOUSES = [
    ("WH-DAL", "Dallas Fulfillment Center", "TX", "South", 350000),
    ("WH-ATL", "Atlanta Fulfillment Center", "GA", "South", 250000),
    ("WH-CHI", "Chicago Fulfillment Center", "IL", "Midwest", 400000),
    ("WH-PHX", "Phoenix Fulfillment Center", "AZ", "West", 300000),
    ("WH-NWK", "Newark Fulfillment Center", "NJ", "Northeast", 450000)
]

def generate_suppliers():
    suppliers = []
    for idx, (name, state, region, specialty) in enumerate(SUPPLIER_NAMES):
        supplier_id = f"SUP-{idx+101:03d}"
        avg_lt = round(random.uniform(5, 45), 1)
        lt_std = round(random.uniform(0.5, avg_lt * 0.25), 1)
        otd = round(random.uniform(0.70, 0.99), 3)
        fill_rate = round(random.uniform(0.80, 0.99), 3)
        defect_rate = round(random.uniform(0.001, 0.04), 4)
        
        # Risk Score out of 100 based on lead time volatility, OTD, fill rate, and defect rate
        risk_score = int(
            (lt_std / avg_lt) * 20 + 
            (1.0 - otd) * 40 + 
            (1.0 - fill_rate) * 20 + 
            (defect_rate * 200)
        )
        risk_score = min(max(risk_score, 5), 95)
        
        single_source = 1 if random.random() < 0.15 else 0
        payment_terms = random.choice(["Net 30", "Net 45", "Net 60", "Net 90", "2/10 Net 30"])
        min_order = round(random.choice([1000, 2500, 5000, 7500, 10000, 15000]), 2)
        
        suppliers.append((
            supplier_id, name, state, region, specialty, avg_lt, lt_std,
            otd, fill_rate, defect_rate, risk_score, single_source,
            payment_terms, min_order
        ))
    return suppliers

def generate_warehouses():
    warehouses = []
    for w_id, w_name, state, region, cap in WAREHOUSES:
        util = round(random.uniform(0.55, 0.92), 3)
        warehouses.append((w_id, w_name, state, region, cap, util))
    return warehouses

def generate_skus(suppliers):
    skus = []
    supplier_ids = [s[0] for s in suppliers]
    
    sku_counter = 1001
    
    for category, subcats in CATEGORIES.items():
        for subcat in subcats:
            # Generate 10-15 SKUs per subcategory to reach 500 total
            num_skus_in_subcat = random.randint(12, 15)
            for _ in range(num_skus_in_subcat):
                sku_id = f"{category[:2].upper()}-{subcat[:3].upper()}-{sku_counter}"
                sku_name = f"{subcat} {random.choice(['Classic', 'Premium', 'Pro', 'Lite', 'Eco', 'Advanced'])} - Version {random.choice(['X', 'Y', 'Z', 'Alpha', 'Beta'])}"
                family = f"{category} {subcat}"
                channel = random.choice(["Omnichannel", "E-Commerce", "Retail Store"])
                
                # Financials
                unit_cost = round(random.uniform(3.50, 150.00), 2)
                markup = random.uniform(1.5, 3.0)
                selling_price = round(unit_cost * markup, 2)
                
                moq = random.choice([50, 100, 250, 500, 1000])
                case_pack = random.choice([10, 12, 24, 48, 100])
                
                # Service level targets: Critical gets higher, normal gets standard
                criticality = random.choice(["Low", "Medium", "High", "Critical"])
                if criticality == "Critical":
                    service_level = 0.99
                elif criticality == "High":
                    service_level = random.choice([0.98, 0.99])
                elif criticality == "Medium":
                    service_level = 0.95
                else:
                    service_level = 0.90
                    
                supplier_id = random.choice(supplier_ids)
                # Find matching supplier avg lead time
                sup_lt = [s[5] for s in suppliers if s[0] == supplier_id][0]
                default_lt = int(np.round(sup_lt + random.randint(-2, 3)))
                default_lt = max(default_lt, 2)
                
                status = random.choices(
                    ["Active", "Phase-out", "Discontinued", "Launch"],
                    weights=[0.80, 0.10, 0.05, 0.05],
                    k=1
                )[0]
                
                launch_date = (datetime.date.today() - datetime.timedelta(days=random.randint(100, 1000))).isoformat()
                seasonal = 1 if category in ["Outdoor & Seasonal", "Apparel"] and random.random() < 0.4 else 0
                
                skus.append((
                    sku_id, sku_name, category, subcat, family, channel,
                    None, None, unit_cost, selling_price, moq, case_pack,
                    service_level, supplier_id, default_lt, criticality,
                    status, launch_date, seasonal
                ))
                sku_counter += 1
                
    # Truncate or pad to exactly 500 SKUs if necessary
    random.shuffle(skus)
    skus = skus[:500]
    # Re-sort to make IDs sequential
    skus.sort(key=lambda x: x[0])
    return skus

def generate_inventory_status(skus):
    inventory = []
    warehouse_ids = [w[0] for w in WAREHOUSES]
    last_updated = datetime.datetime.now().isoformat()
    
    for sku in skus:
        sku_id = sku[0]
        # Each SKU is stored in 1 to 4 warehouses
        num_wh = random.randint(1, 4)
        active_whs = random.sample(warehouse_ids, num_wh)
        
        for wh_id in active_whs:
            # Generate random stock levels
            on_hand = random.choice([0, 10, 50, 150, 400, 800, 1500, 3000])
            on_hand = int(on_hand * random.uniform(0.6, 1.4))
            
            allocated = int(on_hand * random.uniform(0, 0.15))
            backorder = 0
            if on_hand == 0 and random.random() < 0.25:
                backorder = random.randint(5, 50)
                
            safety_override = None
            if random.random() < 0.05:
                safety_override = random.randint(50, 200)
                
            inventory.append((
                sku_id, wh_id, on_hand, allocated, backorder, safety_override, last_updated
            ))
    return inventory

def generate_demand_history(skus, inventory):
    demand = []
    # Build SKU to warehouse mapping
    sku_wh_map = {}
    for inv in inventory:
        sku_id, wh_id = inv[0], inv[1]
        if sku_id not in sku_wh_map:
            sku_wh_map[sku_id] = []
        sku_wh_map[sku_id].append(wh_id)
        
    # Generate 18 months of weekly demand (78 weeks)
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(weeks=78)
    
    date_list = [start_date + datetime.timedelta(weeks=i) for i in range(78)]
    
    for sku in skus:
        sku_id = sku[0]
        category = sku[2]
        seasonal_flag = sku[18]
        status = sku[16]
        
        # Base weekly demand level
        base_demand = random.choice([10, 25, 50, 100, 250, 500])
        
        # Determine warehouses that store this SKU
        whs = sku_wh_map.get(sku_id, ["WH-DAL"])
        
        # Distribute demand across warehouses and channels
        channels = ["Online", "Retail"]
        
        for dt in date_list:
            dt_str = dt.isoformat()
            
            # Adjust demand for seasonality, lifecycle, and random events
            week_of_year = dt.isocalendar()[1]
            season_factor = 1.0
            event = None
            promo = 0
            
            # Apply seasonality
            if seasonal_flag:
                # Summer peaks for outdoor gear
                if category == "Outdoor & Seasonal" and 18 <= week_of_year <= 32:
                    season_factor = random.uniform(1.8, 2.5)
                    event = "Summer Surge"
                # Winter peaks for apparel/cold weather
                elif category == "Apparel" and (week_of_year >= 44 or week_of_year <= 8):
                    season_factor = random.uniform(1.5, 2.2)
                    event = "Winter Rush"
            
            # Holiday season peaks for Electronics and Home Goods
            if category in ["Electronics Accessories", "Home Goods"] and 46 <= week_of_year <= 51:
                season_factor = random.uniform(2.0, 3.2)
                event = "Holiday Peak"
                
            # Random promotions
            if random.random() < 0.05:
                season_factor *= random.uniform(1.5, 2.5)
                promo = 1
                event = "Marketing Campaign"
                
            # Product lifecycle adjustments
            if status == "Phase-out":
                # Gradually decay demand
                days_since_start = (dt - start_date).days
                season_factor *= max(0.1, 1.0 - (days_since_start / 540))
            elif status == "Discontinued":
                season_factor = 0.0
            elif status == "Launch":
                # Start slow and ramp up
                days_since_start = (dt - start_date).days
                season_factor *= min(1.0, 0.1 + (days_since_start / 180))
                
            for wh_id in whs:
                for chan in channels:
                    # Allocate base demand split
                    chan_factor = 0.65 if chan == "Online" else 0.35
                    wh_factor = 1.0 / len(whs)
                    
                    mean_demand = base_demand * season_factor * chan_factor * wh_factor
                    
                    if mean_demand <= 0:
                        qty = 0
                    else:
                        qty = int(np.random.poisson(mean_demand))
                    
                    # Compute actual sales vs lost sales
                    # Simulating inventory shortages in history
                    lost_sales = 0
                    if qty > 0 and random.random() < 0.04:  # 4% chance of historical stockouts
                        lost_sales = int(qty * random.uniform(0.1, 0.5))
                        sales = qty - lost_sales
                    else:
                        sales = qty
                        
                    demand.append((
                        dt_str, sku_id, chan, wh_id, qty, sales, lost_sales, promo, event
                    ))
                    
    # The primary key constraint in database is (date, sku_id).
    # Since date is identical, let's aggregate demand by (date, sku_id) 
    # but store channel/warehouse details in aggregated format or write it to a combined list.
    # To fit the schema: PRIMARY KEY (date, sku_id)
    # We will sum the quantities per sku_id per date for the database insert.
    df_temp = pd.DataFrame(demand, columns=['date', 'sku_id', 'channel', 'warehouse_id', 'demand_qty', 'sales_qty', 'lost_sales_qty', 'promotion_flag', 'seasonality_event'])
    
    # Aggregate to match the PK constraint
    df_agg = df_temp.groupby(['date', 'sku_id']).agg({
        'channel': lambda x: 'Omnichannel' if len(set(x)) > 1 else list(x)[0],
        'warehouse_id': lambda x: list(x)[0] if len(set(x)) == 1 else 'Multiple',
        'demand_qty': 'sum',
        'sales_qty': 'sum',
        'lost_sales_qty': 'sum',
        'promotion_flag': 'max',
        'seasonality_event': lambda x: ', '.join(set(v for v in x if isinstance(v, str))) if any(isinstance(v, str) for v in x) else None
    }).reset_index()
    
    return [tuple(x) for x in df_agg.values]

def generate_purchase_orders(skus, suppliers):
    pos = []
    warehouse_ids = [w[0] for w in WAREHOUSES]
    
    # 1000 POs over the last 12 months
    base_date = datetime.date.today() - datetime.timedelta(days=365)
    
    po_counter = 50001
    
    for i in range(1000):
        po_id = f"PO-{po_counter}"
        po_counter += 1
        
        sku = random.choice(skus)
        sku_id = sku[0]
        sup_id = sku[13]
        wh_id = random.choice(warehouse_ids)
        
        # Find matching supplier parameters
        sup_info = [s for s in suppliers if s[0] == sup_id][0]
        avg_lt = sup_info[5]
        lt_std = sup_info[6]
        otd = sup_info[7]
        fill_rate = sup_info[8]
        
        order_days_ago = random.randint(10, 350)
        order_dt = base_date + datetime.timedelta(days=order_days_ago)
        
        # Expected arrival
        exp_dt = order_dt + datetime.timedelta(days=int(np.ceil(avg_lt)))
        
        # Order Qty
        moq = sku[10]
        order_qty = int(moq * random.choice([1, 1.5, 2, 3, 5]))
        
        # Status assignment
        if exp_dt < datetime.date.today():
            # Completed PO
            status = "Received"
            # OTD rate controls if it was delayed
            if random.random() < otd:
                # On time or early
                delay = int(np.random.normal(0, max(lt_std * 0.5, 0.5)))
                delay = min(delay, 0) # must be <= 0
            else:
                # Delayed
                delay = int(np.random.normal(max(lt_std, 2.0), lt_std))
                delay = max(delay, 1)
                
            act_dt = exp_dt + datetime.timedelta(days=delay)
            if act_dt > datetime.date.today():
                # If delay pushed it to the future, it should still be open
                status = "In Transit"
                act_dt_str = None
                received_qty = 0
            else:
                act_dt_str = act_dt.isoformat()
                # Fill rate controls received quantity
                if random.random() < fill_rate:
                    received_qty = order_qty
                else:
                    received_qty = int(order_qty * random.uniform(0.8, 0.98))
        else:
            # Future PO (Open or In Transit)
            status = "In Transit" if random.random() < 0.7 else "Open"
            act_dt_str = None
            received_qty = 0
            
        pos.append((
            po_id, sku_id, sup_id, wh_id, order_dt.isoformat(),
            exp_dt.isoformat(), act_dt_str, order_qty, received_qty, status
        ))
        
    return pos

def generate_bom_kits(skus):
    bom = []
    # Identify component candidates (low cost, case packs, high inventory)
    components = [s for s in skus if s[8] < 25.0]  # cost < $25
    kit_candidates = [s for s in skus if s[8] > 40.0]  # cost > $40
    
    # Generate exactly 50 kits
    parent_ids = set()
    
    kit_names = [
        "Back to School Desk Kit", "Home Office Set", "Summer Hydration Bundle",
        "Executive Station Pack", "Winter Warmth Bundle", "Eco Kitchen Set",
        "Ultimate Cable Organizer Kit", "Outdoor Camping Bundle", "Morning Essentials Wellness Pack",
        "Smart Home Security Kit", "Deluxe Stationery Set", "Omni Traveler Pack",
        "Classic Wellness Bundle", "Outdoor Patio Lighting Set", "Advanced Cable Pack",
        "Minimalist Desk Organizer Kit", "Cozy Bedding Pack", "Omni Activewear Kit"
    ]
    
    for i in range(50):
        # Pick parent SKU
        if i < len(kit_candidates):
            parent_sku = kit_candidates[i]
        else:
            parent_sku = random.choice(skus)
            
        parent_id = parent_sku[0]
        if parent_id in parent_ids:
            continue
        parent_ids.add(parent_id)
        
        kit_name = f"{random.choice(kit_names)} - {random.choice(['Premium', 'Deluxe', 'Essential'])}"
        
        # Pick 3 to 5 unique components
        num_components = random.randint(3, 5)
        kit_comps = random.sample(components, num_components)
        
        for comp in kit_comps:
            comp_id = comp[0]
            if comp_id == parent_id:
                continue
            comp_qty = random.choice([1, 1, 1, 2, 3])
            bom.append((
                parent_id, comp_id, comp_qty, kit_name, 1
            ))
            
    return bom

def generate_all_demo_data():
    """
    Populates SQLite tables with generated demo data.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Suppliers
    suppliers = generate_suppliers()
    cursor.executemany("""
    INSERT OR REPLACE INTO supplier_master 
    (supplier_id, supplier_name, state, region, product_specialty, avg_lead_time_days, 
     lead_time_std_days, on_time_delivery_rate, fill_rate, defect_rate, risk_score, 
     single_source_flag, payment_terms, minimum_order_value)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, suppliers)
    
    # 2. Warehouses
    warehouses = generate_warehouses()
    cursor.executemany("""
    INSERT OR REPLACE INTO warehouse_master 
    (warehouse_id, warehouse_name, state, region, storage_capacity_units, current_utilization_percent)
    VALUES (?,?,?,?,?,?)
    """, warehouses)
    
    # 3. SKUs
    skus = generate_skus(suppliers)
    cursor.executemany("""
    INSERT OR REPLACE INTO sku_master 
    (sku_id, sku_name, category, subcategory, product_family, channel, abc_class, xyz_class,
     unit_cost, selling_price, moq, case_pack_qty, service_level_target, supplier_id, 
     default_lead_time_days, criticality, lifecycle_status, launch_date, seasonal_flag)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, skus)
    
    # 4. Inventory
    inventory = generate_inventory_status(skus)
    cursor.executemany("""
    INSERT OR REPLACE INTO inventory_status 
    (sku_id, warehouse_id, on_hand_qty, allocated_qty, backorder_qty, safety_stock_override, last_updated)
    VALUES (?,?,?,?,?,?,?)
    """, inventory)
    
    # 5. Demand
    demand = generate_demand_history(skus, inventory)
    cursor.executemany("""
    INSERT OR REPLACE INTO demand_history 
    (date, sku_id, channel, warehouse_id, demand_qty, sales_qty, lost_sales_qty, promotion_flag, seasonality_event)
    VALUES (?,?,?,?,?,?,?,?,?)
    """, demand)
    
    # 6. Purchase Orders
    pos = generate_purchase_orders(skus, suppliers)
    cursor.executemany("""
    INSERT OR REPLACE INTO purchase_orders 
    (po_id, sku_id, supplier_id, warehouse_id, order_date, expected_arrival_date, 
     actual_arrival_date, order_qty, received_qty, status)
    VALUES (?,?,?,?,?,?,?,?,?,?)
    """, pos)
    
    # 7. BOM/Kits
    bom = generate_bom_kits(skus)
    cursor.executemany("""
    INSERT OR REPLACE INTO bom_or_kit_structure 
    (parent_sku_id, component_sku_id, component_qty, kit_name, active_flag)
    VALUES (?,?,?,?,?)
    """, bom)
    
    conn.commit()
    conn.close()
    
    print("Fictional demo data generated and loaded into SQLite successfully.")
