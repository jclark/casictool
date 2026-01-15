# Phase 3: NVM Operations (Save/Load/Reset)

## Overview

Phase 3 implements non-volatile memory (NVM) operations using two CASIC commands:
- **CFG-CFG (0x06 0x05)**: Save, load, or clear configuration sections
- **CFG-RST (0x06 0x02)**: Reset receiver and optionally clear data

## Command-Line Options

| Option | Description | CASIC Command |
|--------|-------------|---------------|
| `--save` | Save configuration changed by this command to NVM | CFG-CFG mode=1 |
| `--save-all` | Save all current configuration to NVM | CFG-CFG mode=1, mask=0xFFFF |
| `--reload` | Reload configuration from NVM (discard unsaved changes) | CFG-CFG mode=2, mask=0xFFFF |
| `--reset` | Cold start: reload NVM config and clear ephemeris/position/time | CFG-RST |
| `--factory-reset` | Factory start: restore NVM to defaults and reset | CFG-RST |

## Semantic Mapping from satpulsetool-gps

### --save vs --save-all

From the satpulsetool-gps man page:

> **--save**: Save the configuration changed by this command to GPS receiver's non-volatile memory. Exactly what is saved depends on the specific GPS receiver; satpulsetool will save the minimum possible to ensure that everything that was changed by this command is saved.

> **--save-all**: Save the current running configuration of the GPS receiver to its non-volatile memory.

**Implementation strategy:**

The key difference is that `--save` should only save sections that were actually modified by the current command, while `--save-all` saves everything. This requires:

1. Track which configuration sections were modified during command execution
2. Build the appropriate CFG-CFG mask based on what changed
3. For `--save-all`, use mask=0xFFFF to save everything

### --reload

> **--reload**: Reloads the configuration of the GPS receiver from its non-volatile memory. Any configuration settings that have not been saved will be lost. This can be used to undo any changes made by the satpulse daemon.

This maps directly to CFG-CFG with mode=2 (Load) and mask=0xFFFF.

### --reset

> **--reset**: Perform a reset that reloads the configuration of the GPS receiver from its non-volatile memory (as with the --reload option), and discards information about the last known position, current time, and satellite orbital data (both ephemeris and almanac).

This is a **cold start**: configuration is preserved, but navigation data is cleared. Maps to CFG-RST with:
- `navBbrMask`: Clear ephemeris, almanac, health, ionosphere, position, clock drift, oscillator params, UTC params, RTC (bits 0-8 = 0x01FF)
- `startMode`: Cold Start (2)

### --factory-reset

> **--factory-reset**: Restore the non-volatile memory of the GPS receiver to its default settings, and then perform a reset as with the --reset option.

This is a **factory start**: NVM is reset to defaults, then all navigation data is also cleared. Maps to CFG-RST with:
- `navBbrMask`: Clear everything including config (bits 0-9 = 0x03FF)
- `startMode`: Factory Start (3)

## Protocol Details

### CFG-CFG (0x06 0x05) - Save/Load Configuration

**Payload (4 bytes):**

| Offset | Type | Name | Description |
|--------|------|------|-------------|
| 0 | U2 | mask | Configuration sections to affect (bitmask) |
| 2 | U1 | mode | 0=Clear, 1=Save, 2=Load |
| 3 | U1 | reserved | Set to 0 |

**Mask bits:**

| Bit | Description | Related CFG Command |
|-----|-------------|---------------------|
| B0 | Port configuration | CFG-PRT |
| B1 | Message output configuration | CFG-MSG |
| B2 | Information messages | CFG-INF |
| B3 | Rate/Timing mode | CFG-RATE, CFG-TMODE |
| B4 | Time pulse | CFG-TP |
| B5 | GLONASS group delay | CFG-GROUP |

**Mode values:**

| Value | Description |
|-------|-------------|
| 0 | Clear (reset to defaults without saving) |
| 1 | Save (current RAM config to NVM) |
| 2 | Load (NVM config to RAM) |

### CFG-RST (0x06 0x02) - Reset Receiver

**Payload (4 bytes):**

| Offset | Type | Name | Description |
|--------|------|------|-------------|
| 0 | U2 | navBbrMask | BBR sections to clear (bitmask) |
| 2 | U1 | resetMode | Reset type |
| 3 | U1 | startMode | Start type |

**navBbrMask bits:**

| Bit | Description |
|-----|-------------|
| B0 | Ephemeris |
| B1 | Almanac |
| B2 | Health |
| B3 | Ionosphere |
| B4 | Position |
| B5 | Clock Drift |
| B6 | Oscillator Parameters |
| B7 | UTC Parameters |
| B8 | RTC |
| B9 | Configuration |

**resetMode values:**

