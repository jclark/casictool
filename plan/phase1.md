# Phase 1: Core Infrastructure

## Overview

Phase 1 implements the foundational CASIC protocol layer: message framing, checksum calculation, serial communication, ACK/NAK handling, and a basic CLI structure.

## Architecture

### Module Structure

```
casictool/
├── casictool.py      # CLI entry point
├── casic/
│   ├── __init__.py
│   ├── protocol.py   # Message framing, checksum, MsgID, registry
│   ├── messages.py   # Message type definitions (ACK, CFG-*, etc.)
│   └── serial.py     # Serial port communication
└── tests/
    ├── __init__.py
    ├── test_protocol.py
    └── test_messages.py
```

### Message Registry Pattern

Following the satpulse/ubx model but simplified:

```python
# protocol.py

SYNC1 = 0xBA
SYNC2 = 0xCE

class MsgID:
    """Combined class/id identifier."""
    def __init__(self, cls: int, id: int):
        self.cls = cls
        self.id = id

    def __eq__(self, other): ...
    def __hash__(self): ...
    def __repr__(self): ...

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

# Registry: MsgID -> (name, struct_format, field_names)
_msg_registry: dict[MsgID, tuple[str, str, tuple[str, ...]]] = {}

def register_msg(cls: int, id: int, name: str, fmt: str, fields: tuple[str, ...]):
    """Register a message type with its struct format."""
    _msg_registry[MsgID(cls, id)] = (name, fmt, fields)

def calc_checksum(cls: int, id: int, payload: bytes) -> int:
    """Calculate CASIC checksum (cumulative 32-bit word sum)."""
    length = len(payload)
    ck_sum = (id << 24) + (cls << 16) + length
    # Pad payload to multiple of 4
    padded = payload + b'\x00' * ((4 - len(payload) % 4) % 4)
    for i in range(0, len(padded), 4):
        word = int.from_bytes(padded[i:i+4], 'little')
        ck_sum = (ck_sum + word) & 0xFFFFFFFF
    return ck_sum

def pack_msg(cls: int, id: int, payload: bytes) -> bytes:
    """Pack a complete CASIC message with header and checksum."""
    ...

def parse_msg(data: bytes) -> tuple[MsgID, dict[str, Any]] | None:
    """Parse a CASIC message, returning (MsgID, fields) or None."""
    ...
```

### Message Definitions

```python
# messages.py

from .protocol import register_msg, CLS_ACK, CLS_CFG

# ACK messages (Class 0x05)
ACK_NAK = MsgID(CLS_ACK, 0x00)
ACK_ACK = MsgID(CLS_ACK, 0x01)

register_msg(CLS_ACK, 0x00, "ACK-NAK", "<BB", ("cls", "id"))
register_msg(CLS_ACK, 0x01, "ACK-ACK", "<BB", ("cls", "id"))

# CFG messages (Class 0x06)
CFG_PRT = MsgID(CLS_CFG, 0x00)
CFG_MSG = MsgID(CLS_CFG, 0x01)
CFG_RST = MsgID(CLS_CFG, 0x02)
CFG_TP = MsgID(CLS_CFG, 0x03)
CFG_RATE = MsgID(CLS_CFG, 0x04)
CFG_CFG = MsgID(CLS_CFG, 0x05)
CFG_TMODE = MsgID(CLS_CFG, 0x06)
CFG_NAVX = MsgID(CLS_CFG, 0x07)

# Phase 1: Only register ACK messages (others in later phases)
```

### Serial Communication

```python
# serial.py

class CasicConnection:
    """Serial connection with CASIC protocol handling."""

    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 2.0):
        ...

    def send(self, cls: int, id: int, payload: bytes = b"") -> None:
        """Send a CASIC message."""
        ...

    def receive(self, timeout: float | None = None) -> tuple[MsgID, bytes] | None:
        """Receive and parse a CASIC message."""
        ...

    def send_and_wait_ack(self, cls: int, id: int, payload: bytes,
                          timeout: float = 2.0) -> bool:
        """Send CFG message and wait for ACK/NAK response."""
        ...

    def poll(self, cls: int, id: int, timeout: float = 2.0) -> bytes | None:
        """Send query (empty payload) and wait for response."""
        ...
```

