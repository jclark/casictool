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
    ConfigJob,
    ConfigProps,
    check_config,
    execute_job,
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
    mismatches = check_config(props, actual)
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
        msgs = sorted(f"{k.value}:{v}" for k, v in nmea_out.items())
        parts.append(f"nmea_out: {{{', '.join(msgs)}}}")
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


# ============================================================================
# CLI
# ============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hardware integration tests for casictool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test groups:
  --gnss       Test GNSS constellation configuration
  --nmea       Test NMEA message output configuration
  --time-mode  Test timing modes (survey, fixed, mobile)
  --pps        Test PPS/time pulse configuration
  --all        Run all test groups

Modifiers:
  --persist    Also test NVM operations (save/reload/factory-reset)
""",
    )
    parser.add_argument("-d", "--device", required=True, help="Serial device path")
    parser.add_argument("-s", "--speed", type=int, required=True, help="Baud rate")
    parser.add_argument("--gnss", action="store_true", help="Test GNSS configuration")
    parser.add_argument("--nmea", action="store_true", help="Test NMEA output")
    parser.add_argument("--time-mode", action="store_true", help="Test timing modes")
    parser.add_argument("--pps", action="store_true", help="Test PPS configuration")
    parser.add_argument("--all", action="store_true", help="Run all test groups")
    parser.add_argument("--persist", action="store_true", help="Test NVM operations")
    parser.add_argument("--verbose", action="store_true", help="Show more detail")

    args = parser.parse_args()

    # Determine which tests to run
    run_gnss = args.gnss or args.all
    run_nmea = args.nmea or args.all
    run_time_mode = getattr(args, "time_mode") or args.all
    run_pps = args.pps or args.all
    run_persist = args.persist

    # Check that at least one test group is specified
    if not (run_gnss or run_nmea or run_time_mode or run_pps or run_persist):
        parser.error("No test groups specified. Use --gnss, --nmea, --time-mode, --pps, --all, or --persist")

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

        # TODO: Add NMEA tests
        # TODO: Add time-mode tests
        # TODO: Add PPS tests
        # TODO: Add persist tests

    finally:
        conn.close()

    return print_summary(results)


if __name__ == "__main__":
    sys.exit(main())