| Value | Description |
|-------|-------------|
| 0 | Immediate Hardware Reset |
| 1 | Controlled Software Reset |
| 2 | Controlled Software Reset (GPS Only) |
| 4 | Hardware Reset after Shutdown |

**startMode values:**

| Value | Description |
|-------|-------------|
| 0 | Hot Start (use stored ephemeris/position) |
| 1 | Warm Start (use almanac, discard ephemeris) |
| 2 | Cold Start (discard all nav data, keep config) |
| 3 | Factory Start (reset config to defaults, discard all) |

## Implementation Plan

### 1. Add builder functions to casic.py

```python
# Mask bits for CFG-CFG
CFG_MASK_PORT = 0x0001      # B0: CFG-PRT
CFG_MASK_MSG = 0x0002       # B1: CFG-MSG
CFG_MASK_INF = 0x0004       # B2: CFG-INF
CFG_MASK_RATE = 0x0008      # B3: CFG-RATE, CFG-TMODE
CFG_MASK_TP = 0x0010        # B4: CFG-TP
CFG_MASK_GROUP = 0x0020     # B5: CFG-GROUP
CFG_MASK_NAVX = 0x0040      # B6: CFG-NAVX (if supported - needs verification)
CFG_MASK_ALL = 0xFFFF       # All sections

# BBR mask bits for CFG-RST
BBR_EPHEMERIS = 0x0001
BBR_ALMANAC = 0x0002
BBR_HEALTH = 0x0004
BBR_IONOSPHERE = 0x0008
BBR_POSITION = 0x0010
BBR_CLOCK_DRIFT = 0x0020
BBR_OSC_PARAMS = 0x0040
BBR_UTC_PARAMS = 0x0080
BBR_RTC = 0x0100
BBR_CONFIG = 0x0200

# Composite masks
BBR_NAV_DATA = 0x01FF       # All nav data (for cold start)
BBR_ALL = 0x03FF            # Everything (for factory reset)


def build_cfg_cfg(mask: int, mode: int) -> bytes:
    """Build CFG-CFG payload (4 bytes).

    Args:
        mask: Configuration sections to affect (bitmask)
        mode: 0=Clear, 1=Save, 2=Load
    """
    return struct.pack("<HBB", mask, mode, 0)


def build_cfg_rst(nav_bbr_mask: int, reset_mode: int, start_mode: int) -> bytes:
    """Build CFG-RST payload (4 bytes).

    Args:
        nav_bbr_mask: BBR sections to clear (bitmask)
        reset_mode: 0=HW immediate, 1=SW controlled, 2=SW GPS only, 4=HW after shutdown
        start_mode: 0=Hot, 1=Warm, 2=Cold, 3=Factory
    """
    return struct.pack("<HBB", nav_bbr_mask, reset_mode, start_mode)
```

### 2. Add command-line arguments to casictool.py

```python
# NVM operations group
nvm_group = parser.add_argument_group("Configuration Storage")
nvm_group.add_argument(
    "--save",
    action="store_true",
    help="Save configuration changed by this command to NVM",
)
nvm_group.add_argument(
    "--save-all",
    action="store_true",
    help="Save all current configuration to NVM",
)
nvm_group.add_argument(
    "--reload",
    action="store_true",
    help="Reload configuration from NVM (discard unsaved changes)",
)
nvm_group.add_argument(
    "--reset",
    action="store_true",
    help="Cold start: reload from NVM and clear navigation data",
)
nvm_group.add_argument(
    "--factory-reset",
    action="store_true",
    help="Factory reset: restore NVM to defaults and reset receiver",
)
```

### 3. Add helper functions to casictool.py

```python
def save_config(conn: CasicConnection, mask: int) -> bool:
    """Save configuration sections to NVM."""
    payload = build_cfg_cfg(mask, mode=1)  # mode=1 is Save
    return conn.send_and_wait_ack(CFG_CFG.cls, CFG_CFG.id, payload)


def load_config(conn: CasicConnection, mask: int) -> bool:
    """Load configuration sections from NVM."""
    payload = build_cfg_cfg(mask, mode=2)  # mode=2 is Load
    return conn.send_and_wait_ack(CFG_CFG.cls, CFG_CFG.id, payload)


def reset_receiver(conn: CasicConnection, factory: bool = False) -> bool:
    """Reset the receiver.

    Args:
        factory: If True, perform factory reset (clears NVM config).
                 If False, perform cold start (preserves NVM config).
    """
    if factory:
        nav_bbr_mask = BBR_ALL  # Clear everything including config
        start_mode = 3  # Factory Start
    else:
        nav_bbr_mask = BBR_NAV_DATA  # Clear nav data, preserve config
        start_mode = 2  # Cold Start

    reset_mode = 1  # Controlled Software Reset
    payload = build_cfg_rst(nav_bbr_mask, reset_mode, start_mode)

    # Note: After reset, receiver may not send ACK before restarting
    # We send the command and give it time to process
    conn.send(CFG_RST.cls, CFG_RST.id, payload)
    return True  # Can't reliably wait for ACK on reset
```

