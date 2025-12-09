import time
import requests
import numpy as np
import json
import random

# ================= CONFIGURATION =================
# The MAC address must match one of the VALID_MACS in your server
SENSOR_MAC = "2c:cf:67:51:17:be"
API_BASE_URL = "http://127.0.0.1:8000/api/v1"

# URL Construction
POLL_URL = f"{API_BASE_URL}/{SENSOR_MAC}/realtime"
DATA_URL = f"{API_BASE_URL}/{SENSOR_MAC}/data"
METRICS_URL = f"{API_BASE_URL}/{SENSOR_MAC}/metrics"

def generate_dummy_spectrum(config):
    """
    Generates a dummy spectral frame based on the config.
    Creates a noise floor and adds a fake signal peak.
    """
    center_freq = config.get("center_freq_hz", 9800000)
    span = config.get("span", 20000000)
    rbw = config.get("resolution_hz", 10000) # Resolution Bandwidth

    # Calculate number of FFT bins
    # Ensure we don't divide by zero
    if rbw <= 0: rbw = 10000
    num_bins = int(span / rbw)
    
    # 1. Generate Noise Floor (Gaussian noise around -100 dBm)
    # Mean = -100, Std Dev = 2.0
    noise_floor = np.random.normal(-100, 2.0, num_bins)
    
    # 2. Add a Dummy "Signal" (Peak)
    # We create a Gaussian peak at a random frequency near the center
    # to simulate a live signal moving slightly.
    
    # Frequency axis relative to array indices
    x = np.arange(num_bins)
    
    # Peak position (drifting slightly)
    drift = random.randint(-50, 50)
    peak_center = (num_bins // 2) + drift
    peak_width = num_bins // 50  # Width of the signal
    
    # Gaussian formula: A * exp(-(x - b)^2 / (2c^2))
    signal_amplitude = 40  # Signal is 40dB above noise floor
    signal = signal_amplitude * np.exp(-0.5 * ((x - peak_center) / peak_width)**2)
    
    # Combine noise + signal
    pxx = noise_floor + signal

    # Calculate frequency boundaries
    start_freq = center_freq - (span / 2)
    end_freq = center_freq + (span / 2)

    return {
        "mac": SENSOR_MAC,
        "Pxx": pxx.tolist(), # Convert numpy array to standard list
        "start_freq_hz": int(start_freq),
        "end_freq_hz": int(end_freq),
        "center_freq_hz": center_freq,
        "span": span,
        "timestamp": int(time.time() * 1000) # Unix MS
    }

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
                else:
                    print(f"[!] Server returned {response.status_code}. Retrying...")
                    time.sleep(2)
                    continue
            except requests.exceptions.ConnectionError:
                print("[!] Connection refused. Is the server running?")
                time.sleep(2)
                continue

            # 2. Check if configuration exists (Sensor might be "Stopped")
            if not config:
                print("[-] Sensor is STOPPED (Config is null). Idling...")
                time.sleep(1)
                continue

            # 3. Generate Data
            payload = generate_dummy_spectrum(config)
            
            # 4. Send Data to Server
            # The server expects POST /api/v1/{mac}/data
            res = requests.post(DATA_URL, json=payload)
            
            if res.status_code == 200:
                print(f"[+] Sent {len(payload['Pxx'])} bins | Center: {config['center_freq_hz']} Hz | Status: OK")
            else:
                print(f"[!] Upload failed: {res.text}")

            # 5. Send Heartbeat/Metrics (Optional, every few loops)
            if random.random() > 0.9: # 10% chance per loop
                metrics = {"temp": random.randint(40, 60), "cpu": random.randint(10, 30)}
                requests.post(METRICS_URL, json=metrics)

            # Sleep to simulate sample rate (e.g., 10 frames per second)
            time.sleep(0.1)

        except KeyboardInterrupt:
            print("\nStopping sensor script.")
            break
        except Exception as e:
            print(f"[!!] Unexpected Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()