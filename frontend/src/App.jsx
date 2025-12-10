import React, { useState } from 'react';
import './App.css';
import Plot from './components/Plot';
import Controls from './components/Controls';

// Default MAC to ensure Plot has a target immediately on load
const DEFAULT_MAC = "d0:65:78:9c:dd:d0";

export default function App() {
  // We hold the shared state here
  const [selectedMac, setSelectedMac] = useState(DEFAULT_MAC);

  return (
    <div className="app-container"> 
      {/* 1. Controls updates the state when the user selects a different MAC */}
      <Controls 
        initialMac={DEFAULT_MAC} 
        onMacChange={setSelectedMac} 
      />

      {/* 2. Plot receives the current MAC and reacts by polling the correct data */}
      <Plot selectedMac={selectedMac} />
    </div>
  );
}