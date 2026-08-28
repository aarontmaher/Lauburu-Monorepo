import React from 'react';

export function BiometricsDspView({ biometricsState, onDispatchAction }) {
  const bio = biometricsState || {};
  const ms = bio.movesenseStream || {};
  const kf = bio.kamathFilter || {};
  const ptt = bio.pttBloodPressure || {};
  const gmap = bio.grapplingMap || {};

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
            Movesense Medical Class IIa BLE GATT Stream, Kamath 20% Filter, Real-time HRV, and 31 OPML Grappling Nodes.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="cyber-btn" onClick={() => onDispatchAction && onDispatchAction('/ping')}>
            🫀 Calibrate 512Hz
          </button>
          <button className="cyber-btn" onClick={() => onDispatchAction && onDispatchAction('/audit')}>
            🔬 Kamath Filter
          </button>
        </div>
      </div>

      {/* Primary Metrics Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
        <div className="cyber-card">
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>HEART RATE (HR)</div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--accent-emerald)', marginTop: '4px' }}>
            {bio.heartRateBpm ? `${bio.heartRateBpm} BPM` : '--'}
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--accent-emerald)', marginTop: '4px' }}>
            ● {bio.zone2Status || 'ZONE_2_OPTIMAL'}
          </div>
        </div>

        <div className="cyber-card">
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>HRV (RMSSD)</div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--accent-cyan)', marginTop: '4px' }}>
            {bio.rmssdMs ? `${bio.rmssdMs} ms` : '--'}
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Parasympathetic Recovery State
          </div>
        </div>

        <div className="cyber-card">
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>DFA-alpha1 (FRACTAL HRV)</div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--accent-amber)', marginTop: '4px' }}>
            {bio.dfaAlpha1 !== undefined ? bio.dfaAlpha1 : '--'}
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Target: 0.750 (Aerobic Threshold 1)
          </div>
        </div>

        <div className="cyber-card">
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>PTT BLOOD PRESSURE</div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '4px' }}>
            {ptt.systolicMmhg ? `${ptt.systolicMmhg}/${ptt.diastolicMmhg} mmHg` : '--'}
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--accent-emerald)', marginTop: '4px' }}>
            ● {ptt.status || 'NOMINAL'} (PTT: {ptt.pulseTransitTimeMs || '--'} ms)
          </div>
        </div>
      </div>

      {/* Sensor Stream & Kinematics Panels */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
        <div className="cyber-card">
          <div style={{ fontWeight: 600, color: 'var(--accent-emerald)', marginBottom: '12px' }}>
            MOVESENSE MEDICAL CLASS IIA BLE STREAM
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.8rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Sensor ID:</span>
              <span style={{ color: 'var(--text-primary)' }}>{ms.sensorId || 'Movesense-Medical-230950000'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Sampling Rate:</span>
              <span style={{ color: 'var(--accent-cyan)' }}>{ms.samplingRateHz || 512} Hz (Pan-Tompkins DSP)</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Signal-to-Noise (SNR):</span>
              <span style={{ color: 'var(--accent-emerald)' }}>{ms.ecgSnrDb || 28.5} dB (Medical Class IIa)</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Kamath 20% Filter:</span>
              <span style={{ color: kf.isActive ? 'var(--accent-emerald)' : 'var(--accent-amber)' }}>
                {kf.isActive ? 'ACTIVE (Rejection: 1.42%)' : 'DISABLED'}
              </span>
            </div>
          </div>
        </div>

        <div className="cyber-card">
          <div style={{ fontWeight: 600, color: 'var(--accent-cyan)', marginBottom: '12px' }}>
            3D SPATIAL GRAPPLING KINEMATICS (31 OPML NODES)
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.8rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Active Position:</span>
              <span style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>{gmap.activePosition || 'Side Control'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Spatial Graph Topology:</span>
              <span>{gmap.totalNodes || 31} Nodes | {gmap.totalTransitions || 57} Transitions</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Tatami Bounds:</span>
              <span>8.0 x 8.0 x 2.5 m (120 FPS Metal Kinematics)</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Recent Submissions:</span>
              <span style={{ color: 'var(--accent-amber)' }}>Straight Armbar, Kimura, RNC</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default BiometricsDspView;
