#!/usr/bin/env python3
"""Hardware integration tests for casictool.

Tests that casictool implementation works correctly on real hardware.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

from casic import CasicConnection
from job import (
    GNSS,
    NMEA,
    ConfigJob,
    ConfigProps,
    FixedMode,
    MobileMode,
    SurveyMode,
    TimePulse,
    execute_job,
    nmea_rates,
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


def verify(conn: CasicConnection, props: ConfigProps) -> TestResult:
    """Apply props and verify they took effect."""
    job = ConfigJob(props=props)
    result = execute_job(conn, job, log_file=sys.stderr)
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


def print_result(props: ConfigProps, result: TestResult) -> None:
    """Print test result."""
    print(f"Testing: {format_props(props)}")
    if isinstance(result, Pass):
        print("  PASS")
    else:
        for key, vals in result.mismatches.items():
            print(f"  FAIL: {key}: expected {vals['expected']}, got {vals['actual']}")


def run_tests(
    conn: CasicConnection,
    name: str,
    tests: list[ConfigProps],
) -> tuple[int, int, list[ConfigProps]]:
    """Run a list of tests and return (passed, total, failed_tests)."""
    print(f"\n=== {name} Tests ===\n")
    passed = 0
    failed: list[ConfigProps] = []

    for props in tests:
        result = verify(conn, props)
        print_result(props, result)
        print()
        if isinstance(result, Pass):
            passed += 1
        else:
            failed.append(props)

    return passed, len(tests), failed


def print_summary(results: dict[str, tuple[int, int, list[ConfigProps]]]) -> int:
    """Print summary and return exit code (0 if all passed)."""
    print("=== Summary ===")
    all_passed = True

    for name, (passed, total, failed) in results.items():
        status = f"{passed}/{total} passed"
        print(f"{name}: {status}")
        if failed:
            all_passed = False
            for props in failed:
                print(f"  FAIL: {format_props(props)}")

    return 0 if all_passed else 1


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
    parser.add_argument("--all", action="store_true", help="Run all test groups")

    args = parser.parse_args()

    # Determine which tests to run
    run_gnss = args.gnss or args.all
    run_nmea = args.nmea or args.all
    run_time_mode = getattr(args, "time_mode") or args.all
    run_pps = args.pps or args.all

    # Check that at least one test group is specified
    if not (run_gnss or run_nmea or run_time_mode or run_pps):
        parser.error("No test groups specified. Use --gnss, --nmea, --time-mode, --pps, or --all")

    # Connect to receiver
    try:
        conn = CasicConnection(args.device, args.speed)
    except Exception as e:
        print(f"Error: Could not connect to {args.device}: {e}", file=sys.stderr)
        return 1

    results: dict[str, tuple[int, int, list[ConfigProps]]] = {}

    try:
        if run_gnss:
            results["GNSS"] = run_tests(conn, "GNSS Configuration", GNSS_TESTS)

        if run_nmea:
            results["NMEA"] = run_tests(conn, "NMEA Output", NMEA_TESTS)

        if run_time_mode:
            results["Time Mode"] = run_tests(conn, "Time Mode", TIME_MODE_TESTS)

        if run_pps:
            results["PPS"] = run_tests(conn, "PPS", PPS_TESTS)

    finally:
        conn.close()

    return print_summary(results)


if __name__ == "__main__":
    sys.exit(main())
