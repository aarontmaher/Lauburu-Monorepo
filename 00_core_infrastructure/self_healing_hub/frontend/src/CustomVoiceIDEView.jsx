import React from 'react';
import TriOrchestratorLiveChatView from './TriOrchestratorLiveChatView';
import AppSimulatorWorkspace from './AppSimulatorWorkspace';
import BackendTerminal from './components/BackendTerminal';

export default function CustomVoiceIDEView() {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '1fr 2fr 1fr',
      gap: '16px',
      height: 'calc(100vh - 100px)',
      width: '100%',
      padding: '16px',
      boxSizing: 'border-box'
    }}>
      {/* Left Column: Voice & Chat */}
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column', 
        gap: '16px', 
        overflowY: 'auto',
        background: '#1e1e1e',
        borderRadius: '8px',
        padding: '16px',
        border: '1px solid #333'
      }}>
        <h2 style={{ margin: '0 0 16px 0', fontSize: '18px', color: '#61dafb' }}>🧠 AI Fabric Chat</h2>
        <TriOrchestratorLiveChatView />
      </div>

      {/* Center Column: App Workspace */}
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column',
        background: '#0f172a',
        borderRadius: '8px',
        border: '1px solid #1e293b',
        overflow: 'hidden'
      }}>
        <AppSimulatorWorkspace />
      </div>

      {/* Right Column: Terminals */}
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column', 
        gap: '16px', 
        overflowY: 'auto',
        background: '#1e1e1e',
        borderRadius: '8px',
        padding: '16px',
        border: '1px solid #333'
      }}>
        <h2 style={{ margin: '0 0 16px 0', fontSize: '18px', color: '#eab308' }}>⚙️ Daemon Logs</h2>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <BackendTerminal title="Exo MLX Native" endpoint="/api/logs/exo" />
        </div>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <BackendTerminal title="llama.cpp RPC" endpoint="/api/logs/llamacpp" />
        </div>
        <div style={{ height: '150px', display: 'flex', flexDirection: 'column', gap: '8px', opacity: 0.6 }}>
            <BackendTerminal title="Petals DHT (Background)" endpoint="/api/logs/petals" />
        </div>
      </div>
    </div>
  );
}
