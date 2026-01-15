# Hardware Integration Test Design for casictool

## Goal

A tool to test that the casictool **implementation** works correctly on real hardware. This tests both that:

1. The code does what it's supposed to do (implementation correctness)
2. The receiver responds as expected (protocol correctness)

Helpful diagnostics should identify whether failures are bugs in casictool vs unexpected hardware behavior.

## Key Requirements

1. **Helpful diagnostics** - Not just PASS/FAIL, but descriptive messages showing:
   - What was tested
   - What command was executed
   - Expected vs actual configuration
   - Whether the issue looks like a bug or hardware quirk

2. **Selective testing** - Run specific test groups via flags:
   - `--gnss` - GNSS constellation configuration
   - `--timing` - Timing modes (survey, fixed, mobile)
   - `--nmea` - NMEA message output
   - `--pps` - PPS/time pulse configuration
   - `--persist` - Modifier: test that changes survive save/reload
   - `--all` - Everything

3. **Separate from unit tests** - Not in `tests/` directory, different invocation

## CLI Design (flags style)

```bash
casic_hwtest -d /dev/ttyUSB0 -s 38400 --gnss           # Test GNSS only
casic_hwtest -d /dev/ttyUSB0 -s 38400 --gnss --timing  # Test GNSS and timing
casic_hwtest -d /dev/ttyUSB0 -s 38400 --all            # Run everything
casic_hwtest --list                                     # Show available test groups
```

Flags:
- `-d`, `--device` - Serial device path (required)
- `-s`, `--speed` - Baud rate (required)
- `--gnss` - Test GNSS constellation configuration
- `--timing` - Test timing modes (survey, fixed, mobile)
- `--nmea` - Test NMEA message output configuration
- `--pps` - Test PPS/time pulse configuration
- `--persist` - Modifier: also test NVM operations (save/reload/factory-reset)
- `--all` - Run all test groups (--gnss --timing --nmea --pps)
- `--verbose` - Show more detail
- `--list` - List available test groups

`--persist` must be specified explicitly to authorize NVM changes. Without it, NVM is never touched.

```bash
casic_hwtest -d /dev/ttyUSB0 -s 38400 --gnss              # Test GNSS in RAM only
casic_hwtest -d /dev/ttyUSB0 -s 38400 --gnss --persist    # Test GNSS + save/reload + factory-reset
casic_hwtest -d /dev/ttyUSB0 -s 38400 --all --persist     # Everything including NVM operations
```

## Output Format

### Example output

```
=== GNSS Configuration Tests ===

Testing: {'gnss': {'GPS'}}
  PASS

Testing: {'gnss': {'GPS', 'BDS'}}
  PASS

Testing: {'gnss': {'GLO'}}
  FAIL: gnss: expected {'GLO'}, got {'GPS', 'BDS'}

=== Summary ===
GNSS: 2/3 passed
  FAIL: {'gnss': {'GLO'}}
```

The ConfigProps dict is both the test input and the expected output - self-documenting.

## Test Implementation Pattern

Using ConfigProps (see `plan/configprops.md`), tests are just data - no per-test assertion code needed:

```python
def verify(conn, props: ConfigProps) -> TestResult:
    """Apply props and verify they took effect."""
    apply_config(conn, props)
    actual = query_config(conn)
    mismatches = check_config(props, actual)
    if mismatches:
        return Fail(mismatches)
    return Pass()
```

Test cases are lists of ConfigProps:

```python
GNSS_TESTS = [
    {'gnss': {'GPS'}},
    {'gnss': {'BDS'}},
    {'gnss': {'GLO'}},
    {'gnss': {'GPS', 'BDS'}},
    {'gnss': {'GPS', 'BDS', 'GLO'}},
]

PPS_TESTS = [
    {'time_pulse': TimePulse(width=0.0001, time_gnss='GPS')},
    {'time_pulse': TimePulse(width=0.001, time_gnss='BDS')},
]

TIMING_TESTS = [
    {'mode': 'mobile'},
    {'mode': 'survey', 'survey': Survey(min_dur=60, acc=50.0)},
    {'mode': 'fixed', 'fixed_pos': FixedPosition(ecef=(X, Y, Z), acc=10.0)},
]
```

Running tests is just iterating over the lists:

```python
for props in GNSS_TESTS:
    result = verify(conn, props)
    print_result(props, result)
```

## File Structure

```
casic_hwtest.py     # Main script with CLI, test data, and runner
```

Single file keeps it simple. Test data grouped by category.

## Test Categories

### --gnss
- Enable GPS only
- Enable BDS only
- Enable GLONASS only
- Enable GPS+BDS
- Enable GPS+BDS+GLONASS
- (verify each combination actually takes effect)

### --timing
- Set mobile mode
- Set survey mode (min duration, accuracy)
- Set fixed position (ECEF coords, accuracy)
- Verify mode transitions work correctly

### --nmea
- Enable single message (GGA)
- Enable multiple messages (GGA,RMC,GSV)
- Disable all messages
- Verify rate changes persist

### --pps
- Set pulse width
- Set time source (GPS, BDS, GLONASS)
- Verify settings applied correctly

### --persist (modifier)

Without `--persist`: Tests only verify config changes work in RAM. NVM is never touched.

With `--persist`: Also verifies NVM operations using the same ConfigProps pattern:

```python
def verify_persist(conn, props: ConfigProps, alt_props: ConfigProps) -> TestResult:
    """Verify save/reload round-trip."""
    apply_config(conn, props, save=True)   # Set X, save
    apply_config(conn, alt_props)           # Set Y (different)
    reload_config(conn)                     # Reload from NVM
    actual = query_config(conn)
    mismatches = check_config(props, actual)  # Should be X, not Y
    if mismatches:
        return Fail(mismatches)
    return Pass()
```

**Factory reset** (once, at end):

```python
FACTORY_DEFAULTS: ConfigProps = {
    'gnss': {'GPS', 'BDS', 'GLO'},  # To be verified
    'mode': 'mobile',
    # ... other defaults
}

def verify_factory_reset(conn) -> TestResult:
    factory_reset(conn)
    actual = query_config(conn)
    mismatches = check_config(FACTORY_DEFAULTS, actual)
    if mismatches:
        return Fail(mismatches)
    return Pass()
```

## Implementation Order

**Prerequisite**: Implement ConfigProps (see `plan/configprops.md`)

1. **Framework + --gnss**: Create `casic_hwtest.py` with:
   - CLI argument parsing
   - `verify()` function using ConfigProps
   - GNSS_TESTS list
   - Test runner that iterates and prints results

2. **Add remaining test groups**: --pps, --timing, --nmea (just add test data lists)

3. **Add --persist**: Add `verify_persist()` and `verify_factory_reset()` functions

## Verification

Run against hardware at `/dev/ttyUSB0`:
```bash
./casic_hwtest.py -d /dev/ttyUSB0 -s 38400 --gnss
./casic_hwtest.py -d /dev/ttyUSB0 -s 38400 --gnss --persist
./casic_hwtest.py -d /dev/ttyUSB0 -s 38400 --all
```
