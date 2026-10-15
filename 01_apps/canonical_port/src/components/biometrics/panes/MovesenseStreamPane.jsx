import React from 'react';

export function MovesenseStreamPane({ streamData }) {
  const ms = streamData || {};
  return (
    <div className="cyber-card">
      <div style={{ fontWeight: 600, color: 'var(--accent-emerald)', marginBottom: '12px' }}>
        MOVESENSE MEDICAL STREAM
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.8rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--text-muted)' }}>Status:</span>
          <span style={{ color: ms.connected ? 'var(--accent-emerald)' : 'var(--accent-amber)' }}>
            {ms.connected ? 'CONNECTED' : 'DISCONNECTED'}
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--text-muted)' }}>Sensor ID:</span>
          <span style={{ color: 'var(--text-primary)' }}>{ms.device_name || ms.sensorId || '--'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--text-muted)' }}>MAC Address:</span>
          <span style={{ color: 'var(--text-primary)' }}>{ms.mac || ms.device_address || '--'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--text-muted)' }}>Firmware:</span>
          <span style={{ color: 'var(--text-primary)' }}>{ms.firmware || '--'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--text-muted)' }}>Class:</span>
          <span style={{ color: 'var(--text-primary)' }}>{ms.medicalClass || '--'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--text-muted)' }}>Battery:</span>
          <span style={{ color: 'var(--text-primary)' }}>{ms.battery_pct !== undefined ? `${ms.battery_pct}%` : (ms.batteryPct !== undefined ? `${ms.batteryPct}%` : '--')}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--text-muted)' }}>Profile:</span>
          <span style={{ color: 'var(--text-primary)' }}>{ms.dsp_profile || ms.profile || '--'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--text-muted)' }}>Sampling Rate:</span>
          <span style={{ color: 'var(--accent-cyan)' }}>
            {(ms.samplingRateHz || ms.sampling_rate_hz) ? `${ms.samplingRateHz || ms.sampling_rate_hz} Hz` : '--'}
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--text-muted)' }}>Signal-to-Noise:</span>
          <span style={{ color: 'var(--accent-emerald)' }}>
            {(ms.ecgSnrDb !== undefined && ms.ecgSnrDb !== null) ? `${ms.ecgSnrDb} dB` : ((ms.ecg_snr_db !== undefined && ms.ecg_snr_db !== null) ? `${ms.ecg_snr_db} dB` : '--')}
          </span>
        </div>
      </div>
    </div>
  );
}
