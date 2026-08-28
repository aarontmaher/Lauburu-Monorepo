import React, { useEffect, useRef, useState } from 'react';

export default function MeshBattlefieldCanvas({ activeAgents = [], activeDaemons = [], onSpecialAction }) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const [is3dMode, setIs3dMode] = useState(true);
  const [fps, setFps] = useState(60);
  const [activeBeams, setActiveBeams] = useState([]);
  const [activeParticles, setActiveParticles] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);

  // Mesh 5 physical nodes layout
  const nodes = [
    { id: 'mac_m4', name: 'Mac M4 Max Host', tier: 'Layer 1: Orchestrator', x3: -120, y3: -40, z3: -50, color: '#38bdf8', icon: '💻', tokens: '89.5M LCT', type: 'local' },
    { id: 'mac_pro', name: 'Mac Pro Worker', tier: 'Layer 2: TB4 Metal', x3: 120, y3: -40, z3: -50, color: '#60a5fa', icon: '⚡', tokens: '10G TB4', type: 'local' },
    { id: 'linux_head', name: 'Linux Head Node', tier: 'Layer 3: NVMe Cache', x3: 0, y3: -80, z3: 60, color: '#4ade80', icon: '🐧', tokens: '1TB NVMe', type: 'local' },
    { id: 'pixel_phone', name: 'Pixel 10 Pro XL', tier: 'Layer 4: Edge TPU', x3: -90, y3: 60, z3: 20, color: '#c084fc', icon: '📱', tokens: '8K PTZ', type: 'local' },
    { id: 's20_tester', name: 'Samsung S20+', tier: 'Layer 5: UI/UX Tester', x3: 90, y3: 60, z3: 20, color: '#f472b6', icon: '🧪', tokens: '15W Qi', type: 'local' },
    // Cloud mirrored pod
    { id: 'gemini_ultra_cloud', name: 'Gemini Ultra Fleet', tier: 'Cloud Mega-Pod (US-Central)', x3: 0, y3: 130, z3: -80, color: '#f87171', icon: '🧠', tokens: '641TB HBM', type: 'cloud' }
  ];

  // Orbit state
  const orbitRef = useRef({
    rotX: 0.25,
    rotY: 0,
    zoom: 1.0,
    isDragging: false,
    lastX: 0,
    lastY: 0,
    frameCount: 0,
    lastFpsTime: performance.now()
  });

  const project3dPoint = (x3, y3, z3, cx, cy) => {
    if (!is3dMode) {
      return { x: cx + x3 * 1.6, y: cy + y3 * 1.4, scale: 1.0, depth: 0 };
    }
    const { rotX, rotY, zoom } = orbitRef.current;
    
    // Rotate Y
    const cosY = Math.cos(rotY);
    const sinY = Math.sin(rotY);
    const x1 = x3 * cosY + z3 * sinY;
    const z1 = -x3 * sinY + z3 * cosY;

    // Rotate X
    const cosX = Math.cos(rotX);
    const sinX = Math.sin(rotX);
    const y2 = y3 * cosX - z1 * sinX;
    const z2 = y3 * sinX + z1 * cosX;

    const focal = 380;
    const scale = (focal / (focal + z2)) * zoom;
    return {
      x: cx + x1 * scale,
      y: cy + y2 * scale,
      scale: scale,
      depth: z2
    };
  };

  const triggerLaserHeist = (fromIdx, toIdx, color = '#38bdf8', text = '⚡ DMA TOKEN SIPHON') => {
    const startNode = nodes[fromIdx] || nodes[0];
    const targetNode = nodes[toIdx] || nodes[1];

    setActiveBeams(prev => [
      ...prev.slice(-4),
      {
        startId: startNode.id,
        targetId: targetNode.id,
        fromIdx,
        toIdx,
        color,
        life: 1.0,
        text
      }
    ]);

    // Spawn particle bursts
    const newParticles = [];
    for (let i = 0; i < 6; i++) {
      newParticles.push({
        fromIdx,
        toIdx,
        progress: 0,
        speed: 0.02 + Math.random() * 0.03,
        color,
        size: 3 + Math.random() * 3
      });
    }
    setActiveParticles(prev => [...prev.slice(-15), ...newParticles]);
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animId;

    const render = () => {
      animId = requestAnimationFrame(render);
      const width = canvas.width;
      const height = canvas.height;
      const cx = width / 2;
      const cy = height / 2;

      // Auto rotation
      if (!orbitRef.current.isDragging && is3dMode) {
        orbitRef.current.rotY += 0.0015;
      }

      // FPS tracking
      orbitRef.current.frameCount++;
      const now = performance.now();
      if (now - orbitRef.current.lastFpsTime >= 1000) {
        setFps(orbitRef.current.frameCount);
        orbitRef.current.frameCount = 0;
        orbitRef.current.lastFpsTime = now;
      }

      // Background wipe
      ctx.fillStyle = '#040714';
      ctx.fillRect(0, 0, width, height);

      // Draw 3D floor grid
      if (is3dMode) {
        ctx.strokeStyle = 'rgba(56, 189, 248, 0.08)';
        ctx.lineWidth = 1;
        const floorY = 100;
        for (let gx = -240; gx <= 240; gx += 60) {
          const p1 = project3dPoint(gx, floorY, -240, cx, cy);
          const p2 = project3dPoint(gx, floorY, 240, cx, cy);
          ctx.beginPath();
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.stroke();
        }
        for (let gz = -240; gz <= 240; gz += 60) {
          const p1 = project3dPoint(-240, floorY, gz, cx, cy);
          const p2 = project3dPoint(240, floorY, gz, cx, cy);
          ctx.beginPath();
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.stroke();
        }
      }

      // Projected positions
      const projectedNodes = nodes.map(n => ({
        ...n,
        proj: project3dPoint(n.x3, n.y3, n.z3, cx, cy)
      }));

      // Draw TB4 / Network Bridges between nodes
      const connections = [
        [0, 1, '10Gbps TB4 Bridge (0.27ms RTT)', 'rgba(56, 189, 248, 0.5)', 3],
        [0, 2, 'Tailscale WireGuard / LAN', 'rgba(74, 222, 128, 0.35)', 1.5],
        [1, 2, 'Decentralized Fast NVMe', 'rgba(74, 222, 128, 0.3)', 1.5],
        [0, 3, 'Termux ADB / 8K Vision Stream', 'rgba(192, 132, 252, 0.35)', 1.5],
        [0, 4, '15W Qi / Automated ADB UI Tester', 'rgba(244, 114, 182, 0.35)', 1.5],
        [0, 5, 'Cloudflare QUIC Zero-Trust WAN Tunnel', 'rgba(248, 113, 113, 0.4)', 2]
      ];

      connections.forEach(([i1, i2, label, color, lw]) => {
        const p1 = projectedNodes[i1].proj;
        const p2 = projectedNodes[i2].proj;
        ctx.strokeStyle = color;
        ctx.lineWidth = lw;
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();
      });

      // Render Active Infiltration Laser Beams
      setActiveBeams(currentBeams => {
        return currentBeams.filter(beam => {
          const p1 = projectedNodes[beam.fromIdx]?.proj;
          const p2 = projectedNodes[beam.toIdx]?.proj;
          if (!p1 || !p2) return false;

          ctx.strokeStyle = beam.color;
          ctx.lineWidth = 3 * beam.life;
          ctx.beginPath();
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.stroke();

          // Laser glow
          ctx.strokeStyle = '#ffffff';
          ctx.lineWidth = 1 * beam.life;
          ctx.beginPath();
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.stroke();

          return beam.life - 0.02 > 0;
        }).map(beam => ({ ...beam, life: beam.life - 0.02 }));
      });

      // Render Siphon Particles
      setActiveParticles(currentParticles => {
        return currentParticles.filter(p => {
          const p1 = projectedNodes[p.fromIdx]?.proj;
          const p2 = projectedNodes[p.toIdx]?.proj;
          if (!p1 || !p2) return false;

          p.progress += p.speed;
          if (p.progress >= 1.0) return false;

          const px = p1.x + (p2.x - p1.x) * p.progress;
          const py = p1.y + (p2.y - p1.y) * p.progress;

          ctx.fillStyle = p.color;
          ctx.beginPath();
          ctx.arc(px, py, p.size, 0, Math.PI * 2);
          ctx.fill();

          return true;
        });
      });

      // Draw Nodes (Sorted by depth for true 3D occlusion)
      const sortedNodes = [...projectedNodes].sort((a, b) => b.proj.depth - a.proj.depth);

      sortedNodes.forEach(node => {
        const { x, y, scale } = node.proj;
        const radius = Math.max(12, 22 * scale);

        // Node Glow
        const glow = ctx.createRadialGradient(x, y, radius * 0.2, x, y, radius * 2.2);
        glow.addColorStop(0, node.color + '88');
        glow.addColorStop(1, node.color + '00');
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(x, y, radius * 2.2, 0, Math.PI * 2);
        ctx.fill();

        // Node Core Circle
        ctx.fillStyle = node.type === 'cloud' ? '#450a0a' : '#0f172a';
        ctx.strokeStyle = node.color;
        ctx.lineWidth = 2.5 * scale;
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();

        // Icon
        ctx.font = `${Math.round(14 * scale)}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(node.icon, x, y);

        // Label Tag
        ctx.font = `bold ${Math.max(9, Math.round(11 * scale))}px system-ui, sans-serif`;
        ctx.fillStyle = '#f8fafc';
        ctx.fillText(node.name, x, y + radius + 14 * scale);

        ctx.font = `${Math.max(8, Math.round(9 * scale))}px system-ui, sans-serif`;
        ctx.fillStyle = node.color;
        ctx.fillText(node.tier, x, y + radius + 26 * scale);
      });
    };

    render();
    return () => cancelAnimationFrame(animId);
  }, [is3dMode]);

  // Mouse drag handlers
  const handleMouseDown = (e) => {
    orbitRef.current.isDragging = true;
    orbitRef.current.lastX = e.clientX;
    orbitRef.current.lastY = e.clientY;
  };

  const handleMouseMove = (e) => {
    if (!orbitRef.current.isDragging) return;
    const dx = e.clientX - orbitRef.current.lastX;
    const dy = e.clientY - orbitRef.current.lastY;
    orbitRef.current.rotY += dx * 0.008;
    orbitRef.current.rotX = Math.max(-0.6, Math.min(0.8, orbitRef.current.rotX + dy * 0.008));
    orbitRef.current.lastX = e.clientX;
    orbitRef.current.lastY = e.clientY;
  };

  const handleMouseUp = () => {
    orbitRef.current.isDragging = false;
  };

  return (
    <div style={{
      background: 'linear-gradient(135deg, rgba(15,23,42,0.95), rgba(4,7,20,0.95))',
      border: '1px solid rgba(56,189,248,0.3)',
      borderRadius: '12px',
      overflow: 'hidden',
      position: 'relative',
      boxShadow: '0 8px 32px rgba(0,0,0,0.5)'
    }}>
      {/* HUD Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '0.6rem 1rem',
        background: 'rgba(0,0,0,0.4)',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        fontSize: '0.8rem',
        flexWrap: 'wrap',
        gap: '0.5rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <span style={{ fontSize: '1.1rem' }}>🛰️</span>
          <strong>3D Mesh Interactive Battlefield &amp; Token Conduit Radar</strong>
          <span style={{ fontSize: '0.7rem', background: 'rgba(16,185,129,0.2)', color: '#34d399', padding: '2px 6px', borderRadius: '4px', border: '1px solid rgba(16,185,129,0.3)', fontWeight: 'bold' }}>
            ● {fps} FPS
          </span>
        </div>

        <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
          <button
            onClick={() => triggerLaserHeist(0, 1, '#38bdf8', '⚡ TB4 10Gbps DMA Heist')}
            style={{ background: 'rgba(56,189,248,0.2)', border: '1px solid #38bdf8', color: '#38bdf8', borderRadius: '6px', padding: '3px 8px', fontSize: '0.72rem', cursor: 'pointer', fontWeight: 'bold' }}
          >
            ⚡ Fire TB4 DMA Burst
          </button>
          <button
            onClick={() => triggerLaserHeist(0, 5, '#f43f5e', '🔴 Cloud Titan Cross-Raid')}
            style={{ background: 'rgba(244,63,94,0.2)', border: '1px solid #f43f5e', color: '#f43f5e', borderRadius: '6px', padding: '3px 8px', fontSize: '0.72rem', cursor: 'pointer', fontWeight: 'bold' }}
          >
            🔴 Cross-Faction Raid
          </button>
          <button
            onClick={() => setIs3dMode(!is3dMode)}
            style={{ background: is3dMode ? 'rgba(168,85,247,0.25)' : 'rgba(255,255,255,0.1)', border: '1px solid #a855f7', color: '#c084fc', borderRadius: '6px', padding: '3px 8px', fontSize: '0.72rem', cursor: 'pointer', fontWeight: 'bold' }}
          >
            {is3dMode ? '🌐 3D Spatial Hologram' : '📐 2D Schematic'}
          </button>
        </div>
      </div>

      {/* Interactive 3D Canvas */}
      <div
        ref={containerRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        style={{
          width: '100%',
          height: '320px',
          cursor: orbitRef.current.isDragging ? 'grabbing' : 'grab',
          position: 'relative'
        }}
      >
        <canvas
          ref={canvasRef}
          width={800}
          height={320}
          style={{ width: '100%', height: '100%', display: 'block' }}
        />
      </div>

      {/* Footer Conduit Telemetry */}
      <div style={{
        padding: '0.4rem 1rem',
        background: 'rgba(0,0,0,0.5)',
        borderTop: '1px solid rgba(255,255,255,0.06)',
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: '0.72rem',
        color: '#94a3b8',
        flexWrap: 'wrap',
        gap: '0.4rem'
      }}>
        <span>⚡ 10Gbps TB4 Bridge: <strong style={{ color: '#38bdf8' }}>0.277ms RTT</strong></span>
        <span>🔒 Tailscale WireGuard: <strong style={{ color: '#4ade80' }}>Encrypted L2/L3</strong></span>
        <span>🧠 Pooled VRAM Mesh: <strong style={{ color: '#c084fc' }}>82.8 GB Usable</strong></span>
        <span>🎯 Drag canvas to rotate orbit in 3D</span>
      </div>
    </div>
  );
}
