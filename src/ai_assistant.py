import streamlit as st
import datetime
import pandas as pd

def get_openai_client(api_key):
    """
    Initializes OpenAI client if key is provided.
    """
    try:
        import openai
        return openai.OpenAI(api_key=api_key)
    except ImportError:
        return None

def explain_sku_risk_ai(row, open_pos, api_key=None):
    """
    Provides a detailed summary of a single SKU's stockout or excess risk.
    """
    sku_id = row['sku_id']
    sku_name = row['sku_name']
    wh = row['warehouse_id']
    doc = row['days_of_cover']
    lt = row['lead_time_adjusted']
    rop = row['reorder_point']
    ip = row['inventory_position']
    on_hand = row['on_hand_qty']
    allocated = row['allocated_qty']
    backorder = row['backorder_qty']
    on_order = row['on_order_qty']
    suggested_qty = row['suggested_order_qty']
    suggested_date = row['suggested_order_date']
    reason = row['reason_code']
    action = row['suggested_action']
    stockout_exposure = row['estimated_stockout_value']
    excess_val = row['excess_inventory_value']
    
    # Supplier Details
    supplier_name = row.get('supplier_name', 'Default Supplier')
    supplier_otd = row.get('on_time_delivery_rate', 0.95)
    supplier_risk = row.get('risk_score', 20.0)
    
    # Check if there is an active PO
    po_summary = ""
    if not open_pos.empty:
        po_details = []
        for _, po in open_pos.iterrows():
            po_details.append(f"{po['po_id']} ({po['order_qty']} units expected {po['expected_arrival_date']})")
        po_summary = "Active open purchase orders: " + ", ".join(po_details) + "."
    else:
        po_summary = "There are no open purchase orders currently in transit for this SKU."

    prompt_context = f"""
    SKU Details:
    - SKU ID: {sku_id}
    - SKU Name: {sku_name}
    - Warehouse: {wh}
    - Inventory Status: On Hand: {on_hand}, Allocated: {allocated}, Backorder: {backorder}, On Order: {on_order}
    - Calculated Position: Inventory Position: {ip}, Days of Cover: {doc:.1f} days, Reorder Point (ROP): {rop:.1f}
    - Demand details: 30-day average: {row['add_30']:.2f} units/day, 90-day average: {row['add_90']:.2f} units/day
    - Supplier performance: {supplier_name} (OTD Rate: {supplier_otd * 100:.1f}%, Risk Score: {supplier_risk}/100, Lead Time: {lt} days)
    - Open PO summary: {po_summary}
    - Calculated Action: {action} (Reason: {reason})
    - Financial impact: Estimated Stockout Exposure: ${stockout_exposure:,.2f}, Excess Inventory Value: ${excess_val:,.2f}
    - Recommended order quantity: {suggested_qty} units on {suggested_date}
    """
    
    if api_key:
        client = get_openai_client(api_key)
        if client:
            try:
                response = client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": "You are a professional senior supply chain planner. Provide a concise, highly analytical risk explanation of this SKU using calculated metrics only. Do not hallucinate or invent facts. Focus on safety stock, lead times, and financial exposure."},
                        {"role": "user", "content": f"Analyze the following SKU:\n{prompt_context}"}
                    ]
                )
                return response.choices[0].message.content
            except Exception as e:
                # Fall back on error
                pass
                
    # Deterministic Rule-Based Fallback
    if reason == "EXCESS_STOCK":
        analysis = (
            f"**Excess Inventory Warning:** {sku_name} ({sku_id}) in {wh} has a severe overstock situation, currently "
            f"covering **{doc:.0f} days** of demand (exceeding the standard 90-day retail threshold). "
            f"The on-hand inventory of {on_hand} units represents a working capital drag of **${excess_val:,.2f}** in excess value. "
            f"This is driven by a slowing demand trend, where the short-term average ({row['add_30']:.1f} units/day) has fallen below "
            f"the 90-day baseline ({row['add_90']:.1f} units/day). "
            f"**Recommendation:** Stop replenishment orders immediately. Consider triggering a marketing promotion, listing "
            f"on online channels at a discount, or executing stock redistribution to other regional fulfillment centers."
        )
    elif doc <= 0:
        analysis = (
            f"**Stockout Active:** {sku_name} ({sku_id}) in {wh} is currently stocked out or has backordered units "
            f"amounting to {backorder} units. The inventory position of {ip} units is severely below the reorder point of {rop:.0f} units. "
            f"{po_summary} "
        )
        if on_order > 0:
            analysis += (
                f"Although open order volume is in transit, the expected arrival times leave an active supply gap. "
                f"The estimated lost revenue exposure is **${stockout_exposure:,.2f}**. "
                f"**Recommendation:** Contact {supplier_name} immediately to expedite the open POs, and review logisitics routing for emergency express shipping."
            )
        else:
            analysis += (
                f"No open purchase orders exist. A replenishment of **{suggested_qty} units** is required immediately to cover MOQ and build back safety stock. "
                f"The total lost sales exposure is **${stockout_exposure:,.2f}**. "
                f"**Recommendation:** Place an immediate order for {suggested_qty} units."
            )
    elif doc < lt:
        gap_days = lt - doc
        analysis = (
            f"**Critical Lead-Time Breach:** {sku_name} ({sku_id}) in {wh} has only **{doc:.1f} days of cover**, which is "
            f"shorter than the supplier's adjusted lead time of **{lt:.0f} days**. This means the current inventory position "
            f"will be exhausted **{gap_days:.1f} days** before a new standard purchase order can arrive. "
            f"The estimated financial risk of this stockout gap is **${stockout_exposure:,.2f}** in lost sales. "
            f"{po_summary} "
            f"**Recommendation:** Execute the suggested replenishment order of **{suggested_qty} units** immediately. "
            f"If an open PO is active, contact {supplier_name} (Risk Score: {supplier_risk}/100, OTD: {supplier_otd*100:.1f}%) "
            f"to request priority processing."
        )
    elif ip < rop:
        analysis = (
            f"**Reorder Point Triggered:** {sku_name} ({sku_id}) in {wh} has fallen below its reorder point of {rop:.0f} units. "
            f"Current inventory position is {ip} units (On Hand: {on_hand}, On Order: {on_order}) representing **{doc:.1f} days of cover**. "
            f"The supplier lead time is {lt:.0f} days with standard deviation of {row.get('lead_time_std_days', 2.0)} days. "
            f"**Recommendation:** Place a standard replenishment order for the suggested quantity of **{suggested_qty} units** "
            f"(adjusted to case pack and supplier MOQ) to restore inventory to the target service level of {row['service_level_target']*100:.0f}%."
        )
    else:
        analysis = (
            f"**Stock Profile Healthy:** {sku_name} ({sku_id}) in {wh} is in a stable inventory position. "
            f"The current inventory position of {ip} units is above the reorder point of {rop:.0f} units, providing "
            f"**{doc:.1f} days of cover**. Demand variability (XYZ class: {row['xyz_class']}) and supplier reliability "
            f"(OTD: {supplier_otd*100:.1f}%) are well balanced within the calculated safety stock of {row['safety_stock']:.0f} units. "
            f"**Recommendation:** No planning action required this week. Monitor weekly demand trends."
        )
        
    return analysis

