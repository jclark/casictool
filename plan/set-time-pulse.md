# Plan: Consolidate CFG-TP into single set_time_pulse() function

## Problems

1. **Double query/write:** When using `--pps --time-gnss` together, we poll CFG-TP twice and send it twice.

2. **Bug:** Using `--time-gnss BDS` alone incorrectly overwrites PPS width to 0.0001s default (line 394 in casictool.py). The intent should be to change only the time source, preserving current width/enable.

## Solution

Replace `set_pps()` and `set_time_gnss()` with a single `set_time_pulse()` function that:
- Takes optional parameters for each modifiable field
- Queries CFG-TP once
- Applies all provided modifications
- Sends a single CFG-TP

## Changes

### job.py

1. **Delete** `set_pps()` (lines 700-733)

2. **Delete** `set_time_gnss()` (lines 736-773)

3. **Add** new `set_time_pulse()` function:
```python
def set_time_pulse(
    conn: CasicConnection,
    *,
    width_seconds: float | None = None,
    enable: int | None = None,
    time_source: int | None = None,
    time_ref: int | None = None,
) -> bool:
    """Configure time pulse using read-modify-write.

    All parameters are optional - only provided values are modified,
    others are preserved from current config.

    Args:
        conn: Active CASIC connection
        width_seconds: Pulse width in seconds (0 to disable)
        enable: Enable mode (TP_OFF, TP_ON, TP_MAINTAIN, TP_FIX_ONLY)
        time_source: 0=GPS, 1=BDS, 2=GLO
        time_ref: TIME_REF_UTC or TIME_REF_SAT

    Returns:
        True if ACK received, False on NAK or timeout
    """
    # Query current config
    result = conn.poll(CFG_TP.cls, CFG_TP.id)
    if not result.success:
        return False

    current = parse_cfg_tp(result.payload)

    # Compute new values, preserving current where not specified
    new_enable = enable if enable is not None else current.enable
    if width_seconds is not None:
        if width_seconds == 0:
            new_enable = TP_OFF
            new_width_us = current.width_us  # preserve
        else:
            new_width_us = int(width_seconds * 1_000_000)
    else:
        new_width_us = current.width_us

    payload = build_cfg_tp(
        interval_us=current.interval_us,
        width_us=new_width_us,
        enable=new_enable,
        polarity=current.polarity,
        time_ref=time_ref if time_ref is not None else current.time_ref,
        time_source=time_source if time_source is not None else current.time_source,
        user_delay=current.user_delay,
    )
    return conn.send_and_wait_ack(CFG_TP.cls, CFG_TP.id, payload)
```

4. **Update** `execute_job()` (lines 986-1008) to use single `set_time_pulse()` call with optional fields:
```python
# Apply time pulse configuration
if "time_pulse" in job.props:
    tp = job.props["time_pulse"]
    time_source_map = {"GPS": 0, "BDS": 1, "GLO": 2}
    time_source = time_source_map[tp.time_gnss.value] if tp.time_gnss else None

    if set_time_pulse(
        conn,
        width_seconds=tp.width,
        enable=tp.enable,
        time_source=time_source,
        time_ref=tp.time_ref,
    ):
        if tp.width is not None:
            if tp.width == 0:
                log.info("PPS disabled")
            else:
                log.info(f"PPS: {tp.width}s width")
        if tp.time_gnss is not None:
            time_gnss_str = tp.time_gnss.value if tp.time_ref == TIME_REF_SAT else f"{tp.time_gnss.value}/UTC"
            log.info(f"PPS time GNSS: {time_gnss_str}")
        changes.mark_tp()
    else:
        result.success = False
        result.error = "failed to configure time pulse"
        return result
```

### job.py - Make TimePulse fields optional

Change `TimePulse` to allow partial specification:

