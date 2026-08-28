import React, { useState, useEffect } from 'react';
import TerminalManager from '../TerminalManager';
import TriOrchestratorLiveChatView from '../TriOrchestratorLiveChatView';

const GlobalFloatingDrawer = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('chat'); // Default to AI Chat
  const [drawerSize, setDrawerSize] = useState('60vh'); // 35vh, 60vh, 90vh

  // Handle Cmd+J toggle
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'j') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        style={{
          position: 'fixed',
          bottom: '20px',
          right: '20px',
          background: 'linear-gradient(135deg, #0284c7, #38bdf8)',
          color: 'black',
          border: '1px solid rgba(255,255,255,0.2)',
          borderRadius: '50px',
          padding: '10px 20px',
          cursor: 'pointer',
          zIndex: 9999,
          boxShadow: '0 4px 15px rgba(56,189,248,0.5)',
          fontWeight: '900',
          display: 'flex',
          gap: '8px',
          alignItems: 'center'
        }}
      >
        <span>💬 Console (Cmd+J)</span>
      </button>
    );
  }

  return (
    <div style={{
      position: 'fixed',
      bottom: 0,
      left: '280px', // Respect the sidebar
      right: 0,
      height: drawerSize,
      background: 'rgba(15, 23, 42, 0.98)',
      backdropFilter: 'blur(10px)',
      borderTop: '1px solid #38bdf8',
      borderLeft: '1px solid #38bdf8',
      borderTopLeftRadius: '16px',
      boxShadow: '0 -10px 40px rgba(0,0,0,0.7)',
      zIndex: 9999,
      display: 'flex',
      flexDirection: 'column',
      color: '#fff',
      transition: 'height 0.2s ease-out'
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '0.5rem 1rem',
        borderBottom: '1px solid rgba(255,255,255,0.1)',
        background: '#0f172a',
        borderTopLeftRadius: '16px'
      }}>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <button
            onClick={() => setActiveTab('chat')}
            style={{
              background: 'transparent',
              color: activeTab === 'chat' ? '#38bdf8' : '#94a3b8',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 'bold',
              padding: '0.5rem',
              borderBottom: activeTab === 'chat' ? '2px solid #38bdf8' : '2px solid transparent'
            }}
          >
            💬 Tri-Orchestrator Chat
          </button>
          <button
            onClick={() => setActiveTab('terminal')}
            style={{
              background: 'transparent',
              color: activeTab === 'terminal' ? '#38bdf8' : '#94a3b8',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 'bold',
              padding: '0.5rem',
              borderBottom: activeTab === 'terminal' ? '2px solid #38bdf8' : '2px solid transparent'
            }}
          >
            💻 Network Terminals
          </button>
        </div>
        
        <div style={{ display: 'flex', gap: '0.8rem', alignItems: 'center' }}>
          <button onClick={() => setDrawerSize('35vh')} style={{ background: 'transparent', color: drawerSize === '35vh' ? '#38bdf8' : '#64748b', border: 'none', cursor: 'pointer', fontSize: '1rem', fontWeight: 'bold' }}>_</button>
          <button onClick={() => setDrawerSize('60vh')} style={{ background: 'transparent', color: drawerSize === '60vh' ? '#38bdf8' : '#64748b', border: 'none', cursor: 'pointer', fontSize: '1rem', fontWeight: 'bold' }}>☐</button>
          <button onClick={() => setDrawerSize('95vh')} style={{ background: 'transparent', color: drawerSize === '95vh' ? '#38bdf8' : '#64748b', border: 'none', cursor: 'pointer', fontSize: '1rem', fontWeight: 'bold' }}>⇡</button>
          <div style={{ width: '1px', height: '16px', background: 'rgba(255,255,255,0.2)' }}></div>
          <button
            onClick={() => setIsOpen(false)}
            style={{ background: 'transparent', color: '#f1f5f9', border: 'none', cursor: 'pointer', fontSize: '1.2rem' }}
          >
            ✖
          </button>
        </div>
      </div>

      <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
        {activeTab === 'chat' && <TriOrchestratorLiveChatView />}
        {activeTab === 'terminal' && <TerminalManager />}
      </div>
    </div>
  );
};

export default GlobalFloatingDrawer;
