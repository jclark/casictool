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
    CasicPacket,
    CasicStreamParser,
    MsgID,
    NmeaSentence,
    StreamEvent,
    UnknownBytes,
    pack_msg,
)

if TYPE_CHECKING:
    from serial import Serial


def _extract_nmea_msg_type(sentence: str) -> str:
    """Extract message type from NMEA sentence (e.g., '$GNGGA,...' -> 'GNGGA')."""
    if sentence.startswith("$") and "," in sentence:
        return sentence[1 : sentence.index(",")]
    return "NMEA"


READ_CHUNK_SIZE = 256

# Timeout constants for query/response handling
INITIAL_TIMEOUT = 5.0  # wait for first/only response (receiver may be slow)
SUBSEQUENT_TIMEOUT = 0.5  # wait for additional responses in multi-response queries



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
        self._parser = CasicStreamParser()
        self._seen_packet_types: set[str] = set()

    @property
    def seen_casic_packet(self) -> bool:
        """True if we've received at least one valid CASIC packet."""
        return "CASIC" in self._seen_packet_types

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

    def _log_unknown_packet(self, data: bytes, ts: float) -> None:
        """Log unrecognized bytes to the packet log."""
        if not self._packet_log:
            return
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        entry: dict[str, object] = {
            "t": dt.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z",
            "out": False,
        }
        # Check if all bytes are printable ASCII or whitespace
        if all(0x20 <= b <= 0x7E or b in (0x09, 0x0A, 0x0D) for b in data):
            entry["ascii"] = data.decode("ascii")
        else:
            entry["bin"] = data.hex()
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
            self._log.debug(f"TX {msg_name} ({len(payload)} payload bytes)")

    def _log_valid_packet_seen(self, packet_type: str) -> None:
        """Log info message the first time we see a valid packet of this type."""
        if packet_type not in self._seen_packet_types:
            self._seen_packet_types.add(packet_type)
            if self._log:
                self._log.info(f"valid {packet_type} packet received; speed OK")

    def _log_event(self, event: StreamEvent) -> None:
        """Log a received event to packet log and debug output."""
        if isinstance(event, NmeaSentence):
            try:
                sentence = event.data.decode("ascii")
            except UnicodeDecodeError:
                return
            self._log_nmea_packet(sentence, event.timestamp)
            self._log_valid_packet_seen("NMEA")
            if self._log:
                msg_type = sentence[1:].split(",", 1)[0] if sentence else "?"
                self._log.debug(f"RX NMEA {msg_type}")
        elif isinstance(event, UnknownBytes):
            self._log_unknown_packet(event.data, event.timestamp)
            if self._log:
                self._log.debug(f"RX UNKNOWN ({len(event.data)} bytes)")
        elif isinstance(event, CasicPacket):
            self._log_casic_packet(event.raw, event.timestamp, out=False)
            self._log_valid_packet_seen("CASIC")
            if self._log:
                msg_name = MSG_NAMES.get(
                    (event.msg_id.cls, event.msg_id.id),
                    f"0x{event.msg_id.cls:02X}-0x{event.msg_id.id:02X}",
                )
                self._log.debug(f"RX {msg_name} ({len(event.payload)} payload bytes)")

    def receive_packet(self, timeout: float | None = None) -> StreamEvent | None:
        """Receive next packet of any type (CASIC, NMEA, or Unknown).

        Handles packet logging and debug output for all packet types.
        Returns None on timeout.
        """
        if timeout is None:
            timeout = self.timeout

        start_time = time.monotonic()
        old_timeout = self._serial.timeout
        self._serial.timeout = min(0.1, timeout)

        try:
            while time.monotonic() - start_time < timeout:
                event = self._parser.pop_event()
                if event is not None:
                    self._log_event(event)
                    return event

                data = self._serial.read(READ_CHUNK_SIZE)
                if not data:
                    continue

                ts = time.time()
                self._parser.feed(data, ts)

                event = self._parser.pop_event()
                if event is not None:
                    self._log_event(event)
                    return event

            return None
        finally:
            self._serial.timeout = old_timeout

    def receive(self, timeout: float | None = None) -> tuple[MsgID, bytes] | None:
        """Receive next CASIC binary message, skipping NMEA and unknown packets."""
        if timeout is None:
            timeout = self.timeout

        start_time = time.monotonic()
        while time.monotonic() - start_time < timeout:
            remaining = timeout - (time.monotonic() - start_time)
            event = self.receive_packet(timeout=remaining)
            if event is None:
                return None
            if isinstance(event, CasicPacket):
                return event.msg_id, event.payload
        return None

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

    def poll(self, cls: int, id: int, payload: bytes = b"", timeout: float = INITIAL_TIMEOUT) -> PollResult:
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