def create_weekly_action_plan_ai(df_recs, df_suppliers, api_key=None):
    """
    Generates a strategic executive planning and weekly action plan.
    """
    total_recs = len(df_recs)
    order_recs = df_recs[df_recs['suggested_action'] == 'Place Order']
    expedite_recs = df_recs[df_recs['suggested_action'] == 'Expedite PO']
    excess_recs = df_recs[df_recs['suggested_action'].isin(['Redistribute Stock', 'Liquidate/Promote'])]
    
    total_order_val = sum(order_recs['suggested_order_qty'] * order_recs['unit_cost'])
    total_stockout_val = df_recs['estimated_stockout_value'].sum()
    total_excess_val = df_recs['excess_inventory_value'].sum()
    
    top_critical = df_recs[df_recs['risk_level'] == 'Critical'].sort_values(by='estimated_stockout_value', ascending=False).head(3)
    critical_list = []
    for _, row in top_critical.iterrows():
        critical_list.append(f"- {row['sku_id']} ({row['sku_name']}) in {row['warehouse_id']}: Stockout Exposure ${row['estimated_stockout_value']:,.2f}, Days Cover: {row['days_of_cover']:.1f}")
        
    prompt_context = f"""
    Portfolio Planning Context:
    - Active SKUs under review: {total_recs}
    - Suggested Orders: {len(order_recs)} replenishment orders totaling ${total_order_val:,.2f} in value.
    - Suggested Expedites: {len(expedite_recs)} overdue/critical open POs requiring expediting.
    - Excess Overstock: {len(excess_recs)} locations with excess stock totaling ${total_excess_val:,.2f}.
    - Total Portfolio Stockout Exposure: ${total_stockout_val:,.2f}.
    - Top 3 Critical Stockout Risks:
    {"\n".join(critical_list) if critical_list else "None"}
    """
    
    if api_key:
        client = get_openai_client(api_key)
        if client:
            try:
                response = client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": "You are a Chief Supply Chain Officer. Write a professional, executive-level Weekly Action Plan. Structure it with clear, actionable bullet points categorizing replenishment priorities, supplier risks, and working capital recovery."},
                        {"role": "user", "content": f"Create a weekly action plan based on these metrics:\n{prompt_context}"}
                    ]
                )
                return response.choices[0].message.content
            except Exception as e:
                pass
                
    # Rule-Based Fallback
    plan = f"""### SupplyPilot Weekly Executive Action Plan
**Report Generated:** {datetime.date.today().strftime('%B %d, %Y')}
**Author:** SupplyPilot AI Decision Engine

---

#### 1. Replenishment & Capital Allocation
- **Replenishment Orders:** Trigger **{len(order_recs)} purchase orders** this week. This requires a capital allocation of **${total_order_val:,.2f}**. 
- **Fulfillment Urgency:** Prioritize release of orders for critical SKUs, focusing on items that have breached their lead-time safety stock threshold.
- **Stockout Prevention:** Successful execution of these orders will mitigate up to **${total_stockout_val:,.2f}** in projected lost sales revenue.

#### 2. Open Purchase Order Expediting
- **Expedite List:** There are **{len(expedite_recs)} open POs** that require active intervention. These SKUs are either currently stocked out or will stock out before the default delivery date.
- **Supplier Contacts:** Planners should reach out to the suppliers for these critical orders to verify logistics transit times and discuss partial air-freight options where possible.

#### 3. Working Capital Recovery (Excess Stock)
- **Excess Value:** We have **${total_excess_val:,.2f}** tied up in non-moving or overstocked inventory across **{len(excess_recs)} locations**.
- **Actions:** 
  - Halt further replenishment for all SKUs flagged with `EXCESS_STOCK`.
  - Coordinate with the marketing team to launch promotion channels on the e-commerce store for categories with over 90 days of cover.
  - Evaluate inter-warehouse transfers from Newark and Dallas to Western regional fulfillment centers to balance stock without purchasing.

#### 4. Top 3 SKU-Level Interventions
{chr(10).join(critical_list) if critical_list else "- No critical stockout risks identified."}
"""
    return plan

