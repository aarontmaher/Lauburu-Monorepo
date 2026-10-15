import React, { useState, useEffect } from 'react';
import { api } from '../../services/api';
import { MovesenseStreamPane } from './panes/MovesenseStreamPane';
import { KamathFilterPane } from './panes/KamathFilterPane';
import { HeartRatePane } from './panes/HeartRatePane';
import { BloodPressurePane } from './panes/BloodPressurePane';
import { GrapplingKinematicsPane } from './panes/GrapplingKinematicsPane';
import { MedicalAiAnalysisPane } from './panes/MedicalAiAnalysisPane';
import { TinyMlGaugePane } from './panes/TinyMlGaugePane';

export function BiometricsDspView({ biometricsState, onDispatchAction }) {
  const bio = biometricsState || {};
  const devicesList = bio.devices || (bio.movesenseStream ? [bio.movesenseStream] : []);
  
  const [isScanning, setIsScanning] = useState(false);
  const [ansiLogs, setAnsiLogs] = useState([]);

  const handleConnectBluetooth = async () => {
    setIsScanning(true);
    try {
      const res = await api.connectBiometrics(["Movesense Chest", "Movesense Bicep", "Whoop"]);
      if (res && res.instructions) {
        alert(res.instructions);
      }
    } catch (e) {
      alert("Error connecting: " + e.message);
    }
    setTimeout(() => setIsScanning(false), 3000);
  };

  useEffect(() => {
    const timer = setInterval(async () => {
      const logs = await api.getBiometricsAnsi();
      if (logs && logs.logs) setAnsiLogs(logs.logs);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header Banner */}
      <div className="cyber-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '1.4rem' }}>🫀</span>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--accent-emerald)' }}>
              2. MEDICAL-GRADE BIOMETRICS & KINEMATICS DSP
            </h2>
            <span className="badge badge-emerald">512Hz ECG / ZONE 2 DFA-alpha1</span>
          </div>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Multi-Device BLE Connection, Movesense Medical Class IIa, Real-time HRV.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="cyber-btn" onClick={handleConnectBluetooth} disabled={isScanning}>
            {isScanning ? 'Scanning...' : '📡 Connect Bluetooth'}
          </button>
          <button className="cyber-btn" onClick={() => onDispatchAction && onDispatchAction('/ping')}>
            🫀 Calibrate 512Hz
          </button>
        </div>
      </div>
      
      {ansiLogs.length > 0 && (
        <div className="cyber-card" style={{ background: '#0a0a0a' }}>
          <div style={{ color: 'var(--accent-cyan)', fontWeight: 600, marginBottom: '8px' }}>BLUETOOTH DAEMON ANSI LOGS</div>
          <div style={{ height: '150px', overflowY: 'auto', fontFamily: 'monospace', fontSize: '0.8rem', whiteSpace: 'pre-wrap' }}>
            {ansiLogs.join('\n')}
          </div>
        </div>
      )}

      {/* Dynamic Device Panes */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {devicesList.map((dev, idx) => (
          <div key={idx} className="cyber-card" style={{ borderLeft: '4px solid var(--accent-cyan)' }}>
            <h3 style={{ marginBottom: '16px', color: 'var(--text-primary)' }}>{dev.device_name || dev.sensorId || `Device ${idx+1}`}</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
              <MovesenseStreamPane streamData={dev} />
              <HeartRatePane bio={{ ...bio, heartRateBpm: dev.heart_rate_bpm || dev.heartRateBpm, zone2Status: dev.status || bio.zone2Status }} />
              <KamathFilterPane filterData={bio.kamathFilter} />
              <TinyMlGaugePane bio={bio} />
            </div>
          </div>
        ))}
        {devicesList.length === 0 && (
          <div className="cyber-card" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
            No Bluetooth Devices Connected. Click "Connect Bluetooth" to scan.
          </div>
        )}
      </div>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
        <BloodPressurePane pttData={bio.pttBloodPressure} />
        <GrapplingKinematicsPane gmapData={bio.grapplingMap} />
      </div>

      <MedicalAiAnalysisPane />
    </div>
  );
}

export default BiometricsDspView;
