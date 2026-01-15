# Phase 6: Timing Mode Implementation Plan

## Overview

Phase 6 implements timing mode configuration using CFG-TMODE (0x06 0x06). This enables three positioning modes:
- **Survey-In**: Receiver averages position over time to establish a fixed reference
- **Fixed Position**: User specifies exact ECEF coordinates
- **Mobile/Auto**: Normal navigation mode (no fixed position)

## CLI Options to Implement

| Option | Description | Example |
|--------|-------------|---------|
| `--survey` | Enable survey-in mode | `--survey` |
| `--survey-time SECS` | Minimum survey duration (default: 2000s) | `--survey-time 3600` |
| `--survey-acc METERS` | Target survey accuracy (default: 20m) | `--survey-acc 10` |
| `--fixed-pos-ecef X,Y,Z` | Set fixed ECEF position | `--fixed-pos-ecef 4000000,1000000,5000000` |
| `--fixed-pos-acc METERS` | Fixed position accuracy (default: 1m) | `--fixed-pos-acc 0.5` |
| `--mobile` | Enable mobile/auto mode (disable timing mode) | `--mobile` |

## CFG-TMODE Payload Structure (40 bytes)

| Offset | Type | Name | Unit | Description |
|--------|------|------|------|-------------|
| 0 | U4 | mode | - | 0=Auto, 1=Survey-In, 2=Fixed |
| 4 | R8 | fixedPosX | m | ECEF X coordinate |
| 12 | R8 | fixedPosY | m | ECEF Y coordinate |
| 20 | R8 | fixedPosZ | m | ECEF Z coordinate |
| 28 | R4 | fixedPosVar | m² | Position variance (accuracy²) |
| 32 | U4 | svinMinDur | s | Survey-in minimum duration |
| 36 | R4 | svinVarLimit | m² | Survey-in variance limit (accuracy²) |

## Implementation Steps

### Step 1: Add CLI Arguments

Add to `argparse` in `casictool.py`:

```python
# Timing mode group
timing_group = parser.add_argument_group("Timing Mode")
timing_group.add_argument("--survey", action="store_true",
    help="Enable survey-in mode")
timing_group.add_argument("--survey-time", type=int, default=2000, metavar="SECS",
    help="Survey-in minimum duration in seconds (default: 2000)")
timing_group.add_argument("--survey-acc", type=float, default=20.0, metavar="METERS",
    help="Survey-in target accuracy in meters (default: 20)")
timing_group.add_argument("--fixed-pos-ecef", type=str, metavar="X,Y,Z",
    help="Set fixed ECEF position (meters, comma-separated)")
timing_group.add_argument("--fixed-pos-acc", type=float, default=1.0, metavar="METERS",
    help="Fixed position accuracy in meters (default: 1)")
timing_group.add_argument("--mobile", action="store_true",
    help="Enable mobile/auto mode (disable timing mode)")
```

### Step 2: Add Payload Builder in `casic.py`

```python
def build_cfg_tmode(
    mode: int,
    fixed_pos: tuple[float, float, float] | None = None,
    fixed_pos_acc: float = 1.0,
    survey_min_dur: int = 2000,
    survey_acc: float = 20.0,
) -> bytes:
    """Build CFG-TMODE payload (40 bytes).

    Args:
        mode: 0=Auto, 1=Survey-In, 2=Fixed
        fixed_pos: (X, Y, Z) ECEF coordinates in meters (required for mode=2)
        fixed_pos_acc: Position accuracy in meters (for mode=2)
        survey_min_dur: Survey minimum duration in seconds (for mode=1)
        survey_acc: Survey target accuracy in meters (for mode=1)
    """
    if fixed_pos is None:
        fixed_pos = (0.0, 0.0, 0.0)

    # Variance = accuracy squared
    fixed_pos_var = fixed_pos_acc ** 2
    survey_var_limit = survey_acc ** 2

    return struct.pack(
        "<IdddfIf",
        mode,                    # U4: mode
        fixed_pos[0],            # R8: fixedPosX
        fixed_pos[1],            # R8: fixedPosY
        fixed_pos[2],            # R8: fixedPosZ
        fixed_pos_var,           # R4: fixedPosVar
        survey_min_dur,          # U4: svinMinDur
        survey_var_limit,        # R4: svinVarLimit
    )
```

