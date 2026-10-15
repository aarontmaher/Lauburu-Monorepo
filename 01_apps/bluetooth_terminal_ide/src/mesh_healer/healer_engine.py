"""
Master Mesh Healer Engine & Autonomous Escalation State Machine
Part of Canonical Mesh Fallback Terminal (bluetooth_terminal_ide).

Orchestrates the 3-stage escalation ladder:
- STAGE 1: Layer 0 IP-Less Raw Serial Lifeline (BLE GATT NUS)
- STAGE 2: Layer 1 Autonomous Bluetooth PAN Escalation (Magic packet + Shizuku BNEP)
- STAGE 3: Layer 3 SSH / Mosh High-Throughput Handoff & Watchdog
"""

from __future__ import annotations

import asyncio
import logging
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple, Union

from .nus_transport import NusTransport
from .outage_detector import MeshOutageDetector
from .protocol import OOBMessage
from .session_spawner import SessionSpawner
from .shizuku_bridge import ShizukuBridge

logger = logging.getLogger("mesh_healer.engine")


class HealerState(str, Enum):
    STAGE_0_NORMAL = "STAGE_0_NORMAL"
    STAGE_1_RAW_SERIAL = "STAGE_1_RAW_SERIAL"
    STAGE_2_PAN_ESCALATING = "STAGE_2_PAN_ESCALATING"
    STAGE_2_PAN_CONNECTED = "STAGE_2_PAN_CONNECTED"
    STAGE_3_SSH_MOSH = "STAGE_3_SSH_MOSH"

    # Convenient aliases
    STAGE_1 = "STAGE_1_RAW_SERIAL"
    STAGE_2 = "STAGE_2_PAN_ESCALATING"
    STAGE_3 = "STAGE_3_SSH_MOSH"


