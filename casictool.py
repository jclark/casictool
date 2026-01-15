#!/usr/bin/env python3
"""CASIC GPS receiver configuration tool - CLI interface."""

from __future__ import annotations

import argparse
import sys

import serial

from casic import CFG_MASK_ALL, CasicConnection
from job import (
    CommandResult,
    ConfigJob,
    execute_job,
    parse_ecef_coords,
    parse_gnss_arg,
    parse_nmea_out,
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="CASIC GPS receiver configuration tool",
        prog="casictool",
    )

    parser.add_argument(
        "-d", "--device", default="/dev/ttyUSB0", help="Serial device (default: /dev/ttyUSB0)"
    )
    parser.add_argument(
        "-s", "--speed", type=int, default=9600, help="Baud rate (default: 9600)"
    )
    parser.add_argument(
        "--show-config", action="store_true", help="Show current configuration"
    )

    # Timing mode group
    timing_group = parser.add_argument_group("Timing Mode")
    timing_group.add_argument(
        "--survey", action="store_true", help="Enable survey-in mode"
    )
    timing_group.add_argument(
        "--survey-time",
        type=int,
        default=2000,
        metavar="SECS",
        help="Survey-in minimum duration in seconds (default: 2000)",
    )
    timing_group.add_argument(
        "--survey-acc",
        type=float,
        default=20.0,
        metavar="METERS",
        help="Survey-in target accuracy in meters (default: 20)",
    )
    timing_group.add_argument(
        "--fixed-pos-ecef",
        type=str,
        metavar="X,Y,Z",
        help="Set fixed ECEF position (meters, comma-separated)",
    )
    timing_group.add_argument(
        "--fixed-pos-acc",
        type=float,
        default=1.0,
        metavar="METERS",
        help="Fixed position accuracy in meters (default: 1)",
    )
    timing_group.add_argument(
        "--mobile", action="store_true", help="Enable mobile/auto mode (disable timing mode)"
    )

    # NMEA message output group
    nmea_group = parser.add_argument_group("NMEA Message Output")
    nmea_group.add_argument(
        "--nmea-out",
        type=str,
        metavar="MSGS",
        help="Set NMEA message output. Comma-separated list of messages to enable "
        "(GGA,GLL,GSA,GSV,RMC,VTG,ZDA). Messages not listed will be disabled.",
    )

    # GNSS constellation group
    gnss_group = parser.add_argument_group("GNSS Configuration")
    gnss_group.add_argument(
        "--gnss",
        type=str,
        metavar="SYSTEMS",
        help="Enable GNSS constellations (GPS,BDS,GLO). "
        "Disables constellations not listed. "
        "Note: GAL, QZSS, NAVIC, SBAS not supported by this receiver.",
    )

    # NVM operations group
    nvm_group = parser.add_argument_group("Configuration Storage")
    nvm_group.add_argument(
        "--save",
        action="store_true",
        help="Save configuration changed by this command to NVM",
    )
    nvm_group.add_argument(
        "--save-all",
        action="store_true",
        help="Save all current configuration to NVM",
    )
    nvm_group.add_argument(
        "--reload",
        action="store_true",
        help="Reload configuration from NVM (discard unsaved changes)",
    )
    nvm_group.add_argument(
        "--reset",
        action="store_true",
        help="Cold start: reload from NVM and clear navigation data",
    )
    nvm_group.add_argument(
        "--factory-reset",
        action="store_true",
        help="Factory reset: restore NVM to defaults and reset receiver",
    )

    return parser.parse_args(argv)


def validate_args(args: argparse.Namespace) -> str | None:
    """Validate parsed arguments for mutual exclusivity.

    Returns error message or None if valid.
    """
    # Check mutual exclusivity of timing mode options
    mode_options = [args.survey, args.fixed_pos_ecef, args.mobile]
    if sum(bool(x) for x in mode_options) > 1:
        return "--survey, --fixed-pos-ecef, and --mobile are mutually exclusive"

    # Check mutual exclusivity of save options
    if args.save and args.save_all:
        return "--save and --save-all are mutually exclusive"

    # Check mutual exclusivity of reset options
    reset_options = [args.reload, args.reset, args.factory_reset]
    if sum(bool(x) for x in reset_options) > 1:
        return "--reload, --reset, and --factory-reset are mutually exclusive"

    return None


