# 📡 Cheapest Spectrum Sensing Project

This project provides a complete solution for **real-time spectrum sensing  (Visualization and Audio Demodulation)** via a web interface, utilizing affordable Software Defined Radio (SDR) hardware.

---

### ⚙️ **Key Features**

* **Real-time Spectrum Streaming:** Capture and stream radio spectrum data.
* **Audio Demodulation:** Extract audio signals from spectrum data in streaming.
* **Web Visualization:** Display spectrum data on a responsive web application.
* **Modular Design:** Separate components for the SDR sensor, backend processing, and frontend display.

---

### 📦 **Project Structure**

The project is divided into three main components:

| Directory | Component | Description |
| :--- | :--- | :--- |
| `sensor/` | **Sensor Backend** | Handles SDR hardware, data acquisition, and streaming. |
| `frontend/` | **Monitor Frontend** | The web application for real-time data visualization. |
| `backend/` | **Backend** | Handles data processing and Sensor Communication. |


### Installation

To install all the project, follow these steps:

```bash
# in project dir
./install-all.sh
```

If you just want to install dependencies run:

```bash
./install.sh
```

Note: Each folder has its own `install.sh` script.

