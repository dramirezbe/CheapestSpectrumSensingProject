/**
@file components/SpectrumPlot.jsx
*/
import React, { useEffect, useRef, useState } from "react";
import uPlot from "uplot";
import "uplot/dist/uPlot.min.css";

/**
 * SpectrumPlot (fixed)
 * - create uPlot only after metadata (fft_size) arrives
 * - always pass x and y arrays of the same length to u.setData()
 * - use requestAnimationFrame to batch plot updates
 */
export default function SpectrumPlot({ wsUrl, maxBinsShown = 2048 }) {
  const rootRef = useRef(null);
  const wsRef = useRef(null);
  const uplotRef = useRef(null);
  const [meta, setMeta] = useState(null);

  // Keep the base X array (Float64Array) here after creating the plot
  const xRef = useRef(null);
  // Reusable y buffer reference (Float64Array)
  const yRef = useRef(null);

  // pending PSD to draw (Float32Array -> will be copied into yRef on raf)
  const pendingRef = useRef(null);
  const rafRef = useRef(null);

  // Create uPlot only after we get metadata. If metadata changes (fft_size), recreate.
  useEffect(() => {
    if (!meta || !rootRef.current) return;

    // Destroy existing plot if present
    if (uplotRef.current) {
      uplotRef.current.destroy();
      uplotRef.current = null;
    }

    const N = meta.fft_size || maxBinsShown;
    // build x: 0..N-1
    const x = new Float64Array(N);
    for (let i = 0; i < N; i++) x[i] = i;
    xRef.current = x;

    // initial zero y
    const y = new Float64Array(N);
    yRef.current = y;

    const data = [x, y];

    const opts = {
      width: rootRef.current.clientWidth || 800,
      height: 380,
      scales: {
        x: { time: false },
        y: { auto: true },
      },
      series: [
        { label: "bin" },
        {
          label: "PSD (dB)",
          stroke: "#1cd362ff",
          width: 1.5,
        },
      ],
      axes: [
        {
          show: true,
          values: (u, vals) => vals.map((v) => v.toFixed(0)),
          stroke: "#ffff",
          grid: { show: true, stroke: "#91878785", width: 0.5 },
        },
        {
          show: true,
          values: (u, vals) => vals.map((v) => v.toFixed(0)),
          stroke: "#ffff",
          grid: { show: true, stroke: "#91878785", width: 0.5 },
        },
      ],
      cursor: { show: false },
      legend: { show: false },
    };

    uplotRef.current = new uPlot(opts, data, rootRef.current);

    // allow responsive resizing
    const onResize = () => {
      if (!uplotRef.current) return;
      uplotRef.current.setSize({ width: rootRef.current.clientWidth });
    };
    window.addEventListener("resize", onResize);

    return () => {
      window.removeEventListener("resize", onResize);
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      if (uplotRef.current) {
        uplotRef.current.destroy();
        uplotRef.current = null;
      }
    };
  }, [meta, rootRef, maxBinsShown]);

  // schedule an RAF to draw the latest pending PSD (if any)
  const scheduleDraw = () => {
    if (rafRef.current) return; // already scheduled
    rafRef.current = requestAnimationFrame(() => {
      rafRef.current = null;
      const pending = pendingRef.current;
      if (!pending || !uplotRef.current || !xRef.current) return;

      const u = uplotRef.current;
      const x = xRef.current;
      const len = Math.min(pending.length, x.length);

      // Ensure yRef is right size
      if (!yRef.current || yRef.current.length !== len) {
        yRef.current = new Float64Array(len);
      }
      const y = yRef.current;

      // copy data: Float32 -> Float64
      // copy up to len bins
      for (let i = 0; i < len; i++) y[i] = pending[i];

      // pass x subarray with matching length (typed array view)
      const x_sub = x.subarray(0, len);

      // debug: lengths must match
      if (x_sub.length !== y.length) {
        console.warn("uPlot length mismatch", x_sub.length, y.length);
      }

      // update plot with matching-length arrays
      try {
        u.setData([x_sub, y]);
      } catch (err) {
        console.warn("uPlot setData failed:", err);
      }
    });
  };

  // WebSocket lifecycle: connect and receive frames
  useEffect(() => {
    const ws = new WebSocket(wsUrl);
    ws.binaryType = "arraybuffer";
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("WS connected", wsUrl);
    };

    ws.onmessage = (evt) => {
      // metadata (text)
      if (typeof evt.data === "string") {
        try {
          const m = JSON.parse(evt.data);
          setMeta(m);
        } catch (e) {
          console.warn("err:", e);
          console.warn("Non-JSON text from WS:", evt.data);
        }
        return;
      }

      // binary Float32Array PSD frame
      try {
        const arr = new Float32Array(evt.data);
        // store latest frame (overwrite older if not yet drawn)
        pendingRef.current = arr;
        scheduleDraw();
      } catch (err) {
        console.warn("Failed to parse binary PSD frame:", err);
      }
    };

    ws.onclose = () => console.log("WS closed");
    ws.onerror = (e) => console.warn("WS error", e);

    return () => {
      if (ws && ws.readyState === WebSocket.OPEN) ws.close();
    };
  }, [wsUrl]);

  return (
    <div>
      <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 8 }}>
        <div>
          <strong>{meta ? `Center ${(meta.center_freq / 1e6).toFixed(3)} MHz` : "Waiting for metadata..."}</strong>
        </div>
        <div style={{ marginLeft: "auto" }}>{meta ? `FFT ${meta.fft_size} | SR ${(meta.sample_rate / 1e6).toFixed(3)} MHz` : null}</div>
      </div>

      <div ref={rootRef} style={{ width: "100%", height: 380 }} />

      <div style={{ marginTop: 8, color: "#ffffffff", fontSize: 13 }}>
        Note: This component builds the plot after metadata arrives and ensures x/y lengths match before updating.
      </div>
    </div>
  );
}