def build_job(args: argparse.Namespace) -> tuple[ConfigJob, str | None]:
    """Build ConfigJob from parsed arguments.

    Returns (job, error_message). error_message is None on success.
    """
    job = ConfigJob()

    # Parse and set timing mode
    if args.survey:
        job.survey = (args.survey_time, args.survey_acc)

    if args.fixed_pos_ecef:
        try:
            ecef = parse_ecef_coords(args.fixed_pos_ecef)
            job.fixed_pos = (ecef, args.fixed_pos_acc)
        except ValueError as e:
            return job, str(e)

    if args.mobile:
        job.mobile = True

    # Parse and set NMEA output configuration
    if args.nmea_out:
        try:
            job.nmea_enable = parse_nmea_out(args.nmea_out)
        except ValueError as e:
            return job, str(e)

    # Parse and set GNSS configuration
    if args.gnss:
        try:
            job.gnss = parse_gnss_arg(args.gnss)
        except ValueError as e:
            return job, str(e)

    # Set NVM operations
    if args.save_all:
        job.save_mask = CFG_MASK_ALL
    elif args.save:
        job.save_changes = True

    if args.reload:
        job.reload = True
    if args.reset:
        job.reset = True
    if args.factory_reset:
        job.factory_reset = True

    # Set show_config
    job.show_config = args.show_config

    return job, None


def has_any_operation(job: ConfigJob) -> bool:
    """Check if the job specifies any operations."""
    return (
        job.survey is not None
        or job.fixed_pos is not None
        or job.mobile
        or job.gnss is not None
        or job.nmea_enable is not None
        or job.save_mask is not None
        or job.save_changes
        or job.reload
        or job.reset
        or job.factory_reset
        or job.show_config
    )


def print_result(result: CommandResult, job: ConfigJob) -> None:
    """Print command result to stdout/stderr."""
    # Print operation messages
    for msg in result.operations:
        if msg.startswith("Warning:"):
            print(msg, file=sys.stderr)
        else:
            print(msg)

    # Print configuration if show_config and no other operations
    has_config_ops = (
        job.survey is not None
        or job.fixed_pos is not None
        or job.mobile
        or job.gnss is not None
        or job.nmea_enable is not None
        or job.save_mask is not None
        or job.save_changes
        or job.reload
        or job.reset
        or job.factory_reset
    )

    if job.show_config and not has_config_ops:
        if result.version:
            print(f"CASIC receiver: {result.version.sw_version} / {result.version.hw_version}")
        else:
            print("CASIC receiver detected (MON-VER not supported)")
        print()
        if result.config_after:
            print(result.config_after.format())


def run_casictool(argv: list[str]) -> CommandResult:
    """Run casictool with given arguments.

    Callable from other programs. Returns structured result.
    """
    args = parse_args(argv)

    # Validate arguments
    error = validate_args(args)
    if error:
        return CommandResult(success=False, error=error)

    # Build job from arguments
    job, error = build_job(args)
    if error:
        return CommandResult(success=False, error=error)

    # Check if any operation is requested
    if not has_any_operation(job):
        # Return empty result; main() will print help
        return CommandResult(success=True, error="no_operation")

    # Execute the job
    try:
        with CasicConnection(args.device, baudrate=args.speed) as conn:
            return execute_job(conn, job)
    except serial.SerialException as e:
        return CommandResult(success=False, error=str(e))


def main() -> int:
    """CLI entry point."""
    result = run_casictool(sys.argv[1:])

    if result.error == "no_operation":
        # Print help when no operation specified
        parse_args(["--help"])
        return 0

    if not result.success:
        print(f"Error: {result.error}", file=sys.stderr)
        return 1

    # Build job again to check show_config flag for printing
    args = parse_args(sys.argv[1:])
    job, _ = build_job(args)
    print_result(result, job)

    return 0


if __name__ == "__main__":
    sys.exit(main())
