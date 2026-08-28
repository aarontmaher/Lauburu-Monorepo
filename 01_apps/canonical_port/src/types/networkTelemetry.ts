/**
 * Canonical Port - Network Telemetry Interface Contracts (R3)
 * Defines structured TypeScript types matching the 7-node Lauburu mesh topology,
 * WAN failover states, Tailscale WireGuard overlay, 10Gbps TB4 DMA Bridge, and llama.cpp Port 50052 RPC matrix.
 */

export interface WanRoute {
  interface: string;
  status: 'ACTIVE' | 'STANDBY' | 'DEGRADED' | 'OFFLINE';
  rttMs: number | null;
  dropRate: number;
  circuitState: 'CLOSED' | 'OPEN' | 'HALF_OPEN';
  bandwidth: string;
  priority?: string;
}

export interface TailscalePeer {
  nodeName: string;
  ip: string;
  status: 'ONLINE' | 'IDLE' | 'OFFLINE';
  relay: string;
  layer?: string;
  os?: string;
}

export interface Tb4DmaInterconnect {
  ip: string;
  status: 'CONNECTED' | 'OFFLINE' | 'DEGRADED';
  rttMs: number;
  throughputGbps: number;
  interface?: string;
  zeroCopyActive?: boolean;
}

export interface LlamaRpcNode {
  nodeName: string;
  endpoint: string;
  layersSharded: number;
  vramUsedGb: number;
  status: 'ONLINE' | 'ACTIVE' | 'OFFLINE';
  latencyMs: number | null;
}

export interface NetworkTelemetryState {
  timestamp: string;
  wanRoutes: WanRoute[];
  tailscalePeers: TailscalePeer[];
  tb4Dma: Tb4DmaInterconnect;
  llamaRpcNodes: LlamaRpcNode[];
}

export type NetworkTelemetrySnapshot = NetworkTelemetryState;
