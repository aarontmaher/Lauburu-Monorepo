import React, { useState, useMemo, useRef } from 'react';
import { runTarjanScc, computeSugiyamaLayout, generateCurvedLinkPath } from './TarjanSccAnalyzer.js';

export function SugiyamaTopologyCanvas({
  nodes = [],
  links = [],
  selectedNode = null,
  onSelectNode = () => {},
  zoomLevel = 1.0,
  onZoomChange = () => {},
  filterCategory = 'all',
  monetizationFilter = 'all',
  searchTerm = '',
  onResetView = () => {}
}) {
  const [hoveredNode, setHoveredNode] = useState(null);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const svgRef = useRef(null);

  const canvasWidth = 880;
  const canvasHeight = 540;

  // Run Tarjan's SCC & Graph Topology analysis
  const {
    sccList,
    cycleNodeIds,
    cycleLinkKeys,
    bidirectionalLinks,
    nodeDegreeMap
  } = useMemo(() => {
    return runTarjanScc(nodes, links);
  }, [nodes, links]);

  // Compute Sugiyama hierarchical layout coordinates
  const nodePositions = useMemo(() => {
    return computeSugiyamaLayout(nodes, links, {
      width: canvasWidth,
      height: canvasHeight,
      paddingX: 70,
      paddingY: 55
    });
  }, [nodes, links]);

  // Filter matching status for nodes
  const nodeMatchMap = useMemo(() => {
    const map = new Map();
    const term = searchTerm.trim().toLowerCase();

    nodes.forEach(n => {
      let matchesCategory = filterCategory === 'all' || n.category === filterCategory;
      if (filterCategory === 'ai_mesh' && (n.category === 'ai_mesh' || n.category === 'governance')) {
        matchesCategory = true;
      }

      let matchesMonetization = true;
      if (monetizationFilter === 'monetized') matchesMonetization = !!n.isMonetized;
      if (monetizationFilter === 'infrastructure') matchesMonetization = !n.isMonetized;

      let matchesSearch = true;
      if (term) {
        matchesSearch = (
          n.label.toLowerCase().includes(term) ||
          n.id.toLowerCase().includes(term) ||
          n.layer.toLowerCase().includes(term) ||
          (n.shardedDevice && n.shardedDevice.toLowerCase().includes(term))
        );
      }

      map.set(n.id, matchesCategory && matchesMonetization && matchesSearch);
    });

    return map;
  }, [nodes, filterCategory, monetizationFilter, searchTerm]);

  // Active highlighted links and neighbors
  const activeFocus = hoveredNode || selectedNode;
  const focusNeighbors = useMemo(() => {
    if (!activeFocus) return new Set();
    const set = new Set([activeFocus.id]);
    links.forEach(l => {
      const s = typeof l.source === 'object' ? l.source.id : l.source;
      const t = typeof l.target === 'object' ? l.target.id : l.target;
      if (s === activeFocus.id) set.add(t);
      if (t === activeFocus.id) set.add(s);
    });
    return set;
  }, [activeFocus, links]);

  // Mouse pan event handlers
  const handleMouseDown = (e) => {
    if (e.target.tagName === 'svg' || e.target.id === 'canvas-bg') {
      setIsDragging(true);
      setDragStart({ x: e.clientX - panOffset.x, y: e.clientY - panOffset.y });
    }
  };

  const handleMouseMove = (e) => {
    if (isDragging) {
      setPanOffset({
        x: Math.round(e.clientX - dragStart.x),
        y: Math.round(e.clientY - dragStart.y)
      });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleWheel = (e) => {
    e.preventDefault();
    const delta = e.deltaY < 0 ? 0.05 : -0.05;
    const newZoom = Math.min(1.5, Math.max(0.7, zoomLevel + delta));
    onZoomChange(Math.round(newZoom * 100) / 100);
  };

  const handleResetPanZoom = () => {
    setPanOffset({ x: 0, y: 0 });
    onZoomChange(1.0);
    onResetView();
  };

  return (
    <div
      className="cyber-panel"
      style={{
        padding: 0,
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        minHeight: '560px',
        overflow: 'hidden',
        position: 'relative',
        userSelect: 'none'
      }}
    >
      {/* Top Toolbar */}
      <div
        style={{
          padding: '10px 16px',
          borderBottom: '1px solid var(--border-subtle)',
          background: 'var(--bg-tertiary)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '8px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '0.9rem', color: 'var(--accent-cyan)' }}>🌐</span>
          <span style={{ fontSize: '0.8rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
            SUGIYAMA DIRECTED TOPOLOGY GRAPH
          </span>
          <span className="badge badge-cyan" style={{ fontSize: '0.68rem' }}>
            {`${nodes.length} NODES`}
          </span>
          <span className="badge badge-purple" style={{ fontSize: '0.68rem' }}>
            {`${links.length} DIRECTED EDGES`}
          </span>
          {cycleNodeIds.size > 0 && (
            <span className="badge badge-rose" style={{ fontSize: '0.68rem', display: 'flex', alignItems: 'center', gap: '3px' }}>
              <span>↺</span> {cycleNodeIds.size} IN SCC CYCLE
            </span>
          )}
        </div>

        {/* Zoom & Reset Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Zoom:</span>
          <button
            onClick={() => onZoomChange(Math.max(0.7, Math.round((zoomLevel - 0.1) * 10) / 10))}
            className="cyber-btn"
            style={{ padding: '2px 8px', fontSize: '0.75rem' }}
            title="Zoom Out (-)"
          >
            -
          </button>
          <span
            style={{
              fontSize: '0.75rem',
              fontFamily: 'var(--font-mono)',
              color: 'var(--accent-cyan)',
              minWidth: '42px',
              textAlign: 'center'
            }}
          >
            {Math.round(zoomLevel * 100)}%
          </span>
          <button
            onClick={() => onZoomChange(Math.min(1.5, Math.round((zoomLevel + 0.1) * 10) / 10))}
            className="cyber-btn"
            style={{ padding: '2px 8px', fontSize: '0.75rem' }}
            title="Zoom In (+)"
          >
            +
          </button>
          <button
            onClick={handleResetPanZoom}
            className="cyber-btn"
            style={{ padding: '2px 8px', fontSize: '0.72rem' }}
            title="Reset Canvas View"
          >
            Reset
          </button>
        </div>
      </div>

      {/* Interactive SVG Canvas */}
      <div
        style={{
          flex: 1,
          background: 'radial-gradient(ellipse at center, rgba(16, 23, 38, 0.9) 0%, rgba(7, 11, 18, 1) 100%)',
          position: 'relative',
          overflow: 'hidden',
          cursor: isDragging ? 'grabbing' : 'grab'
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onWheel={handleWheel}
      >
        <svg
          ref={svgRef}
          id="canvas-bg"
          style={{
            width: '100%',
            height: '100%',
            position: 'absolute',
            top: 0,
            left: 0
          }}
          viewBox={`0 0 ${canvasWidth} ${canvasHeight}`}
          preserveAspectRatio="xMidYMid meet"
        >
          <defs>
            {/* Arrowhead Markers */}
            <marker
              id="marker-arrow-default"
              viewBox="0 0 10 10"
              refX="18"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#64748b" />
            </marker>

            <marker
              id="marker-arrow-cyan"
              viewBox="0 0 10 10"
              refX="18"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#00ffcc" />
            </marker>

            <marker
              id="marker-arrow-emerald"
              viewBox="0 0 10 10"
              refX="18"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#10b981" />
            </marker>

            <marker
              id="marker-arrow-cycle"
              viewBox="0 0 10 10"
              refX="18"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#c084fc" />
            </marker>

            {/* Glowing filters */}
            <filter id="glow-cyan" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>

            <filter id="glow-purple" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>

            {/* Grid Pattern */}
            <pattern id="grid-dots" width="28" height="28" patternUnits="userSpaceOnUse">
              <circle cx="14" cy="14" r="0.75" fill="#1e293b" />
            </pattern>
          </defs>

          {/* Background Grid Pattern */}
          <rect width="100%" height="100%" fill="url(#grid-dots)" style={{ pointerEvents: 'none' }} />

          {/* Layer Hierarchy Guide Lines */}
          <g opacity="0.35" style={{ pointerEvents: 'none' }}>
            <line x1="40" y1="55" x2={canvasWidth - 40} y2="55" stroke="#1e293b" strokeDasharray="4 4" />
            <text x="45" y="48" fill="#475569" fontSize="8" fontFamily="var(--font-mono)">RANK 0: ROOT CORE</text>

            <line x1="40" y1="140" x2={canvasWidth - 40} y2="140" stroke="#1e293b" strokeDasharray="4 4" />
            <text x="45" y="133" fill="#475569" fontSize="8" fontFamily="var(--font-mono)">RANK 1: L0 INFRA / L6 TOOLING</text>

            <line x1="40" y1="225" x2={canvasWidth - 40} y2="225" stroke="#1e293b" strokeDasharray="4 4" />
            <text x="45" y="218" fill="#475569" fontSize="8" fontFamily="var(--font-mono)">RANK 2: L5 GOVERNANCE / L1 APPS</text>

            <line x1="40" y1="310" x2={canvasWidth - 40} y2="310" stroke="#1e293b" strokeDasharray="4 4" />
            <text x="45" y="303" fill="#475569" fontSize="8" fontFamily="var(--font-mono)">RANK 3: L2 BIO / L3 INFERENCE / COMMERCE</text>

            <line x1="40" y1="395" x2={canvasWidth - 40} y2="395" stroke="#1e293b" strokeDasharray="4 4" />
            <text x="45" y="388" fill="#475569" fontSize="8" fontFamily="var(--font-mono)">RANK 4: L4 DATA LAKE & 24/7 LoRA</text>

            <line x1="40" y1="480" x2={canvasWidth - 40} y2="480" stroke="#1e293b" strokeDasharray="4 4" />
            <text x="45" y="473" fill="#475569" fontSize="8" fontFamily="var(--font-mono)">RANK 5: L7 OBSIDIAN KNOWLEDGE GRAPH</text>
          </g>

          {/* Transformed Group for Pan and Zoom */}
          <g transform={`translate(${panOffset.x}, ${panOffset.y}) scale(${zoomLevel})`} style={{ transformOrigin: 'center center', transition: isDragging ? 'none' : 'transform 0.15s ease-out' }}>
            {/* Directed Links */}
            {links.map((link, idx) => {
              const srcId = typeof link.source === 'object' ? link.source.id : link.source;
              const tgtId = typeof link.target === 'object' ? link.target.id : link.target;

              const srcPos = nodePositions.get(srcId);
              const tgtPos = nodePositions.get(tgtId);
              if (!srcPos || !tgtPos) return null;

              const srcNode = nodes.find(n => n.id === srcId);
              const tgtNode = nodes.find(n => n.id === tgtId);

              const linkKey = `${srcId}->${tgtId}`;
              const isBidi = bidirectionalLinks.has(linkKey);
              const isCycle = cycleLinkKeys.has(linkKey);
              const isFocus = activeFocus && (srcId === activeFocus.id || tgtId === activeFocus.id);

              const srcMatched = nodeMatchMap.get(srcId);
              const tgtMatched = nodeMatchMap.get(tgtId);
              const isDimmed = !srcMatched || !tgtMatched;

              // Path computation
              const pathD = generateCurvedLinkPath(srcPos.x, srcPos.y, tgtPos.x, tgtPos.y, isBidi, 0.22);

              // Colors & markers
              let strokeColor = '#475569';
              let markerEnd = 'url(#marker-arrow-default)';
              let strokeWidth = isFocus ? 2.8 : (link.value ? Math.min(3.5, link.value * 0.75) : 1.5);
              let strokeOpacity = isDimmed ? 0.15 : (isFocus ? 0.95 : 0.45);

              if (srcNode?.isMonetized || tgtNode?.isMonetized) {
                strokeColor = '#10b981';
                markerEnd = 'url(#marker-arrow-emerald)';
              }

              if (isCycle) {
                strokeColor = '#c084fc';
                markerEnd = 'url(#marker-arrow-cycle)';
                strokeWidth = Math.max(strokeWidth, 2.2);
              }

              if (isFocus) {
                strokeColor = '#00ffcc';
                markerEnd = 'url(#marker-arrow-cyan)';
              }

              // Midpoint for badges
              const midX = Math.round((srcPos.x + tgtPos.x) / 2);
              const midY = Math.round((srcPos.y + tgtPos.y) / 2);

              return (
                <g key={`link-${idx}`} opacity={strokeOpacity}>
                  <path
                    d={pathD}
                    fill="none"
                    stroke={strokeColor}
                    strokeWidth={strokeWidth}
                    strokeDasharray={isCycle ? '4 3' : (srcNode?.isMonetized ? '6 3' : 'none')}
                    markerEnd={markerEnd}
                  />

                  {/* Bidirectional flow indicator */}
                  {isBidi && !isDimmed && (
                    <g transform={`translate(${midX}, ${midY})`}>
                      <rect
                        x="-18"
                        y="-7"
                        width="36"
                        height="14"
                        rx="3"
                        fill="rgba(11, 17, 28, 0.92)"
                        stroke={isFocus ? 'var(--accent-cyan)' : 'var(--border-strong)'}
                        strokeWidth="1"
                      />
                      <text
                        x="0"
                        y="3"
                        fill={isFocus ? 'var(--accent-cyan)' : '#94a3b8'}
                        fontSize="7.5"
                        fontWeight="bold"
                        fontFamily="var(--font-mono)"
                        textAnchor="middle"
                      >
                        ⇄ BIDI
                      </text>
                    </g>
                  )}
                </g>
              );
            })}

            {/* Nodes */}
            {nodes.map((node) => {
              const pos = nodePositions.get(node.id);
              if (!pos) return null;

              const isSelected = selectedNode?.id === node.id;
              const isHovered = hoveredNode?.id === node.id;
              const isFocused = isSelected || isHovered;
              const isMatched = nodeMatchMap.get(node.id);
              const isNeighbor = focusNeighbors.has(node.id);
              const inCycle = cycleNodeIds.has(node.id);

              const degrees = nodeDegreeMap.get(node.id) || { inDegree: 0, outDegree: 0 };
              const radius = node.size ? Math.max(16, node.size * 0.95) : 18;

              const opacity = isMatched ? (activeFocus ? (isNeighbor ? 1.0 : 0.3) : 1.0) : 0.15;

              return (
                <g
                  key={node.id}
                  transform={`translate(${pos.x}, ${pos.y})`}
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectNode(node);
                  }}
                  onMouseEnter={() => setHoveredNode(node)}
                  onMouseLeave={() => setHoveredNode(null)}
                  style={{ cursor: 'pointer' }}
                  opacity={opacity}
                >
                  {/* Outer Glowing Ring on Focus */}
                  {isFocused && (
                    <circle
                      cx="0"
                      cy="0"
                      r={radius + 7}
                      fill="none"
                      stroke={inCycle ? 'var(--accent-purple)' : 'var(--accent-cyan)'}
                      strokeWidth="2"
                      strokeDasharray="4 2"
                      filter={inCycle ? 'url(#glow-purple)' : 'url(#glow-cyan)'}
                    />
                  )}

                  {/* Monetization Commercial Dashed Ring */}
                  {node.isMonetized && (
                    <circle
                      cx="0"
                      cy="0"
                      r={radius + 4}
                      fill="none"
                      stroke="#10b981"
                      strokeWidth="1.5"
                      strokeDasharray="3 3"
                    />
                  )}

                  {/* Main Node Circle */}
                  <circle
                    cx="0"
                    cy="0"
                    r={radius}
                    fill={node.isMonetized ? '#064e3b' : (inCycle ? '#2e1065' : '#0f172a')}
                    stroke={isSelected ? 'var(--accent-cyan)' : (node.color || '#38bdf8')}
                    strokeWidth={isSelected ? 3 : 2}
                  />

                  {/* Node Icon / Symbol */}
                  <text
                    x="0"
                    y="4"
                    fill="#f8fafc"
                    fontSize="11"
                    textAnchor="middle"
                    style={{ pointerEvents: 'none' }}
                  >
                    {node.category === 'apps' ? '📱' :
                     node.category === 'biometrics' ? '💓' :
                     node.category === 'ai_mesh' ? '🤖' :
                     node.category === 'storage' ? '💾' :
                     node.category === 'governance' ? '⚖️' :
                     node.category === 'commerce' ? '💰' :
                     node.category === 'docs' ? '🧠' :
                     node.category === 'tooling' ? '🛠️' :
                     node.category === 'infrastructure' ? '🏗️' : '🏛️'}
                  </text>

                  {/* Tarjan SCC Cycle Badge */}
                  {inCycle && (
                    <g transform={`translate(${radius - 4}, ${-radius + 4})`}>
                      <circle cx="0" cy="0" r="7" fill="#7e22ce" stroke="#c084fc" strokeWidth="1" />
                      <text
                        x="0"
                        y="2.5"
                        fill="#fff"
                        fontSize="7"
                        fontWeight="bold"
                        fontFamily="var(--font-mono)"
                        textAnchor="middle"
                      >
                        ↺
                      </text>
                    </g>
                  )}

                  {/* Primary Node Label */}
                  <text
                    x="0"
                    y={radius + 13}
                    fill={isSelected ? 'var(--accent-cyan)' : '#e2e8f0'}
                    fontSize="9.5"
                    fontWeight={isSelected ? '700' : '600'}
                    fontFamily="var(--font-mono)"
                    textAnchor="middle"
                    style={{ pointerEvents: 'none' }}
                  >
                    {node.label.split(' (')[0]}
                  </text>

                  {/* Subtitle / Device Badge */}
                  <text
                    x="0"
                    y={radius + 23}
                    fill="#94a3b8"
                    fontSize="7.5"
                    fontFamily="var(--font-mono)"
                    textAnchor="middle"
                    style={{ pointerEvents: 'none' }}
                  >
                    {node.layer} • {node.shardedDevice?.split(' ')[0] || 'Shard'}
                  </text>
                </g>
              );
            })}
          </g>
        </svg>

        {/* Legend Overlay (Bottom-Left) */}
        <div
          style={{
            position: 'absolute',
            bottom: '12px',
            left: '12px',
            background: 'rgba(10, 15, 28, 0.92)',
            backdropFilter: 'blur(8px)',
            padding: '8px 12px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)',
            fontSize: '0.68rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '5px',
            pointerEvents: 'none'
          }}
        >
          <div style={{ fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', marginBottom: '2px' }}>
            TOPOLOGY LEGEND
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981', border: '1px dashed #34d399' }} />
            <span style={{ color: 'var(--accent-emerald)' }}>Commercial / Revenue-Generating Pipeline</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#7e22ce', border: '1px solid #c084fc' }} />
            <span style={{ color: 'var(--accent-purple)' }}>↺ Tarjan SCC Cycle (AI Feedback Loop)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--accent-cyan)' }}>⇄</span>
            <span style={{ color: 'var(--text-secondary)' }}>Bidirectional Data Flow Vector</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#1e293b', border: '1px solid #475569' }} />
            <span style={{ color: 'var(--text-muted)' }}>Internal Monorepo Infrastructure</span>
          </div>
        </div>

        {/* Floating Quick Info (Bottom-Right) */}
        {hoveredNode && (
          <div
            style={{
              position: 'absolute',
              bottom: '12px',
              right: '12px',
              background: 'rgba(11, 17, 28, 0.95)',
              backdropFilter: 'blur(10px)',
              padding: '10px 14px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--accent-cyan)',
              fontSize: '0.72rem',
              fontFamily: 'var(--font-mono)',
              display: 'flex',
              flexDirection: 'column',
              gap: '4px',
              pointerEvents: 'none',
              maxWidth: '280px'
            }}
          >
            <div style={{ color: 'var(--accent-cyan)', fontWeight: 700, fontSize: '0.8rem' }}>
              {hoveredNode.label}
            </div>
            <div style={{ color: 'var(--text-secondary)' }}>
              Layer: <span style={{ color: '#fff' }}>{hoveredNode.layer}</span> | Cat: <span style={{ color: '#fff' }}>{hoveredNode.category}</span>
            </div>
            <div style={{ color: 'var(--text-secondary)' }}>
              Device: <span style={{ color: 'var(--accent-amber)' }}>{hoveredNode.shardedDevice}</span>
            </div>
            <div style={{ color: hoveredNode.isMonetized ? 'var(--accent-emerald)' : 'var(--text-muted)' }}>
              {hoveredNode.isMonetized ? '● Commercial Pipeline ($)' : '○ Internal Infrastructure'}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default SugiyamaTopologyCanvas;
