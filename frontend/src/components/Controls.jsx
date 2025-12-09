/**
 * @file components/Controls.jsx 
 */
import React, { useState, useEffect, useRef } from 'react';
import { updateSensorParams } from '../services/controlService';
import './Controls.css';

// --- CONSTANTS ---
const MAC_LIST = ["d0:65:78:9c:dd:d0", "d0:65:78:9c:dd:d1", "d0:65:78:9c:dd:d2"];
const MIN_FREQ_HZ = 8000000;
const MAX_FREQ_HZ = 6000000000;

// Specific RBW Options
const RBW_OPTIONS = [300, 1000, 5000, 10000, 50000, 100000];

// --- HELPERS ---
const formatFrequency = (freqHz) => {
    if (freqHz >= 1e9) return (freqHz / 1e9).toFixed(3) + ' G';
    if (freqHz >= 1e6) return (freqHz / 1e6).toFixed(3) + ' M';
    if (freqHz >= 1e3) return (freqHz / 1e3).toFixed(3) + ' k';
    return freqHz.toFixed(0);
};

const formatBandwidth = (bwHz) => {
    if (bwHz >= 1e6) return (bwHz / 1e6).toFixed(1) + 'M';
    if (bwHz >= 1e3) return (bwHz / 1e3).toFixed(0) + 'k';
    return bwHz.toFixed(0);
};

// --- SUB-COMPONENTS ---

const DigitSpinner = ({ digit, onUp, onDown }) => (
    <div className="digit-spinner">
        <button className="arrow-btn" onClick={onUp}>▲</button>
        <span className="digit-display">{digit}</span>
        <button className="arrow-btn" onClick={onDown}>▼</button>
    </div>
);

const BandwidthSelector = ({ value, onChange }) => {
    const handleStep = (direction) => {
        let currentIndex = RBW_OPTIONS.indexOf(value);
        if (currentIndex === -1) currentIndex = 3; 
        
        let newIndex = currentIndex + direction;
        if (newIndex < 0) newIndex = 0;
        if (newIndex >= RBW_OPTIONS.length) newIndex = RBW_OPTIONS.length - 1;

        onChange(RBW_OPTIONS[newIndex]);
    };

    return (
        <div className="bw-spinner-container">
            <div className="value-display-row">
                <label>RBW</label>
            </div>
            <div className="bw-spinner-controls">
                <button className="arrow-btn" onClick={() => handleStep(-1)}>▼</button>
                <span className="bw-value-display">{formatBandwidth(value)}</span>
                <button className="arrow-btn" onClick={() => handleStep(1)}>▲</button>
            </div>
        </div>
    );
};

const FrequencySpinner = ({ value, onChange, min, max }) => {
    const clampFrequency = (freq) => Math.min(max, Math.max(min, freq));
    const paddedValue = String(value).padStart(12, '0');
    const digits = Array.from(paddedValue);

    const handleDigitChange = (index, direction) => {
        const placeValue = Math.pow(10, 12 - 1 - index);
        const change = direction === 'up' ? placeValue : -placeValue;
        onChange(clampFrequency(value + change));
    };

    return (
        <div className="frequency-spinner-container">
            <div className="value-display-row">
                <label>Center Freq</label>
                <span className="current-value">{formatFrequency(value)}</span>
            </div>
            <div className="frequency-display-row">
                {digits.map((digit, index) => (
                    <React.Fragment key={index}>
                        <DigitSpinner
                            digit={digit}
                            onUp={() => handleDigitChange(index, 'up')}
                            onDown={() => handleDigitChange(index, 'down')}
                        />
                        {(index === 2 || index === 5 || index === 8) && (
                            <span className="digit-separator">.</span>
                        )}
                    </React.Fragment>
                ))}
                <span className="unit-label">Hz</span>
            </div>
        </div>
    );
};

// --- MAIN CONTROLS ---

