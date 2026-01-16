# Add Standard Python Logging to casictool

## Summary
Add logging using Python's standard `logging` module. Follow Unix conventions: stdout is for machine-readable output only (e.g., `--show-config`), everything else goes to stderr via logging.

## CLI Flags
- **Default**: INFO level
- **--debug**: DEBUG level
- **--quiet / -q**: WARNING level (suppress info messages)

## Logging Levels
- **ERROR**: NAK responses, timeouts, command failures
- **WARNING**: Non-critical issues (e.g., "No configuration changes to save")
- **INFO**: What's happening ("GNSS constellations set: GPS, BDS", "Enabled GGA", etc.)
- **DEBUG**: Extra detail for troubleshooting (not duplicating packet log)

## Files to Modify

### 1. job.py
- Add `import logging`
- Update `execute_job` signature from:
  ```python
  def execute_job(conn, job, log_file: TextIO = sys.stderr)
  ```
  to:
  ```python
  def execute_job(conn: CasicConnection, job: ConfigJob, log: logging.Logger) -> CommandResult
  ```
- Remove `from typing import TextIO` (no longer needed)
- Remove `import sys` if no longer used
- Add logging calls throughout `execute_job`:
  - INFO: Before each operation ("Setting GNSS constellations...")
  - ERROR: When operations fail
  - WARNING: For non-critical issues (e.g., line 729: "No configuration changes to save")

### 2. casictool.py
- Add `--debug` argument (DEBUG level)
- Add `-q` / `--quiet` argument (WARNING level)
- Default level is INFO
- Add `import logging`
- Update `run_casictool(argv: list[str]) -> CommandResult` signature to:
  ```python
  def run_casictool(argv: list[str], log: logging.Logger) -> CommandResult
  ```
- `main()` creates logger with appropriate level and passes to `run_casictool`
- `run_casictool` passes logger to `execute_job` (no default value)
- Remove `result.operations` usage - those messages become `log.info()` calls
- `print_result()` only prints `--show-config` output to stdout

### 3. casic_hwtest.py
- Add `import logging`
- Add `--debug` and `-q` / `--quiet` flags (same as casictool.py)
- Logger outputs to **stdout** (not stderr) - all output is logging
- Create logger in `main()` and pass to `verify()` and `verify_persist()`
- Update `verify()` and `verify_persist()` signatures to accept logger
- Convert ALL output to logging, terse Unix style:
  - `log.info("PASS gnss={GPS, BDS}")`
  - `log.error("FAIL gnss: expected {GPS}, got {BDS}")`
  - `log.info("5/5 passed")` or `log.error("3/5 passed")`
- No banners, no decoration, no excessive whitespace

## Implementation Details

### Logger Setup Pattern
```python
import logging

def main() -> int:
    args = parse_args(...)

    # Setup logging
    log = logging.getLogger("casictool")
    handler = logging.StreamHandler(sys.stderr)  # stdout for casic_hwtest.py
    if args.debug:
        level = logging.DEBUG
    elif args.quiet:
        level = logging.WARNING
    else:
        level = logging.INFO
    handler.setLevel(level)
    log.setLevel(level)
    formatter = logging.Formatter("%(message)s")  # just the message
    handler.setFormatter(formatter)
    log.addHandler(handler)
    ...
```

Format is just `"%(message)s"` - each line should be meaningful on its own. Include level prefix in the message text: `log.error("error: ...")`, `log.warning("warning: ...")`. Start messages with lowercase, no trailing period.

### Log Messages in execute_job

Each `result.operations.append()` becomes a `log.info()` or `log.warning()`. Each error path gets `log.error()`.

| Level | Message |
|-------|---------|
| INFO | "GNSS set: GPS, BDS" |
| ERROR | "error: failed to set GNSS" |
| INFO | "mobile mode enabled" |
| ERROR | "error: failed to set mobile mode" |
| INFO | "survey-in mode: 2000s, 20.0m" |
| ERROR | "error: failed to set survey-in mode" |
| INFO | "fixed position: ECEF (x, y, z)" |
| ERROR | "error: failed to set fixed position" |
| INFO | "PPS disabled" |
| INFO | "PPS: 0.0001s width" |
| ERROR | "error: failed to configure PPS" |
| INFO | "PPS time source: GPS" |
| ERROR | "error: failed to set PPS time source" |
| INFO | "NMEA GGA enabled" |
| INFO | "NMEA GLL disabled" |
| ERROR | "error: failed to set NMEA GGA" |
| INFO | "config saved to NVM" |
| ERROR | "error: failed to save config" |
| WARNING | "warning: no config changes to save" |
| INFO | "config reloaded from NVM" |
| ERROR | "error: failed to reload config" |
| INFO | "cold start initiated" |
| INFO | "factory reset initiated" |

Note: `result.operations` list is no longer needed - remove from `CommandResult` and all usages.

### Distinguishing NAK vs Timeout (Future Enhancement)
Currently command functions return `bool`, losing NAK/timeout distinction. This PR adds logging infrastructure; protocol-level distinction (NAK vs timeout) can be enhanced later by having `send_and_wait_ack` return richer types.

## Execution Order
1. **job.py**: Update `execute_job` signature and add logging calls
2. **casictool.py**: Add `--debug` arg, update `run_casictool` signature, create logger in `main()`
3. **casic_hwtest.py**: Update `verify`/`verify_persist` signatures, create logger in `main()`
4. Run `make check` to verify
