import re

with open('src/App.jsx', 'r') as f:
    content = f.read()

# We need to add GlobalFloatingDrawer and DeveloperSettingsView to imports
imports = """import GlobalFloatingDrawer from './components/GlobalFloatingDrawer';
import DeveloperSettingsView from './DeveloperSettingsView';
"""

if 'import GlobalFloatingDrawer' not in content:
    content = content.replace("import './App.css'\n", "import './App.css'\n" + imports)

# We want to replace the top-level div and nav layout with a sidebar layout
# The current render structure starts near `<div style={{ display: 'flex', flexDirection: 'column', height: '100vh', padding: '1rem', boxSizing: 'border-box' }}>`
# Let's find the start of the return statement.
start_idx = content.find("return (\n    <div style={{ display: 'flex', flexDirection: 'column'")
if start_idx == -1:
    start_idx = content.find("return (\n    <div")

# Let's just create a fresh component string and replace it. But we need to keep the state logic at the top.
# So I'll split by `return (` and only replace the render part.

state_part = content[:start_idx]

render_part = """return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', backgroundColor: 'var(--bg-dark)' }}>
      {/* SIDEBAR */}
      <aside style={{ width: '280px', background: '#0b1121', borderRight: '1px solid rgba(255,255,255,0.1)', display: 'flex', flexDirection: 'column', padding: '1rem', overflowY: 'auto' }}>
        <div className="brand" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '2rem' }}>
          <img src="/assets/lauburu_symbol.png" width="36" height="36" style={{ borderRadius: '8px', objectFit: 'cover', border: '1px solid rgba(0,255,157,0.3)', boxShadow: '0 0 10px rgba(0,255,157,0.2)' }} alt="Lauburu" />
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <h1 style={{ fontSize: '1.2rem', margin: 0, fontWeight: '800', color: '#fff', letterSpacing: '-0.5px' }}>Lauburu Swarm</h1>
            <span style={{ fontSize: '0.65rem', color: 'var(--primary-neon)', fontWeight: 'bold' }}>
              ● {swarmTotals.onlineNodes !== '--' ? `${swarmTotals.onlineNodes}/${swarmTotals.totalNodes} Nodes Online` : 'Telemetry Active'}
            </span>
          </div>
        </div>
        
        {/* NESTED SIDEBAR NAVIGATION */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          <div>
            <h3 style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#64748b', letterSpacing: '1px', marginBottom: '0.75rem', fontWeight: 'bold' }}>Live Operations</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              {[
                { id: 'global_profiler', label: '🌐 Global 11-Config Profiler', color: '#38bdf8' },
                { id: 'exo_cluster', label: '🪐 EXO Distributed Cluster', color: '#f59e0b' },
                { id: 'network_mesh', label: '🌐 Multi-Transport Matrix', color: '#f472b6' },
                { id: 'live_data_harvesters', label: '📡 Live Real-Data Streams', color: '#38bdf8' },
                { id: 'storage_analysis', label: '💾 Storage Analysis', color: '#14b8a6' }
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setMainNavTab(tab.id)}
                  style={{
                    background: mainNavTab === tab.id ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
                    borderLeft: mainNavTab === tab.id ? `3px solid ${tab.color}` : '3px solid transparent',
                    color: mainNavTab === tab.id ? '#fff' : '#94a3b8',
                    padding: '0.5rem 0.75rem',
                    textAlign: 'left',
                    borderRadius: '0 6px 6px 0',
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                    fontWeight: mainNavTab === tab.id ? '600' : '500',
                    transition: 'all 0.2s',
                    border: 'none', borderLeftWidth: '3px', borderLeftStyle: 'solid',
                    borderLeftColor: mainNavTab === tab.id ? tab.color : 'transparent'
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <h3 style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#64748b', letterSpacing: '1px', marginBottom: '0.75rem', fontWeight: 'bold' }}>Training & Arenas</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              {[
                { id: 'meta_training_debate', label: '🎮 AI Debate Game', color: '#ec4899' },
                { id: 'ai_training_game', label: '🥋 Genie 2 Tatami Arena', color: '#ec4899' },
                { id: 'ai_training', label: '🧠 AI Training & LoRA', color: '#c084fc' },
                { id: 'custom_voice_ide', label: '💻 Custom Voice IDE', color: '#10b981' }
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setMainNavTab(tab.id)}
                  style={{
                    background: mainNavTab === tab.id ? 'rgba(236, 72, 153, 0.15)' : 'transparent',
                    borderLeft: mainNavTab === tab.id ? `3px solid ${tab.color}` : '3px solid transparent',
                    color: mainNavTab === tab.id ? '#fff' : '#94a3b8',
                    padding: '0.5rem 0.75rem',
                    textAlign: 'left',
                    borderRadius: '0 6px 6px 0',
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                    fontWeight: mainNavTab === tab.id ? '600' : '500',
                    transition: 'all 0.2s',
                    border: 'none', borderLeftWidth: '3px', borderLeftStyle: 'solid', borderLeftColor: mainNavTab === tab.id ? tab.color : 'transparent'
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <h3 style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#64748b', letterSpacing: '1px', marginBottom: '0.75rem', fontWeight: 'bold' }}>Spatial & Biometrics</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              {[
                { id: 'spatial_map_editor', label: '🥋 Spatial Sandbox (3D)', color: '#10b981' },
                { id: 'grappling_vision', label: '🥋 Grappling Vision & NPU', color: '#10b981' }
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setMainNavTab(tab.id)}
                  style={{
                    background: mainNavTab === tab.id ? 'rgba(16, 185, 129, 0.15)' : 'transparent',
                    borderLeft: mainNavTab === tab.id ? `3px solid ${tab.color}` : '3px solid transparent',
                    color: mainNavTab === tab.id ? '#fff' : '#94a3b8',
                    padding: '0.5rem 0.75rem',
                    textAlign: 'left',
                    borderRadius: '0 6px 6px 0',
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                    fontWeight: mainNavTab === tab.id ? '600' : '500',
                    transition: 'all 0.2s',
                    border: 'none', borderLeftWidth: '3px', borderLeftStyle: 'solid', borderLeftColor: mainNavTab === tab.id ? tab.color : 'transparent'
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <h3 style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#64748b', letterSpacing: '1px', marginBottom: '0.75rem', fontWeight: 'bold' }}>System Settings</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              {[
                { id: 'dev_settings', label: '⚙️ Developer Settings', color: '#38bdf8' },
                { id: 'specialist_skills', label: '🛠️ Specialist Skills', color: '#58a6ff' },
                { id: 'future_sim', label: '🧬 Genetic MoE Sim', color: '#7c3aed' },
                { id: 'roi_triage', label: '🛠️ ROI Improvements', color: '#eab308' }
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setMainNavTab(tab.id)}
                  style={{
                    background: mainNavTab === tab.id ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
                    borderLeft: mainNavTab === tab.id ? `3px solid ${tab.color}` : '3px solid transparent',
                    color: mainNavTab === tab.id ? '#fff' : '#94a3b8',
                    padding: '0.5rem 0.75rem',
                    textAlign: 'left',
                    borderRadius: '0 6px 6px 0',
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                    fontWeight: mainNavTab === tab.id ? '600' : '500',
                    transition: 'all 0.2s',
                    border: 'none', borderLeftWidth: '3px', borderLeftStyle: 'solid', borderLeftColor: mainNavTab === tab.id ? tab.color : 'transparent'
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

        </div>
      </aside>

      {/* MAIN CONTENT AREA */}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        
        {/* Top Header / Sentinel HUD */}
        <div style={{ padding: '1rem', borderBottom: '1px solid rgba(255,255,255,0.05)', background: '#111827' }}>
           <LiveDeviceSentinelHUD />
           {error && <div className="error-banner" style={{ marginTop: '0.5rem' }}>⚠️ {error}</div>}
        </div>

        {/* Scrollable View Area */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', position: 'relative' }}>
          
          {mainNavTab === 'meta_training_debate' && <MetaTrainingGameDashboardView />}
          {mainNavTab === 'global_profiler' && <GlobalMeshShardingProfiler />}
          {mainNavTab === 'exo_cluster' && <ExoClusterView />}
          {mainNavTab === 'specialist_skills' && <ConsensusSpecialistSkillsDashboard />}
          {mainNavTab === 'ai_training_game' && <UnifiedGenieTatamiArenaView />}
          {mainNavTab === 'spatial_map_editor' && <SpatialGrapplingMapEditorView />}
          {mainNavTab === 'live_data_harvesters' && <LiveTrainingDataHarvesterView />}
          {mainNavTab === 'grappling_vision' && <GrapplingVisionBiometricsView />}
          {mainNavTab === 'dev_settings' && <DeveloperSettingsView />}
          {mainNavTab === 'ai_training' && <AITrainingHub />}
          {mainNavTab === 'future_sim' && <FutureNetworkSimulationHub />}
          {mainNavTab === 'storage_analysis' && <StorageAnalysisHub />}
          {mainNavTab === 'roi_triage' && <ROIImprovementsView roiStore={roiStore} setRoiStore={setRoiStore} />}
          {mainNavTab === 'network_mesh' && (
            <section className="card leaderboard-card">
              <div className="card-header-flex">
                <h2>🌐 Multi-Transport Matrix &amp; Self-Healing</h2>
                <span className="live-tag">Active Matrix</span>
              </div>
              <div style={{ background: '#0f172a', padding: '1rem', borderRadius: '10px', marginTop: '0.5rem' }}>
                <p style={{ color: '#94a3b8', fontSize: '0.8rem', margin: 0 }}>
                  Thunderbolt 4 DMA (10Gbps, 0.277ms RTT) • Tailscale WireGuard UDP • GL.iNet USB ADB Tethering • Qi 15W Power
                </p>
              </div>
            </section>
          )}

          <GlobalFloatingDrawer />
          <ModelDownloadSidebar />
        </div>
      </main>
    </div>
  )
}

export default App
"""

new_content = state_part + render_part

with open('src/App.jsx', 'w') as f:
    f.write(new_content)

print("App.jsx rewritten!")
