import streamlit as st
import pandas as pd
import time
import random
import logging
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
import uuid
import os
import json

# ================================
# --- APP SETUP ---
# ================================
st.set_page_config(page_title="Vehicle Diagnostic Dashboard", page_icon="🚗", layout="wide")
st.title("🚗 Vehicle Diagnostic Dashboard")
st.markdown("### Real-time vehicle telemetry and performance simulation")

# ================================
# --- LOGGING SETUP ---
# ================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ================================
# --- SESSION STATE ---
# ================================
def _empty_log_df():
    return pd.DataFrame({
        "Time": pd.Series(dtype="string"),
        "RPM": pd.Series(dtype="int32"),
        "Speed": pd.Series(dtype="float32"),
        "Temp": pd.Series(dtype="float32"),
        "Fuel Level": pd.Series(dtype="float32"),
    })

if "data_log" not in st.session_state:
    st.session_state.data_log = _empty_log_df()
if "running" not in st.session_state:
    st.session_state.running = False
if "telemetry" not in st.session_state:
    st.session_state.telemetry = {"rpm": 900, "speed": 0, "temp": 75, "fuel": 100}
if "distance_km" not in st.session_state:
    st.session_state.distance_km = 0.0
if "last_alerts" not in st.session_state:
    st.session_state.last_alerts = set()
if "settings" not in st.session_state:
    st.session_state.settings = {
        "profile": "Normal",  # Eco | Normal | Sport
        "thresholds": {"temp_high": 110.0, "fuel_low": 10.0, "rpm_high": 6000},
        "max_rows": 5000,
        "points_window": 500,
        "smoothing_window": 1,
        "selected_params": ["RPM", "Speed", "Temp", "Fuel Level"],
        "faults": {"heat_spike": False, "fuel_leak": False, "rpm_spike": False},
    }

# ================================
# --- THEME / CSS ---
# ================================
def load_css(path: str):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except Exception as e:
        logger.warning(f"Could not load CSS from {path}: {e}")

load_css(os.path.join("assets", "styles.css"))

# ================================
# --- SIDEBAR CONTROLS ---
# ================================
st.sidebar.header("⚙️ Controls")

start_button = st.sidebar.button("▶ Start Monitoring")
stop_button = st.sidebar.button("⏸ Stop Monitoring")
reset_button = st.sidebar.button("🔄 Reset Data")

speed_mode = st.sidebar.selectbox(
    "Simulation Speed",
    options=["Normal", "Fast", "Slow"],
    index=0
)
interval = {"Fast": 0.3, "Normal": 1.0, "Slow": 2.0}[speed_mode]

# Status badge
status_color = "green" if st.session_state.running else "gray"
status_text = "Running" if st.session_state.running else "Paused"
st.sidebar.markdown(
    f"<div class='status-badge' style='margin-top:6px'><span class='dot' style='background:{status_color}'></span>{status_text}</div>",
    unsafe_allow_html=True,
)

# Export data as CSV
if not st.session_state.data_log.empty:
    csv = st.session_state.data_log.to_csv(index=False).encode("utf-8")
    st.sidebar.download_button("💾 Download CSV", csv, "telemetry_log.csv", "text/csv")
    # JSON export
    json_bytes = st.session_state.data_log.to_json(orient="records").encode("utf-8")
    st.sidebar.download_button("🗂️ Download JSON", json_bytes, "telemetry_log.json", "application/json")

# ================================
# --- HELPER FUNCTIONS ---
# ================================
def update_value(current, min_val, max_val, variation):
    """Gradually update a telemetry value within limits."""
    delta = random.uniform(-variation, variation)
    new_val = current + delta
    return max(min_val, min(max_val, new_val))

