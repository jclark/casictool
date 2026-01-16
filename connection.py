"""CASIC serial connection: send/receive messages over serial port."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import IO, TYPE_CHECKING

import serial

from casic import (
    ACK_ACK,
    ACK_NAK,
    MSG_NAMES,
    SYNC1,
    SYNC2,
    MsgID,
    pack_msg,
    parse_msg,
)

if TYPE_CHECKING:
    from serial import Serial


def _extract_nmea_msg_type(sentence: str) -> str:
    """Extract message type from NMEA sentence (e.g., '$GNGGA,...' -> 'GNGGA')."""
    if sentence.startswith("$") and "," in sentence:
        return sentence[1 : sentence.index(",")]
    return "NMEA"


@dataclass
class PollResult:
    """Result of a poll operation."""

    payload: bytes | None
    nak: bool = False

    @property
    def success(self) -> bool:
        return self.payload is not None

    @property
    def timeout(self) -> bool:
        return self.payload is None and not self.nak


class CasicConnection:
    """Serial connection with CASIC protocol handling."""

    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        timeout: float = 2.0,
        packet_log: str | None = None,
        log: logging.Logger | None = None,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._serial: Serial = serial.Serial(port, baudrate=baudrate, timeout=timeout)
        self._serial.reset_input_buffer()
        self._packet_log: IO[str] | None = None
        if packet_log:
            self._packet_log = open(packet_log, "a")
        self._log = log

    def close(self) -> None:
        if self._packet_log:
            self._packet_log.close()
            self._packet_log = None
        self._serial.close()

    def _log_casic_packet(self, data: bytes, ts: float, out: bool) -> None:
        """Log a CASIC binary packet to the packet log."""
        if not self._packet_log:
            return
        cls = data[4]
        msg_id = data[5]
        msg_name = MSG_NAMES.get((cls, msg_id), f"UNK-{cls:02X}-{msg_id:02X}")
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        entry = {
            "t": dt.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z",
            "tag": "CSIP",
            "msg": msg_name,
            "bin": data.hex(),
            "out": out,
        }
        self._packet_log.write(json.dumps(entry) + "\n")
        self._packet_log.flush()

    def _log_nmea_packet(self, sentence: str, ts: float) -> None:
        """Log an NMEA text packet to the packet log."""
        if not self._packet_log:
            return
        msg_type = _extract_nmea_msg_type(sentence)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        entry = {
            "t": dt.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z",
            "tag": "NMEA",
            "msg": msg_type,
            "ascii": sentence,
            "out": False,
        }
        self._packet_log.write(json.dumps(entry) + "\n")
        self._packet_log.flush()

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
        ts = time.time()
        self._serial.write(msg)
        self._serial.flush()
        self._log_casic_packet(msg, ts, out=True)
        if self._log:
            msg_name = MSG_NAMES.get((cls, id), f"0x{cls:02X}-0x{id:02X}")
            self._log.debug(f"TX {msg_name} ({len(payload)} bytes)")

    def receive(self, timeout: float | None = None) -> tuple[MsgID, bytes] | None:
        """Receive and parse a CASIC message.

        Also logs NMEA sentences to packet log if enabled.
        """
        if timeout is None:
            timeout = self.timeout

        start_time = time.monotonic()
        old_timeout = self._serial.timeout
        self._serial.timeout = min(0.1, timeout)

        try:
            while time.monotonic() - start_time < timeout:
                byte1 = self._serial.read(1)
                if not byte1:
                    continue

                ts = time.time()  # Timestamp when first byte received

                # Check for NMEA sentence start
                if byte1[0] == 0x24:  # '$'
                    nmea_buf = bytearray(byte1)
                    # Read until newline or timeout
                    while time.monotonic() - start_time < timeout:
                        b = self._serial.read(1)
                        if not b:
                            break
                        nmea_buf.extend(b)
                        if b[0] == 0x0A:  # '\n'
                            try:
                                sentence = nmea_buf.decode("ascii")
                                self._log_nmea_packet(sentence, ts)
                            except UnicodeDecodeError:
                                pass
                            break
                    continue

                # Check for CASIC message start
                if byte1[0] != SYNC1:
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
                    self._log_casic_packet(full_msg, ts, out=False)
                    if self._log:
                        msg_id, payload = result
                        msg_name = MSG_NAMES.get((msg_id.cls, msg_id.id), f"0x{msg_id.cls:02X}-0x{msg_id.id:02X}")
                        self._log.debug(f"RX {msg_name} ({len(payload)} bytes)")
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

    def poll(self, cls: int, id: int, payload: bytes = b"", timeout: float = 2.0) -> PollResult:
        """Send query and wait for response.

        Returns PollResult with:
        - payload set on success
        - nak=True if receiver rejected the query
        - both None/False on timeout
        """
        self.send(cls, id, payload)

        start_time = time.monotonic()
        while time.monotonic() - start_time < timeout:
            result = self.receive(timeout=timeout - (time.monotonic() - start_time))
            if result is None:
                continue

            msg_id, payload = result

            # Check for NAK response to our query
            if msg_id == ACK_NAK and len(payload) >= 2:
                if payload[0] == cls and payload[1] == id:
                    return PollResult(None, nak=True)

            # Check for the actual response
            if msg_id.cls == cls and msg_id.id == id:
                return PollResult(payload)

        return PollResult(None)
