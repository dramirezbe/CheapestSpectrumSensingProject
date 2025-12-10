# 📘 Módulo Sensor – Proyecto: Spectrum Monitoring Platform

## 🛰️ Descripción General

El **Módulo Sensor** es el componente encargado de:

- Capturar el espectro RF mediante **HackRF One**.  
- Procesar la señal para obtener la **PSD (Welch)**.  
- Enviar resultados al servidor central mediante **ZMQ + REST**.  
- Recibir configuraciones remotas desde el Backend (FASTAPI).  
- Registrar métricas internas del sistema (CPU, RAM, disco, tiempos).  

El módulo está compuesto por dos capas:

1. **Orquestador (C Engine)**  
2. **Run Server (Python)**  

---

## 🧩 Arquitectura General

```text
                ┌───────────────────────────┐
                │        Backend FASTAPI     │
                │   (Plataforma central ANE) │
                │       http://.../api/*     │
                └──────────────┬─────────────┘
                               │ REST (JSON)
                               ▼
                      ┌───────────────────────┐
                      │       Run Server       │
                      │        (Python)        │
                      │ - ZMQ pub/sub          │
                      │ - Cliente REST local   │
                      └─────────────┬─────────┘
                                    │ ZMQ (JSON)
                       ▲────────────┘
                       │ publish(data)
                       │ subscribe(acquire)
┌──────────────────────────────────────────────────────────┐
│                 Orquestador (C Engine)                   │
│ - Control HackRF                                          │
│ - Captura IQ                                              │
│ - PSD Welch                                               │
│ - Métricas CPU/RAM/disco                                  │
└──────────────────────────────────────────────────────────┘

```


## ⚙️ Flujo Completo del Sensor

El Backend FASTAPI solicita una adquisición.

El Run Server consulta el endpoint remoto /configuration/{mac}.

El Backend responde con los parámetros de adquisición PSD.

El Run Server envía esa configuración al Orquestador vía ZMQ topic "acquire".

El Orquestador:

- Configura el HackRF  
- Captura IQ  
- Calcula la PSD  
- Publica la PSD por ZMQ topic "data"  

El Run Server reenvía la PSD al Backend mediante POST /data.

El Backend almacena y/o visualiza la señal.

---

# 1. Orquestador (C Engine)

## 1.1 Responsabilidades

- Captura IQ usando HackRF One.  
- Configura el hardware SDR según parámetros remotos.  
- Procesa la señal mediante Welch.  
- Publica la PSD como un JSON vía ZMQ.  
- Registra métricas del sistema en CSV.  

---

## 1.2 Recepción de Órdenes (ZMQ topic "acquire")

El Orquestador escucha comandos desde el Run Server:

zsub_init("acquire", handle_psd_message);

Formato del comando recibido:
```text

{
  "center_freq": 98000000,
  "span": 20000000,
  "rbw": 5000,
  "sample_rate": 20000000,
  "overlap": 0.5,
  "window_type": "hamming",
  "scale": "dBm",
  "lna_gain": 16,
  "vga_gain": 32,
  "amp_enabled": false
}
```
---

## 1.3 Proceso de Adquisición y DSP

### A. Configuración del HackRF

hackrf_apply_cfg(device, &hack_cfg);

### B. Captura IQ

Uso de ring buffer.  
rx_callback() llena el buffer hasta alcanzar rb_cfg.total_bytes.

### C. Cálculo de PSD

execute_welch_psd(sig, &psd_cfg, freq, psd);

### D. Escalado

scale_psd(psd, nperseg, desired.scale);

### E. Publicación de Resultados

publish_results(freq, psd, nperseg);

Ejemplo del JSON publicado:

```text

{
  "start_freq_hz": 88000000,
  "end_freq_hz": 108000000,
  "center_freq": 98000000,
  "Pxx": [-120.5, -115.3, ...]
}
```
---

# 2. Run Server (Python)

El Run Server actúa como puente entre:

- El Backend FASTAPI (REST)  
- El Orquestador C (ZMQ)  

## 2.1 Responsabilidades del Run Server

- Consultar al Backend por configuración → GET /{mac} / realtime
- Enviar esa configuración al Orquestador → ZMQ "acquire"  
- Recibir PSD procesada desde el Orquestador → ZMQ "data"  
- Enviar PSD al Backend → POST /{mac}data  
- Manejar errores y estado del sensor  

---

# 3. API entre Run Server ↔ Backend FASTAPI

## 3.1 GET /{mac}/realtime

Ejemplo de respuesta:
```text

{
  "center_freq": 91500000,
  "span": 10000000,
  "rbw": 5000,
  "sample_rate": 2000000,
  "overlap": 0.5,
  "window_type": 1,
  "scale": "dBm",
  "lna_gain": 16,
  "vga_gain": 32,
  "amp_enabled": false
}
```
El Run Server reenvía este JSON al Orquestador por ZMQ (acquire).

---

## 3.2 POST /data
```text

{
  "start_freq_hz": 88000000,
  "end_freq_hz": 108000000,
  "center_freq_hz": 98000000,
  "timestamp": "2025-01-21T12:30:12.120",
  "Pxx": [-120.5, -119.0, ...]
}
```
Respuesta esperada del Backend:
```text

{ "status": "ok" }