def summarize_supplier_risk_ai(df_suppliers, df_sku, df_po, api_key=None):
    """
    Provides a summary scorecard of supplier reliability and regional risks.
    """
    total_suppliers = len(df_suppliers)
    risky_suppliers = df_suppliers[df_suppliers['risk_score'] > 60]
    avg_risk = df_suppliers['risk_score'].mean()
    single_source = df_suppliers[df_suppliers['single_source_flag'] == 1]
    
    delayed_pos = df_po[(df_po['status'] == 'In Transit') & 
                        (pd.to_datetime(df_po['expected_arrival_date']) < pd.Timestamp.now())]
                        
    prompt_context = f"""
    Supplier Health Metrics:
    - Total Active Suppliers: {total_suppliers}
    - Portfolio Average Risk Score: {avg_risk:.1f}/100
    - Risky Suppliers (>60 score): {len(risky_suppliers)} ({', '.join(risky_suppliers['supplier_name'].tolist())})
    - Single-Source Vulnerabilities: {len(single_source)} suppliers manage sole product lines.
    - Active Delayed POs: {len(delayed_pos)} POs in transit past expected date.
    """
    
    if api_key:
        client = get_openai_client(api_key)
        if client:
            try:
                response = client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": "You are a Procurement Specialist. Write a brief supplier risk assessment summary. Identify which suppliers pose the greatest bottleneck risk, discuss single-source risks, and propose contract reviews."},
                        {"role": "user", "content": f"Summarize supplier risk for:\n{prompt_context}"}
                    ]
                )
                return response.choices[0].message.content
            except Exception as e:
                pass
                
    # Rule-Based Fallback
    summary = f"""### Supplier Reliability & Logistics Risk Assessment

#### Key Risk Indicators:
- **Systemic Risk Index:** The portfolio average supplier risk score is **{avg_risk:.1f}/100**, indicating a moderately stable supplier network, but with specific pockets of high vulnerability.
- **Risky Suppliers:** We have **{len(risky_suppliers)} suppliers** with risk profiles exceeding our compliance target of 60. This includes key partners: {', '.join(risky_suppliers['supplier_name'].tolist()) if not risky_suppliers.empty else 'None'}.
- **Logistical Bottlenecks:** There are **{len(delayed_pos)} open purchase orders** currently past their expected arrival date, contributing to the stockout exposure on high-demand SKUs.
- **Single Source Dependencies:** **{len(single_source)} suppliers** are marked as single-source vendors. Any lead-time deviation from these partners directly threatens product line availability.

#### Strategic Recommendations:
1. **Initiate Audits:** Conduct operational reviews for high-risk suppliers, focusing on reducing lead-time standard deviation (variability).
2. **Buffer Inventory:** Adjust the service level targets (and safety stock) for SKUs dependent on single-source vendors to 98% to insulate the business from transit delays.
3. **Logistics Review:** Establish regional backup freight providers to support critical shipments from East Coast ports.
"""
    return summary

