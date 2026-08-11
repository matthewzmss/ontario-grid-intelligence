"""
Ontario Grid Intelligence Platform — Streamlit Dashboard

Multi-page dashboard displaying Ontario electricity grid analytics.
Connects to PostgreSQL serving layer populated by PySpark + Delta Lake.
"""

import streamlit as st

# ── Page Configuration ──
st.set_page_config(
    page_title="Ontario Grid Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──
st.markdown("""
<style>
    /* Dark theme overrides */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    }
    
    /* KPI card styling */
    .kpi-card {
        background: rgba(30, 41, 59, 0.8);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 12px;
        padding: 1.5rem;
        backdrop-filter: blur(10px);
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: rgba(15, 23, 42, 0.95);
    }
    
    /* Header gradient */
    .main-header {
        background: linear-gradient(90deg, #6366f1, #8b5cf6, #06b6d4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 800;
        margin-bottom: 0;
    }
    
    .sub-header {
        color: #94a3b8;
        font-size: 1.1rem;
        margin-top: 0;
    }
</style>
""", unsafe_allow_html=True)

# ── Main Page ──
st.markdown('<h1 class="main-header">⚡ Ontario Grid Intelligence</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Real-time analytics for Ontario\'s electricity market — powered by PySpark + Delta Lake</p>', unsafe_allow_html=True)

st.divider()

# ── Landing page content ──
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="📊 Data Sources", value="7", delta="IESO + Weather")
with col2:
    st.metric(label="📈 Historical Records", value="87,000+", delta="2015-2026")
with col3:
    st.metric(label="⚡ Fuel Types Tracked", value="6", delta="Nuclear to Solar")
with col4:
    st.metric(label="🔄 Update Frequency", value="Hourly", delta="Live")

st.divider()

st.markdown("""
### 📑 Dashboard Pages

Navigate using the sidebar to explore:

| Page | Description |
|---|---|
| **🟢 Grid Status** | Live Ontario demand, generation mix, and grid health |
| **⚡ Generation Mix** | Fuel type breakdown, renewable penetration trends |
| **💰 Price Analytics** | Real-time vs Day-Ahead prices, volatility analysis |
| **🌱 Carbon Tracker** | Grid carbon intensity, cleanest hours to use power |
| **🔮 Forecasts** | ML-powered price predictions and feature importance |

---

### 🏗 Architecture
```
IESO Data → Python ETL → Delta Lake (Bronze → Silver → Gold) → PostgreSQL → This Dashboard
```

Built by **Matthew Sano** — [GitHub](https://github.com/matthewsano) | [LinkedIn](https://linkedin.com/in/matthewsano)
""")
