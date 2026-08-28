/**
 * Adversarial Fixture Suite 4: False Positive Traps (JavaScript / TypeScript)
 * ===========================================================================
 * Legitimate UI, canvas animation, configuration, and data structures that MUST
 * NOT trigger false violations when audited by ZeroMockStaticJudge.
 */

// Trap 1: Legitimate Visual Animation with Required Exemption Header
/* @verified-visual-animation */
export class BackgroundParticleCanvas {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.particles = [];
  }

  initParticles(count = 50) {
    for (let i = 0; i < count; i++) {
      this.particles.push({
        x: Math.random() * this.canvas.width,
        y: Math.random() * this.canvas.height,
        vx: (Math.random() - 0.5) * 2.0,
        vy: (Math.random() - 0.5) * 2.0,
        radius: Math.random() * 3 + 1,
        hue: Math.floor(Math.random() * 360)
      });
    }
  }

  draw() {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    for (const p of this.particles) {
      this.ctx.beginPath();
      this.ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      this.ctx.fillStyle = `hsla(${p.hue}, 80%, 60%, 0.7)`;
      this.ctx.fill();
    }
  }
}

// Trap 2: Legitimate Application Configuration Constants
export const APP_CONFIG = {
  appName: "Multi-WAN Mesh PWA",
  version: "2.4.0",
  apiBaseUrl: "http://localhost:5050",
  pollingIntervalMs: 2000,
  maxRetryAttempts: 5,
  defaultPort: 5050,
  timeoutSeconds: 30
};

// Trap 3: Legitimate Dynamic REST Hydration & Error Catch Block
export async function fetchLiveFleetTelemetry() {
  try {
    const response = await fetch("/api/mesh/nodes");
    if (!response.ok) {
      throw new Error(`HTTP Error: ${response.status}`);
    }
    const data = await response.json();
    return data.nodes.map(node => ({
      id: node.id,
      name: node.name,
      status: node.is_connected ? "CONNECTED" : "DISCONNECTED",
      latency_ms: node.measured_latency_ms ?? null,
      throughput_mbps: node.measured_bandwidth_mbps ?? 0.0
    }));
  } catch (error) {
    // Explicit null/offline fallback handler
    return {
      status: "OFFLINE",
      devices_active: 0,
      nodes: [],
      error: error.message
    };
  }
}

// Trap 4: Legitimate Physics / Geometry Canvas Math
export function drawGraphGrid(ctx, width, height, step = 50) {
  ctx.strokeStyle = "rgba(255, 255, 255, 0.1)";
  ctx.lineWidth = 1;
  for (let x = 0; x < width; x += step) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }
}
