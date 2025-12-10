from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import os
import io

import matplotlib
matplotlib.use("Agg")  # backend no interactivo (para servidores)
import matplotlib.pyplot as plt
import numpy as np

app = FastAPI(title="ANE PSD API")

# --- Configuración del sensor (MAC fija) ---
SENSOR_MAC = "2c:cf:67:51:17:be"

# --- Estado en memoria ---
pending_config: Optional[Dict[str, Any]] = None   # Config para próxima medición (o modo streaming)
last_result: Optional[Dict[str, Any]] = None      # Última PSD recibida


# ============================
# Modelos Pydantic
# ============================

class ConfigurationIn(BaseModel):
    center_frequency: int       # Hz
    span: int                   # Hz
    resolution_hz: Optional[float] = None
    antenna_port: Optional[int] = None
    window: Optional[str] = None
    overlap: Optional[float] = None
    sample_rate_hz: Optional[int] = None
    lna_gain: Optional[int] = None
    vga_gain: Optional[int] = None
    antenna_amp: Optional[int] = None


class MeasurementResult(BaseModel):
    Pxx: List[float]
    start_freq_hz: float
    end_freq_hz: float
    timestamp: int
    mac: str


# ============================
# 1) Cliente (tú) -> POST /configuration
#    Define configuración actual del sensor
# ============================

@app.post("/configuration")
async def set_configuration(cfg: ConfigurationIn):
    """
    Guardar configuración para la adquisición del sensor.
    Se aplica a la MAC fija SENSOR_MAC.

    - Si span > 0  -> run_server puede entrar en modo "streaming".
    - Si span <= 0 -> run_server puede detener la adquisición (STOP).
    """
    global pending_config
    pending_config = cfg.dict()
    pending_config["last_update"] = datetime.utcnow().isoformat()
    return {
        "status": "ok",
        "message": "configuration stored/updated",
        "mac": SENSOR_MAC,
        "config": pending_config,
    }


# ============================
# 2) Sensor (run_server) -> GET /{mac}/configuration
#    run_server YA espera este formato de endpoint
# ============================

@app.get("/{mac}/configuration")
async def get_configuration(mac: str):
    """
    Endpoint que llama run_server():
      GET /{mac}/configuration

    Devuelve la configuración actual (si existe).
    Si la usas en modo 'oneshot', puedes volver a poner pending_config = None;
    si la usas en streaming, déjala persistir.
    """
    global pending_config

    if mac.lower() != SENSOR_MAC.lower():
        raise HTTPException(status_code=404, detail="Unknown MAC")

    if pending_config is None:
        raise HTTPException(status_code=404, detail="No configuration set")

    cfg = pending_config

    # NOTA:
    # - Para adquisiciones instantáneas: descomenta esta línea para consumir 1 vez.
    # - Para streaming continuo: déjala comentada.
    # pending_config = None

    # Devolver con las claves que usa fetch_job()
    return {
        "center_frequency": cfg.get("center_frequency"),
        "span": cfg.get("span"),
        "resolution_hz": cfg.get("resolution_hz"),
        "antenna_port": cfg.get("antenna_port"),
        "window": cfg.get("window"),
        "overlap": cfg.get("overlap"),
        "sample_rate_hz": cfg.get("sample_rate_hz"),
        "lna_gain": cfg.get("lna_gain"),
        "vga_gain": cfg.get("vga_gain"),
        "antenna_amp": cfg.get("antenna_amp"),
    }


# ============================
# 3) Sensor (run_server) -> POST /data
#    Recibe la PSD y actualiza el último resultado
# ============================

@app.post("/data")
async def receive_data(meas: MeasurementResult):
    """
    Este endpoint lo llama run_server() con client.post_json("/data", data_dict).
    Aquí guardamos el último resultado (PSD) en memoria.
    Ya NO se guardan PNG en disco: la gráfica se genera bajo demanda.
    """
    global last_result

    if meas.mac.lower() != SENSOR_MAC.lower():
        raise HTTPException(status_code=400, detail="MAC mismatch")

    last_result = meas.dict()
    last_result["received_at"] = datetime.utcnow().isoformat()

    return {
        "status": "ok",
        "message": "PSD received",
        "mac": meas.mac,
    }