### CLI Structure

```python
# casictool.py

import argparse

def main():
    parser = argparse.ArgumentParser(description="CASIC GPS receiver configuration tool")

    # Connection options
    parser.add_argument("-d", "--device", default="/dev/ttyUSB0", help="Serial device")
    parser.add_argument("-s", "--speed", type=int, default=9600, help="Baud rate")

    # Phase 1: Minimal options
    parser.add_argument("--show-config", action="store_true", help="Show current configuration")

    args = parser.parse_args()
    # ... dispatch to handlers
```

---

## Implementation Steps

### Step 1: Protocol Core (`casic/protocol.py`)

1. Define constants: `SYNC1`, `SYNC2`, message classes
2. Implement `MsgID` class
3. Implement `calc_checksum()`
4. Implement `pack_msg()` to build complete messages
5. Implement `parse_msg()` to extract class/id/payload from raw bytes
6. Implement message registry (`register_msg`, `get_msg_info`)

### Step 2: Message Definitions (`casic/messages.py`)

1. Define `MsgID` constants for ACK-ACK, ACK-NAK
2. Register ACK message formats
3. Define `MsgID` constants for CFG messages (formats added in later phases)

### Step 3: Serial Communication (`casic/serial.py`)

1. Implement `CasicConnection.__init__()` with pyserial
2. Implement `send()` - pack and write message
3. Implement `receive()` - read and sync to header, validate checksum
4. Implement `send_and_wait_ack()` - send CFG, wait for ACK-ACK/ACK-NAK
5. Implement `poll()` - send empty payload query, return response

### Step 4: CLI Entry Point (`casictool.py`)

1. Set up argparse with `-d`, `-s` options
2. Add `--show-config` stub (actual implementation in Phase 2)
3. Wire up connection and basic error handling

---

## Unit Tests

### `tests/test_protocol.py`

