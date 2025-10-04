# utils.py
import random
import math

def init_vehicle_state():
    """
    Initial state for the simulated vehicle.
    Keep values realistic-ish for passenger cars.
    """
    return {
        "rpm": 800,           # idle RPM
        "speed": 0.0,         # km/h
        "throttle": 0.0,      # 0..100 %
        "coolant_temp": 70.0, # degrees C
        "fuel_rate": 0.5,     # L/h-ish base value
        "maf": 2.0,           # g/s
        "oil_temp": 70.0,     # degrees C
        "load": 10.0          # engine load %
    }

def simulate_step(state, accel_request=0.0, road_slope=0.0, dt=1.0, driving_mode="Normal"):
    """
    Advance the vehicle state by one timestep (dt seconds).
    - accel_request: driver demand (-1.0 .. 1.0), negative for braking
    - road_slope: incline (positive uphill in degrees, negative downhill)
    - driving_mode: "Eco", "Normal", "Sport"
    Returns a new state dict.
    """
    s = state.copy()

    # Driving mode multipliers (affect aggressiveness)
    mode_aggression = {"Eco": 0.6, "Normal": 1.0, "Sport": 1.3}.get(driving_mode, 1.0)

    # Update throttle requested by driver
    # accel_request -1..1 -> throttle 0..100
    requested_throttle = max(0.0, min(100.0, (accel_request * mode_aggression * 50.0) + s["throttle"]))
    # Add small smoothing
    s["throttle"] = s["throttle"] + (requested_throttle - s["throttle"]) * 0.2

    # Speed dynamics (very simplified)
    # thrust ~ throttle, resistance ~ speed^2, slope effect
    thrust = s["throttle"] * 0.05  # arbitrary scale to km/h per dt
    drag = 0.02 * (s["speed"] ** 2) / 100.0
    slope_effect = -road_slope * 0.2  # uphill reduces speed, downhill increases
    s["speed"] = max(0.0, s["speed"] + (thrust - drag + slope_effect) * (dt / 1.0))

    # RPM roughly proportional to speed (and throttle when idle)
    # For low speeds RPM can be higher at idle
    gear_ratio = 4.0  # simplified
    target_rpm = max(700, (s["speed"] * gear_ratio * 30) + s["throttle"] * 2)
    # Smooth rpm
    s["rpm"] = int(s["rpm"] + (target_rpm - s["rpm"]) * 0.25 + random.uniform(-20, 20))

    # Coolant and oil temperature drift towards an operating temp depending on load
    engine_temp_target = 70.0 + (s["load"] / 100.0) * 20.0  # base 70 C, + up to 20 depending on load
    s["coolant_temp"] += (engine_temp_target - s["coolant_temp"]) * 0.05 + random.uniform(-0.2, 0.2)
    s["oil_temp"] += (engine_temp_target - s["oil_temp"]) * 0.03 + random.uniform(-0.1, 0.1)

    # Engine load approximated by throttle + speed
    s["load"] = min(100.0, max(0.0, s["throttle"] * 0.6 + (s["speed"] / 2.0)))

    # Fuel rate (L/h) simplified as function of rpm & load & mode
    base_fuel = 0.3 + (s["rpm"] / 6000.0) * 2.0
    s["fuel_rate"] = base_fuel * (1.0 + s["load"] / 100.0) * (1.0 if driving_mode == "Normal" else (0.9 if driving_mode == "Eco" else 1.15))
    # MAF sensor (mass air flow) proxy
    s["maf"] = 1.0 + (s["rpm"] / 1000.0) * (s["throttle"] / 100.0) * 2.0

    # Add small random jitter to mimic sensor noise
    s["rpm"] = int(max(600, s["rpm"] + random.randint(-10, 10)))
    s["coolant_temp"] = round(s["coolant_temp"], 1)
    s["oil_temp"] = round(s["oil_temp"], 1)
    s["maf"] = round(s["maf"], 2)
    s["fuel_rate"] = round(s["fuel_rate"], 3)
    s["speed"] = round(s["speed"], 1)
    s["throttle"] = round(s["throttle"], 1)
    s["load"] = round(s["load"], 1)

    return s

def check_faults(state):
    """
    Basic fault generator logic (Phase 1: simulated).
    Returns a list of fault dicts (code, description, severity).
    """
    faults = []
    # Example: if coolant_temp too high
    if state["coolant_temp"] > 105:
        faults.append({"code": "P0217", "desc": "Engine Overtemperature", "severity": "High"})
    # Example: rough idle or misfire (random chance when rpm fluctuates)
    if state["rpm"] < 700 and random.random() < 0.02:
        faults.append({"code": "P0300", "desc": "Random/Multiple Cylinder Misfire Detected", "severity": "Medium"})
    # Low oil temp (cold start) — not a fault but info
    if state["oil_temp"] < 40:
        faults.append({"code": "INFO001", "desc": "Oil temperature below optimal", "severity": "Info"})
    return faults
