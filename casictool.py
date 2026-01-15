#!/usr/bin/env python3
"""CASIC GPS receiver configuration tool."""

from __future__ import annotations

import argparse
import sys

import serial

from casic import (
    CFG_NAVX,
    CFG_PRT,
    CFG_RATE,
    CFG_TMODE,
    CFG_TP,
    MON_VER,
    CasicConnection,
    ReceiverConfig,
    VersionInfo,
    build_cfg_tmode,
    parse_cfg_navx,
    parse_cfg_prt,
    parse_cfg_rate,
    parse_cfg_tmode,
    parse_cfg_tp,
    parse_mon_ver,
)


def probe_receiver(conn: CasicConnection) -> tuple[bool, VersionInfo | None]:
    """Probe receiver with MON-VER to verify it's a CASIC device.

    Returns (is_casic, version_info). A NAK response proves it's CASIC
    even if MON-VER isn't supported.
    """
    result = conn.poll(MON_VER.cls, MON_VER.id)
    if result.success:
        return True, parse_mon_ver(result.payload)  # type: ignore[arg-type]
    if result.nak:
        return True, None  # NAK proves it's CASIC
    return False, None  # Timeout - not CASIC


def show_config(conn: CasicConnection) -> ReceiverConfig:
    """Query all CFG messages and return receiver configuration."""
    config = ReceiverConfig()

    # Query CFG-PRT
    result = conn.poll(CFG_PRT.cls, CFG_PRT.id)
    if result.success:
        config.port = parse_cfg_prt(result.payload)  # type: ignore[arg-type]

    # Query CFG-RATE
    result = conn.poll(CFG_RATE.cls, CFG_RATE.id)
    if result.success:
        config.rate = parse_cfg_rate(result.payload)  # type: ignore[arg-type]

    # Query CFG-TP
    result = conn.poll(CFG_TP.cls, CFG_TP.id)
    if result.success:
        config.time_pulse = parse_cfg_tp(result.payload)  # type: ignore[arg-type]

    # Query CFG-TMODE
    result = conn.poll(CFG_TMODE.cls, CFG_TMODE.id)
    if result.success:
        config.timing_mode = parse_cfg_tmode(result.payload)  # type: ignore[arg-type]

    # Query CFG-NAVX
    result = conn.poll(CFG_NAVX.cls, CFG_NAVX.id)
    if result.success:
        config.nav_engine = parse_cfg_navx(result.payload)  # type: ignore[arg-type]

    return config


def parse_ecef_coords(coord_str: str) -> tuple[float, float, float]:
    """Parse comma-separated ECEF coordinates."""
    parts = coord_str.split(",")
    if len(parts) != 3:
        raise ValueError("ECEF coordinates must be X,Y,Z (3 values)")
    return (float(parts[0].strip()), float(parts[1].strip()), float(parts[2].strip()))


def set_survey_mode(conn: CasicConnection, min_dur: int, acc: float) -> bool:
    """Configure receiver for survey-in mode."""
    payload = build_cfg_tmode(
        mode=1,  # Survey-In
        survey_min_dur=min_dur,
        survey_acc=acc,
    )
    return conn.send_and_wait_ack(CFG_TMODE.cls, CFG_TMODE.id, payload)


def set_fixed_position(
    conn: CasicConnection,
    ecef: tuple[float, float, float],
    acc: float,
) -> bool:
    """Configure receiver with fixed ECEF position."""
    payload = build_cfg_tmode(
        mode=2,  # Fixed
        fixed_pos=ecef,
        fixed_pos_acc=acc,
    )
    return conn.send_and_wait_ack(CFG_TMODE.cls, CFG_TMODE.id, payload)


def set_mobile_mode(conn: CasicConnection) -> bool:
    """Configure receiver for mobile/auto mode."""
    payload = build_cfg_tmode(mode=0)  # Auto
    return conn.send_and_wait_ack(CFG_TMODE.cls, CFG_TMODE.id, payload)


def main() -> int:
    """Main entry point for casictool CLI."""
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

    args = parser.parse_args()

    # Check mutual exclusivity of timing mode options
    mode_options = [args.survey, args.fixed_pos_ecef, args.mobile]
    if sum(bool(x) for x in mode_options) > 1:
        print(
            "Error: --survey, --fixed-pos-ecef, and --mobile are mutually exclusive",
            file=sys.stderr,
        )
        return 1

    # Handle timing mode options
    if args.survey:
        try:
            with CasicConnection(args.device, baudrate=args.speed) as conn:
                if not probe_receiver(conn)[0]:
                    print("Error: No response from receiver", file=sys.stderr)
                    return 1
                if set_survey_mode(conn, args.survey_time, args.survey_acc):
                    print(
                        f"Survey-in mode enabled: {args.survey_time}s, "
                        f"{args.survey_acc}m accuracy"
                    )
                else:
                    print("Error: Failed to set survey-in mode", file=sys.stderr)
                    return 1
        except serial.SerialException as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        return 0

    if args.fixed_pos_ecef:
        try:
            ecef = parse_ecef_coords(args.fixed_pos_ecef)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        try:
            with CasicConnection(args.device, baudrate=args.speed) as conn:
                if not probe_receiver(conn)[0]:
                    print("Error: No response from receiver", file=sys.stderr)
                    return 1
                if set_fixed_position(conn, ecef, args.fixed_pos_acc):
                    print(
                        f"Fixed position set: ECEF ({ecef[0]:.3f}, {ecef[1]:.3f}, {ecef[2]:.3f})"
                    )
                else:
                    print("Error: Failed to set fixed position", file=sys.stderr)
                    return 1
        except serial.SerialException as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        return 0

    if args.mobile:
        try:
            with CasicConnection(args.device, baudrate=args.speed) as conn:
                if not probe_receiver(conn)[0]:
                    print("Error: No response from receiver", file=sys.stderr)
                    return 1
                if set_mobile_mode(conn):
                    print("Mobile/auto mode enabled")
                else:
                    print("Error: Failed to set mobile mode", file=sys.stderr)
                    return 1
        except serial.SerialException as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        return 0

    if args.show_config:
        try:
            with CasicConnection(args.device, baudrate=args.speed) as conn:
                # Probe receiver first
                is_casic, version = probe_receiver(conn)
                if not is_casic:
                    print("Error: No response from receiver. Not a CASIC device?", file=sys.stderr)
                    return 1
                if version:
                    print(f"CASIC receiver: {version.sw_version} / {version.hw_version}")
                else:
                    print("CASIC receiver detected (MON-VER not supported)")
                print()
                config = show_config(conn)
                print(config.format())
        except serial.SerialException as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
