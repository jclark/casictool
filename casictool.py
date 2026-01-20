#!/usr/bin/env python3
"""CASIC GPS receiver configuration tool - CLI interface."""

from __future__ import annotations

import argparse
import logging
import sys
import time

import serial

from connection import CasicConnection
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
    # --speed will be used for changing the speed used by the GPS receiver
    parser.add_argument(
        "-s", "--device-speed", type=int, default=9600, help="Baud rate (default: 9600)"
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
    parser.add_argument(
        "--capture",
        type=float,
        metavar="SECONDS",
        help="Capture packets for N seconds after config (0=until interrupted). Requires --packet-log",
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
        "--mobile", action="store_true", help="Disable time mode"
    )

    # NMEA message output group
    nmea_group = parser.add_argument_group("NMEA Message Output")
    nmea_group.add_argument(
        "--nmea-out",
        type=str,
        metavar="MSGS",
        help="Set NMEA message output. Comma-separated list of messages to enable "
        "(GGA,GLL,GSA,GSV,RMC,VTG,ZDA). Use 'none' to disable all. Messages not listed will be disabled.",
    )

    # CASIC binary message output group
    casic_group = parser.add_argument_group("CASIC Binary Message Output")
    casic_group.add_argument(
        "--casic-out",
        type=str,
        metavar="MSGS",
        help="Set CASIC binary message output. Comma-separated list of messages to enable "
        "(e.g., TIM-TP,NAV-SOL). Use 'none' to disable all. Messages not listed will be disabled.",
    )

    # GNSS constellation group
    gnss_group = parser.add_argument_group("GNSS Configuration")
    gnss_group.add_argument(
        "-g",
        "--gnss",
        type=str,
        metavar="SYSTEMS",
        help="Comma-separated list of GNSS constellations (GPS,GAL,BDS,GLO) that should be enabled. "
        "Constellations not listed will be disabled."
    )
    gnss_group.add_argument(
        "--min-elev",
        type=int,
        metavar="DEG",
        help="Minimum satellite elevation angle in degrees (0-90)",
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
    nvm_group = parser.add_argument_group("Non-volatile Memory (NVM) Operations")
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
    # Check mutual exclusivity of time mode options
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

    # --capture requires --packet-log
    if args.capture is not None and not args.packet_log:
        return "--capture requires --packet-log"

    # Validate min_elev range (CLI: 0-90)
    if args.min_elev is not None and not (0 <= args.min_elev <= 90):
        return "--min-elev must be between 0 and 90 degrees"

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
            raise ValueError(f"unknown constellation: {item}")

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
        nmea_str: Comma-separated message list (e.g., "GGA,RMC,ZDA") or "none"

    Returns:
        List of rates indexed by NMEA.value (1 = enabled, 0 = disabled)
    """
    if nmea_str.strip().lower() == "none":
        return [0] * len(NMEA)

    result = [0] * len(NMEA)

    for item in nmea_str.split(","):
        item = item.strip().upper()
        if not item:
            continue
        try:
            nmea = NMEA[item]
            result[nmea.value] = 1
        except KeyError:
            raise ValueError(f"unknown NMEA message: {item}")

    return result


def parse_casic_out(casic_str: str) -> set[str]:
    """Parse --casic-out argument into set of message names.

    Args:
        casic_str: Comma-separated message list (e.g., "TIM-TP,NAV-SOL") or "none"

    Returns:
        Set of uppercase message names (empty set for "none")

    Raises:
        ValueError: If unknown message name specified
    """
    from casic import MSG_IDS

    if casic_str.strip().lower() == "none":
        return set()

    result: set[str] = set()

    for item in casic_str.split(","):
        item = item.strip().upper().replace("_", "-")
        if not item:
            continue
        if item not in MSG_IDS:
            raise ValueError(f"unknown CASIC message: {item}")
        result.add(item)

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
        raise ValueError(f"unknown time source: {system}; use GPS, GAL, BDS, or GLO")
    return GNSS(system)


def build_job(args: argparse.Namespace) -> tuple[ConfigJob, str | None]:
    """Build ConfigJob from parsed arguments.

    Returns (job, error_message). error_message is None on success.
    """
    props: ConfigProps = {}

    # Parse and set time mode
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

    # Parse and set CASIC output configuration
    if args.casic_out is not None:
        try:
            props["casic_out"] = parse_casic_out(args.casic_out)
        except ValueError as e:
            return ConfigJob(), str(e)

    # Parse and set GNSS configuration
    if args.gnss:
        try:
            props["gnss"] = parse_gnss_arg(args.gnss)
        except ValueError as e:
            return ConfigJob(), str(e)

    # Set minimum elevation
    if args.min_elev is not None:
        props["min_elev"] = args.min_elev

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


def print_config(result: CommandResult, job: ConfigJob) -> None:
    """Print --show-config output to stdout."""
    # Print configuration if show_config and no other operations
    has_config_ops = (
        job.props is not None
        or job.save != SaveMode.NONE
        or job.reset != ResetMode.NONE
    )

    if job.show_config and not has_config_ops:
        if result.version:
            print(f"Receiver version: {result.version.sw_version} / {result.version.hw_version}")
        if result.config_after:
            print(result.config_after.format())


def capture_packets(conn: CasicConnection, duration: float, log: logging.Logger) -> None:
    """Capture packets for a specified duration.

    Args:
        conn: Connection to receiver (packets logged automatically via receive_packet)
        duration: Seconds to capture (0 = until interrupted)
        log: Logger for status messages
    """
    if duration == 0:
        # Capture indefinitely until interrupted
        while True:
            conn.receive_packet(timeout=0.5)
    else:
        # Capture for specified duration
        start = time.monotonic()
        while time.monotonic() - start < duration:
            remaining = duration - (time.monotonic() - start)
            conn.receive_packet(timeout=min(0.5, remaining))


def run_casictool(argv: list[str], log: logging.Logger) -> CommandResult:
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
    if not has_any_operation(job) and args.capture is None:
        # Return empty result; main() will print help
        return CommandResult(success=True, error="no_operation")

    # Execute the job
    try:
        with CasicConnection(
            args.device, baudrate=args.device_speed, packet_log=args.packet_log, log=log,
            uart=1 if args.uart1 else 0,
        ) as conn:
            # Probe receiver once (skip for factory/cold reset)
            if job.reset not in (ResetMode.FACTORY, ResetMode.COLD):
                is_casic, version = probe_receiver(conn, log)
                if not is_casic:
                    return CommandResult(
                        success=False, error="no response from receiver; not a CASIC device?"
                    )
            else:
                version = None

            # Execute job only if there are operations
            if has_any_operation(job):
                result = execute_job(conn, job, log)
                result.version = version
            else:
                result = CommandResult(success=True)
                result.version = version

            # Capture packets if requested
            if args.capture is not None:
                capture_packets(conn, args.capture, log)

            return result
    except KeyboardInterrupt:
        log.debug("interrupted")
        return CommandResult(success=True)
    except serial.SerialException as e:
        return CommandResult(success=False, error=str(e))


class LevelFormatter(logging.Formatter):
    """Formatter that prefixes non-INFO messages with their level."""

    def format(self, record: logging.LogRecord) -> str:
        if record.levelno == logging.DEBUG:
            record.msg = f"debug: {record.msg}"
        elif record.levelno == logging.WARNING:
            record.msg = f"warning: {record.msg}"
        elif record.levelno == logging.ERROR:
            record.msg = f"error: {record.msg}"
        return super().format(record)


def main() -> int:
    """CLI entry point."""
    # Parse args early to get logging level
    args = parse_args(sys.argv[1:])

    # Setup logging
    log = logging.getLogger("casictool")
    handler = logging.StreamHandler(sys.stderr)
    if args.debug:
        level = logging.DEBUG
    elif args.quiet:
        level = logging.WARNING
    else:
        level = logging.INFO
    handler.setLevel(level)
    log.setLevel(level)
    handler.setFormatter(LevelFormatter("%(message)s"))
    log.addHandler(handler)

    result = run_casictool(sys.argv[1:], log)

    if result.error == "no_operation":
        # Print help when no operation specified
        parse_args(["--help"])
        return 0

    if not result.success:
        log.error(result.error)
        return 1

    # Build job again to check show_config flag for printing
    job, _ = build_job(args)
    print_config(result, job)

    return 0


if __name__ == "__main__":
    sys.exit(main())
