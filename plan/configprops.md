# ConfigProps: Property-Based Configuration for casictool

## Goal

Replace the current `ConfigJob` approach with a property-based model that makes verification trivial. Instead of manually checking each field, we compare "what we asked for" with "what we got".

## Key Insight

In Python, a dict naturally represents "properties that are set":
- Presence of a key means the property is set
- Absence means it wasn't specified
- Comparison is just dict operations

Use `TypedDict` for type safety while keeping dict semantics.

## Design

### Property Value Types (dataclasses)

Group related settings into dataclasses (like Go's structs):

```python
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class TimePulse:
    """PPS/time pulse configuration."""
    width: float              # pulse width in seconds
    time_gnss: str            # time source: 'GPS', 'BDS', 'GLO'

@dataclass(frozen=True)
class Survey:
    """Survey-in mode parameters."""
    min_dur: int              # minimum duration in seconds
    acc: float                # target accuracy in meters

@dataclass(frozen=True)
class FixedPosition:
    """Fixed position mode parameters."""
    ecef: tuple[float, float, float]  # ECEF coordinates in meters
    acc: float                         # position accuracy in meters

@dataclass(frozen=True)
class NMEARates:
    """NMEA message output rates (0 = disabled)."""
    gga: int = 0
    rmc: int = 0
    gsv: int = 0
    gsa: int = 0
    vtg: int = 0
    zda: int = 0
```

### ConfigProps (TypedDict)

```python
from typing import TypedDict, Literal

class ConfigProps(TypedDict, total=False):
    # GNSS constellation selection - high level, not a bitmask
    gnss: set[str]                    # e.g., {'GPS', 'BDS', 'GLO'}

    # Timing mode - one of these will be set
    mode: Literal['mobile', 'survey', 'fixed']
    survey: Survey                    # present when mode='survey'
    fixed_pos: FixedPosition          # present when mode='fixed'

    # Time pulse / PPS
    time_pulse: TimePulse

    # NMEA output
    nmea: NMEARates
```

### Usage

```python
# What we want to set
target: ConfigProps = {
    'gnss': {'GPS', 'BDS'},
    'time_pulse': TimePulse(width=0.0001, time_gnss='GPS'),
}

# Apply to receiver
apply_config(conn, target)

# Query back
actual = query_config(conn)

# Verification - automatic!
def check_config(target: ConfigProps, actual: ConfigProps) -> ConfigProps:
    """Return properties that don't match."""
    mismatches: ConfigProps = {}
    for key, expected in target.items():
        if actual.get(key) != expected:
            mismatches[key] = {'expected': expected, 'actual': actual.get(key)}
    return mismatches
```

### Property Summary

| Property | Type | Description |
|----------|------|-------------|
| `gnss` | `set[str]` | Enabled constellations: `{'GPS', 'BDS', 'GLO'}` |
| `mode` | `Literal` | `'mobile'`, `'survey'`, or `'fixed'` |
| `survey` | `Survey` | Survey parameters (when mode='survey') |
| `fixed_pos` | `FixedPosition` | Fixed position (when mode='fixed') |
| `time_pulse` | `TimePulse` | PPS configuration |
| `nmea` | `NMEARates` | NMEA message rates |

### Operations (not properties)

NVM operations are not properties - they're actions:

```python
# Separate from properties
apply_config(conn, props, save=True)   # Save after applying
apply_config(conn, props, save='all')  # Save all config
reload_config(conn)                     # Reload from NVM
factory_reset(conn)                     # Factory reset
```

### CLI Mapping

```
--gnss GPS,BDS              → {'gnss': {'GPS', 'BDS'}}
--pps 0.0001 --time-gnss GPS → {'time_pulse': TimePulse(width=0.0001, time_gnss='GPS')}
--survey 3600 10            → {'mode': 'survey', 'survey': Survey(min_dur=3600, acc=10.0)}
--fixed-pos-ecef X,Y,Z 10   → {'mode': 'fixed', 'fixed_pos': FixedPosition(ecef=(X,Y,Z), acc=10.0)}
--mobile                    → {'mode': 'mobile'}
--nmea-out GGA,RMC          → {'nmea': NMEARates(gga=1, rmc=1)}
--save                      → save=True (operation, not property)
```

### Hardware Test Integration

Tests become trivial:

```python
def verify(conn, props: ConfigProps) -> TestResult:
    """Apply props and verify they took effect."""
    apply_config(conn, props)
    actual = query_config(conn)
    mismatches = check_config(props, actual)
    if mismatches:
        return Fail(mismatches)
    return Pass()

# Tests are one-liners
verify(conn, {'gnss': {'GPS'}})
verify(conn, {'gnss': {'GPS', 'BDS'}})
verify(conn, {'time_pulse': TimePulse(width=0.0001, time_gnss='GPS')})
verify(conn, {'mode': 'survey', 'survey': Survey(min_dur=3600, acc=10.0)})
```

## Changes Required

### New: configprops.py
- `ConfigProps` TypedDict
- Property value dataclasses: `TimePulse`, `Survey`, `FixedPosition`, `NMEARates`
- `check_config(target, actual) -> ConfigProps` - find mismatches

### casic.py
- Keep protocol layer as-is (parsing, building binary payloads)
- Low-level dataclasses stay (they map to binary format)

### job.py
- `apply_config(conn, props: ConfigProps, save=False)` - apply properties
- `query_config(conn) -> ConfigProps` - query current config
- Translation layer: ConfigProps ↔ low-level binary dataclasses

### casictool.py
- Build `ConfigProps` from CLI args
- Call `apply_config()` with props
- Display result using `query_config()`

### casic_hwtest.py
- Use `verify(conn, props)` pattern
- Tests are just ConfigProps dicts
