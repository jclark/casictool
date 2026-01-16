#!/usr/bin/env python3
"""Hardware integration tests for casictool.

Tests that casictool implementation works correctly on real hardware.
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass

from connection import CasicConnection
from job import (
    GNSS,
    NMEA,
    ConfigJob,
    ConfigProps,
    FixedMode,
    MobileMode,
    ResetMode,
    SaveMode,
    SurveyMode,
    TimePulse,
    execute_job,
    nmea_rates,
    probe_receiver,
    query_config_props,
)

# ============================================================================
# Test Result Types
# ============================================================================


@dataclass
class Pass:
    """Test passed."""

    pass


@dataclass
class Fail:
    """Test failed with mismatches."""

    mismatches: dict[str, dict[str, object]]


TestResult = Pass | Fail


# ============================================================================
# Test Framework
# ============================================================================


def verify(conn: CasicConnection, props: ConfigProps, log: logging.Logger) -> TestResult:
    """Apply props and verify they took effect."""
    job = ConfigJob(props=props)
    result = execute_job(conn, job, log)
    if not result.success:
        return Fail({"error": {"expected": "success", "actual": result.error}})
    actual = query_config_props(conn)
    mismatches: dict[str, dict[str, object]] = {}
    for key, expected_val in props.items():
        actual_val = actual.get(key)
        if actual_val != expected_val:
            mismatches[key] = {"expected": expected_val, "actual": actual_val}
    if mismatches:
        return Fail(mismatches)
    return Pass()


def verify_persist(
    conn: CasicConnection, props: ConfigProps, alt_props: ConfigProps, log: logging.Logger
) -> TestResult:
    """Verify save/reload round-trip.

    Proves that `props` was saved to NVM:
    1. Set `props` and save to NVM
    2. Set `alt_props` (different config) WITHOUT saving - this changes RAM
    3. Reload from NVM - should restore `props`, not `alt_props`
    4. If we get `props` back, the save worked; if we get `alt_props`, it didn't
    """
    # Set props and save to NVM
    job = ConfigJob(props=props, save=SaveMode.CHANGES)
    result = execute_job(conn, job, log)
    if not result.success:
        return Fail({"save": {"expected": "success", "actual": result.error}})

    # Set alt_props WITHOUT saving (changes RAM only)
    job = ConfigJob(props=alt_props)
    result = execute_job(conn, job, log)
    if not result.success:
        return Fail({"alt_config": {"expected": "success", "actual": result.error}})

    # Reload from NVM - should restore props
    job = ConfigJob(reset=ResetMode.RELOAD)
    result = execute_job(conn, job, log)
    if not result.success:
        return Fail({"reload": {"expected": "success", "actual": result.error}})

    # Verify we got props back, not alt_props
    actual = query_config_props(conn)
    mismatches: dict[str, dict[str, object]] = {}
    for key, expected_val in props.items():
        actual_val = actual.get(key)
        if actual_val != expected_val:
            mismatches[key] = {"expected": expected_val, "actual": actual_val}
    if mismatches:
        return Fail(mismatches)
    return Pass()


def format_props(props: ConfigProps) -> str:
    """Format ConfigProps for display."""
    parts = []
    if "gnss" in props:
        systems = sorted(g.value for g in props["gnss"])
        parts.append(f"gnss: {{{', '.join(systems)}}}")
    if "time_mode" in props:
        parts.append(f"time_mode: {props['time_mode']}")
    if "time_pulse" in props:
        parts.append(f"time_pulse: {props['time_pulse']}")
    if "nmea_out" in props:
        nmea_out = props["nmea_out"]
        # Show only enabled messages
        enabled = [nmea.name for nmea in NMEA if nmea_out[nmea.value] > 0]
        parts.append(f"nmea_out: {{{', '.join(enabled)}}}")
    return "{" + ", ".join(parts) + "}"


def log_result(log: logging.Logger, props: ConfigProps, result: TestResult) -> None:
    """Log test result."""
    if isinstance(result, Pass):
        log.info(f"PASS {format_props(props)}")
    else:
        for key, vals in result.mismatches.items():
            log.error(f"FAIL {key}: expected {vals['expected']}, got {vals['actual']}")


def run_tests(
    conn: CasicConnection,
    name: str,
    tests: list[ConfigProps],
    log: logging.Logger,
) -> tuple[int, int, list[ConfigProps]]:
    """Run a list of tests and return (passed, total, failed_tests)."""
    log.info(f"[{name}]")
    passed = 0
    failed: list[ConfigProps] = []

    for props in tests:
        result = verify(conn, props, log)
        log_result(log, props, result)
        if isinstance(result, Pass):
            passed += 1
        else:
            failed.append(props)

    return passed, len(tests), failed


def log_summary(log: logging.Logger, results: dict[str, tuple[int, int, list[ConfigProps]]]) -> int:
    """Log summary and return exit code (0 if all passed)."""
    all_passed = True
    total_passed = 0
    total_tests = 0

    for _name, (passed, total, failed) in results.items():
        total_passed += passed
        total_tests += total
        if failed:
            all_passed = False

    if all_passed:
        log.info(f"{total_passed}/{total_tests} passed")
    else:
        log.error(f"{total_passed}/{total_tests} passed")

    return 0 if all_passed else 1


def run_persist_tests(
    conn: CasicConnection,
    name: str,
    tests: list[ConfigProps],
    log: logging.Logger,
) -> tuple[int, int, list[ConfigProps]]:
    """Run persist tests for a list of ConfigProps.

    For each test, use the next item in the list as alt_props (wrap around for last).
    """
    log.info(f"[{name} persist]")
    passed = 0
    failed: list[ConfigProps] = []

    for i, props in enumerate(tests):
        # Use next item as alt_props (wrap around)
        alt_props = tests[(i + 1) % len(tests)]
        result = verify_persist(conn, props, alt_props, log)
        if isinstance(result, Pass):
            log.info(f"PASS persist {format_props(props)}")
            passed += 1
        else:
            for key, vals in result.mismatches.items():
                log.error(f"FAIL {key}: expected {vals['expected']}, got {vals['actual']}")
            failed.append(props)

    return passed, len(tests), failed


# ============================================================================
# Test Data
# ============================================================================

GNSS_TESTS: list[ConfigProps] = [
    {"gnss": {GNSS.GPS}},
    {"gnss": {GNSS.BDS}},
    {"gnss": {GNSS.GLO}},
    {"gnss": {GNSS.GPS, GNSS.BDS}},
    {"gnss": {GNSS.GPS, GNSS.BDS, GNSS.GLO}},
]

NMEA_TESTS: list[ConfigProps] = [
    # Single message
    {"nmea_out": nmea_rates(GGA=1)},
    # Multiple messages
    {"nmea_out": nmea_rates(GGA=1, RMC=1, GSV=1)},
    # Different single message
    {"nmea_out": nmea_rates(RMC=1)},
    # All messages
    {"nmea_out": nmea_rates(GGA=1, GLL=1, GSA=1, GSV=1, RMC=1, VTG=1, ZDA=1)},
]

# Sample ECEF position for testing
TEST_ECEF = (-1144698.0455, 6090335.4099, 1504171.3914)

TIME_MODE_TESTS: list[ConfigProps] = [
    # Mobile mode
    {"time_mode": MobileMode()},
    # Survey-in mode with different parameters
    {"time_mode": SurveyMode(min_dur=60, acc=50.0)},
    {"time_mode": SurveyMode(min_dur=120, acc=25.0)},
    # Fixed position mode
    {"time_mode": FixedMode(ecef=TEST_ECEF, acc=10.0)},
    # Back to mobile mode
    {"time_mode": MobileMode()},
]

PPS_TESTS: list[ConfigProps] = [
    # GPS time source with 100us pulse
    {"time_pulse": TimePulse(period=1.0, width=0.0001, time_gnss=GNSS.GPS)},
    # BDS time source with 1ms pulse
    {"time_pulse": TimePulse(period=1.0, width=0.001, time_gnss=GNSS.BDS)},
    # GLONASS time source
    {"time_pulse": TimePulse(period=1.0, width=0.0001, time_gnss=GNSS.GLO)},
    # Back to GPS
    {"time_pulse": TimePulse(period=1.0, width=0.0001, time_gnss=GNSS.GPS)},
]


# ============================================================================
# CLI
# ============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hardware integration tests for casictool",
    )
    parser.add_argument("-d", "--device", required=True, help="Serial device path")
    parser.add_argument("-s", "--speed", type=int, required=True, help="Baud rate")
    parser.add_argument("--gnss", action="store_true", help="Test GNSS configuration")
    parser.add_argument("--nmea", action="store_true", help="Test NMEA output")
    parser.add_argument("--time-mode", action="store_true", help="Test timing modes")
    parser.add_argument("--pps", action="store_true", help="Test PPS configuration")
    parser.add_argument(
        "--persist",
        action="store_true",
        help="Test NVM operations (save/reload + factory reset)",
    )
    parser.add_argument("--all", action="store_true", help="Run all test groups")
    parser.add_argument(
        "-l", "--packet-log", type=str, metavar="PATH", help="Log all packets to JSONL file"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress info messages (only show warnings and errors)",
    )

    args = parser.parse_args()

    # Setup logging (output to stdout for hwtest)
    log = logging.getLogger("casic_hwtest")
    handler = logging.StreamHandler(sys.stdout)
    if args.debug:
        level = logging.DEBUG
    elif args.quiet:
        level = logging.WARNING
    else:
        level = logging.INFO
    handler.setLevel(level)
    log.setLevel(level)
    handler.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(handler)

    # Determine which tests to run
    run_gnss = args.gnss or args.all
    run_nmea = args.nmea or args.all
    run_time_mode = getattr(args, "time_mode") or args.all
    run_pps = args.pps or args.all
    run_persist = args.persist

    # Check that at least one test group or --persist is specified
    if not (run_gnss or run_nmea or run_time_mode or run_pps or run_persist):
        parser.error(
            "No test groups specified. Use --gnss, --nmea, --time-mode, --pps, --persist, or --all"
        )

    # Connect to receiver
    try:
        conn = CasicConnection(args.device, args.speed, packet_log=args.packet_log, log=log)
    except Exception as e:
        log.error(f"error: could not connect to {args.device}: {e}")
        return 1

    # Probe receiver once at startup
    is_casic, version = probe_receiver(conn)
    if not is_casic:
        log.error("error: no response from receiver")
        conn.close()
        return 1
    if version:
        log.info(f"receiver: {version.sw_version}")
    else:
        log.info("receiver: CASIC (MON-VER not supported)")

    results: dict[str, tuple[int, int, list[ConfigProps]]] = {}

    try:
        # Run normal (RAM-only) tests if not --persist-only mode
        if not run_persist or (run_gnss or run_nmea or run_time_mode or run_pps):
            if run_gnss:
                results["GNSS"] = run_tests(conn, "GNSS", GNSS_TESTS, log)

            if run_nmea:
                results["NMEA"] = run_tests(conn, "NMEA", NMEA_TESTS, log)

            if run_time_mode:
                results["Time Mode"] = run_tests(conn, "time-mode", TIME_MODE_TESTS, log)

            if run_pps:
                results["PPS"] = run_tests(conn, "PPS", PPS_TESTS, log)

        # Run persist tests if --persist specified
        if run_persist:
            if run_gnss:
                results["GNSS Persist"] = run_persist_tests(
                    conn, "GNSS", GNSS_TESTS, log
                )

            if run_nmea:
                results["NMEA Persist"] = run_persist_tests(
                    conn, "NMEA", NMEA_TESTS, log
                )

            if run_time_mode:
                results["Time Mode Persist"] = run_persist_tests(
                    conn, "time-mode", TIME_MODE_TESTS, log
                )

            if run_pps:
                results["PPS Persist"] = run_persist_tests(conn, "PPS", PPS_TESTS, log)

    finally:
        conn.close()

    return log_summary(log, results)


if __name__ == "__main__":
    sys.exit(main())
