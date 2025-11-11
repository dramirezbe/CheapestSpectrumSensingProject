import React, { useEffect, useRef } from "react";
import uPlot from "uplot";
import "uplot/dist/uPlot.min.css";
import { subscribe } from "../services/streamingSpectrum";
import "./SpectrumPlot.css";

const N = 4096;
const TARGET_FPS = 15;
const FRAME_MS = 1000 / TARGET_FPS;

export default function SpectrumPlot() {
  const wrapperRef = useRef(null);
  const plotRootRef = useRef(null);
  const uRef = useRef(null);
  const latestFrameRef = useRef(null); // owned Float32Array latest
  const scratchRef = useRef(null);     // reusable scratch of length N
  const rafRef = useRef(null);
  const userFrozenRef = useRef(false);
  const unsubRef = useRef(null);

  useEffect(() => {
    const wrapper = wrapperRef.current;
    if (!wrapper) return;

    // create uPlot container
    const plotDiv = document.createElement("div");
    plotDiv.style.width = "100%";
    plotDiv.style.height = "360px";
    wrapper.appendChild(plotDiv);
    plotRootRef.current = plotDiv;

    // prepare x and initial y
    const x = new Float64Array(N);
    for (let i = 0; i < N; i++) x[i] = i;
    const y0 = new Float64Array(N);

    const opts = {
      title: "Spectrum Plot",
      width: plotDiv.clientWidth || 800,
      height: 360,
      series: [
        {}, // x
        {
          label: "Magnitude",
          stroke: "#0aa",
          width: 1,
          show: true
        }
      ],
      scales: {
        x: { time: false },
      },
      axes: [
        { space: 50 },
        {}
      ],
      plugins: []
    };

    const data = [x, y0];

    const u = new uPlot(opts, data, plotDiv);
    uRef.current = u;

    // resize observer
    const resizeObserver = new ResizeObserver(() => {
      try {
        u.setSize({ width: plotDiv.clientWidth, height: 360 });
      } catch (err) {
        console.error(err);
      }
    });
    resizeObserver.observe(wrapper);

    // reusable scratch
    scratchRef.current = new Float32Array(N);

    // autoscale state
    let currentMin = 0;
    let currentMax = 1;

    // user interaction handlers to freeze autoscale
    function onUserInteractStart() {
      userFrozenRef.current = true;
    }
    function onUserReset() {
      userFrozenRef.current = false;
    }
    plotDiv.addEventListener("mousedown", onUserInteractStart);
    plotDiv.addEventListener("wheel", onUserInteractStart, { passive: true });
    plotDiv.addEventListener("dblclick", onUserReset);

    // subscribe to frames
    const unsubscribe = subscribe((frame) => {
      let dataArr = frame;
      if (dataArr instanceof ArrayBuffer) dataArr = new Float32Array(dataArr);
      else if (!(dataArr instanceof Float32Array)) {
        if (Array.isArray(dataArr)) dataArr = Float32Array.from(dataArr);
        else return;
      }

      const len = Math.min(dataArr.length, N);
      scratchRef.current.set(dataArr.subarray(0, len));
      if (len < N) scratchRef.current.fill(0, len);

      // store an owned copy to avoid mutation races
      latestFrameRef.current = scratchRef.current.slice(0);
    });
    unsubRef.current = unsubscribe;

    // draw loop (throttled)
    let lastTs = 0;
    function drawLoop(ts) {
      if (!lastTs) lastTs = ts;
      const dt = ts - lastTs;
      if (dt >= FRAME_MS && latestFrameRef.current) {
        const latest = latestFrameRef.current;

        if (!userFrozenRef.current) {
          let min = Infinity, max = -Infinity;
          for (let i = 0; i < latest.length; i++) {
            const v = latest[i];
            if (v < min) min = v;
            if (v > max) max = v;
          }
          if (!Number.isFinite(min) || !Number.isFinite(max)) {
            min = 0; max = 1;
          }
          const pad = (max - min) * 0.05 || 1;
          currentMin = min - pad;
          currentMax = max + pad;

          try {
            u.setData([x, latest]);
            u.setScale("y", { min: currentMin, max: currentMax });
          } catch (err) {
            console.error(err);
          }
        } else {
          // user frozen: update series values without changing scale
          try {
            // uPlot doesn't have a direct typed-array-only series update; setData is reliable.
            u.setData([x, latest]);
          } catch (err) {
            console.error(err);
          }
        }

        lastTs = ts;
      }
      rafRef.current = requestAnimationFrame(drawLoop);
    }

    rafRef.current = requestAnimationFrame(drawLoop);

    // cleanup
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      if (unsubRef.current) unsubRef.current();
      plotDiv.removeEventListener("mousedown", onUserInteractStart);
      plotDiv.removeEventListener("wheel", onUserInteractStart);
      plotDiv.removeEventListener("dblclick", onUserReset);
      try { u.destroy(); } catch (err) { console.error(err); }
      try { resizeObserver.disconnect(); } catch (err) { console.error(err); }
      try { wrapper.removeChild(plotDiv); } catch (err) { console.error(err); }
    };
  }, []);

  return <div ref={wrapperRef} className="spectrum-plot" />;
}
