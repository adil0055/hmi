"""End-to-end protection of a CAN message: alive counter and CRC.

AUTOSAR E2E profile 1 style, as the matrix (can/cluster.dbc) describes it: a
4-bit counter that counts 0..14, and an 8-bit CRC -- CRC-8 SAE J1850, poly
0x1D, init 0xFF, final XOR 0xFF -- over the Data ID (the message ID, low byte
then high byte) and every data byte but the CRC's own. A message carries
protection when it has a signal ending ``_CRC`` and one ending ``_Counter``.

The sender (backend.restbus) protects each frame it sends; the cluster
(backend.ecu) checks each frame it gets, and a frame with a wrong CRC or a
counter that did not move is not used.
"""

from __future__ import annotations

COUNTER_MAX = 14            # 15 is reserved in profile 1


def crc8_sae_j1850(data: bytes, crc: int = 0xFF) -> int:
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1D) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc ^ 0xFF


class Protection:
    """Where a message's counter and CRC are, and how to fill or check them."""

    def __init__(self, message) -> None:
        names = {s.name: s for s in message.signals}
        self.crc = next((s for n, s in names.items() if n.endswith("_CRC")), None)
        self.counter = next((s for n, s in names.items() if n.endswith("_Counter")), None)
        self.frame_id = message.frame_id
        self.message = message

    @property
    def active(self) -> bool:
        return self.crc is not None and self.counter is not None

    def _crc_of(self, data: bytes) -> int:
        at = self.crc.start // 8
        body = bytes(b for i, b in enumerate(data) if i != at)
        return crc8_sae_j1850(bytes([self.frame_id & 0xFF, (self.frame_id >> 8) & 0xFF]) + body)

    def protect(self, raw: dict, counter: int) -> bytes:
        """Encode ``raw`` (raw signal values) with this counter and its CRC."""
        raw = dict(raw)
        raw[self.counter.name] = counter % (COUNTER_MAX + 1)
        raw[self.crc.name] = 0
        data = bytearray(self.message.encode(raw, scaling=False, strict=False))
        data[self.crc.start // 8] = self._crc_of(bytes(data))
        return bytes(data)

    def check(self, data: bytes) -> tuple[bool, int]:
        """(CRC right, counter) of a received frame."""
        if len(data) <= self.crc.start // 8:
            return False, -1
        decoded = self.message.decode(data, decode_choices=False, scaling=False)
        return data[self.crc.start // 8] == self._crc_of(data), int(decoded[self.counter.name])
