import { useState, useEffect } from 'react'
import './index.css'
import TerminalManager from './TerminalManager'
import AITrainingHub from './AITrainingHub'
import ROIImprovementsView from './ROIImprovementsView'
import Spatial3DMapView from './Spatial3DMapView'
import StorageAnalysisHub from './StorageAnalysisHub'
import FutureNetworkSimulationHub from './FutureNetworkSimulationHub'
import ModelDownloadSidebar from './ModelDownloadSidebar'
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
import PublicBenchmarkArenaView from './PublicBenchmarkArenaView'
import MetaTrainingGameDashboardView from './MetaTrainingGameDashboardView'

function App() {
  const [telemetry, setTelemetry] = useState(null)
  const [registry, setRegistry] = useState(null)
  const [error, setError] = useState(null)
  const [mainNavTab, setMainNavTab] = useState('meta_training_debate');
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
    <div className="app-wrapper">
      <header className="header" style={{ marginBottom: '0.4rem', padding: '0.4rem 0.8rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div className="brand" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <img src="/assets/lauburu_symbol.png" width="28" height="28" style={{ borderRadius: '6px', objectFit: 'cover', border: '1px solid rgba(255,255,255,0.15)' }} alt="Lauburu" />
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <h1 style={{ fontSize: '1.1rem', margin: 0, fontWeight: '900', color: '#f8fafc' }}>Lauburu Swarm Mesh</h1>
            <span style={{ fontSize: '0.68rem', color: '#94a3b8' }}>
              • {swarmTotals.totalNodes} Physical Nodes • 82.8 GB Pooled VRAM
            </span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <a href="http://localhost:4000" target="_blank" rel="noreferrer" style={{ fontSize: '0.7rem', background: 'linear-gradient(135deg, #0284c7, #38bdf8)', color: '#000', padding: '3px 8px', borderRadius: '10px', textDecoration: 'none', fontWeight: 'bold' }}>
            📱 Port 4000 App Store ↗
          </a>
          <span style={{
            fontSize: '0.66rem',
            background: swarmTotals.onlineNodes !== '--' ? 'rgba(16,185,129,0.15)' : 'rgba(148,163,184,0.15)',
            color: swarmTotals.onlineNodes !== '--' ? '#34d399' : '#94a3b8',
            padding: '2px 7px',
            borderRadius: '10px',
            border: swarmTotals.onlineNodes !== '--' ? '1px solid rgba(16,185,129,0.3)' : '1px solid rgba(148,163,184,0.3)',
            fontWeight: 'bold'
          }}>
            ● Mesh {swarmTotals.onlineNodes !== '--' ? `${swarmTotals.onlineNodes}/${swarmTotals.totalNodes} Online` : 'Live Telemetry Active'}
          </span>
        </div>
      </header>

      {error && <div className="error-banner">⚠️ {error}</div>}

      {/* 🛰️ 7-LAYER LIVE DEVICE SENTINEL & DISCONNECTION MONITOR */}
      <LiveDeviceSentinelHUD />

      {/* MASTER APP NAVIGATION BAR */}
      <nav style={{
        display: 'flex',
        gap: '0.35rem',
        marginBottom: '0.8rem',
        overflowX: 'auto',
        whiteSpace: 'nowrap',
        padding: '0.2rem 0',
        scrollbarWidth: 'none'
      }}>
        {[
          { id: 'meta_training_debate', label: '🎮 Meta-Training Game & AI Debate', color: '#ec4899', activeBg: 'linear-gradient(135deg, #b91c1c, #ec4899)' },
          { id: 'global_profiler', label: '🌐 Global 11-Config Profiler', color: '#38bdf8', activeBg: 'linear-gradient(135deg, #0284c7, #38bdf8)' },
          { id: 'public_benchmarks', label: '🏆 Public AI Benchmarks', color: '#38bdf8', activeBg: 'linear-gradient(135deg, #0284c7, #38bdf8)' },
          { id: 'ai_training_game', label: '🥋 AI Training Game (Genie 2 Tatami Arena)', color: '#ec4899', activeBg: 'linear-gradient(135deg, #b91c1c, #ec4899)' },
          { id: 'exo_cluster', label: '🪐 EXO Distributed Cluster (:52415)', color: '#f59e0b', activeBg: 'linear-gradient(135deg, #b45309, #f59e0b)' },
          { id: 'specialist_skills', label: '🛠️ Specialist Skills & Consensus', color: '#58a6ff', activeBg: 'linear-gradient(135deg, #1f6feb, #58a6ff)' },
          { id: 'spatial_map_editor', label: '🥋 3D Instructional Map & Editor', color: '#10b981', activeBg: 'linear-gradient(135deg, #065f46, #10b981)' },
          { id: 'live_data_harvesters', label: '📡 Live Real-Data Streams', color: '#38bdf8', activeBg: 'linear-gradient(135deg, #0284c7, #38bdf8)' },
          { id: 'grappling_vision', label: '🥋 Grappling Vision & NPU (1.2W)', color: '#10b981', activeBg: 'linear-gradient(135deg, #047857, #10b981)' },
          { id: 'pyspark_mesh_crons', label: '⚡ PySpark Mesh & Crons (:8750)', color: '#38bdf8', activeBg: 'linear-gradient(135deg, #0284c7, #38bdf8)' },
          { id: 'live_chat', label: '💬 Tri-Orchestrator Chat', color: '#8b5cf6', activeBg: 'linear-gradient(135deg, #1e3a8a, #8b5cf6)' },
          { id: 'spatial_3d', label: '🛰️ 3D Spatial Radar', color: '#10b981', activeBg: 'linear-gradient(135deg, #064e3b, #10b981)' },
          { id: 'ai_training', label: '🧠 AI Training & LoRA', color: '#c084fc', activeBg: 'linear-gradient(135deg, #581c87, #8b5cf6)' },
          { id: 'terminal', label: '💻 Whole-Network Terminal', color: '#3b82f6', activeBg: 'linear-gradient(135deg, #1e3a8a, #3b82f6)' },
          { id: 'future_sim', label: '🧬 Genetic MoE Sim', color: '#7c3aed', activeBg: 'linear-gradient(135deg, #4c1d95, #7c3aed)' },
          { id: 'storage_analysis', label: '💾 Storage Analysis', color: '#14b8a6', activeBg: 'linear-gradient(135deg, #0f766e, #14b8a6)' },
          { id: 'network_mesh', label: '🌐 Multi-Transport Matrix', color: '#f472b6', activeBg: 'linear-gradient(135deg, #831843, #ec4899)' },
          { id: 'roi_triage', label: '🛠️ ROI Improvements', color: '#eab308', activeBg: 'linear-gradient(135deg, #713f12, #eab308)' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setMainNavTab(tab.id)}
            style={{
              flexShrink: 0,
              background: mainNavTab === tab.id ? tab.activeBg : '#111827',
              border: mainNavTab === tab.id ? `1px solid ${tab.color}` : '1px solid rgba(255,255,255,0.08)',
              color: '#fff',
              padding: '0.45rem 0.9rem',
              borderRadius: '20px',
              cursor: 'pointer',
              fontWeight: mainNavTab === tab.id ? 'bold' : '500',
              fontSize: '0.78rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
              boxShadow: mainNavTab === tab.id ? `0 2px 10px ${tab.color}40` : 'none',
              transition: 'all 0.2s ease'
            }}
          >
            <span>{tab.label}</span>
          </button>
        ))}
      </nav>

      {/* RENDER ACTIVE TAB */}
      {mainNavTab === 'meta_training_debate' && <MetaTrainingGameDashboardView />}
      {mainNavTab === 'global_profiler' && <GlobalMeshShardingProfiler />}
      {mainNavTab === 'public_benchmarks' && <PublicBenchmarkArenaView />}
      {mainNavTab === 'exo_cluster' && <ExoClusterView />}
      {mainNavTab === 'specialist_skills' && <ConsensusSpecialistSkillsDashboard />}
      {mainNavTab === 'ai_training_game' && <UnifiedGenieTatamiArenaView />}
      {mainNavTab === 'spatial_map_editor' && <SpatialGrapplingMapEditorView />}
      {mainNavTab === 'live_data_harvesters' && <LiveTrainingDataHarvesterView />}
      {mainNavTab === 'grappling_vision' && <GrapplingVisionBiometricsView />}
      {mainNavTab === 'pyspark_mesh_crons' && <PySparkMeshControlCenterView />}
      {mainNavTab === 'live_chat' && <TriOrchestratorLiveChatView />}
      {mainNavTab === 'spatial_3d' && <Spatial3DMapView spatialMap={spatialMap} />}
      {mainNavTab === 'ai_training' && <AITrainingHub />}
      {mainNavTab === 'terminal' && <TerminalManager />}
      {mainNavTab === 'future_sim' && <FutureNetworkSimulationHub />}
      {mainNavTab === 'storage_analysis' && <StorageAnalysisHub />}
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
      {mainNavTab === 'roi_triage' && <ROIImprovementsView roiStore={roiStore} setRoiStore={setRoiStore} />}

      <ModelDownloadSidebar />
    </div>
  )
}

export default App