```python
@dataclass(frozen=True)
class TimePulse:
    """PPS/time pulse configuration. None fields mean 'preserve current'."""

    width: float | None         # pulse width in seconds (0 to disable)
    time_gnss: GNSS | None     # time source constellation
    time_ref: int | None       # TIME_REF_UTC or TIME_REF_SAT
    enable: int | None         # TP_OFF, TP_ON, TP_MAINTAIN, or TP_FIX_ONLY
    period: float = 1.0               # pulse period (always 1.0 for now)
```

### casictool.py - Only set fields user specified

Update CLI parsing to only populate fields the user actually provided:

```python
if args.pps is not None or args.time_gnss:
    if args.pps is None:
        enable = None
        time_ref = None
    else:
        enable = TP_FIX_ONLY
        time_ref = TIME_REF_SAT

    if args.time_gnss is None:
        time_gnss = None
    else:
        time_gnss = parse_time_gnss_arg(args.time_gnss)

    props["time_pulse"] = TimePulse(
        width=args.pps,
        time_gnss=time_gnss,
        time_ref=time_ref,
        enable=enable,
    )
```

### casic_hwtest.py - Extend table-driven tests for partial updates

1. **Update `verify()` comparison** to handle partial `TimePulse` matching:

```python
def time_pulse_matches(expected: TimePulse, actual: TimePulse) -> bool:
    """Check if actual matches expected, ignoring None fields in expected."""
    if expected.width is not None and expected.width != actual.width:
        return False
    if expected.time_gnss is not None and expected.time_gnss != actual.time_gnss:
        return False
    if expected.time_ref is not None and expected.time_ref != actual.time_ref:
        return False
    if expected.enable is not None and expected.enable != actual.enable:
        return False
    return True

# In verify(), replace direct equality check with:
if key == "time_pulse":
    if not time_pulse_matches(expected_val, actual_val):
        mismatches[key] = {"expected": expected_val, "actual": actual_val}
else:
    if actual_val != expected_val:
        mismatches[key] = {"expected": expected_val, "actual": actual_val}
```

2. **Add partial update tests to `TP_TESTS`** that verify preservation:

```python
TP_TESTS: list[ConfigProps] = [
    # Disabled PPS (width=0 sets enable=TP_OFF)
    {"time_pulse": TimePulse(period=1.0, width=0.0, time_gnss=GNSS.GPS, time_ref=TIME_REF_SAT, enable=TP_OFF)},
    # BDS time source with 1ms pulse, enable=ON (always output), UTC time ref
    {"time_pulse": TimePulse(period=1.0, width=0.001, time_gnss=GNSS.BDS, time_ref=TIME_REF_UTC, enable=TP_ON)},
    # GLONASS time source with 100us pulse, enable=FIX_ONLY
    {"time_pulse": TimePulse(period=1.0, width=0.0001, time_gnss=GNSS.GLO, time_ref=TIME_REF_SAT, enable=TP_FIX_ONLY)},

    # Partial: change only time_gnss (width 0.0001 should be preserved from previous)
    {"time_pulse": TimePulse(time_gnss=GNSS.BDS, time_ref=TIME_REF_UTC)},

    # Partial: change only width (BDS/UTC should be preserved from previous)
    {"time_pulse": TimePulse(width=0.002, enable=TP_FIX_ONLY)},

    # Good state: full spec (last test leaves receiver in clean state)
    {"time_pulse": TimePulse(width=0.1, time_gnss=GNSS.GPS, time_ref=TIME_REF_SAT, enable=TP_FIX_ONLY)},
]
```

The partial tests rely on state from the previous test to verify preservation. If `--time-gnss BDS/UTC` clobbers width, the width would become the old buggy default (0.0001) instead of staying at 0.002 from the prior test.

### casic_hwtest.py - Rename --pps to --tp

Rename the test flag from `--pps` to `--tp` for consistency with "time pulse":
- Line 334: `--pps` → `--tp`
- Line 387: `run_pps` → `run_tp` (and `args.pps` → `args.tp`)
- Line 392, 395: Update error message references

## Verification

1. Run `make check` to ensure lint/typecheck/tests pass
2. Run hardware tests: `casic_hwtest --tp` to verify partial updates work correctly