def create_gauge(value, title, min_val, max_val, unit, color):
    """Generate a Plotly gauge chart."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={'text': title, 'font': {'size': 18, 'color': '#0f172a'}},
        gauge={
            'axis': {'range': [min_val, max_val], 'tickcolor': '#334155'},
            'bar': {'color': color, 'thickness': 0.35},
            'bgcolor': 'rgba(0,0,0,0)',
            'borderwidth': 0,
            'steps': [
                {'range': [min_val, max_val], 'color': '#eef2f7'}
            ],
        },
        number={'suffix': f" {unit}", 'font': {'color': '#0f172a'}}
    ))
    fig.update_layout(
        margin=dict(t=10, b=10, l=10, r=10),
        autosize=True,
        template='plotly_white',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=220,
    )
    return fig

def log_telemetry(t):
    """Append telemetry data to the session dataframe."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")
    new_row = pd.DataFrame([{
        "Time": timestamp,
        "RPM": int(t["rpm"]),
        "Speed": round(t["speed"], 1),
        "Temp": round(t["temp"], 1),
        "Fuel Level": round(t["fuel"], 1)
    }])
    st.session_state.data_log = pd.concat(
        [st.session_state.data_log, new_row],
        ignore_index=True
    )
    # Cap rows to prevent memory bloat
    max_rows = int(st.session_state.settings.get("max_rows", 5000))
    if len(st.session_state.data_log) > max_rows:
        st.session_state.data_log = st.session_state.data_log.tail(max_rows).reset_index(drop=True)

def generate_alerts(t, thresholds):
    alerts = []
    if t["temp"] > thresholds.get("temp_high", 110):
        alerts.append("⚠️ Engine Overheating!")
    if t["fuel"] < thresholds.get("fuel_low", 10):
        alerts.append("⛽ Low Fuel Level!")
    if t["rpm"] > thresholds.get("rpm_high", 6000):
        alerts.append("🚨 RPM limit reached!")
    return alerts

PROFILE_CONFIG = {
    "Eco": {
        "rpm_var": 90,
        "speed_var": 2.5,
        "temp_var": 0.2,
        "base_fuel_rate": 0.0008,  # % per second base
        "speed_fuel_factor": 0.000010,  # % per sec per km/h
    },
    "Normal": {
        "rpm_var": 140,
        "speed_var": 4.0,
        "temp_var": 0.3,
        "base_fuel_rate": 0.0012,
        "speed_fuel_factor": 0.000016,
    },
    "Sport": {
        "rpm_var": 200,
        "speed_var": 6.0,
        "temp_var": 0.4,
        "base_fuel_rate": 0.0018,
        "speed_fuel_factor": 0.000024,
    },
}

# ================================
# --- BUTTON ACTIONS ---
# ================================
if start_button:
    st.session_state.running = True
    logger.info("Simulation started.")
elif stop_button:
    st.session_state.running = False
    logger.info("Simulation paused.")
elif reset_button:
    st.session_state.data_log = _empty_log_df()
    st.session_state.telemetry = {"rpm": 900, "speed": 0, "temp": 75, "fuel": 100}
    st.session_state.distance_km = 0.0
    st.session_state.last_alerts = set()
    st.session_state.running = False
    st.success("✅ Data reset complete.")
    logger.info("Data reset complete.")

# ================================
# --- SIMULATION UPDATE (ONE STEP) ---
# ================================
t = st.session_state.telemetry
if st.session_state.running:
    s = st.session_state.settings
    prof = PROFILE_CONFIG.get(s["profile"], PROFILE_CONFIG["Normal"])

    # Telemetry updates influenced by profile and faults
    rpm_var = prof["rpm_var"] * (1.4 if s["faults"].get("rpm_spike") else 1.0)
    speed_var = prof["speed_var"]
    temp_var = prof["temp_var"]

    t["rpm"] = update_value(t["rpm"], 800, 6500, rpm_var)
    t["speed"] = update_value(t["speed"], 0, 220, speed_var)
    t["temp"] = update_value(t["temp"], 70, 125, temp_var)
    if s["faults"].get("heat_spike"):
        t["temp"] = min(150, t["temp"] + random.uniform(0.2, 0.8))

    # Fuel consumption model (% per second)
    base = prof["base_fuel_rate"]
    factor = prof["speed_fuel_factor"]
    leak_extra = 0.001 if s["faults"].get("fuel_leak") else 0.0
    fuel_drop = (base + factor * max(t["speed"], 0) + leak_extra) * interval
    t["fuel"] = max(0.0, t["fuel"] - fuel_drop * 100)  # convert to %

    # Distance integration (km)
    st.session_state.distance_km += max(t["speed"], 0) * (interval / 3600.0)

    # Log telemetry
    log_telemetry(t)

    # Handle new alerts
    thresholds = st.session_state.settings["thresholds"]
    alerts = generate_alerts(t, thresholds)
    new_alerts = set(alerts) - st.session_state.last_alerts
    for a in new_alerts:
        st.toast(a)
    st.session_state.last_alerts = set(alerts)

