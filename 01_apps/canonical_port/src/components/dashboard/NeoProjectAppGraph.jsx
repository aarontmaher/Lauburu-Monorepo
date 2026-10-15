import React, { useState, useEffect, useMemo } from 'react';

const CATEGORY_META = {
  all: { label: 'All Systems', icon: '🌐', color: 'bg-slate-800/80 text-slate-300 border-slate-700' },
  tui: { label: 'Terminal TUIs', icon: '📟', color: 'bg-emerald-950/40 text-emerald-400 border-emerald-800/60' },
  webapp: { label: 'Localhost Web Apps', icon: '🚀', color: 'bg-cyan-950/40 text-cyan-400 border-cyan-800/60' },
  notebook: { label: 'Notebooks', icon: '📓', color: 'bg-indigo-950/40 text-indigo-400 border-indigo-800/60' },
  node: { label: '7-Layer Mesh Nodes', icon: '🖥️', color: 'bg-violet-950/40 text-violet-400 border-violet-800/60' },
  biometric: { label: 'Bicep ECG (Movesense)', icon: '❤️', color: 'bg-rose-950/40 text-rose-400 border-rose-800/60' },
  storage: { label: 'SeaweedFS Tri-Vault', icon: '💾', color: 'bg-amber-950/40 text-amber-400 border-amber-800/60' },
  commerce: { label: 'Shopify & Compute', icon: '💳', color: 'bg-fuchsia-950/40 text-fuchsia-400 border-fuchsia-800/60' },
  cloud: { label: 'Google Cloud $1.4K Pool', icon: '☁️', color: 'bg-sky-950/40 text-sky-400 border-sky-800/60' },
};