class MeshHealer:
    """
    Master Controller governing the Canonical Mesh Fallback Escalation Ladder.
    """

    def __init__(
        self,
        app: Optional[Any] = None,
        outage_detector: Optional[MeshOutageDetector] = None,
        shizuku_bridge: Optional[ShizukuBridge] = None,
        session_spawner: Optional[SessionSpawner] = None,
        nus_transport: Optional[NusTransport] = None,
        initial_state: HealerState = HealerState.STAGE_1_RAW_SERIAL,
        on_stage_changed: Optional[Callable[[HealerState, HealerState], Any]] = None,
        on_log_message: Optional[Callable[[str, str], Any]] = None,
    ) -> None:
        self.app = app
        self.state: HealerState = initial_state
        self.on_stage_changed = on_stage_changed
        self.on_log_message = on_log_message

        # Subsystems
        self.outage_detector = outage_detector or MeshOutageDetector(
            on_outage_detected=self._on_overlay_outage,
            on_outage_recovered=self._on_overlay_recovered,
        )
        # Ensure detector callbacks point to this engine if custom detector was passed
        self.outage_detector.on_outage_detected = self._on_overlay_outage
        self.outage_detector.on_outage_recovered = self._on_overlay_recovered

        self.shizuku_bridge = shizuku_bridge or ShizukuBridge()
        self.session_spawner = session_spawner or SessionSpawner(
            app=self.app,
            on_link_collapsed=self._on_pan_link_collapsed,
        )
        self.session_spawner.on_link_collapsed = self._on_pan_link_collapsed

        self.nus_transport = nus_transport or NusTransport(
            on_message_received=self._on_nus_message_received,
        )

        self._escalation_lock = asyncio.Lock()
        self._pan_poll_task: Optional[asyncio.Task] = None
        self.is_monitoring: bool = False

    @property
    def current_stage(self) -> HealerState:
        return self.state

    def get_state(self) -> HealerState:
        return self.state

    def _set_stage(self, new_stage: HealerState) -> None:
        if self.state != new_stage:
            old_stage = self.state
            self.state = new_stage
            self._log("info", f"State transitioned: {old_stage.value} ➡️ {new_stage.value}")
            if self.on_stage_changed:
                try:
                    self.on_stage_changed(old_stage, new_stage)
                except Exception as e:
                    logger.error(f"Error in on_stage_changed callback: {e}")
            
            # Update app UI if connected
            if self.app and hasattr(self.app, "update_healer_stage"):
                try:
                    self.app.update_healer_stage(new_stage)
                except Exception:
                    pass

    def _log(self, level: str, message: str) -> None:
        """Dispatches log message to callback and Textual log widget safely."""
        logger.info(f"[{level.upper()}] {message}")
        if self.on_log_message:
            try:
                self.on_log_message(level, message)
            except Exception as e:
                logger.error(f"Error in on_log_message callback: {e}")

        if self.app and hasattr(self.app, "log_widget") and self.app.log_widget:
            try:
                import threading
                if threading.current_thread() is threading.main_thread():
                    self.app.log_widget.write(message)
                elif hasattr(self.app, "call_from_thread"):
                    self.app.call_from_thread(self.app.log_widget.write, message)
                else:
                    self.app.log_widget.write(message)
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # Lifecycle Management
    # -------------------------------------------------------------------------

    async def start_monitoring(self) -> None:
        """Starts background outage detection probers."""
        self.is_monitoring = True
        self.outage_detector.start()
        self._log("info", "[MESH_HEALER] 🛡️ Autonomous mesh monitoring active.")

    async def stop_monitoring(self) -> None:
        """Cancels background tasks and watchdogs cleanly."""
        self.is_monitoring = False
        self.outage_detector.stop()
        if self._pan_poll_task and not self._pan_poll_task.done():
            self._pan_poll_task.cancel()
            self._pan_poll_task = None
        await self.session_spawner.terminate_session()
        await self.nus_transport.disconnect()
        self._log("info", "[MESH_HEALER] 🛑 Monitoring stopped.")

    # -------------------------------------------------------------------------
    # State Machine Transitions
    # -------------------------------------------------------------------------

    async def _on_overlay_outage(self) -> None:
        """Triggered when outage detector confirms 3 consecutive failed cycles."""
        self._log(
            "warning",
            "[MESH_HEALER] 🚨 Overlay network outage confirmed (Tailscale/Nebula offline). "
            "Autonomous escalation from Stage 1 to Stage 2 triggered.",
        )
        await self.trigger_pan_escalation(source="outage_detector")

    async def _on_overlay_recovered(self) -> None:
        """Triggered when overlay network health is restored."""
        self._log(
            "info",
            "[MESH_HEALER] 🌐 Overlay network connectivity restored.",
        )
        if self.state in [HealerState.STAGE_1_RAW_SERIAL, HealerState.STAGE_0_NORMAL]:
            self._set_stage(HealerState.STAGE_0_NORMAL)

    async def trigger_pan_escalation(self, source: str = "manual") -> bool:
        """
        Executes Dual-Mode Stage 2 Bluetooth PAN Escalation:
        Vector A: OOB Magic Packet (/nexus ENABLE_PAN) over Stage 1 BLE NUS
        Vector B: Android Edge Shizuku SDK Bridge forcing BNEP tethering
        """
        async with self._escalation_lock:
            self._set_stage(HealerState.STAGE_2_PAN_ESCALATING)
            self._log(
                "warning",
                f"[MESH_HEALER] ⚡ Escalating to Stage 2 Bluetooth PAN (Source: {source})",
            )

            # Vector A: Send magic packet over BLE NUS if connected
            if self.nus_transport.is_connected:
                magic_msg = OOBMessage(
                    id=f"pan_{int(asyncio.get_event_loop().time())}",
                    cmd="ENABLE_PAN",
                    params={"source": source, "subnet": "192.168.44.0/24"},
                )
                sent = await self.nus_transport.write_oob_message(magic_msg)
                if sent:
                    self._log(
                        "info",
                        "[MESH_HEALER] 📤 Magic packet dispatched over BLE NUS: ENABLE_PAN",
                    )
            else:
                self._log(
                    "info",
                    "[MESH_HEALER] 📤 Stage 1 BLE NUS offline; proceeding with direct Shizuku elevation.",
                )

            # Vector B: Invoke Android Edge Shizuku SDK Bridge
            target_device = "L6_Pixel_10 / L7_Samsung_S20"
            mode = "rish" if self.shizuku_bridge._resolve_rish_binary() else "adb"
            self._log(
                "info",
                f"[MESH_HEALER] 📲 Invoking Android Edge Shizuku SDK Bridge for BNEP tethering "
                f"(Device: {target_device}, Mode: {mode})",
            )

            shizuku_ok, receipt = await self.shizuku_bridge.start_bluetooth_tethering()
            self._log("info", receipt)

            # Begin polling 192.168.44.1 for Stage 3 handoff
            if not self._pan_poll_task or self._pan_poll_task.done():
                self._pan_poll_task = asyncio.create_task(self._poll_pan_reachability())

            return shizuku_ok

    async def _poll_pan_reachability(self, max_attempts: int = 30) -> None:
        """Polls 192.168.44.1 subnet reachability until confirmed, then triggers Stage 3."""
        for attempt in range(max_attempts):
            reachable, port = await self.session_spawner.probe_reachability(timeout=1.0)
            if reachable and port:
                self._set_stage(HealerState.STAGE_2_PAN_CONNECTED)
                self._log(
                    "info",
                    f"[MESH_HEALER] 🌐 Bluetooth PAN subnet 192.168.44.1:{port} verified reachable!",
                )
                await self.trigger_stage3_handoff("192.168.44.1", port)
                return
            await asyncio.sleep(1.0)

        self._log(
            "warning",
            "[MESH_HEALER] ⏳ Stage 2 PAN reachability polling timed out without response.",
        )

    async def trigger_stage3_handoff(
        self, target_ip: str = "192.168.44.1", port: int = 8022
    ) -> bool:
        """
        Executes non-blocking Stage 3 SSH / Mosh handoff without freezing Textual event loop.
        """
        self._set_stage(HealerState.STAGE_3_SSH_MOSH)
        success, receipt = await self.session_spawner.spawn_session(
            host=target_ip, port=port
        )
        self._log("info", receipt)
        return success

    async def _on_pan_link_collapsed(self) -> None:
        """
        Called when Stage 3 watchdog detects link collapse (3 consecutive misses).
        Demotes to Stage 1 and fires OOB resurrection.
        """
        self._log(
            "error",
            "[bold red]⚠️ PAN link collapsed! Demoted to Stage 1 Raw Serial Lifeline.[/]",
        )
        self._set_stage(HealerState.STAGE_1_RAW_SERIAL)

        # OOB Resurrection
        if self.nus_transport.is_connected:
            resurrect_msg = OOBMessage(
                id=f"resurrect_{int(asyncio.get_event_loop().time())}",
                cmd="ENABLE_PAN",
                params={"action": "resurrect"},
            )
            await self.nus_transport.write_oob_message(resurrect_msg)
            self._log(
                "info",
                "[MESH_HEALER] 🔄 Dispatched OOB resurrection packet over Stage 1 BLE NUS.",
            )

    def _on_nus_message_received(self, msg: Union[OOBMessage, str]) -> None:
        """Handles incoming message or OOB frame from BLE NUS."""
        if isinstance(msg, OOBMessage):
            self._log("info", f"[OOB_RX] <{msg.cmd}> {msg.params}")
            if msg.cmd == "ENABLE_PAN":
                asyncio.create_task(self.trigger_pan_escalation(source="oob_rx"))
        else:
            self._log("info", f"[NUS_RX] {msg}")

    # -------------------------------------------------------------------------
    # Command Interceptor
    # -------------------------------------------------------------------------

    async def handle_command(self, cmd_text: str) -> Optional[str]:
        """
        Intercepts /nexus and OOB commands.
        Returns response string if handled, or None to pass through.
        """
        clean = cmd_text.strip()

        # Intercept /nexus ENABLE_PAN
        if clean in ["/nexus ENABLE_PAN", "/dispatch ENABLE_PAN", "ENABLE_PAN"]:
            ok = await self.trigger_pan_escalation(source="nexus_command")
            return f"[MESH_HEALER] Stage 2 PAN Escalation triggered (Result: {'SUCCESS' if ok else 'DISPATCHED'})."

        # Status inspection
        if clean in ["/nexus STATUS", "/status", "/nexus STAGE"]:
            return (
                f"[MESH_HEALER] Status: Stage={self.state.value} | "
                f"BLE_NUS={'CONNECTED' if self.nus_transport.is_connected else 'DISCONNECTED'} | "
                f"OutageDetected={self.outage_detector.is_outage_detected} | "
                f"SessionActive={self.session_spawner.is_session_active}"
            )

        # Test demotion trigger
        if clean == "/nexus DEMOTE_STAGE_1":
            await self._on_pan_link_collapsed()
            return "[MESH_HEALER] Manually triggered demotion to Stage 1."

        return None
