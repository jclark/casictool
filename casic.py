"""CASIC protocol implementation: framing, checksum, messages, and serial communication."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import serial

if TYPE_CHECKING:
    from serial import Serial

# Sync bytes
SYNC1 = 0xBA
SYNC2 = 0xCE

# Message classes
CLS_NAV = 0x01
CLS_TIM = 0x02
CLS_RXM = 0x03
CLS_ACK = 0x05
CLS_CFG = 0x06
CLS_MSG = 0x08
CLS_MON = 0x0A
CLS_AID = 0x0B
CLS_NMEA = 0x4E


class MsgID:
    """Combined class/id identifier for CASIC messages."""

    def __init__(self, cls: int, id: int) -> None:
        self.cls = cls
        self.id = id

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MsgID):
            return NotImplemented
        return self.cls == other.cls and self.id == other.id

    def __hash__(self) -> int:
        return hash((self.cls, self.id))

    def __repr__(self) -> str:
        return f"MsgID(0x{self.cls:02X}, 0x{self.id:02X})"


# ACK messages
ACK_NAK = MsgID(CLS_ACK, 0x00)
ACK_ACK = MsgID(CLS_ACK, 0x01)

# CFG messages
CFG_PRT = MsgID(CLS_CFG, 0x00)
CFG_MSG = MsgID(CLS_CFG, 0x01)
CFG_RST = MsgID(CLS_CFG, 0x02)
CFG_TP = MsgID(CLS_CFG, 0x03)
CFG_RATE = MsgID(CLS_CFG, 0x04)
CFG_CFG = MsgID(CLS_CFG, 0x05)
CFG_TMODE = MsgID(CLS_CFG, 0x06)
CFG_NAVX = MsgID(CLS_CFG, 0x07)


def calc_checksum(cls: int, id: int, payload: bytes) -> int:
    """Calculate CASIC checksum (cumulative 32-bit word sum)."""
    length = len(payload)
    ck_sum = (id << 24) + (cls << 16) + length

    # Pad payload to multiple of 4 bytes
    pad_len = (4 - len(payload) % 4) % 4
    padded = payload + b"\x00" * pad_len

    # Sum 32-bit little-endian words
    for i in range(0, len(padded), 4):
        word = int.from_bytes(padded[i : i + 4], "little")
        ck_sum = (ck_sum + word) & 0xFFFFFFFF

    return ck_sum


def pack_msg(cls: int, id: int, payload: bytes) -> bytes:
    """Pack a complete CASIC message with header and checksum."""
    length = len(payload)
    checksum = calc_checksum(cls, id, payload)

    msg = bytearray()
    msg.append(SYNC1)
    msg.append(SYNC2)
    msg.extend(length.to_bytes(2, "little"))
    msg.append(cls)
    msg.append(id)
    msg.extend(payload)
    msg.extend(checksum.to_bytes(4, "little"))

    return bytes(msg)


def parse_msg(data: bytes) -> tuple[MsgID, bytes] | None:
    """Parse a CASIC message, returning (MsgID, payload) or None on error."""
    if len(data) < 10:
        return None

    if data[0] != SYNC1 or data[1] != SYNC2:
        return None

    length = int.from_bytes(data[2:4], "little")
    expected_size = 6 + length + 4
    if len(data) < expected_size:
        return None

    cls = data[4]
    id = data[5]
    payload = data[6 : 6 + length]

    received_checksum = int.from_bytes(data[6 + length : 6 + length + 4], "little")
    calculated_checksum = calc_checksum(cls, id, payload)

    if received_checksum != calculated_checksum:
        return None

    return MsgID(cls, id), payload


class CasicConnection:
    """Serial connection with CASIC protocol handling."""

    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 2.0) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._serial: Serial = serial.Serial(port, baudrate=baudrate, timeout=timeout)

    def close(self) -> None:
        self._serial.close()

    def __enter__(self) -> CasicConnection:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        self.close()

    def send(self, cls: int, id: int, payload: bytes = b"") -> None:
        """Send a CASIC message."""
        msg = pack_msg(cls, id, payload)
        self._serial.write(msg)
        self._serial.flush()

    def receive(self, timeout: float | None = None) -> tuple[MsgID, bytes] | None:
        """Receive and parse a CASIC message."""
        if timeout is None:
            timeout = self.timeout

        start_time = time.monotonic()
        old_timeout = self._serial.timeout
        self._serial.timeout = min(0.1, timeout)

        try:
            while time.monotonic() - start_time < timeout:
                byte1 = self._serial.read(1)
                if not byte1 or byte1[0] != SYNC1:
                    continue

                byte2 = self._serial.read(1)
                if not byte2 or byte2[0] != SYNC2:
                    continue

                length_bytes = self._serial.read(2)
                if len(length_bytes) < 2:
                    continue

                length = int.from_bytes(length_bytes, "little")
                remaining = 2 + length + 4
                rest = self._serial.read(remaining)
                if len(rest) < remaining:
                    continue

                full_msg = bytes([SYNC1, SYNC2]) + length_bytes + rest
                result = parse_msg(full_msg)
                if result is not None:
                    return result

            return None
        finally:
            self._serial.timeout = old_timeout

    def send_and_wait_ack(
        self, cls: int, id: int, payload: bytes, timeout: float = 2.0
    ) -> bool:
        """Send CFG message and wait for ACK/NAK response."""
        self.send(cls, id, payload)

        start_time = time.monotonic()
        while time.monotonic() - start_time < timeout:
            result = self.receive(timeout=timeout - (time.monotonic() - start_time))
            if result is None:
                continue

            msg_id, ack_payload = result

            if msg_id == ACK_ACK and len(ack_payload) >= 2:
                if ack_payload[0] == cls and ack_payload[1] == id:
                    return True

            if msg_id == ACK_NAK and len(ack_payload) >= 2:
                if ack_payload[0] == cls and ack_payload[1] == id:
                    return False

        return False

    def poll(self, cls: int, id: int, timeout: float = 2.0) -> bytes | None:
        """Send query (empty payload) and wait for response."""
        self.send(cls, id, b"")

        start_time = time.monotonic()
        while time.monotonic() - start_time < timeout:
            result = self.receive(timeout=timeout - (time.monotonic() - start_time))
            if result is None:
                continue

            msg_id, payload = result
            if msg_id.cls == cls and msg_id.id == id:
                return payload

        return None
