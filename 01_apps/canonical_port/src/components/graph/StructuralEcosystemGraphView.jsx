import React, { useState } from 'react';
import { INITIAL_MONOREPO_GRAPH_NODES, INITIAL_MONOREPO_GRAPH_LINKS } from '../../services/mockFallbackData.js';
import { SugiyamaTopologyCanvas } from './SugiyamaTopologyCanvas.jsx';
import { GraphSidebarTree } from './GraphSidebarTree.jsx';
import { SubsystemNodeInspector } from './SubsystemNodeInspector.jsx';

export function StructuralEcosystemGraphView({ onDispatchAction = () => {} }) {
  const [nodes] = useState(INITIAL_MONOREPO_GRAPH_NODES);
  const [links] = useState(INITIAL_MONOREPO_GRAPH_LINKS);
  const [filterCategory, setFilterCategory] = useState('all');
  const [monetizationFilter, setMonetizationFilter] = useState('all');
  const [selectedNode, setSelectedNode] = useState(INITIAL_MONOREPO_GRAPH_NODES[0]);
  const [searchTerm, setSearchTerm] = useState('');
  const [zoomLevel, setZoomLevel] = useState(1.0);

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
              Directed Sugiyama topology with Tarjan SCC cycle detection, 10 categories, and 7-node hardware sharding.
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="badge badge-cyan">14 FEDERATED NODES</span>
          <span className="badge badge-emerald">17 DIRECTED EDGES</span>
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
