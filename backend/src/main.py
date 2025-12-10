import json
import numpy as np
from fastapi import FastAPI, Body, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional

# ==============================
#    Swagger & App Config
# ==============================
tags_metadata = [
    {
        "name": "Frontend",
        "description": "Endpoints used by the **React UI**. Defined first to avoid path collisions.",
    },
    {
        "name": "Sensor",
        "description": "Endpoints used by the **physical hardware**.",
    },
]

app = FastAPI(
    title="Spectrum Sensor API",
    description="API for controlling remote spectrum sensors and visualizing data.",
    version="1.3.0",
    openapi_tags=tags_metadata
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================
#       Data Storage
# ==============================

# --- Load Valid MACs ---
def load_valid_macs():
    try:
        with open("src/macs.json", "r") as f:
            return set(json.load(f))
    except FileNotFoundError:
        # Fallback for dev if file doesn't exist
        return {"d0:65:78:9c:dd:d0", "d0:65:78:9c:dd:d1", "d0:65:78:9c:dd:d2"}

VALID_MACS = load_valid_macs()

# --- In-Memory Storage ---
# Structure: { 
#   "aa:bb:cc...": { 
#       "config": {...} | None, 
#       "metrics": {...}, 
#       "data": {...} 
#   } 
# }
device_state: Dict[str, Dict[str, Any]] = {}

# ==============================
#      Helper Functions
# ==============================

def log_json(title: str, data: Any):
    print(f"\n{'='*20} {title} {'='*20}")
    print(json.dumps(data, indent=4, default=str))
    print("=" * (42 + len(title)) + "\n")

def get_default_config():
    return {
        "center_freq_hz": 9800000,
        "resolution_hz": 10000,
        "sample_rate_hz": 20000000,
        "span": 20000000,
        "scale": "dbm",
        "window": "hamming",
        "overlap": 0.5,
        "lna_gain": 0,
        "vga_gain": 0,
        "antenna_amp": False,
        "demodulation": {
            "bw_hz": 250000,
            "center_freq_hz": 9800000,
            "port_socket": "/1234"
        }
    }

def get_device_store(mac: str):
    """Ensures device has storage initialized if valid."""
    if mac not in VALID_MACS:
        raise HTTPException(status_code=403, detail=f"Access Denied: MAC '{mac}' not in whitelist.")
    
    if mac not in device_state:
        device_state[mac] = {
            "config": get_default_config(),
            "metrics": {},
            "data": {} 
        }
    return device_state[mac]

def calculate_rf_metrics(pxx: list):
    """
    Calculates statistical RF metrics from the Power Spectral Density array.
    """
    if not pxx or len(pxx) == 0:
        return {
            "noise_floor_dbm": 0,
            "peak_power_dbm": 0,
            "avg_power_dbm": 0,
            "snr_db": 0,
            "auto_threshold_dbm": 0
        }

    # Convert to numpy array for fast math
    arr = np.array(pxx)

    # 1. Peak Power (Max value in the sweep)
    peak_power = float(np.max(arr))

    # 2. Noise Floor Estimation (Median is robust against peaks)
    noise_floor = float(np.median(arr))

    # 3. Auto Threshold (Noise Floor + 6dB margin)
    auto_threshold = noise_floor + 6.0 

    # 4. Signal-to-Noise Ratio (SNR)
    snr = peak_power - noise_floor

    return {
        "noise_floor_dbm": round(noise_floor, 2),
        "peak_power_dbm": round(peak_power, 2),
        "avg_power_dbm": round(float(np.mean(arr)), 2),
        "snr_db": round(snr, 2),
        "auto_threshold_dbm": round(auto_threshold, 2)
    }

# ==============================
#    FRONTEND ENDPOINTS
# ==============================
# Defined BEFORE /{mac}/ to avoid path collisions.

@app.get("/api/v1/front/metrics", tags=["Frontend"])
async def get_frontend_metrics(mac: str):
    """
    **View Sensor Health**
    """
    store = get_device_store(mac)
    return store["metrics"]

@app.get("/api/v1/front/data", tags=["Frontend"])
async def get_frontend_data(mac: str):
    """
    **Poll Spectrum Data**
    Returns raw Pxx data PLUS calculated RF metrics.
    """
    store = get_device_store(mac)
    raw_data = store.get("data", {})
    
    # Handle case where no data exists yet
    if not raw_data or "Pxx" not in raw_data:
        return {
            "start_freq_hz": 0,
            "end_freq_hz": 0,
            "Pxx": [],
            "metrics": {}
        }

    # 1. Get the Raw Data
    pxx = raw_data.get("Pxx", [])

    # 2. Calculate Metrics on the fly
    rf_stats = calculate_rf_metrics(pxx)

    # 3. Construct the Final JSON Structure
    return {
        "start_freq_hz": raw_data.get("start_freq_hz"),
        "end_freq_hz": raw_data.get("end_freq_hz"),
        "center_freq_hz": raw_data.get("center_freq_hz"),
        "timestamp": raw_data.get("timestamp"),
        "Pxx": pxx,
        "metrics": rf_stats 
    }

@app.post("/api/v1/front/params", tags=["Frontend"])
async def update_frontend_params(payload: dict = Body(...)):
    """
    **Update Sensor Configuration**
    Accepts: { "mac": "...", "params": {...} OR null }
    """
    mac = payload.get("mac")
    new_params = payload.get("params")
    
    if mac is None:
        raise HTTPException(status_code=400, detail="Invalid JSON format. Need 'mac'.")

    store = get_device_store(mac)
    store["config"] = new_params 
    
    status_msg = "updated" if new_params else "stopped"
    log_json(f"FRONTEND ACTION ({status_msg.upper()}) -> MAC {mac}", new_params)
    
    return {"status": status_msg, "mac": mac}


# ==============================
#      SENSOR ENDPOINTS
# ==============================

@app.get("/api/v1/{mac}/realtime", tags=["Sensor"])
async def get_sensor_job(mac: str):
    """
    **Sensor Polling Endpoint**
    Returns the current config (or null if stopped).
    """
    store = get_device_store(mac)
    return store["config"]

@app.post("/api/v1/{mac}/metrics", tags=["Sensor"])
async def post_sensor_metrics(mac: str, metrics: dict = Body(...)):
    """
    **Sensor Health Reporting**
    """
    store = get_device_store(mac)
    store["metrics"] = metrics 
    log_json(f"SENSOR REPORT (METRICS) -> MAC {mac}", metrics)
    return {"status": "saved"}

@app.post("/api/v1/{mac}/data", tags=["Sensor"])
async def post_sensor_data(mac: str, data: dict = Body(...)):
    """
    **Sensor Data Ingestion**
    """
    if mac not in VALID_MACS:
         raise HTTPException(status_code=403, detail="Access Denied")
    
    store = get_device_store(mac)
    store["data"] = data 
    return {"status": "received"}