def create_procurement_note(row):
    """
    Generates a professional email draft to send to the supplier regarding critical replenishment needs.
    """
    sku_id = row['sku_id']
    sku_name = row['sku_name']
    wh = row['warehouse_id']
    qty = row['suggested_order_qty']
    supplier_name = row.get('supplier_name', 'Vendor partner')
    payment_terms = row.get('payment_terms', 'Net 30')
    
    email = f"""**Subject:** Urgent Replenishment Request: {sku_name} ({sku_id}) - Meridian Retail Group

**To:** Procurement Operations / Sales Account Manager, {supplier_name}
**From:** Meridian Retail Group Inventory Planning Team

Dear Team,

We are contacting you regarding a critical replenishment requirement for the following SKU:
- **SKU Description:** {sku_name} (ID: {sku_id})
- **Target Fulfillment Location:** {wh}
- **Required Order Quantity:** {qty} units
- **Standard Lead Time:** {row['default_lead_time_days']} days

Our current regional inventory levels have breached safety thresholds. We would like to initiate a Purchase Order for **{qty} units** immediately under our agreed terms of **{payment_terms}**.

**Please confirm the following as soon as possible:**
1. Stock availability for immediate shipment.
2. Estimated dispatch date and transit tracking numbers.
3. Options to expedite delivery or utilize express routing if available.

Thank you for your prompt attention to this matter. We look forward to your confirmation.

Sincerely,
Meridian Retail Group
Inventory Control Department
"""
    return email

def explain_mrp_kit_constraints(parent_sku_id, parent_sku_name, max_kits, components_df):
    """
    Explains constraints holding back the assembly of bundles or kits.
    """
    # Find the bottleneck component (the one with lowest available count relative to required component_qty)
    components_df['buildable_units'] = components_df['on_hand_qty'] / components_df['component_qty']
    bottleneck_row = components_df.sort_values(by='buildable_units').iloc[0]
    
    bottleneck_id = bottleneck_row['component_sku_id']
    bottleneck_name = bottleneck_row.get('sku_name', 'Component SKU')
    bottleneck_on_hand = bottleneck_row['on_hand_qty']
    bottleneck_req = bottleneck_row['component_qty']
    
    report = f"""### MRP Readiness Report: {parent_sku_name} ({parent_sku_id})
**Active Parent Kit Assembly Status**

- **Total Buildable Bundles:** **{max_kits} units** can be fully assembled with current warehouse inventory.
- **Primary Bottleneck Component:** **{bottleneck_name} ({bottleneck_id})** is the limiting constraint.
- **Constraint Detail:** 
  - Current Available Component Stock: {bottleneck_on_hand} units
  - Required per Bundle: {bottleneck_req} units
  - This limits the total buildable kits to {max_kits}.

#### Replenishment Impact:
To build a target run of **100 additional kits**, the following component shortages must be ordered:
"""
    for _, comp in components_df.iterrows():
        needed_qty = int(max(0, (100 * comp['component_qty']) - comp['on_hand_qty']))
        status_symbol = "🟢" if needed_qty == 0 else "🔴"
        comp_name = comp.get('sku_name', comp['component_sku_id'])
        report += f"\n- {status_symbol} **{comp_name} ({comp['component_sku_id']}):** Required: {comp['component_qty'] * 100} units | On Hand: {comp['on_hand_qty']} units | Shortage: {needed_qty} units"
        
    report += f"\n\n**Planning Recommendation:** Place an immediate order for the component shortages highlighted in red. Focus procurement resources on the primary constraint: {bottleneck_name}."
    return report
