# 🛰️ Sensor Backend

The **Sensor Backend** is the core component responsible for interfacing with the Software Defined Radio (SDR) hardware, acquiring spectrum data, and streaming it to the main monitor frontend.

This is part of the [Cheapest Spectrum Sensing Project](https://github.com/dramirezbe/CheapestSpectrumSensingProject.git).

---

### 🛠️ **Required Hardware**

This component is designed to run with the following hardware stack:

* **Compute:** Raspberry Pi 5
* **SDR:** HackRF One
* **Connectivity:** LTE/GPS Module (4G)
* **RF Switching:** Antenna Multiplexer (4 ports)
* **Antennas:** FM Antenna, 2.4GHz Antenna

---

### 🚀 **Quick Start Installation**

These instructions are tested on **Raspbian (ARM64)** Linux distributions.

Ensure you are in the `sensor/` directory for all commands.

```bash
./install.sh
```
