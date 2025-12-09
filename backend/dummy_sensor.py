import time
import requests
import numpy as np
import json
import random

# ================= CONFIGURATION =================
SENSOR_MAC = "2c:cf:67:51:17:be"
API_BASE_URL = "http://127.0.0.1:8000/api/v1"

# URL Construction
POLL_URL = f"{API_BASE_URL}/{SENSOR_MAC}/realtime"
DATA_URL = f"{API_BASE_URL}/{SENSOR_MAC}/data"
METRICS_URL = f"{API_BASE_URL}/{SENSOR_MAC}/metrics"

def generate_dummy_spectrum(config):
    """
    Generates a dummy spectral frame based on the config.
    """
    center_freq = config.get("center_freq_hz", 9800000)
    span = config.get("span", 20000000)
    rbw = config.get("resolution_hz", 10000) 

    if rbw <= 0: rbw = 10000
    num_bins = int(span / rbw)
    
    # 1. Generate Noise Floor
    noise_floor = np.random.normal(-100, 2.0, num_bins)
    
    # 2. Add a Dummy "Signal"
    x = np.arange(num_bins)
    drift = random.randint(-50, 50)
    peak_center = (num_bins // 2) + drift
    peak_width = num_bins // 50 
    
    signal_amplitude = 40 
    signal = signal_amplitude * np.exp(-0.5 * ((x - peak_center) / peak_width)**2)
    
    pxx = noise_floor + signal

    start_freq = center_freq - (span / 2)
    end_freq = center_freq + (span / 2)

    return {
        "mac": SENSOR_MAC,
        "Pxx": pxx.tolist(),
        "start_freq_hz": int(start_freq),
        "end_freq_hz": int(end_freq),
        "center_freq_hz": center_freq,
        "span": span,
        "timestamp": int(time.time() * 1000)
    }

def print_verbose_json(label, data, truncate_arrays=True):
    """
    Helper to pretty print JSON. 
    Truncates large arrays to keep console readable.
    """
    print(f"\n{'-'*10} {label} {'-'*10}")
    
    # Create a copy so we don't modify the actual data being sent
    display_data = data.copy() if isinstance(data, dict) else data
    
    # Visual truncation for Pxx if it exists and is huge
    if truncate_arrays and isinstance(display_data, dict) and "Pxx" in display_data:
        full_len = len(display_data["Pxx"])
        if full_len > 10:
            first_3 = [round(x, 2) for x in display_data["Pxx"][:3]]
            last_3 = [round(x, 2) for x in display_data["Pxx"][-3:]]
            display_data["Pxx"] = f"<Array of {full_len} floats: {first_3} ... {last_3}>"

    print(json.dumps(display_data, indent=4))
    print(f"{'-'*40}\n")

def main():
    print(f"--- Starting Dummy Sensor {SENSOR_MAC} ---")
    print(f"Target API: {API_BASE_URL}")

    while True:
        try:
            # 1. Poll for Config
            try:
                response = requests.get(POLL_URL)
                if response.status_code == 200:
                    config = response.json()
                    # VERBOSE PRINT: INCOMING
                    print_verbose_json("INCOMING CONFIG (FROM API)", config)
                else:
                    print(f"[!] Server returned {response.status_code}. Retrying...")
                    time.sleep(2)
                    continue
            except requests.exceptions.ConnectionError:
                print("[!] Connection refused. Is the server running?")
                time.sleep(2)
                continue

            # 2. Check if configuration exists
            if not config:
                print("[-] Sensor is STOPPED (Config is null). Idling...")
                time.sleep(1)
                continue

            # 3. Generate Data
            payload = generate_dummy_spectrum(config)
            
            # VERBOSE PRINT: OUTGOING
            # We set truncate_arrays=True so your terminal isn't flooded with 4000 numbers
            print_verbose_json("OUTGOING DATA (TO API)", payload, truncate_arrays=True)
            
            # 4. Send Data to Server
            res = requests.post(DATA_URL, json=payload)
            
            if res.status_code == 200:
                print(f"[+] Upload Success | Status: {res.status_code}")
            else:
                print(f"[!] Upload failed: {res.text}")

            # 5. Send Heartbeat/Metrics
            if random.random() > 0.9: 
                metrics = {"temp": random.randint(40, 60), "cpu": random.randint(10, 30)}
                print_verbose_json("OUTGOING METRICS", metrics)
                requests.post(METRICS_URL, json=metrics)

            # Sleep
            time.sleep(1) # Slowed down slightly to make logs readable

        except KeyboardInterrupt:
            print("\nStopping sensor script.")
            break
        except Exception as e:
            print(f"[!!] Unexpected Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()