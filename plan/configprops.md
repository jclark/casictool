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
- `save: SaveMode` - what to save to NVM (NONE, CHANGES, ALL)
- `reset: ResetMode` - what reset to perform (NONE, RELOAD, COLD, FACTORY)
- `show_config: bool` - query and return current config

Both live in `job.py` - the middle layer between CLI and protocol.

## Design

### Property Value Types (dataclasses)

Group related settings into dataclasses (like Go's structs):

```python
from dataclasses import dataclass
from enum import Enum
from typing import Literal

class GNSS(Enum):
    """GNSS constellation identifiers."""
    GPS = "GPS"
    GAL = "GAL"
    BDS = "BDS"
    GLO = "GLO"

class NMEA(Enum):
    """NMEA sentence types."""
    GGA = "GGA"
    GLL = "GLL"
    GSA = "GSA"
    GSV = "GSV"
    RMC = "RMC"
    VTG = "VTG"
    ZDA = "ZDA"

class SaveMode(Enum):
    """What to save to NVM."""
    NONE = "none"           # don't save
    CHANGES = "changes"     # save only what was changed by this job
    ALL = "all"             # save all current configuration

class ResetMode(Enum):
    """What kind of reset to perform."""
    NONE = "none"           # no reset
    RELOAD = "reload"       # reload config from NVM (discard unsaved changes)
    COLD = "cold"           # reload from NVM + cold start (clear nav data)
    FACTORY = "factory"     # restore NVM to factory defaults + cold start

@dataclass(frozen=True)
class TimePulse:
    """PPS/time pulse configuration."""
    period: float             # pulse period in seconds (1.0 = 1Hz PPS)
    width: float              # pulse width in seconds
    time_gnss: GNSS           # time source for PPS alignment

@dataclass(frozen=True)
class MobileMode:
    """Mobile/auto mode - antenna position may change."""
    pass

@dataclass(frozen=True)
class SurveyMode:
    """Survey-in mode - determine fixed position by surveying."""
    min_dur: int              # minimum duration in seconds
    acc: float                # target accuracy in meters

@dataclass(frozen=True)
class FixedMode:
    """Fixed position mode - use known antenna position."""
    ecef: tuple[float, float, float]  # ECEF coordinates in meters
    acc: float                         # position accuracy in meters

# Union of time modes (use isinstance() or match/case to check which)
TimeMode = MobileMode | SurveyMode | FixedMode

# NMEA output rates: maps sentence type to rate (0 = disabled, 1 = every fix)
NMEARates = dict[NMEA, int]
```

### ConfigProps (TypedDict)

```python
from typing import TypedDict, Literal

class ConfigProps(TypedDict, total=False):
    gnss: set[GNSS]           # enabled constellations
    time_mode: TimeMode       # mobile, survey, or fixed position mode
    time_pulse: TimePulse     # PPS configuration
    nmea_out: NMEARates       # NMEA message output rates
```

### ConfigJob (dataclass)

```python
@dataclass
class ConfigJob:
    """Complete specification of what casictool should do."""
    props: ConfigProps | None = None       # Properties to set
    save: SaveMode = SaveMode.NONE         # What to save to NVM
    reset: ResetMode = ResetMode.NONE      # What kind of reset to perform
    show_config: bool = False              # Query and return current config
```

### Usage

```python
# Build a job
job = ConfigJob(
    props={'gnss': {GNSS.GPS, GNSS.BDS}, 'time_pulse': TimePulse(period=1.0, width=0.0001, time_gnss=GNSS.GPS)},
    save=SaveMode.CHANGES,
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
| `gnss` | `set[GNSS]` | Enabled constellations |
| `time_mode` | `TimeMode` | MobileMode, SurveyMode, or FixedMode |
| `time_pulse` | `TimePulse` | PPS configuration |
| `nmea_out` | `dict[NMEA, int]` | NMEA message rates |

### Operations (part of ConfigJob, not ConfigProps)

NVM operations use enums on ConfigJob, not properties:

```python
# Set props and save just what changed
job = ConfigJob(props={'gnss': {GNSS.GPS}}, save=SaveMode.CHANGES)

# Set props and save all config
job = ConfigJob(props={'gnss': {GNSS.GPS}}, save=SaveMode.ALL)

# Reload config from NVM (discard unsaved changes)
job = ConfigJob(reset=ResetMode.RELOAD)

# Cold start (reload from NVM + clear nav data)
job = ConfigJob(reset=ResetMode.COLD)

# Factory reset (restore NVM defaults + cold start)
job = ConfigJob(reset=ResetMode.FACTORY)

# Just query current config
job = ConfigJob(show_config=True)
```

### CLI Mapping

```
--gnss GPS,BDS              → {'gnss': {GNSS.GPS, GNSS.BDS}}
--pps 0.0001 --time-gnss GPS → {'time_pulse': TimePulse(period=1.0, width=0.0001, time_gnss=GNSS.GPS)}
--survey 3600 10            → {'time_mode': SurveyMode(min_dur=3600, acc=10.0)}
--fixed-pos-ecef X,Y,Z 10   → {'time_mode': FixedMode(ecef=(X,Y,Z), acc=10.0)}
--mobile                    → {'time_mode': MobileMode()}
--nmea-out GGA,RMC          → {'nmea_out': {NMEA.GGA: 1, NMEA.RMC: 1}}
--save                      → save=SaveMode.CHANGES
--save-all                  → save=SaveMode.ALL
--reload                    → reset=ResetMode.RELOAD
--reset                     → reset=ResetMode.COLD
--factory-reset             → reset=ResetMode.FACTORY
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
verify(conn, {'gnss': {GNSS.GPS}})
verify(conn, {'gnss': {GNSS.GPS, GNSS.BDS}})
verify(conn, {'time_pulse': TimePulse(period=1.0, width=0.0001, time_gnss=GNSS.GPS)})
verify(conn, {'time_mode': SurveyMode(min_dur=3600, acc=10.0)})
```

## Changes Required

### casic.py
- Keep protocol layer as-is (parsing, building binary payloads)
- Low-level dataclasses stay (they map to binary format)

### job.py (refactor)
- Add `ConfigProps` TypedDict
- Add enums: `GNSS`, `NMEA`, `SaveMode`, `ResetMode`
- Add property value dataclasses: `TimePulse`, `MobileMode`, `SurveyMode`, `FixedMode`
- Add type alias: `TimeMode = MobileMode | SurveyMode | FixedMode`
- Add type alias: `NMEARates = dict[NMEA, int]`
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