### Step 3: Add Command Handler Functions in `casictool.py`

```python
def parse_ecef_coords(coord_str: str) -> tuple[float, float, float]:
    """Parse comma-separated ECEF coordinates."""
    parts = coord_str.split(",")
    if len(parts) != 3:
        raise ValueError("ECEF coordinates must be X,Y,Z (3 values)")
    return (float(parts[0]), float(parts[1]), float(parts[2]))


def set_survey_mode(conn: CasicConnection, min_dur: int, acc: float) -> bool:
    """Configure receiver for survey-in mode."""
    payload = build_cfg_tmode(
        mode=1,  # Survey-In
        survey_min_dur=min_dur,
        survey_acc=acc,
    )
    return conn.send_and_wait_ack(CFG_TMODE.cls, CFG_TMODE.id, payload)


def set_fixed_position(
    conn: CasicConnection,
    ecef: tuple[float, float, float],
    acc: float,
) -> bool:
    """Configure receiver with fixed ECEF position."""
    payload = build_cfg_tmode(
        mode=2,  # Fixed
        fixed_pos=ecef,
        fixed_pos_acc=acc,
    )
    return conn.send_and_wait_ack(CFG_TMODE.cls, CFG_TMODE.id, payload)


def set_mobile_mode(conn: CasicConnection) -> bool:
    """Configure receiver for mobile/auto mode."""
    payload = build_cfg_tmode(mode=0)  # Auto
    return conn.send_and_wait_ack(CFG_TMODE.cls, CFG_TMODE.id, payload)
```

### Step 4: Integrate into Main Function

Add to `main()` after argument parsing:

```python
# Handle timing mode options
if args.survey:
    with CasicConnection(args.device, baudrate=args.speed) as conn:
        if not probe_receiver(conn)[0]:
            print("Error: No response from receiver", file=sys.stderr)
            return 1
        if set_survey_mode(conn, args.survey_time, args.survey_acc):
            print(f"Survey-in mode enabled: {args.survey_time}s, {args.survey_acc}m accuracy")
        else:
            print("Error: Failed to set survey-in mode", file=sys.stderr)
            return 1
    return 0

if args.fixed_pos_ecef:
    try:
        ecef = parse_ecef_coords(args.fixed_pos_ecef)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    with CasicConnection(args.device, baudrate=args.speed) as conn:
        if not probe_receiver(conn)[0]:
            print("Error: No response from receiver", file=sys.stderr)
            return 1
        if set_fixed_position(conn, ecef, args.fixed_pos_acc):
            print(f"Fixed position set: ECEF ({ecef[0]:.3f}, {ecef[1]:.3f}, {ecef[2]:.3f})")
        else:
            print("Error: Failed to set fixed position", file=sys.stderr)
            return 1
    return 0

if args.mobile:
    with CasicConnection(args.device, baudrate=args.speed) as conn:
        if not probe_receiver(conn)[0]:
            print("Error: No response from receiver", file=sys.stderr)
            return 1
        if set_mobile_mode(conn):
            print("Mobile/auto mode enabled")
        else:
            print("Error: Failed to set mobile mode", file=sys.stderr)
            return 1
    return 0
```

### Step 5: Add Tests

Create tests in `tests/test_timing_mode.py`:

