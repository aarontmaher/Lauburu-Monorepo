import React, { useState, useEffect, useRef, useMemo } from 'react';
import { ECOSYSTEM_CATEGORIES } from './TarjanSccAnalyzer.js';

export function GraphSidebarTree({
  nodes = [],
  selectedNode = null,
  onSelectNode = () => {},
  filterCategory = 'all',
  onSelectCategory = () => {},
  monetizationFilter = 'all',
  onSelectMonetization = () => {},
  searchTerm = '',
  onSearchChange = () => {}
}) {
  const [groupBy, setGroupBy] = useState('category'); // 'category' or 'layer'
  const [collapsedGroups, setCollapsedGroups] = useState({});
  const searchInputRef = useRef(null);

  // Global hotkey '/' to focus search input
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === '/' && document.activeElement !== searchInputRef.current) {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
      if (e.key === 'Escape' && document.activeElement === searchInputRef.current) {
        onSearchChange('');
        searchInputRef.current?.blur();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onSearchChange]);

  // Group nodes hierarchically
  const groupedNodes = useMemo(() => {
    const groups = {};

    nodes.forEach((node) => {
      // Filter check
      const matchesCat = filterCategory === 'all' || node.category === filterCategory ||
        (filterCategory === 'ai_mesh' && (node.category === 'ai_mesh' || node.category === 'governance'));
      
      let matchesMonetization = true;
      if (monetizationFilter === 'monetized') matchesMonetization = !!node.isMonetized;
      if (monetizationFilter === 'infrastructure') matchesMonetization = !node.isMonetized;

      const term = searchTerm.trim().toLowerCase();
      let matchesSearch = true;
      if (term) {
        matchesSearch = (
          node.label.toLowerCase().includes(term) ||
          node.id.toLowerCase().includes(term) ||
          node.layer.toLowerCase().includes(term) ||
          (node.shardedDevice && node.shardedDevice.toLowerCase().includes(term))
        );
      }

      if (!matchesCat || !matchesMonetization || !matchesSearch) return;

      const groupKey = groupBy === 'category' ? node.category : node.layer;
      if (!groups[groupKey]) {
        groups[groupKey] = [];
      }
      groups[groupKey].push(node);
    });

    return groups;
  }, [nodes, filterCategory, monetizationFilter, searchTerm, groupBy]);

  const toggleGroupCollapse = (key) => {
    setCollapsedGroups(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  const totalFilteredCount = Object.values(groupedNodes).reduce((sum, arr) => sum + arr.length, 0);

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
      {/* Search Header */}
      <div
        style={{
          padding: '12px 14px',
          borderBottom: '1px solid var(--border-subtle)',
          background: 'var(--bg-tertiary)',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '0.78rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>
            🌲 ARCHITECTURE EXPLORER
          </span>
          <span className="badge badge-cyan" style={{ fontSize: '0.65rem' }}>
            {totalFilteredCount} / {nodes.length}
          </span>
        </div>

        {/* Search Input */}
        <div
          style={{
            position: 'relative',
            display: 'flex',
            alignItems: 'center',
            background: 'var(--bg-primary)',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)',
            padding: '4px 8px'
          }}
        >
          <span style={{ fontSize: '0.75rem', marginRight: '6px', color: 'var(--text-muted)' }}>🔍</span>
          <input
            ref={searchInputRef}
            type="text"
            value={searchTerm}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search subsystems (Press '/' to focus)..."
            style={{
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: 'var(--text-primary)',
              fontSize: '0.75rem',
              fontFamily: 'var(--font-mono)',
              width: '100%'
            }}
          />
          {searchTerm && (
            <button
              onClick={() => onSearchChange('')}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                fontSize: '0.7rem'
              }}
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* 10 Category Filter Chips Bar */}
      <div
        style={{
          padding: '8px 12px',
          borderBottom: '1px solid var(--border-subtle)',
          background: 'var(--bg-secondary)',
          display: 'flex',
          flexDirection: 'column',
          gap: '6px'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.68rem', color: 'var(--text-muted)' }}>
          <span>CATEGORY FILTERS</span>
          <div style={{ display: 'flex', gap: '4px' }}>
            <button
              onClick={() => setGroupBy('category')}
              className="cyber-btn"
              style={{
                padding: '1px 5px',
                fontSize: '0.65rem',
                background: groupBy === 'category' ? 'var(--accent-cyan)' : 'transparent',
                color: groupBy === 'category' ? '#000' : 'var(--text-secondary)'
              }}
            >
              By Cat
            </button>
            <button
              onClick={() => setGroupBy('layer')}
              className="cyber-btn"
              style={{
                padding: '1px 5px',
                fontSize: '0.65rem',
                background: groupBy === 'layer' ? 'var(--accent-cyan)' : 'transparent',
                color: groupBy === 'layer' ? '#000' : 'var(--text-secondary)'
              }}
            >
              By Layer
            </button>
          </div>
        </div>

        {/* Category Scrollable Chips */}
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '4px',
            maxHeight: '110px',
            overflowY: 'auto'
          }}
        >
          {ECOSYSTEM_CATEGORIES.map((cat) => {
            const isSelected = filterCategory === cat.id;
            return (
              <button
                key={cat.id}
                onClick={() => onSelectCategory(cat.id)}
                className="cyber-btn"
                style={{
                  padding: '2px 6px',
                  fontSize: '0.68rem',
                  background: isSelected ? 'rgba(0, 255, 204, 0.18)' : 'transparent',
                  borderColor: isSelected ? 'var(--accent-cyan)' : 'var(--border-subtle)',
                  color: isSelected ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
              >
                <span>{cat.icon}</span>
                <span>{cat.label}</span>
              </button>
            );
          })}
        </div>

        {/* Monetization Filter Switcher */}
        <div style={{ display: 'flex', gap: '4px', marginTop: '2px' }}>
          <button
            onClick={() => onSelectMonetization('all')}
            className="cyber-btn"
            style={{
              flex: 1,
              padding: '2px 4px',
              fontSize: '0.65rem',
              background: monetizationFilter === 'all' ? 'var(--bg-tertiary)' : 'transparent',
              borderColor: monetizationFilter === 'all' ? 'var(--border-strong)' : 'transparent'
            }}
          >
            All
          </button>
          <button
            onClick={() => onSelectMonetization('monetized')}
            className="cyber-btn"
            style={{
              flex: 1,
              padding: '2px 4px',
              fontSize: '0.65rem',
              background: monetizationFilter === 'monetized' ? 'rgba(16, 185, 129, 0.2)' : 'transparent',
              borderColor: monetizationFilter === 'monetized' ? 'var(--accent-emerald)' : 'transparent',
              color: monetizationFilter === 'monetized' ? 'var(--accent-emerald)' : 'var(--text-secondary)'
            }}
          >
            💰 Revenue
          </button>
          <button
            onClick={() => onSelectMonetization('infrastructure')}
            className="cyber-btn"
            style={{
              flex: 1,
              padding: '2px 4px',
              fontSize: '0.65rem',
              background: monetizationFilter === 'infrastructure' ? 'rgba(148, 163, 184, 0.2)' : 'transparent',
              borderColor: monetizationFilter === 'infrastructure' ? 'var(--text-secondary)' : 'transparent',
              color: monetizationFilter === 'infrastructure' ? 'var(--text-primary)' : 'var(--text-secondary)'
            }}
          >
            🏗️ Infra
          </button>
        </div>
      </div>

      {/* Hierarchical Tree Body */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '10px 12px',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px'
        }}
      >
        {Object.keys(groupedNodes).length === 0 ? (
          <div style={{ textAlign: 'center', padding: '24px 8px', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
            No matching subsystems found.
          </div>
        ) : (
          Object.entries(groupedNodes).map(([groupKey, groupNodes]) => {
            const isCollapsed = collapsedGroups[groupKey];
            return (
              <div
                key={groupKey}
                style={{
                  background: 'var(--bg-secondary)',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)',
                  overflow: 'hidden'
                }}
              >
                {/* Group Header */}
                <div
                  onClick={() => toggleGroupCollapse(groupKey)}
                  style={{
                    padding: '6px 10px',
                    background: 'var(--bg-tertiary)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    cursor: 'pointer',
                    fontSize: '0.72rem',
                    fontFamily: 'var(--font-mono)',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    color: 'var(--text-secondary)'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                      {isCollapsed ? '▶' : '▼'}
                    </span>
                    <span>{groupKey}</span>
                  </div>
                  <span className="badge badge-cyan" style={{ fontSize: '0.6rem' }}>
                    {groupNodes.length}
                  </span>
                </div>

                {/* Subsystem Item Nodes */}
                {!isCollapsed && (
                  <div style={{ display: 'flex', flexDirection: 'column', padding: '4px 0' }}>
                    {groupNodes.map((node) => {
                      const isSelected = selectedNode?.id === node.id;
                      return (
                        <div
                          key={node.id}
                          onClick={() => onSelectNode(node)}
                          style={{
                            padding: '6px 12px',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            cursor: 'pointer',
                            background: isSelected ? 'rgba(0, 255, 204, 0.12)' : 'transparent',
                            borderLeft: isSelected ? '3px solid var(--accent-cyan)' : '3px solid transparent',
                            transition: 'background 0.15s ease'
                          }}
                        >
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', overflow: 'hidden' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <span style={{ fontSize: '0.75rem' }}>
                                {node.isMonetized ? '💰' : '🔹'}
                              </span>
                              <span
                                style={{
                                  fontSize: '0.74rem',
                                  fontWeight: isSelected ? 700 : 500,
                                  color: isSelected ? 'var(--accent-cyan)' : 'var(--text-primary)',
                                  whiteSpace: 'nowrap',
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis'
                                }}
                              >
                                {node.label.split(' (')[0]}
                              </span>
                            </div>
                            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                              {node.layer} • {node.shardedDevice?.split(' ')[0] || 'Cluster'}
                            </div>
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            {node.isMonetized && (
                              <span className="badge badge-emerald" style={{ fontSize: '0.58rem', padding: '1px 4px' }}>
                                $ REV
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

export default GraphSidebarTree;
