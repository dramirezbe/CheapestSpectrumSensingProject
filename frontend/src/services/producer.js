// producer.js (DEV ONLY)
// Simulate a data source sending Float32Array frames.
// Dev-only: main.jsx imports this only when import.meta.env.DEV

import { pushFrame } from './streamingSpectrum';

const N = 4096;

// Helper: create a Float32Array with random noise shaped like a spectrum
function generateSpectrum() {
  const a = new Float32Array(N);
  const baseline = 0.1;
  for (let i = 0; i < N; i++) {
    a[i] = baseline + (Math.random() - 0.5) * 0.05;
  }
  const addPeak = (center, width, amp) => {
    const start = Math.max(0, Math.floor(center - width));
    const end = Math.min(N - 1, Math.floor(center + width));
    for (let i = start; i <= end; i++) {
      const d = Math.abs(i - center);
      const v = amp * Math.exp(-(d * d) / (2 * width * width));
      a[i] += v;
    }
  };

  addPeak(N * 0.25, 40, 2.0);
  addPeak(N * 0.5, 80, 1.2);
  addPeak(N * 0.8, 20, 0.9);

  for (let i = 0; i < N; i++) {
    a[i] += (Math.random() - 0.5) * 0.02;
  }
  return a;
}

// Emit frames at about 60 fps (producer faster than consumer)
const PRODUCER_FPS = 60;
const INTERVAL_MS = Math.round(1000 / PRODUCER_FPS);

let timer = setInterval(() => {
  const frame = generateSpectrum(); // Float32Array length N
  // pushFrame accepts Float32Array or ArrayBuffer
  pushFrame(frame);
}, INTERVAL_MS);

// Optional console controls during dev
window.__spectrumProducer = {
  stop: () => {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
  },
  start: () => {
    if (!timer) timer = setInterval(() => pushFrame(generateSpectrum()), INTERVAL_MS);
  }
};
