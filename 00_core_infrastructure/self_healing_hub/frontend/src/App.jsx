import { useState, useEffect } from 'react'
import './index.css'
import GlobalFloatingDrawer from './components/GlobalFloatingDrawer';
import DeveloperSettingsView from './DeveloperSettingsView';
import TerminalManager from './TerminalManager'
import AITrainingHub from './AITrainingHub'
import ROIImprovementsView from './ROIImprovementsView'
import Spatial3DMapView from './Spatial3DMapView'
import StorageAnalysisHub from './StorageAnalysisHub'
import FutureNetworkSimulationHub from './FutureNetworkSimulationHub'
import TriOrchestratorLiveChatView from './TriOrchestratorLiveChatView'
import UnifiedGenieTatamiArenaView from './UnifiedGenieTatamiArenaView'
import PySparkMeshControlCenterView from './PySparkMeshControlCenterView'
import GrapplingVisionBiometricsView from './GrapplingVisionBiometricsView'
import LiveTrainingDataHarvesterView from './LiveTrainingDataHarvesterView'
import SpatialGrapplingMapEditorView from './SpatialGrapplingMapEditorView'
import LiveDeviceSentinelHUD from './LiveDeviceSentinelHUD'
import ConsensusSpecialistSkillsDashboard from './ConsensusSpecialistSkillsDashboard'
import ExoClusterView from './ExoClusterView'
import GlobalMeshShardingProfiler from './GlobalMeshShardingProfiler'
import MetaTrainingGameDashboardView from './MetaTrainingGameDashboardView'
import CustomVoiceIDEView from './CustomVoiceIDEView'

function App() {
  const [telemetry, setTelemetry] = useState(null)
  const [registry, setRegistry] = useState(null)
  const [error, setError] = useState(null)
  const [mainNavTab, setMainNavTab] = useState('meta_training_dashboard');
  const [activeLeaderboardTab, setActiveLeaderboardTab] = useState('power_cables');
  const [spatialMap, setSpatialMap] = useState(null);
  const [spatialProjection, setSpatialProjection] = useState(null);
  const [roiStore, setRoiStore] = useState(null);
  const [powerCableData, setPowerCableData] = useState(null);
  const [meshMatrixData, setMeshMatrixData] = useState(null);
  const [selfHealingIncidents, setSelfHealingIncidents] = useState([]);
  const [unorthodoxActionFeedback, setUnorthodoxActionFeedback] = useState(null);

  useEffect(() => {
    const fetchCoreTelemetry = async () => {
      try {
        const telRes = await fetch('http://127.0.0.1:5001/api/telemetry');
        if (telRes.ok) setTelemetry(await telRes.json());
        setError(null);
      } catch (err) {
        setError('Failed to fetch telemetry. Is orchestrator running?');
      }
    };

    fetchCoreTelemetry();
    const interval = setInterval(fetchCoreTelemetry, 3000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const fetchTabData = async () => {
      try {
        const apiHost = window.location.hostname || 'localhost';
        if (mainNavTab === 'spatial_3d') {
          const [spatRes, projRes] = await Promise.all([
            fetch(`http://${apiHost}:5001/api/spatial_3d_map`),
            fetch(`http://${apiHost}:5001/api/spatial_dashboard_projection`)
          ]);
          if (spatRes.ok) setSpatialMap(await spatRes.json());
          if (projRes.ok) setSpatialProjection(await projRes.json());
        } else if (mainNavTab === 'roi_triage') {
          const roiRes = await fetch(`http://${apiHost}:5001/api/roi_improvements`);
          if (roiRes.ok) setRoiStore(await roiRes.json());
        } else if (mainNavTab === 'network_mesh') {
          const [powerRes, matrixRes, healRes] = await Promise.all([
            fetch(`http://${apiHost}:5001/api/power_cable_network_analysis`),
            fetch(`http://${apiHost}:5001/api/mesh_all_to_all_matrix`),
            fetch(`http://${apiHost}:5001/api/self_healing_incidents`)
          ]);
          if (powerRes.ok) setPowerCableData(await powerRes.json());
          if (matrixRes.ok) setMeshMatrixData(await matrixRes.json());
          if (healRes.ok) setSelfHealingIncidents(await healRes.json());
        }
      } catch (e) {
        console.warn('Tab data fetch error:', e);
      }
    };

    fetchTabData();
    const tabInterval = setInterval(fetchTabData, 4000);
    return () => clearInterval(tabInterval);
  }, [mainNavTab, activeLeaderboardTab]);

  useEffect(() => {
    const fetchRegistry = async () => {
      try {
        const res = await fetch('http://127.0.0.1:5001/api/devices')
        if (res.ok) setRegistry(await res.json())
      } catch (err) {
        console.error(err)
      }
    }
    fetchRegistry()
  }, [])

  const calculateSwarmTotals = () => {
    if (!telemetry?.devices) {
      const regCount = registry ? Object.keys(registry).length : 7
      return { totalRamGb: '--', usedRamGb: '--', avgCpu: '--', activeNpus: '--', totalNodes: regCount, onlineNodes: '--' }
    }
    const devices = Object.values(telemetry.devices)
    let totalRamMb = 0
    let usedRamMb = 0
    let cpuSum = 0
    let cpuCount = 0
    let activeNpus = 0
    let onlineNodes = 0

    devices.forEach(dev => {
      if (dev.memory?.total_mb) {
        totalRamMb += dev.memory.total_mb
        usedRamMb += (dev.memory.used_mb || 0)
        onlineNodes++
      }
      if (dev.cpu_usage != null) {
        cpuSum += dev.cpu_usage
        cpuCount++
      }
      if (dev.hardware?.npu && dev.hardware.npu !== 'None') {
        activeNpus++
      }
    })

    const totalNodesCount = registry ? Object.keys(registry).length : (devices.length || 7)

    return {
      totalRamGb: totalRamMb > 0 ? (totalRamMb / 1024).toFixed(1) : '--',
      usedRamGb: usedRamMb > 0 ? (usedRamMb / 1024).toFixed(1) : '--',
      avgCpu: cpuCount > 0 ? Math.round(cpuSum / cpuCount) : '--',
      activeNpus: activeNpus > 0 ? activeNpus : '--',
      totalNodes: totalNodesCount,
      onlineNodes: onlineNodes > 0 ? onlineNodes : (devices.filter(d => d.online || d.status === 'ONLINE').length || '--')
    }
  }

  const swarmTotals = calculateSwarmTotals()

  return (
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
                  </div>
      </main>
    </div>
  )
}

export default App
