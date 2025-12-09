/**
 * @file components/Plot.jsx 
 */
import React, { useEffect, useRef } from "react";
import uPlot from "uplot";
import "uplot/dist/uPlot.min.css";
import { api_cfg, getCssVar } from '../services/cfg.js';
import "./Plot.css";

const N = 4096;
const POLL_INTERVAL_MS = 1000;

export default function Plot({ selectedMac }) {
  const wrapperRef = useRef(null);
  const uRef = useRef(null);
  
  // Refs to store data for the animation loop
  const latestYRef = useRef(new Float32Array(N)); 
  const latestXRef = useRef(new Float64Array(N));
  const rafRef = useRef(null);
  const userFrozenRef = useRef(false);

  useEffect(() => {
    const wrapper = wrapperRef.current;
    if (!wrapper) return;

    // 1. Create Div
    const plotDiv = document.createElement("div");
    plotDiv.style.width = "100%";
    plotDiv.style.height = "360px";
    wrapper.appendChild(plotDiv);

    // 2. Initialize default Data (0 to N)
    const x = new Float64Array(N);
    for (let i = 0; i < N; i++) x[i] = i; 
    const y = new Float64Array(N).fill(-100); 

    latestXRef.current = x;
    latestYRef.current = y;

    // 3. Configure uPlot
    const opts = {
      title: "Spectrum Plot",
      width: plotDiv.clientWidth || 800,
      height: 360,
      series: [
        {}, // x
        {
          label: "Magnitude",
          stroke: getCssVar('--primary-color') || "#00ffff",
          width: 1,
          show: true
        }
      ],
      scales: {
        x: { time: false },
      },
      axes: [
        { 
            space: 50,
            label: "Frequency (MHz)",
            values: (self, splits) => splits.map(v => v.toFixed(3))
        },
        {
            label: "Power (dBm/Hz)"
        }
      ],
      plugins: []
    };

    const u = new uPlot(opts, [x, y], plotDiv);
    uRef.current = u;

    // 4. Resize Observer
    const resizeObserver = new ResizeObserver(() => {
      try {
        if(uRef.current) uRef.current.setSize({ width: plotDiv.clientWidth, height: 360 });
      } catch (err) {
        console.error(err);
      }
    });
    resizeObserver.observe(wrapper);

    // 5. User Interaction Handlers
    function onUserInteractStart() { userFrozenRef.current = true; }
    function onUserReset() { userFrozenRef.current = false; }
    
    plotDiv.addEventListener("mousedown", onUserInteractStart);
    plotDiv.addEventListener("wheel", onUserInteractStart, { passive: true });
    plotDiv.addEventListener("dblclick", onUserReset);

    // 6. Draw Loop
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

  // --- DATA POLLING EFFECT ---
  useEffect(() => {
    if (!selectedMac) return;

    const fetchData = async () => {
      try {
        const url = `${api_cfg.baseApiUrl}${api_cfg.DATA_EP}?mac=${selectedMac}`;
        const response = await fetch(url);
        
        if (!response.ok) throw new Error(`Fetch Error: ${response.status}`);

        const data = await response.json();
        
        // Ensure we have a valid Pxx array
        if (data && data.Pxx && data.Pxx.length > 0) {
            
            // --- VERBOSE LOGGING START ---
            console.log(`<<< [Plot] Fetched Frame (${data.Pxx.length} bins):`);
            console.log("    Range:", data.start_freq_hz, "-", data.end_freq_hz, "Hz");
            console.log("    Pxx Data:", data.Pxx); 
            // --- VERBOSE LOGGING END ---

            const pxxRaw = data.Pxx;
            const startHz = data.start_freq_hz;
            const endHz = data.end_freq_hz;
            const count = pxxRaw.length;

            // 1. Prepare Y Data
            const newY = new Float32Array(pxxRaw);

            // 2. Prepare X Data
            const startMhz = startHz / 1e6;
            const endMhz = endHz / 1e6;
            const stepMhz = (endMhz - startMhz) / (count > 1 ? count - 1 : 1);

            const newX = new Float64Array(count);
            for(let i=0; i<count; i++) {
                newX[i] = startMhz + (i * stepMhz);
            }

            // 3. Update Refs
            latestXRef.current = newX;
            latestYRef.current = newY;
        }
      } catch (err) {
        console.warn("Polling warning:", err);
      }
    };

    // Initial Fetch
    fetchData();

    // Start Polling Interval
    const intervalId = setInterval(fetchData, POLL_INTERVAL_MS);

    return () => clearInterval(intervalId);
  }, [selectedMac]); 

  return <div ref={wrapperRef} className="spectrum-plot" />;
}