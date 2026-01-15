# ConfigProps: Property-Based Configuration for casictool

## Goal

Refactor configuration handling so verification is trivial: compare "what we asked for" with "what we got".

## Key Concepts

**ConfigProps** (TypedDict) = what properties to set/query
- Presence of a key means the property is set
- Absence means it wasn't specified
- Comparison is just dict operations

**ConfigJob** (dataclass) = complete job specification
- `props: ConfigProps` - properties to set
- `save: bool` - save to NVM after changes
- `reload: bool` - reload config from NVM
- `factory_reset: bool` - factory reset
- `show_config: bool` - query and return current config

Both live in `job.py` - the middle layer between CLI and protocol.

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

### ConfigJob (dataclass)

```python
@dataclass
class ConfigJob:
    """Complete specification of what casictool should do."""
    props: ConfigProps | None = None   # Properties to set
    save: bool = False                  # Save to NVM after changes
    reload: bool = False                # Reload config from NVM
    factory_reset: bool = False         # Factory reset
    show_config: bool = False           # Query and return current config
```

### Usage

```python
# Build a job
job = ConfigJob(
    props={'gnss': {'GPS', 'BDS'}, 'time_pulse': TimePulse(width=0.0001, time_gnss='GPS')},
    save=True,
    show_config=True,
)

# Execute it - returns the current config after operations
result: ConfigProps = execute_job(conn, job)

# Verification - automatic!
def check_config(target: ConfigProps, actual: ConfigProps) -> dict:
    """Return properties that don't match."""
    mismatches = {}
    for key, expected in target.items():
        if actual.get(key) != expected:
            mismatches[key] = {'expected': expected, 'actual': actual.get(key)}
    return mismatches

# Check that what we set is what we got
mismatches = check_config(job.props, result)
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

### Operations (part of ConfigJob, not ConfigProps)

NVM operations are flags on ConfigJob, not properties:

```python
# Set props and save
job = ConfigJob(props={'gnss': {'GPS'}}, save=True)

# Just reload from NVM
job = ConfigJob(reload=True)

# Factory reset
job = ConfigJob(factory_reset=True)

# Just query current config
job = ConfigJob(show_config=True)
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
    job = ConfigJob(props=props, show_config=True)
    result = execute_job(conn, job)
    mismatches = check_config(props, result)
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

### casic.py
- Keep protocol layer as-is (parsing, building binary payloads)
- Low-level dataclasses stay (they map to binary format)

### job.py (refactor)
- Add `ConfigProps` TypedDict
- Add property value dataclasses: `TimePulse`, `Survey`, `FixedPosition`, `NMEARates`
- Refactor `ConfigJob` to use `props: ConfigProps` instead of individual fields
- `execute_job(conn, job: ConfigJob) -> ConfigProps` - run job, return current config
- `check_config(target, actual) -> dict` - find mismatches
- Translation layer: ConfigProps ↔ low-level binary dataclasses

### casictool.py
- Build `ConfigJob` from CLI args (props + operation flags)
- Call `execute_job()`
- Display result ConfigProps

### casic_hwtest.py
- Build ConfigJob with props to test
- Call `execute_job()`
- Use `check_config()` to verify