# ============================
# 4) Cliente (tú) -> GET /last_result
#    Para recuperar la PSD y metadatos en JSON
# ============================

@app.get("/last_result")
async def get_last_result():
    global last_result
    if last_result is None:
        raise HTTPException(status_code=404, detail="No result available")
    return last_result


# ============================
# 5) Cliente -> GET /psd_plot.png
#    Devuelve SIEMPRE un PNG con la ÚLTIMA PSD
# ============================

@app.get("/psd_plot.png")
async def psd_plot_png():
    """
    Genera un PNG en memoria con la última PSD disponible
    y lo devuelve como image/png.
    """
    global last_result
    if last_result is None:
        raise HTTPException(status_code=404, detail="No result available")

    Pxx = np.array(last_result["Pxx"])
    start_f = float(last_result["start_freq_hz"])
    end_f = float(last_result["end_freq_hz"])

    if len(Pxx) == 0 or end_f <= start_f:
        raise HTTPException(status_code=400, detail="Invalid PSD data")

    freqs = np.linspace(start_f, end_f, len(Pxx))  # Hz

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(freqs / 1e6, Pxx)
    ax.set_xlabel("Frecuencia [MHz]")
    ax.set_ylabel("PSD [dB/Hz ?]")
    ax.set_title(f"PSD Sensor {SENSOR_MAC}")
    ax.grid(True)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")


# ============================
# 6) Front -> GET /psd_live
#    Página HTML con:
#      - gráfica que se actualiza
#      - botones Start/Stop
#      - métricas bonitas
# ============================

from fastapi.responses import HTMLResponse