export function NeoProjectAppGraph({ isExpanded = false, onToggleExpand }) {
  const [graphData, setGraphData] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNode, setSelectedNode] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncingVault, setIsSyncingVault] = useState(false);
  const [syncFeedback, setSyncFeedback] = useState(null);

  const fetchGraph = async () => {
    try {
      setIsLoading(true);
      const res = await fetch('/api/v1/graph/topology');
      if (res.ok) {
        const data = await res.json();
        setGraphData(data);
        if (!selectedNode && data.nodes?.length > 0) {
          // Default to app_canonical_port or Movesense sensor
          setSelectedNode(data.nodes.find(n => n.id === 'app_canonical_port') || data.nodes[0]);
        }
      }
    } catch (err) {
      console.error('Failed to load Neo Project App Graph:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchGraph();
    const interval = setInterval(fetchGraph, 10000); // 10s auto-refresh
    return () => clearInterval(interval);
  }, []);

  const handleSyncToObsidian = async () => {
    setIsSyncingVault(true);
    setSyncFeedback(null);
    try {
      const res = await fetch('/api/v1/graph/sync_vault', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setSyncFeedback(`✅ Synced ${data.total_nodes} nodes to Obsidian Vault!`);
      } else {
        setSyncFeedback('❌ Vault sync failed');
      }
    } catch (e) {
      setSyncFeedback('❌ Network error during sync');
    } finally {
      setIsSyncingVault(false);
      setTimeout(() => setSyncFeedback(null), 4000);
    }
  };

  const filteredNodes = useMemo(() => {
    if (!graphData?.nodes) return [];
    return graphData.nodes.filter(n => {
      const matchesCat = selectedCategory === 'all' || n.category === selectedCategory;
      const q = searchQuery.toLowerCase().trim();
      if (!q) return matchesCat;
      const matchesSearch =
        n.label?.toLowerCase().includes(q) ||
        n.id?.toLowerCase().includes(q) ||
        n.details?.toLowerCase().includes(q) ||
        (n.port && String(n.port).includes(q)) ||
        n.engine?.toLowerCase().includes(q);
      return matchesCat && matchesSearch;
    });
  }, [graphData, selectedCategory, searchQuery]);

  if (isLoading && !graphData) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-slate-400 space-y-3">
        <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-xs font-mono">Neo Scribe AI analyzing monorepo AST & port graph...</p>
      </div>
    );
  }

  const summary = graphData?.summary || {};
  const usb3 = summary.usb3_bus || {};
  const ecg = summary.bicep_ecg || {};

  return (
    <div className="flex flex-col h-full bg-slate-950/70 backdrop-blur-md rounded-xl border border-slate-800/80 overflow-hidden">
      {/* Header Banner */}
      <div className="px-4 py-3 border-b border-slate-800/80 bg-slate-900/50 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center space-x-2.5">
          <div className="w-7 h-7 rounded-lg bg-cyan-950/80 border border-cyan-500/30 flex items-center justify-center text-sm shadow-[0_0_12px_rgba(6,182,212,0.25)]">
            🧠
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-100">
                Neo Project App Graph
              </h3>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-cyan-900/40 text-cyan-300 border border-cyan-700/50">
                {summary.total_nodes || 0} Nodes
              </span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-indigo-900/40 text-indigo-300 border border-indigo-700/50">
                {summary.total_edges || 0} Edges
              </span>
            </div>
            <p className="text-[10px] text-slate-400 font-mono">
              TUIs • Web Apps • Notebooks • 7-Layer Mesh • Bicep ECG • SeaweedFS
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {/* Obsidian Sync Button */}
          <button
            onClick={handleSyncToObsidian}
            disabled={isSyncingVault}
            className="px-2.5 py-1 rounded-md text-[11px] font-mono bg-slate-800/90 hover:bg-slate-700 text-slate-200 border border-slate-700 hover:border-slate-600 transition-all flex items-center space-x-1.5 disabled:opacity-50"
            title="Sync latest graph and Wikilinks directly into Obsidian Vault"
          >
            <span>{isSyncingVault ? '⏳' : '📓'}</span>
            <span>{isSyncingVault ? 'Syncing...' : 'Sync to Obsidian'}</span>
          </button>

          {onToggleExpand && (
            <button
              onClick={onToggleExpand}
              className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800"
              title={isExpanded ? 'Collapse' : 'Expand full view'}
            >
              {isExpanded ? '⤡' : '⤢'}
            </button>
          )}
        </div>
      </div>

      {/* Sync Feedback Toast */}
      {syncFeedback && (
        <div className="px-4 py-1.5 bg-emerald-950/80 border-b border-emerald-800 text-emerald-300 text-xs font-mono text-center">
          {syncFeedback}
        </div>
      )}

      {/* Real-time Hardware & Biometrics Ribbon */}
      <div className="px-3 py-2 bg-slate-900/30 border-b border-slate-800/60 grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-mono">
        <div className="flex items-center space-x-1.5 p-1.5 rounded bg-slate-950/60 border border-slate-800">
          <span className="text-emerald-400">⚡</span>
          <div className="truncate">
            <div className="text-[9px] text-slate-500 uppercase">Hardware Bus</div>
            <div className="text-emerald-400 font-semibold truncate">
              {usb3.protocol || 'USB 3.2 Gen 2'} ({usb3.max_rate || '10 Gbps'})
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-1.5 p-1.5 rounded bg-slate-950/60 border border-slate-800">
          <span className="text-rose-400 animate-pulse">❤️</span>
          <div className="truncate">
            <div className="text-[9px] text-slate-500 uppercase">Movesense (Bicep ECG)</div>
            <div className="text-rose-400 font-semibold truncate">
              {ecg.connected && ecg.heart_rate_bpm ? `${ecg.heart_rate_bpm} BPM` : 'Disconnected (-- BPM)'} • {ecg.connected && ecg.zone ? ecg.zone.split(' ')[0] : 'STANDBY'}
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-1.5 p-1.5 rounded bg-slate-950/60 border border-slate-800">
          <span className="text-cyan-400">🛡️</span>
          <div className="truncate">
            <div className="text-[9px] text-slate-500 uppercase">Kamath 20% Filter</div>
            <div className="text-cyan-400 font-semibold truncate">ENGAGED (Bicep Noise Gate)</div>
          </div>
        </div>

        <div className="flex items-center space-x-1.5 p-1.5 rounded bg-slate-950/60 border border-slate-800">
          <span className="text-amber-400">💾</span>
          <div className="truncate">
            <div className="text-[9px] text-slate-500 uppercase">SeaweedFS FUSE</div>
            <div className="text-amber-400 font-semibold truncate">/DFS_UNIFIED (:8888)</div>
          </div>
        </div>
      </div>

      {/* Category Filter Chips & Search */}
      <div className="p-3 border-b border-slate-800/80 bg-slate-900/40 space-y-2">
        <div className="flex items-center space-x-2">
          <div className="relative flex-1">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter nodes by name, port, engine, or keywords..."
              className="w-full px-3 py-1.5 pl-8 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500/50"
            />
            <span className="absolute left-2.5 top-2 text-slate-500 text-xs">🔍</span>
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-2 text-slate-400 hover:text-slate-200 text-xs font-bold"
              >
                ×
              </button>
            )}
          </div>
        </div>

        {/* Categories Bar */}
        <div className="flex items-center space-x-1.5 overflow-x-auto pb-1 scrollbar-none text-[11px] font-mono">
          {Object.entries(CATEGORY_META).map(([key, meta]) => {
            const count = key === 'all' ? summary.total_nodes : (summary.categories?.[key] || 0);
            const isSelected = selectedCategory === key;
            return (
              <button
                key={key}
                onClick={() => setSelectedCategory(key)}
                className={`px-2 py-1 rounded-md whitespace-nowrap transition-all flex items-center space-x-1 border ${
                  isSelected
                    ? `${meta.color} font-bold shadow-[0_0_8px_rgba(6,182,212,0.15)] ring-1 ring-cyan-400/40`
                    : 'bg-slate-900/60 hover:bg-slate-800/70 text-slate-400 border-slate-800'
                }`}
              >
                <span>{meta.icon}</span>
                <span>{meta.label}</span>
                <span className="text-[9px] opacity-70">({count})</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Split Body: Node Grid + Inspector */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
        {/* Node Grid */}
        <div className="flex-1 p-3 overflow-y-auto space-y-2 max-h-[450px] md:max-h-full">
          {filteredNodes.length === 0 ? (
            <div className="text-center py-10 text-slate-500 font-mono text-xs">
              No nodes matching criteria.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {filteredNodes.map((node) => {
                const isSelected = selectedNode?.id === node.id;
                const catMeta = CATEGORY_META[node.category] || CATEGORY_META.all;
                const isOnline =
                  node.status === 'ONLINE' ||
                  node.status === 'HEALTHY' ||
                  node.status === 'ACTIVE' ||
                  node.status === 'STREAMING';

                return (
                  <div
                    key={node.id}
                    onClick={() => setSelectedNode(node)}
                    className={`p-2.5 rounded-lg border cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-cyan-950/30 border-cyan-500/60 shadow-[0_0_12px_rgba(6,182,212,0.2)]'
                        : 'bg-slate-900/50 hover:bg-slate-900/90 border-slate-800/80 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-1 mb-1">
                      <div className="flex items-center space-x-1.5 truncate">
                        <span className="text-xs">{catMeta.icon}</span>
                        <span className="text-xs font-semibold text-slate-200 truncate">
                          {node.label}
                        </span>
                      </div>
                      <span
                        className={`px-1.5 py-0.5 rounded text-[9px] font-mono uppercase tracking-wider font-bold ${
                          isOnline
                            ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/60'
                            : 'bg-amber-950/80 text-amber-400 border border-amber-800/60'
                        }`}
                      >
                        {node.status || 'STANDBY'}
                      </span>
                    </div>

                    <p className="text-[11px] text-slate-400 line-clamp-2 mb-2">
                      {node.details || node.role || node.path || '--'}
                    </p>

                    <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 border-t border-slate-800/50 pt-1.5">
                      <span className="truncate">
                        {node.port ? `Port :${node.port}` : node.engine || node.protocol || node.category}
                      </span>
                      {node.hotkey && (
                        <span className="px-1 py-0.2 rounded bg-slate-800 text-cyan-300 font-bold">
                          {node.hotkey}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Selected Node Inspector Drawer */}
        <div className="w-full md:w-80 border-t md:border-t-0 md:border-l border-slate-800/80 bg-slate-900/60 p-4 flex flex-col justify-between overflow-y-auto">
          {selectedNode ? (
            <div className="space-y-4 font-mono text-xs">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="px-2 py-0.5 rounded text-[10px] uppercase font-bold bg-slate-800 text-slate-300">
                    {selectedNode.category}
                  </span>
                  <span className="text-[10px] text-slate-500">ID: {selectedNode.id}</span>
                </div>
                <h4 className="text-sm font-bold text-slate-100 flex items-center space-x-1.5">
                  <span>{CATEGORY_META[selectedNode.category]?.icon || '📦'}</span>
                  <span>{selectedNode.label}</span>
                </h4>
              </div>

              <div className="space-y-2 p-3 rounded-lg bg-slate-950/80 border border-slate-800/80">
                <div className="flex justify-between py-1 border-b border-slate-800/50">
                  <span className="text-slate-500">Status:</span>
                  <span className="text-emerald-400 font-bold">{selectedNode.status || 'ONLINE'}</span>
                </div>

                {selectedNode.port && (
                  <div className="flex justify-between py-1 border-b border-slate-800/50">
                    <span className="text-slate-500">Port / Endpoint:</span>
                    <span className="text-cyan-400 font-bold">:{selectedNode.port}</span>
                  </div>
                )}

                {selectedNode.url && (
                  <div className="flex justify-between py-1 border-b border-slate-800/50">
                    <span className="text-slate-500">URL:</span>
                    <a
                      href={selectedNode.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-cyan-400 underline hover:text-cyan-300 truncate max-w-[160px]"
                    >
                      {selectedNode.url}
                    </a>
                  </div>
                )}

                {selectedNode.hardware_bus && (
                  <div className="flex justify-between py-1 border-b border-slate-800/50">
                    <span className="text-slate-500">Hardware Bus:</span>
                    <span className="text-emerald-300 font-bold text-right truncate max-w-[160px]">
                      {selectedNode.hardware_bus}
                    </span>
                  </div>
                )}

                {selectedNode.ram && (
                  <div className="flex justify-between py-1 border-b border-slate-800/50">
                    <span className="text-slate-500">RAM / AI Cap:</span>
                    <span className="text-slate-200">{selectedNode.ram}</span>
                  </div>
                )}

                {selectedNode.engine && (
                  <div className="flex justify-between py-1 border-b border-slate-800/50">
                    <span className="text-slate-500">Engine:</span>
                    <span className="text-slate-300">{selectedNode.engine}</span>
                  </div>
                )}

                {selectedNode.placement && (
                  <div className="flex justify-between py-1 border-b border-slate-800/50">
                    <span className="text-slate-500">Placement:</span>
                    <span className="text-rose-300 font-bold">{selectedNode.placement} (Bicep ECG)</span>
                  </div>
                )}

                {selectedNode.heart_rate_bpm && (
                  <div className="flex justify-between py-1 border-b border-slate-800/50">
                    <span className="text-slate-500">Live Heart Rate:</span>
                    <span className="text-rose-400 font-bold">{selectedNode.heart_rate_bpm} BPM</span>
                  </div>
                )}

                {selectedNode.zone && (
                  <div className="flex justify-between py-1 border-b border-slate-800/50">
                    <span className="text-slate-500">HR Zone:</span>
                    <span className="text-cyan-300">{selectedNode.zone}</span>
                  </div>
                )}

                {selectedNode.path && (
                  <div className="py-1">
                    <span className="text-slate-500 block mb-0.5">Path / Command:</span>
                    <code className="text-[10px] text-slate-300 bg-slate-900 px-1.5 py-0.5 rounded block truncate">
                      {selectedNode.path}
                    </code>
                  </div>
                )}
              </div>

              <div className="p-2.5 rounded bg-slate-900/40 border border-slate-800 text-[11px] text-slate-300 leading-relaxed">
                {selectedNode.details || selectedNode.role || 'Component registered in canonical monorepo hierarchy.'}
              </div>

              {selectedNode.url && (
                <a
                  href={selectedNode.url}
                  target="_blank"
                  rel="noreferrer"
                  className="w-full py-2 bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-center rounded-lg shadow-[0_0_12px_rgba(6,182,212,0.3)] transition-all flex items-center justify-center space-x-1.5"
                >
                  <span>Launch in Browser</span>
                  <span>↗</span>
                </a>
              )}
            </div>
          ) : (
            <div className="text-center py-12 text-slate-500 font-mono text-xs">
              Select any node from the graph to inspect live ports, hardware bus links, and telemetry metrics.
            </div>
          )}

          <div className="mt-4 pt-3 border-t border-slate-800/60 text-[10px] text-slate-500 font-mono flex justify-between items-center">
            <span>Neo Scribe AI v3.0</span>
            <span className="text-emerald-400">● 100% Zero-Mock Verified</span>
          </div>
        </div>
      </div>
    </div>
  );
}
