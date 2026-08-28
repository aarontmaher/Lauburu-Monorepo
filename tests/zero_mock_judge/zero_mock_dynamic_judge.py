#!/usr/bin/env python3
"""
Zero-Mock Dynamic Runtime Judge
===============================
Runtime verification engine that samples live HTTP/WebSocket telemetry endpoints,
computes statistical zero-variance metrics, and correlates reported network
throughput against OS kernel interface byte counters.

Detection Capabilities:
- Zero-Variance Detection: Detects flat-line / static telemetry values (e.g. latency always 0.28ms, CPU always 12.5%).
- Cross-Verification: Correlates reported throughput against OS kernel network statistics (/proc/net/dev or netstat).
- Synthetic Payload Inspection: Detects canned mock JSON responses on live endpoints.
"""

import json
import math
import os
import platform
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set


# Metrics that naturally exhibit ambient jitter and must not have zero variance over multiple samples
JITTER_MANDATORY_METRICS: Set[str] = {
    "latency", "latency_ms", "ping", "ping_ms", "rtt", "rtt_ms",
    "cpu", "cpu_pct", "cpu_percent", "cpu_load", "load", "loadavg",
    "throughput", "throughput_mbps", "speed_mbps", "tx_bytes", "rx_bytes",
    "free_memory_mb", "free_memory", "temperature_c"
}

# Fields that are naturally constant or discrete (exempt from zero-variance checks)
DISCRETE_CONSTANT_FIELDS: Set[str] = {
    "port", "port_number", "id", "node_id", "name", "ip", "version",
    "total_memory_mb", "cores", "device_count", "devices_total", "max_speed_mbps"
}


@dataclass
class MetricSample:
    sample_index: int
    timestamp: float
    endpoint: str
    status_code: int
    raw_payload: Any
    extracted_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class MetricVarianceStat:
    metric_name: str
    sample_count: int
    values: List[float]
    mean: float
    variance: float
    std_dev: float
    min_val: float
    max_val: float
    is_zero_variance: bool
    is_jitter_mandatory: bool
    verdict: str  # PASS, SUSPECT_MOCK_DATA, EXEMPT_CONSTANT
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class KernelByteCorrelation:
    interface: str
    bytes_delta: int
    packets_delta: int
    duration_seconds: float
    reported_throughput_mbps: float
    kernel_measured_mbps: float
    is_correlated: bool
    verdict: str
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class KernelInterfaceProbe:
    """Reads real-time OS kernel network counters."""

    @staticmethod
    def get_interface_counters(interface: Optional[str] = None) -> Dict[str, Dict[str, int]]:
        """
        Returns {interface_name: {'rx_bytes': int, 'tx_bytes': int, 'rx_packets': int, 'tx_packets': int}}
        """
        counters: Dict[str, Dict[str, int]] = {}
        system = platform.system()

        if system == "Linux" and os.path.exists("/proc/net/dev"):
            try:
                with open("/proc/net/dev", "r") as f:
                    lines = f.readlines()
                for line in lines[2:]:
                    parts = line.strip().split(":")
                    if len(parts) == 2:
                        iface = parts[0].strip()
                        fields = parts[1].split()
                        rx_bytes = int(fields[0])
                        rx_packets = int(fields[1])
                        tx_bytes = int(fields[8])
                        tx_packets = int(fields[9])
                        counters[iface] = {
                            "rx_bytes": rx_bytes,
                            "tx_bytes": tx_bytes,
                            "rx_packets": rx_packets,
                            "tx_packets": tx_packets,
                            "total_bytes": rx_bytes + tx_bytes
                        }
            except Exception:
                pass
        elif system == "Darwin":
            # macOS netstat -ibn
            try:
                out = subprocess.check_output(["netstat", "-ibn"], text=True, stderr=subprocess.DEVNULL)
                for line in out.splitlines()[1:]:
                    parts = line.split()
                    if len(parts) >= 10 and parts[0] != "Name":
                        iface = parts[0]
                        # Look for IPv4 or Link rows with byte counters
                        try:
                            # Typical macOS netstat -ibn cols: Name Mtu Network Address Ipkts Ierrs Ibytes Opkts Oerrs Obytes
                            # Often: parts[6] = Ibytes, parts[9] = Obytes
                            if len(parts) >= 10:
                                ibytes = int(parts[6]) if parts[6].isdigit() else 0
                                obytes = int(parts[9]) if parts[9].isdigit() else 0
                                if iface not in counters or (ibytes + obytes) > counters[iface]["total_bytes"]:
                                    counters[iface] = {
                                        "rx_bytes": ibytes,
                                        "tx_bytes": obytes,
                                        "rx_packets": int(parts[4]) if parts[4].isdigit() else 0,
                                        "tx_packets": int(parts[7]) if parts[7].isdigit() else 0,
                                        "total_bytes": ibytes + obytes
                                    }
                        except (ValueError, IndexError):
                            continue
            except Exception:
                pass

        if interface and interface in counters:
            return {interface: counters[interface]}
        return counters


