# Phase 7: Time Pulse (PPS) Configuration

## Overview

Implement `--pps` and `--time-gnss` options using CFG-TP (0x06 0x03).

## CFG-TP Payload Structure (16 bytes)

| Offset | Type | Name | Unit | Description |
|--------|------|------|------|-------------|
| 0 | U4 | interval | µs | Pulse interval (1000000 = 1Hz) |
| 4 | U4 | width | µs | Pulse width |
| 8 | U1 | enable | | 0=Off, 1=On, 2=Auto, 3=FixOnly |
| 9 | I1 | polar | | 0=Rising, 1=Falling |
| 10 | U1 | timeRef | | 0=UTC, 1=Satellite time |
| 11 | U1 | timeSource | | See below |
| 12 | R4 | userDelay | s | User delay compensation |

### timeSource Values

| Value | Display |
|-------|---------|
| 0 | GPS |
| 1 | BDS |
| 2 | GLONASS |
| 4 | BDS (mainly) |
| 5 | GPS (mainly) |
| 6 | GLONASS (mainly) |

Values 0-2 force a single constellation with no fallback. Values 4-6 ("mainly") prefer a constellation but automatically switch to others when unavailable.

**Tool behavior:**
- When displaying config: Show the full name including "(mainly)" suffix for values 4-6
- When setting via `--time-gnss`: Only support values 0-2 (GPS, BDS, GLO)

## CLI Options

### --pps WIDTH

Set PPS pulse width in seconds (0 to disable, max 1.0).

```
--pps 0.1      # 100ms pulse width, enable PPS
--pps 0        # Disable PPS
```

**Implementation:**
- `--pps 0`: Set `enable=0`
- `--pps N`: Set `width=N*1000000` (convert to µs), `enable=1`
- Interval stays at default (1Hz = 1000000µs) unless we add `--pps-period`

### --time-gnss SYSTEM

Set the time source constellation for PPS alignment.

```
--time-gnss GPS       # Use GPS time
--time-gnss BDS       # Use BeiDou time
--time-gnss GLO       # Use GLONASS time
```

**Implementation:**
- Map system name to timeSource value
- Use read-modify-write: query current CFG-TP, change only timeSource, send back

## Implementation Plan

### 1. Add build_cfg_tp() to casic.py

```python
def build_cfg_tp(
    interval_us: int = 1000000,
    width_us: int = 100000,
    enable: int = 1,
    polarity: int = 0,
    time_ref: int = 0,
    time_source: int = 0,
    user_delay: float = 0.0,
) -> bytes:
    """Build CFG-TP payload (16 bytes)."""
    return struct.pack(
        "<IIbbbBf",
        interval_us,
        width_us,
        enable,
        polarity,
        time_ref,
        time_source,
        user_delay,
    )
```

### 2. Add command functions to job.py

```python
def set_pps(conn: CasicConnection, width_seconds: float) -> bool:
    """Configure PPS output.

    Args:
        width_seconds: Pulse width in seconds (0 to disable)
    """
    # Query current config to preserve other settings
    result = conn.poll(CFG_TP.cls, CFG_TP.id)
    if not result.success:
        return False

    current = parse_cfg_tp(result.payload)

    if width_seconds == 0:
        enable = 0
        width_us = current.width_us  # Preserve existing width
    else:
        enable = 1
        width_us = int(width_seconds * 1_000_000)

    payload = build_cfg_tp(
        interval_us=current.interval_us,
        width_us=width_us,
        enable=enable,
        polarity=current.polarity,
        time_ref=current.time_ref,
        time_source=current.time_source,
        user_delay=current.user_delay,
    )
    return conn.send_and_wait_ack(CFG_TP.cls, CFG_TP.id, payload)


def set_time_gnss(conn: CasicConnection, system: str) -> bool:
    """Set PPS time source constellation.

    Args:
        system: "GPS", "BDS", or "GLO"
    """
    time_source_map = {
        "GPS": 0,
        "BDS": 1,
        "GLO": 2,
        "GLONASS": 2,
    }

    time_source = time_source_map.get(system.upper())
    if time_source is None:
        return False

    # Query current config
    result = conn.poll(CFG_TP.cls, CFG_TP.id)
    if not result.success:
        return False

    current = parse_cfg_tp(result.payload)

    payload = build_cfg_tp(
        interval_us=current.interval_us,
        width_us=current.width_us,
        enable=current.enable,
        polarity=current.polarity,
        time_ref=current.time_ref,
        time_source=time_source,
        user_delay=current.user_delay,
    )
    return conn.send_and_wait_ack(CFG_TP.cls, CFG_TP.id, payload)
```

### 3. Add parsing helper to job.py

