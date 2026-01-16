#!/usr/bin/env python3
"""CASIC GPS receiver configuration tool - CLI interface."""

from __future__ import annotations

import argparse
import sys

import serial

from casic import CasicConnection
from job import (
    GNSS,
    NMEA,
    CommandResult,
    ConfigJob,
    ConfigProps,
    FixedMode,
    MobileMode,
    ResetMode,
    SaveMode,
    SurveyMode,
    TimePulse,
    execute_job,
    parse_ecef_coords,
    probe_receiver,
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
    parser.add_argument(
        "--packet-log",
        type=str,
        metavar="PATH",
        help="Log all packets to JSONL file",
    )

    # Time mode group
    time_mode_group = parser.add_argument_group("Time Mode")
    time_mode_group.add_argument(
        "--survey", action="store_true", help="Enable survey-in mode"
    )
    time_mode_group.add_argument(
        "--survey-time",
        type=int,
        default=2000,
        metavar="SECS",
        help="Survey-in minimum duration in seconds (default: 2000)",
    )
    time_mode_group.add_argument(
        "--survey-acc",
        type=float,
        default=20.0,
        metavar="METERS",
        help="Survey-in target accuracy in meters (default: 20)",
    )
    time_mode_group.add_argument(
        "--fixed-pos-ecef",
        type=str,
        metavar="X,Y,Z",
        help="Set fixed ECEF position (meters, comma-separated)",
    )
    time_mode_group.add_argument(
        "--fixed-pos-acc",
        type=float,
        default=1.0,
        metavar="METERS",
        help="Fixed position accuracy in meters (default: 1)",
    )
    time_mode_group.add_argument(
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
        "-g",
        "--gnss",
        type=str,
        metavar="SYSTEMS",
        help="Enable GNSS constellations (GPS,GAL,BDS,GLO). "
        "Disables constellations not listed. "
        "Note: QZSS, NAVIC, SBAS not supported by this receiver.",
    )

    # Time pulse (PPS) group
    pps_group = parser.add_argument_group("Time Pulse (PPS)")
    pps_group.add_argument(
        "--pps",
        type=float,
        metavar="WIDTH",
        help="Set PPS pulse width in seconds (0 to disable, max 1.0)",
    )
    pps_group.add_argument(
        "--time-gnss",
        type=str,
        metavar="SYSTEM",
        help="Set PPS time source (GPS, GAL, BDS, GLO)",
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


VALID_GNSS = {"GPS", "GAL", "GALILEO", "BDS", "GLO", "GLN", "GLONASS"}


def parse_gnss_arg(gnss_str: str) -> set[GNSS]:
    """Parse --gnss argument into set of GNSS enums.

    Args:
        gnss_str: Comma-separated list (e.g., "GPS,BDS,GLO")

    Returns:
        Set of GNSS enums

    Raises:
        ValueError: If unknown or unsupported constellation specified
    """
    result: set[GNSS] = set()

    for item in gnss_str.split(","):
        item = item.strip().upper()
        if not item:
            continue
        if item not in VALID_GNSS:
            raise ValueError(f"Unknown constellation: {item}")

        if item == "GPS":
            result.add(GNSS.GPS)
        elif item in ("GAL", "GALILEO"):
            result.add(GNSS.GAL)
        elif item == "BDS":
            result.add(GNSS.BDS)
        elif item in ("GLO", "GLN", "GLONASS"):
            result.add(GNSS.GLO)

    return result


def parse_nmea_out(nmea_str: str) -> list[int]:
    """Parse --nmea-out argument into NMEARates list.

    Args:
        nmea_str: Comma-separated message list (e.g., "GGA,RMC,ZDA")

    Returns:
        List of rates indexed by NMEA.value (1 = enabled, 0 = disabled)
    """
    result = [0] * len(NMEA)

    for item in nmea_str.split(","):
        item = item.strip().upper()
        if not item:
            continue
        try:
            nmea = NMEA[item]
            result[nmea.value] = 1
        except KeyError:
            raise ValueError(f"Unknown NMEA message: {item}")

    return result


def parse_time_gnss_arg(system: str) -> GNSS:
    """Validate and parse --time-gnss argument.

    Args:
        system: Time source constellation name

    Returns:
        GNSS enum

    Raises:
        ValueError: If unknown time source specified
    """
    system = system.strip().upper()
    if system == "GLONASS":
        system = "GLO"
    elif system == "GALILEO":
        system = "GAL"
    if system not in {"GPS", "GAL", "BDS", "GLO"}:
        raise ValueError(f"Unknown time source: {system}. Use GPS, GAL, BDS, or GLO.")
    return GNSS(system)


def build_job(args: argparse.Namespace) -> tuple[ConfigJob, str | None]:
    """Build ConfigJob from parsed arguments.

    Returns (job, error_message). error_message is None on success.
    """
    props: ConfigProps = {}

    # Parse and set timing mode
    if args.survey:
        props["time_mode"] = SurveyMode(min_dur=args.survey_time, acc=args.survey_acc)

    if args.fixed_pos_ecef:
        try:
            ecef = parse_ecef_coords(args.fixed_pos_ecef)
            props["time_mode"] = FixedMode(ecef=ecef, acc=args.fixed_pos_acc)
        except ValueError as e:
            return ConfigJob(), str(e)

    if args.mobile:
        props["time_mode"] = MobileMode()

    # Parse and set NMEA output configuration
    if args.nmea_out:
        try:
            props["nmea_out"] = parse_nmea_out(args.nmea_out)
        except ValueError as e:
            return ConfigJob(), str(e)

    # Parse and set GNSS configuration
    if args.gnss:
        try:
            props["gnss"] = parse_gnss_arg(args.gnss)
        except ValueError as e:
            return ConfigJob(), str(e)

    # Parse and set PPS configuration
    if args.pps is not None or args.time_gnss:
        if args.pps is not None and (args.pps < 0 or args.pps > 1.0):
            return ConfigJob(), "PPS width must be between 0 and 1.0 seconds"

        # Default values
        width = args.pps if args.pps is not None else 0.0001  # 100us default
        time_gnss = GNSS.GPS  # Default to GPS

        if args.time_gnss:
            try:
                time_gnss = parse_time_gnss_arg(args.time_gnss)
            except ValueError as e:
                return ConfigJob(), str(e)

        props["time_pulse"] = TimePulse(period=1.0, width=width, time_gnss=time_gnss)

    # Determine save mode
    save = SaveMode.NONE
    if args.save_all:
        save = SaveMode.ALL
    elif args.save:
        save = SaveMode.CHANGES

    # Determine reset mode
    reset = ResetMode.NONE
    if args.reload:
        reset = ResetMode.RELOAD
    elif args.reset:
        reset = ResetMode.COLD
    elif args.factory_reset:
        reset = ResetMode.FACTORY

    job = ConfigJob(
        props=props if props else None,
        save=save,
        reset=reset,
        show_config=args.show_config,
    )

    return job, None


def has_any_operation(job: ConfigJob) -> bool:
    """Check if the job specifies any operations."""
    return (
        job.props is not None
        or job.save != SaveMode.NONE
        or job.reset != ResetMode.NONE
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
        job.props is not None
        or job.save != SaveMode.NONE
        or job.reset != ResetMode.NONE
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
        with CasicConnection(
            args.device, baudrate=args.speed, packet_log=args.packet_log
        ) as conn:
            # Probe receiver once (skip for factory/cold reset)
            if job.reset not in (ResetMode.FACTORY, ResetMode.COLD):
                is_casic, version = probe_receiver(conn)
                if not is_casic:
                    return CommandResult(
                        success=False, error="No response from receiver. Not a CASIC device?"
                    )
            else:
                version = None
            result = execute_job(conn, job)
            result.version = version
            return result
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
