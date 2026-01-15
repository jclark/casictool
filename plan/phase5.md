# Phase 5: GNSS Configuration Implementation Plan

## Overview

Phase 5 implements the `--gnss` option using CFG-NAVX (0x06 0x07). This allows users to select which GNSS constellations are enabled on the receiver. The CASIC protocol supports GPS, BDS (BeiDou), and GLONASS only.

## Current State

### Already Implemented
- `CFG_NAVX` message ID constant (`casic.py:66`)
- `NavEngineConfig` dataclass with `nav_system` field and `gnss_list` property (`casic.py:516-571`)
- `parse_cfg_navx()` function to parse response payload (`casic.py:699-744`)
- GNSS display in `--show-config` via `NavEngineConfig.format()` (`casic.py:569-571`)
- Query of CFG-NAVX in `show_config()` (`casictool.py:183-186`)

### Missing
- `build_cfg_navx()` function to construct SET payload
- `--gnss` CLI argument
- `parse_gnss_arg()` to validate user input
- `set_gnss()` function to configure constellations
- `CFG_MASK_NAVX` or appropriate mask for `--save` tracking
- Tests for new functionality

## Implementation Steps

### Step 1: Add `build_cfg_navx()` to `casic.py`

The CFG-NAVX payload is 44 bytes. The receiver requires a **read-modify-write** approach: query current config, modify `nav_system`, send back the complete payload.

```python
def build_cfg_navx(config: NavEngineConfig, nav_system: int | None = None) -> bytes:
    """Build CFG-NAVX payload (44 bytes) from existing config.

    Args:
        config: Current NavEngineConfig from parse_cfg_navx()
        nav_system: New constellation mask, or None to keep existing

    Returns:
        44-byte payload ready for CFG-NAVX SET command
    """
```

**Implementation details:**
- Accept a `NavEngineConfig` object (from querying current config)
- Optionally override `nav_system` field
- Pack all fields back into 44-byte payload using same struct format as parser
- Set `mask` to 0xFFFFFFFF to apply all fields

This read-modify-write approach ensures we don't accidentally reset other navigation parameters (dynamic model, fix mode, DOP limits, etc.) to defaults.

### Step 2: Add GNSS mask constant to `casic.py`

According to the plan doc, CFG-NAVX may fall under CFG_MASK_RATE (B3) based on the CFG-CFG mask bits. Verify this or add appropriate constant:

```python
# Note: CFG-NAVX appears to use CFG_MASK_RATE for save operations
# based on plan/casictool.md section 4.6
```

### Step 3: Add `parse_gnss_arg()` to `casictool.py`

Parse user input like `--gnss GPS,BDS,GLO` or `--gnss GPS`:

```python
VALID_GNSS = {"GPS", "BDS", "GLO", "GLN", "GLONASS"}  # GLO/GLN/GLONASS aliases

def parse_gnss_arg(gnss_str: str) -> int:
    """Parse --gnss argument into navSystem bitmask.

    Args:
        gnss_str: Comma-separated list (e.g., "GPS,BDS,GLO")

    Returns:
        Bitmask: B0=GPS, B1=BDS, B2=GLONASS

    Raises:
        ValueError: If unknown constellation specified
    """
```

**Validation:**
- Accept: GPS, BDS, GLO, GLN, GLONASS (GLO/GLN/GLONASS all map to bit 2)
- Reject: GAL, GALILEO, QZSS, NAVIC, SBAS (with clear error message)

### Step 4: Add `set_gnss()` to `casictool.py`

```python
def set_gnss(conn: CasicConnection, nav_system: int) -> bool:
    """Configure GNSS constellation selection using read-modify-write.

    Steps:
    1. Query current CFG-NAVX configuration
    2. Modify nav_system field only
    3. Send complete payload back to receiver
    4. Wait for ACK

    Args:
        conn: Active CASIC connection
        nav_system: Bitmask (B0=GPS, B1=BDS, B2=GLONASS)

    Returns:
        True if ACK received, False on NAK or timeout
    """
    # Query current config
    result = conn.poll(CFG_NAVX.cls, CFG_NAVX.id)
    if not result.success:
        return False

    # Parse and modify
    config = parse_cfg_navx(result.payload)
    payload = build_cfg_navx(config, nav_system=nav_system)

    # Send and wait for ACK
    return conn.send_and_wait_ack(CFG_NAVX.cls, CFG_NAVX.id, payload)
```

