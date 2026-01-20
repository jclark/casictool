# Automatic dyn_model for Time Mode

## Problem

When configuring a receiver for time mode (survey or fixed position), the dynamic model should be set to Stationary for optimal performance. Currently this must be done manually.

## Solution

Automatically set dyn_model when changing time mode:

- `--survey` or `--fixed-pos-ecef` → dyn_model = Stationary (1)
- `--mobile` → dyn_model = Portable (0)

## Prerequisites

Requires navx-mask.md to be implemented first (for `build_cfg_navx()` with targeted mask bits).

## Dynamic Model Values (casic.py)

Add constants for dyModel field:

```python
# CFG-NAVX dynamic model values
DYN_MODEL_PORTABLE = 0
DYN_MODEL_STATIONARY = 1
DYN_MODEL_PEDESTRIAN = 2
DYN_MODEL_AUTOMOTIVE = 3
DYN_MODEL_MARINE = 4
DYN_MODEL_AIRBORNE_1G = 5
DYN_MODEL_AIRBORNE_2G = 6
DYN_MODEL_AIRBORNE_4G = 7
```

## build_cfg_navx() Extension

Add `dyn_model` parameter to `build_cfg_navx()`:

```python
def build_cfg_navx(
    nav_system: int | None = None,
    min_elev: int | None = None,
    dyn_model: int | None = None,
) -> bytes:
    """..."""
    mask = 0
    if nav_system is not None:
        mask |= NAVX_MASK_NAV_SYSTEM
    if min_elev is not None:
        mask |= NAVX_MASK_MIN_ELEV
    if dyn_model is not None:
        mask |= NAVX_MASK_DYN_MODEL

    return struct.pack(
        "<IBBBBBBbbbBHfffffff",
        mask,
        dyn_model or 0,
        ...
    )
```

## job.py Changes

Modify the time mode functions to also set dyn_model:

```python
def set_time_mode_survey(conn: CasicConnection, ..., changes: ConfigChanges) -> bool:
    # Set CFG-TMODE for survey mode
    if not _set_tmode_survey(conn, duration, accuracy):
        return False
    changes.mark_tmode()

    # Also set dyn_model to Stationary
    payload = build_cfg_navx(dyn_model=DYN_MODEL_STATIONARY)
    if not conn.send_and_wait_ack(CFG_NAVX.cls, CFG_NAVX.id, payload):
        return False
    changes.mark_navx()
    return True

def set_time_mode_fixed(conn: CasicConnection, ..., changes: ConfigChanges) -> bool:
    # Set CFG-TMODE for fixed position
    if not _set_tmode_fixed(conn, ecef, accuracy):
        return False
    changes.mark_tmode()

    # Also set dyn_model to Stationary
    payload = build_cfg_navx(dyn_model=DYN_MODEL_STATIONARY)
    if not conn.send_and_wait_ack(CFG_NAVX.cls, CFG_NAVX.id, payload):
        return False
    changes.mark_navx()
    return True

def set_time_mode_mobile(conn: CasicConnection, changes: ConfigChanges) -> bool:
    # Set CFG-TMODE for mobile mode
    if not _set_tmode_mobile(conn):
        return False
    changes.mark_tmode()

    # Also set dyn_model to Portable
    payload = build_cfg_navx(dyn_model=DYN_MODEL_PORTABLE)
    if not conn.send_and_wait_ack(CFG_NAVX.cls, CFG_NAVX.id, payload):
        return False
    changes.mark_navx()
    return True
```

## casic_hwtest.py Changes

Add `dyn_model` to `ConfigProps` and `query_config_props()` so hardware tests can verify the automatic behavior. Note: `dyn_model` is an internal implementation detail and should NOT be shown in `--show-config`.

Update `TIME_MODE_TESTS` to include expected `dyn_model` values:

```python
TIME_MODE_TESTS: list[ConfigProps] = [
    {"time_mode": SurveyMode(min_dur=60, acc=50.0), "dyn_model": DYN_MODEL_STATIONARY},
    {"time_mode": SurveyMode(min_dur=120, acc=25.0), "dyn_model": DYN_MODEL_STATIONARY},
    {"time_mode": FixedMode(ecef=TEST_ECEF, acc=10.0), "dyn_model": DYN_MODEL_STATIONARY},
    {"time_mode": MobileMode(), "dyn_model": DYN_MODEL_PORTABLE},
]
```

The `verify()` function already compares all keys in `props` against `query_config_props()`, so adding `dyn_model` to both will automatically verify the side effect.

## Benefits

- Optimal time mode performance with Stationary model
- No manual configuration needed
- Consistent behavior across survey/fixed/mobile modes
