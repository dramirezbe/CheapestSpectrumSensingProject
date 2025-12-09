import json
from fastapi import FastAPI, Body, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional

# --- Swagger/OpenAPI Configuration ---
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
    version="1.2.1",
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

# --- Load Valid MACs ---
def load_valid_macs():
    try:
        with open("src/macs.json", "r") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return {"d0:65:78:9c:dd:d0", "d0:65:78:9c:dd:d1", "d0:65:78:9c:dd:d2"}

VALID_MACS = load_valid_macs()

# --- In-Memory Storage ---
device_state: Dict[str, Dict[str, Any]] = {}

# --- Helper for Printing ---
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


# ==============================
#      FRONTEND SIDE ENDPOINTS
# ==============================
# IMPORTANT: These must be defined BEFORE the /{mac}/ endpoints.
# Otherwise, FastAPI will interpret "front" as a {mac} parameter.

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
    Used by Plot.jsx to fetch the latest PSD frame.
    """
    store = get_device_store(mac)
    
    if not store.get("data"):
        return {
            "Pxx": [],
            "center_freq": 0,
            "span": 0
        }
    return store["data"]

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
#      SENSOR SIDE ENDPOINTS
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