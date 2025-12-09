/**
@file services/cfg.js
 */

// --- 1. Environment Variable Initialization ---
const VITE_API_PORT = import.meta.env.VITE_API_PORT || "8000";
const VITE_API_IP = import.meta.env.VITE_API_IP || "127.0.0.1";

const VITE_DEVELOPMENT_STRING = import.meta.env.VITE_DEVELOPMENT;
const inDevelopment = (VITE_DEVELOPMENT_STRING === 'true' || VITE_DEVELOPMENT_STRING === '1');

let baseApiUrl;
if (inDevelopment) {
    // In Development, use HTTP
    baseApiUrl = `http://${VITE_API_IP}:${VITE_API_PORT}/api/v1`;
}
else {
    // In Production/Other, use HTTPS
    baseApiUrl = `https://${VITE_API_IP}:${VITE_API_PORT}/api/v1`;
}

// --- 3. Endpoint Paths and Final Export ---
const REALTIME_EP = import.meta.env.VITE_REALTIME_EP || "/front/realtime";
const DATA_EP = import.meta.env.VITE_DATA_EP || "/front/data";
const RECONNECT_INTERVAL_MS_WS = 3000;
const MAX_RECONNECT_ATTEMPTS_WS = 5;

const api_cfg = {
    baseApiUrl,
    REALTIME_EP,
    DATA_EP,
    RECONNECT_INTERVAL_MS_WS,
    MAX_RECONNECT_ATTEMPTS_WS,
    inDevelopment
};



class SocketService {
    /**
     * @param {string} wsPath - The path or endpoint for the WebSocket connection (e.g., 'metrics').
     * @param {number} [wsPort] - Optional port number if different from the baseApiUrl's default.
     */
    constructor(wsPath) {
        // Construct the full WebSocket URL
        // Example: ws://localhost:8000/ws/metrics
        this.fullWsUrl = `${baseApiUrl}${wsPath}`; 
        this.socket = null;
        this.shouldReconnect = true; // Flag to control reconnection behavior
        this.reconnectAttempts = 0;
        this.messageListeners = []; // Array to hold functions that handle incoming messages
    }

    /**
     * Starts the WebSocket connection and sets up event handlers.
     */
    open() {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            console.log("WebSocket is already open.");
            return;
        }

        this.socket = new WebSocket(this.fullWsUrl);
        
        this.socket.onopen = (event) => {
            console.log(`WebSocket connected to: ${this.fullWsUrl}`);
            this.reconnectAttempts = 0; // Reset attempts on successful connection
            // You can call a user-defined onOpen callback here if needed
            this.onOpenEvent = event;
        };

        this.socket.onmessage = (event) => {
            // Distribute the incoming message to all registered listeners
            const data = JSON.parse(event.data);
            this.messageListeners.forEach(listener => listener(data));
        };

        this.socket.onclose = (event) => {
            console.log(`WebSocket closed. Code: ${event.code}. Reason: ${event.reason}`);
            // Attempt to reconnect only if `close()` wasn't explicitly called
            if (this.shouldReconnect) {
                this.scheduleReconnect();
            }
        };

        this.socket.onerror = (error) => {
            console.error("WebSocket error:", error);
            // Error typically triggers onclose, where reconnection logic is handled
        };
    }

    /**
     * Closes the WebSocket connection and prevents automatic reconnection.
     */
    close() {
        if (this.socket) {
            this.shouldReconnect = false; // Stop reconnection attempts
            this.socket.close(1000, "Client closed connection.");
            console.log("WebSocket connection manually closed.");
        }
    }

    /**
     * Schedules a reconnection attempt with exponential backoff and a maximum limit.
     */
    scheduleReconnect() {
        if (this.reconnectAttempts >= RECONNECT_INTERVAL_MS_WS) {
            console.error("Maximum reconnection attempts reached. Giving up.");
            return;
        }

        const delay = RECONNECT_INTERVAL_MS_WS * Math.pow(2, this.reconnectAttempts);
        this.reconnectAttempts++;
        
        console.log(`Attempting to reconnect in ${delay}ms (Attempt ${this.reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS_WS})...`);
        
        setTimeout(() => {
            if (this.shouldReconnect) {
                this.open();
            }
        }, delay);
    }
    
    /**
     * Registers a callback function to handle incoming messages.
     * @param {function(any): void} listener 
     */
    onMessage(listener) {
        this.messageListeners.push(listener);
    }
    
    /**
     * Removes a callback function from the message listeners.
     * @param {function(any): void} listener 
     */
    removeMessageListener(listener) {
        this.messageListeners = this.messageListeners.filter(l => l !== listener);
    }

    /**
     * Sends data over the WebSocket connection.
     * @param {Object} data - The data object to send.
     */
    send(data) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(data));
        } else {
            console.warn("WebSocket not open. Cannot send data.");
        }
    }
}

const getCssVar = (name) => {return getComputedStyle(document.documentElement).getPropertyValue(name).trim();}

export default SocketService;
export { getCssVar };

export { api_cfg };