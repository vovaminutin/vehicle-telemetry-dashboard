# 🚗 Vehicle Telemetry Dashboard

**Monitor, visualize, and explore vehicle performance in real-time – all from your browser!**

This interactive **Vehicle Telemetry Dashboard** simulates live car data, including engine RPM, speed, engine temperature, and fuel level. Built with **Streamlit** and **Plotly**, it delivers a sleek, dynamic experience that feels like a real car diagnostics system – but fully virtual and safe.  

---

## 🌟 Features

- **Real-Time Telemetry Simulation**  
  Watch engine and vehicle data change smoothly with each second.  

- **Interactive Gauges & Charts**  
  - Engine RPM  
  - Vehicle Speed  
  - Engine Temperature  
  - Fuel Level  
  Historical trends are displayed in easy-to-read charts.  

- **Customizable Simulation**  
  Control the simulation speed (Slow / Normal / Fast) to suit your testing needs.  

- **Session State Persistence**  
  All data persists as you interact with the dashboard, allowing continuous monitoring.  

- **User-Friendly Controls**  
  Start, stop, or reset the simulation with a single click.  

---

## 🚀 Demo

Run the dashboard locally and explore:

```bash
git clone https://github.com/vovaminutin/vehicle-telemetry-dashboard.git
cd vehicle-telemetry-dashboard
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
pip install -r requirements.txt
streamlit run main.py