const Controls = ({ onMacChange, initialMac }) => {
    // Initialize with prop or default
    const [selectedMac, setSelectedMac] = useState(initialMac || MAC_LIST[0]);
    const [isRunning, setIsRunning] = useState(false);
    const [lastStatus, setLastStatus] = useState(null);

    const [config, setConfig] = useState({
        center_freq_hz: 9800000,
        resolution_hz: 10000,
        sample_rate_hz: 20000000,
        span: 20000000,
        scale: "dbm",
        window: "hamming",
        overlap: 0.5,
        lna_gain: 0,
        vga_gain: 0,
        antenna_amp: false,
        demodulation: {
            bw_hz: 200000,
            port_socket: "/1234"
        }
    });
    
    const [demodEnabled, setDemodEnabled] = useState(true);

    const isRunningRef = useRef(isRunning);
    const configRef = useRef(config);
    const demodEnabledRef = useRef(demodEnabled);
    const macRef = useRef(selectedMac);

    useEffect(() => {
        isRunningRef.current = isRunning;
        configRef.current = config;
        demodEnabledRef.current = demodEnabled;
        macRef.current = selectedMac;
    }, [isRunning, config, demodEnabled, selectedMac]);

    useEffect(() => {
        const intervalId = setInterval(async () => {
            const currentMac = macRef.current;
            
            // Default payload is NULL (for STOP state)
            let payloadParams = null;

            // If running, construct the actual configuration object
            if (isRunningRef.current) {
                const currentConfig = configRef.current;
                
                // Sync Demod Center Freq with Main Freq
                const demodConfig = {
                    ...currentConfig.demodulation,
                    center_freq_hz: currentConfig.center_freq_hz 
                };

                payloadParams = { 
                    ...currentConfig,
                    demodulation: demodEnabledRef.current ? demodConfig : null 
                };
            }

            // Always send to backend (params or null)
            try {
                await updateSensorParams(currentMac, payloadParams);
                setLastStatus('success');
                setTimeout(() => setLastStatus(null), 500);
            } catch (err) {
                setLastStatus('error');
                console.error("Error sending config:", err);
            }
        }, 1000);

        return () => clearInterval(intervalId);
    }, []);

    const handleMacSelection = (e) => {
        const newMac = e.target.value;
        setSelectedMac(newMac);
        if (onMacChange) {
            onMacChange(newMac);
        }
    };

    const handleGenericChange = (e) => {
        const { name, value, type, checked } = e.target;
        const finalVal = type === 'checkbox' ? checked : (type === 'number' ? parseFloat(value) : value);
        setConfig(prev => ({ ...prev, [name]: finalVal }));
    };

    const handleDemodChange = (e) => {
        const { name, value, type } = e.target;
        const finalVal = type === 'number' ? parseFloat(value) : value;
        setConfig(prev => ({
            ...prev,
            demodulation: { ...prev.demodulation, [name]: finalVal }
        }));
    };

    const setCenterFreq = (val) => setConfig(prev => ({ ...prev, center_freq_hz: val }));
    const setRbw = (val) => setConfig(prev => ({ ...prev, resolution_hz: val }));

    return (
        <div className="spectrum-controls-container">
            <div>
                <div className="cp-header">
                    <h2 className="cp-title">Sensor Control</h2>
                    <div className={`cp-feedback ${lastStatus}`}>
                        {lastStatus === 'success' && "● OK"}
                        {lastStatus === 'error' && "● ERR"}
                    </div>
                </div>

                <div className="cp-status-row">
                    <select className="cp-select" value={selectedMac} onChange={handleMacSelection}>
                        {MAC_LIST.map(mac => <option key={mac} value={mac}>{mac.split(':').slice(-2).join(':')}</option>)}
                    </select>
                    <button 
                        className={`cp-btn-toggle ${isRunning ? 'stop' : 'start'}`}
                        onClick={() => setIsRunning(!isRunning)}
                    >
                        {isRunning ? 'STOP' : 'RUN'}
                    </button>
                </div>
            </div>

            <div style={{ display:'flex', flexDirection:'column', gap:'10px', flex:1, overflowY:'auto' }}>
                
                <div className="cp-section">
                    <h4 className="cp-section-title">Tuner</h4>
                    <FrequencySpinner 
                        value={config.center_freq_hz} 
                        onChange={setCenterFreq} 
                        min={MIN_FREQ_HZ} 
                        max={MAX_FREQ_HZ} 
                    />
                    <BandwidthSelector 
                        value={config.resolution_hz} 
                        onChange={setRbw} 
                    />
                </div>

                <div className="settings-grid">
                    <div className="settings-column">
                        <div className="cp-section" style={{flex: 1}}>
                            <h4 className="cp-section-title">Hardware</h4>
                            <div className="cp-form-group">
                                <label className="cp-label">S. Rate</label>
                                <input className="cp-input" type="number" name="sample_rate_hz" 
                                    value={config.sample_rate_hz} onChange={handleGenericChange} />
                            </div>
                            <div className="cp-form-group">
                                <label className="cp-label">Span</label>
                                <input className="cp-input" type="number" name="span" 
                                    value={config.span} onChange={handleGenericChange} />
                            </div>
                            <div className="cp-form-group">
                                <label className="cp-label">LNA</label>
                                <input className="cp-input" type="number" name="lna_gain" 
                                    value={config.lna_gain} onChange={handleGenericChange} />
                            </div>
                            <div className="cp-form-group">
                                <label className="cp-label">VGA</label>
                                <input className="cp-input" type="number" name="vga_gain" 
                                    value={config.vga_gain} onChange={handleGenericChange} />
                            </div>
                            <div className="cp-form-group">
                                <label className="cp-label">Amp</label>
                                <input className="cp-checkbox" type="checkbox" name="antenna_amp" 
                                    checked={config.antenna_amp} onChange={handleGenericChange} />
                            </div>
                        </div>
                    </div>

                    <div className="settings-column">
                        <div className="cp-section">
                            <h4 className="cp-section-title">DSP</h4>
                            <div className="cp-form-group">
                                <label className="cp-label">Window</label>
                                <select className="cp-input" name="window" value={config.window} onChange={handleGenericChange}>
                                    <option value="hamming">Hamm</option>
                                    <option value="hanning">Hann</option>
                                    <option value="blackman">Blk</option>
                                    <option value="rectangular">Rect</option>
                                </select>
                            </div>
                            <div className="cp-form-group">
                                <label className="cp-label">Scale</label>
                                <select className="cp-input" name="scale" value={config.scale} onChange={handleGenericChange}>
                                    <option value="dbm">dBm</option>
                                    <option value="dbmv">dBmV</option>
                                    <option value="dbuv">dBuV</option>
                                    <option value="v">V</option>
                                    <option value="w">W</option>
                                </select>
                            </div>
                        </div>

                        <div className="cp-section" style={{flex: 1}}>
                            <div className="cp-form-group">
                                <h4 className="cp-section-title" style={{border:0, margin:0}}>Demod</h4>
                                <input className="cp-checkbox" type="checkbox" 
                                    checked={demodEnabled} onChange={(e) => setDemodEnabled(e.target.checked)} />
                            </div>
                            {demodEnabled && (
                                <div style={{marginTop: '10px'}}>
                                    <div className="cp-form-group">
                                        <label className="cp-label">BW</label>
                                        <input className="cp-input" type="number" name="bw_hz" 
                                            value={config.demodulation.bw_hz} onChange={handleDemodChange} />
                                    </div>
                                    <div className="cp-form-group">
                                        <label className="cp-label">Port</label>
                                        <input className="cp-input" type="text" name="port_socket" 
                                            value={config.demodulation.port_socket} onChange={handleDemodChange} />
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Controls;