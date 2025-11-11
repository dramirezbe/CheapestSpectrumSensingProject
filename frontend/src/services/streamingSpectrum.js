// streamingSpectrum.js
// Simple pub/sub for streaming frames
// Usage: import { subscribe, pushFrame } from './streamingSpectrum';

const listeners = new Set();

/**
 * Subscribe to frames.
 * @param {(Float32Array|ArrayBuffer) => void} cb
 * @returns {() => void} unsubscribe
 */
export function subscribe(cb) {
  listeners.add(cb);
  return () => listeners.delete(cb);
}

/**
 * Push a new frame into the pipeline.
 * Accepts Float32Array or ArrayBuffer.
 * @param {Float32Array|ArrayBuffer} frame
 */
export function pushFrame(frame) {
  for (const cb of listeners) {
    try {
      cb(frame);
    } catch (err) {
      // keep other listeners alive
      console.error('streamingSpectrum subscriber error', err);
    }
  }
}
