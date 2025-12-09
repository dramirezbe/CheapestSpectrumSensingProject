/**
 * @file components/Plot.jsx 
 */
import React, { useEffect, useRef, useState } from "react";
import uPlot from "uplot";
import "uplot/dist/uPlot.min.css";
import { api_cfg, getCssVar } from '../services/cfg.js';
import "./Plot.css";

const N = 4096;
const POLL_INTERVAL_MS = 1000;

export default function Plot({ selectedMac }) {
  const wrapperRef = useRef(null);
  const uRef = useRef(null);
  
  // -- State for Metrics (Updates UI) --
  const [metrics, setMetrics] = useState({
      noise_floor_dbm: 0,
      peak_power_dbm: 0,
      avg_power_dbm: 0,
      snr_db: 0,
      auto_threshold_dbm: 0
  });

  // -- Refs for High-Speed Plotting (Updates Canvas) --
  const latestYRef = useRef(new Float32Array(N)); 
  const latestXRef = useRef(new Float64Array(N));
  const rafRef = useRef(null);
  const userFrozenRef = useRef(false);

  // 1. Initialize uPlot (Runs once)
  useEffect(() => {
    const wrapper = wrapperRef.current;
    if (!wrapper) return;

    // Create Plot Container
    const plotDiv = document.createElement("div");
    plotDiv.style.width = "100%";
    plotDiv.style.height = "360px";
    wrapper.appendChild(plotDiv);

    // Initial Data
    const x = new Float64Array(N);
    for (let i = 0; i < N; i++) x[i] = i; 
    const y = new Float64Array(N).fill(-100); 

    latestXRef.current = x;
    latestYRef.current = y;

    // uPlot Config
    const opts = {
      title: "Real-Time Spectrum",
      width: plotDiv.clientWidth || 800,
      height: 360,
      series: [
        {}, // x
        {
          label: "Magnitude",
          stroke: getCssVar('--primary-color') || "#00aaaa",
          width: 2,
          fill: "rgba(0, 170, 170, 0.1)", // Light fill for better visibility
          show: true
        }
      ],
      scales: {
        x: { time: false },
        y: { auto: false, range: [-120, -20] } // Fixed range prevents jitter
      },
      axes: [
        { 
            space: 50,
            label: "Frequency (MHz)",
            stroke: "#444",
            grid: { show: true, stroke: "#eee", width: 1 },
            values: (self, splits) => splits.map(v => v.toFixed(3))
        },
        {
            label: "Power (dBm/Hz)",
            stroke: "#444",
            grid: { show: true, stroke: "#eee", width: 1 }
        }
      ]
    };

    const u = new uPlot(opts, [x, y], plotDiv);
    uRef.current = u;

    // Resize Observer
    const resizeObserver = new ResizeObserver(() => {
      try {
        if(uRef.current) uRef.current.setSize({ width: plotDiv.clientWidth, height: 360 });
      } catch (err) {
        console.error(err);
      }
    });
    resizeObserver.observe(wrapper);

    // Interaction Handlers (Pause on click/hover)
    function onUserInteractStart() { userFrozenRef.current = true; }
    function onUserReset() { userFrozenRef.current = false; }
    
    plotDiv.addEventListener("mousedown", onUserInteractStart);
    plotDiv.addEventListener("wheel", onUserInteractStart, { passive: true });
    plotDiv.addEventListener("dblclick", onUserReset);

    // Animation Loop
    function drawLoop() {
        if (uRef.current && !userFrozenRef.current) {
            const currentX = latestXRef.current;
            const currentY = latestYRef.current;
            
            if (currentX.length === currentY.length) {
                uRef.current.setData([currentX, currentY]);
            }
        }
        rafRef.current = requestAnimationFrame(drawLoop);
    }
    rafRef.current = requestAnimationFrame(drawLoop);

    // Cleanup
    return () => {
      if(rafRef.current) cancelAnimationFrame(rafRef.current);
      resizeObserver.disconnect();
      plotDiv.removeEventListener("mousedown", onUserInteractStart);
      plotDiv.removeEventListener("wheel", onUserInteractStart);
      plotDiv.removeEventListener("dblclick", onUserReset);
      if(uRef.current) uRef.current.destroy();
      wrapper.innerHTML = "";
    };
  }, []); 

  // 2. Data Polling
  useEffect(() => {
    if (!selectedMac) return;

    const fetchData = async () => {
      try {
        const url = `${api_cfg.baseApiUrl}${api_cfg.DATA_EP}?mac=${selectedMac}`;
        const response = await fetch(url);
        
        if (!response.ok) throw new Error(`Fetch Error: ${response.status}`);

        const data = await response.json();
        
        // A. Update Metrics (React State)
        if (data.metrics) {
            setMetrics(data.metrics);
        }

        // B. Update Plot Data (Refs)
        if (data && data.Pxx && data.Pxx.length > 0) {
            
            const pxxRaw = data.Pxx;
            const startHz = data.start_freq_hz;
            const endHz = data.end_freq_hz;
            const count = pxxRaw.length;

            // Prepare Y
            const newY = new Float32Array(pxxRaw);

            // Prepare X
            const startMhz = startHz / 1e6;
            const endMhz = endHz / 1e6;
            const stepMhz = (endMhz - startMhz) / (count > 1 ? count - 1 : 1);

            const newX = new Float64Array(count);
            for(let i=0; i<count; i++) {
                newX[i] = startMhz + (i * stepMhz);
            }

            latestXRef.current = newX;
            latestYRef.current = newY;
        }
      } catch (err) {
        console.warn("Polling warning:", err);
      }
    };

    fetchData(); // Initial call
    const intervalId = setInterval(fetchData, POLL_INTERVAL_MS);

    return () => clearInterval(intervalId);
  }, [selectedMac]); 

  // --- RENDER ---
  return (
    <div className="spectrum-plot-card">
        
        {/* Metrics Header */}
        <div className="plot-metrics-header">
            <div className="metric-item">
                <span className="metric-label">Peak Power</span>
                <span className="metric-value highlight">{metrics.peak_power_dbm} <small>dBm</small></span>
            </div>
            <div className="metric-item">
                <span className="metric-label">Noise Floor</span>
                <span className="metric-value">{metrics.noise_floor_dbm} <small>dBm</small></span>
            </div>
            <div className="metric-item">
                <span className="metric-label">SNR</span>
                <span className="metric-value">{metrics.snr_db} <small>dB</small></span>
            </div>
            <div className="metric-item">
                <span className="metric-label">Avg Power</span>
                <span className="metric-value">{metrics.avg_power_dbm} <small>dBm</small></span>
            </div>
            <div className="metric-item">
                <span className="metric-label">Threshold</span>
                <span className="metric-value">{metrics.auto_threshold_dbm} <small>dBm</small></span>
            </div>
        </div>

        {/* The uPlot Container */}
        <div ref={wrapperRef} className="uplot-wrapper" />
    </div>
  );
}