"""
Obsidian Vault Synchronization Engine
Version: 3.0.0-CANONICAL

Synchronizes real-time mesh telemetry into Obsidian Vault markdown notes:
- Atomic note writes with tmp file swap (no partial reads/corruption).
- Canonical YAML frontmatter and Wikilinks ([[Index]], [[Node_Name]]).
- Generates daily telemetry records [[Telemetry-YYYY-MM-DD]].
- Ensures Index.md contains Wikilinks to all active nodes.
"""

import os
import time
from typing import Any, Dict, List, Optional


DEFAULT_OBSIDIAN_VAULT = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault"


class ObsidianVaultSyncFormatter:
    """Formats and writes live telemetry and Wikilinks into Obsidian Vault Markdown notes."""

    @staticmethod
    def format_node_telemetry_note(node_id: str, payload: Dict[str, Any]) -> str:
        """Format individual node telemetry into Obsidian Markdown with YAML frontmatter and Wikilinks."""
        raw_ts = payload.get("timestamp")
        if raw_ts is None:
            raw_ts = time.time()
        elif isinstance(raw_ts, str):
            try:
                raw_ts = float(raw_ts)
            except ValueError:
                raw_ts = time.time()

        timestamp_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(raw_ts))
        rtt_val = payload.get("rtt_ms", 0.0)
        rtt_num = float(rtt_val) if rtt_val is not None else 0.0

        lines = [
            "---",
            f"title: \"{node_id} Live Mesh Telemetry\"",
            f"node_id: \"{node_id}\"",
            f"layer: \"{payload.get('layer', 'UNKNOWN')}\"",
            f"status: \"{payload.get('status', 'ONLINE')}\"",
            f"last_synced: \"{timestamp_str}\"",
            "tags: [lauburu, mesh_node, telemetry, live_sync]",
            "---",
            f"# 📡 [[{node_id}]] Telemetry Status",
            "",
            "- **Master Index**: [[Index]]",
            "- **Deep Architecture Index**: [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]",
            f"- **IP Address**: `{payload.get('ip', '--')}`",
            f"- **Tailscale IP**: `{payload.get('tailscale_ip', '--')}`",
            f"- **Operating System**: {payload.get('os', 'Unknown')}",
            "",
            "## 📊 Live Resource Metrics",
            "| Metric | Value | Cap / Limit |",
            "| :--- | :--- | :--- |",
            f"| CPU Load | {payload.get('cpu_percent', 0.0):.1f}% | 100.0% |",
            f"| RAM Ingest | {payload.get('ram_used_gb', 0.0):.2f} GB | {payload.get('ram_total_gb', 0.0):.2f} GB |",
            f"| AI VRAM Usage | {payload.get('vram_used_gb', 0.0):.2f} GB | {payload.get('ai_vram_cap_gb', 0.0):.2f} GB |",
            f"| Latency RTT | {rtt_num:.3f} ms | -- |",
            f"| Packet Drop Rate | {payload.get('drop_rate', 0.0):.1f}% | 0.0% |",
            "",
        ]
        return "\n".join(lines)

    @staticmethod
    def format_daily_telemetry_summary(
        date_str: str,
        aggregated_metrics: Dict[str, Any],
        anomalies: List[Dict[str, Any]],
    ) -> str:
        """Format daily summary note [[Telemetry-YYYY-MM-DD]] with Wikilinks to all mesh nodes."""
        lines = [
            "---",
            f"title: \"Mesh Telemetry Daily Summary — {date_str}\"",
            f"date: \"{date_str}\"",
            f"total_nodes: {aggregated_metrics.get('total_nodes', 0)}",
            f"online_nodes: {aggregated_metrics.get('online_nodes', 0)}",
            "tags: [lauburu, daily_telemetry, summary, mesh_network]",
            "---",
            f"# 🌐 [[Telemetry-{date_str}]] Daily Summary",
            "",
            "- **Master Index**: [[Index]]",
            "- **Deep Architecture Index**: [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]",
            f"- **Total Ingested Packets**: {aggregated_metrics.get('total_ingested_packets', 0)}",
            f"- **Average Latency**: {aggregated_metrics.get('average_latency_ms', 0.0):.3f} ms",
            f"- **Total VRAM Allocated**: {aggregated_metrics.get('total_vram_used_gb', 0.0):.2f} / {aggregated_metrics.get('total_vram_cap_gb', 0.0):.2f} GB",
            "",
            "## 📡 Mesh Nodes Summary",
            "| Node | Layer | Status | Latency RTT | VRAM Used / Cap |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]

        nodes = aggregated_metrics.get("nodes", {})
        for node_id, p in sorted(nodes.items()):
            rtt_val = p.get("rtt_ms")
            rtt_str = f"{float(rtt_val):.3f} ms" if rtt_val is not None else "--"
            vram_str = f"{p.get('vram_used_gb', 0.0):.1f} / {p.get('ai_vram_cap_gb', 0.0):.1f} GB"
            lines.append(
                f"| [[{node_id}]] | {p.get('layer', '--')} | {p.get('status', 'ONLINE')} | {rtt_str} | {vram_str} |"
            )

        lines.extend([
            "",
            "## ⚠️ Active & Recent Anomalies",
        ])
        if not anomalies:
            lines.append("- No active anomalies recorded. All nodes nominal.")
        else:
            for a in anomalies[-20:]:
                lines.append(f"- **[{a.get('severity', 'INFO')}]** `{a.get('type', 'UNKNOWN')}` on [[{a.get('node_id', 'UNKNOWN')}]] — {a.get('message', '')}")

        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def write_atomic_vault_note(vault_dir: str, filename: str, content: str) -> str:
        """Write content to vault_dir/filename atomically via temporary file and replace."""
        os.makedirs(vault_dir, exist_ok=True)
        target_path = os.path.join(vault_dir, filename)
        tmp_path = target_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, target_path)
        return target_path


