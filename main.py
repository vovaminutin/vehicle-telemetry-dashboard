import streamlit as st
import pandas as pd
import time
import random
from datetime import datetime
import plotly.graph_objects as go
import uuid

# --- Page setup ---
st.set_page_config(page_title="Vehicle Diagnostic Dashboard", page_icon="🚗", layout="wide")

st.title("🚗 Vehicle Diagnostic Dashboard")
st.markdown("### Real-time vehicle telemetry and performance simulation")

# --- Initialize session state ---
if "data_log" not in st.session_state:
    st.session_state.data_log = pd.DataFrame(columns=["Time", "RPM", "Speed", "Temp", "Fuel Level"])
if "running" not in st.session_state:
    st.session_state.running = False
if "telemetry" not in st.session_state:
    st.session_state.telemetry = {"rpm": 900, "speed": 0, "temp": 75, "fuel": 100}

# --- Sidebar controls ---
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

# --- Helper: gradual telemetry update ---
def update_value(current, min_val, max_val, variation):
    delta = random.uniform(-variation, variation)
    new_val = current + delta
    return max(min_val, min(max_val, new_val))

# --- Gauge creation function ---
def create_gauge(value, title, min_val, max_val, unit, color):
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

# --- Button actions ---
if start_button:
    st.session_state.running = True
elif stop_button:
    st.session_state.running = False
elif reset_button:
    st.session_state.data_log = pd.DataFrame(columns=["Time", "RPM", "Speed", "Temp", "Fuel Level"])
    st.session_state.running = False
    st.session_state.telemetry = {"rpm": 900, "speed": 0, "temp": 75, "fuel": 100}
    st.success("Data reset complete.")

# --- Main placeholder ---
placeholder = st.empty()

# --- Real-time simulation ---
if st.session_state.running:
    while st.session_state.running:
        t = st.session_state.telemetry

        # Smooth telemetry updates
        t["rpm"] = update_value(t["rpm"], 800, 6500, 150)
        t["speed"] = update_value(t["speed"], 0, 220, 5)
        t["temp"] = update_value(t["temp"], 70, 120, 0.3)
        t["fuel"] = update_value(t["fuel"], 0, 100, 0.05)

        timestamp = datetime.now().strftime("%H:%M:%S.%f")
        new_row = pd.DataFrame([{
            "Time": timestamp,
            "RPM": int(t["rpm"]),
            "Speed": round(t["speed"], 1),
            "Temp": round(t["temp"], 1),
            "Fuel Level": round(t["fuel"], 1)
        }], columns=st.session_state.data_log.columns)

        # Concatenate safely
        st.session_state.data_log = pd.concat(
            [st.session_state.data_log, new_row],
            ignore_index=True,
            axis=0
        )

        # --- Render gauges and chart ---
        with placeholder.container():
            col1, col2, col3, col4 = st.columns(4)
            col1.plotly_chart(create_gauge(t["rpm"], "Engine RPM", 0, 7000, "rpm", "#007BFF"),
                              config={}, key=f"rpm_{uuid.uuid4().hex}")
            col2.plotly_chart(create_gauge(t["speed"], "Speed", 0, 250, "km/h", "#28A745"),
                              config={}, key=f"speed_{uuid.uuid4().hex}")
            col3.plotly_chart(create_gauge(t["temp"], "Engine Temp", 0, 150, "°C", "#FFC107"),
                              config={}, key=f"temp_{uuid.uuid4().hex}")
            col4.plotly_chart(create_gauge(t["fuel"], "Fuel Level", 0, 100, "%", "#DC3545"),
                              config={}, key=f"fuel_{uuid.uuid4().hex}")

            st.markdown("### 📊 Telemetry History")
            df_plot = st.session_state.data_log.copy()
            # Ensure numeric types
            for col in ["RPM", "Speed", "Temp", "Fuel Level"]:
                df_plot[col] = pd.to_numeric(df_plot[col], errors="coerce")
            st.line_chart(df_plot, x="Time", y=["RPM", "Speed", "Temp", "Fuel Level"])

        time.sleep(interval)

# --- Last recorded data ---
if not st.session_state.data_log.empty:
    st.markdown("### 🔍 Last Recorded Data")
    st.dataframe(st.session_state.data_log.tail(10))
else:
    st.info("No data recorded yet.")
