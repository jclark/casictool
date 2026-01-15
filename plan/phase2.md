# Phase 2: Show Config

## Overview

Phase 2 implements the `--show-config` command that queries all CFG messages from the receiver and displays the current configuration in a human-readable format.

## Project Structure

```
casictool/
├── casic.py       # Protocol, messages, serial (add config dataclasses + parsers + formatter)
├── casictool.py   # CLI entry point (add --show-config handler)
└── tests/
    └── test_casic.py  # Add config parsing tests
```

## CFG Messages to Query

| Message | Class/ID | Response Length | Key Information |
|---------|----------|-----------------|-----------------|
| CFG-PRT | 0x06 0x00 | 8 bytes | Baud rate, protocol mask |
| CFG-RATE | 0x06 0x04 | 4 bytes | Navigation update interval |
| CFG-TP | 0x06 0x03 | 16 bytes | PPS settings |
| CFG-TMODE | 0x06 0x06 | 40 bytes | Timing mode, position, survey |
| CFG-NAVX | 0x06 0x07 | 44 bytes | GNSS, dynamic model, accuracy |

## Implementation Steps

### Step 1: Add Configuration Dataclasses to `casic.py`

Add dataclasses for each CFG response type with computed properties for human-readable values:

- `PortConfig` - baud rate, protocol mask, data format
- `RateConfig` - navigation interval
- `TimePulseConfig` - PPS interval, width, enable, polarity, time source
- `TimingModeConfig` - mode, fixed position, survey params
- `NavEngineConfig` - GNSS systems, dynamic model, accuracy limits
- `ReceiverConfig` - container for all config sections

### Step 2: Add Payload Parsers to `casic.py`

Implement parser functions using struct.unpack:

- `parse_cfg_prt(payload)` - `"<BBHI"` (8 bytes)
- `parse_cfg_rate(payload)` - `"<HH"` (4 bytes)
- `parse_cfg_tp(payload)` - `"<IIBbBBf"` (16 bytes)
- `parse_cfg_tmode(payload)` - `"<IdddfIf"` (40 bytes)
- `parse_cfg_navx(payload)` - `"<IbBbbBbbbBHfffffff"` (44 bytes)

### Step 3: Add Configuration Formatter to `casic.py`

Implement `format_config(config: ReceiverConfig) -> str` that produces human-readable output.

### Step 4: Implement Show Config Handler in `casictool.py`

1. Add `show_config(conn: CasicConnection) -> ReceiverConfig` that polls all CFG commands
2. Update `main()` to call show_config when `--show-config` is used
3. Handle serial port errors and timeouts gracefully

## Unit Tests

Add to `tests/test_casic.py`:

```python
class TestPortConfig:
    def test_protocol_mask_flags(self):
        cfg = PortConfig(port_id=0, proto_mask=0x33, mode=0x0800, baud_rate=9600)
        assert cfg.binary_input is True
        assert cfg.baud_rate == 9600

    def test_parse_cfg_prt(self):
        payload = struct.pack("<BBHI", 0, 0x33, 0x0800, 9600)
        cfg = parse_cfg_prt(payload)
        assert cfg.baud_rate == 9600

class TestNavEngineConfig:
    def test_gnss_list(self):
        cfg = NavEngineConfig(nav_system=0x07, ...)
        assert cfg.gnss_list == ["GPS", "BDS", "GLONASS"]

class TestFormatConfig:
    def test_format_complete_config(self):
        config = ReceiverConfig(port=PortConfig(...), ...)
        output = format_config(config)
        assert "Baud Rate: 9600" in output
```

## Acceptance Criteria

1. `--show-config` displays all configuration sections
2. Human-readable values (e.g., "GPS, BDS" instead of "0x03")
3. Serial port errors produce clear error messages
4. `make check` passes

## Example Output

```
Current Receiver Configuration
========================================

Serial Port (CFG-PRT):
  Baud Rate: 9600
  Data Format: 8N1

Navigation Rate (CFG-RATE):
  Update Interval: 1000 ms
  Update Rate: 1.0 Hz

Time Pulse / PPS (CFG-TP):
  Enable: On
  Interval: 1.0 s
  Width: 100.0 ms
  Polarity: Rising edge
  Time Source: GPS

Timing Mode (CFG-TMODE):
  Mode: Mobile/Auto

Navigation Engine (CFG-NAVX):
  GNSS Systems: GPS, BDS, GLONASS
  Dynamic Model: Portable
  Fix Mode: Auto
```
