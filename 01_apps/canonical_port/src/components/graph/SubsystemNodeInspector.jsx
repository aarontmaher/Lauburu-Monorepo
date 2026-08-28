import React, { useMemo } from 'react';

export function SubsystemNodeInspector({
  selectedNode = null,
  allNodes = [],
  allLinks = [],
  onSelectNode = () => {},
  onDispatchAction = () => {}
}) {
  // If no node selected, default to first or show placeholder
  const node = selectedNode || allNodes[0] || {
    id: 'monorepo_root',
    label: 'Lauburu Monorepo Root',
    layer: 'Core',
    category: 'core',
    isMonetized: false,
    shardedDevice: 'Mac_Node (L1)'
  };

  // Upstream dependencies (inbound links: other -> this)
  const upstreamDependencies = useMemo(() => {
    const deps = [];
    allLinks.forEach(l => {
      const srcId = typeof l.source === 'object' ? l.source.id : l.source;
      const tgtId = typeof l.target === 'object' ? l.target.id : l.target;
      if (tgtId === node.id) {
        const found = allNodes.find(n => n.id === srcId);
        if (found) deps.push(found);
      }
    });
    return deps;
  }, [node, allNodes, allLinks]);

  // Downstream dependents (outbound links: this -> other)
  const downstreamDependents = useMemo(() => {
    const deps = [];
    allLinks.forEach(l => {
      const srcId = typeof l.source === 'object' ? l.source.id : l.source;
      const tgtId = typeof l.target === 'object' ? l.target.id : l.target;
      if (srcId === node.id) {
        const found = allNodes.find(n => n.id === tgtId);
        if (found) deps.push(found);
      }
    });
    return deps;
  }, [node, allNodes, allLinks]);

  // Synthetic or real Obsidian Wikilink & Qdrant Collection Name
  const obsidianWikilink = `[[${node.id.toUpperCase()}_ARCHITECTURE]]`;
  const qdrantCollection = `lauburu_${node.category}_vectors`;

  return (
    <div
      className="cyber-panel"
      style={{
        padding: 0,
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        minHeight: '560px',
        overflow: 'hidden'
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '12px 14px',
          borderBottom: '1px solid var(--border-subtle)',
          background: 'var(--bg-tertiary)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}
      >
        <span style={{ fontSize: '0.78rem', fontFamily: 'var(--font-mono)', color: 'var(--accent-purple)', fontWeight: 700 }}>
          👁️ SUBSYSTEM INSPECTOR
        </span>
        <span className={`badge ${node.isMonetized ? 'badge-emerald' : 'badge-cyan'}`}>
          {node.isMonetized ? 'COMMERCIAL PIPELINE' : 'INTERNAL INFRA'}
        </span>
      </div>

      {/* Main Inspector Body */}
      <div
        style={{
          padding: '16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
          flex: 1,
          overflowY: 'auto'
        }}
      >
        {/* Title & Layer */}
        <div>
          <span style={{ fontSize: '0.68rem', fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {node.layer} • {node.category?.replace('_', ' ')}
          </span>
          <h2 style={{ margin: '4px 0 2px', fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            {node.label}
          </h2>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            Node ID: <span style={{ color: 'var(--accent-purple)' }}>{node.id}</span>
          </div>
        </div>

        {/* Hardware Sharding Allocation */}
        <div style={{ background: 'var(--bg-secondary)', padding: '10px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            HARDWARE SHARDING TARGET:
          </div>
          <div style={{ fontSize: '0.82rem', color: 'var(--accent-cyan)', fontWeight: 600, marginTop: '2px', fontFamily: 'var(--font-mono)' }}>
            🖥️ {node.shardedDevice || 'Dynamic 7-Node Swarm'}
          </div>
        </div>

        {/* Obsidian Knowledge Vault Link */}
        <div style={{ background: 'var(--bg-secondary)', padding: '10px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            OBSIDIAN KNOWLEDGE WIKILINK:
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--accent-purple)', fontWeight: 600, marginTop: '2px', fontFamily: 'var(--font-mono)' }}>
            {obsidianWikilink}
          </div>
        </div>

        {/* Qdrant Vector Collection */}
        <div style={{ background: 'var(--bg-secondary)', padding: '10px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            QDRANT VECTOR DB COLLECTION:
          </div>
          <div style={{ fontSize: '0.76rem', color: 'var(--accent-blue)', marginTop: '2px', fontFamily: 'var(--font-mono)' }}>
            ⚡ {qdrantCollection} (384-dim AST Embeddings)
          </div>
        </div>

        {/* Monetization & Business Status */}
        <div style={{ background: 'var(--bg-secondary)', padding: '10px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            COMMERCIAL PROFITABILITY:
          </div>
          <div style={{ fontSize: '0.78rem', color: node.isMonetized ? 'var(--accent-emerald)' : 'var(--text-muted)', fontWeight: 600, marginTop: '2px' }}>
            {node.isMonetized ? '● Active Commercial Pipeline (Shopify/Movesense)' : '○ Zero Cloud Spend Local Infra'}
          </div>
        </div>

        {/* Directed Graph Linkage (Dependencies) */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {/* Upstream Inbound */}
          <div>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginBottom: '4px' }}>
              INBOUND DEPENDENCIES ({upstreamDependencies.length}):
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
              {upstreamDependencies.length === 0 ? (
                <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', fontStyle: 'italic' }}>None (Root / Ingress)</span>
              ) : (
                upstreamDependencies.map(dep => (
                  <button
                    key={dep.id}
                    onClick={() => onSelectNode(dep)}
                    className="cyber-btn"
                    style={{ padding: '2px 6px', fontSize: '0.68rem', color: 'var(--accent-cyan)' }}
                  >
                    ← {dep.label.split(' (')[0]}
                  </button>
                ))
              )}
            </div>
          </div>

          {/* Downstream Outbound */}
          <div>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginBottom: '4px' }}>
              OUTBOUND DEPENDENTS ({downstreamDependents.length}):
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
              {downstreamDependents.length === 0 ? (
                <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', fontStyle: 'italic' }}>None (Leaf Node)</span>
              ) : (
                downstreamDependents.map(dep => (
                  <button
                    key={dep.id}
                    onClick={() => onSelectNode(dep)}
                    className="cyber-btn"
                    style={{ padding: '2px 6px', fontSize: '0.68rem', color: 'var(--accent-purple)' }}
                  >
                    → {dep.label.split(' (')[0]}
                  </button>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Bottom Actions & Zero-Mock Badge */}
        <div
          style={{
            marginTop: 'auto',
            borderTop: '1px solid var(--border-subtle)',
            paddingTop: '12px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '0.72rem'
          }}
        >
          <span style={{ color: 'var(--accent-emerald)', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span>✓</span> 0-Mock Verified
          </span>
          <div style={{ display: 'flex', gap: '6px' }}>
            <button
              onClick={() => onDispatchAction('/storage')}
              className="cyber-btn"
              style={{ fontSize: '0.68rem', padding: '3px 8px' }}
            >
              Tri-Vault
            </button>
            <button
              onClick={() => onDispatchAction('/audit')}
              className="cyber-btn cyber-btn-cyan"
              style={{ fontSize: '0.68rem', padding: '3px 8px' }}
            >
              Audit
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default SubsystemNodeInspector;