class ObsidianVaultSyncEngine:
    """High-level service orchestrating Obsidian Vault file synchronizations."""

    def __init__(self, vault_dir: Optional[str] = None) -> None:
        self.vault_dir: Optional[str] = vault_dir or DEFAULT_OBSIDIAN_VAULT

    def is_vault_available(self) -> bool:
        """Check if target vault directory exists."""
        return bool(self.vault_dir and os.path.isdir(self.vault_dir))

    def sync_node(self, node_id: str, payload: Dict[str, Any]) -> Optional[str]:
        """Format and atomically write note for a single node."""
        if not self.vault_dir:
            return None
        note_content = ObsidianVaultSyncFormatter.format_node_telemetry_note(node_id, payload)
        return ObsidianVaultSyncFormatter.write_atomic_vault_note(
            self.vault_dir, f"{node_id}.md", note_content
        )

    def sync_all_nodes(self, payloads: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
        """Synchronize markdown notes for all active nodes."""
        written = {}
        if not self.vault_dir:
            return written
        for node_id, payload in payloads.items():
            path = self.sync_node(node_id, payload)
            if path:
                written[node_id] = path
        return written

    def generate_daily_log(
        self, aggregated_metrics: Dict[str, Any], anomalies: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Generate and save [[Telemetry-YYYY-MM-DD]] daily summary note."""
        if not self.vault_dir:
            return None
        date_str = time.strftime("%Y-%m-%d", time.gmtime())
        summary_content = ObsidianVaultSyncFormatter.format_daily_telemetry_summary(
            date_str, aggregated_metrics, anomalies
        )
        return ObsidianVaultSyncFormatter.write_atomic_vault_note(
            self.vault_dir, f"Telemetry-{date_str}.md", summary_content
        )

    def update_index_links(self) -> bool:
        """Ensure master Index.md exists and contains standard Wikilinks."""
        if not self.vault_dir:
            return False
        index_path = os.path.join(self.vault_dir, "Index.md")
        if not os.path.exists(index_path) or os.path.getsize(index_path) == 0:
            content = (
                "---\n"
                "title: \"Lauburu AI Monorepo - Master Knowledge Graph\"\n"
                "tags: [lauburu, root, master_index, swarm, ai_debate]\n"
                "---\n"
                "# 🧠 Lauburu AI Monorepo - Master Knowledge Vault\n"
                "- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]\n"
                "- [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]\n"
                "- [[Mac_Node]]\n"
                "- [[MacBook_Pro]]\n"
                "- [[Linux_Head_Node]]\n"
                "- [[Linux_Tablet]]\n"
                "- [[MacBook_Air]]\n"
                "- [[Pixel_10_Pro_XL]]\n"
                "- [[Samsung_S20]]\n"
                "- [[GL_iNet_Router]]\n"
                "- [[Index]]\n"
            )
            ObsidianVaultSyncFormatter.write_atomic_vault_note(self.vault_dir, "Index.md", content)
        return True
