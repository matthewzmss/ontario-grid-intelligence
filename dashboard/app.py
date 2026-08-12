import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Ontario Grid Intelligence", page_icon="⚡",
                   layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    /* Bliss desktop */
    .stApp {
        background: linear-gradient(180deg,
            #3a7bd5 0%, #5b9bd5 15%, #87ceeb 30%, #a8d8ea 40%,
            #90c850 40.1%, #7ab648 50%, #6aaa40 60%, #5a9e38 70%,
            #4a9230 80%, #3d8628 90%, #357a20 100%);
        background-attachment: fixed;
    }

    #MainMenu, footer, header {visibility: hidden;}
    [data-testid="stSidebar"] {display: none;}

    /* Main container TRANSPARENT so Bliss shows */
    [data-testid="stMainBlockContainer"] {
        background: transparent !important;
        padding: 5rem 2rem 2rem 2rem !important;
    }

    /* ── ONLY the main two-panel columns get XP window style ── */
    [data-testid="stMainBlockContainer"] > div > div > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        background: #ece9d8 !important;
        border: 2px solid #0054e3;
        border-top: none;
        border-radius: 0 0 4px 4px;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.3);
        padding: 6px !important;
    }

    /* Left column: always same height */
    [data-testid="stMainBlockContainer"] > div > div > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child {
        align-self: flex-start !important;
        min-height: 65vh;
    }

    /* RIGHT column: natural height */
    [data-testid="stMainBlockContainer"] > div > div > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child {
        align-self: flex-start !important;
    }

    /* ALL other columns anywhere = reset (KPI cards, chart pairs, etc) */
    [data-testid="stColumn"] [data-testid="stHorizontalBlock"] [data-testid="stColumn"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 4px !important;
        border-radius: 0 !important;
        align-self: auto !important;
        min-height: 0 !important;
    }

    /* ── XP Title Bars ── */
    .xp-titlebar {
        background: linear-gradient(180deg,
            #0997ff 0%, #0053ee 8%, #0050ee 20%,
            #0853f5 40%, #045cf7 48%, #0041d2 52%,
            #0046d5 60%, #0050e8 72%, #1963e0 80%,
            #3c7df1 92%, #4e8cf6 100%);
        color: white;
        font-family: 'Trebuchet MS', 'Tahoma', sans-serif;
        font-size: 12px; font-weight: bold;
        padding: 3px 8px;
        display: flex; align-items: center; justify-content: space-between;
        text-shadow: 1px 1px 1px rgba(0,0,0,0.4);
        border-radius: 6px 6px 0 0;
        margin: -6px -6px 6px -6px;
    }
    .xp-titlebar-r { margin: -6px -6px 6px -6px; }
    .xp-btns { display: flex; gap: 2px; }
    .xp-b {
        width: 18px; height: 18px;
        background: linear-gradient(180deg, #3c8df6 0%, #236ee1 50%, #1b62d1 51%, #3a8cf5 100%);
        border: 1px solid rgba(255,255,255,0.6); border-radius: 3px;
        color: white; font-size: 8px;
        display: flex; align-items: center; justify-content: center;
    }
    .xp-bx { background: linear-gradient(180deg, #e5735d 0%, #d1503b 50%, #c54433 51%, #e87565 100%); }

    /* ── XP Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        background: #ece9d8 !important; border-bottom: 1px solid #aca899;
        gap: 0px !important; padding: 0 !important;
    }
    .stTabs [data-baseweb="tab"] {
        background: #ece9d8 !important;
        border: 1px solid #aca899 !important;
        border-bottom: 1px solid #aca899 !important;
        border-radius: 3px 3px 0 0 !important;
        color: #000 !important;
        font-family: 'Tahoma', sans-serif !important;
        font-size: 12px !important;
        padding: 3px 12px !important;
        margin-right: 1px !important;
        margin-bottom: -1px;
        height: auto !important; min-height: 0 !important;
    }
    .stTabs [aria-selected="true"] {
        background: #fff !important;
        border-bottom-color: #fff !important;
        font-weight: bold !important;
    }
    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"] { display: none !important; }
    .stTabs [data-baseweb="tab-panel"] {
        background: #fff !important;
        border: 1px solid #aca899; border-top: none;
        padding: 8px !important;
    }

    /* ── Text ── */
    .stMarkdown, .stMarkdown p, .stMarkdown li {
        color: #000 !important; font-family: 'Tahoma', sans-serif !important;
    }
    h1,h2,h3,h4 { color: #003399 !important; font-family: 'Trebuchet MS', 'Tahoma', sans-serif !important; }

    /* Metrics */
    [data-testid="stMetric"] { background: #f5f3ee; border: 1px solid #aca899; padding: 6px; }
    [data-testid="stMetricLabel"] { color: #555 !important; font-family: 'Tahoma' !important; font-size: 11px !important; }
    [data-testid="stMetricValue"] { color: #003399 !important; font-family: 'Tahoma' !important; }

    /* Radio nav */
    .stRadio > div { flex-direction: column; gap: 0 !important; }
    .stRadio > div > label {
        background: transparent !important;
        border-bottom: 1px solid #d4d0c8 !important;
        border-radius: 0 !important;
        padding: 8px 8px !important;
        font-family: 'Tahoma' !important; font-size: 12px !important;
        color: #003399 !important; margin: 0 !important;
    }
    .stRadio > div > label:hover { background: #fff !important; }

    /* Buttons */
    .stButton > button {
        background: #ece9d8 !important;
        border: 2px outset #fff !important;
        border-right-color: #aca899 !important; border-bottom-color: #aca899 !important;
        color: #000 !important; font-family: 'Tahoma' !important; font-size: 12px !important;
        border-radius: 3px !important;
    }

    .stDataFrame { border: 2px inset #d4d0c8; }
    .stSelectbox label, .stTextArea label {
        color: #000 !important; font-family: 'Tahoma' !important; font-size: 12px !important;
    }

    /* Nav info */
    .xp-sysinfo {
        font-family: 'Tahoma'; font-size: 10px; color: #555;
        padding: 6px 4px; border-top: 1px solid #d4d0c8; margin-top: 8px;
    }

    /* Taskbar */
    .xp-taskbar {
        position: fixed; bottom: 0; left: 0; right: 0;
        background: linear-gradient(180deg, #3168d5 0%, #1941a5 30%, #1941a5 70%, #3168d5 100%);
        height: 30px; display: flex; align-items: center; padding: 0 4px; z-index: 9999;
        border-top: 1px solid #5b8de5;
    }
    .xp-start {
        background: linear-gradient(180deg, #3b9c30 0%, #267d1b 100%);
        color: white; font-family: 'Trebuchet MS'; font-size: 12px; font-weight: bold;
        padding: 2px 10px; border-radius: 0 8px 8px 0; border: 1px solid #2d6e16;
        display: flex; align-items: center; gap: 4px; height: 24px;
    }
    .xp-ttab {
        background: linear-gradient(180deg, #3c7cf6 0%, #2f6ada 100%);
        color: white; font-family: 'Tahoma'; font-size: 11px; padding: 2px 12px;
        margin-left: 4px; border: 1px solid rgba(255,255,255,0.3); border-radius: 2px; height: 22px;
        display: flex; align-items: center;
    }
    .xp-ttab-a { background: linear-gradient(180deg, #1c5dcc 0%, #1450b8 100%); font-weight: bold; }
    .xp-clock {
        margin-left: auto; background: rgba(15,69,181,0.8); color: white;
        font-family: 'Tahoma'; font-size: 11px; padding: 0 12px; height: 24px;
        display: flex; align-items: center; border: 1px inset rgba(255,255,255,0.2);
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_engine():
    return create_engine("postgresql://grid_admin:ontario_grid_2026@localhost:5432/ontario_grid")

@st.cache_data(ttl=300)
def query_db(sql):
    return pd.read_sql(sql, get_engine())

FC = {"nuclear":"#7B68EE","hydro":"#4169E1","wind":"#228B22","solar":"#DAA520","gas":"#B22222","biofuel":"#6B8E23"}
LY = dict(template="plotly_white", font=dict(family="Tahoma",size=11,color="#000"),
    paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0.95)", margin=dict(l=0,r=0,t=30,b=0))


# ════════════════════════════════════════════════
# TWO WINDOWS ON BLISS DESKTOP
# ════════════════════════════════════════════════

nav_col, content_col = st.columns([1, 4], gap="medium")

# ── LEFT WINDOW: Navigation ──
with nav_col:
    st.markdown("""<div class="xp-titlebar">
        <span>📂 Grid Analytics</span>
        <div class="xp-btns"><div class="xp-b">_</div><div class="xp-b xp-bx">✕</div></div>
    </div>""", unsafe_allow_html=True)

    page = st.radio("nav", label_visibility="collapsed",
        options=["📊 Overview", "⚡ Generation", "💰 Prices", "🌱 Carbon", "🔍 Explorer"])

    st.markdown("""<div class="xp-sysinfo">
        <b>System</b><br>📡 PostgreSQL: Online<br>📁 Tables: 5<br>⚡ PySpark + Delta Lake
    </div>""", unsafe_allow_html=True)

# ── RIGHT WINDOW: Content with XP tabs ──
with content_col:
    st.markdown("""<div class="xp-titlebar xp-titlebar-r">
        <span>⚡ Ontario Grid Intelligence — Data Analytics</span>
        <div class="xp-btns"><div class="xp-b">_</div><div class="xp-b">□</div><div class="xp-b xp-bx">✕</div></div>
    </div>""", unsafe_allow_html=True)

    # XP tabs inside the right window
    tab1, tab2, tab3 = st.tabs(["Contents", "Charts", "Details"])

    if page == "📊 Overview":
        with tab1:
            try:
                lat = query_db("SELECT date,hour,ontario_demand,total_generation_mw,clean_energy_pct,hoep,carbon_intensity_gco2_kwh FROM fct_hourly_grid_snapshot WHERE total_generation_mw IS NOT NULL ORDER BY date DESC,hour DESC LIMIT 1")
                if not lat.empty:
                    r=lat.iloc[0]
                    c1,c2,c3,c4,c5=st.columns(5)
                    with c1: st.metric("Ontario Demand",f"{r['ontario_demand']:,.0f} MW")
                    with c2: v=r.get('total_generation_mw'); st.metric("Generation",f"{v:,.0f} MW" if pd.notna(v) else "—")
                    with c3: v=r.get('clean_energy_pct'); st.metric("Clean Energy",f"{v:.1f}%" if pd.notna(v) else "—")
                    with c4: v=r.get('hoep'); st.metric("HOEP",f"${v:.2f}" if pd.notna(v) else "—")
                    with c5: v=r.get('carbon_intensity_gco2_kwh'); st.metric("CO₂",f"{v:.0f} g/kWh" if pd.notna(v) else "—")
                daily = query_db("SELECT date,season,avg_demand_mw,peak_demand_mw,avg_price,avg_clean_energy_pct,avg_carbon_intensity,avg_temp_c FROM mart_daily_summary ORDER BY date DESC LIMIT 14")
                if not daily.empty:
                    daily=daily.sort_values("date")
                    for c in ["avg_price"]:
                        if c in daily.columns: daily[c]=pd.to_numeric(daily[c],errors="coerce")
                    daily=daily.fillna(0)
                    st.dataframe(daily,use_container_width=True,hide_index=True)
            except Exception as e: st.error(f"⚠ {e}")

        with tab2:
            try:
                d=query_db("SELECT date,hour,ontario_demand,market_demand FROM fct_hourly_grid_snapshot WHERE date>=(SELECT MAX(date)-7 FROM fct_hourly_grid_snapshot) ORDER BY date,hour")
                if not d.empty:
                    d["dt"]=pd.to_datetime(d["date"].astype(str))+pd.to_timedelta(d["hour"],unit="h")
                    fig=go.Figure()
                    fig.add_trace(go.Scatter(x=d["dt"],y=d["ontario_demand"],name="Ontario",line=dict(color="#003399",width=2),fill="tozeroy",fillcolor="rgba(0,51,153,0.08)"))
                    fig.add_trace(go.Scatter(x=d["dt"],y=d["market_demand"],name="Market",line=dict(color="#999",width=1,dash="dot")))
                    fig.update_layout(**LY,height=350,yaxis_title="MW",legend=dict(orientation="h",y=1.1))
                    st.plotly_chart(fig,use_container_width=True)
            except Exception as e: st.error(f"⚠ {e}")

        with tab3:
            st.markdown("#### 📖 Definitions")
            st.markdown("""
**Ontario Demand** — Total electricity being consumed in Ontario right now (MWw).  
**Generation** — Total electricity being produced by all fuel sources (MW). When Generation > Demand, Ontario is exporting surplus.  
**Clean Energy %** — `(Nuclear + Hydro + Wind + Solar + Biofuel) / Total Generation × 100`. Based on IESO fuel classification.  
**HOEP** — Hourly Ontario Energy Price ($/MWh). Set by IESO's real-time market based on supply/demand bidding.  
**CO₂** — Carbon intensity (gCO₂/kWh). Calculated using emission factors: Gas = 490 g/kWh, Biofuel = 50 g/kWh, all others = 0.  

**Daily Summary Table:**  
- `avg_demand_mw` — Average of all 24 hourly demand values for that day  
- `peak_demand_mw` — Highest single-hour demand  
- `avg_price` — Average HOEP across all hours (0 = no price data for that day)  
- `avg_clean_energy_pct` — Average clean energy percentage  
- `avg_carbon_intensity` — Average gCO₂/kWh  
- `avg_temp_c` — Average temperature in Toronto (°C)  

**Data Source:** IESO API → CSV → Delta Lake (Bronze → Silver → Gold) → PostgreSQL
            """)

    elif page == "⚡ Generation":
        with tab1:
            try:
                gen=query_db("SELECT date,hour,nuclear_mw,gas_mw,hydro_mw,wind_mw,solar_mw,biofuel_mw,total_generation_mw,clean_energy_pct FROM fct_hourly_grid_snapshot ORDER BY date,hour")
                if not gen.empty:
                    fc_cols=["nuclear_mw","gas_mw","hydro_mw","wind_mw","solar_mw","biofuel_mw"]
                    am=gen[fc_cols].mean(); am.index=[c.replace("_mw","").title() for c in am.index]
                    for f in am.index:
                        p=am[f]/am.sum()*100
                        st.markdown(f"`{f:10s}` {'█'*max(1,int(p*1.5))} **{p:.1f}%** ({am[f]:,.0f} MW)")
            except Exception as e: st.error(f"⚠ {e}")

        with tab2:
            try:
                gen=query_db("SELECT date,hour,nuclear_mw,gas_mw,hydro_mw,wind_mw,solar_mw,biofuel_mw FROM fct_hourly_grid_snapshot ORDER BY date,hour")
                if not gen.empty:
                    am=gen[["nuclear_mw","gas_mw","hydro_mw","wind_mw","solar_mw","biofuel_mw"]].mean()
                    am.index=[c.replace("_mw","").title() for c in am.index]
                    fig_pie=px.pie(values=am.values,names=am.index,color=am.index,
                        color_discrete_map={"Nuclear":FC["nuclear"],"Gas":FC["gas"],"Hydro":FC["hydro"],"Wind":FC["wind"],"Solar":FC["solar"],"Biofuel":FC["biofuel"]},hole=0.35)
                    fig_pie.update_layout(**LY,height=350)
                    st.plotly_chart(fig_pie,use_container_width=True)

                    rec=gen[gen["date"]>=gen["date"].max()-pd.Timedelta(days=7)].copy()
                    rec["dt"]=pd.to_datetime(rec["date"].astype(str))+pd.to_timedelta(rec["hour"],unit="h")
                    fig_s=go.Figure()
                    for fl,k in [("nuclear_mw","nuclear"),("hydro_mw","hydro"),("wind_mw","wind"),("solar_mw","solar"),("gas_mw","gas"),("biofuel_mw","biofuel")]:
                        fig_s.add_trace(go.Scatter(x=rec["dt"],y=rec[fl],name=fl.replace("_mw","").title(),stackgroup="one",line=dict(width=0.5,color=FC[k])))
                    fig_s.update_layout(**LY,height=350,yaxis_title="MW",legend=dict(orientation="h",y=1.1))
                    st.plotly_chart(fig_s,use_container_width=True)
            except Exception as e: st.error(f"⚠ {e}")

        with tab3:
            st.markdown("#### 📖 Definitions")
            st.markdown("""
**Nuclear** — Baseload power from stations like Bruce, Darlington, Pickering. Runs 24/7 at near-constant output (~10,000 MW).  
**Hydro** — Hydroelectric dams (Niagara Falls, etc). Flexible — can ramp up/down to match demand.  
**Wind** — Wind turbines across Ontario. Output depends on weather — can swing from 0 to 5,000 MW.  
**Solar** — Solar farms. Only generates during daytime. Peaks around noon.  
**Gas** — Natural gas plants. The "peaker" fuel — turns on during high demand. Main source of carbon emissions.  
**Biofuel** — Biomass/landfill gas. Small contribution (~50 MW avg).  

**Clean Energy %** = `(Nuclear + Hydro + Wind + Solar + Biofuel) / Total × 100`  
**Generation Stack** — Area chart showing how each fuel contributes hour by hour. Width = MW output.
            """)

    elif page == "💰 Prices":
        with tab1:
            try:
                pr=query_db("SELECT date,hour,hoep,season,temperature_c FROM fct_hourly_grid_snapshot WHERE hoep IS NOT NULL ORDER BY date,hour")
                if not pr.empty:
                    c1,c2,c3,c4=st.columns(4)
                    with c1: st.metric("Average",f"${pr['hoep'].mean():.2f}/MWh")
                    with c2: st.metric("Maximum",f"${pr['hoep'].max():.2f}/MWh")
                    with c3: st.metric("Minimum",f"${pr['hoep'].min():.2f}/MWh")
                    with c4: st.metric("Spikes",f"{len(pr[pr['hoep']>100])}")
            except Exception as e: st.error(f"⚠ {e}")

        with tab2:
            try:
                pr=query_db("SELECT date,hour,hoep,temperature_c FROM fct_hourly_grid_snapshot WHERE hoep IS NOT NULL ORDER BY date,hour")
                if not pr.empty:
                    pr["dt"]=pd.to_datetime(pr["date"].astype(str))+pd.to_timedelta(pr["hour"],unit="h")
                    fig_p=go.Figure()
                    fig_p.add_trace(go.Scatter(x=pr["dt"],y=pr["hoep"],line=dict(color="#003399",width=1),fill="tozeroy",fillcolor="rgba(0,51,153,0.08)"))
                    fig_p.add_hline(y=pr["hoep"].mean(),line_dash="dash",line_color="#999",annotation_text="Avg")
                    fig_p.update_layout(**LY,height=350,yaxis_title="$/MWh",showlegend=False)
                    st.plotly_chart(fig_p,use_container_width=True)

                    c1,c2=st.columns(2)
                    with c1:
                        ha=pr.groupby("hour")["hoep"].mean().reset_index()
                        fig_h=px.bar(ha,x="hour",y="hoep",color_discrete_sequence=["#003399"])
                        fig_h.update_layout(**LY,height=280,xaxis_title="Hour",yaxis_title="$/MWh")
                        st.plotly_chart(fig_h,use_container_width=True)
                    with c2:
                        tp=pr.dropna(subset=["temperature_c"])
                        if not tp.empty:
                            fig_t=px.scatter(tp.sample(min(500,len(tp))),x="temperature_c",y="hoep",color_discrete_sequence=["#B22222"],opacity=0.4)
                            fig_t.update_layout(**LY,height=280,xaxis_title="°C",yaxis_title="$/MWh")
                            st.plotly_chart(fig_t,use_container_width=True)
            except Exception as e: st.error(f"⚠ {e}")

        with tab3:
            st.markdown("#### 📖 Definitions")
            st.markdown("""
**HOEP** — Hourly Ontario Energy Price ($/MWh). The wholesale price generators are paid. Set by IESO's real-time market every hour.  
**Average** — Mean price across all hours in the dataset.  
**Maximum** — Highest single-hour price. Spikes happen during extreme heat/cold or supply shortages.  
**Minimum** — Lowest price. Can go negative when surplus power needs to be dumped.  
**Spikes** — Hours where HOEP > $100/MWh (roughly 3-5× normal).  

**Price by Hour** — Bar chart showing average price per hour of day. Peaks at 5-7 PM (dinner time = AC + cooking + lighting).  
**Price vs Temp** — Scatter plot. Shows U-shape: extreme cold (heating) and extreme heat (AC) both drive prices up.
            """)

    elif page == "🌱 Carbon":
        with tab1:
            try:
                cb=query_db("SELECT date,hour,carbon_intensity_gco2_kwh,carbon_category,gas_mw,season FROM mart_carbon_intensity ORDER BY date,hour")
                if not cb.empty:
                    c1,c2,c3,c4=st.columns(4)
                    with c1: st.metric("Avg",f"{cb['carbon_intensity_gco2_kwh'].mean():.0f} g/kWh")
                    with c2: st.metric("Cleanest",f"{cb['carbon_intensity_gco2_kwh'].min():.0f} g/kWh")
                    with c3: st.metric("Dirtiest",f"{cb['carbon_intensity_gco2_kwh'].max():.0f} g/kWh")
                    with c4: vc=len(cb[cb["carbon_category"]=="Very Clean"])/len(cb)*100; st.metric("Very Clean",f"{vc:.1f}%")
            except Exception as e: st.error(f"⚠ {e}")

        with tab2:
            try:
                cb=query_db("SELECT date,hour,carbon_intensity_gco2_kwh,gas_mw,season FROM mart_carbon_intensity ORDER BY date,hour")
                if not cb.empty:
                    cb["dt"]=pd.to_datetime(cb["date"].astype(str))+pd.to_timedelta(cb["hour"],unit="h")
                    fig_c=go.Figure()
                    fig_c.add_trace(go.Scatter(x=cb["dt"],y=cb["carbon_intensity_gco2_kwh"],line=dict(color="#228B22",width=1),fill="tozeroy",fillcolor="rgba(34,139,34,0.08)"))
                    fig_c.add_hline(y=50,line_dash="dash",line_color="#228B22",annotation_text="Very Clean")
                    fig_c.update_layout(**LY,height=350,yaxis_title="gCO₂/kWh",showlegend=False)
                    st.plotly_chart(fig_c,use_container_width=True)

                    c1,c2=st.columns(2)
                    with c1:
                        hc=cb.groupby("hour")["carbon_intensity_gco2_kwh"].mean().reset_index()
                        fig_hc=px.bar(hc,x="hour",y="carbon_intensity_gco2_kwh",color="carbon_intensity_gco2_kwh",color_continuous_scale=["#228B22","#DAA520","#B22222"])
                        fig_hc.update_layout(**LY,height=280,xaxis_title="Hour",yaxis_title="gCO₂/kWh",coloraxis_showscale=False)
                        st.plotly_chart(fig_hc,use_container_width=True)
                    with c2:
                        fig_g=px.scatter(cb.sample(min(800,len(cb))),x="gas_mw",y="carbon_intensity_gco2_kwh",color="season",
                            color_discrete_map={"Winter":"#4169E1","Spring":"#228B22","Summer":"#DAA520","Fall":"#CD853F"},opacity=0.5)
                        fig_g.update_layout(**LY,height=280,xaxis_title="Gas MW",yaxis_title="gCO₂/kWh")
                        st.plotly_chart(fig_g,use_container_width=True)
            except Exception as e: st.error(f"⚠ {e}")

        with tab3:
            st.markdown("#### 📖 Definitions")
            st.markdown("""
**Carbon Intensity** — Grams of CO₂ emitted per kilowatt-hour generated (gCO₂/kWh). Lower = cleaner.  
**Very Clean** — < 50 gCO₂/kWh (mostly nuclear + hydro, minimal gas).  
**Clean** — 50-100 gCO₂/kWh.  
**Moderate** — 100-200 gCO₂/kWh.  
**Dirty** — > 200 gCO₂/kWh (heavy gas usage).  

**Emission Factors Used:**  
- Nuclear, Hydro, Wind, Solar = 0 gCO₂/kWh  
- Biofuel = 50 gCO₂/kWh  
- Gas = 490 gCO₂/kWh  

**Carbon by Hour** — Shows when the grid is dirtiest (peak hours when gas ramps up).  
**Carbon vs Gas** — Scatter plot proving the direct relationship: more gas MW = higher carbon intensity.
            """)

    elif page == "🔍 Explorer":
        with tab1:
            try:
                table=st.selectbox("📁 Table:",["fct_hourly_grid_snapshot","mart_daily_summary","mart_carbon_intensity","dim_date","dim_fuel_type"])
                cnt=query_db(f"SELECT COUNT(*) as rows FROM {table}")
                st.info(f"📁 **{table}** — {cnt['rows'].iloc[0]:,} rows")
                st.dataframe(query_db(f"SELECT * FROM {table} LIMIT 100"),use_container_width=True,hide_index=True)
            except Exception as e: st.error(f"⚠ {e}")

        with tab2:
            st.markdown("Select a table from the Contents tab to preview data.")

        with tab3:
            try:
                sql=st.text_area("SQL:",value="SELECT * FROM fct_hourly_grid_snapshot LIMIT 10",height=80)
                if st.button("▶ Run"):
                    result=query_db(sql)
                    st.dataframe(result,use_container_width=True,hide_index=True)
                    st.success(f"✅ {len(result)} rows")
            except Exception as e: st.error(f"⚠ {e}")


# Taskbar
st.markdown("""
<div class="xp-taskbar">
    <div class="xp-start">🪟 start</div>
    <div class="xp-ttab xp-ttab-a">⚡ Ontario Grid Intelligence</div>
    <div class="xp-clock">🔊 7:30 PM</div>
</div>
""", unsafe_allow_html=True)
