import React, { useState } from 'react';
import IDENativeVoiceChannel from './components/IDENativeVoiceChannel';

export const DEVICE_PROFILES = {
  android: {
    id: 'android',
    name: 'Android Device (Pixel 10 Pro XL / S20+)',
    shortName: 'Android',
    icon: '🤖',
    width: 412,
    height: 890,
    radius: 40,
    notchType: 'camera_punch_hole',
    os: 'Android 15 (ARM64)',
    color: '#34d399'
  },
  iphone: {
    id: 'iphone',
    name: 'iPhone Simulator (iPhone 16 Pro)',
    shortName: 'iPhone',
    icon: '🍎',
    width: 393,
    height: 852,
    radius: 48,
    notchType: 'dynamic_island',
    os: 'iOS 18.2',
    color: '#38bdf8'
  },
  laptop: {
    id: 'laptop',
    name: 'Computer / Laptop Simulator (MacBook Pro)',
    shortName: 'Laptop / PC',
    icon: '💻',
    width: 1180,
    height: 740,
    radius: 12,
    notchType: 'mac_window_header',
    os: 'macOS Sequoia 15.3',
    color: '#a855f7'
  }
};

export default function AppSimulatorWorkspace({ children, activeDevice = 'android', onDeviceChange }) {
  const [device, setDevice] = useState(activeDevice);
  const [orientation, setOrientation] = useState('portrait'); // 'portrait', 'landscape'
  const [zoomLevel, setZoomLevel] = useState(0.95);
  const [showFrame, setShowFrame] = useState(true);

  const selectedProfile = DEVICE_PROFILES[device] || DEVICE_PROFILES.android;

  const effectiveWidth = orientation === 'portrait' ? selectedProfile.width : selectedProfile.height;
  const effectiveHeight = orientation === 'portrait' ? selectedProfile.height : selectedProfile.width;

  const handleSelectDevice = (devId) => {
    setDevice(devId);
    if (onDeviceChange) onDeviceChange(devId);
    if (devId === 'laptop') {
      setOrientation('landscape');
      setZoomLevel(0.9);
    } else {
      setOrientation('portrait');
      setZoomLevel(0.95);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', width: '100%' }}>
      
      {/* VOICE IDE CHANNEL */}
      <IDENativeVoiceChannel />

      
      {/* SIMULATOR CONTROL BAR */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(15,23,42,0.95), rgba(30,41,59,0.95))',
        border: '1px solid rgba(255,255,255,0.1)',
        borderRadius: '12px',
        padding: '0.6rem 1rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '0.8rem',
        boxShadow: '0 4px 20px rgba(0,0,0,0.4)'
      }}>
        {/* Device Switcher Chips */}
        <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.74rem', color: '#94a3b8', fontWeight: 'bold' }}>🧪 Target Simulator:</span>
          {Object.values(DEVICE_PROFILES).map(p => (
            <button
              key={p.id}
              onClick={() => handleSelectDevice(p.id)}
              style={{
                background: device === p.id ? `${p.color}25` : 'rgba(255,255,255,0.03)',
                border: device === p.id ? `1.5px solid ${p.color}` : '1px solid rgba(255,255,255,0.08)',
                color: device === p.id ? '#fff' : '#94a3b8',
                padding: '5px 12px',
                borderRadius: '8px',
                fontSize: '0.76rem',
                fontWeight: device === p.id ? 'bold' : '500',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.35rem',
                transition: 'all 0.2s ease'
              }}
            >
              <span>{p.icon}</span>
              <span>{p.name}</span>
            </button>
          ))}
        </div>

        {/* Viewport Scale & Orientation Controls */}
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
          {device !== 'laptop' && (
            <button
              onClick={() => setOrientation(orientation === 'portrait' ? 'landscape' : 'portrait')}
              style={{
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid rgba(255,255,255,0.15)',
                color: '#38bdf8',
                padding: '4px 10px',
                borderRadius: '6px',
                fontSize: '0.72rem',
                fontWeight: 'bold',
                cursor: 'pointer'
              }}
            >
              {orientation === 'portrait' ? '📱 Portrait' : '🔄 Landscape'}
            </button>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.72rem', color: '#94a3b8' }}>
            <span>Zoom:</span>
            {[0.75, 0.9, 1.0].map(z => (
              <button
                key={z}
                onClick={() => setZoomLevel(z)}
                style={{
                  background: zoomLevel === z ? '#38bdf8' : 'rgba(255,255,255,0.05)',
                  color: zoomLevel === z ? '#000' : '#cbd5e1',
                  border: 'none',
                  padding: '2px 7px',
                  borderRadius: '4px',
                  fontSize: '0.68rem',
                  fontWeight: 'bold',
                  cursor: 'pointer'
                }}
              >
                {Math.round(z * 100)}%
              </button>
            ))}
          </div>

          <button
            onClick={() => setShowFrame(!showFrame)}
            style={{
              background: showFrame ? 'rgba(56,189,248,0.15)' : 'rgba(255,255,255,0.05)',
              border: `1px solid ${showFrame ? '#38bdf8' : 'rgba(255,255,255,0.1)'}`,
              color: showFrame ? '#38bdf8' : '#94a3b8',
              padding: '4px 8px',
              borderRadius: '6px',
              fontSize: '0.7rem',
              fontWeight: 'bold',
              cursor: 'pointer'
            }}
          >
            {showFrame ? '🖼️ Frame On' : 'Bare View'}
          </button>
        </div>
      </div>

      {/* SIMULATOR VIEWPORT STAGE */}
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'flex-start',
        background: '#090d16',
        borderRadius: '16px',
        padding: '2rem 1rem',
        border: '1px solid rgba(255,255,255,0.05)',
        minHeight: '800px',
        overflowX: 'auto'
      }}>
        
        {/* PHYSICAL DEVICE FRAME MOCKUP */}
        <div style={{
          width: `${effectiveWidth}px`,
          height: `${effectiveHeight}px`,
          transform: `scale(${zoomLevel})`,
          transformOrigin: 'top center',
          background: '#020617',
          borderRadius: showFrame ? `${selectedProfile.radius}px` : '8px',
          border: showFrame ? '8px solid #1e293b' : '1px solid rgba(255,255,255,0.1)',
          boxShadow: showFrame ? '0 25px 60px rgba(0,0,0,0.8), 0 0 0 2px rgba(255,255,255,0.1)' : 'none',
          position: 'relative',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          flexShrink: 0
        }}>
          
          {/* TOP OS STATUS BAR / NOTCH */}
          {showFrame && (
            <>
              {selectedProfile.id === 'android' && (
                <div style={{
                  height: '28px',
                  background: '#020617',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '0 16px',
                  fontSize: '0.68rem',
                  color: '#94a3b8',
                  zIndex: 9999,
                  borderBottom: '1px solid rgba(255,255,255,0.04)'
                }}>
                  <span>9:41</span>
                  {/* Camera Punch Hole */}
                  <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#000', border: '1.5px solid #334155' }}></div>
                  <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                    <span>5G</span>
                    <span>100%</span>
                  </div>
                </div>
              )}

              {selectedProfile.id === 'iphone' && (
                <div style={{
                  height: '36px',
                  background: '#020617',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '0 18px',
                  fontSize: '0.68rem',
                  color: '#94a3b8',
                  zIndex: 9999,
                  borderBottom: '1px solid rgba(255,255,255,0.04)'
                }}>
                  <span>9:41</span>
                  {/* Dynamic Island */}
                  <div style={{
                    width: '90px',
                    height: '22px',
                    borderRadius: '16px',
                    background: '#000',
                    border: '1px solid #1e293b',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px'
                  }}>
                    <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10b981' }}></div>
                    <span style={{ fontSize: '0.55rem', color: '#cbd5e1' }}>Movesense</span>
                  </div>
                  <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                    <span>📶</span>
                    <span>🔋</span>
                  </div>
                </div>
              )}

              {selectedProfile.id === 'laptop' && (
                <div style={{
                  height: '34px',
                  background: '#0f172a',
                  display: 'flex',
                  alignItems: 'center',
                  padding: '0 12px',
                  borderBottom: '1px solid rgba(255,255,255,0.08)',
                  zIndex: 9999,
                  gap: '8px'
                }}>
                  <div style={{ display: 'flex', gap: '6px' }}>
                    <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#ef4444' }}></div>
                    <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#f59e0b' }}></div>
                    <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#10b981' }}></div>
                  </div>
                  <span style={{ fontSize: '0.7rem', color: '#94a3b8', marginLeft: 'auto', marginRight: 'auto', fontWeight: 'bold' }}>
                    Lauburu Mesh App — {selectedProfile.name}
                  </span>
                </div>
              )}
            </>
          )}

          {/* INNER APP SCROLLABLE CONTAINER */}
          <div style={{
            flex: 1,
            overflowY: 'auto',
            overflowX: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            position: 'relative'
          }}>
            {children}
          </div>

          {/* BOTTOM OS NAVIGATION BAR */}
          {showFrame && selectedProfile.id !== 'laptop' && (
            <div style={{
              height: '24px',
              background: '#020617',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              borderTop: '1px solid rgba(255,255,255,0.04)',
              zIndex: 9999
            }}>
              {/* Home Indicator Pill */}
              <div style={{ width: '100px', height: '4px', borderRadius: '2px', background: '#475569' }}></div>
            </div>
          )}

        </div>

      </div>

    </div>
  );
}