```python
import pytest
from casic.protocol import calc_checksum, pack_msg, parse_msg, MsgID, CLS_ACK, CLS_CFG

class TestMsgID:
    def test_equality(self):
        a = MsgID(0x05, 0x01)
        b = MsgID(0x05, 0x01)
        c = MsgID(0x05, 0x00)
        assert a == b
        assert a != c

    def test_hash(self):
        a = MsgID(0x05, 0x01)
        b = MsgID(0x05, 0x01)
        assert hash(a) == hash(b)
        d = {a: "ack"}
        assert d[b] == "ack"

    def test_repr(self):
        a = MsgID(0x05, 0x01)
        assert "05" in repr(a) and "01" in repr(a)


class TestChecksum:
    def test_empty_payload(self):
        # CFG-PRT query: class=0x06, id=0x00, payload=[]
        # ck_sum = (0x00 << 24) + (0x06 << 16) + 0 = 0x00060000
        ck = calc_checksum(0x06, 0x00, b"")
        assert ck == 0x00060000

    def test_4byte_payload(self):
        # class=0x06, id=0x05, payload=[0x01, 0x02, 0x03, 0x04]
        # ck_sum = (0x05 << 24) + (0x06 << 16) + 4 = 0x05060004
        # word = 0x04030201
        # ck_sum = 0x05060004 + 0x04030201 = 0x09090205
        ck = calc_checksum(0x06, 0x05, bytes([0x01, 0x02, 0x03, 0x04]))
        assert ck == 0x09090205

    def test_partial_word_payload(self):
        # 2-byte payload gets padded with zeros
        # class=0x06, id=0x01, payload=[0xAB, 0xCD]
        # ck_sum = (0x01 << 24) + (0x06 << 16) + 2 = 0x01060002
        # padded word = 0x0000CDAB
        # ck_sum = 0x01060002 + 0x0000CDAB = 0x0106CDAD
        ck = calc_checksum(0x06, 0x01, bytes([0xAB, 0xCD]))
        assert ck == 0x0106CDAD


class TestPackMsg:
    def test_pack_empty_payload(self):
        # CFG-PRT query
        msg = pack_msg(0x06, 0x00, b"")
        assert msg[:2] == bytes([0xBA, 0xCE])  # sync
        assert msg[2:4] == bytes([0x00, 0x00])  # length = 0, little-endian
        assert msg[4] == 0x06  # class
        assert msg[5] == 0x00  # id
        # checksum at bytes 6-9
        assert len(msg) == 10

    def test_pack_with_payload(self):
        payload = bytes([0x01, 0x02, 0x03, 0x04])
        msg = pack_msg(0x06, 0x05, payload)
        assert msg[:2] == bytes([0xBA, 0xCE])
        assert msg[2:4] == bytes([0x04, 0x00])  # length = 4
        assert msg[4:6] == bytes([0x06, 0x05])  # class, id
        assert msg[6:10] == payload
        # checksum at bytes 10-13
        assert len(msg) == 14


class TestParseMsg:
    def test_parse_valid_message(self):
        # Build a message then parse it
        payload = bytes([0x06, 0x00])  # ACK for CFG-PRT
        msg = pack_msg(0x05, 0x01, payload)
        result = parse_msg(msg)
        assert result is not None
        mid, data = result
        assert mid == MsgID(0x05, 0x01)
        assert data == payload

    def test_parse_bad_sync(self):
        msg = bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        result = parse_msg(msg)
        assert result is None

    def test_parse_bad_checksum(self):
        msg = pack_msg(0x05, 0x01, bytes([0x06, 0x00]))
        # Corrupt the checksum
        corrupted = msg[:-1] + bytes([msg[-1] ^ 0xFF])
        result = parse_msg(corrupted)
        assert result is None

    def test_roundtrip(self):
        """Pack then parse should return original data."""
        for cls, id, payload in [
            (0x05, 0x00, bytes([0x06, 0x01])),
            (0x05, 0x01, bytes([0x06, 0x00])),
            (0x06, 0x00, b""),
            (0x06, 0x05, bytes([0xFF, 0x00, 0x01, 0x00])),
        ]:
            msg = pack_msg(cls, id, payload)
            result = parse_msg(msg)
            assert result is not None
            mid, data = result
            assert mid.cls == cls
            assert mid.id == id
            assert data == payload
```

### `tests/test_messages.py`

```python
import struct
import pytest
from casic.protocol import MsgID, CLS_ACK, CLS_CFG
from casic.messages import ACK_ACK, ACK_NAK, CFG_PRT, CFG_RST

class TestMessageConstants:
    def test_ack_ids(self):
        assert ACK_NAK == MsgID(CLS_ACK, 0x00)
        assert ACK_ACK == MsgID(CLS_ACK, 0x01)

    def test_cfg_ids(self):
        assert CFG_PRT == MsgID(CLS_CFG, 0x00)
        assert CFG_RST == MsgID(CLS_CFG, 0x02)
```

---

## Acceptance Criteria

1. `calc_checksum()` produces correct checksums per CASIC spec
2. `pack_msg()` produces valid CASIC frames
3. `parse_msg()` correctly extracts class/id/payload and validates checksum
4. `MsgID` is hashable and usable as dict key
5. All unit tests pass
6. `make check` passes (lint + typecheck + test)

---

## Dependencies

- Python >= 3.9
- pyserial >= 3.5 (already in pyproject.toml)

---

## Notes

- Variable-length messages (NAV-GPSINFO, etc.) will be handled in later phases if needed
- The registry pattern allows Phase 2+ to add message definitions without changing core protocol code
- Serial receive needs to handle byte-by-byte sync searching (CASIC stream may have NMEA mixed in)
