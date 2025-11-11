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
    baseApiUrl = `http://${VITE_API_IP}:${VITE_API_PORT}`;
}
else {
    // In Production/Other, use HTTPS
    baseApiUrl = `https://${VITE_API_IP}:${VITE_API_PORT}`;
}

// --- 3. Endpoint Paths and Final Export ---
const SOCKET_SPECTRUM = import.meta.env.VITE_SOCKET_SPECTRUM || "/frontSpectrum";
const SOCKET_DEMOD = import.meta.env.VITE_SOCKET_DEMOD || "/frontDemod";
const PARAMS_EP = import.meta.env.VITE_PARAMS_EP || "/frontParams";
const STATUS_EP = import.meta.env.VITE_STATUS_EP || "/frontStatus";

const api_cfg = {
    baseApiUrl,
    SOCKET_SPECTRUM,
    SOCKET_DEMOD,
    PARAMS_EP,
    STATUS_EP,
    inDevelopment
};

class SocketService {
    constructor(payload, apiHandShakeUrl) {
        this.payload = payload;

        const protocolApi = inDevelopment ? 'http' : 'https';
        const protocolWs = inDevelopment ? 'ws' : 'wss';
        this.fullApiHandShakeUrl = `${protocolApi}://${baseApiUrl}${apiHandShakeUrl}`;
        this.WsUrl = `${protocolWs}://${baseApiUrl}`;
        this.fullWsUrl = null;

        this.initialConnection = false;
        this.sensorWs = null;
    }

    cleanupWs() {
        if (this.sensorWs) {
            console.log(`Closing existing WS connection to ${this.fullWsUrl}`);
            this.sensorWs.close();
            this.sensorWs = null;
        }
    }

    /**
     * Does backend handshake, returns true if successful, false otherwise
     */
    async requestConnection() {
        let isBusy = false;
        let deviceHash = null;
        try {
            
            const response = await fetch(this.fullApiHandShakeUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(this.payload)
            });

            
            if(response.ok) {
                
                const data = await response.json(); 
                
                console.log("Backend Handshake OK");
                isBusy = data.isBusy;
                deviceHash = data.deviceHash;
                
                if (deviceHash) {
                    this.fullWsUrl = `${this.WsUrl}/${deviceHash}`;
                }
            } else {
                console.error(`Handshake failed with status: ${response.status}`);
            }
        }
        catch (e) {
            console.error(`Handshake error: ${e}`);
        }
        
        if (isBusy) {
            console.log("Sensor is busy");
            this.initialConnection = false;
        } else if (deviceHash) {
             this.initialConnection = true;
        } else {
             this.initialConnection = false;
        }
        
        return this.initialConnection; //return true if the handshake was successful
    }

    /**
     * try to open WS
     */
    async openWs() {
        this.cleanupWs();
        
        const canConnect = await this.requestConnection(); 

        if (!canConnect) {
            return null;
        }

        this.sensorWs = new WebSocket(this.fullWsUrl);
        this.sensorWs.binaryType = 'arraybuffer';

        return this.sensorWs; 
    }

    startDataStream(onDataReceived) {
        if (!this.sensorWs || !onDataReceived) {
            console.warn("No WS instance or onDataReceived callback provided.");
            this.cleanupWs();
            return null;
        }

        this.sensorWs.onopen = () => {
            console.log(`WS ${this.fullWsUrl} connected`);
        };

        this.sensorWs.onmessage = (evt) => {
            try {
                // evt.data is an ArrayBuffer
                const arr = new Float32Array(evt.data);
                onDataReceived(arr);
            } catch (err) {
                console.warn("Failed to parse binary PSD frame:", err);
            }
        };

        this.sensorWs.onerror = (err) => {
             console.error("WebSocket Error:", err);
        };
        this.sensorWs.onclose = () => {
             console.log("WebSocket connection closed.");
        };
    }   
}

export default SocketService;

export { api_cfg };