/**
 * @file services/controlService.js
 */
import { api_cfg } from './cfg'; 

export const updateSensorParams = async (mac, params) => {
    const url = `${api_cfg.baseApiUrl}/front/params`;

    // 1. Prepare Payload
    const payload = { mac, params };

    // --- VERBOSE LOGGING START ---
    console.log(">>> [Control] Sending Payload:", JSON.stringify(payload, null, 2));
    // --- VERBOSE LOGGING END ---

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP Error: ${response.status}`);
        }

        const responseData = await response.json();
        
        // --- VERBOSE LOGGING START ---
        console.log("<<< [Control] API Response:", JSON.stringify(responseData, null, 2));
        // --- VERBOSE LOGGING END ---

        return responseData;
    } catch (error) {
        console.error("API Error sending params:", error);
        throw error;
    }
};