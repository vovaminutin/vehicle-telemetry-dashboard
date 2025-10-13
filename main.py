import streamlit as st
import pandas as pd
import time
import random
import logging
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
import uuid

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
if "data_log" not in st.session_state:
    st.session_state.data_log = pd.DataFrame(columns=["Time", "RPM", "Speed", "Temp", "Fuel Level"])
if "running" not in st.session_state:
    st.session_state.running = False
if "telemetry" not in st.session_state:
    st.session_state.telemetry = {"rpm": 900, "speed": 0, "temp": 75, "fuel": 100}

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

# Export data as CSV
if not st.session_state.data_log.empty:
    csv = st.session_state.data_log.to_csv(index=False).encode("utf-8")
    st.sidebar.download_button("💾 Download CSV", csv, "telemetry_log.csv", "text/csv")

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
        title={'text': title, 'font': {'size': 18}},
        gauge={
            'axis': {'range': [min_val, max_val]},
            'bar': {'color': color},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#ccc",
        },
        number={'suffix': f" {unit}"}
    ))
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), autosize=True)
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
    st.session_state.data_log = pd.DataFrame(columns=["Time", "RPM", "Speed", "Temp", "Fuel Level"])
    st.session_state.telemetry = {"rpm": 900, "speed": 0, "temp": 75, "fuel": 100}
    st.session_state.running = False
    st.success("✅ Data reset complete.")
    logger.info("Data reset complete.")

# ================================
# --- MAIN DASHBOARD ---
# ================================
placeholder = st.empty()

if st.session_state.running:
    while st.session_state.running:
        t = st.session_state.telemetry

        # Smooth telemetry updates
        t["rpm"] = update_value(t["rpm"], 800, 6500, 150)
        t["speed"] = update_value(t["speed"], 0, 220, 5)
        t["temp"] = update_value(t["temp"], 70, 120, 0.3)
        t["fuel"] = update_value(t["fuel"], 0, 100, 0.05)

        # Log telemetry
        log_telemetry(t)

        # ================================
        # --- ALERTS ---
        # ================================
        alerts = []
        if t["temp"] > 110:
            alerts.append("⚠️ Engine Overheating!")
        if t["fuel"] < 10:
            alerts.append("⛽ Low Fuel Level!")
        if t["rpm"] > 6000:
            alerts.append("🚨 RPM limit reached!")

        with placeholder.container():
            # KPI metrics
            col_a, col_b, col_c = st.columns(3)
            df = st.session_state.data_log
            col_a.metric("Average Speed", f"{df['Speed'].mean():.1f} km/h")
            col_b.metric("Max RPM", f"{df['RPM'].max():.0f} rpm")
            col_c.metric("Fuel Remaining", f"{t['fuel']:.1f} %")

            # Gauges
            col1, col2, col3, col4 = st.columns(4)
            col1.plotly_chart(create_gauge(t["rpm"], "Engine RPM", 0, 7000, "rpm", "#007BFF"),
                              config={}, key=f"rpm_{uuid.uuid4().hex}")
            col2.plotly_chart(create_gauge(t["speed"], "Speed", 0, 250, "km/h", "#28A745"),
                              config={}, key=f"speed_{uuid.uuid4().hex}")
            col3.plotly_chart(create_gauge(t["temp"], "Engine Temp", 0, 150, "°C", "#FFC107"),
                              config={}, key=f"temp_{uuid.uuid4().hex}")
            col4.plotly_chart(create_gauge(t["fuel"], "Fuel Level", 0, 100, "%", "#DC3545"),
                              config={}, key=f"fuel_{uuid.uuid4().hex}")

            # Alerts
            for alert in alerts:
                st.warning(alert)

            # Interactive chart
            st.markdown("### 📊 Telemetry History")
            df_plot = df.copy()
            for col in ["RPM", "Speed", "Temp", "Fuel Level"]:
                df_plot[col] = pd.to_numeric(df_plot[col], errors="coerce")

            fig = px.line(df_plot, x="Time", y=["RPM", "Speed", "Temp", "Fuel Level"],
                          title="Telemetry Over Time")
            fig.update_layout(legend_title_text="Parameters", xaxis_title="Time", yaxis_title="Value")
            st.plotly_chart(fig, use_container_width=True)

        time.sleep(interval)

# ================================
# --- LAST RECORDED DATA ---
# ================================
if not st.session_state.data_log.empty:
    st.markdown("### 🔍 Last Recorded Data")
    st.dataframe(st.session_state.data_log.tail(10))
else:
    st.info("No data recorded yet.")
