# 📘 Módulo Sensor – Proyecto: Spectrum Monitoring Platform

## 🛰️ Descripción General

El **Módulo Sensor** es el componente de borde encargado de monitorear el espectro RF. Este sistema no solo captura señales, sino que implementa un monitoreo continuo de la "salud" del hardware y tiempos de ejecución.

**Funciones Principales:**
- **Captura RF:** Uso de **HackRF One** con gestión de errores y reconexión automática.
- **DSP (C Engine):** Procesamiento de señal (Welch PSD) de alto rendimiento.
- **Gestión (Python):** Orquestación, recorte de ancho de banda (*Span Chopping*) y comunicación con Backend.
- **Logging Exhaustivo:** Generación local de archivos CSV con métricas de sistema (CPU/RAM) y de servicio (Latencia/Red).

El módulo consta de dos procesos independientes comunicados por **ZMQ (IPC)**:
1.  **`rf_metrics` (C):** Motor de adquisición y procesamiento.
2.  **`metrics_server` (Python):** Servidor de gestión y cliente API.

---

## 🧩 Arquitectura del Sistema

```text
                ┌───────────────────────────┐
                │      Backend FASTAPI      │
                │   (Plataforma Central)    │
                └──────────────┬────────────┘
                               │ REST (JSON)
                               │ GET /configuration
                               │ POST /data
                               ▼
                      ┌───────────────────────┐
                      │    Metrics Server     │
                      │       (Python)        │
                      │-----------------------│
                      │ - Polling de Config   │
                      │ - Span Chopping Logic │
                      │ - CSV Metrics (Net)   │
                      │ - ZMQ Gateway         │
                      └─────────────┬─────────┘
                                    │ ZMQ (IPC)
                       ▲────────────┘
                       │ topic: "data"
                       │ topic: "acquire"
┌──────────────────────────────────────────────────────────┐
│                 Orquestador (C Engine)                   │
│----------------------------------------------------------│
│ - Control HackRF & Recovery (Watchdog)                   │
│ - Captura IQ (Ring Buffer)                               │
│ - PSD Welch & Scaling                                    │
│ - CSV Metrics (System/Hardware)                          │
└──────────────────────────────────────────────────────────┘
```

---

# 1. rf_metrics (C Engine - `rf.c`)

Proceso "headless" de ejecución continua. Prioriza la estabilidad, la velocidad de cálculo y la supervisión del hardware.

## 1.1 Funcionalidades Clave
1.  **Autorrecuperación de Hardware (`recover_hackrf`):**
    * Si el HackRF falla o se desconecta, el sistema entra en un bucle de reintento para cerrar y reabrir el dispositivo USB automáticamente sin detener el proceso.
2.  **Cálculo PSD (Welch):**
    * Convierte muestras IQ crudas a dominio de frecuencia.
    * Aplica ventaneo y solapamiento (*overlap*) configurable.
3.  **Monitoreo de Recursos:**
    * Mide el tiempo exacto de adquisición (`Acq_Time`) vs. procesamiento (`DSP_Time`).
    * Calcula la carga de CPU diferencial y uso de RAM en cada ciclo.

## 1.2 Flujo de Datos (ZMQ)
El motor escucha comandos en el tópico `acquire` y publica resultados en `data`.

**Ejemplo de JSON publicado (Salida del Motor C):**
```json
{
  "start_freq_hz": 88000000,
  "end_freq_hz": 108000000,
  "bin_count": 4096,
  "Pxx": [-120.5, -115.3, -110.2, ...]
}
```

## 1.3 Archivos de Log (`CSV_metrics_psdSDRService`)
El código C genera archivos rotativos con el siguiente formato:

| Columna | Descripción |
| :--- | :--- |
| `Timestamp_Epoch` | Momento de la grabación. |
| `Acq_Time_ms` | Tiempo llenando el buffer RX (aire). |
| `DSP_Time_ms` | Tiempo calculando la FFT/Welch. |
| `CPU_Load_Pct` | Uso de CPU del sistema (%). |
| `RAM_Used_MB` | Memoria RAM ocupada. |
| `RF Params` | Frecuencia central, Ganancias (LNA/VGA), etc. |

---

# 2. Metrics Server (Python - `server.py`)

Controlador inteligente que adapta la información del sensor para la nube.

## 2.1 Lógica de Streaming y "Span Chopping"
El script `server.py` no solo retransmite datos, sino que los procesa:

1.  **Polling:** Consulta `GET /configuration` periódicamente.
    * Si `span <= 0`: Detiene el flujo (Idle).
    * Si `span > 0`: Activa el flujo.
2.  **Span Chopping (Recorte de Banda):**
    * El HackRF captura un ancho de banda fijo basado en el `sample_rate`.
    * Si la configuración pide un `span` menor al capturado, Python **recorta el array `Pxx`** eliminando los bordes innecesarios.
    * **Beneficio:** Reduce drásticamente el tamaño del JSON enviado al servidor (ahorro de datos 4G/IoT).
3.  **Gestión de Logs:** Utiliza la clase `MetricsManager` para rotar archivos y evitar llenar el disco.

## 2.2 API REST Interfaz

### A. Petición de Configuración (Backend -> Python -> C)
El Python recibe esto del API y lo envía al C por ZMQ (`topic: acquire`).

```json
{
  "center_freq": 98000000,
  "span": 20000000,
  "rbw": 5000,
  "sample_rate": 20000000,
  "overlap": 0.5,
  "window_type": 2,
  "scale": "dBm",
  "lna_gain": 16,
  "vga_gain": 32,
  "amp_enabled": false
}
```

### B. Envío de Datos (Python -> Backend)
Endpoint: `POST /data`

El JSON final incluye métricas enriquecidas y el array recortado.

```json
{
  "start_freq_hz": 93000000,
  "end_freq_hz": 103000000,
  "center_freq_hz": 98000000,
  "timestamp": 1705845012120,
  "mac": "b8:27:eb:aa:bb:cc",
  "Pxx": [-100.2, -99.5, -80.1, ...] // Array optimizado
}
```

## 2.3 Archivos de Log (`CSV_metrics_service`)
Registra el rendimiento de la red y la comunicación interna.

| Columna | Descripción |
| :--- | :--- |
| `fetch_duration_ms` | Latencia obteniendo configuración del API. |
| `zmq_send_duration_ms` | Tiempo de envío al motor C. |
| `c_engine_response_ms` | Tiempo total que el motor C tardó en responder. |
| `upload_duration_ms` | Tiempo subiendo el POST de datos. |
| `server_pkg_KB` | Tamaño de la configuración descargada. |
| `outgoing_pkg_KB` | Tamaño del JSON final subido (útil para auditoría de datos). |

---

## 3. Manejo de Errores y Recuperación

1.  **Fallo de API:** Si el Backend no responde, el sensor mantiene la última configuración válida y sigue operando (si `streaming_enabled` es True).
2.  **Fallo de ZMQ:** Si el motor C no responde en 5 segundos (`timeout`), el Python registra el error y reintenta en el siguiente ciclo.
3.  **Fallo de USB:** El motor C detecta la desconexión, libera recursos y reintenta abrir el dispositivo indefinidamente.
