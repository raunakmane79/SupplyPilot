import pandas as pd
import numpy as np

def generate_forecasts(df_demand, sku_id, warehouse_id=None, forecast_weeks=12):
    """
    Computes moving average, weighted moving average, and exponential smoothing forecasts.
    Returns:
        df_hist: DataFrame of historical weekly demand.
        df_fc: DataFrame of 12-week future projections for each method.
        metrics: Dictionary of historical MAPE errors for each method.
    """
    # 1. Filter and aggregate historical demand by week
    df_filtered = df_demand[df_demand['sku_id'] == sku_id].copy()
    if warehouse_id:
        df_filtered = df_filtered[df_filtered['warehouse_id'] == warehouse_id]
        
    df_filtered['date'] = pd.to_datetime(df_filtered['date'])
    # Aggregate by week
    df_filtered['week_start'] = df_filtered['date'].dt.to_period('W').dt.start_time
    df_weekly = df_filtered.groupby('week_start')['demand_qty'].sum().reset_index()
    df_weekly = df_weekly.sort_values('week_start')
    
    # Ensure continuous timeline (if there are gaps)
    if not df_weekly.empty:
        r = pd.date_range(start=df_weekly['week_start'].min(), end=df_weekly['week_start'].max(), freq='W-MON')
        df_weekly = df_weekly.set_index('week_start').reindex(r, fill_value=0).reset_index()
        df_weekly.rename(columns={'index': 'date', 'demand_qty': 'demand_qty'}, inplace=True)
    else:
        df_weekly = pd.DataFrame(columns=['date', 'demand_qty'])
        return df_weekly, pd.DataFrame(), {}
        
    hist_len = len(df_weekly)
    if hist_len < 8:
        # Not enough history to forecast
        return df_weekly, pd.DataFrame(), {}
        
    actuals = df_weekly['demand_qty'].values
    dates = df_weekly['date'].values
    
    # Define parameters
    ma_window = 4
    weights = [0.4, 0.3, 0.2, 0.1] # recent to oldest
    alpha = 0.3
    
    # Initialize historical forecast arrays (for error metric calculation)
    # Start checking from index 4 onwards
    fc_ma_hist = np.zeros(hist_len)
    fc_wma_hist = np.zeros(hist_len)
    fc_es_hist = np.zeros(hist_len)
    
    # Seed Exponential Smoothing
    fc_es_hist[0] = actuals[0]
    
    for t in range(1, hist_len):
        # SES
        fc_es_hist[t] = alpha * actuals[t-1] + (1 - alpha) * fc_es_hist[t-1]
        
        # MA & WMA (require 4 periods)
        if t >= ma_window:
            fc_ma_hist[t] = np.mean(actuals[t-ma_window:t])
            # Weighted MA: most recent gets weights[0]
            recent_vals = actuals[t-ma_window:t][::-1] # reverse so t-1 is index 0
            fc_wma_hist[t] = np.dot(recent_vals, weights)
        else:
            # Fallback to mean of whatever we have
            fc_ma_hist[t] = np.mean(actuals[:t])
            fc_wma_hist[t] = np.mean(actuals[:t])
            
    # Calculate historical errors (MAPE)
    # Avoid division by zero
    valid_mask = actuals > 0
    valid_actuals = actuals[valid_mask]
    
    mape_ma = 99.9
    mape_wma = 99.9
    mape_es = 99.9
    
    if len(valid_actuals) > ma_window:
        mape_ma = np.mean(np.abs(valid_actuals[ma_window:] - fc_ma_hist[valid_mask][ma_window:]) / valid_actuals[ma_window:]) * 100.0
        mape_wma = np.mean(np.abs(valid_actuals[ma_window:] - fc_wma_hist[valid_mask][ma_window:]) / valid_actuals[ma_window:]) * 100.0
        mape_es = np.mean(np.abs(valid_actuals[ma_window:] - fc_es_hist[valid_mask][ma_window:]) / valid_actuals[ma_window:]) * 100.0
        
    metrics = {
        'moving_average': round(float(mape_ma), 1),
        'weighted_moving_average': round(float(mape_wma), 1),
        'exponential_smoothing': round(float(mape_es), 1)
    }
    
    # 2. Project 12 Weeks Future Forecast
    # Generate future dates
    last_date = pd.Timestamp(dates[-1])
    future_dates = [last_date + pd.Timedelta(weeks=i+1) for i in range(forecast_weeks)]
    
    # Base level calculations for future
    base_ma = np.mean(actuals[-ma_window:])
    
    recent_vals = actuals[-ma_window:][::-1]
    base_wma = np.dot(recent_vals, weights)
    
    base_es = alpha * actuals[-1] + (1 - alpha) * fc_es_hist[-1]
    
    # Check for seasonality index
    # We group by week number of the year in history to get weekly index
    df_weekly['week_num'] = df_weekly['date'].dt.isocalendar().week
    overall_mean = df_weekly['demand_qty'].mean()
    
    seasonal_indices = {}
    if overall_mean > 0:
        weekly_means = df_weekly.groupby('week_num')['demand_qty'].mean()
        # Smooth seasonal indices
        for w_num, val in weekly_means.items():
            seasonal_indices[w_num] = val / overall_mean
            
    # Project forward
    fc_ma = []
    fc_wma = []
    fc_es = []
    
    for f_date in future_dates:
        w_num = f_date.isocalendar()[1]
        s_idx = seasonal_indices.get(w_num, 1.0)
        
        # Clip seasonal index to avoid extreme noise (0.3 to 2.5)
        s_idx = np.clip(s_idx, 0.4, 2.2)
        
        # Apply seasonal index (if stable demand, seasonal index is close to 1.0 anyway)
        # We apply it to make the forecast visually curve in seasonal periods
        fc_ma.append(max(round(base_ma * s_idx, 1), 0.0))
        fc_wma.append(max(round(base_wma * s_idx, 1), 0.0))
        fc_es.append(max(round(base_es * s_idx, 1), 0.0))
        
    df_fc = pd.DataFrame({
        'date': future_dates,
        'moving_average': fc_ma,
        'weighted_moving_average': fc_wma,
        'exponential_smoothing': fc_es
    })
    
    return df_weekly[['date', 'demand_qty']], df_fc, metrics
