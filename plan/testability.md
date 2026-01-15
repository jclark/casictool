# Casictool Testability Refactoring Plan

## Goal
Refactor casictool for better testability following clock-model patterns:
1. Layered architecture with clean separation of concerns
2. Programmatic API returning structured data (not just exit codes)
3. Separate hardware integration test script (`casic_hwtest.py`)

## Current State

**casictool.py** (624 lines):
- `main()` does everything: arg parsing, validation, connection, operations
- Returns exit codes (int), not structured data
- Mixes CLI concerns with command implementation

**casic.py** (840 lines):
- Protocol layer with dataclasses: `ReceiverConfig`, `PortConfig`, `NavEngineConfig`, etc.
- `CasicConnection` class for serial I/O
- Currently contains some command logic (should be protocol only)

## New File Structure

```
casic.py        - Protocol only: framing, parsing, dataclasses, CasicConnection
job.py          - ConfigJob, execute_job, individual commands (NEW)
casictool.py    - CLI only: arg parsing, main(), calls job.execute_job
casic_hwtest.py - Hardware integration tests (NEW)
```

## Architecture Changes

### 1. casic.py (Protocol Layer)

Keep only CASIC protocol concerns:
- Message framing (pack_msg, parse_msg, calc_checksum)
- Message IDs and constants
- CasicConnection (send, receive, poll, send_and_wait_ack)
- Config dataclasses (ReceiverConfig, PortConfig, NavEngineConfig, etc.)
- Payload parsers (parse_cfg_prt, parse_cfg_navx, etc.)
- Payload builders (build_cfg_tmode, build_cfg_navx, etc.)

### 2. job.py (Command Layer) - NEW

ConfigJob, execute_job, and individual command implementations:

```python
"""CASIC receiver command implementations."""

from dataclasses import dataclass, field
from typing import TextIO
import sys

from casic import (
    CasicConnection, ReceiverConfig,
    CFG_NAVX, CFG_TMODE, CFG_MSG, CFG_CFG, CFG_RST,
    parse_cfg_navx, build_cfg_navx, build_cfg_tmode,
    # ... other imports
)

@dataclass
class CommandResult:
    """Result of command operations."""
    config_before: ReceiverConfig | None = None
    config_after: ReceiverConfig | None = None
    operations: list[str] = field(default_factory=list)
    success: bool = True
    error: str | None = None


def query_config(conn: CasicConnection) -> ReceiverConfig:
    """Query all CFG messages and return receiver configuration."""


def set_gnss(conn: CasicConnection, nav_system: int) -> bool:
    """Configure GNSS constellation selection."""


def set_survey_mode(conn: CasicConnection, min_dur: int, acc: float) -> bool:
    """Configure receiver for survey-in mode."""


def set_fixed_position(conn: CasicConnection, ecef: tuple[float, float, float], acc: float) -> bool:
    """Configure receiver with fixed ECEF position."""


def set_mobile_mode(conn: CasicConnection) -> bool:
    """Configure receiver for mobile/auto mode."""


def set_nmea_message_rate(conn: CasicConnection, message_name: str, rate: int) -> bool:
    """Set output rate for a specific NMEA message."""


def save_config(conn: CasicConnection, mask: int) -> bool:
    """Save configuration sections to NVM."""


def load_config(conn: CasicConnection, mask: int) -> bool:
    """Load configuration sections from NVM."""


def reset_receiver(conn: CasicConnection, factory: bool = False) -> None:
    """Reset the receiver."""


# Argument parsing helpers (used by CLI and potentially other callers)
def parse_ecef_coords(coord_str: str) -> tuple[float, float, float]:
    """Parse comma-separated ECEF coordinates."""


def parse_nmea_out(nmea_str: str) -> list[str]:
    """Parse NMEA message list."""


def parse_gnss_arg(gnss_str: str) -> int:
    """Parse GNSS constellation string to bitmask."""


@dataclass
class ConfigJob:
    """Specification of configuration operations to perform."""
    # Timing mode (mutually exclusive)
    survey: tuple[int, float] | None = None       # (min_dur_secs, acc_meters)
    fixed_pos: tuple[tuple[float, float, float], float] | None = None  # (ecef, acc)
    mobile: bool = False

    # GNSS selection
    gnss: int | None = None                       # Bitmask: B0=GPS, B1=BDS, B2=GLO

    # NMEA output
    nmea_enable: list[str] | None = None          # Messages to enable (others disabled)

    # NVM operations (mutually exclusive)
    save_mask: int | None = None                  # Save these sections to NVM
    reload: bool = False                          # Load from NVM
    reset: bool = False                           # Cold start
    factory_reset: bool = False                   # Factory reset


def execute_job(
    conn: CasicConnection,
    job: ConfigJob,
    log_file: TextIO = sys.stderr,
) -> CommandResult:
    """Execute configuration job and return structured result.

    This is the main programmatic entry point for other tools.
    Always queries config before and after operations.
    """
```

