import streamlit as st

def inject_custom_css():
    """
    Injects custom CSS to style the Streamlit app as a professional, high-density enterprise SaaS dashboard.
    """
    st.markdown(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
        
        <style>
        /* Global CSS Overrides */
        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        /* Main background */
        .stApp {
            background-color: #0b0f19;
            color: #e2e8f0;
        }
        
        /* Headers styling */
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Outfit', sans-serif;
            font-weight: 600 !important;
            letter-spacing: -0.01em;
            color: #f8fafc;
        }
        
        h1 {
            font-size: 2.25rem !important;
            margin-bottom: 0.5rem !important;
        }
        
        h2 {
            font-size: 1.5rem !important;
            margin-top: 1.5rem !important;
            margin-bottom: 0.75rem !important;
            border-bottom: 1px solid #1e293b;
            padding-bottom: 0.5rem;
        }
        
        h3 {
            font-size: 1.2rem !important;
            margin-top: 1.2rem !important;
            margin-bottom: 0.5rem !important;
        }
        
        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background-color: #0f172a !important;
            border-right: 1px solid #1e293b;
        }
        
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {
            background-color: #0f172a !important;
        }
        
        /* Streamlit native container border modifications to make them look like premium dashboard panels */
        div[data-testid="stVerticalBlockBorderContainer"] {
            background-color: #111827 !important;
            border: 1px solid #1e293b !important;
            border-radius: 8px !important;
            padding: 18px !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1) !important;
        }
        
        /* Primary Buttons */
        .stButton>button {
            border-radius: 6px;
            font-weight: 500;
            padding: 0.45rem 1.1rem;
            background-color: #2563eb !important;
            color: #ffffff !important;
            border: 1px solid #3b82f6 !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            transition: all 0.15s ease-in-out;
        }
        
        .stButton>button:hover {
            background-color: #1d4ed8 !important;
            border-color: #2563eb !important;
            color: #ffffff !important;
        }

        /* Badges styling */
        .badge {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.02em;
        }
        
        .badge-critical {
            background-color: rgba(239, 68, 68, 0.1);
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.2);
        }
        
        .badge-high {
            background-color: rgba(249, 115, 22, 0.1);
            color: #fb923c;
            border: 1px solid rgba(249, 115, 22, 0.2);
        }
        
        .badge-medium {
            background-color: rgba(234, 179, 8, 0.1);
            color: #facc15;
            border: 1px solid rgba(234, 179, 8, 0.2);
        }
        
        .badge-low {
            background-color: rgba(59, 130, 246, 0.1);
            color: #60a5fa;
            border: 1px solid rgba(59, 130, 246, 0.2);
        }
        
        .badge-healthy {
            background-color: rgba(34, 197, 94, 0.1);
            color: #4ade80;
            border: 1px solid rgba(34, 197, 94, 0.2);
        }
        
        /* Table data cell adjustments */
        .dataframe td {
            font-size: 0.85rem !important;
        }
        
        .dataframe th {
            font-size: 0.85rem !important;
            font-weight: 500 !important;
        }

        /* Hero page styling elements */
        .hero-title {
            font-family: 'Outfit', sans-serif;
            font-size: 2.75rem;
            font-weight: 800;
            color: #ffffff;
            margin-bottom: 8px;
            letter-spacing: -0.025em;
        }
        
        .hero-gradient-text {
            color: #3b82f6;
        }
        
        .hero-desc {
            font-size: 1.15rem;
            color: #94a3b8;
            max-width: 900px;
            margin-bottom: 24px;
            line-height: 1.5;
        }
        
        </style>
        """,
        unsafe_allow_html=True
    )
