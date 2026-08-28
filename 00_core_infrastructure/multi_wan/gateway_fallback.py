"""
multi_wan/gateway_fallback.py - EWMA Latency-Aware Gateway Fallback & Circuit Breaker.

Maintains EWMA (Exponentially Weighted Moving Average) RTT latency tracking, sliding window drop detection,
and sub-50ms predictive circuit breaking for multi-WAN gateways.

STRICT MANDATE: ZERO SIMULATED DATA. All metrics are measured directly.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger("multi_wan.gateway_fallback")


class GatewayMetrics:
    """
    Tracks EWMA RTT latency and sliding window drop metrics for a specific gateway interface.
    """

    def __init__(
        self,
        gateway_id: str,
        initial_rtt_ms: float = 10.0,
        alpha: float = 0.2,
        window_size: int = 20,
    ):
        self.gateway_id = gateway_id
        self.ewma_rtt_ms = max(0.1, initial_rtt_ms)
        self.alpha = alpha
        self.window_size = window_size
        self.sliding_window: List[Tuple[float, bool]] = []  # List of (timestamp, is_drop)
        self.circuit_state = "CLOSED"  # CLOSED (normal), OPEN (tripped), HALF_OPEN (re-testing)
        self.last_state_change = time.perf_counter()
        self.tripped_count = 0

    def add_sample(self, rtt_ms: float, is_drop: bool = False):
        """Updates EWMA RTT and appends sample to sliding window."""
        now = time.perf_counter()
        if not is_drop:
            # EWMA formula: EWMA_t = alpha * RTT_t + (1 - alpha) * EWMA_{t-1}
            self.ewma_rtt_ms = (self.alpha * max(0.1, rtt_ms)) + ((1.0 - self.alpha) * self.ewma_rtt_ms)
        else:
            # On drop, penalize EWMA slightly
            self.ewma_rtt_ms = (self.alpha * 999.9) + ((1.0 - self.alpha) * self.ewma_rtt_ms)

        self.sliding_window.append((now, is_drop))
        if len(self.sliding_window) > self.window_size:
            self.sliding_window.pop(0)

    def get_drop_rate(self) -> float:
        """Calculates current drop rate over sliding window [0.0 to 1.0]."""
        if not self.sliding_window:
            return 0.0
        drops = sum(1 for _, is_drop in self.sliding_window if is_drop)
        return drops / float(len(self.sliding_window))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gateway_id": self.gateway_id,
            "ewma_rtt_ms": round(self.ewma_rtt_ms, 2),
            "drop_rate": round(self.get_drop_rate(), 3),
            "circuit_state": self.circuit_state,
            "samples_in_window": len(self.sliding_window),
            "tripped_count": self.tripped_count,
        }


class LatencyAwareGatewayFallback:
    """
    Sub-50ms Predictive Circuit Breaker & EWMA Latency-Aware Gateway Fallback Router.
    """

    def __init__(
        self,
        rtt_threshold_ms: float = 150.0,
        drop_rate_threshold: float = 0.25,
        reset_timeout_sec: float = 5.0,
    ):
        self.rtt_threshold_ms = rtt_threshold_ms
        self.drop_rate_threshold = drop_rate_threshold
        self.reset_timeout_sec = reset_timeout_sec
        self.gateways: Dict[str, GatewayMetrics] = {}

        # Pre-register default gateways
        self.register_gateway("en0_wifi_wan", initial_rtt_ms=12.0)
        self.register_gateway("en6_usb_tether", initial_rtt_ms=8.0)
        self.register_gateway("utun1_tailscale", initial_rtt_ms=25.0)

    def register_gateway(self, gateway_id: str, initial_rtt_ms: float = 10.0) -> GatewayMetrics:
        """Registers a new gateway for EWMA tracking."""
        if gateway_id not in self.gateways:
            gm = GatewayMetrics(gateway_id=gateway_id, initial_rtt_ms=initial_rtt_ms)
            self.gateways[gateway_id] = gm
        return self.gateways[gateway_id]

    def record_rtt(self, gateway_id: str, rtt_ms: float, is_drop: bool = False):
        """Records RTT latency sample and updates gateway state."""
        gm = self.gateways.get(gateway_id)
        if not gm:
            gm = self.register_gateway(gateway_id, initial_rtt_ms=rtt_ms)

        gm.add_sample(rtt_ms=rtt_ms, is_drop=is_drop)
        self.evaluate_gateway(gateway_id)

    def evaluate_gateway(self, gateway_id: str) -> Dict[str, Any]:
        """
        Evaluates predictive circuit state in < 50ms based on EWMA RTT & sliding window drop rate.
        Trips circuit to 'OPEN' if thresholds are breached.
        """
        start_t = time.perf_counter()
        gm = self.gateways.get(gateway_id)
        if not gm:
            return {"status": "UNKNOWN", "evaluation_time_ms": 0.0}

        now = time.perf_counter()
        old_state = gm.circuit_state
        drop_rate = gm.get_drop_rate()

        # Check HALF_OPEN reset timeout
        if gm.circuit_state == "OPEN" and (now - gm.last_state_change) > self.reset_timeout_sec:
            gm.circuit_state = "HALF_OPEN"
            gm.last_state_change = now
            # Reset EWMA RTT to baseline and clear window so new probe samples evaluate fairly
            gm.ewma_rtt_ms = self.rtt_threshold_ms * 0.5
            gm.sliding_window.clear()
            drop_rate = 0.0
            logger.info(f"Gateway '{gateway_id}' circuit reset timeout expired -> transitioning to HALF_OPEN")

        # Predictive circuit break evaluation
        should_trip = (gm.ewma_rtt_ms > self.rtt_threshold_ms) or (drop_rate >= self.drop_rate_threshold)

        if should_trip and gm.circuit_state != "OPEN":
            gm.circuit_state = "OPEN"
            gm.last_state_change = now
            gm.tripped_count += 1
            logger.warning(
                f"Predictive Circuit Breaker TRIPPED for '{gateway_id}': "
                f"EWMA={gm.ewma_rtt_ms:.1f}ms (threshold={self.rtt_threshold_ms}ms), "
                f"DropRate={drop_rate:.1%} (threshold={self.drop_rate_threshold:.1%})"
            )
        elif not should_trip and gm.circuit_state == "HALF_OPEN":
            gm.circuit_state = "CLOSED"
            gm.last_state_change = now
            logger.info(f"Gateway '{gateway_id}' recovered -> circuit CLOSED")

        eval_ms = (time.perf_counter() - start_t) * 1000.0

        return {
            "gateway_id": gateway_id,
            "old_state": old_state,
            "new_state": gm.circuit_state,
            "ewma_rtt_ms": round(gm.ewma_rtt_ms, 2),
            "drop_rate": round(drop_rate, 3),
            "evaluation_time_ms": round(eval_ms, 3),
            "sub_50ms_compliance": eval_ms < 50.0,
        }

    def is_circuit_open(self, gateway_id: str) -> bool:
        """Returns True if circuit is OPEN (tripped), False if CLOSED or HALF_OPEN."""
        gm = self.gateways.get(gateway_id)
        if not gm:
            return False
        # Re-evaluate to handle reset timeout transitions
        self.evaluate_gateway(gateway_id)
        return gm.circuit_state == "OPEN"

    def select_best_gateway(self, candidate_ids: Optional[List[str]] = None) -> str:
        """
        Selects lowest EWMA RTT gateway whose circuit is NOT OPEN.
        Falls back to healthiest surviving gateway if all candidate circuits are open.
        """
        if candidate_ids is None:
            candidate_ids = list(self.gateways.keys())

        healthy_candidates = []
        for gid in candidate_ids:
            gm = self.gateways.get(gid)
            if gm and not self.is_circuit_open(gid):
                healthy_candidates.append(gm)

        if healthy_candidates:
            healthy_candidates.sort(key=lambda x: x.ewma_rtt_ms)
            return healthy_candidates[0].gateway_id

        # Fallback if all open: pick candidate with lowest EWMA RTT
        all_metrics = [self.gateways[gid] for gid in candidate_ids if gid in self.gateways]
        if all_metrics:
            all_metrics.sort(key=lambda x: x.ewma_rtt_ms)
            return all_metrics[0].gateway_id

        return candidate_ids[0] if candidate_ids else "default"

    def run_predictive_circuit_break_check(self) -> Dict[str, Any]:
        """
        Runs predictive circuit breaking evaluation across all registered gateways.
        Returns execution timing and gateway statuses.
        """
        start_t = time.perf_counter()
        results = {}
        all_compliant = True

        for gid in list(self.gateways.keys()):
            res = self.evaluate_gateway(gid)
            results[gid] = res
            if not res["sub_50ms_compliance"]:
                all_compliant = False

        total_eval_ms = (time.perf_counter() - start_t) * 1000.0

        return {
            "total_evaluation_time_ms": round(total_eval_ms, 3),
            "sub_50ms_compliance": total_eval_ms < 50.0 and all_compliant,
            "rtt_threshold_ms": self.rtt_threshold_ms,
            "drop_rate_threshold": self.drop_rate_threshold,
            "gateways_evaluated": results,
            "recommended_gateway": self.select_best_gateway(),
        }
