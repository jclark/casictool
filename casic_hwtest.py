#!/usr/bin/env python3
"""Hardware integration tests for casictool.

Tests that casictool implementation works correctly on real hardware.
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass

from casic import DYN_MODEL_NAMES, DYN_MODEL_PORTABLE, DYN_MODEL_STATIONARY, TP_FIX_ONLY, TP_OFF, TP_ON
from casictool import LevelFormatter
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


def verify(conn: CasicConnection, props: ConfigProps, tool_log: logging.Logger) -> TestResult:
    """Apply props and verify they took effect."""
    job = ConfigJob(props=props)
    result = execute_job(conn, job, tool_log)
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
    conn: CasicConnection, props: ConfigProps, alt_props: ConfigProps, tool_log: logging.Logger
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
    result = execute_job(conn, job, tool_log)
    if not result.success:
        return Fail({"save": {"expected": "success", "actual": result.error}})

    # Set alt_props WITHOUT saving (changes RAM only)
    job = ConfigJob(props=alt_props)
    result = execute_job(conn, job, tool_log)
    if not result.success:
        return Fail({"alt_config": {"expected": "success", "actual": result.error}})

    # Reload from NVM - should restore props
    job = ConfigJob(reset=ResetMode.RELOAD)
    result = execute_job(conn, job, tool_log)
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
    if "min_elev" in props:
        parts.append(f"min_elev: {props['min_elev']}°")
    if "dyn_model" in props:
        name = DYN_MODEL_NAMES.get(props["dyn_model"], str(props["dyn_model"]))
        parts.append(f"dyn_model: {name}")
    if "time_mode" in props:
        parts.append(f"time_mode: {props['time_mode']}")
    if "time_pulse" in props:
        parts.append(f"time_pulse: {props['time_pulse']}")
    if "nmea_out" in props:
        nmea_out = props["nmea_out"]
        # Show only enabled messages
        enabled = [nmea.name for nmea in NMEA if nmea_out[nmea.value] > 0]
        parts.append(f"nmea_out: {{{', '.join(enabled)}}}")
    if "casic_out" in props:
        casic_out = props["casic_out"]
        parts.append(f"casic_out: {{{', '.join(sorted(casic_out))}}}")
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
    test_log: logging.Logger,
    tool_log: logging.Logger,
) -> tuple[int, int, list[ConfigProps]]:
    """Run a list of tests and return (passed, total, failed_tests)."""
    test_log.info(f"running {name} tests")
    passed = 0
    failed: list[ConfigProps] = []

    for props in tests:
        result = verify(conn, props, tool_log)
        log_result(test_log, props, result)
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
        # Collect failed tests for summary
        failures = [
            (name, props)
            for name, (_passed, _total, failed) in results.items()
            for props in failed
        ]
        if failures:
            log.error("failed tests:")
            for name, props in failures:
                log.error(f"  {name}: {format_props(props)}")

    return 0 if all_passed else 1


def run_persist_tests(
    conn: CasicConnection,
    name: str,
    tests: list[ConfigProps],
    test_log: logging.Logger,
    tool_log: logging.Logger,
) -> tuple[int, int, list[ConfigProps]]:
    """Run persist tests for a list of ConfigProps.

    For each test, use the next item in the list as alt_props (wrap around for last).
    """
    test_log.info(f"running {name} persist tests")
    passed = 0
    failed: list[ConfigProps] = []

    for i, props in enumerate(tests):
        # Use next item as alt_props (wrap around)
        alt_props = tests[(i + 1) % len(tests)]
        result = verify_persist(conn, props, alt_props, tool_log)
        if isinstance(result, Pass):
            test_log.info(f"PASS persist {format_props(props)}")
            passed += 1
        else:
            for key, vals in result.mismatches.items():
                test_log.error(f"FAIL {key}: expected {vals['expected']}, got {vals['actual']}")
            failed.append(props)

    return passed, len(tests), failed


# ============================================================================
# Test Data
# ============================================================================

GNSS_TESTS: list[ConfigProps] = [
    {"gnss": {GNSS.GPS, GNSS.BDS, GNSS.GLO}},
    {"gnss": {GNSS.GPS, GNSS.BDS}},
    {"gnss": {GNSS.BDS}},
    {"gnss": {GNSS.GLO}},
    # Good state: just GPS (last test leaves receiver in clean state)
    {"gnss": {GNSS.GPS}},
]

NMEA_TESTS: list[ConfigProps] = [
    # Multiple messages (no GSV - too much bandwidth at low baud rates)
    {"nmea_out": nmea_rates(GGA=1, RMC=1, GLL=1)},
    # Single message
    {"nmea_out": nmea_rates(GGA=1)},
    # Good state: just RMC enabled (last test leaves receiver in clean state)
    {"nmea_out": nmea_rates(RMC=1)},
]

# Sample ECEF position for testing
TEST_ECEF = (-1144698.0455, 6090335.4099, 1504171.3914)

TIME_MODE_TESTS: list[ConfigProps] = [
    # Survey-in mode with different parameters (dyn_model auto-set to Stationary)
    {"time_mode": SurveyMode(min_dur=60, acc=50.0), "dyn_model": DYN_MODEL_STATIONARY},
    {"time_mode": SurveyMode(min_dur=120, acc=25.0), "dyn_model": DYN_MODEL_STATIONARY},
    # Fixed position mode (dyn_model auto-set to Stationary)
    {"time_mode": FixedMode(ecef=TEST_ECEF, acc=10.0), "dyn_model": DYN_MODEL_STATIONARY},
    # Good state: mobile mode (dyn_model auto-set to Portable)
    {"time_mode": MobileMode(), "dyn_model": DYN_MODEL_PORTABLE},
]

PPS_TESTS: list[ConfigProps] = [
    # Disabled PPS (width=0 sets enable=TP_OFF)
    {"time_pulse": TimePulse(period=1.0, width=0.0, time_gnss=GNSS.GPS, enable=TP_OFF)},
    # BDS time source with 1ms pulse, enable=ON (always output)
    {"time_pulse": TimePulse(period=1.0, width=0.001, time_gnss=GNSS.BDS, enable=TP_ON)},
    # GLONASS time source with 100us pulse, enable=FIX_ONLY (default)
    {"time_pulse": TimePulse(period=1.0, width=0.0001, time_gnss=GNSS.GLO, enable=TP_FIX_ONLY)},
    # Good state: GPS time source with 0.1s pulse, FIX_ONLY (last test leaves receiver in clean state)
    {"time_pulse": TimePulse(period=1.0, width=0.1, time_gnss=GNSS.GPS, enable=TP_FIX_ONLY)},
]

CASIC_OUT_TESTS: list[ConfigProps] = [
    # Multiple messages
    {"casic_out": {"TIM-TP", "NAV-SOL", "NAV-TIMEUTC"}},
    # Single message
    {"casic_out": {"TIM-TP"}},
    # Good state: none enabled (last test leaves receiver in clean state)
    {"casic_out": set()},
]

MIN_ELEV_TESTS: list[ConfigProps] = [
    {"min_elev": 5},
    {"min_elev": 15},
    # Good state: 0° (factory default)
    {"min_elev": 0},
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
    parser.add_argument("--nmea-out", action="store_true", help="Test NMEA output")
    parser.add_argument("--casic-out", action="store_true", help="Test CASIC binary output")
    parser.add_argument("--time-mode", action="store_true", help="Test time modes")
    parser.add_argument("--pps", action="store_true", help="Test PPS configuration")
    parser.add_argument("--min-elev", action="store_true", help="Test minimum elevation")
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
    parser.add_argument(
        "--uart1",
        action="store_true",
        help="Use UART1 instead of UART0 (default)",
    )

    args = parser.parse_args()

    # Setup logging (output to stdout for hwtest)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(LevelFormatter("%(message)s"))

    # Test progress logger (INFO level normally)
    test_log = logging.getLogger("casic_hwtest")
    if args.debug:
        test_log.setLevel(logging.DEBUG)
    elif args.quiet:
        test_log.setLevel(logging.WARNING)
    else:
        test_log.setLevel(logging.INFO)
    test_log.addHandler(handler)

    # Protocol logger for lower layers (WARNING level normally, DEBUG if --debug)
    tool_log = logging.getLogger("casictool")
    tool_log.setLevel(logging.DEBUG if args.debug else logging.WARNING)
    tool_log.addHandler(handler)

    # Determine which tests to run
    run_gnss = args.gnss or args.all
    run_nmea = args.nmea_out or args.all
    run_casic_out = args.casic_out or args.all
    run_time_mode = getattr(args, "time_mode") or args.all
    run_pps = args.pps or args.all
    run_min_elev = args.min_elev or args.all
    run_persist = args.persist

    # Check that at least one test group or --persist is specified
    if not (run_gnss or run_nmea or run_casic_out or run_time_mode or run_pps or run_min_elev or run_persist):
        parser.error(
            "No test groups specified. "
            "Use --gnss, --nmea-out, --casic-out, --time-mode, --pps, --min-elev, --persist, or --all"
        )

    # Connect to receiver
    try:
        conn = CasicConnection(
            args.device, args.speed, packet_log=args.packet_log, log=tool_log,
            uart=1 if args.uart1 else 0,
        )
    except Exception as e:
        test_log.error(f"could not connect to {args.device}: {e}")
        return 1

    # Probe receiver once at startup
    is_casic, version = probe_receiver(conn, tool_log)
    if not is_casic:
        test_log.error("no response from receiver")
        conn.close()
        return 1
    if version:
        test_log.info(f"receiver: {version.sw_version}")
    else:
        test_log.info("receiver: CASIC (MON-VER not supported)")

    results: dict[str, tuple[int, int, list[ConfigProps]]] = {}

    try:
        # Run normal (RAM-only) tests if not --persist-only mode
        # NMEA/CASIC output runs first to minimize output before other tests
        if not run_persist or (run_gnss or run_nmea or run_casic_out or run_time_mode or run_pps or run_min_elev):
            if run_nmea:
                results["NMEA"] = run_tests(conn, "NMEA", NMEA_TESTS, test_log, tool_log)

            if run_casic_out:
                results["CASIC"] = run_tests(conn, "CASIC", CASIC_OUT_TESTS, test_log, tool_log)

            if run_gnss:
                results["GNSS"] = run_tests(conn, "GNSS", GNSS_TESTS, test_log, tool_log)

            if run_time_mode:
                results["Time Mode"] = run_tests(conn, "time mode", TIME_MODE_TESTS, test_log, tool_log)

            if run_pps:
                results["PPS"] = run_tests(conn, "PPS", PPS_TESTS, test_log, tool_log)

            if run_min_elev:
                results["Min Elev"] = run_tests(conn, "min elev", MIN_ELEV_TESTS, test_log, tool_log)

        # Run persist tests if --persist specified
        if run_persist:
            if run_nmea:
                results["NMEA Persist"] = run_persist_tests(
                    conn, "NMEA", NMEA_TESTS, test_log, tool_log
                )

            if run_casic_out:
                results["CASIC Persist"] = run_persist_tests(
                    conn, "CASIC", CASIC_OUT_TESTS, test_log, tool_log
                )

            if run_gnss:
                results["GNSS Persist"] = run_persist_tests(
                    conn, "GNSS", GNSS_TESTS, test_log, tool_log
                )

            if run_time_mode:
                results["Time Mode Persist"] = run_persist_tests(
                    conn, "time mode", TIME_MODE_TESTS, test_log, tool_log
                )

            if run_pps:
                results["PPS Persist"] = run_persist_tests(conn, "PPS", PPS_TESTS, test_log, tool_log)

            if run_min_elev:
                results["Min Elev Persist"] = run_persist_tests(
                    conn, "min elev", MIN_ELEV_TESTS, test_log, tool_log
                )

    finally:
        conn.close()

    return log_summary(test_log, results)


if __name__ == "__main__":
    sys.exit(main())
