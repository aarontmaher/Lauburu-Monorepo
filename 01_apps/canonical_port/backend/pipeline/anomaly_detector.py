"""
Real-Time Network Anomaly Detection Engine
Version: 3.0.0-CANONICAL

Detects latency spikes (>15ms / >100ms), packet loss bursts (>2%),
VRAM saturation (>90% dynamic cap), CPU saturation, z-score variations,
and node disconnection / dropout events across the 7-layer mesh network.
"""

from typing import Any, Dict, List, Optional
from .metrics_buffer import TimeSeriesRingBuffer


class AnomalyDetector:
    """
    Evaluates real-time node telemetry payloads against statistical thresholds
    and physical mesh operating constraints.
    """

    def __init__(
        self,
        rtt_spike_threshold_ms: float = 15.0,
        drop_threshold_percent: float = 2.0,
        vram_saturation_ratio: float = 0.90,
        cpu_saturation_pct: float = 95.0,
        z_score_threshold: float = 3.0,
    ) -> None:
        self.rtt_spike_threshold_ms: float = rtt_spike_threshold_ms
        self.drop_threshold_percent: float = drop_threshold_percent
        self.vram_saturation_ratio: float = vram_saturation_ratio
        self.cpu_saturation_pct: float = cpu_saturation_pct
        self.z_score_threshold: float = z_score_threshold

    def evaluate_payload(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evaluate a single telemetry payload and return a list of detected anomalies.
        Returns empty list if payload is within nominal bounds.
        """
        anomalies: List[Dict[str, Any]] = []
        node_id = payload.get("node_id", "UNKNOWN")
        rtt = payload.get("rtt_ms")
        drop_rate = float(payload.get("drop_rate", 0.0))
        vram_used = float(payload.get("vram_used_gb", 0.0))
        ai_vram_cap = float(payload.get("ai_vram_cap_gb", 0.0))
        cpu_percent = float(payload.get("cpu_percent", 0.0))
        status = payload.get("status", "ONLINE")

        # 1. Disconnection / Drop out / Offline Status
        if status not in ("ONLINE", "IDLE"):
            anomalies.append({
                "type": "NODE_OFFLINE",
                "severity": "CRITICAL",
                "node_id": node_id,
                "value": status,
                "message": f"Node {node_id} is in status {status}",
            })

        # 2. Latency Spike (WARNING if > threshold, HIGH if > 100ms)
        if rtt is not None and float(rtt) > self.rtt_spike_threshold_ms:
            severity = "HIGH" if float(rtt) >= 100.0 else "WARNING"
            anomalies.append({
                "type": "LATENCY_SPIKE",
                "severity": severity,
                "node_id": node_id,
                "value": float(rtt),
                "message": f"RTT {float(rtt):.2f}ms exceeds threshold {self.rtt_spike_threshold_ms}ms",
            })

        # 3. Packet Drop Burst
        if drop_rate > self.drop_threshold_percent:
            anomalies.append({
                "type": "PACKET_LOSS_BURST",
                "severity": "HIGH",
                "node_id": node_id,
                "value": drop_rate,
                "message": f"Drop rate {drop_rate:.1f}% exceeds threshold {self.drop_threshold_percent}%",
            })

        # 4. VRAM Saturation (> dynamic cap ratio)
        if ai_vram_cap > 0 and (vram_used / ai_vram_cap) > self.vram_saturation_ratio:
            ratio = vram_used / ai_vram_cap
            severity = "HIGH" if ratio >= 0.98 else "WARNING"
            anomalies.append({
                "type": "VRAM_SATURATION",
                "severity": severity,
                "node_id": node_id,
                "value": ratio,
                "message": f"VRAM usage {ratio*100:.1f}% exceeds {int(self.vram_saturation_ratio*100)}% dynamic cap",
            })

        # 5. CPU Saturation (> cpu_saturation_pct)
        if cpu_percent > self.cpu_saturation_pct:
            anomalies.append({
                "type": "CPU_SATURATION",
                "severity": "WARNING",
                "node_id": node_id,
                "value": cpu_percent,
                "message": f"CPU load {cpu_percent:.1f}% exceeds threshold {self.cpu_saturation_pct:.1f}%",
            })

        return anomalies

    def evaluate_z_score(
        self,
        node_id: str,
        current_value: float,
        buffer: TimeSeriesRingBuffer,
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate whether `current_value` is an anomaly based on z-score against historical buffer.
        Requires at least 5 historical samples.
        """
        stats = buffer.get_stats()
        if stats["count"] < 5.0 or stats["stddev"] <= 0.0001:
            return None

        z = (current_value - stats["mean"]) / stats["stddev"]
        if abs(z) >= self.z_score_threshold:
            return {
                "type": "Z_SCORE_ANOMALY",
                "severity": "WARNING" if abs(z) < 4.0 else "HIGH",
                "node_id": node_id,
                "value": round(current_value, 3),
                "z_score": round(z, 2),
                "mean": stats["mean"],
                "stddev": stats["stddev"],
                "message": f"Value {current_value:.2f} has z-score {z:.2f} (exceeds threshold {self.z_score_threshold})",
            }
        return None