@app.get("/psd_live")
async def psd_live_page():
    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
      <meta charset="UTF-8" />
      <title>PSD en vivo - ANE Sensor</title>

      <!-- Chart.js -->
      <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

      <style>
        body {{
          font-family: Arial, sans-serif;
          background: #111;
          color: #eee;
          margin: 0;
          padding: 20px;
        }}

        h2 {{
          margin-bottom: 0.3rem;
        }}

        #estado {{
          font-size: 0.9rem;
          color: #aaa;
          margin-bottom: 0.5rem;
        }}

        .panel-controles {{
          max-width: 900px;
          margin: 0 auto 10px auto;
          background: #1b1b1b;
          border-radius: 10px;
          padding: 10px 20px;
          box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
          align-items: center;
        }}

        .panel-controles label {{
          font-size: 0.9rem;
          margin-right: 5px;
        }}

        .panel-controles input {{
          width: 90px;
          padding: 3px 5px;
          border-radius: 4px;
          border: 1px solid #444;
          background: #222;
          color: #eee;
          font-size: 0.9rem;
        }}

        .panel-controles button {{
          padding: 5px 10px;
          border-radius: 5px;
          border: none;
          cursor: pointer;
          background: #2d7dd2;
          color: #fff;
          font-weight: bold;
        }}

        .panel-controles button:hover {{
          opacity: 0.9;
        }}

        #mensaje-error {{
          color: #ff8080;
          font-size: 0.85rem;
          margin-top: 4px;
        }}

        .contenedor {{
          max-width: 900px;
          margin: 0 auto;
          background: #1b1b1b;
          border-radius: 10px;
          padding: 20px;
          box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
          height: 500px; /* altura fija para el gráfico */
        }}

        canvas {{
          background: #000;
          border-radius: 8px;
        }}

        .metricos {{
          max-width: 900px;
          margin: 10px auto 0 auto;
          font-size: 0.9rem;
          color: #ccc;
        }}

        .metricos span.label {{
          font-weight: bold;
          color: #eee;
        }}

        .metricos span.valor {{
          color: #93c5fd;
        }}
      </style>
    </head>
    <body>

      <h2>PSD en vivo - Sensor {SENSOR_MAC}</h2>
      <div id="estado">Esperando datos...</div>

      <!-- Panel de controles -->
      <div class="panel-controles">
        <div>
          <label for="center_mhz">f_centro [MHz]:</label>
          <input type="number" id="center_mhz" value="98" step="0.1" />
        </div>
        <div>
          <label for="span_mhz">Span [MHz]:</label>
          <input type="number" id="span_mhz" value="20" step="0.1" />
        </div>
        <div>
          <label for="fs_mhz">Fs [MHz]:</label>
          <input type="number" id="fs_mhz" value="20" step="0.1" />
        </div>
        <div>
          <label for="rbw_hz">RBW [Hz]:</label>
          <input type="number" id="rbw_hz" value="10000" step="100" />
        </div>
        <div>
          <label for="lna_gain">LNA gain:</label>
          <input type="number" id="lna_gain" value="0" />
        </div>
        <div>
          <label for="vga_gain">VGA gain:</label>
          <input type="number" id="vga_gain" value="0" />
        </div>
        <div>
          <label for="ant_amp">Ant amp (0/1):</label>
          <input type="number" id="ant_amp" value="1" />
        </div>
        <div>
          <button onclick="start()">START</button>
        </div>
        <div>
          <button onclick="stop()">STOP</button>
        </div>
        <div id="mensaje-error"></div>
      </div>

      <!-- Contenedor de la gráfica -->
      <div class="contenedor">
        <canvas id="psdChart"></canvas>
      </div>

      <!-- Métricas -->
      <div class="metricos">
        <p><span class="label">Centro (Hz):</span> <span id="m_center" class="valor">-</span></p>
        <p><span class="label">Span (Hz):</span> <span id="m_span" class="valor">-</span></p>
        <p><span class="label">Fs (Hz):</span> <span id="m_fs" class="valor">-</span></p>
        <p><span class="label">Start (Hz):</span> <span id="m_start" class="valor">-</span></p>
        <p><span class="label">End (Hz):</span> <span id="m_end" class="valor">-</span></p>
        <p><span class="label">Len Pxx:</span> <span id="m_len" class="valor">-</span></p>
        <p><span class="label">Timestamp:</span> <span id="m_ts" class="valor">-</span></p>
      </div>

      <script>
        const estadoElem = document.getElementById("estado");
        const mensajeErrorElem = document.getElementById("mensaje-error");

        const inputCenter = document.getElementById("center_mhz");
        const inputSpan   = document.getElementById("span_mhz");
        const inputFs     = document.getElementById("fs_mhz");
        const inputRBW    = document.getElementById("rbw_hz");
        const inputLna    = document.getElementById("lna_gain");
        const inputVga    = document.getElementById("vga_gain");
        const inputAntAmp = document.getElementById("ant_amp");

        // Límites fijos en Y (dB/Hz)
        const Y_MIN = -90;
        const Y_MAX = -30;

        const ctx = document.getElementById("psdChart").getContext("2d");

        // Gráfico Chart.js con límites estáticos en Y y X lineal
        const psdChart = new Chart(ctx, {{
          type: "line",
          data: {{
            datasets: [{{
              label: "PSD [dB/Hz ?]",
              data: [],   // puntos con frecuencia en MHz y PSD en dB
              borderWidth: 1,
              pointRadius: 0,
              tension: 0,
              borderColor: "rgba(59,130,246,1)",
              backgroundColor: "rgba(59,130,246,0.2)",
            }}]
          }},
          options: {{
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            parsing: false,   // usamos directamente x,y en cada punto
            scales: {{
              x: {{
                type: "linear",
                title: {{ display: true, text: "Frecuencia [MHz]" }},
                min: 0,
                max: 20,
                ticks: {{
                  stepSize: 1,
                  callback: function(value) {{
                    return value.toFixed(0);
                  }}
                }},
                grid: {{
                  color: "rgba(75,85,99,0.5)"
                }}
              }},
              y: {{
                title: {{ display: true, text: "PSD [dB/Hz]" }},
                min: Y_MIN,
                max: Y_MAX,
                grid: {{
                  color: "rgba(75,85,99,0.5)"
                }}
              }}
            }},
            plugins: {{
              legend: {{ display: true }}
            }}
          }}
        }});

        // Actualización de PSD desde /last_result
        async function updatePsd() {{
          try {{
            const resp = await fetch("/last_result");
            if (!resp.ok) {{
              throw new Error("No result");
            }}
            const data = await resp.json();

            const Pxx = data.Pxx || [];
            const startHz = data.start_freq_hz || 0;
            const endHz   = data.end_freq_hz || 0;
            const spanHz  = endHz - startHz;
            const N = Pxx.length;

            if (!Pxx || N === 0 || spanHz <= 0) {{
              estadoElem.textContent = "Sin datos válidos (Pxx vacío o span <= 0)";
              return;
            }}

            // Construir puntos (freq_MHz, PSD_dB)
            const puntos = Pxx.map((y, i) => {{
              const frac = (N > 1) ? i / (N - 1) : 0;
              const fHz = startHz + frac * spanHz;
              return {{ x: fHz / 1e6, y: y }};
            }});

            psdChart.data.datasets[0].data = puntos;

            // Límites estáticos en Y, pero X se ajusta al rango de frecuencias medido
            const fStartMHz = startHz / 1e6;
            const fEndMHz   = endHz   / 1e6;
            psdChart.options.scales.x.min = fStartMHz;
            psdChart.options.scales.x.max = fEndMHz;
            psdChart.options.scales.x.ticks.stepSize = Math.max((fEndMHz - fStartMHz) / 10, 0.1);

            psdChart.update("none");

            // Actualizar métricas
            estadoElem.textContent = "Recibiendo datos de PSD...";
            document.getElementById("m_center").textContent = data.center_frequency ?? "-";
            document.getElementById("m_span").textContent   = data.span ?? "-";
            document.getElementById("m_fs").textContent     = data.sample_rate_hz ?? "-";
            document.getElementById("m_start").textContent  = startHz;
            document.getElementById("m_end").textContent    = endHz;
            document.getElementById("m_len").textContent    = N;
            document.getElementById("m_ts").textContent     = data.timestamp ?? "-";

          }} catch (err) {{
            estadoElem.textContent = "Sin datos /last_result";
          }}
        }}

        // Llamar periódicamente para actualizar
        setInterval(updatePsd, 1000);

        // START: envía configuración con parámetros en MHz convertidos a Hz
        function start() {{
          const centerMHz = parseFloat(inputCenter.value);
          const spanMHz   = parseFloat(inputSpan.value);
          const fsMHz     = parseFloat(inputFs.value);
          const rbwHz     = parseFloat(inputRBW.value);
          const lna       = parseInt(inputLna.value);
          const vga       = parseInt(inputVga.value);
          const antAmp    = parseInt(inputAntAmp.value);

          if (isNaN(centerMHz) || isNaN(spanMHz) || isNaN(fsMHz) || isNaN(rbwHz)) {{
            mensajeErrorElem.textContent = "Parámetros numéricos inválidos.";
            return;
          }}

          const cfg = {{
            center_frequency: centerMHz * 1e6,
            span: spanMHz * 1e6,
            sample_rate_hz: fsMHz * 1e6,
            resolution_hz: rbwHz,
            antenna_port: 1,
            window: "hamming",
            overlap: 0.5,
            lna_gain: lna,
            vga_gain: vga,
            antenna_amp: antAmp
          }};

          mensajeErrorElem.textContent = "";

          fetch("/configuration", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify(cfg)
          }})
          .then(r => r.json())
          .then(j => {{
            console.log("START config:", j);
            estadoElem.textContent = "Configuración enviada. Esperando PSD...";
          }})
          .catch(err => {{
            console.error("Error START:", err);
            mensajeErrorElem.textContent = "Error al enviar configuración START.";
          }});
        }}

        // STOP: envía span=0 para que run_server pare
        function stop() {{
          const cfg = {{
            center_frequency: 0,
            span: 0
          }};

          fetch("/configuration", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify(cfg)
          }})
          .then(r => r.json())
          .then(j => {{
            console.log("STOP config:", j);
            estadoElem.textContent = "STOP enviado. El sensor debería detener la adquisición.";
          }})
          .catch(err => {{
            console.error("Error STOP:", err);
            mensajeErrorElem.textContent = "Error al enviar STOP.";
          }});
        }}
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

