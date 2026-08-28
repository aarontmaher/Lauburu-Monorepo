import React from 'react';
import PySparkMeshControlCenterView from './PySparkMeshControlCenterView';

const DeveloperSettingsView = () => {
  return (
    <div style={{ padding: '2rem' }}>
      <h1 style={{ marginBottom: '2rem', fontSize: '1.8rem', color: '#38bdf8' }}>⚙️ Developer Settings</h1>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
        <section style={{ padding: '1.5rem', background: 'rgba(15, 23, 42, 0.6)', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
          <h2 style={{ color: '#f1f5f9', borderBottom: '1px solid rgba(255, 255, 255, 0.1)', paddingBottom: '0.5rem', marginBottom: '1rem' }}>Big Data & Crons</h2>
          <PySparkMeshControlCenterView />
        </section>
        
        {/* We can add other dev settings here later */}
      </div>
    </div>
  );
};

export default DeveloperSettingsView;