### 3. casictool.py (CLI Layer)

Only CLI concerns:

```python
"""CASIC GPS receiver configuration tool - CLI interface."""

import argparse
import sys

from casic import CasicConnection
from job import (
    ConfigJob, CommandResult, execute_job, query_config,
    parse_ecef_coords, parse_nmea_out, parse_gnss_arg,
    VALID_NMEA_MESSAGES,
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(...)
    # All argument definitions
    return parser.parse_args(argv)


def run_casictool(argv: list[str]) -> CommandResult:
    """Run casictool with given arguments.

    Callable from other programs. Returns structured result.
    """
    args = parse_args(argv)
    # Validation, then call run_commands()


def main() -> None:
    """CLI entry point."""
    try:
        result = run_casictool(sys.argv[1:])
        if result.config_after and should_print_config(result):
            print(result.config_after.format())
        if not result.success:
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
```

### 4. casic_hwtest.py (Hardware Tests) - NEW

Separate script that exercises jobs on real hardware. **Detailed design deferred to a future plan.**

Key requirements:
- Uses `ConfigJob` and `execute_job()` programmatically
- Compares `ReceiverConfig` dataclasses directly (no output parsing)
- Needs higher-level test helpers for concise test writing
- Must provide helpful diagnostics on failure (not bare asserts)
- Should restore original config after each test

## Files Summary

| File | Responsibility |
|------|----------------|
| casic.py | Protocol: framing, parsing, dataclasses, CasicConnection |
| job.py | ConfigJob, execute_job, query_config, individual commands |
| casictool.py | CLI: parse_args, main, user output formatting |
| casic_hwtest.py | Hardware tests: exercises jobs on real device |

## Key Design Decisions

1. **job.py owns ConfigJob and CommandResult**: Not in casic.py since it's about commands, not protocol.

2. **ConfigJob + execute_job() is the programmatic API**: Job dataclass specifies what to do, execute_job() runs it and returns structured result with before/after configs.

3. **casictool.py is thin**: Just CLI parsing and calling execute_job(). Could be replaced by another CLI without touching job.py.

4. **Hardware tests use commands directly**: No CLI parsing overhead, direct dataclass comparison.

5. **Arg parsing helpers in job.py**: `parse_ecef_coords`, `parse_nmea_out`, `parse_gnss_arg` move to job.py since they're not CLI-specific (could be used by other callers).

## Implementation Order

1. Create job.py, move command functions from casictool.py
2. Add ConfigJob and CommandResult dataclasses to job.py
3. Add execute_job() function that runs a ConfigJob
4. Refactor casictool.py to import from job.py
5. Extract parse_args() in casictool.py
6. Simplify main() to build ConfigJob from args and call execute_job()
7. Run `make check` to verify no regressions

**casic_hwtest.py**: Deferred to separate plan (needs proper test framework design)
