"""
Nordic UART Service (NUS) Async BLE Transport Manager
Part of Canonical Mesh Fallback Terminal (bluetooth_terminal_ide).

Manages BLE GATT connections, safe paced MTU-aware writes, and stream deframed
incoming notifications without cross-thread event loop conflicts.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, List, Optional, Union

from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

from .protocol import (
    NUS_RX_UUID,
    NUS_SERVICE_UUID,
    NUS_TX_UUID,
    PACING_DELAY_SECONDS,
    NusStreamDeframer,
    OOBMessage,
    assert_not_tunneling,
    calculate_chunk_size,
    chunk_payload,
)

logger = logging.getLogger("mesh_healer.nus_transport")


class NusTransport:
    """
    Asynchronous session manager for Nordic UART Service (NUS) over BLE GATT.
    Enforces paced MTU chunking and stream deframing.
    """

    def __init__(
        self,
        on_message_received: Optional[Callable[[Union[OOBMessage, str]], None]] = None,
        on_disconnect: Optional[Callable[[], None]] = None,
    ) -> None:
        self.client: Optional[BleakClient] = None
        self.target_address: Optional[str] = None
        self.is_connected: bool = False
        self.deframer = NusStreamDeframer()
        self.on_message_received = on_message_received
        self.on_disconnect = on_disconnect
        self._write_lock = asyncio.Lock()

    def get_mtu_size(self) -> int:
        """Returns the negotiated MTU size from the client, or 23 as default."""
        if self.client and hasattr(self.client, "mtu_size") and self.client.mtu_size:
            return self.client.mtu_size
        return 23

    async def connect(self, address: str, timeout: float = 10.0) -> bool:
        """Connects to peripheral device by BLE address/UUID."""
        self.target_address = address
        try:
            self.client = BleakClient(
                address,
                disconnected_callback=self._handle_disconnect,
                timeout=timeout,
            )
            await self.client.connect()
            self.is_connected = self.client.is_connected
            if self.is_connected:
                # Start notifications on NUS TX characteristic
                await self.client.start_notify(NUS_TX_UUID, self._on_gatt_notification)
                logger.info(f"Connected to BLE NUS peripheral: {address} (MTU: {self.get_mtu_size()})")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to connect to BLE NUS peripheral {address}: {e}")
            self.is_connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnects cleanly from the peripheral."""
        self.is_connected = False
        if self.client:
            try:
                if self.client.is_connected:
                    await self.client.stop_notify(NUS_TX_UUID)
                    await self.client.disconnect()
            except Exception as e:
                logger.warning(f"Error during BLE disconnect: {e}")
            finally:
                self.client = None

    def _handle_disconnect(self, client: BleakClient) -> None:
        """Bleak disconnected callback."""
        self.is_connected = False
        logger.warning(f"BLE peripheral {self.target_address} disconnected.")
        if self.on_disconnect:
            try:
                self.on_disconnect()
            except Exception as e:
                logger.error(f"Error in on_disconnect callback: {e}")

    def _on_gatt_notification(self, sender: Any, data: bytearray) -> None:
        """Receives incoming BLE GATT notification chunks and feeds the deframer."""
        frames = self.deframer.feed(bytes(data))
        for frame in frames:
            msg = OOBMessage.deserialize(frame)
            dispatch_item = msg if msg is not None else frame
            if self.on_message_received:
                try:
                    self.on_message_received(dispatch_item)
                except Exception as e:
                    logger.error(f"Error in on_message_received callback: {e}")

    async def write_oob_message(
        self, message: OOBMessage, response: bool = False
    ) -> bool:
        """Serializes and sends an OOBMessage with MTU chunking and pacing delay."""
        serialized = message.serialize()
        return await self.write_raw_data(serialized, response=response)

    async def write_raw_data(
        self, data: bytes, response: bool = False
    ) -> bool:
        """
        Transmits raw bytes over NUS_RX with anti-tunneling verification,
        MTU-bounded slicing, and inter-chunk pacing delay.
        """
        assert_not_tunneling(data)

        if not self.is_connected or not self.client:
            logger.warning("Attempted to write over BLE NUS while disconnected.")
            return False

        mtu = self.get_mtu_size()
        chunk_size = calculate_chunk_size(mtu)
        chunks = chunk_payload(data, chunk_size)

        async with self._write_lock:
            try:
                for idx, chunk in enumerate(chunks):
                    # Write to characteristic
                    await self.client.write_gatt_char(NUS_RX_UUID, chunk, response=response)
                    # Pace consecutive chunks if more remain
                    if idx < len(chunks) - 1:
                        await asyncio.sleep(PACING_DELAY_SECONDS)
                return True
            except (BleakError, Exception) as e:
                logger.error(f"Failed writing GATT chunk over NUS: {e}")
                return False
