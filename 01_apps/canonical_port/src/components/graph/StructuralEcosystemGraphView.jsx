import React, { useState, useEffect } from 'react';
import { INITIAL_MONOREPO_GRAPH_NODES, INITIAL_MONOREPO_GRAPH_LINKS } from '../../services/mockFallbackData.js';
import { SugiyamaTopologyCanvas } from './SugiyamaTopologyCanvas.jsx';
import { GraphSidebarTree } from './GraphSidebarTree.jsx';
import { SubsystemNodeInspector } from './SubsystemNodeInspector.jsx';

const CATEGORY_COLORS = {
  core: '#8b5cf6',
  infrastructure: '#06b6d4',
  apps: '#10b981',
  ai_mesh: '#ec4899',
  biometrics: '#f59e0b',
  storage: '#3b82f6',
  governance: '#a855f7',
  tooling: '#14b8a6',
  docs: '#6366f1',
  commerce: '#22c55e',
  tui: '#eab308',
  hardware: '#f43f5e',
  mesh: '#0ea5e9'
};

export function StructuralEcosystemGraphView({ onDispatchAction = () => {} }) {
  const [nodes, setNodes] = useState(INITIAL_MONOREPO_GRAPH_NODES);
  const [links, setLinks] = useState(INITIAL_MONOREPO_GRAPH_LINKS);
  const [filterCategory, setFilterCategory] = useState('all');
  const [monetizationFilter, setMonetizationFilter] = useState('all');
  const [selectedNode, setSelectedNode] = useState(INITIAL_MONOREPO_GRAPH_NODES[0]);
  const [searchTerm, setSearchTerm] = useState('');
  const [zoomLevel, setZoomLevel] = useState(1.0);
  const [isLiveNeo, setIsLiveNeo] = useState(false);
  const [syncStatus, setSyncStatus] = useState('');

  useEffect(() => {
    fetch('/api/v1/neo/graph')
      .then(r => r.json())
      .then(data => {
        if (data && data.nodes && data.nodes.length > 0) {
          const mappedNodes = data.nodes.map(n => ({
            id: n.id,
            label: n.label,
            category: n.category || 'core',
            layer: n.category ? n.category.toUpperCase() : 'L0',
            isMonetized: ['apps', 'commerce', 'biometrics'].includes(n.category),
            revenueStatus: ['apps', 'commerce', 'biometrics'].includes(n.category) ? 'revenue_generating' : 'internal',
            shardedDevice: n.engine || 'Mac_Node (L1)',
            color: CATEGORY_COLORS[n.category] || '#8b5cf6',
            size: n.id === 'monorepo_root' ? 28 : (n.category === 'ai_mesh' || n.category === 'hardware' ? 24 : 20),
            status: n.status || 'ONLINE',
            details: n.details || ''
          }));
          const mappedLinks = (data.edges || []).map(e => ({
            source: e.source,
            target: e.target,
            value: e.bandwidth ? 5 : 3,
            protocol: e.protocol
          }));
          setNodes(mappedNodes);
          setLinks(mappedLinks);
          setSelectedNode(mappedNodes[0]);
          setIsLiveNeo(true);
        }
      })
      .catch(err => console.debug('Neo graph fetch fallback to initial:', err));
  }, []);

  const handleSyncObsidian = async () => {
    setSyncStatus('Syncing...');
    try {
      const res = await fetch('/api/v1/neo/sync-obsidian', { method: 'POST' });
      const data = await res.json();
      setSyncStatus(`Synced: ${data.nodes_synced} nodes`);
      setTimeout(() => setSyncStatus(''), 4000);
    } catch (e) {
      setSyncStatus('Sync error');
      setTimeout(() => setSyncStatus(''), 3000);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {/* Top Banner */}
      <div
        className="cyber-panel"
        style={{
          padding: '14px 18px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '1.5rem' }}>🌐</span>
          <div>
            <h1 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, color: 'var(--accent-cyan)', letterSpacing: '0.02em' }}>
              The Obsidian View: 3D Structural Ecosystem Graph (F27)
            </h1>
            <p style={{ margin: '3px 0 0', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              Neo Monorepo Knowledge Graph: {nodes.length} nodes, {links.length} directed edges, 167,976 files indexed across 8 canonical domains.
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className={`badge ${isLiveNeo ? 'badge-emerald' : 'badge-cyan'}`}>
            {nodes.length} {isLiveNeo ? 'LIVE NEO NODES' : 'FEDERATED NODES'}
          </span>
          <span className="badge badge-emerald">{links.length} DIRECTED EDGES</span>
          <button
            onClick={handleSyncObsidian}
            className="cyber-btn cyber-btn-cyan"
            style={{ fontSize: '0.72rem', padding: '4px 10px' }}
          >
            🧠 {syncStatus || 'Sync Obsidian'}
          </button>
          <button
            onClick={() => onDispatchAction('/audit')}
            className="cyber-btn cyber-btn-cyan"
            style={{ fontSize: '0.72rem', padding: '4px 10px' }}
          >
            ⚡ Swarm Audit
          </button>
        </div>
      </div>

      {/* 3-Pane High Visual Density Split Layout */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(260px, 25%) minmax(420px, 50%) minmax(280px, 25%)',
          gap: '14px',
          height: 'calc(100vh - 220px)',
          minHeight: '620px'
        }}
      >
        {/* Left Pane (25%): Architecture Tree & Category Filters */}
        <GraphSidebarTree
          nodes={nodes}
          selectedNode={selectedNode}
          onSelectNode={setSelectedNode}
          filterCategory={filterCategory}
          onSelectCategory={setFilterCategory}
          monetizationFilter={monetizationFilter}
          onSelectMonetization={setMonetizationFilter}
          searchTerm={searchTerm}
          onSearchChange={setSearchTerm}
        />

        {/* Center Canvas (50%): Sugiyama Directed Graph */}
        <SugiyamaTopologyCanvas
          nodes={nodes}
          links={links}
          selectedNode={selectedNode}
          onSelectNode={setSelectedNode}
          zoomLevel={zoomLevel}
          onZoomChange={setZoomLevel}
          filterCategory={filterCategory}
          monetizationFilter={monetizationFilter}
          searchTerm={searchTerm}
          onResetView={() => {
            setFilterCategory('all');
            setMonetizationFilter('all');
            setSearchTerm('');
            setZoomLevel(1.0);
          }}
        />

        {/* Right Pane (25%): Subsystem Node Inspector */}
        <SubsystemNodeInspector
          selectedNode={selectedNode}
          allNodes={nodes}
          allLinks={links}
          onSelectNode={setSelectedNode}
          onDispatchAction={onDispatchAction}
        />
      </div>
    </div>
  );
}

export default StructuralEcosystemGraphView;
