import React, { useState, useEffect } from 'react';

export function VoiceCodingHud({ onVoiceCommand }) {
  const [isListening, setIsListening] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(true);
  const [audioLevel, setAudioLevel] = useState(0);
  const [lastSpoken, setLastSpoken] = useState('Voice assistant standing by on Port 4000 Whisper.cpp/Piper bridge.');

  // Waveform animation when listening
  useEffect(() => {
    let interval = null;
    if (isListening) {
      interval = setInterval(() => {
        // Deterministic wave cycle without Math.random
        const t = Date.now() / 200;
        const level = Math.abs(Math.sin(t)) * 0.8 + 0.2;
        setAudioLevel(level);
      }, 100);
    } else {
      setAudioLevel(0);
    }
    return () => clearInterval(interval);
  }, [isListening]);

  const handleToggleListening = () => {
    const nextState = !isListening;
    setIsListening(nextState);
    if (nextState) {
      setLastSpoken('Listening for hands-free voice prompt (e.g. "synthesize TB4 DMA ring buffer")...');
    } else {
      setLastSpoken('Voice ingestion paused.');
    }
  };

  const handleSimulateVoiceInput = (phrase) => {
    setLastSpoken(`Recognized [Whisper.cpp]: "${phrase}"`);
    if (onVoiceCommand) onVoiceCommand(phrase);
  };

  // Generate 16 animated waveform bars
  const waveBars = Array.from({ length: 16 }, (_, i) => {
    const barHeight = isListening
      ? Math.max(4, Math.round(Math.abs(Math.sin(i * 0.4 + audioLevel * 3)) * 28))
      : 4;
    return barHeight;
  });

  return (
    <div className="cyber-panel" style={{ padding: '14px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '6px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '1rem' }}>🎙️</span>
          <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
            VOICE CODING HUD (STT / TTS)
          </span>
        </div>

        <div style={{ display: 'flex', gap: '6px' }}>
          <span className={`badge ${isListening ? 'badge-emerald' : 'badge-rose'}`} style={{ fontSize: '0.62rem' }}>
            {isListening ? '● MIC ACTIVE' : '○ MUTED'}
          </span>
          <span className="badge badge-purple" style={{ fontSize: '0.62rem' }}>
            ZERO-CLOUD PRIVACY
          </span>
        </div>
      </div>

      {/* Waveform Visualizer */}
      <div style={{
        height: '42px',
        background: 'var(--bg-primary)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-sm)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '4px',
        padding: '0 12px'
      }}>
        {waveBars.map((height, idx) => (
          <div
            key={idx}
            style={{
              width: '4px',
              height: `${height}px`,
              background: isListening ? 'var(--accent-cyan)' : 'var(--border-strong)',
              borderRadius: '2px',
              transition: 'height 0.1s ease',
              boxShadow: isListening ? '0 0 6px rgba(0,255,204,0.4)' : 'none'
            }}
          />
        ))}
      </div>

      {/* Voice Status & Quick Triggers */}
      <div style={{
        background: 'var(--bg-secondary)',
        padding: '8px 10px',
        borderRadius: 'var(--radius-sm)',
        border: '1px solid var(--border-subtle)',
        fontSize: '0.72rem',
        fontFamily: 'var(--font-mono)',
        color: 'var(--text-secondary)',
        lineHeight: 1.4
      }}>
        <div style={{ color: 'var(--accent-cyan)', fontWeight: 600, marginBottom: '2px' }}>
          SPEECH ENGINE TELEMETRY:
        </div>
        <div>{lastSpoken}</div>
      </div>

      {/* Controls & Quick Prompts */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '6px' }}>
        <div style={{ display: 'flex', gap: '6px' }}>
          <button
            onClick={handleToggleListening}
            className={`cyber-btn ${isListening ? 'cyber-btn-rose' : 'cyber-btn-cyan'}`}
            style={{ padding: '4px 10px', fontSize: '0.72rem' }}
          >
            <span>{isListening ? '⏹ Mute Mic' : '🎙️ Start Mic'}</span>
          </button>

          <button
            onClick={() => setTtsEnabled(!ttsEnabled)}
            className="cyber-btn"
            style={{ padding: '4px 8px', fontSize: '0.72rem', borderColor: ttsEnabled ? 'var(--accent-emerald)' : 'var(--border-subtle)' }}
          >
            <span>{ttsEnabled ? '🔊 TTS On' : '🔇 TTS Off'}</span>
          </button>
        </div>

        <div style={{ display: 'flex', gap: '4px' }}>
          <button
            onClick={() => handleSimulateVoiceInput('Optimize TB4 DMA ring buffer')}
            className="cyber-btn"
            style={{ padding: '2px 6px', fontSize: '0.65rem' }}
            title="Simulate STT input"
          >
            &quot;Optimize DMA&quot;
          </button>
          <button
            onClick={() => handleSimulateVoiceInput('Run ASan test suite')}
            className="cyber-btn"
            style={{ padding: '2px 6px', fontSize: '0.65rem' }}
            title="Simulate STT input"
          >
            &quot;Run ASan&quot;
          </button>
        </div>
      </div>
    </div>
  );
}

export default VoiceCodingHud;
