import io
import pandas as pd
import numpy as np

# Required column schemas for database tables
SCHEMAS = {
    'sku_master': {
        'required': ['sku_id', 'sku_name', 'category', 'unit_cost', 'selling_price', 'moq', 'default_lead_time_days', 'service_level_target'],
        'optional': ['subcategory', 'product_family', 'channel', 'abc_class', 'xyz_class', 'case_pack_qty', 'supplier_id', 'criticality', 'lifecycle_status', 'launch_date', 'seasonal_flag'],
        'sample': pd.DataFrame([{
            'sku_id': 'AP-SWE-1001',
            'sku_name': 'Classic Fleece Hoodie',
            'category': 'Apparel',
            'subcategory': 'Activewear',
            'product_family': 'Apparel Activewear',
            'channel': 'Omnichannel',
            'abc_class': 'A',
            'xyz_class': 'X',
            'unit_cost': 18.50,
            'selling_price': 45.00,
            'moq': 100,
            'case_pack_qty': 12,
            'service_level_target': 0.95,
            'supplier_id': 'SUP-101',
            'default_lead_time_days': 14,
            'criticality': 'High',
            'lifecycle_status': 'Active',
            'launch_date': '2024-01-15',
            'seasonal_flag': 0
        }])
    },
    'inventory_status': {
        'required': ['sku_id', 'warehouse_id', 'on_hand_qty'],
        'optional': ['allocated_qty', 'backorder_qty', 'safety_stock_override', 'last_updated'],
        'sample': pd.DataFrame([{
            'sku_id': 'AP-SWE-1001',
            'warehouse_id': 'WH-DAL',
            'on_hand_qty': 450,
            'allocated_qty': 25,
            'backorder_qty': 0,
            'safety_stock_override': None,
            'last_updated': '2026-05-26T19:11:32'
        }])
    },
    'demand_history': {
        'required': ['date', 'sku_id', 'demand_qty'],
        'optional': ['channel', 'warehouse_id', 'sales_qty', 'lost_sales_qty', 'promotion_flag', 'seasonality_event'],
        'sample': pd.DataFrame([{
            'date': '2025-01-06',
            'sku_id': 'AP-SWE-1001',
            'channel': 'Omnichannel',
            'warehouse_id': 'WH-DAL',
            'demand_qty': 45,
            'sales_qty': 45,
            'lost_sales_qty': 0,
            'promotion_flag': 0,
            'seasonality_event': None
        }])
    },
    'supplier_master': {
        'required': ['supplier_id', 'supplier_name', 'avg_lead_time_days', 'risk_score'],
        'optional': ['state', 'region', 'product_specialty', 'lead_time_std_days', 'on_time_delivery_rate', 'fill_rate', 'defect_rate', 'single_source_flag', 'payment_terms', 'minimum_order_value'],
        'sample': pd.DataFrame([{
            'supplier_id': 'SUP-101',
            'supplier_name': 'Texas Cotton Co.',
            'state': 'TX',
            'region': 'South',
            'product_specialty': 'Apparel',
            'avg_lead_time_days': 15.0,
            'lead_time_std_days': 2.5,
            'on_time_delivery_rate': 0.94,
            'fill_rate': 0.97,
            'defect_rate': 0.005,
            'risk_score': 15,
            'single_source_flag': 0,
            'payment_terms': 'Net 30',
            'minimum_order_value': 1000.00
        }])
    },
    'purchase_orders': {
        'required': ['po_id', 'sku_id', 'supplier_id', 'warehouse_id', 'order_qty', 'status'],
        'optional': ['order_date', 'expected_arrival_date', 'actual_arrival_date', 'received_qty'],
        'sample': pd.DataFrame([{
            'po_id': 'PO-50001',
            'sku_id': 'AP-SWE-1001',
            'supplier_id': 'SUP-101',
            'warehouse_id': 'WH-DAL',
            'order_date': '2026-05-10',
            'expected_arrival_date': '2026-05-25',
            'actual_arrival_date': None,
            'order_qty': 200,
            'received_qty': 0,
            'status': 'In Transit'
        }])
    },
    'bom_or_kit_structure': {
        'required': ['parent_sku_id', 'component_sku_id', 'component_qty'],
        'optional': ['kit_name', 'active_flag'],
        'sample': pd.DataFrame([{
            'parent_sku_id': 'KT-DESK-001',
            'component_sku_id': 'AP-SWE-1001',
            'component_qty': 1,
            'kit_name': 'Back to School Desk Kit',
            'active_flag': 1
        }])
    }
}

def validate_dataframe(df, table_name):
    """
    Validates an uploaded dataframe against the schema specifications.
    Returns (is_valid, error_message, df_cleaned).
    """
    if table_name not in SCHEMAS:
        return False, f"Unknown schema table '{table_name}'", df
        
    schema = SCHEMAS[table_name]
    required_cols = schema['required']
    
    # Standardize column headers to lowercase & strip whitespace
    df.columns = [str(c).strip().lower() for c in df.columns]
    required_normalized = [c.lower() for c in required_cols]
    
    # Identify missing headers
    missing_cols = [orig for orig, norm in zip(required_cols, required_normalized) if norm not in df.columns]
    
    if missing_cols:
        return (
            False, 
            f"Missing required columns: {', '.join(missing_cols)}. Expected: {', '.join(required_cols)}",
            df
        )
        
    # Build clean dataframe with schema column names
    clean_df = pd.DataFrame()
    
    # 1. Map columns back to original casing
    for orig, norm in zip(required_cols + schema['optional'], [c.lower() for c in required_cols + schema['optional']]):
        matching_cols = [c for c in df.columns if c == norm]
        if matching_cols:
            clean_df[orig] = df[matching_cols[0]]
        else:
            # Optional column not provided, fill with default null
            clean_df[orig] = np.nan
            
    # Simple data conversions
    # SKU and other identifiers should be strings, trim strings
    id_cols = ['sku_id', 'parent_sku_id', 'component_sku_id', 'supplier_id', 'warehouse_id', 'po_id']
    for col in id_cols:
        if col in clean_df.columns:
            clean_df[col] = clean_df[col].astype(str).str.strip()
            
    return True, "", clean_df

def get_template_csv(table_name):
    """
    Returns CSV bytes of the template file for download.
    """
    if table_name not in SCHEMAS:
        return b""
        
    df_sample = SCHEMAS[table_name]['sample']
    output = io.StringIO()
    df_sample.to_csv(output, index=False)
    return output.getvalue().encode('utf-8')
