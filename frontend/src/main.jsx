import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import App from './App.jsx';

// Import dev-only mock producer (emits frames) only in dev builds
if (import.meta.env.DEV) {
  // dynamic import so bundler can drop it in production builds
  import('./services/producer.js');
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>
);
