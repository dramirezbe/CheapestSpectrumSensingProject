import cfg
import json
import asyncio
import numpy as np
import matplotlib.pyplot as plt
from utils import ZmqPub, ZmqSub 

# --- CONFIGURATION (Topics and Parameters) ---
# Topics must match the C orchestrator's expectations
TOPIC_CMD = "acquire" 
TOPIC_DATA = "data"

# Acquisition request parameters (Adjust these to test different setups)
ACQUISITION_REQUEST_CFG = {
    "center_freq_hz": 915000000, 
    "sample_rate_hz": 20000000.0,
    "rbw_hz": 5000,              
    "span": 10000000,          # 10 MHz span
    "overlap": 0.5,           
    "window": 1,              # 1 often means Hamming/Hann
    "scale": "dBm",           # The scale for the PSD output
    "lna_gain": 20,           
    "vga_gain": 30,           
    "antenna_amp": 1,         # True/1 to enable amp
}

# --- ASYNCHRONOUS ZMQ COMMUNICATION ---

async def run_acquisition_and_plot():
    """
    Sets up ZMQ, sends the acquisition request, waits for the PSD, and plots it.
    """
    print("Initializing ZMQ Publisher and Subscriber...")
    # ZmqPub: Used to send the command to the C orchestrator
    pub_cmd = ZmqPub(addr=cfg.IPC_CMD_ADDR) 
    # ZmqSub: Used to receive the results from the C orchestrator (subscribed to 'data')
    sub_data = ZmqSub(addr=cfg.IPC_DATA_ADDR, topic=TOPIC_DATA)

    # Give sockets a moment to connect/bind before sending
    await asyncio.sleep(0.5) 
    
    try:
        # 1. SEND THE ACQUISITION REQUEST
        print(f"\n📡 Sending acquisition command on topic '{TOPIC_CMD}'...")
        # Your ZmqPub.public_client() sends the topic + JSON payload
        pub_cmd.public_client(TOPIC_CMD, ACQUISITION_REQUEST_CFG)
        print("   Request sent. Waiting for PSD data from C engine (5s Timeout)...")

        # 2. WAIT FOR AND RECEIVE THE RESULT
        # sub.wait_msg() returns the JSON payload dict directly (assuming your utility does this)
        raw_data = await asyncio.wait_for(sub_data.wait_msg(), timeout=5)
        
        # 3. EXTRACT AND PROCESS DATA
        # The C orchestrator publishes a dictionary with start_freq_hz, end_freq_hz, and Pxx
        pxx = np.array(raw_data.get("Pxx", []))
        start_freq = raw_data.get("start_freq_hz", 0.0)
        end_freq = raw_data.get("end_freq_hz", 0.0)
        bin_count = raw_data.get("bin_count", 0)
        
        if bin_count == 0 or len(pxx) == 0:
            print("❌ Received data, but Pxx array is empty or bin_count is zero.")
            return

        print(f"✅ Results received: {bin_count} bins of PSD data.")
        
        # Calculate Frequency Array
        freqs = np.linspace(start_freq, end_freq, bin_count)
        center_freq = ACQUISITION_REQUEST_CFG["center_freq_hz"]
        scale = ACQUISITION_REQUEST_CFG["scale"]

        # 4. PLOT THE PSD
        plt.figure(figsize=(12, 6))
        
        # Convert frequency axis to MHz for readability
        plt.plot(freqs / 1e6, pxx) 
        
        plt.title(f"Power Spectral Density (PSD) at {center_freq / 1e6:.2f} MHz")
        plt.xlabel("Frequency (MHz)")
        plt.ylabel(f"Power ({scale})")
        plt.grid(True, alpha=0.5)
        plt.minorticks_on()
        plt.grid(which='minor', linestyle=':', alpha=0.3)
        plt.tight_layout()
        plt.show()


    except asyncio.TimeoutError:
        print("\n⏳ TIMEOUT: No data received from C engine. Check if the C program is running and bound to the correct addresses.")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
        
    finally:
        # 5. CLEANUP
        print("\n👋 Closing ZMQ sockets...")
        pub_cmd.close()
        sub_data.close()


if __name__ == "__main__":
    try:
        asyncio.run(run_acquisition_and_plot())
    except KeyboardInterrupt:
        print("\nProgram interrupted by user.")