### Step 5: Add CLI argument and integration

In `main()`:

1. Add argument to argument group:
```python
gnss_group = parser.add_argument_group("GNSS Configuration")
gnss_group.add_argument(
    "--gnss",
    type=str,
    metavar="SYSTEMS",
    help="Enable GNSS constellations (GPS,BDS,GLO). "
         "Disables constellations not listed. "
         "Note: GAL, QZSS, NAVIC, SBAS not supported by this receiver.",
)
```

2. Parse before connection:
```python
gnss_mask: int | None = None
if args.gnss:
    try:
        gnss_mask = parse_gnss_arg(args.gnss)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
```

3. Execute within connection context:
```python
if gnss_mask is not None:
    if set_gnss(conn, gnss_mask):
        systems = []
        if gnss_mask & 0x01: systems.append("GPS")
        if gnss_mask & 0x02: systems.append("BDS")
        if gnss_mask & 0x04: systems.append("GLONASS")
        print(f"GNSS constellations set: {', '.join(systems)}")
        changes.mark_rate()  # Or appropriate mask
    else:
        print("Error: Failed to set GNSS constellations", file=sys.stderr)
        return 1
```

4. Update `has_any_op` check.

### Step 6: Add `ConfigChanges.mark_gnss()` (optional)

If GNSS config uses a different mask bit than RATE, add a method. Otherwise, use `mark_rate()` since both CFG-TMODE and CFG-NAVX likely share the same save category.

### Step 7: Add tests to `tests/test_casic.py`

```python
class TestBuildCfgNavx:
    def test_gps_only(self) -> None:
        ...

    def test_all_constellations(self) -> None:
        ...

    def test_payload_structure(self) -> None:
        ...

class TestParseGnssArg:
    def test_single_constellation(self) -> None:
        ...

    def test_multiple_constellations(self) -> None:
        ...

    def test_case_insensitive(self) -> None:
        ...

    def test_glonass_aliases(self) -> None:
        # GLO, GLN, GLONASS all map to bit 2
        ...

    def test_invalid_constellation(self) -> None:
        ...

    def test_unsupported_galileo(self) -> None:
        ...
```

## CFG-NAVX Payload Structure (44 bytes)

Per `plan/casictool.md` section 4.8:

| Offset | Type | Name | Description |
|--------|------|------|-------------|
| 0 | U4 | mask | Parameter mask (which fields to set) |
| 4 | U1 | dyModel | Dynamic model |
| 5 | U1 | fixMode | Fix mode (1=2D, 2=3D, 3=Auto) |
| ... | ... | ... | ... |
| 13 | U1 | navSystem | **GNSS constellation mask** |
| ... | ... | ... | ... |

**navSystem bits:**
- B0: GPS
- B1: BDS (BeiDou)
- B2: GLONASS

## Files to Modify

1. **casic.py**
   - Add `build_cfg_navx()` function

2. **casictool.py**
   - Add `parse_gnss_arg()` function
   - Add `set_gnss()` function
   - Add `--gnss` argument to parser
   - Add execution logic in main()
   - Update `has_any_op` check

3. **tests/test_casic.py**
   - Add `TestBuildCfgNavx` class
   - Add `TestParseGnssArg` class

## Risk Assessment

**Low Risk:**
- Parsing and validation logic
- Test additions
- CLI argument addition

**Medium Risk:**
- `build_cfg_navx()` payload construction - must match exactly what receiver expects
- Read-modify-write pattern if implemented

**Mitigation:**
- Test with actual hardware using `--show-config` before and after
- Start with a simple test case (e.g., GPS only)
- Verify ACK response before considering operation successful

## Testing Plan

1. Unit tests for `parse_gnss_arg()` and `build_cfg_navx()`
2. Integration test with hardware:
   ```bash
   # Query current config
   ./casictool.py -d /dev/ttyUSB0 -s 38400 --show-config

   # Set GPS only
   ./casictool.py -d /dev/ttyUSB0 -s 38400 --gnss GPS

   # Verify change
   ./casictool.py -d /dev/ttyUSB0 -s 38400 --show-config

   # Set all constellations
   ./casictool.py -d /dev/ttyUSB0 -s 38400 --gnss GPS,BDS,GLO --save
   ```