```python
VALID_TIME_GNSS = {"GPS", "BDS", "GLO", "GLONASS"}

def parse_time_gnss_arg(system: str) -> str:
    """Validate and normalize --time-gnss argument."""
    system = system.strip().upper()
    if system not in VALID_TIME_GNSS:
        raise ValueError(f"Unknown time source: {system}. Use GPS, BDS, or GLO.")
    return system
```

### 4. Extend ConfigJob dataclass

```python
@dataclass
class ConfigJob:
    # ... existing fields ...

    # Time pulse (PPS) configuration
    pps_width: float | None = None  # Pulse width in seconds (0 to disable)
    time_gnss: str | None = None    # Time source: "GPS", "BDS", "GLO"
```

### 5. Update execute_job() in job.py

Add after GNSS configuration, before NVM operations:

```python
# Execute time pulse configuration
if job.pps_width is not None:
    if set_pps(conn, job.pps_width):
        if job.pps_width == 0:
            result.operations.append("PPS disabled")
        else:
            result.operations.append(f"PPS enabled: {job.pps_width}s pulse width")
        changes.mark_tp()
    else:
        result.success = False
        result.error = "Failed to configure PPS"
        return result

if job.time_gnss is not None:
    if set_time_gnss(conn, job.time_gnss):
        result.operations.append(f"PPS time source set to {job.time_gnss}")
        changes.mark_tp()
    else:
        result.success = False
        result.error = "Failed to set PPS time source"
        return result
```

### 6. Add ConfigChanges.mark_tp()

```python
def mark_tp(self) -> None:
    """Mark time pulse configuration as changed (CFG-TP)."""
    self.mask |= CFG_MASK_TP
```

### 7. Add CLI arguments to casictool.py

```python
# Time pulse (PPS) group
pps_group = parser.add_argument_group("Time Pulse (PPS)")
pps_group.add_argument(
    "--pps",
    type=float,
    metavar="WIDTH",
    help="Set PPS pulse width in seconds (0 to disable, max 1.0)",
)
pps_group.add_argument(
    "--time-gnss",
    type=str,
    metavar="SYSTEM",
    help="Set PPS time source (GPS, BDS, GLO)",
)
```

### 8. Update build_job() in casictool.py

```python
# Parse and set PPS configuration
if args.pps is not None:
    if args.pps < 0 or args.pps > 1.0:
        return job, "PPS width must be between 0 and 1.0 seconds"
    job.pps_width = args.pps

if args.time_gnss:
    try:
        job.time_gnss = parse_time_gnss_arg(args.time_gnss)
    except ValueError as e:
        return job, str(e)
```

## Tests to Add

### tests/test_pps.py

```python
class TestBuildCfgTp:
    def test_default_values(self) -> None:
        """Test default 1Hz, 100ms pulse."""
        payload = build_cfg_tp()
        assert len(payload) == 16
        interval, width, enable = struct.unpack("<IIb", payload[:9])
        assert interval == 1000000
        assert width == 100000
        assert enable == 1

    def test_disable_pps(self) -> None:
        """Test disable sets enable=0."""
        payload = build_cfg_tp(enable=0)
        enable = payload[8]
        assert enable == 0

    def test_time_source(self) -> None:
        """Test time_source field."""
        payload = build_cfg_tp(time_source=2)  # GLONASS
        time_source = payload[11]
        assert time_source == 2


class TestParseTimeGnssArg:
    def test_valid_systems(self) -> None:
        assert parse_time_gnss_arg("GPS") == "GPS"
        assert parse_time_gnss_arg("BDS") == "BDS"
        assert parse_time_gnss_arg("GLO") == "GLO"
        assert parse_time_gnss_arg("gps") == "GPS"

    def test_invalid_system(self) -> None:
        with pytest.raises(ValueError, match="Unknown time source"):
            parse_time_gnss_arg("GAL")
```

## Verification

After implementation, test on hardware:

```bash
# Show current PPS config
casictool -d /dev/ttyUSB0 -s 38400 --show-config

# Set PPS pulse width to 100ms
casictool -d /dev/ttyUSB0 -s 38400 --pps 0.1

# Disable PPS
casictool -d /dev/ttyUSB0 -s 38400 --pps 0

# Set time source to GPS
casictool -d /dev/ttyUSB0 -s 38400 --time-gnss GPS

# Set time source to BeiDou and save
casictool -d /dev/ttyUSB0 -s 38400 --time-gnss BDS --save
```

## Notes

1. **Read-modify-write pattern**: Both `--pps` and `--time-gnss` use read-modify-write to preserve other CFG-TP settings.

2. **CFG_MASK_TP**: PPS configuration uses bit 4 (0x0010) in CFG-CFG mask for save operations.

3. **Interval fixed at 1Hz**: We don't expose interval configuration. Could add `--pps-period` later if needed.

4. **Polarity not exposed**: Could add `--pps-polarity rising|falling` later if needed.

5. **userDelay limited**: The protocol only supports seconds, not nanoseconds, so cable delay compensation is limited.
