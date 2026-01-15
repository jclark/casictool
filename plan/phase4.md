# Phase 4 Implementation Plan: NMEA Output

## Overview

Phase 4 implements the `--nmea-out` option to configure NMEA message output rates using CFG-MSG (0x06 0x01). This enables users to enable/disable specific NMEA sentences and control their output rate.

## CLI Interface Design

```bash
# Enable specific NMEA messages (rate=1 means every fix)
casictool --nmea-out GGA,RMC,ZDA

# Enable with custom rate (every N fixes)
casictool --nmea-out GGA,RMC --nmea-rate 5

# Disable specific messages
casictool --nmea-out -GGA,-GSV

# Enable some, disable others in one command
casictool --nmea-out GGA,RMC,-GSV,-VTG

# Save after configuration
casictool --nmea-out GGA,RMC,ZDA --save
```

**Supported NMEA Messages** (Class 0x4E):
| Message | ID | Description |
|---------|-----|-------------|
| GGA | 0x00 | GPS fix data (position, quality, satellites) |
| GLL | 0x01 | Geographic position (lat/lon) |
| GSA | 0x02 | DOP and active satellites |
| GSV | 0x03 | Satellites in view |
| RMC | 0x04 | Recommended minimum data |
| VTG | 0x05 | Course over ground and speed |
| ZDA | 0x08 | Time and date |

## Implementation Steps

### Step 1: Add `build_cfg_msg_set()` to casic.py

**Location**: After `build_cfg_msg_query()` (around line 765)

```python
def build_cfg_msg_set(msg_cls: int, msg_id: int, rate: int) -> bytes:
    """Build CFG-MSG SET payload (4 bytes).

    Args:
        msg_cls: Message class to configure
        msg_id: Message ID within class
        rate: Output rate (0=off, 1=every fix, N=every N fixes)

    Returns:
        4-byte payload: [cls(U1)][id(U1)][rate(U2)]
    """
    return struct.pack("<BBH", msg_cls, msg_id, rate)
```

### Step 2: Add `set_nmea_message_rate()` to casictool.py

**Location**: After `query_nmea_rates()` (around line 127)

```python
def set_nmea_message_rate(conn: CasicConnection, message_name: str, rate: int) -> bool:
    """Set output rate for a specific NMEA message.

    Args:
        conn: Active CASIC connection
        message_name: NMEA message name (GGA, RMC, etc.)
        rate: Output rate (0=disable, 1+=enable at rate)

    Returns:
        True if acknowledged, False on failure
    """
    # Lookup message ID from name
    nmea_lookup = {name: msg for name, msg in NMEA_MESSAGES}
    msg = nmea_lookup.get(message_name.upper())
    if msg is None:
        return False

    payload = build_cfg_msg_set(msg.cls, msg.id, rate)
    return conn.send_and_wait_ack(CFG_MSG.cls, CFG_MSG.id, payload)
```

### Step 3: Add `mark_msg()` to ConfigChanges class

**Location**: In ConfigChanges class (around line 51)

```python
def mark_msg(self) -> None:
    """Mark message output configuration as changed."""
    self.mask |= CFG_MASK_MSG
```

### Step 4: Add CLI Arguments

**Location**: After timing_group arguments (around line 270)

```python
nmea_group = parser.add_argument_group("NMEA Message Output")
nmea_group.add_argument(
    "--nmea-out",
    type=str,
    metavar="MSGS",
    help="Configure NMEA message output. Comma-separated list of messages "
         "(GGA,GLL,GSA,GSV,RMC,VTG,ZDA). Prefix with '-' to disable (e.g., -GSV)"
)
nmea_group.add_argument(
    "--nmea-rate",
    type=int,
    default=1,
    metavar="N",
    help="Output rate for enabled NMEA messages (1=every fix, N=every N fixes, default: 1)"
)
```

### Step 5: Add Argument Parsing Function

**Location**: After argument validation section (around line 310)

```python
def parse_nmea_out(nmea_str: str) -> tuple[list[str], list[str]]:
    """Parse --nmea-out argument into enable and disable lists.

    Args:
        nmea_str: Comma-separated message list (e.g., "GGA,RMC,-GSV")

    Returns:
        Tuple of (enable_list, disable_list)
    """
    valid_messages = {"GGA", "GLL", "GSA", "GSV", "RMC", "VTG", "ZDA"}
    enable = []
    disable = []

    for item in nmea_str.split(","):
        item = item.strip().upper()
        if not item:
            continue
        if item.startswith("-"):
            msg = item[1:]
            if msg in valid_messages:
                disable.append(msg)
            else:
                raise ValueError(f"Unknown NMEA message: {msg}")
        else:
            if item in valid_messages:
                enable.append(item)
            else:
                raise ValueError(f"Unknown NMEA message: {item}")

    return enable, disable
```

### Step 6: Add Execution Logic in main()

**Location**: After timing mode execution, before NVM operations (around line 375)

