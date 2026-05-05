API_BASE = "http://localhost:8000"

ANTI_GRAVITY_CSS = """
<style>
/* Deep Space / Anti-Gravity Theme */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');

.stApp {
    background: radial-gradient(circle at center, #0B0A1A 0%, #05040A 100%);
    color: #E2E8F0;
    font-family: 'Outfit', sans-serif;
}

/* Base text */
h1, h2, h3, h4, h5, h6 { 
    color: #F8FAFC !important; 
    font-family: 'Outfit', sans-serif;
    letter-spacing: -0.5px;
}

/* Sidebar styling */
[data-testid="stSidebar"] { 
    background: linear-gradient(180deg, rgba(10,10,20,0.95) 0%, rgba(5,4,10,0.95) 100%) !important; 
    border-right: 1px solid rgba(124,58,237,0.15);
}

[data-testid="stSidebar"] > div:first-child {
    background: transparent !important;
}

[data-testid="stSidebarNav"] span {
    color: #E2E8F0 !important;
}

/* Primary Button */
.stButton>button {
    background: linear-gradient(135deg, #7C3AED 0%, #3B82F6 100%);
    color: white !important; 
    border: 1px solid rgba(255,255,255,0.1); 
    border-radius: 16px;
    padding: 0.6rem 2rem; 
    font-weight: 600;
    font-size: 1rem;
    box-shadow: 0 4px 15px rgba(124,58,237,0.4), inset 0 1px 0 rgba(255,255,255,0.2);
    transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
    width: 100%;
}

.stButton>button:hover { 
    box-shadow: 0 8px 25px rgba(59,130,246,0.6), inset 0 1px 0 rgba(255,255,255,0.3); 
    transform: translateY(-3px) scale(1.02); 
    background: linear-gradient(135deg, #8B5CF6 0%, #60A5FA 100%);
}

.stButton>button:active {
    transform: translateY(1px);
}

/* Custom Metric Cards */
.metric-card {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px; 
    padding: 1.5rem;
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    box-shadow: 0 10px 40px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05);
    transition: all 0.3s ease;
    margin-bottom: 1rem;
}

.metric-card:hover {
    transform: translateY(-5px);
    border-color: rgba(124,58,237,0.4);
    box-shadow: 0 15px 50px rgba(124,58,237,0.2), inset 0 1px 0 rgba(255,255,255,0.1);
}

.metric-card h3 {
    margin-top: 0;
    color: #F8FAFC !important;
    font-weight: 600;
}

/* Global labels for inputs and radio buttons */
label, div[data-testid="stWidgetLabel"] p, .stRadio p, .stSelectbox p, .stTextInput p {
    color: #E2E8F0 !important;
    font-weight: 500 !important;
}

/* Inputs and Selects */
.stSelectbox>div>div, .stTextInput>div>div, .stTextArea>div>div { 
    background: rgba(255, 255, 255, 0.04) !important; 
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 12px !important;
    color: #F8FAFC !important;
    transition: all 0.2s ease;
}

.stSelectbox>div>div:focus-within, .stTextInput>div>div:focus-within, .stTextArea>div>div:focus-within {
    border-color: #7C3AED !important;
    box-shadow: 0 0 0 2px rgba(124,58,237,0.2) !important;
    background: rgba(255, 255, 255, 0.06) !important;
}

/* Streamlit Metrics (built-in) */
div[data-testid="stMetric"] {
    background: linear-gradient(180deg, rgba(30,41,59,0.7) 0%, rgba(15,23,42,0.7) 100%);
    border: 1px solid rgba(124,58,237,0.3);
    border-radius: 16px; 
    padding: 1.2rem;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}

div[data-testid="stMetricValue"] {
    font-size: 2.5rem !important;
    font-weight: 800 !important;
    background: linear-gradient(135deg, #A855F7, #3B82F6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

/* Dataframe & Tables */
.stDataFrame { 
    background: rgba(255,255,255,0.02) !important; 
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.05);
}

/* Headers */
header[data-testid="stHeader"] {
    background: transparent !important;
}

/* Expander */
.streamlit-expanderHeader {
    background: rgba(255,255,255,0.05) !important;
    border-radius: 10px !important;
}

/* Alert Boxes */
.stAlert {
    border-radius: 12px !important;
    border: none !important;
}
.stAlert[data-testid="stAlert"] {
    background: rgba(16, 185, 129, 0.1) !important;
    border-left: 4px solid #10B981 !important;
}
.stAlert[data-baseweb="notification"] {
    background: rgba(239, 68, 68, 0.1) !important;
    border-left: 4px solid #EF4444 !important;
}
</style>
"""
