# SupplyPilot AI

**One-line Pitch:** Predict stockouts, reduce excess inventory, and turn ERP/MRP data into automated replenishment planning decisions.

---

## 🎯 Target Roles
This portfolio project demonstrates skills relevant to:
- **Supply Chain Product Managers**
- **Inventory Analysts & Demand Planners**
- **Logistics Data Engineers**
- **Full-Stack SaaS Developers (Python/Streamlit)**

---

## 💼 The Business Challenge
Retailers and e-commerce brands lose billions of dollars annually due to two opposing inventory forces:
1. **Stockouts:** Sparing safety stock leads to empty shelves, backorders, and lost customer goodwill.
2. **Excess Capital Lockup:** Over-purchasing leads to high holding costs, warehouse bottlenecks, and eventual inventory markdowns or liquidations.

**SupplyPilot AI** bridges this gap. It operates as a decision-support command center that simulates consumer demand patterns, monitors supplier delivery reliability, calculates dynamic safety stock values, and parses multi-component BOM (Bill of Materials) structures to optimize procurement workflows.

---

## 🚀 Key Features

- **Inventory Command Center:** An executive dashboard showing platform health indexes, total stockout exposure value, overstocked capital, and operational metrics.
- **SKU Risk Intelligence:** An interactive grid with advanced filters (ABC class, XYZ variability, warehouse, supplier) and detailed tabs for inventory analysis, safety thresholds, and forecasts.
- **Replenishment Workbench:** An actionable order authorization center. Users check rows to authorize suggested replenishment orders or PO expedites, which are committed directly to the SQLite database.
- **Demand Forecasting Lab:** Evaluates statistical models (Simple Moving Average, Weighted Moving Average, Exponential Smoothing) against historical weekly demand, computing fit errors (MAPE) and projecting a 12-week seasonal curve.
- **Supplier Reliability Center:** Scorecard grading suppliers on lead time deviation, OTD rates, fill rates, and defect rates, dynamically adjusting safety stock targets for high-risk vendors.
- **MRP Readiness View:** A component availability dashboard for kits and bundles. Identifies bottleneck subcomponents and calculates shortage quantities for planned assembly runs.
- **Scenario Planning Studio:** A "what-if" sandbox simulating demand surges and supplier lead-time delays to instantly recalculate stockout exposures and required capital in real-time.
- **On-Demand AI Copilot:** Generates natural language summaries of SKU risks, procurement email drafts, and supplier audits. Uses deterministic rule-based generators when no LLM API key is provided.

---

## 🧮 Supply Chain Planning Logic Used

1. **Inventory Position:**
   $$IP = OnHand + OnOrder - Allocated - Backorder$$
   *Ensures in-transit orders are factored into coverage before triggering duplicates.*

2. **Days of Cover:**
   $$DaysOfCover = \frac{InventoryPosition}{AverageDailyDemand}$$
   *Uses 90-day Average Daily Demand (ADD) to evaluate coverage timeline.*

3. **XYZ Demand Classification:**
   Categorizes SKUs by their demand Coefficient of Variation ($CV = \frac{\sigma}{\mu}$):
   - **X (Stable):** $CV \le 0.20$
   - **Y (Moderate):** $0.20 < CV \le 0.50$
   - **Z (Volatile):** $CV > 0.50$

4. **ABC Value Classification:**
   Classifies SKUs by annualized consumption value ($AnnualDemand \times UnitCost$).
   - **A (Critical Value):** Top 80% cumulative value
   - **B (Medium Value):** Next 15% cumulative value
   - **C (Low Value):** Remaining 5% cumulative value

5. **Dynamic Safety Stock:**
   $$SafetyStock = Z \times \sigma_{daily\_demand} \times \sqrt{LeadTime} \times (1 + \frac{SupplierRiskScore}{200})$$
   *Adjusts safety stock upwards to account for high supplier lead-time standard deviation.*

6. **Reorder Point (ROP):**
   $$ROP = (AverageDailyDemand \times LeadTime) + SafetyStock$$

7. **Suggested Order Quantity:**
   $$SuggestedQty = \max(ROP + CycleStock - InventoryPosition, MOQ)$$
   *Rounded to the nearest case pack size to match logistics constraint standards.*

---