# ================================
# --- MAIN DASHBOARD ---
# ================================

# We build tabs and widget controls once per run.
def get_tabs():
    return st.tabs(["Overview", "Charts", "Data", "Settings"])

def render_overview_controls_and_get_container(tab):
    with tab:
        container = st.container()
    return container

def render_charts_controls_and_get_container(tab, df, key_prefix: str = ""):
    with tab:
        settings = st.session_state.settings
        cols = ["RPM", "Speed", "Temp", "Fuel Level"]
        selected = st.multiselect("Parameters", cols, key=f"{key_prefix}charts_params", default=[c for c in settings["selected_params"] if c in cols])
        settings["selected_params"] = selected or cols

        points_window = st.slider("Points window", min_value=100, max_value=5000, value=int(settings["points_window"]), key=f"{key_prefix}charts_points")
        settings["points_window"] = int(points_window)

        smooth = st.slider("Smoothing window (rolling)", min_value=1, max_value=50, value=int(settings["smoothing_window"]), key=f"{key_prefix}charts_smooth")
        settings["smoothing_window"] = int(smooth)

        container = st.container()
    return container

def render_data_controls_and_get_container(tab, df, key_prefix: str = ""):
    with tab:
        st.markdown("#### 🔍 Recorded Data")
        cols = list(df.columns)
        view_cols = st.multiselect("Columns", cols, default=cols, key=f"{key_prefix}data_columns")
        query = st.text_input("Filter contains", "", key=f"{key_prefix}data_filter")
        container = st.container()
    return container

def render_settings(tab, key_prefix: str = ""):
    with tab:
        st.markdown("#### ⚙️ Simulation Settings")
        s = st.session_state.settings
        s["profile"] = st.selectbox("Driving profile", ["Eco", "Normal", "Sport"], index=["Eco","Normal","Sport"].index(s["profile"]), key=f"{key_prefix}settings_profile")
        st.markdown("##### Alert thresholds")
        col1, col2, col3 = st.columns(3)
        s["thresholds"]["temp_high"] = col1.number_input("Temp high (°C)", value=float(s["thresholds"]["temp_high"]), key=f"{key_prefix}th_temp_high")
        s["thresholds"]["fuel_low"] = col2.number_input("Fuel low (%)", value=float(s["thresholds"]["fuel_low"]), key=f"{key_prefix}th_fuel_low")
        s["thresholds"]["rpm_high"] = col3.number_input("RPM high", value=int(s["thresholds"]["rpm_high"]), key=f"{key_prefix}th_rpm_high")

        st.markdown("##### Data & chart")
        col4, col5 = st.columns(2)
        s["max_rows"] = int(col4.number_input("Max log rows", min_value=1000, max_value=100000, value=int(s["max_rows"]), key=f"{key_prefix}set_max_rows"))
        s["points_window"] = int(col5.number_input("Default points window", min_value=100, max_value=5000, value=int(s["points_window"]), key=f"{key_prefix}set_points_window"))
        s["smoothing_window"] = int(st.number_input("Default smoothing window", min_value=1, max_value=50, value=int(s["smoothing_window"]), key=f"{key_prefix}set_smoothing_window") )

        st.markdown("##### Fault injection (for testing)")
        fcol1, fcol2, fcol3 = st.columns(3)
        with fcol1:
            s["faults"]["heat_spike"] = bool(st.toggle("Heat spike", value=bool(s["faults"].get("heat_spike", False)), key=f"{key_prefix}fault_heat_spike"))
        with fcol2:
            s["faults"]["fuel_leak"] = bool(st.toggle("Fuel leak", value=bool(s["faults"].get("fuel_leak", False)), key=f"{key_prefix}fault_fuel_leak"))
        with fcol3:
            s["faults"]["rpm_spike"] = bool(st.toggle("RPM spike", value=bool(s["faults"].get("rpm_spike", False)), key=f"{key_prefix}fault_rpm_spike"))

