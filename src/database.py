import sqlite3
import os
import pandas as pd

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
DB_PATH = os.path.join(DB_DIR, 'supplypilot.db')

def get_db_connection():
    """
    Establish a connection to the SQLite database.
    """
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Creates the tables if they don't already exist.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. sku_master
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sku_master (
        sku_id TEXT PRIMARY KEY,
        sku_name TEXT NOT NULL,
        category TEXT NOT NULL,
        subcategory TEXT,
        product_family TEXT,
        channel TEXT,
        abc_class TEXT,
        xyz_class TEXT,
        unit_cost REAL NOT NULL,
        selling_price REAL NOT NULL,
        moq INTEGER NOT NULL,
        case_pack_qty INTEGER,
        service_level_target REAL NOT NULL,
        supplier_id TEXT,
        default_lead_time_days INTEGER NOT NULL,
        criticality TEXT,
        lifecycle_status TEXT,
        launch_date TEXT,
        seasonal_flag INTEGER DEFAULT 0
    )
    """)
    
    # 2. inventory_status
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory_status (
        sku_id TEXT NOT NULL,
        warehouse_id TEXT NOT NULL,
        on_hand_qty INTEGER NOT NULL DEFAULT 0,
        allocated_qty INTEGER NOT NULL DEFAULT 0,
        backorder_qty INTEGER NOT NULL DEFAULT 0,
        safety_stock_override INTEGER,
        last_updated TEXT,
        PRIMARY KEY (sku_id, warehouse_id)
    )
    """)
    
    # 3. demand_history
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS demand_history (
        date TEXT NOT NULL,
        sku_id TEXT NOT NULL,
        channel TEXT,
        warehouse_id TEXT,
        demand_qty INTEGER NOT NULL DEFAULT 0,
        sales_qty INTEGER NOT NULL DEFAULT 0,
        lost_sales_qty INTEGER NOT NULL DEFAULT 0,
        promotion_flag INTEGER DEFAULT 0,
        seasonality_event TEXT,
        PRIMARY KEY (date, sku_id)
    )
    """)
    
    # 4. supplier_master
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS supplier_master (
        supplier_id TEXT PRIMARY KEY,
        supplier_name TEXT NOT NULL,
        state TEXT,
        region TEXT,
        product_specialty TEXT,
        avg_lead_time_days REAL NOT NULL,
        lead_time_std_days REAL NOT NULL,
        on_time_delivery_rate REAL NOT NULL,
        fill_rate REAL NOT NULL,
        defect_rate REAL NOT NULL,
        risk_score REAL NOT NULL,
        single_source_flag INTEGER DEFAULT 0,
        payment_terms TEXT,
        minimum_order_value REAL NOT NULL DEFAULT 0.0
    )
    """)
    
    # 5. purchase_orders
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS purchase_orders (
        po_id TEXT PRIMARY KEY,
        sku_id TEXT NOT NULL,
        supplier_id TEXT NOT NULL,
        warehouse_id TEXT NOT NULL,
        order_date TEXT NOT NULL,
        expected_arrival_date TEXT NOT NULL,
        actual_arrival_date TEXT,
        order_qty INTEGER NOT NULL,
        received_qty INTEGER,
        status TEXT NOT NULL
    )
    """)
    
    # 6. warehouse_master
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS warehouse_master (
        warehouse_id TEXT PRIMARY KEY,
        warehouse_name TEXT NOT NULL,
        state TEXT,
        region TEXT,
        storage_capacity_units INTEGER,
        current_utilization_percent REAL
    )
    """)
    
    # 7. bom_or_kit_structure
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bom_or_kit_structure (
        parent_sku_id TEXT NOT NULL,
        component_sku_id TEXT NOT NULL,
        component_qty INTEGER NOT NULL DEFAULT 1,
        kit_name TEXT,
        active_flag INTEGER DEFAULT 1,
        PRIMARY KEY (parent_sku_id, component_sku_id)
    )
    """)
    
    # 8. recommendation_output
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recommendation_output (
        sku_id TEXT NOT NULL,
        warehouse_id TEXT NOT NULL,
        risk_level TEXT NOT NULL,
        inventory_position INTEGER,
        days_of_cover REAL,
        reorder_point REAL,
        safety_stock REAL,
        suggested_order_qty INTEGER,
        suggested_order_date TEXT,
        suggested_action TEXT,
        reason_code TEXT,
        estimated_stockout_value REAL,
        excess_inventory_value REAL,
        created_at TEXT,
        PRIMARY KEY (sku_id, warehouse_id)
    )
    """)
    
    conn.commit()
    conn.close()

def is_db_empty():
    """
    Check if the sku_master table has any records.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sku_master")
    count = cursor.fetchone()[0]
    conn.close()
    return count == 0

def load_dataframe_from_table(table_name):
    """
    Retrieves data from a specific table as a pandas DataFrame.
    """
    conn = get_db_connection()
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    conn.close()
    return df

def clear_all_tables():
    """
    Clears all tables in the database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    tables = [
        'sku_master', 'inventory_status', 'demand_history', 'supplier_master', 
        'purchase_orders', 'warehouse_master', 'bom_or_kit_structure', 'recommendation_output'
    ]
    for table in tables:
        cursor.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()

def get_full_dataset():
    """
    Helper function to load the entire database as a dictionary of dataframes.
    """
    return {
        'sku_master': load_dataframe_from_table('sku_master'),
        'inventory_status': load_dataframe_from_table('inventory_status'),
        'demand_history': load_dataframe_from_table('demand_history'),
        'supplier_master': load_dataframe_from_table('supplier_master'),
        'purchase_orders': load_dataframe_from_table('purchase_orders'),
        'warehouse_master': load_dataframe_from_table('warehouse_master'),
        'bom_or_kit_structure': load_dataframe_from_table('bom_or_kit_structure'),
        'recommendation_output': load_dataframe_from_table('recommendation_output'),
    }
