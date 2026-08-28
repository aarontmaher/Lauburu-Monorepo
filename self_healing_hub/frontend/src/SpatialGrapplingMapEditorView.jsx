import React, { useState, useEffect } from 'react';

export default function SpatialGrapplingMapEditorView() {
  const [mapData, setMapData] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedTransition, setSelectedTransition] = useState(null);
  const [activeTab, setActiveTab] = useState('canvas'); // 'canvas', 'node_editor', 'transition_linker', 'flow_sim'
  const [simulatedChain, setSimulatedChain] = useState([]);
  const [statusMessage, setStatusMessage] = useState(null);
  const [filterCategory, setFilterCategory] = useState('ALL');

  // Form states for creating/editing nodes
  const [nodeForm, setNodeForm] = useState({
    id: '',
    name: '',
    category: 'Guard',
    x: 0.0,
    y: 1.5,
    z: 0.5,
    risk: 'Medium',
    description: ''
  });

  // Form states for transitions
  const [transForm, setTransForm] = useState({
    from: '',
    to: '',
    name: '',
    difficulty: 7.5,
    torque_nm: 150,
    min_time_s: 1.2
  });

  const apiHost = window.location.hostname || 'localhost';

  const fetchMap = async () => {
    try {
      const res = await fetch(`http://${apiHost}:5001/api/spatial/grappling_map`);
      if (res.ok) {
        const data = await res.json();
        setMapData(data);
        if (!selectedNode && Object.keys(data.nodes || {}).length > 0) {
          const firstNode = Object.values(data.nodes)[0];
          setSelectedNode(firstNode);
          setNodeForm(firstNode);
        }
      }
    } catch (err) {
      console.error('Error fetching spatial grappling map:', err);
    }
  };

  useEffect(() => {
    fetchMap();
  }, [apiHost]);

  const handleSelectNode = (node) => {
    setSelectedNode(node);
    setSelectedTransition(null);
    setNodeForm(node);
    if (transForm.from === '') {
      setTransForm(prev => ({ ...prev, from: node.id }));
    }
  };

  const handleSaveNode = async (e) => {
    e.preventDefault();
    setStatusMessage('⏳ Saving node & exporting AI training pairs...');
    try {
      const res = await fetch(`http://${apiHost}:5001/api/spatial/grappling_map/node`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(nodeForm)
      });
      if (res.ok) {
        setStatusMessage('✅ Spatial Node saved and added to 24/7 LoRA training corpus!');
        fetchMap();
        setTimeout(() => setStatusMessage(null), 3500);
      }
    } catch (err) {
      setStatusMessage(`❌ Error saving node: ${err.message}`);
    }
  };

  const handleAddTransition = async (e) => {
    e.preventDefault();
    if (!transForm.from || !transForm.to) {
      alert('Please select both Origin and Destination nodes.');
      return;
    }
    setStatusMessage('⏳ Linking transition & generating biomechanical training pairs...');
    try {
      const res = await fetch(`http://${apiHost}:5001/api/spatial/grappling_map/transition`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(transForm)
      });
      if (res.ok) {
        setStatusMessage('✅ Transition linked and exported to Google Drive AI Memory!');
        fetchMap();
        setTransForm({ from: '', to: '', name: '', difficulty: 7.5, torque_nm: 150, min_time_s: 1.2 });
        setTimeout(() => setStatusMessage(null), 3500);
      }
    } catch (err) {
      setStatusMessage(`❌ Error linking transition: ${err.message}`);
    }
  };

  const nodesList = Object.values(mapData?.nodes || {});
  const transitionsList = mapData?.transitions || [];

  const filteredNodes = filterCategory === 'ALL'
    ? nodesList
    : nodesList.filter(n => n.category === filterCategory);

  const categories = ['ALL', 'Neutral', 'Clinch', 'Takedown', 'Guard', 'Passing', 'Pin', 'Leg Entanglement', 'Submission'];

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '1.2rem',
      padding: '1.2rem',
      background: '#080c14',
      minHeight: '85vh',
      color: '#f8fafc',
      fontFamily: 'Inter, system-ui, sans-serif'
    }}>
      {/* TOP HEADER */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        background: 'linear-gradient(135deg, rgba(16,185,129,0.12), rgba(15,23,42,0.95))',
        border: '1px solid rgba(16,185,129,0.35)',
        borderRadius: '12px',
        padding: '1.2rem 1.4rem',
        boxShadow: '0 8px 24px rgba(0,0,0,0.45)',
        flexWrap: 'wrap',
        gap: '0.8rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem' }}>
          <div style={{ fontSize: '2.2rem' }}>🥋</div>
          <div>
            <div style={{ fontSize: '1.25rem', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span>3D Spatial Instructional Map &amp; Live Training Editor</span>
              <span style={{ fontSize: '0.72rem', background: '#10b981', color: '#000', padding: '2px 8px', borderRadius: '6px', fontWeight: 'bold' }}>
                OPML KINEMATICS ACTIVE
              </span>
            </div>
            <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '2px' }}>
              31 Positional States • 57 Biomechanical Transitions • Movesense 128Hz Triggers • 24/7 LoRA Corpus Export
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center' }}>
          <button
            onClick={() => {
              setNodeForm({ id: `pos_${Date.now()}`, name: 'New Technique Position', category: 'Guard', x: 0.0, y: 1.5, z: 0.5, risk: 'Medium', description: '' });
              setActiveTab('node_editor');
            }}
            style={{
              background: 'linear-gradient(135deg, #10b981, #34d399)',
              border: 'none',
              color: '#000',
              padding: '8px 16px',
              borderRadius: '8px',
              fontWeight: 'bold',
              fontSize: '0.8rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem'
            }}
          >
            <span>➕</span>
            <span>Add Technique Node</span>
          </button>
        </div>
      </div>

      {statusMessage && (
        <div style={{
          padding: '10px 14px',
          background: statusMessage.includes('❌') ? 'rgba(239,68,68,0.2)' : 'rgba(16,185,129,0.2)',
          border: `1px solid ${statusMessage.includes('❌') ? '#ef4444' : '#10b981'}`,
          borderRadius: '8px',
          fontSize: '0.82rem',
          color: statusMessage.includes('❌') ? '#fca5a5' : '#86efac'
        }}>
          {statusMessage}
        </div>
      )}

      {/* NAVIGATION TABS & CATEGORY FILTERS */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.6rem' }}>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {[
            { id: 'canvas', label: '🌌 3D Spatial Mat Canvas', icon: '📐' },
            { id: 'node_editor', label: '🛠️ Technique & Node Editor', icon: '✏️' },
            { id: 'transition_linker', label: '🔄 Transition & Vector Linker', icon: '🔗' },
            { id: 'flow_sim', label: '⚡ Attack Flow Simulator', icon: '🥋' }
          ].map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              style={{
                background: activeTab === t.id ? 'rgba(16,185,129,0.15)' : 'rgba(255,255,255,0.04)',
                border: activeTab === t.id ? '1px solid #10b981' : '1px solid rgba(255,255,255,0.08)',
                color: activeTab === t.id ? '#10b981' : '#94a3b8',
                padding: '6px 12px',
                borderRadius: '6px',
                fontSize: '0.78rem',
                fontWeight: activeTab === t.id ? 'bold' : 'normal',
                cursor: 'pointer'
              }}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Category Filter Chips */}
        <div style={{ display: 'flex', gap: '0.3rem', overflowX: 'auto', paddingBottom: '2px' }}>
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setFilterCategory(cat)}
              style={{
                background: filterCategory === cat ? '#38bdf8' : '#1f2937',
                color: filterCategory === cat ? '#000' : '#94a3b8',
                border: 'none',
                padding: '4px 8px',
                borderRadius: '12px',
                fontSize: '0.68rem',
                fontWeight: filterCategory === cat ? 'bold' : 'normal',
                cursor: 'pointer'
              }}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* TAB 1: 3D SPATIAL MAT CANVAS */}
      {activeTab === 'canvas' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.8fr) minmax(280px, 1fr)', gap: '1rem' }}>
          {/* SVG 3D Isometric Projection */}
          <div style={{ background: '#111827', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '10px', padding: '1rem', position: 'relative' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', fontSize: '0.74rem', marginBottom: '0.6rem' }}>
              <span>📐 8m × 8m Tatami Plane (Origin: Mat Center)</span>
              <span>Showing {filteredNodes.length} Positions • {transitionsList.length} Transitions</span>
            </div>

            <svg viewBox="0 0 800 500" style={{ width: '100%', height: '460px', background: 'radial-gradient(circle at 50% 50%, #172033 0%, #090d16 100%)', borderRadius: '8px', cursor: 'crosshair' }}>
              <defs>
                <pattern id="grid_tatami" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(16,185,129,0.08)" strokeWidth="1"/>
                </pattern>
                <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(56,189,248,0.5)"/>
                </marker>
              </defs>

              <rect width="800" height="500" fill="url(#grid_tatami)" />

              {/* Mat Outline Ring */}
              <circle cx="400" cy="250" r="220" fill="none" stroke="rgba(16,185,129,0.2)" strokeWidth="2" strokeDasharray="6 4" />
              <circle cx="400" cy="250" r="100" fill="none" stroke="rgba(56,189,248,0.15)" strokeWidth="1" />

              {/* Transitions (Directed Lines) */}
              {transitionsList.map((t, idx) => {
                const fromNode = mapData?.nodes?.[t.from];
                const toNode = mapData?.nodes?.[t.to];
                if (!fromNode || !toNode) return null;

                const x1 = 400 + fromNode.x * 120;
                const y1 = 250 - fromNode.y * 70;
                const x2 = 400 + toNode.x * 120;
                const y2 = 250 - toNode.y * 70;

                const isSelected = selectedTransition === t;

                return (
                  <g key={idx} onClick={() => setSelectedTransition(t)} style={{ cursor: 'pointer' }}>
                    <line
                      x1={x1}
                      y1={y1}
                      x2={x2}
                      y2={y2}
                      stroke={isSelected ? '#f59e0b' : 'rgba(56,189,248,0.35)'}
                      strokeWidth={isSelected ? 3 : 1.5}
                      markerEnd="url(#arrow)"
                    />
                  </g>
                );
              })}

              {/* Position Nodes */}
              {filteredNodes.map(node => {
                const cx = 400 + node.x * 120;
                const cy = 250 - node.y * 70;
                const isSelected = selectedNode?.id === node.id;
                const isSub = node.category === 'Submission';

                return (
                  <g key={node.id} onClick={() => handleSelectNode(node)} style={{ cursor: 'pointer' }}>
                    <circle
                      cx={cx}
                      cy={cy}
                      r={isSelected ? 14 : (isSub ? 10 : 8)}
                      fill={isSub ? '#ef4444' : (isSelected ? '#10b981' : '#38bdf8')}
                      stroke={isSelected ? '#fff' : 'rgba(0,0,0,0.5)'}
                      strokeWidth={2}
                      style={{ filter: isSelected ? 'drop-shadow(0 0 8px #10b981)' : 'none', transition: 'all 0.2s ease' }}
                    />
                    <text
                      x={cx}
                      y={cy - 12}
                      fill={isSelected ? '#fff' : '#cbd5e1'}
                      fontSize="9px"
                      fontWeight={isSelected ? 'bold' : 'normal'}
                      textAnchor="middle"
                    >
                      {node.name}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          {/* Node & Transition Inspector Sidebar */}
          <div style={{ background: '#111827', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '10px', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
            <div style={{ fontSize: '0.92rem', fontWeight: 'bold', color: '#10b981', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span>🔍</span>
              <span>Spatial Node Inspector</span>
            </div>

            {selectedNode ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', fontSize: '0.78rem' }}>
                <div style={{ background: 'rgba(0,0,0,0.4)', padding: '10px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                  <div style={{ color: '#94a3b8', fontSize: '0.7rem' }}>Technique Node</div>
                  <div style={{ fontSize: '1.05rem', fontWeight: 'bold', color: '#fff', marginTop: '2px' }}>{selectedNode.name}</div>
                  <div style={{ color: '#38bdf8', fontSize: '0.72rem', marginTop: '2px' }}>Category: {selectedNode.category} • Risk: {selectedNode.risk}</div>
                </div>

                <div style={{ background: 'rgba(0,0,0,0.4)', padding: '10px', borderRadius: '8px' }}>
                  <div style={{ color: '#94a3b8', fontSize: '0.7rem' }}>3D Mat Coordinates</div>
                  <div style={{ fontFamily: 'monospace', color: '#86efac', marginTop: '2px' }}>
                    X: {selectedNode.x}m | Y: {selectedNode.y}m | Z: {selectedNode.z}m
                  </div>
                </div>

                <div style={{ background: 'rgba(0,0,0,0.4)', padding: '10px', borderRadius: '8px' }}>
                  <div style={{ color: '#94a3b8', fontSize: '0.7rem' }}>Tactical Kinematics</div>
                  <div style={{ color: '#cbd5e1', marginTop: '2px', lineHeight: '1.4' }}>{selectedNode.description || 'Primary tactical anchor'}</div>
                </div>

                <button
                  onClick={() => {
                    setNodeForm(selectedNode);
                    setActiveTab('node_editor');
                  }}
                  style={{
                    background: 'rgba(56,189,248,0.2)',
                    border: '1px solid #38bdf8',
                    color: '#7dd3fc',
                    padding: '8px',
                    borderRadius: '6px',
                    fontWeight: 'bold',
                    cursor: 'pointer',
                    marginTop: '0.5rem'
                  }}
                >
                  ✏️ Edit Node Parameters
                </button>
              </div>
            ) : (
              <div style={{ color: '#64748b', fontSize: '0.8rem', textAlign: 'center', padding: '2rem' }}>
                Click on any node in the 3D map to inspect kinematics.
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: TECHNIQUE & NODE EDITOR */}
      {activeTab === 'node_editor' && (
        <div style={{ background: '#111827', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '10px', padding: '1.4rem' }}>
          <div style={{ fontSize: '1rem', fontWeight: 'bold', color: '#38bdf8', marginBottom: '1rem' }}>
            🛠️ Author / Edit 3D Spatial Technique Position
          </div>

          <form onSubmit={handleSaveNode} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
            <div>
              <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Position Name</label>
              <input
                type="text"
                value={nodeForm.name}
                onChange={e => setNodeForm({ ...nodeForm, name: e.target.value })}
                style={{ width: '100%', padding: '8px', background: '#1f2937', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', borderRadius: '6px', marginTop: '4px' }}
                required
              />
            </div>

            <div>
              <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Category</label>
              <select
                value={nodeForm.category}
                onChange={e => setNodeForm({ ...nodeForm, category: e.target.value })}
                style={{ width: '100%', padding: '8px', background: '#1f2937', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', borderRadius: '6px', marginTop: '4px' }}
              >
                {categories.filter(c => c !== 'ALL').map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>3D Mat Coordinates (X, Y, Z meters)</label>
              <div style={{ display: 'flex', gap: '0.4rem', marginTop: '4px' }}>
                <input
                  type="number"
                  step="0.1"
                  placeholder="X"
                  value={nodeForm.x}
                  onChange={e => setNodeForm({ ...nodeForm, x: parseFloat(e.target.value) || 0 })}
                  style={{ width: '33%', padding: '8px', background: '#1f2937', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', borderRadius: '6px' }}
                />
                <input
                  type="number"
                  step="0.1"
                  placeholder="Y"
                  value={nodeForm.y}
                  onChange={e => setNodeForm({ ...nodeForm, y: parseFloat(e.target.value) || 0 })}
                  style={{ width: '33%', padding: '8px', background: '#1f2937', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', borderRadius: '6px' }}
                />
                <input
                  type="number"
                  step="0.1"
                  placeholder="Z"
                  value={nodeForm.z}
                  onChange={e => setNodeForm({ ...nodeForm, z: parseFloat(e.target.value) || 0 })}
                  style={{ width: '33%', padding: '8px', background: '#1f2937', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', borderRadius: '6px' }}
                />
              </div>
            </div>

            <div style={{ gridColumn: '1 / -1' }}>
              <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Tactical &amp; Biomechanical Description</label>
              <textarea
                rows="3"
                value={nodeForm.description}
                onChange={e => setNodeForm({ ...nodeForm, description: e.target.value })}
                style={{ width: '100%', padding: '8px', background: '#1f2937', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', borderRadius: '6px', marginTop: '4px' }}
              />
            </div>

            <button
              type="submit"
              style={{
                background: 'linear-gradient(135deg, #10b981, #34d399)',
                border: 'none',
                color: '#000',
                fontWeight: 'bold',
                padding: '10px 18px',
                borderRadius: '6px',
                cursor: 'pointer',
                gridColumn: '1 / -1'
              }}
            >
              💾 Save Node &amp; Export to LoRA Training Corpus
            </button>
          </form>
        </div>
      )}

      {/* TAB 3: TRANSITION & VECTOR LINKER */}
      {activeTab === 'transition_linker' && (
        <div style={{ background: '#111827', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '10px', padding: '1.4rem' }}>
          <div style={{ fontSize: '1rem', fontWeight: 'bold', color: '#10b981', marginBottom: '1rem' }}>
            🔄 Link 3D Biomechanical Transition Between Nodes
          </div>

          <form onSubmit={handleAddTransition} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
            <div>
              <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Origin Position (From)</label>
              <select
                value={transForm.from}
                onChange={e => setTransForm({ ...transForm, from: e.target.value })}
                style={{ width: '100%', padding: '8px', background: '#1f2937', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', borderRadius: '6px', marginTop: '4px' }}
                required
              >
                <option value="">Select origin node...</option>
                {nodesList.map(n => <option key={n.id} value={n.id}>{n.name} ({n.category})</option>)}
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Destination Position (To)</label>
              <select
                value={transForm.to}
                onChange={e => setTransForm({ ...transForm, to: e.target.value })}
                style={{ width: '100%', padding: '8px', background: '#1f2937', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', borderRadius: '6px', marginTop: '4px' }}
                required
              >
                <option value="">Select destination node...</option>
                {nodesList.map(n => <option key={n.id} value={n.id}>{n.name} ({n.category})</option>)}
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Transition Name</label>
              <input
                type="text"
                placeholder="e.g. Berimbolo Inversion Spin"
                value={transForm.name}
                onChange={e => setTransForm({ ...transForm, name: e.target.value })}
                style={{ width: '100%', padding: '8px', background: '#1f2937', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', borderRadius: '6px', marginTop: '4px' }}
                required
              />
            </div>

            <div>
              <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Difficulty &amp; Peak Torque (Nm)</label>
              <div style={{ display: 'flex', gap: '0.4rem', marginTop: '4px' }}>
                <input
                  type="number"
                  step="0.5"
                  placeholder="Difficulty (1-10)"
                  value={transForm.difficulty}
                  onChange={e => setTransForm({ ...transForm, difficulty: parseFloat(e.target.value) || 5 })}
                  style={{ width: '50%', padding: '8px', background: '#1f2937', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', borderRadius: '6px' }}
                />
                <input
                  type="number"
                  placeholder="Torque (Nm)"
                  value={transForm.torque_nm}
                  onChange={e => setTransForm({ ...transForm, torque_nm: parseInt(e.target.value) || 100 })}
                  style={{ width: '50%', padding: '8px', background: '#1f2937', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', borderRadius: '6px' }}
                />
              </div>
            </div>

            <button
              type="submit"
              style={{
                background: 'linear-gradient(135deg, #0284c7, #38bdf8)',
                border: 'none',
                color: '#000',
                fontWeight: 'bold',
                padding: '10px 18px',
                borderRadius: '6px',
                cursor: 'pointer',
                gridColumn: '1 / -1'
              }}
            >
              🔗 Link Vector &amp; Export Biomechanical LoRA Pair
            </button>
          </form>
        </div>
      )}

      {/* TAB 4: ATTACK FLOW SIMULATOR */}
      {activeTab === 'flow_sim' && (
        <div style={{ background: '#111827', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '10px', padding: '1.4rem' }}>
          <div style={{ fontSize: '1rem', fontWeight: 'bold', color: '#c084fc', marginBottom: '0.8rem' }}>
            ⚡ Interactive Positional Attack Chain Simulator
          </div>
          <p style={{ fontSize: '0.78rem', color: '#94a3b8', marginBottom: '1rem' }}>
            Simulates dynamic transitions from standing neutral to terminal submissions with Movesense 128Hz IMU verification.
          </p>

          <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap', marginBottom: '1.2rem' }}>
            {[
              { name: '🥋 Berimbolo to RNC Flow', chain: ['pos_standing_neutral', 'pos_closed_guard', 'pos_de_la_riva', 'pos_back_control', 'sub_rear_naked_choke'] },
              { name: '🦵 Shin-to-Shin to Inside Heel Hook', chain: ['pos_standing_neutral', 'pos_open_guard', 'pos_ashi_garami', 'pos_inside_saddle', 'sub_inside_heel_hook'] },
              { name: '💥 Blast Double to S-Mount Armbar', chain: ['pos_standing_neutral', 'pos_collar_tie_clinch', 'pos_double_leg_entry', 'pos_side_control', 'pos_full_mount', 'sub_armbar'] }
            ].map((preset, idx) => (
              <button
                key={idx}
                onClick={() => setSimulatedChain(preset.chain)}
                style={{
                  background: 'rgba(192,132,252,0.15)',
                  border: '1px solid #c084fc',
                  color: '#e9d5ff',
                  padding: '8px 14px',
                  borderRadius: '8px',
                  fontSize: '0.78rem',
                  fontWeight: 'bold',
                  cursor: 'pointer'
                }}
              >
                {preset.name}
              </button>
            ))}
          </div>

          {simulatedChain.length > 0 && (
            <div style={{ background: 'rgba(0,0,0,0.4)', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(192,132,252,0.3)' }}>
              <div style={{ fontSize: '0.82rem', fontWeight: 'bold', color: '#c084fc', marginBottom: '0.6rem' }}>
                Simulated Kinematic Execution Sequence:
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                {simulatedChain.map((nodeId, idx) => {
                  const node = mapData?.nodes?.[nodeId] || { name: nodeId };
                  const isLast = idx === simulatedChain.length - 1;
                  return (
                    <React.Fragment key={idx}>
                      <div style={{
                        background: isLast ? 'rgba(239,68,68,0.2)' : 'rgba(56,189,248,0.2)',
                        border: `1px solid ${isLast ? '#ef4444' : '#38bdf8'}`,
                        color: isLast ? '#fca5a5' : '#7dd3fc',
                        padding: '6px 12px',
                        borderRadius: '6px',
                        fontSize: '0.76rem',
                        fontWeight: 'bold'
                      }}>
                        {node.name}
                      </div>
                      {!isLast && <span style={{ color: '#64748b' }}>➔</span>}
                    </React.Fragment>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
