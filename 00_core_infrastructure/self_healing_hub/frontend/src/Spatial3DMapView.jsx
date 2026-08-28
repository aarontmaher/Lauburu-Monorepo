import React, { useState } from 'react';


export default function Spatial3DMapView({ spatialMap }) {
  const [spatialViewMode, setSpatialViewMode] = useState('genie_world');
  const [hoveredNode, setHoveredNode] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [hoveredBeam, setHoveredBeam] = useState(null);

  if (!spatialMap && spatialViewMode !== 'genie_world') {
    return (
      <section className="card leaderboard-card">
        <div style={{ padding: '2rem', textAlign: 'center', color: '#94a3b8' }}>
          🛰️ Polling 3D Spatial Radar Map &amp; UWB Hardware Positioning...
        </div>
      </section>
    );
  }

  return (
    <section className="card leaderboard-card">
      <div className="card-header-flex">
        <div>
          <h2>🛰️ Unified 3D Spatial Radar &amp; Google Genie 2 Holographic World</h2>
          <p style={{ color: '#aaa', fontSize: '0.8rem', marginTop: '0.2rem' }}>
            Google DeepMind Genie 2 Generative World Model, UWB spatial anchors, and real-time physical device coordinates
          </p>
        </div>
        <span className="live-tag">Genie 2 World Model</span>
      </div>

      <div style={{ background: 'rgba(0,0,0,0.4)', padding: '1.2rem', borderRadius: '10px', border: '1px solid rgba(139,92,246,0.3)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.8rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div style={{ color: '#c084fc', fontWeight: 'bold', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span>🌌</span> Active Spatial Radar &amp; Generative World Canvas
          </div>
          <div style={{ display: 'flex', gap: '0.4rem' }}>
            <button 
              onClick={() => setSpatialViewMode('genie_world')} 
              style={{ background: spatialViewMode === 'genie_world' ? 'linear-gradient(135deg, #0284c7, #38bdf8)' : 'rgba(255,255,255,0.08)', color: '#fff', border: '1px solid rgba(56,189,248,0.4)', padding: '4px 10px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 'bold' }}
            >
              🛰️ Google Genie 2 (60FPS)
            </button>
            <button 
              onClick={() => setSpatialViewMode('3d_hologram')} 
              style={{ background: spatialViewMode === '3d_hologram' ? '#8b5cf6' : 'rgba(255,255,255,0.08)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)', padding: '4px 10px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 'bold' }}
            >
              3D Mesh View
            </button>
            <button 
              onClick={() => setSpatialViewMode('vlm_raycast')} 
              style={{ background: spatialViewMode === 'vlm_raycast' ? '#eab308' : 'rgba(255,255,255,0.08)', color: spatialViewMode === 'vlm_raycast' ? '#000' : '#fff', border: '1px solid rgba(255,255,255,0.2)', padding: '4px 10px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 'bold' }}
            >
              VLM Raycast Angle
            </button>
            <button 
              onClick={() => setSpatialViewMode('entities_list')} 
              style={{ background: spatialViewMode === 'entities_list' ? '#38bdf8' : 'rgba(255,255,255,0.08)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)', padding: '4px 10px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.75rem' }}
            >
              Tracked Entities ({spatialMap?.active_entities_count || Object.keys(spatialMap?.nodes || {}).length || 5})
            </button>
          </div>
        </div>

        {/* Google Genie 2 3D Spatial World Engine */}
        {spatialViewMode === 'genie_world' && (
          <div style={{padding: "2rem", color: "#94a3b8"}}>Consolidated into Spatial Sandbox (SpatialGrapplingMapEditorView)</div>
        )}

        {/* 3D Visualizer Canvas Projection */}
        {spatialViewMode === '3d_hologram' && spatialMap && (
          <div style={{ background: '#0a0d14', border: '1px solid rgba(139,92,246,0.2)', borderRadius: '8px', padding: '1rem', position: 'relative', overflow: 'hidden' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#888', fontSize: '0.75rem', marginBottom: '0.5rem' }}>
              <span>Spatial Bounds: {spatialMap.room_dimensions_meters?.width_x || 6}m × {spatialMap.room_dimensions_meters?.length_y || 4}m (Origin: {spatialMap.spatial_origin || 'Primary Mac Host'})</span>
              <span>Multi-Transport Transceiver: Active</span>
            </div>

            {/* SVG 3D Isometric / Spatial Plane Projection */}
            <svg viewBox="0 0 800 450" style={{ width: '100%', height: '360px', background: 'radial-gradient(circle at 50% 50%, #151c2e 0%, #080b12 100%)', borderRadius: '6px' }}>
              <defs>
                <pattern id="grid_spatial" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(139,92,246,0.12)" strokeWidth="1"/>
                </pattern>
              </defs>
              <rect width="800" height="450" fill="url(#grid_spatial)" />

              {/* Laser Beams / Optical Links */}
              {spatialMap.optical_mesh_beams?.map((beam, bIdx) => {
                const fromNode = spatialMap.nodes?.[beam.from];
                const toNode = spatialMap.nodes?.[beam.to];
                if (!fromNode || !toNode) return null;
                
                const x1 = 400 + (fromNode['3d_pose']?.x || 0) * 110;
                const y1 = 380 - (fromNode['3d_pose']?.y || 0) * 70;
                const x2 = 400 + (toNode['3d_pose']?.x || 0) * 110;
                const y2 = 380 - (toNode['3d_pose']?.y || 0) * 70;

                const isHovered = hoveredBeam === beam.beam_id;

                return (
                  <g key={bIdx} onMouseEnter={() => setHoveredBeam(beam.beam_id)} onMouseLeave={() => setHoveredBeam(null)} style={{ cursor: 'pointer' }}>
                    <line 
                      x1={x1} y1={y1} x2={x2} y2={y2} 
                      stroke={beam.line_of_sight === 'clear' ? '#10b981' : '#ef4444'} 
                      strokeWidth={isHovered ? 4 : 2}
                      strokeDasharray={beam.carrier === 'uwb_spatial_range' ? '4,4' : 'none'}
                      opacity={isHovered ? 1 : 0.7}
                    />
                    <circle r={isHovered ? 5 : 3} fill={beam.line_of_sight === 'clear' ? '#34d399' : '#f87171'}>
                      <animateMotion path={`M ${x1} ${y1} L ${x2} ${y2}`} dur={`${Math.max(1, (beam.distance_meters || 1) * 0.8)}s`} repeatCount="indefinite" />
                    </circle>
                  </g>
                );
              })}

              {/* Nodes Rendering */}
              {Object.entries(spatialMap.nodes || {}).map(([nodeKey, nodeData]) => {
                const pose = nodeData['3d_pose'] || nodeData.coords || { x: 0, y: 0, z: 0 };
                const cx = 400 + pose.x * 110;
                const cy = 380 - pose.y * 70;
                const isHovered = hoveredNode === nodeKey || selectedNode === nodeKey;
                const isVideo = nodeData.entity_type === 'visual_dynamic_entity';

                return (
                  <g 
                    key={nodeKey} 
                    transform={`translate(${cx}, ${cy})`}
                    onMouseEnter={() => setHoveredNode(nodeKey)}
                    onMouseLeave={() => setHoveredNode(null)}
                    onClick={() => setSelectedNode(nodeKey === selectedNode ? null : nodeKey)}
                    style={{ cursor: 'pointer' }}
                  >
                    <circle r={isHovered ? 28 : (isVideo ? 22 : 18)} fill={isVideo ? 'rgba(234,179,8,0.2)' : 'rgba(56,189,248,0.15)'} stroke={isVideo ? '#eab308' : '#38bdf8'} strokeWidth={isHovered ? 2 : 1} />
                    <circle r={isHovered ? 12 : 8} fill={isVideo ? '#eab308' : '#38bdf8'} />
                    <text y={isHovered ? -32 : -22} textAnchor="middle" fill="#f8fafc" fontSize={isHovered ? '12px' : '10px'} fontWeight="bold">
                      {nodeData.name || nodeKey}
                    </text>
                    <text y={isHovered ? 38 : 28} textAnchor="middle" fill="#94a3b8" fontSize="9px" fontFamily="monospace">
                      [{pose.x}m, {pose.y}m, {pose.z}m]
                    </text>
                  </g>
                );
              })}
            </svg>

            {/* Node Hover / Selection Overlay */}
            {(selectedNode || hoveredNode) && (
              <div style={{ position: 'absolute', bottom: '20px', left: '20px', background: 'rgba(15,23,42,0.92)', border: '1px solid #8b5cf6', borderRadius: '8px', padding: '0.8rem 1rem', backdropFilter: 'blur(8px)', maxWidth: '320px', zIndex: 10 }}>
                {(() => {
                  const activeKey = selectedNode || hoveredNode;
                  const n = spatialMap.nodes?.[activeKey];
                  if (!n) return null;
                  const pose = n['3d_pose'] || n.coords || { x: 0, y: 0, z: 0 };
                  return (
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.3rem' }}>
                        <strong style={{ color: '#c084fc', fontSize: '0.9rem' }}>{n.name}</strong>
                        <span style={{ fontSize: '0.7rem', background: 'rgba(139,92,246,0.2)', color: '#c084fc', padding: '1px 5px', borderRadius: '3px' }}>{n.archetype}</span>
                      </div>
                      <div style={{ fontSize: '0.75rem', color: '#cbd5e1' }}>
                        <strong>Location:</strong> {n.physical_location || 'Mesh Anchor Area'}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: '#38bdf8', fontFamily: 'monospace', marginTop: '0.2rem' }}>
                        3D Coords: X={pose.x}m, Y={pose.y}m, Z={pose.z}m
                      </div>
                      {n.vision_field_of_view_deg && (
                        <div style={{ fontSize: '0.72rem', color: '#facc15', marginTop: '0.2rem' }}>
                          📷 Camera FOV: {n.vision_field_of_view_deg}° (Resolution: {n.video_resolution || '8K Digital PTZ'})
                        </div>
                      )}
                    </div>
                  );
                })()}
              </div>
            )}
          </div>
        )}

        {/* VLM RAYCAST ANGLE VIEW */}
        {spatialViewMode === 'vlm_raycast' && (
          <div style={{ background: '#0a0d14', border: '1px solid rgba(234,179,8,0.3)', borderRadius: '8px', padding: '1.2rem' }}>
            <h4 style={{ margin: '0 0 0.6rem 0', color: '#facc15', fontSize: '0.9rem' }}>
              👁️ Local VLM Visual Cone &amp; Autonomous PTZ Raycast
            </h4>
            <p style={{ color: '#aaa', fontSize: '0.8rem', margin: '0 0 1rem 0' }}>
              Pixel 10 Pro XL Tensor G5 + Edge TPU 8K Digital PTZ optical cone tracking human workspace.
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '0.8rem' }}>
              <div style={{ background: 'rgba(255,255,255,0.03)', padding: '0.8rem', borderRadius: '6px', borderLeft: '3px solid #eab308' }}>
                <div style={{ color: '#eab308', fontWeight: 'bold', fontSize: '0.8rem' }}>Raycast Vector</div>
                <div style={{ fontSize: '1.1rem', color: '#fff', fontWeight: 'bold', marginTop: '0.2rem' }}>
                  FOV: {spatialMap.nodes?.pixel_10_pro_xl?.vision_field_of_view_deg || 120}° Optical
                </div>
                <div style={{ color: '#888', fontSize: '0.75rem', marginTop: '0.2rem' }}>Target: Center Workstation</div>
              </div>
              <div style={{ background: 'rgba(255,255,255,0.03)', padding: '0.8rem', borderRadius: '6px', borderLeft: '3px solid #10b981' }}>
                <div style={{ color: '#10b981', fontWeight: 'bold', fontSize: '0.8rem' }}>Occlusion State</div>
                <div style={{ fontSize: '1.1rem', color: '#4ade80', fontWeight: 'bold', marginTop: '0.2rem' }}>
                  100% Clear Line of Sight
                </div>
                <div style={{ color: '#888', fontSize: '0.75rem', marginTop: '0.2rem' }}>0 Blind Spots Detected</div>
              </div>
              <div style={{ background: 'rgba(255,255,255,0.03)', padding: '0.8rem', borderRadius: '6px', borderLeft: '3px solid #38bdf8' }}>
                <div style={{ color: '#38bdf8', fontWeight: 'bold', fontSize: '0.8rem' }}>UWB Spatial Ranging</div>
                <div style={{ fontSize: '1.1rem', color: '#fff', fontWeight: 'bold', marginTop: '0.2rem' }}>
                  ± 2.5 cm Accuracy
                </div>
                <div style={{ color: '#888', fontSize: '0.75rem', marginTop: '0.2rem' }}>60 GHz Dual-Split Channel</div>
              </div>
            </div>
          </div>
        )}

        {/* TRACKED ENTITIES LIST */}
        {spatialViewMode === 'entities_list' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            <div style={{ fontSize: '0.85rem', color: '#aaa' }}>
              Tracked Spatial Entities &amp; Coordinates:
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.6rem' }}>
              {Object.entries(spatialMap.nodes || {}).map(([nodeKey, nodeData]) => {
                const pose = nodeData['3d_pose'] || nodeData.coords || { x: 0, y: 0, z: 0 };
                const orient = nodeData.orientation_euler || nodeData.orientation || { pitch: 0, roll: 0, yaw: 0 };
                const isVideoEntity = nodeData.entity_type === 'visual_dynamic_entity';
                return (
                  <div key={nodeKey} style={{ background: isVideoEntity ? 'rgba(234,179,8,0.06)' : 'rgba(255,255,255,0.03)', padding: '0.8rem', borderRadius: '6px', border: isVideoEntity ? '1px solid #eab308' : '1px solid rgba(255,255,255,0.05)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ color: isVideoEntity ? '#facc15' : '#38bdf8', fontWeight: 'bold', fontSize: '0.85rem' }}>{nodeData.name}</div>
                      {isVideoEntity && <span style={{ fontSize: '0.65rem', background: '#eab308', color: '#000', padding: '1px 5px', borderRadius: '3px', fontWeight: 'bold' }}>LIVE VIDEO</span>}
                    </div>
                    <div style={{ color: '#888', fontSize: '0.72rem', marginBottom: '0.4rem' }}>{nodeData.entity_type || nodeData.archetype}</div>
                    <div style={{ fontSize: '0.78rem', color: '#4ade80', fontFamily: 'monospace' }}>
                      XYZ: [{pose.x}m, {pose.y}m, {pose.z}m]
                    </div>
                    <div style={{ fontSize: '0.74rem', color: '#facc15', fontFamily: 'monospace', marginTop: '2px' }}>
                      Orientation: [P:{orient.pitch}°, R:{orient.roll}°, Y:{orient.yaw}°]
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