### 4. Implement --save tracking

For `--save` to work correctly, we need to track which configuration sections were modified. Add a simple mechanism:

```python
class ConfigChanges:
    """Track which configuration sections were modified."""

    def __init__(self) -> None:
        self.mask = 0

    def mark_port(self) -> None:
        self.mask |= CFG_MASK_PORT

    def mark_msg(self) -> None:
        self.mask |= CFG_MASK_MSG

    def mark_rate(self) -> None:
        self.mask |= CFG_MASK_RATE

    def mark_tp(self) -> None:
        self.mask |= CFG_MASK_TP

    # etc.
```

### 5. Main function integration

```python
def main() -> int:
    # ... existing argument parsing ...

    # Track configuration changes
    changes = ConfigChanges()

    # ... execute configuration commands, marking changes ...

    # Handle NVM operations (after configuration changes)
    if args.save_all:
        with CasicConnection(args.device, baudrate=args.speed) as conn:
            if save_config(conn, CFG_MASK_ALL):
                print("All configuration saved to NVM")
            else:
                print("Error: Failed to save configuration", file=sys.stderr)
                return 1
    elif args.save:
        if changes.mask == 0:
            print("Warning: No configuration changes to save")
        else:
            with CasicConnection(args.device, baudrate=args.speed) as conn:
                if save_config(conn, changes.mask):
                    print("Configuration saved to NVM")
                else:
                    print("Error: Failed to save configuration", file=sys.stderr)
                    return 1

    if args.reload:
        with CasicConnection(args.device, baudrate=args.speed) as conn:
            if load_config(conn, CFG_MASK_ALL):
                print("Configuration reloaded from NVM")
            else:
                print("Error: Failed to reload configuration", file=sys.stderr)
                return 1

    if args.factory_reset:
        with CasicConnection(args.device, baudrate=args.speed) as conn:
            reset_receiver(conn, factory=True)
            print("Factory reset initiated")
    elif args.reset:
        with CasicConnection(args.device, baudrate=args.speed) as conn:
            reset_receiver(conn, factory=False)
            print("Cold start reset initiated")

    return 0
```

## Option Interactions

### Mutual Exclusivity

- `--save` and `--save-all` are mutually exclusive (save changed vs save all)
- `--reset` and `--factory-reset` are mutually exclusive
- `--reload` should be exclusive with `--reset`/`--factory-reset` (reset already reloads)

### Ordering

When multiple operations are specified:

1. Execute configuration changes (e.g., `--survey`, `--gnss`)
2. Execute `--save` or `--save-all` (if specified)
3. Execute `--reload`, `--reset`, or `--factory-reset` (if specified)

The `--reload`/`--reset`/`--factory-reset` after `--save` makes sense: save changes, then reset to verify they persist.

### Use Cases

1. **Configure and save:**
   ```bash
   casictool --survey --survey-time 3000 --save
   ```

2. **Undo daemon changes:**
   ```bash
   casictool --reload
   ```

3. **Full factory reset:**
   ```bash
   casictool --factory-reset
   ```

4. **Clear navigation data (cold start):**
   ```bash
   casictool --reset
   ```

5. **Save everything (backup current state):**
   ```bash
   casictool --save-all
   ```

## Testing

### Unit Tests

1. Test `build_cfg_cfg` generates correct payloads for each mode
2. Test `build_cfg_rst` generates correct payloads for cold/factory start
3. Test mask bit constants are correct

### Integration Tests (with hardware)

1. `--save-all` then `--reload` should preserve settings
2. `--reset` should clear navigation but preserve configuration
3. `--factory-reset` should reset all configuration to defaults
4. After configuration change + `--save`, verify setting persists after `--reset`

## Notes

### Reset Behavior

After sending CFG-RST, the receiver will reset and may not send an ACK. The implementation should:
1. Send the reset command
2. Close the connection gracefully
3. Not wait for an ACK (it may not come)
4. Optionally wait a few seconds and reconnect to verify the reset completed

### CFG-NAVX Mask Bit

The documented mask bits (B0-B5) don't explicitly mention CFG-NAVX. Testing may be required to determine:
- Whether NAVX is saved under an existing bit (possibly B3 with RATE?)
- Whether there's an undocumented bit for NAVX
- Whether NAVX is always saved with --save-all (mask=0xFFFF)

For safety, `--save-all` uses 0xFFFF which should cover all sections.
