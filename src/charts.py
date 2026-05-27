import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# Palette configuration
THEME_COLORS = {
    'primary': '#1f6feb',      # E.g. Blue
    'secondary': '#bc8cff',    # E.g. Purple
    'success': '#56d364',      # E.g. Green
    'warning': '#ffa657',      # E.g. Orange
    'danger': '#ff7b72',       # E.g. Red
    'info': '#58a6ff',         # E.g. Light Blue
    'bg': 'rgba(13, 17, 23, 0.7)',
    'card_bg': 'rgba(22, 27, 34, 0.7)',
    'border': '#30363d',
    'text': '#c9d1d9',
    'grid': '#21262d'
}

def apply_chart_theme(fig):
    """
    Standardizes a Plotly figure layout to match the dark SaaS aesthetic.
    """
    fig.update_layout(
        font_family="Outfit, -apple-system, sans-serif",
        font_color=THEME_COLORS['text'],
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=20, t=40, b=40),
        legend=dict(
            bgcolor="rgba(22,27,34,0.8)",
            bordercolor=THEME_COLORS['border'],
            borderwidth=1,
            font=dict(size=11)
        ),
        xaxis=dict(
            gridcolor=THEME_COLORS['grid'],
            linecolor=THEME_COLORS['border'],
            tickfont=dict(size=11),
            titlefont=dict(size=12, color='#8b949e')
        ),
        yaxis=dict(
            gridcolor=THEME_COLORS['grid'],
            linecolor=THEME_COLORS['border'],
            tickfont=dict(size=11),
            titlefont=dict(size=12, color='#8b949e')
        )
    )
    return fig

def plot_inventory_health_donut(df_sku):
    """
    Donut chart of inventory SKU counts by risk level.
    """
    # Count SKUs by risk level
    counts = df_sku['risk_level'].value_counts().reset_index()
    counts.columns = ['Risk Level', 'SKU Count']
    
    # Custom color mapping
    color_map = {
        'Critical': THEME_COLORS['danger'],
        'High': THEME_COLORS['warning'],
        'Medium': '#d4bbff',  # Soft purple
        'Low': THEME_COLORS['info'],
        'Healthy': THEME_COLORS['success']
    }
    
    fig = px.pie(
        counts, 
        names='Risk Level', 
        values='SKU Count',
        hole=0.6,
        color='Risk Level',
        color_discrete_map=color_map,
        title="Inventory Risk Classification"
    )
    
    fig.update_traces(
        textposition='inside', 
        textinfo='percent+label',
        hoverinfo='label+value+percent',
        marker=dict(line=dict(color=THEME_COLORS['border'], width=1))
    )
    return apply_chart_theme(fig)

def plot_stockout_exposure_bar(df_sku):
    """
    Horizontal bar chart showing Stockout Exposure Value by Category.
    """
    # Aggregate stockout exposure by Category
    grouped = df_sku.groupby('category')['estimated_stockout_value'].sum().reset_index()
    grouped = grouped.sort_values(by='estimated_stockout_value', ascending=True)
    
    fig = px.bar(
        grouped,
        y='category',
        x='estimated_stockout_value',
        orientation='h',
        title="Est. Stockout Exposure by Product Category",
        labels={'category': 'Category', 'estimated_stockout_value': 'Stockout Exposure ($)'},
        color_discrete_sequence=[THEME_COLORS['danger']]
    )
    
    fig.update_traces(
        marker_line_color=THEME_COLORS['border'],
        marker_line_width=1,
        hovertemplate="<b>%{y}</b><br>Stockout Exposure: $%{x:,.2f}<extra></extra>"
    )
    return apply_chart_theme(fig)

def plot_excess_inventory_bar(df_sku):
    """
    Vertical bar chart of Excess Inventory Value by Category.
    """
    grouped = df_sku.groupby('category')['excess_inventory_value'].sum().reset_index()
    grouped = grouped.sort_values(by='excess_inventory_value', ascending=False)
    
    fig = px.bar(
        grouped,
        x='category',
        y='excess_inventory_value',
        title="Excess Inventory Value by Category",
        labels={'category': 'Category', 'excess_inventory_value': 'Excess Value ($)'},
        color_discrete_sequence=[THEME_COLORS['warning']]
    )
    
    fig.update_traces(
        marker_line_color=THEME_COLORS['border'],
        marker_line_width=1,
        hovertemplate="<b>%{x}</b><br>Excess Value: $%{y:,.2f}<extra></extra>"
    )
    return apply_chart_theme(fig)

