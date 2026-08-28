import React, { useState } from 'react';
import TerminalManager from './TerminalManager';
import AITrainingHub from './AITrainingHub';
import ROIImprovementsView from './ROIImprovementsView';
import Spatial3DMapView from './Spatial3DMapView';
import StorageAnalysisHub from './StorageAnalysisHub';
import FutureNetworkSimulationHub from './FutureNetworkSimulationHub';
import TriOrchestratorLiveChatView from './TriOrchestratorLiveChatView';
import PySparkMeshControlCenterView from './PySparkMeshControlCenterView';
import GrapplingVisionBiometricsView from './GrapplingVisionBiometricsView';
import LiveTrainingDataHarvesterView from './LiveTrainingDataHarvesterView';
import SpatialGrapplingMapEditorView from './SpatialGrapplingMapEditorView';
import UnifiedGenieTatamiArenaView from './UnifiedGenieTatamiArenaView';

export default function AdminPortalView({ telemetry, onOpenSimulator }) {
  const [adminTab, setAdminTab] = useState('pyspark_crons'); // 'pyspark_crons', 'spatial_editor', 'harvesters', 'grappling_vision', 'terminal', 'live_chat', 'spatial_radar', 'ai_training', 'future_sim', 'storage', 'roi_triage'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem', padding: '1rem', width: '100%' }}>
      
      {/* ADMIN CONTROL HEADER */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(15,23,42,0.98), rgba(20,28,48,0.95))',
        border: '1px solid rgba(239,68,68,0.4)',
        borderRadius: '16px',
        padding: '1rem 1.5rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '1rem',
        boxShadow: '0 8px 30px rgba(239,68,68,0.2)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem' }}>
          <span style={{ fontSize: '1.6rem' }}>🔐</span>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <h2 style={{ margin: 0, color: '#f8fafc', fontSize: '1.2rem', fontWeight: 'bold' }}>
                Monorepo Admin Command Center
              </h2>
              <span style={{ background: '#ef4444', color: '#fff', fontSize: '0.65rem', fontWeight: 'bold', padding: '2px 8px', borderRadius: '10px' }}>
                ADMIN ONLY
              </span>
            </div>
            <p style={{ margin: '0.2rem 0 0 0', color: '#94a3b8', fontSize: '0.74rem' }}>
              5-Layer Distributed Hardware Mesh • NPU-First Power States • PySpark Crons • 24/7 LoRA Sinks
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center' }}>
          {onOpenSimulator && (
            <button
              onClick={onOpenSimulator}
              style={{
                background: 'rgba(56,189,248,0.15)',
                border: '1px solid #38bdf8',
                color: '#38bdf8',
                padding: '6px 12px',
                borderRadius: '8px',
                fontWeight: 'bold',
                fontSize: '0.78rem',
                cursor: 'pointer'
              }}
            >
              📱 Multi-Device Simulator Testbench
            </button>
          )}
          <span style={{ fontSize: '0.72rem', color: '#10b981', background: 'rgba(16,185,129,0.15)', padding: '4px 10px', borderRadius: '12px', fontWeight: 'bold' }}>
            ● Mesh Sockets Healthy
          </span>
        </div>
      </div>

      {/* ADMIN NAVIGATION TABS */}
      <nav style={{
        display: 'flex',
        gap: '0.35rem',
        overflowX: 'auto',
        whiteSpace: 'nowrap',
        padding: '0.2rem 0',
        scrollbarWidth: 'none'
      }}>
        {[
          { id: 'pyspark_crons', label: '⚡ PySpark Mesh & Crons (:8750)', color: '#38bdf8', activeBg: 'linear-gradient(135deg, #0284c7, #38bdf8)' },
          { id: 'spatial_editor', label: '🥋 3D Spatial Map & Live Editor', color: '#10b981', activeBg: 'linear-gradient(135deg, #065f46, #10b981)' },
          { id: 'harvesters', label: '📡 Live Real-Data Harvesters', color: '#38bdf8', activeBg: 'linear-gradient(135deg, #0284c7, #38bdf8)' },
          { id: 'grappling_vision', label: '🥋 Grappling Vision & NPU (1.2W)', color: '#10b981', activeBg: 'linear-gradient(135deg, #047857, #10b981)' },
          { id: 'terminal', label: '💻 Whole-Network Terminal', color: '#3b82f6', activeBg: 'linear-gradient(135deg, #1e3a8a, #3b82f6)' },
          { id: 'live_chat', label: '💬 Tri-Orchestrator Live Chat', color: '#8b5cf6', activeBg: 'linear-gradient(135deg, #1e3a8a, #8b5cf6)' },
          { id: 'spatial_radar', label: '🛰️ 3D Spatial Radar', color: '#10b981', activeBg: 'linear-gradient(135deg, #064e3b, #10b981)' },
          { id: 'ai_training', label: '🧠 24/7 AI Training & LoRA Hub', color: '#c084fc', activeBg: 'linear-gradient(135deg, #581c87, #8b5cf6)' },
          { id: 'future_sim', label: '🧬 Genetic MoE Simulator', color: '#7c3aed', activeBg: 'linear-gradient(135deg, #4c1d95, #7c3aed)' },
          { id: 'storage', label: '💾 Storage Deep Analysis', color: '#14b8a6', activeBg: 'linear-gradient(135deg, #0f766e, #14b8a6)' },
          { id: 'roi_triage', label: '🛠️ ROI Improvements Triage', color: '#eab308', activeBg: 'linear-gradient(135deg, #713f12, #eab308)' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setAdminTab(tab.id)}
            style={{
              flexShrink: 0,
              background: adminTab === tab.id ? tab.activeBg : '#111827',
              border: adminTab === tab.id ? `1px solid ${tab.color}` : '1px solid rgba(255,255,255,0.08)',
              color: '#fff',
              padding: '0.45rem 0.9rem',
              borderRadius: '20px',
              cursor: 'pointer',
              fontWeight: adminTab === tab.id ? 'bold' : '500',
              fontSize: '0.78rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
              boxShadow: adminTab === tab.id ? `0 2px 10px ${tab.color}40` : 'none',
              transition: 'all 0.2s ease'
            }}
          >
            <span>{tab.label}</span>
          </button>
        ))}
      </nav>

      {/* ADMIN ACTIVE VIEW CONTENT */}
      {adminTab === 'pyspark_crons' && <PySparkMeshControlCenterView />}
      {adminTab === 'spatial_editor' && <SpatialGrapplingMapEditorView />}
      {adminTab === 'harvesters' && <LiveTrainingDataHarvesterView />}
      {adminTab === 'grappling_vision' && <GrapplingVisionBiometricsView />}
      {adminTab === 'terminal' && <TerminalManager />}
      {adminTab === 'live_chat' && <TriOrchestratorLiveChatView />}
      {adminTab === 'spatial_radar' && <Spatial3DMapView />}
      {adminTab === 'ai_training' && <AITrainingHub />}
      {adminTab === 'future_sim' && <FutureNetworkSimulationHub />}
      {adminTab === 'storage' && <StorageAnalysisHub />}
      {adminTab === 'roi_triage' && <ROIImprovementsView />}

    </div>
  );
}