```python
"""Tests for Phase 6: Timing mode configuration."""

import struct
import pytest
from casic import build_cfg_tmode, parse_cfg_tmode, TimingModeConfig


class TestBuildCfgTmode:
    def test_auto_mode(self):
        """Mode 0 (auto) sets all position fields to zero."""
        payload = build_cfg_tmode(mode=0)
        assert len(payload) == 40
        mode, = struct.unpack("<I", payload[:4])
        assert mode == 0

    def test_survey_mode(self):
        """Mode 1 (survey) sets duration and variance limit."""
        payload = build_cfg_tmode(
            mode=1,
            survey_min_dur=3600,
            survey_acc=10.0,
        )
        assert len(payload) == 40
        mode, _, _, _, _, svin_dur, svin_var = struct.unpack("<IdddfIf", payload)
        assert mode == 1
        assert svin_dur == 3600
        assert svin_var == pytest.approx(100.0)  # 10^2

    def test_fixed_mode(self):
        """Mode 2 (fixed) sets ECEF coordinates and variance."""
        payload = build_cfg_tmode(
            mode=2,
            fixed_pos=(4000000.0, 1000000.0, 5000000.0),
            fixed_pos_acc=0.5,
        )
        assert len(payload) == 40
        mode, x, y, z, var, _, _ = struct.unpack("<IdddfIf", payload)
        assert mode == 2
        assert x == pytest.approx(4000000.0)
        assert y == pytest.approx(1000000.0)
        assert z == pytest.approx(5000000.0)
        assert var == pytest.approx(0.25)  # 0.5^2


class TestParseEcefCoords:
    def test_valid_coords(self):
        from casictool import parse_ecef_coords
        result = parse_ecef_coords("4000000,1000000,5000000")
        assert result == (4000000.0, 1000000.0, 5000000.0)

    def test_with_spaces(self):
        from casictool import parse_ecef_coords
        result = parse_ecef_coords("4000000, 1000000, 5000000")
        assert result == (4000000.0, 1000000.0, 5000000.0)

    def test_invalid_count(self):
        from casictool import parse_ecef_coords
        with pytest.raises(ValueError, match="3 values"):
            parse_ecef_coords("4000000,1000000")

    def test_invalid_number(self):
        from casictool import parse_ecef_coords
        with pytest.raises(ValueError):
            parse_ecef_coords("4000000,abc,5000000")
```

## Validation Considerations

### Input Validation

1. **Survey time**: Must be positive integer
2. **Survey accuracy**: Must be positive float
3. **ECEF coordinates**: Must be 3 comma-separated floats
4. **Fixed position accuracy**: Must be positive float

### Mutual Exclusivity

The `--survey`, `--fixed-pos-ecef`, and `--mobile` options are mutually exclusive. Add validation:

```python
mode_options = [args.survey, args.fixed_pos_ecef, args.mobile]
if sum(bool(x) for x in mode_options) > 1:
    print("Error: --survey, --fixed-pos-ecef, and --mobile are mutually exclusive",
          file=sys.stderr)
    return 1
```

### Hardware Testing

After implementation, test against the physical receiver at `/dev/ttyUSB0`:

```bash
# Test survey mode
./casictool.py --survey --survey-time 60 --survey-acc 50
./casictool.py --show-config  # Verify mode changed

# Test fixed position (actual test site coordinates)
./casictool.py --fixed-pos-ecef -1144698.0455,6090335.4099,1504171.3914 --fixed-pos-acc 1
./casictool.py --show-config  # Verify position set

# Test mobile mode
./casictool.py --mobile
./casictool.py --show-config  # Verify mode=auto
```

## Files to Modify

| File | Changes |
|------|---------|
| `casic.py` | Add `build_cfg_tmode()` function |
| `casictool.py` | Add CLI arguments, `parse_ecef_coords()`, command handlers |
| `tests/test_timing_mode.py` | New test file for Phase 6 |

## Dependencies on Previous Phases

- Phase 1 core: `CasicConnection`, `send_and_wait_ack()`, `CFG_TMODE`
- Phase 2 show-config: `parse_cfg_tmode()`, `TimingModeConfig` (already implemented)

## Success Criteria

1. All unit tests pass (`make test`)
2. Lint and type checks pass (`make check`)
3. Hardware tests confirm mode changes on physical receiver
4. `--show-config` correctly displays timing mode after each change