def plot_historical_demand(df_demand, sku_id=None):
    """
    Line chart showing aggregate monthly or daily demand.
    """
    df_demand['date'] = pd.to_datetime(df_demand['date'])
    
    # If SKU specified, filter
    if sku_id:
        df_filtered = df_demand[df_demand['sku_id'] == sku_id]
        title = f"Historical Demand for SKU: {sku_id}"
    else:
        df_filtered = df_demand
        title = "Meridian Omnichannel Retail Demand Trend"
        
    # Group by date and channel
    grouped = df_filtered.groupby(['date', 'channel'])['demand_qty'].sum().reset_index()
    
    fig = px.line(
        grouped,
        x='date',
        y='demand_qty',
        color='channel',
        title=title,
        color_discrete_sequence=[THEME_COLORS['primary'], THEME_COLORS['secondary']],
        labels={'date': 'Date', 'demand_qty': 'Units Demanded', 'channel': 'Channel'}
    )
    
    fig.update_traces(line=dict(width=2.5))
    return apply_chart_theme(fig)

def plot_actual_vs_forecast(df_hist, df_fc, sku_id):
    """
    Line chart comparing actual demand and forecast projections for 12 weeks.
    """
    fig = go.Figure()
    
    # Historical demand (last 12 weeks for clean visual)
    df_hist = df_hist.sort_values('date')
    hist_tail = df_hist.tail(24)  # Use last 24 periods for context
    
    fig.add_trace(go.Scatter(
        x=hist_tail['date'],
        y=hist_tail['demand_qty'],
        name='Actual Demand',
        line=dict(color=THEME_COLORS['text'], width=2),
        mode='lines+markers'
    ))
    
    # Forecast lines
    for method in ['moving_average', 'weighted_moving_average', 'exponential_smoothing']:
        if method in df_fc.columns:
            name_map = {
                'moving_average': 'Simple Moving Average',
                'weighted_moving_average': 'Weighted MA',
                'exponential_smoothing': 'Exponential Smoothing'
            }
            fig.add_trace(go.Scatter(
                x=df_fc['date'],
                y=df_fc[method],
                name=name_map.get(method, method),
                line=dict(width=2, dash='dash' if method != 'exponential_smoothing' else 'solid'),
                mode='lines'
            ))
            
    fig.update_layout(
        title=f"12-Week Forecast Comparisons for {sku_id}",
        xaxis_title="Timeline",
        yaxis_title="Quantity (Units)"
    )
    return apply_chart_theme(fig)

def plot_supplier_risk_matrix(df_suppliers):
    """
    Scatter plot mapping lead time standard deviation against average lead time,
    with bubble size representing risk score.
    """
    fig = px.scatter(
        df_suppliers,
        x='avg_lead_time_days',
        y='lead_time_std_days',
        size='risk_score',
        color='risk_score',
        hover_name='supplier_name',
        title="Supplier Reliability Profiles",
        labels={
            'avg_lead_time_days': 'Average Lead Time (Days)',
            'lead_time_std_days': 'Lead Time Standard Deviation (Days)',
            'risk_score': 'Supplier Risk Score'
        },
        color_continuous_scale=px.colors.sequential.OrRd
    )
    fig.update_layout(coloraxis_colorbar=dict(title="Risk Score"))
    return apply_chart_theme(fig)

def plot_supplier_otd_bar(df_suppliers):
    """
    Horizontal bar chart showing On-Time Delivery rate by supplier.
    """
    df_sorted = df_suppliers.sort_values(by='on_time_delivery_rate', ascending=True)
    
    # Create target line value
    fig = px.bar(
        df_sorted,
        y='supplier_name',
        x='on_time_delivery_rate',
        title="On-Time Delivery Rate by Supplier",
        labels={'supplier_name': 'Supplier', 'on_time_delivery_rate': 'OTD %'},
        color='on_time_delivery_rate',
        color_continuous_scale=px.colors.sequential.Viridis
    )
    
    # Add a target threshold at 95%
    fig.add_vline(x=0.95, line_dash="dash", line_color=THEME_COLORS['danger'], 
                 annotation_text="95% Target", annotation_position="bottom right")
                 
    fig.update_layout(coloraxis_showscale=False)
    return apply_chart_theme(fig)

def plot_risk_trend():
    """
    Plots risk trend over time (simulated historical risk indices).
    """
    dates = pd.date_range(end=pd.Timestamp.now(), periods=12, freq='ME')
    data = {
        'Date': dates,
        'Stockout Risk Index': [54, 52, 49, 42, 38, 41, 45, 51, 62, 58, 44, 32],
        'Excess Capital Risk Index': [35, 38, 41, 44, 48, 52, 49, 45, 41, 39, 36, 33]
    }
    df = pd.DataFrame(data)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['Stockout Risk Index'],
        name='Stockout Risk Index',
        line=dict(color=THEME_COLORS['danger'], width=2.5)
    ))
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['Excess Capital Risk Index'],
        name='Excess Capital Risk Index',
        line=dict(color=THEME_COLORS['warning'], width=2.5)
    ))
    
    fig.update_layout(
        title="12-Month Systemic Risk Profiles",
        xaxis_title="Date",
        yaxis_title="Index Level (0-100)"
    )
    return apply_chart_theme(fig)