```python
# NMEA message output configuration
if args.nmea_out:
    try:
        enable_msgs, disable_msgs = parse_nmea_out(args.nmea_out)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Enable messages at specified rate
    for msg_name in enable_msgs:
        if set_nmea_message_rate(conn, msg_name, args.nmea_rate):
            print(f"Enabled {msg_name} (rate={args.nmea_rate})")
            changes.mark_msg()
        else:
            print(f"Error: Failed to configure {msg_name}", file=sys.stderr)
            return 1

    # Disable messages (rate=0)
    for msg_name in disable_msgs:
        if set_nmea_message_rate(conn, msg_name, 0):
            print(f"Disabled {msg_name}")
            changes.mark_msg()
        else:
            print(f"Error: Failed to disable {msg_name}", file=sys.stderr)
            return 1
```

### Step 7: Add Rate Validation

**Location**: In argument validation section (around line 305)

```python
# Validate NMEA rate
if args.nmea_rate is not None and args.nmea_rate < 0:
    print("Error: --nmea-rate must be non-negative", file=sys.stderr)
    return 1
```

## Test Plan

### Unit Tests (tests/test_casic.py)

```python
def test_build_cfg_msg_set():
    """Test CFG-MSG SET payload construction."""
    # Enable GGA at rate 1
    payload = build_cfg_msg_set(0x4E, 0x00, 1)
    assert payload == bytes([0x4E, 0x00, 0x01, 0x00])

    # Disable RMC
    payload = build_cfg_msg_set(0x4E, 0x04, 0)
    assert payload == bytes([0x4E, 0x04, 0x00, 0x00])

    # Enable GSV at rate 5
    payload = build_cfg_msg_set(0x4E, 0x03, 5)
    assert payload == bytes([0x4E, 0x03, 0x05, 0x00])


def test_parse_nmea_out():
    """Test --nmea-out argument parsing."""
    # Enable only
    enable, disable = parse_nmea_out("GGA,RMC,ZDA")
    assert enable == ["GGA", "RMC", "ZDA"]
    assert disable == []

    # Disable only
    enable, disable = parse_nmea_out("-GSV,-VTG")
    assert enable == []
    assert disable == ["GSV", "VTG"]

    # Mixed
    enable, disable = parse_nmea_out("GGA,RMC,-GSV,-GLL")
    assert enable == ["GGA", "RMC"]
    assert disable == ["GSV", "GLL"]

    # Case insensitive
    enable, disable = parse_nmea_out("gga,Rmc,-gsv")
    assert enable == ["GGA", "RMC"]
    assert disable == ["GSV"]

    # Invalid message
    with pytest.raises(ValueError, match="Unknown NMEA message"):
        parse_nmea_out("GGA,INVALID")


def test_config_changes_mark_msg():
    """Test ConfigChanges tracks MSG modifications."""
    changes = ConfigChanges()
    assert changes.mask == 0
    changes.mark_msg()
    assert changes.mask & CFG_MASK_MSG != 0
```

### Integration Tests (Manual with Hardware)

```bash
# Test 1: Enable single message
casictool -d /dev/ttyUSB0 -s 38400 --nmea-out GGA --show-config
# Verify: GGA shows rate=1 in output

# Test 2: Enable multiple messages
casictool -d /dev/ttyUSB0 -s 38400 --nmea-out GGA,RMC,ZDA --show-config
# Verify: All three show rate=1

# Test 3: Disable messages
casictool -d /dev/ttyUSB0 -s 38400 --nmea-out -GGA,-RMC --show-config
# Verify: GGA and RMC show rate=0

# Test 4: Custom rate
casictool -d /dev/ttyUSB0 -s 38400 --nmea-out GGA --nmea-rate 5 --show-config
# Verify: GGA shows rate=5

# Test 5: Save configuration
casictool -d /dev/ttyUSB0 -s 38400 --nmea-out GGA,RMC --save
# Power cycle receiver, then verify settings persisted

# Test 6: Invalid message name
casictool -d /dev/ttyUSB0 -s 38400 --nmea-out INVALID
# Verify: Error message displayed, exit code != 0
```

## File Changes Summary

| File | Changes |
|------|---------|
| casic.py | Add `build_cfg_msg_set()` function |
| casictool.py | Add `mark_msg()` to ConfigChanges |
| casictool.py | Add `set_nmea_message_rate()` function |
| casictool.py | Add `parse_nmea_out()` function |
| casictool.py | Add `--nmea-out` and `--nmea-rate` arguments |
| casictool.py | Add execution logic in main() |
| tests/test_casic.py | Add unit tests for new functions |

## Dependencies

- **Existing Infrastructure**: CFG-MSG query already implemented
- **Prerequisite**: Phase 3 (NVM operations) complete for `--save` integration

## Estimated Complexity

- **Code additions**: ~80 lines in casic.py/casictool.py
- **Test additions**: ~50 lines in tests/test_casic.py
- **Risk**: Low - follows established patterns from Phase 6
