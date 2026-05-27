import streamlit as st

def inject_custom_css():
    """
    Injects custom CSS to style the Streamlit app as a premium SaaS dashboard.
    """
    st.markdown(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        
        <style>
        /* Global CSS Overrides */
        html, body, [class*="css"] {
            font-family: 'Outfit', 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        /* Main background and alignment */
        .stApp {
            background-color: #0d1117;
            color: #c9d1d9;
        }
        
        /* Headers styling */
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Outfit', sans-serif;
            font-weight: 600 !important;
            letter-spacing: -0.02em;
            color: #ffffff;
        }
        
        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background-color: #161b22 !important;
            border-right: 1px solid #30363d;
        }
        
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {
            background-color: #161b22 !important;
        }
        
        /* Custom card elements */
        .saas-card {
            background: rgba(22, 27, 34, 0.7);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(48, 54, 61, 0.8);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        .saas-card:hover {
            transform: translateY(-2px);
            border-color: #58a6ff;
            box-shadow: 0 6px 24px rgba(88, 166, 255, 0.15);
        }
        
        /* Metric Styling */
        .metric-title {
            font-size: 0.85rem;
            color: #8b949e;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 500;
            margin-bottom: 4px;
        }
        
        .metric-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #ffffff;
            line-height: 1.2;
        }
        
        .metric-delta {
            font-size: 0.85rem;
            font-weight: 600;
            margin-top: 4px;
        }
        
        .delta-positive {
            color: #3fb950;
        }
        
        .delta-negative {
            color: #f85149;
        }
        
        .delta-neutral {
            color: #8b949e;
        }

        /* KPI Banner styling */
        .kpi-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }
        
        /* Custom buttons styling */
        .stButton>button {
            border-radius: 8px;
            font-weight: 600;
            padding: 0.5rem 1.25rem;
            transition: all 0.2s ease-in-out;
            background: linear-gradient(135deg, #1f6feb 0%, #094cb5 100%);
            color: #ffffff;
            border: none;
            box-shadow: 0 4px 12px rgba(31, 111, 235, 0.2);
        }
        
        .stButton>button:hover {
            background: linear-gradient(135deg, #388bfd 0%, #1f6feb 100%);
            box-shadow: 0 4px 18px rgba(31, 111, 235, 0.35);
            transform: translateY(-1px);
            color: #ffffff;
        }
        
        .stButton>button:active {
            transform: translateY(0);
        }
        
        /* Secondary / Outline Button */
        div[data-testid="stMarkdownContainer"] button.secondary-btn {
            background: transparent !important;
            color: #c9d1d9 !important;
            border: 1px solid #30363d !important;
            box-shadow: none !important;
        }
        
        div[data-testid="stMarkdownContainer"] button.secondary-btn:hover {
            background: #21262d !important;
            border-color: #8b949e !important;
            color: #ffffff !important;
        }

        /* Badges */
        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }
        
        .badge-critical {
            background-color: rgba(248, 81, 73, 0.15);
            color: #ff7b72;
            border: 1px solid rgba(248, 81, 73, 0.3);
        }
        
        .badge-high {
            background-color: rgba(240, 136, 62, 0.15);
            color: #ffa657;
            border: 1px solid rgba(240, 136, 62, 0.3);
        }
        
        .badge-medium {
            background-color: rgba(227, 179, 65, 0.15);
            color: #d4bbff; /* Adjusted purple/yellow tone */
            border: 1px solid rgba(227, 179, 65, 0.3);
        }
        
        .badge-low {
            background-color: rgba(88, 166, 255, 0.15);
            color: #58a6ff;
            border: 1px solid rgba(88, 166, 255, 0.3);
        }
        
        .badge-healthy {
            background-color: rgba(63, 185, 80, 0.15);
            color: #56d364;
            border: 1px solid rgba(63, 185, 80, 0.3);
        }
        
        /* Table enhancements */
        .dataframe {
            background-color: #161b22 !important;
            border: 1px solid #30363d !important;
            border-collapse: collapse;
        }
        
        .dataframe th {
            background-color: #21262d !important;
            color: #ffffff !important;
            font-weight: 600 !important;
            padding: 10px !important;
            text-align: left !important;
            border-bottom: 2px solid #30363d !important;
        }
        
        .dataframe td {
            padding: 8px 10px !important;
            border-bottom: 1px solid #21262d !important;
            color: #c9d1d9 !important;
        }
        
        /* Hero section specific styling */
        .hero-title {
            font-size: 3rem;
            font-weight: 800;
            background: linear-gradient(135deg, #ffffff 0%, #8b949e 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
            line-height: 1.15;
        }
        
        .hero-gradient-text {
            background: linear-gradient(135deg, #58a6ff 0%, #bc8cff 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
        }
        
        .hero-desc {
            font-size: 1.25rem;
            color: #8b949e;
            max-width: 800px;
            margin-bottom: 30px;
            line-height: 1.6;
        }
        
        .gradient-border-card {
            background: #161b22;
            position: relative;
            border-radius: 12px;
            padding: 24px;
            border: 1px solid #30363d;
            overflow: hidden;
        }
        
        .gradient-border-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #58a6ff, #bc8cff);
        }

        /* Tooltip styling */
        div[data-testid="stTooltipIcon"] {
            color: #58a6ff !important;
        }
        
        </style>
        """,
        unsafe_allow_html=True
    )

def create_kpi_card(title, value, delta=None, delta_direction="up", tooltip=None):
    """
    Returns HTML component for a beautiful glassmorphic KPI card with details.
    """
    delta_html = ""
    if delta is not None:
        if delta_direction == "up":
            class_name = "delta-positive"
            arrow = "↑"
        elif delta_direction == "down":
            class_name = "delta-negative"
            arrow = "↓"
        else:
            class_name = "delta-neutral"
            arrow = "•"
        delta_html = f'<div class="metric-delta {class_name}">{arrow} {delta}</div>'
        
    tooltip_attr = f'title="{tooltip}"' if tooltip else ""
    
    return f"""
    <div class="saas-card" {tooltip_attr}>
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value}</div>
        {delta_html}
    </div>
    """