class ZeroMockDynamicJudge:
    """Dynamic runtime judge for zero-variance and kernel-level verification."""

    def __init__(self, timeout: float = 3.0):
        self.timeout = timeout

    def extract_numeric_metrics(self, data: Any, prefix: str = "") -> Dict[str, float]:
        """Recursively extracts all numeric values with flat metric names."""
        metrics: Dict[str, float] = {}

        if isinstance(data, dict):
            for k, v in data.items():
                k_norm = k.strip().lower()
                metric_key = f"{prefix}.{k_norm}" if prefix else k_norm

                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    metrics[metric_key] = float(v)
                elif isinstance(v, str):
                    # Check if numeric string e.g. "0.28ms" or "10.5"
                    clean_str = v.strip()
                    m_num = re.match(r"^([0-9]+(\.[0-9]+)?)\s*(ms|us|s|mbps|kbps|gbps|%)?$", clean_str, re.I)
                    if m_num:
                        try:
                            metrics[metric_key] = float(m_num.group(1))
                        except ValueError:
                            pass
                elif isinstance(v, (dict, list)):
                    metrics.update(self.extract_numeric_metrics(v, metric_key))
        elif isinstance(data, list):
            for idx, item in enumerate(data):
                item_prefix = f"{prefix}[{idx}]"
                metrics.update(self.extract_numeric_metrics(item, item_prefix))

        return metrics

    def fetch_sample(self, endpoint_url: str, sample_idx: int) -> MetricSample:
        """Fetches a single HTTP JSON sample."""
        req = urllib.request.Request(
            endpoint_url,
            headers={"User-Agent": "ZeroMockDynamicJudge/1.0", "Accept": "application/json"}
        )
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status_code = resp.status
                body = resp.read().decode("utf-8")
                try:
                    payload = json.loads(body)
                except json.JSONDecodeError:
                    payload = {"raw_text": body}
                metrics = self.extract_numeric_metrics(payload)
                return MetricSample(
                    sample_index=sample_idx,
                    timestamp=t0,
                    endpoint=endpoint_url,
                    status_code=status_code,
                    raw_payload=payload,
                    extracted_metrics=metrics
                )
        except urllib.error.HTTPError as e:
            return MetricSample(
                sample_index=sample_idx,
                timestamp=t0,
                endpoint=endpoint_url,
                status_code=e.code,
                raw_payload={"error": str(e)},
                extracted_metrics={}
            )
        except Exception as e:
            return MetricSample(
                sample_index=sample_idx,
                timestamp=t0,
                endpoint=endpoint_url,
                status_code=0,
                raw_payload={"error": str(e)},
                extracted_metrics={}
            )

    def sample_endpoint(self, endpoint_url: str, sample_count: int = 5, interval_seconds: float = 0.5) -> List[MetricSample]:
        """Gathers multiple time-series samples from an endpoint."""
        samples: List[MetricSample] = []
        for i in range(sample_count):
            sample = self.fetch_sample(endpoint_url, i + 1)
            samples.append(sample)
            if i < sample_count - 1:
                time.sleep(interval_seconds)
        return samples

    def analyze_variance(self, samples: List[MetricSample]) -> Dict[str, MetricVarianceStat]:
        """Computes statistical variance across all extracted numeric metrics."""
        if not samples:
            return {}

        # Aggregate time series per metric key
        series_by_metric: Dict[str, List[float]] = {}
        for s in samples:
            for k, v in s.extracted_metrics.items():
                if k not in series_by_metric:
                    series_by_metric[k] = []
                series_by_metric[k].append(v)

        stats: Dict[str, MetricVarianceStat] = {}

        for metric_name, values in series_by_metric.items():
            n = len(values)
            if n < 2:
                continue

            mean = sum(values) / n
            variance = sum((x - mean) ** 2 for x in values) / n
            std_dev = math.sqrt(variance)
            min_v = min(values)
            max_v = max(values)
            is_zero_var = (max_v == min_v) or (variance < 1e-9) or math.isclose(min_v, max_v, abs_tol=1e-7)

            # Check if this metric is in mandatory jitter category
            short_name = metric_name.split(".")[-1].split("[")[0]
            is_jitter = any(k in short_name for k in JITTER_MANDATORY_METRICS)
            is_discrete = any(k in short_name for k in DISCRETE_CONSTANT_FIELDS)

            if is_zero_var and is_jitter and not is_discrete and mean > 0:
                verdict = "SUSPECT_MOCK_DATA"
                message = f"Zero variance detected on physical metric '{metric_name}' (constant {mean:.4f} across {n} polls). Likely static mock data."
            elif is_discrete:
                verdict = "EXEMPT_CONSTANT"
                message = f"Constant value on discrete field '{metric_name}' ({mean:.1f}). Normal behavior."
            else:
                verdict = "PASS"
                message = f"Natural variance observed: std_dev={std_dev:.4f}, range=[{min_v}, {max_v}]."

            stats[metric_name] = MetricVarianceStat(
                metric_name=metric_name,
                sample_count=n,
                values=values,
                mean=round(mean, 4),
                variance=round(variance, 6),
                std_dev=round(std_dev, 4),
                min_val=min_v,
                max_val=max_v,
                is_zero_variance=is_zero_var,
                is_jitter_mandatory=is_jitter,
                verdict=verdict,
                message=message
            )

        return stats

    def audit_endpoint(self, endpoint_url: str, sample_count: int = 5, interval_seconds: float = 0.5) -> Dict[str, Any]:
        """Performs complete dynamic zero-variance audit of an endpoint."""
        samples = self.sample_endpoint(endpoint_url, sample_count, interval_seconds)
        stats = self.analyze_variance(samples)

        mock_violations = [s for s in stats.values() if s.verdict == "SUSPECT_MOCK_DATA"]
        successful_samples = [s for s in samples if s.status_code == 200]

        is_alive = len(successful_samples) > 0
        is_clean = is_alive and (len(mock_violations) == 0)

        return {
            "endpoint": endpoint_url,
            "status": "ONLINE" if is_alive else "OFFLINE",
            "samples_collected": len(samples),
            "successful_samples": len(successful_samples),
            "total_metrics_tracked": len(stats),
            "mock_violations_count": len(mock_violations),
            "verdict": "ZERO_MOCK_CERTIFIED" if is_clean else ("SUSPECT_SYNTHETIC_DATA" if mock_violations else "OFFLINE_OR_UNAVAILABLE"),
            "variance_statistics": {k: v.to_dict() for k, v in stats.items()},
            "violations": [v.to_dict() for v in mock_violations]
        }

    def correlate_kernel_throughput(self, endpoint_url: str, duration: float = 2.0, interface: Optional[str] = None) -> KernelByteCorrelation:
        """
        Measures OS kernel byte counters over duration while pinging endpoint_url,
        checking if reported network activity matches physical kernel socket counters.
        """
        # Step 1: Pre-measurement kernel stats
        pre_counters = KernelInterfaceProbe.get_interface_counters(interface)

        t0 = time.time()
        sample = self.fetch_sample(endpoint_url, 1)
        time.sleep(duration)
        t1 = time.time()

        post_counters = KernelInterfaceProbe.get_interface_counters(interface)

        total_rx_delta = 0
        total_tx_delta = 0
        target_iface = interface or "all"

        for iface, post in post_counters.items():
            pre = pre_counters.get(iface, {"rx_bytes": 0, "tx_bytes": 0, "rx_packets": 0, "tx_packets": 0})
            rx_diff = max(0, post.get("rx_bytes", 0) - pre.get("rx_bytes", 0))
            tx_diff = max(0, post.get("tx_bytes", 0) - pre.get("tx_bytes", 0))
            total_rx_delta += rx_diff
            total_tx_delta += tx_diff

        elapsed = max(0.001, t1 - t0)
        total_bytes = total_rx_delta + total_tx_delta
        measured_mbps = (total_bytes * 8) / (elapsed * 1_000_000)

        # Check reported throughput in payload
        reported_tp = 0.0
        if sample.extracted_metrics:
            for k, v in sample.extracted_metrics.items():
                if "throughput" in k or "speed" in k:
                    reported_tp = v
                    break

        # Verification logic
        if (reported_tp > 10.0 and (total_bytes < 100 or measured_mbps < reported_tp * 0.2)) or (reported_tp > 50.0 and total_bytes < 100):
            is_correlated = False
            verdict = "FABRICATED_THROUGHPUT_VIOLATION"
            msg = f"Endpoint claimed {reported_tp:.2f} Mbps, but kernel recorded only {total_bytes} bytes ({measured_mbps:.4f} Mbps) over {elapsed:.2f}s."
        else:
            is_correlated = True
            verdict = "CORRELATED_TRUTHFUL"
            msg = f"Kernel recorded {total_bytes} bytes ({measured_mbps:.4f} Mbps) over {elapsed:.2f}s."

        return KernelByteCorrelation(
            interface=target_iface,
            bytes_delta=total_bytes,
            packets_delta=0,
            duration_seconds=round(elapsed, 3),
            reported_throughput_mbps=round(reported_tp, 2),
            kernel_measured_mbps=round(measured_mbps, 4),
            is_correlated=is_correlated,
            verdict=verdict,
            message=msg
        )


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Zero-Mock Dynamic Runtime Judge")
    parser.add_argument("--url", type=str, required=True, help="Target HTTP/REST endpoint URL")
    parser.add_argument("--samples", type=int, default=5, help="Number of samples to collect (default: 5)")
    parser.add_argument("--interval", type=float, default=0.5, help="Interval between samples in seconds (default: 0.5)")
    parser.add_argument("--check-kernel", action="store_true", help="Correlate throughput with kernel interface counters")
    parser.add_argument("--interface", type=str, default=None, help="Specific network interface for kernel stats")
    parser.add_argument("--json-output", type=str, default=None, help="Output JSON path")

    args = parser.parse_args()

    judge = ZeroMockDynamicJudge()
    print(f"\n=======================================================")
    print(f" ZERO-MOCK DYNAMIC RUNTIME JUDGE")
    print(f"=======================================================")
    print(f" Target Endpoint: {args.url}")
    print(f" Sampling:        {args.samples} samples @ {args.interval}s interval\n")

    report = judge.audit_endpoint(args.url, sample_count=args.samples, interval_seconds=args.interval)

    print(f" Status:          {report['status']}")
    print(f" Verdict:         {report['verdict']}")
    print(f" Metrics Tracked: {report['total_metrics_tracked']}")
    print(f" Mock Violations: {report['mock_violations_count']}")
    print(f"-------------------------------------------------------")

    for k, v in report["variance_statistics"].items():
        print(f" - {k:<30} mean={v['mean']:<10} std_dev={v['std_dev']:<10} [{v['verdict']}]")

    if args.check_kernel:
        print(f"\n--- Kernel Byte Correlation ---")
        corr = judge.correlate_kernel_throughput(args.url, duration=1.0, interface=args.interface)
        print(f" Kernel Verdict:  {corr.verdict}")
        print(f" Detail:          {corr.message}")
        report["kernel_correlation"] = corr.to_dict()

    if args.json_output:
        out_path = Path(args.json_output).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\nSaved report to: {out_path}")

    sys.exit(0 if report["verdict"] == "ZERO_MOCK_CERTIFIED" else 1)


if __name__ == "__main__":
    main()