## 🗄️ Database Schema Design

SupplyPilot AI uses local SQLite (`data/supplypilot.db`) with 8 tables:
- `sku_master`: Central repository of SKU details, categories, cost, price, and MOQ constraints.
- `inventory_status`: On hand, allocated, and backorder counts per SKU per warehouse.
- `demand_history`: 18 months of weekly historical quantities, promotional flags, and events.
- `supplier_master`: Lead time averages, lead time standard deviation, OTD rates, fill rates, and risk scores.
- `purchase_orders`: Ledger of completed and open orders, tracking transit delay variance.
- `warehouse_master`: Geographical location, capacity, and current utilization.
- `bom_or_kit_structure`: Mapping parent bundle SKUs to component quantities.
- `recommendation_output`: Precalculated actions, days of cover, ROP thresholds, and financial exposures.

---

## 🛠️ Tech Stack
- **Backend:** Python 3.14+
- **Database:** SQLite (with native Python `sqlite3` library)
- **Data Engineering:** Pandas, NumPy
- **Visualizations:** Plotly Express & Graph Objects
- **Frontend UI:** Streamlit (with custom CSS/HTML markup overrides)

---

## 📦 How to Run Locally

### Prerequisites
- Python 3.10+
- Virtual environment support

### Installation
1. Clone the repository to your workspace:
   ```bash
   cd SupplyPilot
   ```
2. Set up a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the Streamlit web application:
   ```bash
   streamlit run app.py
   ```
5. Open your browser to `http://localhost:8501`.

---

## 📊 Screenshots
*(Place screenshots here showcasing the custom glassmorphic KPI cards, interactive data editor, and plotly forecast lines)*

---

## 🎭 Demo Story & Workflow
1. **Enter the Workspace:** Launch the app, review the marketing metrics, and click **Open Planning Workspace**.
2. **Review Command Center:** Observe that Meridian Retail Group has a 62% Health Index due to lead-time delays, with $32,000 in stockout exposure.
3. **Filter Risks:** Go to **SKU Risk Intelligence**, filter for category "Apparel" and risk level "Critical".
4. **Deep-Dive SKU:** Select a Hoodie SKU, look at the forecast comparisons chart in the tab, and click **Generate AI SKU Risk Analysis** to read a breakdown of why this item is at risk.
5. **Approve PO:** In **Replenishment Workbench**, review the suggested order size of 400. Tick **Approve** and click **Commit Checked Orders**. This updates the SQLite PO ledger and recalculates recommendations instantly.
6. **Simulate Shocks:** Go to **Scenario Planning Studio** and push the transit delay slider to 10 days. Observe the health index fall as safety stocks dynamically adjust.

---

## 📝 Resume Bullet Suggestions
- **Built SupplyPilot AI**, an interactive inventory planning web app using Python, Streamlit, SQL, and Plotly to calculate stockout risk, reorder points, safety stock, and replenishment actions across 500 simulated retail SKUs.
- **Designed ERP/MRP-style planning logic** connecting SKU inventory, open purchase orders, supplier lead times, and kit/component availability to identify fulfillment risk before customer demand is missed.
- **Developed supplier risk**, demand forecasting, ABC/XYZ classification, and scenario planning modules to support balanced inventory optimization across service level, working capital, and stockout exposure.

---

## 🔗 LinkedIn Post Draft
```text
🚀 Excited to share my latest portfolio project: SupplyPilot AI!

I built SupplyPilot AI, an enterprise-grade inventory orchestration SaaS app designed for retail and e-commerce brands to balance service levels against working capital lockups.

Key Technical Elements:
🔹 Dynamic safety stock calculations utilizing standard normal Z-scores adjusted by supplier risk indices.
🔹 E-Commerce MRP & BOM logic that traces subcomponent bottlenecks and assembly shortages.
🔹 Forecasting lab comparing SMA, WMA, and Single Exponential Smoothing models with historical MAPE scoring.
🔹 A "What-If" Scenario Planning Studio to simulate demand spikes and logistics delays in real time.
🔹 Interactive write-back database integration committed using SQLite and Streamlit.

Check out the full repository and project logic: [insert link]

#SupplyChain #InventoryPlanning #DataEngineering #Python #Streamlit #SaaS
```