# Build UI: tabs, controls, and containers (once per run)
df = st.session_state.data_log
tab_overview, tab_charts, tab_data, tab_settings = get_tabs()
overview_container = render_overview_controls_and_get_container(tab_overview)
charts_container = render_charts_controls_and_get_container(tab_charts, df, key_prefix="ui_")
data_container = render_data_controls_and_get_container(tab_data, df, key_prefix="ui_")
render_settings(tab_settings, key_prefix="ui_")

# Create stable placeholders once
with overview_container:
    _mcola, _mcolb, _mcolc, _mcold = st.columns(4)
    metric_placeholders = [_mcola.empty(), _mcolb.empty(), _mcolc.empty(), _mcold.empty()]
    _g1, _g2, _g3, _g4 = st.columns(4)
    gauge_placeholders = [_g1.empty(), _g2.empty(), _g3.empty(), _g4.empty()]
    alerts_placeholder = st.empty()

with charts_container:
    chart_placeholder = st.empty()

with data_container:
    table_placeholder = st.empty()

# ================================
# --- RENDER CURRENT STATE ---
# ================================
df_loop = st.session_state.data_log

# Update metrics
avg_speed = df_loop['Speed'].mean() if not df_loop.empty else 0.0
max_rpm = df_loop['RPM'].max() if not df_loop.empty else 0
metric_placeholders[0].metric("Average Speed", f"{avg_speed:.1f} km/h")
metric_placeholders[1].metric("Max RPM", f"{max_rpm:.0f} rpm")
metric_placeholders[2].metric("Fuel Remaining", f"{t['fuel']:.1f} %")
metric_placeholders[3].metric("Distance", f"{st.session_state.distance_km:.2f} km")

# Update gauges
gauge_placeholders[0].plotly_chart(create_gauge(t["rpm"], "Engine RPM", 0, 7000, "rpm", "#007BFF"), key="gauge_rpm", use_container_width=True)
gauge_placeholders[1].plotly_chart(create_gauge(t["speed"], "Speed", 0, 250, "km/h", "#28A745"), key="gauge_speed", use_container_width=True)
gauge_placeholders[2].plotly_chart(create_gauge(t["temp"], "Engine Temp", 0, 150, "°C", "#FFC107"), key="gauge_temp", use_container_width=True)
gauge_placeholders[3].plotly_chart(create_gauge(t["fuel"], "Fuel Level", 0, 100, "%", "#DC3545"), key="gauge_fuel", use_container_width=True)

# Update alerts
thresholds = st.session_state.settings["thresholds"]
alerts = generate_alerts(t, thresholds)
alerts_placeholder.empty()
with alerts_placeholder:
    if alerts:
        for alert in alerts:
            st.warning(alert)

# Update charts
cols = ["RPM", "Speed", "Temp", "Fuel Level"]
selected = [c for c in st.session_state.settings["selected_params"] if c in cols] or cols
points_window = int(st.session_state.settings["points_window"])
smooth = int(st.session_state.settings["smoothing_window"])
df_plot = df_loop.tail(points_window).copy()
for col in cols:
    df_plot[col] = pd.to_numeric(df_plot[col], errors="coerce")
if smooth > 1:
    for c in selected:
        df_plot[c] = df_plot[c].rolling(window=smooth, min_periods=1).mean()
fig = px.line(df_plot, x="Time", y=selected, title="Telemetry Over Time")
fig.update_layout(
    legend_title_text="Parameters",
    xaxis_title="Time",
    yaxis_title="Value",
    xaxis=dict(rangeslider=dict(visible=True)),
    template='plotly_white',
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    height=420,
)
chart_placeholder.plotly_chart(fig, use_container_width=True, key="main_chart")

# Update data table
cols_data = list(df_loop.columns)
view_cols = [c for c in st.session_state.get("ui_data_columns", cols_data) if c in cols_data] if "ui_data_columns" in st.session_state else cols_data
query = st.session_state.get("ui_data_filter", "")
view = df_loop[view_cols] if view_cols else df_loop
if query:
    view = view[view.apply(lambda r: r.astype(str).str.contains(query, case=False, na=False).any(), axis=1)]
table_placeholder.dataframe(view.tail(1000), use_container_width=True)

# ================================
# --- AUTO-RELOAD FOR SIMULATION ---
# ================================
if st.session_state.running:
    # Streamlit-native rerun to continue simulation without full page reload
    time.sleep(interval)
    st.rerun()