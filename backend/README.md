# 📘 Módulo Backend – Proyecto: Spectrum Monitoring Platform

## 🛰️ Descripción General

El **Módulo Backend** es el núcleo de coordinación de la plataforma. Construido sobre **FASTAPI**, actúa como intermediario inteligente entre la red de sensores físicos y la interfaz de usuario (Dashboard).

**Características Principales (v1.3.0):**
- **Arquitectura API Restful:** Endpoints versionados (`/api/v1`) segregados por rol (Frontend vs. Sensor).
- **Seguridad:** Control de acceso mediante lista blanca de MACs (`src/macs.json`).
- **Almacenamiento en Memoria:** Gestión de estado en tiempo real usando estructuras de datos volátiles (`device_state`) para baja latencia.
- **Post-Procesamiento RF:** Cálculo "on-the-fly" de métricas de calidad de señal (SNR, Noise Floor, Peak Power) antes de servir los datos al frontend.

---

## 🧩 Arquitectura General

```text
 ┌───────────────────────────────┐
 │       UI Web (React)          │
 │       (Dashboard ANE)         │
 └──────────────┬────────────────┘
                │ /api/v1/front/...
                │ (Polling de Data & Envío de Config)
                ▼
      ┌──────────────────────────────┐
      │       Backend FASTAPI        │
      │  - Valida MACs (Whitelist)   │
      │  - Almacena Estado (RAM)     │
      │  - Calcula SNR/Noise Floor   │
      └──────────────┬───────────────┘
                     │ /api/v1/{mac}/...
                     │ (Heartbeat & Data Ingestion)
                     ▼
           ┌──────────────────────┐
           │   Sensor (Python)    │
           │  Gateway & Control   │
           └───────────┬──────────┘
                       │ ZMQ
                       ▼
           ┌──────────────────────┐
           │   Orquestador (C)    │
           └──────────────────────┘
```

# 📘 Módulo Backend – Proyecto: Spectrum Monitoring Platform

## ⚙️ Flujo de Datos y Lógica de Negocio

### 1. Ingesta (Sensor -> Backend)
1.  **Consulta:** El sensor consulta su trabajo actual en `GET /api/v1/{mac}/realtime`.
2.  **Captura:** Si hay configuración activa, el sensor captura y procesa la señal.
3.  **Envío:** El sensor envía la PSD cruda a `POST /api/v1/{mac}/data`.
4.  **Almacenamiento:** El backend almacena el array `Pxx` en memoria (`device_state`).

### 2. Consumo y Cálculo (Backend -> Frontend)
1.  **Solicitud:** El Frontend solicita visualización a `GET /api/v1/front/data`.
2.  **Recuperación:** El Backend recupera la PSD cruda de la memoria.
3.  **Cálculo Matemático (`calculate_rf_metrics`):** Antes de responder, el backend analiza el array numérico para derivar métricas de calidad.
4.  **Respuesta:** El JSON resultante se envía al navegador listo para graficar.

---

# 1. API Reference: Frontend (UI)

Estos endpoints son consumidos exclusivamente por el Dashboard Web.

### 1.1 `GET /api/v1/front/data`
Obtiene la última PSD capturada más las métricas calculadas.

* **Parámetros:** `?mac=AA:BB:CC...`
* **Respuesta:**

```json
{
  "start_freq_hz": 88000000,
  "end_freq_hz": 108000000,
  "center_freq_hz": 98000000,
  "timestamp": 170584123.12,
  "Pxx": [-120.5, -119.0, -115.4],
  "metrics": {
      "noise_floor_dbm": -120.0,
      "peak_power_dbm": -85.2,
      "avg_power_dbm": -110.5,
      "snr_db": 34.8,
      "auto_threshold_dbm": -114.0
  }
}
```

# 📘 Módulo Backend – Proyecto: Spectrum Monitoring Platform

## ⚙️ Flujo de Datos y Lógica de Negocio

### 1. Ingesta (Sensor -> Backend)
1. **Consulta:** El sensor consulta su trabajo actual en `GET /api/v1/{mac}/realtime`.
2. **Captura:** Si hay configuración activa, el sensor captura y procesa la señal.
3. **Envío:** El sensor envía la PSD cruda a `POST /api/v1/{mac}/data`.
4. **Almacenamiento:** El backend almacena el array `Pxx` en memoria (`device_state`).

### 2. Consumo y Cálculo (Backend -> Frontend)
1. **Solicitud:** El Frontend solicita visualización a `GET /api/v1/front/data`.
2. **Recuperación:** El Backend recupera la PSD cruda de la memoria.
3. **Cálculo Matemático (`calculate_rf_metrics`):** Antes de responder, el backend analiza el array numérico para derivar métricas de calidad.
4. **Respuesta:** El JSON resultante se envía al navegador listo para graficar.

---

# 1. API Reference: Frontend (UI)

Estos endpoints son consumidos exclusivamente por el Dashboard Web.

### 1.1 `GET /api/v1/front/data`
Obtiene la última PSD capturada más las métricas calculadas.

* **Parámetros:** `?mac=AA:BB:CC...`
* **Respuesta:**

```json
{
  "start_freq_hz": 88000000,
  "end_freq_hz": 108000000,
  "center_freq_hz": 98000000,
  "timestamp": 170584123.12,
  "Pxx": [-120.5, -119.0, -115.4],
  "metrics": {
      "noise_floor_dbm": -120.0,
      "peak_power_dbm": -85.2,
      "avg_power_dbm": -110.5,
      "snr_db": 34.8,
      "auto_threshold_dbm": -114.0
  }
}
``` 
